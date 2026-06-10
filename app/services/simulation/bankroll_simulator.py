"""
Bankroll Simulator
==================
Flat-staking simulation for individual strategies and PORTFOLIO_BALANCED_V1.
Analytics only — no production DB writes.

Strategies simulated:
  Individual : BETIQ_LIVE_SAFE, SHADOW_TEAM_GOALS, TEAM_GOALS_CONSERVATIVE,
               SHADOW_BTTS, NO_EXTREME_UNDERS, SHADOW_MARKET_V1
  Portfolio  : PORTFOLIO_BALANCED_V1 (weighted, deduplicated by fixture)

Public entry point:
  build_bankroll_simulation(rows, shadow_predictions, starting_bankroll, stake)
  → dict ready for /api/shadow-lab response key "bankroll_simulation"
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

REAL_ODDS_THRESHOLD: float = 1.3

_SHADOW_IMPLIED_ODD: Dict[str, float] = {
    "BTTS_YES": 1.9,
    "BTTS_NO": 1.9,
    "HOME_TEAM_OVER_0_5": 1.8,
    "HOME_TEAM_OVER_1_5": 1.8,
    "AWAY_TEAM_OVER_0_5": 1.8,
    "AWAY_TEAM_OVER_1_5": 1.8,
}

_PORTFOLIO_WEIGHTS: Dict[str, float] = {
    "TEAM_GOALS_CONSERVATIVE": 0.40,
    "SHADOW_TEAM_GOALS": 0.30,
    "SHADOW_BTTS": 0.20,
    "EXPERIMENTAL": 0.10,
}

_PORTFOLIO_PRIORITY: List[str] = [
    "TEAM_GOALS_CONSERVATIVE",
    "SHADOW_TEAM_GOALS",
    "SHADOW_BTTS",
    "EXPERIMENTAL",
]

_EXPERIMENTAL_STRATEGIES: List[str] = ["NO_EXTREME_UNDERS", "SHADOW_MARKET_V1"]


# ─── Internal helpers ────────────────────────────────────────────────────────

def _effective_odd(pick: Dict) -> float:
    """Return the effective bookmaker odd for a normalised pick."""
    odd = pick.get("odd") or 0.0
    if float(odd) >= 1.01:
        return float(odd)
    return float(_SHADOW_IMPLIED_ODD.get(pick.get("market", ""), 1.8))


def _pl_per_unit(pick: Dict) -> float:
    """P/L per 1u stake for a single settled pick."""
    result = pick.get("result", "")
    if result == "WON":
        return round(_effective_odd(pick) - 1.0, 6)
    if result == "LOST":
        return -1.0
    return 0.0


def _volatility(pl_list: List[float]) -> float:
    """Population std-dev of per-pick P/L values (in units)."""
    n = len(pl_list)
    if n < 2:
        return 0.0
    mean = sum(pl_list) / n
    variance = sum((x - mean) ** 2 for x in pl_list) / n
    return round(math.sqrt(variance), 4)


def _empty_metrics(strategy: str, starting_bankroll: float, stake: float) -> Dict:
    return {
        "strategy": strategy,
        "starting_bankroll": starting_bankroll,
        "final_bankroll": starting_bankroll,
        "profit": 0.0,
        "roi": 0.0,
        "settled_picks": 0,
        "wins": 0,
        "losses": 0,
        "hit_rate": 0.0,
        "avg_odd": 0.0,
        "max_drawdown_units": 0.0,
        "max_drawdown_percent": 0.0,
        "peak_bankroll": starting_bankroll,
        "lowest_bankroll": starting_bankroll,
        "longest_win_streak": 0,
        "longest_losing_streak": 0,
        "profit_factor": 0.0,
        "volatility_score": 0.0,
        "equity_curve": [{
            "index": 0, "settled_at": "", "fixture_id": "", "match": "",
            "market": "", "result": "", "odd": 0.0, "stake": stake,
            "profit_loss": 0.0, "bankroll_after": starting_bankroll,
        }],
    }


def _calc_metrics(
    strategy: str,
    settled_picks: List[Dict],
    starting_bankroll: float,
    stake: float,
) -> Dict:
    """Compute all simulation metrics for a sorted list of settled picks."""
    if not settled_picks:
        return _empty_metrics(strategy, starting_bankroll, stake)

    bankroll = starting_bankroll
    peak     = starting_bankroll
    lowest   = starting_bankroll
    max_dd_units = 0.0
    max_dd_pct   = 0.0
    cur_loss = cur_win = 0
    max_loss = max_win = 0
    total_win_profit = 0.0
    total_loss_abs   = 0.0
    odds_acc  = 0.0
    pl_series: List[float] = []

    equity_curve = [{
        "index": 0, "settled_at": "", "fixture_id": "", "match": "",
        "market": "", "result": "", "odd": 0.0, "stake": stake,
        "profit_loss": 0.0, "bankroll_after": round(starting_bankroll, 2),
    }]

    for i, pick in enumerate(settled_picks):
        eff_odd = _effective_odd(pick)
        pl      = round(_pl_per_unit(pick) * stake, 6)
        bankroll = round(bankroll + pl, 6)
        pl_series.append(pl)

        if bankroll > peak:
            peak = bankroll
        if bankroll < lowest:
            lowest = bankroll

        dd_u = round(peak - bankroll, 6)
        dd_p = (dd_u / peak * 100.0) if peak > 0 else 0.0
        if dd_u > max_dd_units:
            max_dd_units = dd_u
        if dd_p > max_dd_pct:
            max_dd_pct = dd_p

        if pick.get("result") == "WON":
            cur_win += 1
            cur_loss = 0
            total_win_profit += max(pl, 0.0)
        else:
            cur_loss += 1
            cur_win = 0
            total_loss_abs += abs(min(pl, 0.0))

        if cur_win > max_win:
            max_win = cur_win
        if cur_loss > max_loss:
            max_loss = cur_loss

        odds_acc += eff_odd

        home = pick.get("home_team", "")
        away = pick.get("away_team", "")
        match_str = f"{home} vs {away}" if home or away else ""
        date_str  = (pick.get("date") or "")

        equity_curve.append({
            "index":        i + 1,
            "settled_at":   date_str[:19] if date_str else "",
            "fixture_id":   pick.get("fixture_id", ""),
            "match":        match_str,
            "market":       pick.get("market", ""),
            "result":       pick.get("result", ""),
            "odd":          round(eff_odd, 3),
            "stake":        stake,
            "profit_loss":  round(pl, 4),
            "bankroll_after": round(bankroll, 2),
        })

    n = len(settled_picks)
    wins_count   = sum(1 for p in settled_picks if p.get("result") == "WON")
    losses_count = n - wins_count
    profit       = round(bankroll - starting_bankroll, 4)
    roi          = round(profit / (n * stake) * 100.0, 2) if n else 0.0
    hit_rate     = round(wins_count / n * 100.0, 1)
    pf           = round(total_win_profit / total_loss_abs, 3) if total_loss_abs > 0 else (
        999.0 if total_win_profit > 0 else 0.0
    )
    avg_odd = round(odds_acc / n, 3)

    return {
        "strategy":           strategy,
        "starting_bankroll":  starting_bankroll,
        "final_bankroll":     round(bankroll, 2),
        "profit":             round(profit, 2),
        "roi":                roi,
        "settled_picks":      n,
        "wins":               wins_count,
        "losses":             losses_count,
        "hit_rate":           hit_rate,
        "avg_odd":            avg_odd,
        "max_drawdown_units": round(max_dd_units, 2),
        "max_drawdown_percent": round(max_dd_pct, 1),
        "peak_bankroll":      round(peak, 2),
        "lowest_bankroll":    round(lowest, 2),
        "longest_win_streak": max_win,
        "longest_losing_streak": max_loss,
        "profit_factor":      pf,
        "volatility_score":   _volatility(pl_series),
        "equity_curve":       equity_curve,
    }


# ─── Normalisation ───────────────────────────────────────────────────────────

def _norm_shadow(sp: Dict) -> Optional[Dict]:
    """Normalise a shadow_prediction entry to a pick dict."""
    result = sp.get("simulated_result")
    if result not in ("WON", "LOST"):
        return None
    market = sp.get("market", "")
    return {
        "result":     result,
        "odd":        sp.get("bookmaker_odd") or _SHADOW_IMPLIED_ODD.get(market, 1.8),
        "market":     market,
        "fixture_id": str(sp.get("fixture_id", "")),
        "home_team":  sp.get("home_team", ""),
        "away_team":  sp.get("away_team", ""),
        "date":       sp.get("kickoff_time") or sp.get("created_at") or "",
    }


def _norm_real(row: Dict) -> Optional[Dict]:
    """Normalise a Supabase prediction row to a pick dict."""
    result = row.get("status")
    if result not in ("WON", "LOST"):
        return None
    odd = row.get("bookmaker_odd") or 0.0
    if float(odd) < 1.01:
        return None
    return {
        "result":     result,
        "odd":        float(odd),
        "market":     row.get("market", ""),
        "fixture_id": str(row.get("fixture_id", "")),
        "home_team":  row.get("home_team", ""),
        "away_team":  row.get("away_team", ""),
        "date":       row.get("kickoff_time") or row.get("created_at") or "",
    }


def _sorted_picks(picks: List[Dict]) -> List[Dict]:
    return sorted(picks, key=lambda x: x.get("date") or "")


# ─── Strategy extractors ─────────────────────────────────────────────────────

def _picks_betiq_live_safe(rows: List[Dict]) -> List[Dict]:
    return _sorted_picks([
        p for p in (_norm_real(r) for r in rows if r.get("selection_mode") in ("LIVE_SAFE", "LIVE"))
        if p
    ])


def _picks_no_extreme_unders(rows: List[Dict]) -> List[Dict]:
    result = []
    for r in rows:
        market = r.get("market", "")
        odd    = float(r.get("bookmaker_odd") or 0.0)
        is_extreme_under = (
            ("_UNDER_" in market or market.startswith("UNDER")) and odd > 4.0
        )
        if market not in ("FT_UNDER_1_5", "HT_UNDER_0_5") and not is_extreme_under:
            p = _norm_real(r)
            if p:
                result.append(p)
    return _sorted_picks(result)


def _picks_shadow_market_v1(rows: List[Dict]) -> List[Dict]:
    preferred = {"HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5"}
    excluded  = {"FT_UNDER_1_5", "HT_UNDER_0_5"}
    result = []
    for r in rows:
        odd    = float(r.get("bookmaker_odd") or 0.0)
        market = r.get("market", "")
        ev     = r.get("ev_percentage") or 0
        if (
            REAL_ODDS_THRESHOLD <= odd <= 5.0
            and market not in excluded
            and float(ev) <= 35
            and market in preferred
        ):
            p = _norm_real(r)
            if p:
                result.append(p)
    return _sorted_picks(result)


def _picks_shadow_strategy(shadow_predictions: List[Dict], strategy: str) -> List[Dict]:
    return _sorted_picks([
        p for p in (_norm_shadow(sp) for sp in shadow_predictions if sp.get("strategy") == strategy)
        if p
    ])


# ─── Portfolio ───────────────────────────────────────────────────────────────

def _simulate_portfolio_balanced_v1(
    strategy_picks: Dict[str, List[Dict]],
    starting_bankroll: float,
) -> Dict:
    """Simulate PORTFOLIO_BALANCED_V1 with deduplication by fixture_id."""
    experimental = _sorted_picks(
        strategy_picks.get("NO_EXTREME_UNDERS", []) +
        strategy_picks.get("SHADOW_MARKET_V1",  [])
    )

    bucket_picks: Dict[str, List[Dict]] = {
        "TEAM_GOALS_CONSERVATIVE": strategy_picks.get("TEAM_GOALS_CONSERVATIVE", []),
        "SHADOW_TEAM_GOALS":       strategy_picks.get("SHADOW_TEAM_GOALS",       []),
        "SHADOW_BTTS":             strategy_picks.get("SHADOW_BTTS",             []),
        "EXPERIMENTAL":            experimental,
    }

    timeline: List[Dict] = []
    for bucket, picks in bucket_picks.items():
        for pick in picks:
            timeline.append({**pick, "_bucket": bucket})
    timeline.sort(key=lambda x: x.get("date") or "")

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

    deduped.sort(key=lambda x: x.get("date") or "")

    bankroll = starting_bankroll
    peak     = starting_bankroll
    lowest   = starting_bankroll
    max_dd_u = max_dd_p = 0.0
    cur_loss = cur_win = 0
    max_loss = max_win = 0
    wins = losses = 0
    total_win_profit = total_loss_abs = 0.0
    pl_series: List[float] = []

    equity_curve = [{
        "index": 0, "settled_at": "", "fixture_id": "", "match": "",
        "market": "", "result": "", "odd": 0.0, "stake": 0.0,
        "profit_loss": 0.0, "bankroll_after": round(starting_bankroll, 2),
    }]

    for i, pick in enumerate(deduped):
        stake    = _PORTFOLIO_WEIGHTS.get(pick.get("_bucket", ""), 0.10)
        eff_odd  = _effective_odd(pick)
        pl       = round(_pl_per_unit(pick) * stake, 6)
        bankroll = round(bankroll + pl, 6)
        pl_series.append(pl)

        if bankroll > peak:
            peak = bankroll
        if bankroll < lowest:
            lowest = bankroll

        dd_u = round(peak - bankroll, 6)
        dd_p = (dd_u / peak * 100.0) if peak > 0 else 0.0
        if dd_u > max_dd_u:
            max_dd_u = dd_u
        if dd_p > max_dd_p:
            max_dd_p = dd_p

        if pick.get("result") == "WON":
            cur_win += 1; cur_loss = 0; wins += 1
            total_win_profit += max(pl, 0.0)
        else:
            cur_loss += 1; cur_win = 0; losses += 1
            total_loss_abs += abs(min(pl, 0.0))

        max_win  = max(max_win,  cur_win)
        max_loss = max(max_loss, cur_loss)

        home = pick.get("home_team", "")
        away = pick.get("away_team", "")
        date_str = (pick.get("date") or "")

        equity_curve.append({
            "index":          i + 1,
            "settled_at":     date_str[:19] if date_str else "",
            "fixture_id":     pick.get("fixture_id", ""),
            "match":          f"{home} vs {away}" if home or away else "",
            "market":         pick.get("market", ""),
            "result":         pick.get("result", ""),
            "odd":            round(eff_odd, 3),
            "stake":          stake,
            "profit_loss":    round(pl, 4),
            "bankroll_after": round(bankroll, 2),
        })

    total_bets = len(deduped)
    profit     = round(bankroll - starting_bankroll, 4)
    avg_stake  = (sum(_PORTFOLIO_WEIGHTS.get(p.get("_bucket", ""), 0.10) for p in deduped) / total_bets
                  if total_bets else 1.0)
    roi        = round(profit / (total_bets * avg_stake) * 100.0, 2) if total_bets else 0.0
    pf         = round(total_win_profit / total_loss_abs, 3) if total_loss_abs > 0 else (
        999.0 if total_win_profit > 0 else 0.0
    )

    return {
        "name":                  "PORTFOLIO_BALANCED_V1",
        "weights":               _PORTFOLIO_WEIGHTS,
        "portfolio_total_bets":  total_bets,
        "portfolio_settled":     total_bets,
        "portfolio_wins":        wins,
        "portfolio_losses":      losses,
        "portfolio_profit":      round(profit, 2),
        "portfolio_roi":         roi,
        "final_bankroll":        round(bankroll, 2),
        "peak_bankroll":         round(peak, 2),
        "lowest_bankroll":       round(lowest, 2),
        "max_drawdown":          round(max_dd_u, 2),
        "max_drawdown_percent":  round(max_dd_p, 1),
        "longest_losing_streak": max_loss,
        "profit_factor":         pf,
        "volatility_score":      _volatility(pl_series),
        "equity_curve":          equity_curve,
    }


# ─── Public entry point ──────────────────────────────────────────────────────

def build_bankroll_simulation(
    rows: List[Dict],
    shadow_predictions: List[Dict],
    starting_bankroll: float = 100.0,
    stake: float = 1.0,
) -> Dict:
    """
    Build the full bankroll simulation ready for the /api/shadow-lab response.

    Returns:
        {
            "settings": {...},
            "strategies": [ {strategy, metrics...}, ... ],   # 6 individual strategies
            "comparison": { best_final_bankroll, ... },
            "portfolios": [ PORTFOLIO_BALANCED_V1 ]
        }
    """
    strategy_picks: Dict[str, List[Dict]] = {
        "BETIQ_LIVE_SAFE":         _picks_betiq_live_safe(rows),
        "SHADOW_TEAM_GOALS":       _picks_shadow_strategy(shadow_predictions, "SHADOW_TEAM_GOALS"),
        "TEAM_GOALS_CONSERVATIVE": _picks_shadow_strategy(shadow_predictions, "TEAM_GOALS_CONSERVATIVE"),
        "SHADOW_BTTS":             _picks_shadow_strategy(shadow_predictions, "SHADOW_BTTS"),
        "NO_EXTREME_UNDERS":       _picks_no_extreme_unders(rows),
        "SHADOW_MARKET_V1":        _picks_shadow_market_v1(rows),
    }

    strategies: List[Dict] = []
    for name, picks in strategy_picks.items():
        strategies.append(_calc_metrics(name, picks, starting_bankroll, stake))

    portfolio = _simulate_portfolio_balanced_v1(strategy_picks, starting_bankroll)

    # ── Comparison summary ───────────────────────────────────────────────────
    settled_strategies = [s for s in strategies if s["settled_picks"] > 0]

    if settled_strategies:
        best_fb   = max(settled_strategies, key=lambda s: s["final_bankroll"])
        low_dd    = min(settled_strategies, key=lambda s: s["max_drawdown_units"])
        best_pf   = max(settled_strategies, key=lambda s: s["profit_factor"])
        most_stbl = min(settled_strategies, key=lambda s: s["volatility_score"])
        comparison = {
            "best_final_bankroll":  {"strategy": best_fb["strategy"],  "value": best_fb["final_bankroll"]},
            "lowest_drawdown":      {"strategy": low_dd["strategy"],   "value": low_dd["max_drawdown_units"]},
            "best_profit_factor":   {"strategy": best_pf["strategy"],  "value": best_pf["profit_factor"]},
            "most_stable_strategy": {"strategy": most_stbl["strategy"],"value": most_stbl["volatility_score"]},
        }
    else:
        comparison = {
            "best_final_bankroll":  None,
            "lowest_drawdown":      None,
            "best_profit_factor":   None,
            "most_stable_strategy": None,
        }

    return {
        "settings": {
            "starting_bankroll": starting_bankroll,
            "staking_model":     "FLAT",
            "flat_stake":        stake,
        },
        "strategies":  strategies,
        "comparison":  comparison,
        "portfolios":  [portfolio],
    }
