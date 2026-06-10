"""
Bankroll Simulator — Phases 1 & 2
===================================
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


def _empty_metrics(starting_bankroll: float) -> Dict:
    return {
        "final_bankroll": starting_bankroll,
        "profit": 0.0,
        "roi": 0.0,
        "settled": 0,
        "wins": 0,
        "losses": 0,
        "hit_rate": 0.0,
        "max_drawdown_units": 0.0,
        "max_drawdown_percent": 0.0,
        "longest_losing_streak": 0,
        "longest_winning_streak": 0,
        "profit_factor": 0.0,
        "avg_odd": 0.0,
        "equity_curve": [{"pick": 0, "bankroll": starting_bankroll, "date": ""}],
    }


def _calc_metrics(
    settled_picks: List[Dict],
    starting_bankroll: float,
    stake: float,
) -> Dict:
    """Compute all simulation metrics for a sorted list of settled picks."""
    if not settled_picks:
        return _empty_metrics(starting_bankroll)

    bankroll = starting_bankroll
    peak = starting_bankroll
    max_dd_units = 0.0
    max_dd_pct = 0.0
    cur_loss = cur_win = 0
    max_loss = max_win = 0
    total_win_profit = 0.0
    total_loss_abs = 0.0
    odds_acc = 0.0

    equity_curve = [{"pick": 0, "bankroll": round(starting_bankroll, 2), "date": ""}]

    for i, pick in enumerate(settled_picks):
        pl = _pl_per_unit(pick) * stake
        bankroll = round(bankroll + pl, 6)

        if bankroll > peak:
            peak = bankroll
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

        odds_acc += _effective_odd(pick)
        equity_curve.append({
            "pick": i + 1,
            "bankroll": round(bankroll, 2),
            "date": (pick.get("date") or "")[:10],
        })

    wins_count = sum(1 for p in settled_picks if p.get("result") == "WON")
    losses_count = len(settled_picks) - wins_count
    profit = round(bankroll - starting_bankroll, 4)
    total_staked = len(settled_picks) * stake
    roi = round(profit / total_staked * 100.0, 2) if total_staked else 0.0
    hit_rate = round(wins_count / len(settled_picks) * 100.0, 1)
    pf = round(total_win_profit / total_loss_abs, 3) if total_loss_abs > 0 else (
        999.0 if total_win_profit > 0 else 0.0
    )
    avg_odd = round(odds_acc / len(settled_picks), 3)

    return {
        "final_bankroll": round(bankroll, 2),
        "profit": round(profit, 2),
        "roi": roi,
        "settled": len(settled_picks),
        "wins": wins_count,
        "losses": losses_count,
        "hit_rate": hit_rate,
        "max_drawdown_units": round(max_dd_units, 2),
        "max_drawdown_percent": round(max_dd_pct, 1),
        "longest_losing_streak": max_loss,
        "longest_winning_streak": max_win,
        "profit_factor": pf,
        "avg_odd": avg_odd,
        "equity_curve": equity_curve,
    }


# ─── Normalisation ───────────────────────────────────────────────────────────

def _norm_shadow(sp: Dict) -> Optional[Dict]:
    """Normalise a shadow_prediction entry to a pick dict."""
    result = sp.get("simulated_result")
    if result not in ("WON", "LOST"):
        return None
    market = sp.get("market", "")
    return {
        "result": result,
        "odd": sp.get("bookmaker_odd") or _SHADOW_IMPLIED_ODD.get(market, 1.8),
        "market": market,
        "fixture_id": str(sp.get("fixture_id", "")),
        "date": sp.get("kickoff_time") or sp.get("created_at") or "",
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
        "result": result,
        "odd": float(odd),
        "market": row.get("market", ""),
        "fixture_id": str(row.get("fixture_id", "")),
        "date": row.get("kickoff_time") or row.get("created_at") or "",
    }


def _sorted(picks: List[Dict]) -> List[Dict]:
    return sorted(picks, key=lambda x: x.get("date") or "")


# ─── Strategy extractors ─────────────────────────────────────────────────────

def _picks_betiq_live_safe(rows: List[Dict]) -> List[Dict]:
    return _sorted([
        p for p in (_norm_real(r) for r in rows if r.get("selection_mode") in ("LIVE_SAFE", "LIVE"))
        if p
    ])


def _picks_no_extreme_unders(rows: List[Dict]) -> List[Dict]:
    result = []
    for r in rows:
        market = r.get("market", "")
        odd = float(r.get("bookmaker_odd") or 0.0)
        is_under_extreme = (
            ("_UNDER_" in market or market.startswith("UNDER")) and odd > 4.0
        )
        if market not in ("FT_UNDER_1_5", "HT_UNDER_0_5") and not is_under_extreme:
            p = _norm_real(r)
            if p:
                result.append(p)
    return _sorted(result)


def _picks_shadow_market_v1(rows: List[Dict]) -> List[Dict]:
    preferred = {"HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5"}
    excluded = {"FT_UNDER_1_5", "HT_UNDER_0_5"}
    result = []
    for r in rows:
        odd = float(r.get("bookmaker_odd") or 0.0)
        market = r.get("market", "")
        ev = r.get("ev_percentage") or 0
        if (
            REAL_ODDS_THRESHOLD <= odd <= 5.0
            and market not in excluded
            and float(ev) <= 35
            and market in preferred
        ):
            p = _norm_real(r)
            if p:
                result.append(p)
    return _sorted(result)


def _picks_shadow_strategy(shadow_predictions: List[Dict], strategy: str) -> List[Dict]:
    return _sorted([
        p for p in (_norm_shadow(sp) for sp in shadow_predictions if sp.get("strategy") == strategy)
        if p
    ])


# ─── Portfolio ───────────────────────────────────────────────────────────────

def _simulate_portfolio_balanced_v1(
    strategy_picks: Dict[str, List[Dict]],
    starting_bankroll: float,
) -> Dict:
    """Simulate PORTFOLIO_BALANCED_V1 with deduplication by fixture_id."""

    experimental = _sorted(
        strategy_picks.get("NO_EXTREME_UNDERS", []) +
        strategy_picks.get("SHADOW_MARKET_V1", [])
    )

    bucket_picks: Dict[str, List[Dict]] = {
        "TEAM_GOALS_CONSERVATIVE": strategy_picks.get("TEAM_GOALS_CONSERVATIVE", []),
        "SHADOW_TEAM_GOALS":       strategy_picks.get("SHADOW_TEAM_GOALS", []),
        "SHADOW_BTTS":             strategy_picks.get("SHADOW_BTTS", []),
        "EXPERIMENTAL":            experimental,
    }

    # Tag each pick with its portfolio bucket, then sort chronologically
    timeline: List[Dict] = []
    for bucket, picks in bucket_picks.items():
        for pick in picks:
            timeline.append({**pick, "_bucket": bucket})
    timeline.sort(key=lambda x: x.get("date") or "")

    # Deduplicate: one bet per fixture, highest-priority bucket wins
    seen: Dict[str, int] = {}      # fixture_id -> priority_index of accepted pick
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

    # Simulate
    bankroll  = starting_bankroll
    peak      = starting_bankroll
    max_dd_u  = 0.0
    max_dd_p  = 0.0
    cur_loss = cur_win = 0
    max_loss = max_win = 0
    wins = losses = 0
    total_win_profit = total_loss_abs = 0.0

    equity_curve = [{"pick": 0, "bankroll": round(starting_bankroll, 2), "date": ""}]

    for i, pick in enumerate(deduped):
        stake = _PORTFOLIO_WEIGHTS.get(pick.get("_bucket", ""), 0.10)
        pl    = _pl_per_unit(pick) * stake
        bankroll = round(bankroll + pl, 6)

        if bankroll > peak:
            peak = bankroll
        dd_u = round(peak - bankroll, 6)
        dd_p = (dd_u / peak * 100.0) if peak > 0 else 0.0
        if dd_u > max_dd_u:
            max_dd_u = dd_u
        if dd_p > max_dd_p:
            max_dd_p = dd_p

        if pick.get("result") == "WON":
            cur_win += 1
            cur_loss = 0
            wins += 1
            total_win_profit += max(pl, 0.0)
        else:
            cur_loss += 1
            cur_win = 0
            losses += 1
            total_loss_abs += abs(min(pl, 0.0))

        if cur_win > max_win:
            max_win = cur_win
        if cur_loss > max_loss:
            max_loss = cur_loss

        equity_curve.append({
            "pick": i + 1,
            "bankroll": round(bankroll, 2),
            "date": (pick.get("date") or "")[:10],
        })

    total_bets = len(deduped)
    profit     = round(bankroll - starting_bankroll, 4)
    avg_stake  = sum(_PORTFOLIO_WEIGHTS.get(p.get("_bucket", ""), 0.10) for p in deduped) / total_bets if total_bets else 1.0
    roi        = round(profit / (total_bets * avg_stake) * 100.0, 2) if total_bets else 0.0
    pf         = round(total_win_profit / total_loss_abs, 3) if total_loss_abs > 0 else (
        999.0 if total_win_profit > 0 else 0.0
    )

    return {
        "name": "PORTFOLIO_BALANCED_V1",
        "weights": _PORTFOLIO_WEIGHTS,
        "portfolio_total_bets": total_bets,
        "portfolio_settled":    total_bets,
        "portfolio_wins":       wins,
        "portfolio_losses":     losses,
        "portfolio_profit":     round(profit, 2),
        "portfolio_roi":        roi,
        "final_bankroll":       round(bankroll, 2),
        "max_drawdown":         round(max_dd_u, 2),
        "max_drawdown_percent": round(max_dd_p, 1),
        "longest_losing_streak": max_loss,
        "profit_factor":        pf,
        "equity_curve":         equity_curve,
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

    Args:
        rows               : Supabase prediction rows (from shadow-lab endpoint)
        shadow_predictions : Virtual shadow picks (already generated in shadow-lab)
        starting_bankroll  : Initial bankroll in units (default 100u)
        stake              : Flat stake per pick in units (default 1u)

    Returns:
        {
            "settings": {...},
            "individual_strategies": { STRATEGY: metrics, ... },
            "portfolios": [ PORTFOLIO_BALANCED_V1 ]
        }
    """
    strategy_picks: Dict[str, List[Dict]] = {
        "BETIQ_LIVE_SAFE":          _picks_betiq_live_safe(rows),
        "SHADOW_TEAM_GOALS":        _picks_shadow_strategy(shadow_predictions, "SHADOW_TEAM_GOALS"),
        "TEAM_GOALS_CONSERVATIVE":  _picks_shadow_strategy(shadow_predictions, "TEAM_GOALS_CONSERVATIVE"),
        "SHADOW_BTTS":              _picks_shadow_strategy(shadow_predictions, "SHADOW_BTTS"),
        "NO_EXTREME_UNDERS":        _picks_no_extreme_unders(rows),
        "SHADOW_MARKET_V1":         _picks_shadow_market_v1(rows),
    }

    individual: Dict[str, Dict] = {}
    for name, picks in strategy_picks.items():
        individual[name] = _calc_metrics(picks, starting_bankroll, stake)

    portfolio = _simulate_portfolio_balanced_v1(strategy_picks, starting_bankroll)

    return {
        "settings": {
            "starting_bankroll": starting_bankroll,
            "staking_model":     "FLAT",
            "stake_per_pick":    stake,
        },
        "individual_strategies": individual,
        "portfolios":            [portfolio],
    }
