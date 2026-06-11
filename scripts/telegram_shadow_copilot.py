"""
Shadow Portfolio Telegram Copilot V1
=====================================
Sends Telegram notifications for PORTFOLIO_BALANCED_V1 shadow picks.

NOT automatic betting. Manual execution only.
Does NOT modify production BetIQ logic or prediction generation.

Usage:
  python scripts/telegram_shadow_copilot.py --dry-run
  python scripts/telegram_shadow_copilot.py
  python scripts/telegram_shadow_copilot.py --daily-report
  python scripts/telegram_shadow_copilot.py --new-bets
  python scripts/telegram_shadow_copilot.py --settlements
  python scripts/telegram_shadow_copilot.py --divergences

Environment variables required:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  SHADOW_ALERTS_ENABLED   (true|false, default true)
  DASHBOARD_PUBLIC_URL
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore

from app.database.supabase_repository import get_repository
from app.services.simulation.bankroll_simulator import (
    _PORTFOLIO_WEIGHTS,
    _PORTFOLIO_PRIORITY,
    _SHADOW_IMPLIED_ODD,
    _EXPERIMENTAL_STRATEGIES,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
ENABLED      = os.environ.get("SHADOW_ALERTS_ENABLED", "true").lower() == "true"
DASH_URL     = os.environ.get("DASHBOARD_PUBLIC_URL", "").rstrip("/")
RESET_AT     = os.environ.get("TRACKING_RESET_AT", "").strip()
STARTING_BR  = 100.0
PORTFOLIO    = "PORTFOLIO_BALANCED_V1"

DATA_DIR     = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SENT_BETS_FILE  = DATA_DIR / "telegram_alerts_sent.json"
SENT_SETT_FILE  = DATA_DIR / "telegram_settlements_sent.json"
SENT_DIV_FILE   = DATA_DIR / "telegram_divergences_sent.json"


# ─── Dedup helpers ────────────────────────────────────────────────────────────

def _load_sent(path: Path) -> set:
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_sent(path: Path, keys: set) -> None:
    path.write_text(json.dumps(sorted(keys), indent=2), encoding="utf-8")


# ─── Telegram ────────────────────────────────────────────────────────────────

def _send_telegram(text: str, dry_run: bool = False) -> bool:
    if dry_run:
        print("\n" + "─" * 60)
        print("[DRY RUN] Would send:")
        print(text)
        print("─" * 60)
        return True
    if not ENABLED:
        return False
    if not BOT_TOKEN or not CHAT_ID:
        return False
    if _requests is None:
        logger.error("requests library not installed — pip install requests")
        return False
    try:
        resp = _requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.error(f"Telegram error: {exc}")
        return False


# ─── Data fetching ────────────────────────────────────────────────────────────

_PRED_COLS = (
    "id, market, status, selection_mode, bookmaker_odd, ev_percentage, "
    "created_at, prediction_date, home_team, away_team, league, fixture_id, "
    "offensive_profile, defensive_profile, market_regime, confidence_score, "
    "volatility_score, chaos_score, country, kickoff_time"
)


def _fetch_data() -> Tuple[List[Dict], Dict]:
    repo = get_repository()
    if RESET_AT:
        fc = "created_at" if "T" in RESET_AT else "prediction_date"
        fv = RESET_AT
    else:
        fv = (date.today() - timedelta(days=60)).isoformat()
        fc = "prediction_date"

    rows, page, sz = [], 0, 1000
    while True:
        batch = (
            repo._client.table("predictions")
            .select(_PRED_COLS)
            .gte(fc, fv)
            .range(page * sz, (page + 1) * sz - 1)
            .execute()
            .data or []
        )
        rows.extend(batch)
        if len(batch) < sz:
            break
        page += 1

    needed = list({r["fixture_id"] for r in rows if r.get("fixture_id")})
    fixtures: List[Dict] = []
    for i in range(0, len(needed), 200):
        batch = (
            repo._client.table("fixtures")
            .select("fixture_id, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status")
            .in_("fixture_id", needed[i : i + 200])
            .execute()
            .data or []
        )
        fixtures.extend(batch)

    fixture_lookup = {f["fixture_id"]: f for f in fixtures if f.get("fixture_id")}
    return rows, fixture_lookup


# ─── Shadow prediction generation ────────────────────────────────────────────

def _gp(profile, key, default=0):
    if not profile:
        return default
    if isinstance(profile, str):
        try:
            profile = json.loads(profile)
        except Exception:
            return default
    return profile.get(key, default) or default


def _generate_shadow_predictions(rows: List[Dict], fixture_lookup: Dict) -> List[Dict]:
    """Generate shadow predictions for ALL rows (settled + pending), no lookahead bias."""
    shadow: List[Dict] = []

    for pred in rows:
        fid        = pred.get("fixture_id", "")
        kickoff    = pred.get("kickoff_time") or pred.get("prediction_date", "")
        created_at = pred.get("created_at", "")
        if not kickoff or not created_at:
            continue
        try:
            if (
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                > datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            ):
                continue
        except Exception:
            continue

        op = pred.get("offensive_profile") or {}
        if isinstance(op, str):
            try: op = json.loads(op)
            except Exception: op = {}

        btts_rate       = _gp(op, "btts_rate", 0)
        over_2_5_rate   = _gp(op, "over_2_5_rate", 0)
        early_goal_rate = _gp(op, "early_goal_rate", 0)
        away_btts_rate  = _gp(op, "away_btts_rate", 0)
        explosive_score = _gp(op, "explosive_pairing_score", 0)
        market_regime   = pred.get("market_regime", "")
        volatility      = pred.get("volatility_score", 0) or 0
        chaos           = pred.get("chaos_score", 0) or 0

        fixture = fixture_lookup.get(fid, {})
        home_sc = fixture.get("home_score")
        away_sc = fixture.get("away_score")

        def _add(strategy: str, market: str, confidence: int, reason: str) -> None:
            sp: Dict = {
                "fixture_id":            fid,
                "strategy":              strategy,
                "market":                market,
                "confidence":            confidence,
                "reason":                reason,
                "home_team":             pred.get("home_team", ""),
                "away_team":             pred.get("away_team", ""),
                "league":                pred.get("league", ""),
                "country":               pred.get("country", ""),
                "kickoff_time":          kickoff,
                "created_at":            created_at,
                "bookmaker_odd":         None,
                "simulated_result":      None,
                "simulated_profit_loss": None,
            }
            if home_sc is not None and away_sc is not None:
                h, a = int(home_sc), int(away_sc)
                outcomes = {
                    "BTTS_YES":           "WON" if h > 0 and a > 0 else "LOST",
                    "BTTS_NO":            "WON" if h == 0 or a == 0 else "LOST",
                    "HOME_TEAM_OVER_0_5": "WON" if h >= 1 else "LOST",
                    "HOME_TEAM_OVER_1_5": "WON" if h >= 2 else "LOST",
                    "AWAY_TEAM_OVER_0_5": "WON" if a >= 1 else "LOST",
                    "AWAY_TEAM_OVER_1_5": "WON" if a >= 2 else "LOST",
                }
                r = outcomes.get(market)
                sp["simulated_result"] = r
                if r == "WON":
                    sp["simulated_profit_loss"] = 0.9 if "BTTS" in market else 0.8
                elif r == "LOST":
                    sp["simulated_profit_loss"] = -1.0
            shadow.append(sp)

        HIGH = {"HIGH_TEMPO", "CHAOTIC", "HIGH_TEMPO_OVER", "SECOND_HALF_CHAOS"}

        if btts_rate >= 65 or (volatility >= 60 and chaos >= 55):
            _add("SHADOW_BTTS", "BTTS_YES", 70, f"btts_rate={btts_rate}%")
        if over_2_5_rate <= 35 or btts_rate <= 30:
            _add("SHADOW_BTTS", "BTTS_NO", 65, f"btts_rate={btts_rate}%")
        if early_goal_rate >= 60 or (over_2_5_rate >= 50 and btts_rate >= 50):
            _add("SHADOW_TEAM_GOALS", "HOME_TEAM_OVER_0_5", 70, f"early_goal={early_goal_rate}%")
        if early_goal_rate >= 75 and over_2_5_rate >= 60:
            _add("SHADOW_TEAM_GOALS", "HOME_TEAM_OVER_1_5", 75, f"early_goal={early_goal_rate}%")
        if away_btts_rate >= 50 or (btts_rate >= 55 and over_2_5_rate >= 50):
            _add("SHADOW_TEAM_GOALS", "AWAY_TEAM_OVER_0_5", 70, f"away_btts={away_btts_rate}%")
        if away_btts_rate >= 65 and over_2_5_rate >= 65:
            _add("SHADOW_TEAM_GOALS", "AWAY_TEAM_OVER_1_5", 75, f"away_btts={away_btts_rate}%")
        if early_goal_rate >= 70 and over_2_5_rate >= 60 and market_regime in HIGH:
            _add("TEAM_GOALS_CONSERVATIVE", "HOME_TEAM_OVER_0_5", 80, f"regime={market_regime}")
        if early_goal_rate >= 80 and over_2_5_rate >= 70 and explosive_score >= 65:
            _add("TEAM_GOALS_CONSERVATIVE", "HOME_TEAM_OVER_1_5", 85, f"explosive={explosive_score}")
        if away_btts_rate >= 60 and btts_rate >= 60:
            _add("TEAM_GOALS_CONSERVATIVE", "AWAY_TEAM_OVER_0_5", 75, f"away_btts={away_btts_rate}%")
        if away_btts_rate >= 70 and over_2_5_rate >= 70:
            _add("TEAM_GOALS_CONSERVATIVE", "AWAY_TEAM_OVER_1_5", 80, f"away_btts={away_btts_rate}%")

    return shadow


def _generate_experimental_picks(rows: List[Dict], fixture_lookup: Dict) -> List[Dict]:
    """Generate EXPERIMENTAL bucket picks from real BetIQ prediction rows."""
    picks: List[Dict] = []
    preferred = {"HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5"}
    excluded  = {"FT_UNDER_1_5", "HT_UNDER_0_5"}

    seen: set = set()  # avoid duplicates within experimental

    for r in rows:
        market = r.get("market", "")
        odd    = float(r.get("bookmaker_odd") or 0.0)
        status = r.get("status", "")
        fid    = str(r.get("fixture_id", ""))
        kickoff = r.get("kickoff_time") or r.get("prediction_date", "")

        # NO_EXTREME_UNDERS
        is_extreme_under = (
            ("_UNDER_" in market or market.startswith("UNDER")) and odd > 4.0
        )
        if (
            market not in excluded
            and not is_extreme_under
            and odd >= 1.01
            and (fid, market, "NO_EXTREME_UNDERS") not in seen
        ):
            seen.add((fid, market, "NO_EXTREME_UNDERS"))
            picks.append({
                "fixture_id":            fid,
                "strategy":              "NO_EXTREME_UNDERS",
                "market":                market,
                "confidence":            r.get("confidence_score") or 65,
                "reason":                "no extreme unders filter",
                "home_team":             r.get("home_team", ""),
                "away_team":             r.get("away_team", ""),
                "league":                r.get("league", ""),
                "country":               r.get("country", ""),
                "kickoff_time":          kickoff,
                "created_at":            r.get("created_at", ""),
                "bookmaker_odd":         odd,
                "simulated_result":      status if status in ("WON", "LOST") else None,
                "simulated_profit_loss": None,
            })

        # SHADOW_MARKET_V1
        ev = float(r.get("ev_percentage") or 0)
        if (
            1.3 <= odd <= 5.0
            and market not in excluded
            and ev <= 35
            and market in preferred
            and (fid, market, "SHADOW_MARKET_V1") not in seen
        ):
            seen.add((fid, market, "SHADOW_MARKET_V1"))
            picks.append({
                "fixture_id":            fid,
                "strategy":              "SHADOW_MARKET_V1",
                "market":                market,
                "confidence":            r.get("confidence_score") or 65,
                "reason":                "shadow market v1 filter",
                "home_team":             r.get("home_team", ""),
                "away_team":             r.get("away_team", ""),
                "league":                r.get("league", ""),
                "country":               r.get("country", ""),
                "kickoff_time":          kickoff,
                "created_at":            r.get("created_at", ""),
                "bookmaker_odd":         odd,
                "simulated_result":      status if status in ("WON", "LOST") else None,
                "simulated_profit_loss": None,
            })

    return picks


# ─── Portfolio builder (all statuses) ────────────────────────────────────────

def _build_portfolio_all(
    shadow_predictions: List[Dict],
    experimental_picks: List[Dict],
) -> List[Dict]:
    """
    Build PORTFOLIO_BALANCED_V1 picks (settled + pending) after deduplication.
    Each pick is tagged with _bucket and _stake.
    """
    buckets: Dict[str, List[Dict]] = {
        "TEAM_GOALS_CONSERVATIVE": [],
        "SHADOW_TEAM_GOALS":       [],
        "SHADOW_BTTS":             [],
        "EXPERIMENTAL":            [],
    }

    for sp in shadow_predictions:
        strat = sp.get("strategy", "")
        if strat in ("TEAM_GOALS_CONSERVATIVE", "SHADOW_TEAM_GOALS", "SHADOW_BTTS"):
            buckets[strat].append(sp)

    for ep in experimental_picks:
        buckets["EXPERIMENTAL"].append(ep)

    timeline: List[Dict] = []
    for bucket, picks in buckets.items():
        stake = _PORTFOLIO_WEIGHTS.get(bucket, 0.10)
        for p in picks:
            timeline.append({**p, "_bucket": bucket, "_stake": stake})
    timeline.sort(key=lambda x: x.get("kickoff_time") or "")

    seen: Dict[str, int] = {}
    deduped: List[Dict] = []
    for pick in timeline:
        fid    = pick.get("fixture_id", "")
        bucket = pick.get("_bucket", "")
        prio   = _PORTFOLIO_PRIORITY.index(bucket) if bucket in _PORTFOLIO_PRIORITY else 99
        if fid not in seen:
            seen[fid] = prio
            deduped.append(pick)
        elif prio < seen[fid]:
            deduped = [p for p in deduped if p.get("fixture_id") != fid]
            seen[fid] = prio
            deduped.append(pick)

    deduped.sort(key=lambda x: x.get("kickoff_time") or "")
    return deduped


# ─── Bankroll series ──────────────────────────────────────────────────────────

def _pick_odd(pick: Dict) -> float:
    odd = float(pick.get("bookmaker_odd") or pick.get("odd") or 0.0)
    if odd >= 1.01:
        return odd
    return float(_SHADOW_IMPLIED_ODD.get(pick.get("market", ""), 1.8))


def _compute_bankroll_series(
    portfolio_picks: List[Dict],
) -> Tuple[float, List[Tuple[Dict, float, float, float]]]:
    """
    Walk settled picks chronologically and compute bankroll at each step.
    Returns (current_bankroll, [(pick, bk_before, bk_after, pl_units), ...])
    """
    settled = sorted(
        [p for p in portfolio_picks if p.get("simulated_result") in ("WON", "LOST")],
        key=lambda x: x.get("kickoff_time") or "",
    )
    bk     = STARTING_BR
    series: List[Tuple[Dict, float, float, float]] = []
    for pick in settled:
        stake  = pick.get("_stake", 0.10)
        odd    = _pick_odd(pick)
        result = pick.get("simulated_result", "")
        bk_before = round(bk, 4)
        pl = round((odd - 1.0) * stake, 6) if result == "WON" else round(-stake, 6)
        bk = round(bk + pl, 4)
        series.append((pick, bk_before, round(bk, 4), round(pl, 6)))
    return round(bk, 2), series


# ─── Message formatters ───────────────────────────────────────────────────────

def _fmt_daily_report(
    portfolio_picks: List[Dict],
    fixture_lookup: Dict,
    target_date: Optional[date] = None,
) -> str:
    """Message Type 1 — Morning Daily Report."""
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    current_bk, series = _compute_bankroll_series(portfolio_picks)
    date_str = str(target_date)

    yest = [(p, b4, ba, pl) for (p, b4, ba, pl) in series
            if (p.get("kickoff_time") or "")[:10] == date_str]

    start_br  = yest[0][1] if yest else current_bk
    end_br    = yest[-1][2] if yest else current_bk
    daily_pl  = round(end_br - start_br, 2)

    total_profit = round(current_bk - STARTING_BR, 2)
    total_staked = sum(p.get("_stake", 0.10) for p, _, _, _ in series)
    total_roi    = round(total_profit / total_staked * 100, 2) if total_staked else 0.0

    peak = STARTING_BR
    max_dd = 0.0
    for _, _, ba, _ in series:
        if ba > peak: peak = ba
        dd = peak - ba
        if dd > max_dd: max_dd = dd

    yest_wins   = [x for x in yest if x[0].get("simulated_result") == "WON"]
    yest_losses = [x for x in yest if x[0].get("simulated_result") == "LOST"]
    yest_pl     = round(sum(x[3] for x in yest), 2)
    hit_rate    = round(len(yest_wins) / len(yest) * 100, 1) if yest else 0.0

    now_utc = datetime.now(timezone.utc)
    open_pos = [p for p in portfolio_picks
                if p.get("simulated_result") is None
                and (p.get("kickoff_time") or "") > now_utc.isoformat()[:19]]

    breakdown: Dict[str, Dict] = {}
    for p, _, _, pl in yest:
        b = p.get("_bucket", "?")
        bd = breakdown.setdefault(b, {"W": 0, "L": 0, "pl": 0.0})
        if p.get("simulated_result") == "WON": bd["W"] += 1
        else: bd["L"] += 1
        bd["pl"] = round(bd["pl"] + pl, 4)

    top_wins   = sorted([x for x in yest if x[3] > 0],  key=lambda x: -x[3])[:3]
    top_losses = sorted([x for x in yest if x[3] < 0],  key=lambda x:  x[3])[:3]

    lines = [
        "📊 <b>Shadow Portfolio Daily Report</b>",
        f"Date: {date_str}",
        "",
        f"Starting BR yesterday: {start_br:.2f}u",
        f"Ending BR yesterday:   {end_br:.2f}u",
        f"Daily P/L:             {daily_pl:+.2f}u",
        f"Current BR:            {current_bk:.2f}u",
        f"Total ROI:             {total_roi:+.1f}%",
        f"Max Drawdown:          {max_dd:.2f}u",
        f"Open positions:        {len(open_pos)}",
        "",
        "Yesterday results:",
        f"  Wins:       {len(yest_wins)}",
        f"  Losses:     {len(yest_losses)}",
        f"  Void:       0",
        f"  Hit rate:   {hit_rate:.1f}%",
        f"  Profit/loss: {yest_pl:+.2f}u",
        "",
        "Strategy breakdown:",
    ]
    for bucket in ["TEAM_GOALS_CONSERVATIVE", "SHADOW_TEAM_GOALS", "SHADOW_BTTS", "EXPERIMENTAL"]:
        bd = breakdown.get(bucket, {"W": 0, "L": 0, "pl": 0.0})
        lines.append(f"  {bucket}: {bd['W']}W/{bd['L']}L  {bd['pl']:+.2f}u")

    if top_wins:
        lines += ["", "Top 3 winning bets:"]
        for p, _, _, pl in top_wins:
            m = f"{p.get('home_team','')} vs {p.get('away_team','')} / {p.get('market','')} / {p.get('_bucket','')} / +{pl:.4f}u"
            lines.append(f"  - {m}")

    if top_losses:
        lines += ["", "Top 3 losing bets:"]
        for p, _, _, pl in top_losses:
            m = f"{p.get('home_team','')} vs {p.get('away_team','')} / {p.get('market','')} / {p.get('_bucket','')} / {pl:.4f}u"
            lines.append(f"  - {m}")

    return "\n".join(lines)


def _fmt_new_bet(pick: Dict, current_bk: float) -> str:
    """Message Type 2 — New Portfolio Bet."""
    fid   = pick.get("fixture_id", "")
    stake = pick.get("_stake", 0.10)
    ko    = (pick.get("kickoff_time") or "")[:16].replace("T", " ")
    dash  = f"{DASH_URL}/matches/{fid}" if DASH_URL else f"fixture:{fid}"

    return "\n".join([
        "📌 <b>New Shadow Portfolio Bet</b>",
        "",
        f"Match: {pick.get('home_team','')} vs {pick.get('away_team','')}",
        f"League: {pick.get('league') or pick.get('country','')}",
        f"Strategy: {pick.get('_bucket', pick.get('strategy',''))}",
        f"Market: {pick.get('market','')}",
        f"Confidence: {pick.get('confidence', '?')}%",
        f"Stake: {stake}u",
        f"Current BR: {current_bk:.2f}u",
        f"Kickoff: {ko}",
        f"Reason: {pick.get('reason', '')}",
        f"Open: {dash}",
        "",
        "<i>Manual execution only. No bet placed automatically.</i>",
    ])


def _fmt_settlement(
    pick: Dict,
    bk_before: float,
    bk_after: float,
    current_bk: float,
    fixture_lookup: Dict,
) -> str:
    """Message Type 3 — Settlement Result (WON or LOST)."""
    fid    = pick.get("fixture_id", "")
    fix    = fixture_lookup.get(fid, {})
    h_sc   = fix.get("home_score", "?")
    a_sc   = fix.get("away_score", "?")
    pl     = round(bk_after - bk_before, 4)
    result = pick.get("simulated_result", "")
    icon   = "✅" if result == "WON" else "❌"
    pl_str = f"+{pl:.4f}u" if pl >= 0 else f"{pl:.4f}u"

    return "\n".join([
        f"{icon} <b>Shadow Bet {result}</b>",
        "",
        f"Match: {pick.get('home_team','')} vs {pick.get('away_team','')}",
        f"Market: {pick.get('market','')}",
        f"Strategy: {pick.get('_bucket', pick.get('strategy',''))}",
        f"Result: {result}",
        f"Score: {h_sc}-{a_sc}",
        f"P/L: {pl_str}",
        f"BR impact: {bk_before:.2f}u → {bk_after:.2f}u",
        f"Current BR: {current_bk:.2f}u",
    ])


def _fmt_divergence(div: Dict) -> str:
    """Message Type 4 — Model Divergence (new alert)."""
    fid  = div.get("fixture_id", "")
    ko   = (div.get("kickoff_time") or "")[:16].replace("T", " ")
    dash = f"{DASH_URL}/matches/{fid}" if DASH_URL else f"fixture:{fid}"

    return "\n".join([
        "⚔️ <b>Model Divergence</b>",
        "",
        f"Match: {div.get('home_team','')} vs {div.get('away_team','')}",
        "",
        f"BetIQ: {div.get('betiq_market','')}",
        f"Shadow Portfolio: {div.get('shadow_market','')}",
        f"Shadow Strategy: {div.get('shadow_strategy','')}",
        f"Kickoff: {ko}",
        "",
        "Why important:",
        "Shadow and BetIQ disagree on this fixture.",
        "",
        f"Open: {dash}",
    ])


def _fmt_divergence_settled(div: Dict, fixture_lookup: Dict) -> str:
    """Message Type 4 — Divergence Settlement."""
    fid      = div.get("fixture_id", "")
    fix      = fixture_lookup.get(fid, {})
    h_sc     = fix.get("home_score", "?")
    a_sc     = fix.get("away_score", "?")
    betiq_r  = div.get("betiq_result", "PENDING")
    shadow_r = div.get("shadow_result", "PENDING")

    if betiq_r == "WON" and shadow_r == "WON":   winner = "BOTH"
    elif betiq_r == "WON":                        winner = "BETIQ"
    elif shadow_r == "WON":                       winner = "SHADOW"
    else:                                          winner = "NONE"

    bk_b = div.get("bk_before", 0.0)
    bk_a = div.get("bk_after",  0.0)

    return "\n".join([
        "⚔️ <b>Divergence Settled</b>",
        "",
        f"Match: {div.get('home_team','')} vs {div.get('away_team','')}",
        f"Score: {h_sc}-{a_sc}",
        "",
        f"BetIQ: {div.get('betiq_market','')} — {betiq_r}",
        f"Shadow: {div.get('shadow_market','')} — {shadow_r}",
        "",
        f"Winner: {winner}",
        f"BR impact: {bk_b:.2f}u → {bk_a:.2f}u",
    ])


# ─── Divergence detection ────────────────────────────────────────────────────

def _detect_divergences(rows: List[Dict], portfolio_picks: List[Dict]) -> List[Dict]:
    """Fixtures where BetIQ and Shadow portfolio disagree on market."""
    betiq_by_fid: Dict[str, List[Dict]] = {}
    for r in rows:
        if r.get("selection_mode") in ("LIVE", "LIVE_SAFE"):
            fid = r.get("fixture_id", "")
            if fid:
                betiq_by_fid.setdefault(fid, []).append(r)

    shadow_by_fid = {p["fixture_id"]: p for p in portfolio_picks if p.get("fixture_id")}

    divs: List[Dict] = []
    for fid, sp in shadow_by_fid.items():
        if fid not in betiq_by_fid:
            continue
        shadow_market = sp.get("market", "")
        for bq in betiq_by_fid[fid]:
            betiq_market = bq.get("market", "")
            if betiq_market == shadow_market:
                continue
            bq_status = bq.get("status", "")
            divs.append({
                "fixture_id":      fid,
                "home_team":       sp.get("home_team") or bq.get("home_team", ""),
                "away_team":       sp.get("away_team") or bq.get("away_team", ""),
                "league":          sp.get("league") or bq.get("league", ""),
                "kickoff_time":    sp.get("kickoff_time", ""),
                "betiq_market":    betiq_market,
                "shadow_market":   shadow_market,
                "shadow_strategy": sp.get("_bucket") or sp.get("strategy", ""),
                "shadow_result":   sp.get("simulated_result"),
                "betiq_result":    bq_status if bq_status in ("WON", "LOST") else "PENDING",
                "_shadow_pick":    sp,
                "_betiq_row":      bq,
            })

    return divs


# ─── Handler functions ───────────────────────────────────────────────────────

def _do_daily_report(
    portfolio_picks: List[Dict],
    fixture_lookup: Dict,
    dry_run: bool,
    counters: Dict,
) -> None:
    target = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    sent   = _load_sent(SENT_SETT_FILE)
    key    = f"daily_report:{target}"

    if not dry_run and key in sent:
        counters["skipped_duplicates"] += 1
        return

    if not BOT_TOKEN and not dry_run:
        counters["skipped_missing_config"] += 1
        return

    msg = _fmt_daily_report(portfolio_picks, fixture_lookup, target)
    ok  = _send_telegram(msg, dry_run)
    if ok:
        counters["daily_reports_sent"] += 1
        if not dry_run:
            sent.add(key)
            _save_sent(SENT_SETT_FILE, sent)


def _do_new_bets(
    portfolio_picks: List[Dict],
    current_bk: float,
    dry_run: bool,
    counters: Dict,
) -> None:
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc + timedelta(hours=6)
    now_s   = now_utc.isoformat()[:19]
    cut_s   = cutoff.isoformat()[:19]
    sent    = _load_sent(SENT_BETS_FILE)
    new_sent = set(sent)

    pending = [
        p for p in portfolio_picks
        if p.get("simulated_result") is None
        and now_s <= (p.get("kickoff_time") or "")[:19] <= cut_s
    ]

    for pick in pending:
        fid    = pick.get("fixture_id", "")
        bucket = pick.get("_bucket", "")
        strat  = pick.get("strategy", "")
        market = pick.get("market", "")
        key    = f"{fid}:{PORTFOLIO}:{strat or bucket}:{market}"

        if key in sent:
            counters["skipped_duplicates"] += 1
            continue

        if not BOT_TOKEN and not dry_run:
            counters["skipped_missing_config"] += 1
            continue

        msg = _fmt_new_bet(pick, current_bk)
        ok  = _send_telegram(msg, dry_run)
        if ok:
            counters["new_bet_alerts_sent"] += 1
            new_sent.add(key)

    if not dry_run:
        _save_sent(SENT_BETS_FILE, new_sent)


def _do_settlements(
    portfolio_picks: List[Dict],
    fixture_lookup: Dict,
    dry_run: bool,
    counters: Dict,
) -> None:
    sent_bets  = _load_sent(SENT_BETS_FILE)
    sent_setts = _load_sent(SENT_SETT_FILE)
    current_bk, series = _compute_bankroll_series(portfolio_picks)
    new_sent = set(sent_setts)

    for pick, bk_before, bk_after, pl in series:
        fid    = pick.get("fixture_id", "")
        bucket = pick.get("_bucket", "")
        strat  = pick.get("strategy", "")
        market = pick.get("market", "")
        result = pick.get("simulated_result", "")

        bet_key  = f"{fid}:{PORTFOLIO}:{strat or bucket}:{market}"
        sett_key = f"{fid}:{PORTFOLIO}:{strat or bucket}:{market}:{result}"

        # In live mode: only settle picks we previously alerted as new bets
        if not dry_run and bet_key not in sent_bets:
            continue

        if sett_key in sent_setts:
            counters["skipped_duplicates"] += 1
            continue

        if not BOT_TOKEN and not dry_run:
            counters["skipped_missing_config"] += 1
            continue

        msg = _fmt_settlement(pick, bk_before, bk_after, current_bk, fixture_lookup)
        ok  = _send_telegram(msg, dry_run)
        if ok:
            counters["settlement_alerts_sent"] += 1
            new_sent.add(sett_key)

    if not dry_run:
        _save_sent(SENT_SETT_FILE, new_sent)


def _do_divergences(
    rows: List[Dict],
    portfolio_picks: List[Dict],
    fixture_lookup: Dict,
    dry_run: bool,
    counters: Dict,
) -> None:
    sent      = _load_sent(SENT_DIV_FILE)
    divs      = _detect_divergences(rows, portfolio_picks)
    now_utc   = datetime.now(timezone.utc)
    current_bk, _ = _compute_bankroll_series(portfolio_picks)
    new_sent  = set(sent)

    for div in divs:
        fid          = div.get("fixture_id", "")
        betiq_market = div.get("betiq_market", "")
        shadow_market = div.get("shadow_market", "")
        key      = f"{fid}:{betiq_market}:{shadow_market}"
        sett_key = f"{key}:settled"

        shadow_r = div.get("shadow_result")
        betiq_r  = div.get("betiq_result", "PENDING")
        is_settled = shadow_r in ("WON", "LOST") and betiq_r in ("WON", "LOST")

        if is_settled:
            # Only send settlement if we sent the initial divergence alert
            if not dry_run and key not in sent:
                continue
            if sett_key in sent:
                counters["skipped_duplicates"] += 1
                continue

            sp    = div.get("_shadow_pick", {})
            stake = sp.get("_stake", 0.10)
            odd   = _pick_odd(sp)
            if shadow_r == "WON":
                div["bk_after"]  = round(current_bk + (odd - 1.0) * stake, 2)
            else:
                div["bk_after"]  = round(current_bk - stake, 2)
            div["bk_before"] = current_bk

            msg = _fmt_divergence_settled(div, fixture_lookup)
            ok  = _send_telegram(msg, dry_run)
            if ok:
                counters["divergence_alerts_sent"] += 1
                new_sent.add(sett_key)
        else:
            ko = div.get("kickoff_time", "")
            if ko and ko[:19] < now_utc.isoformat()[:19]:
                continue  # past fixture with no result yet — skip
            if key in sent:
                counters["skipped_duplicates"] += 1
                continue
            if not BOT_TOKEN and not dry_run:
                counters["skipped_missing_config"] += 1
                continue

            msg = _fmt_divergence(div)
            ok  = _send_telegram(msg, dry_run)
            if ok:
                counters["divergence_alerts_sent"] += 1
                new_sent.add(key)

    if not dry_run:
        _save_sent(SENT_DIV_FILE, new_sent)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Shadow Portfolio Telegram Copilot V1")
    parser.add_argument("--dry-run",      action="store_true", help="Print messages, do not send")
    parser.add_argument("--daily-report", action="store_true", help="Morning report only")
    parser.add_argument("--new-bets",     action="store_true", help="New bet alerts only")
    parser.add_argument("--settlements",  action="store_true", help="Settlement alerts only")
    parser.add_argument("--divergences",  action="store_true", help="Divergence alerts only")
    args = parser.parse_args()

    run_all = not any([args.daily_report, args.new_bets, args.settlements, args.divergences])
    dry_run = args.dry_run

    if dry_run:
        print("[DRY RUN MODE — no messages will be sent]\n")

    if not BOT_TOKEN and not dry_run:
        print("[WARNING] TELEGRAM_BOT_TOKEN not configured")
    if not CHAT_ID and not dry_run:
        print("[WARNING] TELEGRAM_CHAT_ID not configured")
    if not ENABLED and not dry_run:
        print("[WARNING] SHADOW_ALERTS_ENABLED=false — all sends will be skipped")

    print("Fetching data from Supabase...")
    rows, fixture_lookup = _fetch_data()
    print(f"  Predictions: {len(rows)} | Fixtures: {len(fixture_lookup)}")

    print("Generating shadow predictions...")
    shadow_predictions   = _generate_shadow_predictions(rows, fixture_lookup)
    experimental_picks   = _generate_experimental_picks(rows, fixture_lookup)
    print(f"  Shadow: {len(shadow_predictions)} | Experimental: {len(experimental_picks)}")

    print("Building portfolio (all statuses)...")
    portfolio_picks = _build_portfolio_all(shadow_predictions, experimental_picks)
    settled_count   = sum(1 for p in portfolio_picks if p.get("simulated_result") in ("WON", "LOST"))
    pending_count   = sum(1 for p in portfolio_picks if p.get("simulated_result") is None)
    print(f"  Portfolio: {len(portfolio_picks)} total ({settled_count} settled, {pending_count} pending)")

    current_bk, _ = _compute_bankroll_series(portfolio_picks)
    print(f"  Current bankroll: {current_bk:.2f}u")

    counters: Dict[str, int] = {
        "daily_reports_sent":     0,
        "new_bet_alerts_sent":    0,
        "settlement_alerts_sent": 0,
        "divergence_alerts_sent": 0,
        "skipped_duplicates":     0,
        "skipped_missing_config": 0,
    }

    if args.daily_report or run_all:
        print("\nProcessing daily report...")
        _do_daily_report(portfolio_picks, fixture_lookup, dry_run, counters)

    if args.new_bets or run_all:
        print("Processing new bets...")
        _do_new_bets(portfolio_picks, current_bk, dry_run, counters)

    if args.settlements or run_all:
        print("Processing settlements...")
        _do_settlements(portfolio_picks, fixture_lookup, dry_run, counters)

    if args.divergences or run_all:
        print("Processing divergences...")
        _do_divergences(rows, portfolio_picks, fixture_lookup, dry_run, counters)

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for k, v in counters.items():
        print(f"  {k:<30}: {v}")
    print("=" * 50)
    print("\nSHADOW_TELEGRAM_COPILOT_OK")


if __name__ == "__main__":
    main()
