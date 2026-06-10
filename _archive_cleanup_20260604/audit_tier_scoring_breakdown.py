"""
audit_tier_scoring_breakdown.py
===============================
For every POST_RESET prediction, outputs tier scoring features:
- tier
- confidence
- market_probability
- implied_probability
- edge_percentage
- ev_percentage
- bookmaker_odd
- odds_source
- result

Computes averages by tier.

Usage:
  python audit_tier_scoring_breakdown.py
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
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


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  TIER SCORING BREAKDOWN AUDIT{RESET}")
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

    # ── Fetch POST_RESET predictions with scoring features ─────────────────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions with scoring features {'─'*22}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, statistical_tier, ev_tier, confidence_score, "
                "market_probability, implied_probability, edge_percentage, "
                "ev_percentage, bookmaker_odd, odds_source, status, "
                "false_signal_score, chaos_score, volatility_score, "
                "ranking_score, league_edge_rating, market_historical_profitability, "
                "created_at"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.limit(5000).execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Parse and group by tier ────────────────────────────────────────────────
    tier_data: Dict[str, List[dict]] = defaultdict(list)
    all_data = []

    for r in rows:
        tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        status = r.get("status", "")
        is_win = status == "WON"
        is_loss = status == "LOST"
        is_void = status == "VOID"

        confidence = r.get("confidence_score")
        market_prob = r.get("market_probability")
        implied_prob = r.get("implied_probability")
        edge_pct = r.get("edge_percentage")
        ev_pct = r.get("ev_percentage")
        bookmaker_odd = r.get("bookmaker_odd")
        odds_src = r.get("odds_source")
        false_signal = r.get("false_signal_score")
        chaos = r.get("chaos_score")
        volatility = r.get("volatility_score")
        ranking = r.get("ranking_score")
        lse_rating = r.get("league_edge_rating")
        mhp = r.get("market_historical_profitability")

        try:
            confidence = float(confidence) if confidence else None
            market_prob = float(market_prob) if market_prob else None
            implied_prob = float(implied_prob) if implied_prob else None
            edge_pct = float(edge_pct) if edge_pct else None
            ev_pct = float(ev_pct) if ev_pct else None
            bookmaker_odd = float(bookmaker_odd) if bookmaker_odd else None
            false_signal = float(false_signal) if false_signal else None
            chaos = float(chaos) if chaos else None
            volatility = float(volatility) if volatility else None
            ranking = float(ranking) if ranking else None
        except (TypeError, ValueError):
            continue

        row_data = {
            "tier": tier,
            "confidence": confidence,
            "market_probability": market_prob,
            "implied_probability": implied_prob,
            "edge_percentage": edge_pct,
            "ev_percentage": ev_pct,
            "bookmaker_odd": bookmaker_odd,
            "odds_source": odds_src,
            "status": status,
            "is_win": is_win,
            "is_loss": is_loss,
            "is_void": is_void,
            "false_signal_score": false_signal,
            "chaos_score": chaos,
            "volatility_score": volatility,
            "ranking_score": ranking,
            "league_edge_rating": lse_rating,
            "market_historical_profitability": mhp,
        }
        tier_data[tier].append(row_data)
        all_data.append(row_data)

    _info(f"Processed {len(all_data)} predictions")

    # ── Compute averages by tier ───────────────────────────────────────────────
    print(f"\n{BOLD}── Average Scoring Features by Tier {'─'*39}{RESET}")

    def _avg(values):
        if not values:
            return None
        return sum(v for v in values if v is not None) / len([v for v in values if v is not None])

    tier_stats = {}
    for tier in sorted(tier_data.keys()):
        rows = tier_data[tier]
        stats = {
            "count": len(rows),
            "wins": sum(1 for r in rows if r["is_win"]),
            "losses": sum(1 for r in rows if r["is_loss"]),
            "voids": sum(1 for r in rows if r["is_void"]),
            "accuracy": sum(1 for r in rows if r["is_win"]) / len(rows) if rows else 0,
            "confidence": _avg([r["confidence"] for r in rows]),
            "market_probability": _avg([r["market_probability"] for r in rows]),
            "implied_probability": _avg([r["implied_probability"] for r in rows]),
            "edge_percentage": _avg([r["edge_percentage"] for r in rows]),
            "ev_percentage": _avg([r["ev_percentage"] for r in rows]),
            "bookmaker_odd": _avg([r["bookmaker_odd"] for r in rows]),
            "false_signal_score": _avg([r["false_signal_score"] for r in rows]),
            "chaos_score": _avg([r["chaos_score"] for r in rows]),
            "volatility_score": _avg([r["volatility_score"] for r in rows]),
            "ranking_score": _avg([r["ranking_score"] for r in rows]),
        }
        tier_stats[tier] = stats

    # Print table
    print(f"  {'Tier':<12} {'Count':<6} {'Win%':<7} {'Conf':<7} {'MktProb':<8} {'ImplProb':<8} {'Edge%':<7} {'EV%':<7} {'Odd':<7}")
    print(f"  {'─'*12} {'─'*6} {'─'*7} {'─'*7} {'─'*8} {'─'*8} {'─'*7} {'─'*7} {'─'*7}")
    for tier in sorted(tier_stats.keys()):
        s = tier_stats[tier]
        print(f"  {tier:<12} {s['count']:<6} {s['accuracy']*100:>5.1f}%  "
              f"{s['confidence']:>5.2f}  {s['market_probability']:>6.3f}  "
              f"{s['implied_probability']:>6.3f}  {s['edge_percentage']:>5.1f}%  "
              f"{s['ev_percentage']:>5.1f}%  {s['bookmaker_odd']:>5.2f}")

    # ── Odds source distribution by tier ───────────────────────────────────────
    print(f"\n{BOLD}── Odds Source Distribution by Tier {'─'*40}{RESET}")
    for tier in sorted(tier_stats.keys()):
        rows = tier_data[tier]
        src_counts = defaultdict(int)
        for r in rows:
            src = r["odds_source"] or "NO_ODDS"
            src_counts[src] += 1
        print(f"\n  {tier}:")
        for src in sorted(src_counts.keys()):
            pct = src_counts[src] / len(rows) * 100 if rows else 0
            print(f"    {src:<20}: {src_counts[src]:>3} ({pct:>5.1f}%)")

    # ── Sample rows per tier ───────────────────────────────────────────────────
    print(f"\n{BOLD}── Sample Rows by Tier (first 3 each) {'─'*36}{RESET}")
    for tier in sorted(tier_stats.keys()):
        rows = tier_data[tier][:3]
        print(f"\n  {tier}:")
        print(f"    {'Conf':<6} {'MktProb':<8} {'ImplProb':<8} {'Edge%':<7} {'EV%':<7} {'Odd':<7} {'Result':<8}")
        print(f"    {'─'*6} {'─'*8} {'─'*8} {'─'*7} {'─'*7} {'─'*7} {'─'*8}")
        for r in rows:
            conf_str = f"{r['confidence']:.2f}" if r['confidence'] else "N/A"
            prob_str = f"{r['market_probability']:.3f}" if r['market_probability'] else "N/A"
            impl_str = f"{r['implied_probability']:.3f}" if r['implied_probability'] else "N/A"
            edge_str = f"{r['edge_percentage']:.1f}%" if r['edge_percentage'] else "N/A"
            ev_str = f"{r['ev_percentage']:.1f}%" if r['ev_percentage'] else "N/A"
            odd_str = f"{r['bookmaker_odd']:.2f}" if r['bookmaker_odd'] else "N/A"
            print(f"    {conf_str:>5}  {prob_str:>6}  {impl_str:>6}  {edge_str:>5}  "
                  f"{ev_str:>5}  {odd_str:>5}  {r['status']:<8}")

    print()


if __name__ == "__main__":
    main()
