"""
audit_toxic_patterns.py
========================
Identify toxic patterns in settled predictions (POST_RESET only).

Groups by:
- tier
- market
- league
- odds_bucket
- ev_bucket
- market_probability_bucket

Outputs accuracy, ROI, count, avg_odd, avg_ev for each group.

Buckets:
  odds: 1.1-1.5, 1.5-2.0, 2.0-3.0, 3.0-5.0, 5.0+
  EV: 0-5, 5-10, 10-20, 20-40, 40+
  Market probability: 0.15-0.35, 0.35-0.50, 0.50-0.65, 0.65-0.80, 0.80+

Identifies:
- toxic markets
- toxic odds ranges
- toxic EV ranges
- toxic leagues
- tiers that should be disabled

Usage:
  python audit_toxic_patterns.py
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def _parse_reset_at() -> str:
    """Return TRACKING_RESET_AT exactly as set in env (full ISO datetime or date), or ''."""
    raw = os.environ.get("TRACKING_RESET_AT", "").strip()
    if not raw:
        return ""
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))  # validate
        else:
            from datetime import date as _date
            _date.fromisoformat(raw[:10])  # validate
        return raw
    except Exception:
        return ""


def _apply_since_filter(query, since_date: str):
    """Apply date/datetime filter to a Supabase query builder."""
    if not since_date:
        return query
    if "T" in since_date:
        return query.gte("created_at", since_date)
    return query.gte("prediction_date", since_date)


def _odds_bucket(odd: float) -> str:
    if odd < 1.5:
        return "1.1-1.5"
    elif odd < 2.0:
        return "1.5-2.0"
    elif odd < 3.0:
        return "2.0-3.0"
    elif odd < 5.0:
        return "3.0-5.0"
    else:
        return "5.0+"


def _ev_bucket(ev: float) -> str:
    if ev < 5:
        return "0-5"
    elif ev < 10:
        return "5-10"
    elif ev < 20:
        return "10-20"
    elif ev < 40:
        return "20-40"
    else:
        return "40+"


def _prob_bucket(prob: float) -> str:
    if prob < 0.35:
        return "0.15-0.35"
    elif prob < 0.50:
        return "0.35-0.50"
    elif prob < 0.65:
        return "0.50-0.65"
    elif prob < 0.80:
        return "0.65-0.80"
    else:
        return "0.80+"


def _compute_group_stats(rows: List[dict]) -> dict:
    """Compute accuracy, ROI, count, avg_odd, avg_ev for a group."""
    if not rows:
        return {"count": 0, "wins": 0, "accuracy": 0, "roi": 0, "avg_odd": 0, "avg_ev": 0}

    total = len(rows)
    wins = sum(1 for r in rows if r["is_win"])
    accuracy = wins / total if total > 0 else 0

    with_odd = [r for r in rows if r["bookmaker_odd"]]
    if with_odd:
        pl = sum((1 if r["is_win"] else -1) * r["bookmaker_odd"] for r in with_odd)
        roi = pl / len(with_odd) * 100
        avg_odd = sum(r["bookmaker_odd"] for r in with_odd) / len(with_odd)
    else:
        pl = 0
        roi = 0
        avg_odd = 0

    avg_ev = sum(r["ev_percentage"] for r in rows) / total

    return {
        "count": total,
        "wins": wins,
        "accuracy": accuracy,
        "roi": roi,
        "avg_odd": avg_odd,
        "avg_ev": avg_ev,
    }


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  TOXIC PATTERNS AUDIT{RESET}")
    print(f"{'═'*66}")

    reset_at = _parse_reset_at()
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — using all predictions")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch settled predictions ───────────────────────────────────────────────
    print(f"\n{BOLD}── Fetching settled predictions (POST_RESET) {'─'*30}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, fixture_id, home_team, away_team, market, league, "
                "statistical_tier, ev_tier, bookmaker_odd, market_probability, implied_probability, "
                "ev_percentage, edge_percentage, status, prediction_date, created_at"
            )
            .in_("status", ["WON", "LOST", "VOID"])
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.limit(5000).execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} settled predictions")

    # ── Parse and bucket ─────────────────────────────────────────────────────────
    tier_groups: Dict[str, List[dict]] = defaultdict(list)
    market_groups: Dict[str, List[dict]] = defaultdict(list)
    league_groups: Dict[str, List[dict]] = defaultdict(list)
    odds_groups: Dict[str, List[dict]] = defaultdict(list)
    ev_groups: Dict[str, List[dict]] = defaultdict(list)
    prob_groups: Dict[str, List[dict]] = defaultdict(list)

    for r in rows:
        tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        status = r.get("status", "")
        if status == "VOID":
            continue
        is_win = status == "WON"
        bookmaker_odd = r.get("bookmaker_odd")
        market_prob = r.get("market_probability")
        implied_prob = r.get("implied_probability")
        ev_pct = r.get("ev_percentage") or r.get("ev_percent") or 0
        market = r.get("market", "")
        league = r.get("league", "")

        try:
            bookmaker_odd = float(bookmaker_odd) if bookmaker_odd else None
            market_prob = float(market_prob) if market_prob else None
            implied_prob = float(implied_prob) if implied_prob else None
            ev_pct = float(ev_pct)
        except (TypeError, ValueError):
            continue

        row_data = {
            "tier": tier,
            "market": market,
            "league": league,
            "bookmaker_odd": bookmaker_odd,
            "market_probability": market_prob,
            "implied_probability": implied_prob,
            "ev_percentage": ev_pct,
            "is_win": is_win,
            "status": status,
        }

        tier_groups[tier].append(row_data)
        market_groups[market].append(row_data)
        league_groups[league].append(row_data)

        if bookmaker_odd:
            odds_groups[_odds_bucket(bookmaker_odd)].append(row_data)
        if market_prob:
            prob_groups[_prob_bucket(market_prob)].append(row_data)
        ev_groups[_ev_bucket(ev_pct)].append(row_data)

    _info(f"Processed {len(tier_groups)} tiers, {len(market_groups)} markets, {len(league_groups)} leagues")

    # ── Toxic Tier Analysis ─────────────────────────────────────────────────────
    print(f"\n{BOLD}── Toxic Tier Analysis {'─'*48}{RESET}")
    print(f"  {'Tier':<12} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10} {'AvgOdd':<10} {'AvgEV':<10}")
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    toxic_tiers = []
    for tier in sorted(tier_groups.keys()):
        stats = _compute_group_stats(tier_groups[tier])
        print(f"  {tier:<12} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%  {stats['avg_odd']:>8.3f}  {stats['avg_ev']:>8.2f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_tiers.append(tier)

    if toxic_tiers:
        _warn(f"Toxic tiers (accuracy < 30% or ROI < -50%): {', '.join(toxic_tiers)}")

    # ── Toxic Market Analysis ───────────────────────────────────────────────────
    print(f"\n{BOLD}── Toxic Market Analysis {'─'*47}{RESET}")
    print(f"  {'Market':<25} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10}")
    print(f"  {'─'*25} {'─'*6} {'─'*6} {'─'*10} {'─'*10}")
    toxic_markets = []
    for market in sorted(market_groups.keys()):
        stats = _compute_group_stats(market_groups[market])
        if stats["count"] < 3:
            continue
        print(f"  {market[:25]:<25} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_markets.append(market)

    if toxic_markets:
        _warn(f"Toxic markets: {', '.join(toxic_markets)}")

    # ── Toxic Odds Range Analysis ───────────────────────────────────────────────
    print(f"\n{BOLD}── Toxic Odds Range Analysis {'─'*44}{RESET}")
    print(f"  {'Odds Bucket':<12} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10}")
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*10} {'─'*10}")
    toxic_odds = []
    for bucket in sorted(odds_groups.keys()):
        stats = _compute_group_stats(odds_groups[bucket])
        print(f"  {bucket:<12} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_odds.append(bucket)

    if toxic_odds:
        _warn(f"Toxic odds ranges: {', '.join(toxic_odds)}")

    # ── Toxic EV Range Analysis ─────────────────────────────────────────────────
    print(f"\n{BOLD}── Toxic EV Range Analysis {'─'*48}{RESET}")
    print(f"  {'EV Bucket':<12} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10}")
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*10} {'─'*10}")
    toxic_ev = []
    for bucket in sorted(ev_groups.keys()):
        stats = _compute_group_stats(ev_groups[bucket])
        print(f"  {bucket:<12} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_ev.append(bucket)

    if toxic_ev:
        _warn(f"Toxic EV ranges: {', '.join(toxic_ev)}")

    # ── Toxic Market Probability Analysis ───────────────────────────────────────
    print(f"\n{BOLD}── Toxic Market Probability Analysis {'─'*38}{RESET}")
    print(f"  {'Prob Bucket':<12} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10}")
    print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*10} {'─'*10}")
    toxic_prob = []
    for bucket in sorted(prob_groups.keys()):
        stats = _compute_group_stats(prob_groups[bucket])
        print(f"  {bucket:<12} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_prob.append(bucket)

    if toxic_prob:
        _warn(f"Toxic probability ranges: {', '.join(toxic_prob)}")

    # ── Toxic League Analysis (top 20 by count) ─────────────────────────────────
    print(f"\n{BOLD}── Toxic League Analysis (top 20 by count) {'─'*33}{RESET}")
    print(f"  {'League':<30} {'Count':<6} {'Wins':<6} {'Accuracy':<10} {'ROI':<10}")
    print(f"  {'─'*30} {'─'*6} {'─'*6} {'─'*10} {'─'*10}")
    toxic_leagues = []
    sorted_leagues = sorted(league_groups.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    for league, rows in sorted_leagues:
        stats = _compute_group_stats(rows)
        print(f"  {league[:30]:<30} {stats['count']:<6} {stats['wins']:<6} {stats['accuracy']*100:>8.1f}%  "
              f"{stats['roi']:>8.1f}%")
        if stats["accuracy"] < 0.30 or stats["roi"] < -50:
            toxic_leagues.append(league)

    if toxic_leagues:
        _warn(f"Toxic leagues: {', '.join(toxic_leagues)}")

    # ── Summary ─────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  TOXIC PATTERN SUMMARY{RESET}")
    print(f"{'═'*66}")
    if toxic_tiers:
        _err(f"Disable tiers: {', '.join(toxic_tiers)}")
    if toxic_markets:
        _err(f"Disable markets: {', '.join(toxic_markets)}")
    if toxic_odds:
        _err(f"Avoid odds ranges: {', '.join(toxic_odds)}")
    if toxic_ev:
        _err(f"Avoid EV ranges: {', '.join(toxic_ev)}")
    if toxic_prob:
        _err(f"Avoid probability ranges: {', '.join(toxic_prob)}")
    if toxic_leagues:
        _err(f"Avoid leagues: {', '.join(toxic_leagues)}")

    if not (toxic_tiers or toxic_markets or toxic_odds or toxic_ev or toxic_prob or toxic_leagues):
        _ok("No toxic patterns detected")
    print()


if __name__ == "__main__":
    main()
