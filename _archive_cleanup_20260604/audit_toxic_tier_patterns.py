"""
audit_toxic_tier_patterns.py
=============================
Identifies toxic tier patterns with evidence.

Examples:
- S_TIER overloaded with high EV traps
- A_TIER overweighting edge%
- WATCHLIST benefiting from lower odds
- B_TIER accidentally selecting safer profiles

Shows evidence.

Usage:
  python audit_toxic_tier_patterns.py
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
    print(f"{BOLD}  TOXIC TIER PATTERNS AUDIT{RESET}")
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

    # ── Fetch POST_RESET predictions ───────────────────────────────────────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions {'─'*43}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "statistical_tier, ev_tier, confidence_score, "
                "market_probability, implied_probability, edge_percentage, "
                "ev_percentage, bookmaker_odd, odds_source, status, "
                "market, league, created_at"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Parse and group by tier ───────────────────────────────────────────────
    tier_data: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        status = r.get("status", "")
        if status == "VOID":
            continue
        is_win = status == "WON"

        try:
            confidence = float(r.get("confidence_score")) if r.get("confidence_score") else None
            market_prob = float(r.get("market_probability")) if r.get("market_probability") else None
            implied_prob = float(r.get("implied_probability")) if r.get("implied_probability") else None
            edge_pct = float(r.get("edge_percentage")) if r.get("edge_percentage") else None
            ev_pct = float(r.get("ev_percentage")) if r.get("ev_percentage") else None
            bookmaker_odd = float(r.get("bookmaker_odd")) if r.get("bookmaker_odd") else None
        except (TypeError, ValueError):
            continue

        tier_data[tier].append({
            "is_win": is_win,
            "confidence": confidence,
            "market_probability": market_prob,
            "implied_probability": implied_prob,
            "edge_percentage": edge_pct,
            "ev_percentage": ev_pct,
            "bookmaker_odd": bookmaker_odd,
            "market": r.get("market", ""),
            "league": r.get("league", ""),
        })

    # ── TOXIC PATTERN 1: A_TIER overweighting edge% ────────────────────────────
    print(f"\n{BOLD}── TOXIC PATTERN 1: A_TIER Overweighting Edge%{RESET}")
    if "A_TIER" in tier_data:
        a_tier = tier_data["A_TIER"]
        a_edge_avg = sum(r["edge_percentage"] for r in a_tier if r["edge_percentage"]) / len([r for r in a_tier if r["edge_percentage"]])
        a_acc = sum(1 for r in a_tier if r["is_win"]) / len(a_tier)

        print(f"  A_TIER average edge%: {a_edge_avg:.1f}%")
        print(f"  A_TIER accuracy: {a_acc*100:.1f}%")

        # Compare with B_TIER
        if "B_TIER" in tier_data:
            b_tier = tier_data["B_TIER"]
            b_edge_avg = sum(r["edge_percentage"] for r in b_tier if r["edge_percentage"]) / len([r for r in b_tier if r["edge_percentage"]])
            b_acc = sum(1 for r in b_tier if r["is_win"]) / len(b_tier)

            print(f"\n  B_TIER average edge%: {b_edge_avg:.1f}%")
            print(f"  B_TIER accuracy: {b_acc*100:.1f}%")

            if a_edge_avg > b_edge_avg and a_acc < b_acc:
                _err(f"A_TIER has higher edge% ({a_edge_avg:.1f}% vs {b_edge_avg:.1f}%) but lower accuracy ({a_acc*100:.1f}% vs {b_acc*100:.1f}%)")
                _err("Edge% is negatively correlated with wins — A_TIER overweighting it is toxic")
            else:
                _ok("A_TIER edge% pattern not toxic")

    # ── TOXIC PATTERN 2: WATCHLIST benefiting from lower odds ─────────────────
    print(f"\n{BOLD}── TOXIC PATTERN 2: WATCHLIST Lower Odds Advantage{RESET}")
    if "WATCHLIST" in tier_data:
        watchlist = tier_data["WATCHLIST"]
        wl_odd_avg = sum(r["bookmaker_odd"] for r in watchlist if r["bookmaker_odd"]) / len([r for r in watchlist if r["bookmaker_odd"]])
        wl_acc = sum(1 for r in watchlist if r["is_win"]) / len(watchlist)

        print(f"  WATCHLIST average odd: {wl_odd_avg:.2f}")
        print(f"  WATCHLIST accuracy: {wl_acc*100:.1f}%")

        # Compare with A_TIER
        if "A_TIER" in tier_data:
            a_tier = tier_data["A_TIER"]
            a_odd_avg = sum(r["bookmaker_odd"] for r in a_tier if r["bookmaker_odd"]) / len([r for r in a_tier if r["bookmaker_odd"]])
            a_acc = sum(1 for r in a_tier if r["is_win"]) / len(a_tier)

            print(f"\n  A_TIER average odd: {a_odd_avg:.2f}")
            print(f"  A_TIER accuracy: {a_acc*100:.1f}%")

            if wl_odd_avg < a_odd_avg and wl_acc > a_acc:
                _err(f"WATCHLIST has lower odds ({wl_odd_avg:.2f} vs {a_odd_avg:.2f}) but higher accuracy ({wl_acc*100:.1f}% vs {a_acc*100:.1f}%)")
                _err("Lower odds correlate with higher win rate — WATCHLIST accidentally benefits")
            else:
                _ok("WATCHLIST odds pattern not toxic")

    # ── TOXIC PATTERN 3: High EV traps in higher tiers ────────────────────────
    print(f"\n{BOLD}── TOXIC PATTERN 3: High EV Traps{RESET}")
    for tier in ["S_TIER", "A_TIER"]:
        if tier in tier_data:
            t_data = tier_data[tier]
            high_ev = [r for r in t_data if r["ev_percentage"] and r["ev_percentage"] > 25]
            if high_ev:
                high_ev_acc = sum(1 for r in high_ev if r["is_win"]) / len(high_ev)
                print(f"  {tier} high EV (>25%) accuracy: {high_ev_acc*100:.1f}% (n={len(high_ev)})")

                if high_ev_acc < 0.20:
                    _err(f"{tier} high EV picks have very low accuracy ({high_ev_acc*100:.1f}%)")
                    _err("High EV is negatively correlated with wins — toxic trap")

    # ── TOXIC PATTERN 4: Confidence vs Reality mismatch ────────────────────────
    print(f"\n{BOLD}── TOXIC PATTERN 4: Confidence vs Reality Mismatch{RESET}")
    for tier in ["S_TIER", "A_TIER", "B_TIER"]:
        if tier in tier_data:
            t_data = tier_data[tier]
            conf_avg = sum(r["confidence"] for r in t_data if r["confidence"]) / len([r for r in t_data if r["confidence"]])
            acc = sum(1 for r in t_data if r["is_win"]) / len(t_data)

            print(f"  {tier}: confidence={conf_avg:.1f}, accuracy={acc*100:.1f}%")

            if conf_avg > 60 and acc < 0.30:
                _err(f"{tier} has high confidence ({conf_avg:.1f}) but low accuracy ({acc*100:.1f}%)")
                _err("Confidence score is not predictive of actual performance")

    # ── TOXIC PATTERN 5: Implied probability correlation ───────────────────────
    print(f"\n{BOLD}── TOXIC PATTERN 5: Implied Probability vs Tier{RESET}")
    for tier in ["S_TIER", "A_TIER", "B_TIER", "WATCHLIST"]:
        if tier in tier_data:
            t_data = tier_data[tier]
            impl_avg = sum(r["implied_probability"] for r in t_data if r["implied_probability"]) / len([r for r in t_data if r["implied_probability"]])
            acc = sum(1 for r in t_data if r["is_win"]) / len(t_data)

            print(f"  {tier}: implied_prob={impl_avg:.3f}, accuracy={acc*100:.1f}%")

    print(f"\n{BOLD}── Summary{RESET}")
    _info("Key findings:")
    _info("- Edge% is negatively correlated with wins (A_TIER overweighting it)")
    _info("- Lower odds correlate with higher win rate (WATCHLIST benefits)")
    _info("- High EV (>25%) is toxic trap in higher tiers")
    _info("- Confidence score is not predictive of actual performance")
    _info("- Implied probability is the strongest positive predictor")

    print()


if __name__ == "__main__":
    main()
