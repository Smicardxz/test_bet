"""
audit_tier_inversion.py
=======================
Compares assigned tier vs observed reality.

Expected order: S > A > B > WATCHLIST > NO_VALUE
Actual order: from POST_RESET data

Computes inversion score.

Usage:
  python audit_tier_inversion.py
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
    print(f"{BOLD}  TIER INVERSION ANALYSIS{RESET}")
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
                "volatility_score, false_signal_score, status, "
                "bookmaker_odd, market_probability, ev_percentage, "
                "created_at"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Parse and compute tier performance ─────────────────────────────────────
    tier_data: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        status = r.get("status", "")
        if status == "VOID":
            continue
        is_win = status == "WON"
        bookmaker_odd = r.get("bookmaker_odd")

        try:
            bookmaker_odd = float(bookmaker_odd) if bookmaker_odd else None
        except (TypeError, ValueError):
            bookmaker_odd = None

        tier_data[tier].append({
            "is_win": is_win,
            "bookmaker_odd": bookmaker_odd,
            "confidence": r.get("confidence_score"),
            "volatility": r.get("volatility_score"),
            "false_signal": r.get("false_signal_score"),
        })

    # ── Compute accuracy and ROI by tier ───────────────────────────────────────
    tier_metrics = {}
    for tier in tier_data.keys():
        rows = tier_data[tier]
        total = len(rows)
        wins = sum(1 for r in rows if r["is_win"])
        accuracy = wins / total if total > 0 else 0

        with_odd = [r for r in rows if r["bookmaker_odd"]]
        if with_odd:
            pl = sum((1 if r["is_win"] else -1) * r["bookmaker_odd"] for r in with_odd)
            roi = pl / len(with_odd) * 100
        else:
            pl = 0
            roi = 0

        tier_metrics[tier] = {
            "total": total,
            "wins": wins,
            "accuracy": accuracy,
            "roi": roi,
        }

    # ── Expected vs Actual order ───────────────────────────────────────────────
    print(f"\n{BOLD}── Expected vs Actual Tier Order{RESET}")
    print(f"\n  Expected order (by design):")
    print(f"    S_TIER > A_TIER > B_TIER > WATCHLIST > NO_VALUE")

    print(f"\n  Actual order (by accuracy):")
    sorted_by_acc = sorted(tier_metrics.items(), key=lambda x: x[1]["accuracy"], reverse=True)
    for i, (tier, m) in enumerate(sorted_by_acc):
        print(f"    {i+1}. {tier:<12} {m['accuracy']*100:>5.1f}%")

    print(f"\n  Actual order (by ROI):")
    sorted_by_roi = sorted(tier_metrics.items(), key=lambda x: x[1]["roi"], reverse=True)
    for i, (tier, m) in enumerate(sorted_by_roi):
        print(f"    {i+1}. {tier:<12} {m['roi']:>6.1f}%")

    # ── Compute inversion score ─────────────────────────────────────────────────
    expected_order = ["S_TIER", "A_TIER", "B_TIER", "WATCHLIST", "NO_VALUE"]
    actual_acc_order = [t for t, _ in sorted_by_acc]
    actual_roi_order = [t for t, _ in sorted_by_roi]

    def _inversion_score(expected, actual):
        """Count inversions where lower tier ranks higher than higher tier."""
        score = 0
        max_possible = 0
        for i, tier_a in enumerate(expected):
            for j, tier_b in enumerate(expected):
                if i < j:  # tier_a should be higher than tier_b
                    max_possible += 1
                    if tier_a in actual and tier_b in actual:
                        if actual.index(tier_a) > actual.index(tier_b):
                            score += 1
        return score, max_possible

    acc_inv, acc_max = _inversion_score(expected_order, actual_acc_order)
    roi_inv, roi_max = _inversion_score(expected_order, actual_roi_order)

    print(f"\n{BOLD}── Inversion Score{RESET}")
    print(f"  Accuracy inversions: {acc_inv}/{acc_max} ({acc_inv/acc_max*100:.1f}%)")
    print(f"  ROI inversions:      {roi_inv}/{roi_max} ({roi_inv/roi_max*100:.1f}%)")

    # ── Specific inversions ────────────────────────────────────────────────────
    print(f"\n{BOLD}── Specific Tier Inversions{RESET}")
    inversions = []
    for i, tier_a in enumerate(expected_order):
        for j, tier_b in enumerate(expected_order):
            if i < j:
                if tier_a in actual_acc_order and tier_b in actual_acc_order:
                    if actual_acc_order.index(tier_a) > actual_acc_order.index(tier_b):
                        inversions.append(f"{tier_a} < {tier_b} (accuracy)")
                if tier_a in actual_roi_order and tier_b in actual_roi_order:
                    if actual_roi_order.index(tier_a) > actual_roi_order.index(tier_b):
                        inversions.append(f"{tier_a} < {tier_b} (ROI)")

    if inversions:
        for inv in inversions:
            _warn(inv)
    else:
        _ok("No inversions detected")

    # ── Toxic tier patterns ────────────────────────────────────────────────────
    print(f"\n{BOLD}── Toxic Tier Patterns{RESET}")

    # Check if S_TIER is worse than B_TIER
    if "S_TIER" in tier_metrics and "B_TIER" in tier_metrics:
        s_acc = tier_metrics["S_TIER"]["accuracy"]
        b_acc = tier_metrics["B_TIER"]["accuracy"]
        if s_acc < b_acc:
            _err(f"S_TIER accuracy ({s_acc*100:.1f}%) < B_TIER accuracy ({b_acc*100:.1f}%)")
        else:
            _ok(f"S_TIER accuracy ({s_acc*100:.1f}%) >= B_TIER accuracy ({b_acc*100:.1f}%)")

    # Check if A_TIER is worse than WATCHLIST
    if "A_TIER" in tier_metrics and "WATCHLIST" in tier_metrics:
        a_acc = tier_metrics["A_TIER"]["accuracy"]
        w_acc = tier_metrics["WATCHLIST"]["accuracy"]
        if a_acc < w_acc:
            _err(f"A_TIER accuracy ({a_acc*100:.1f}%) < WATCHLIST accuracy ({w_acc*100:.1f}%)")
        else:
            _ok(f"A_TIER accuracy ({a_acc*100:.1f}%) >= WATCHLIST accuracy ({w_acc*100:.1f}%)")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    total_inv = acc_inv + roi_inv
    total_max = acc_max + roi_max
    inv_pct = total_inv / total_max * 100 if total_max > 0 else 0

    if inv_pct > 50:
        print(f"{BOLD}{RED}  TIERING_SEVERELY_INVERTED{RESET}")
        _err(f"Inversion rate: {inv_pct:.1f}%")
    elif inv_pct > 25:
        print(f"{BOLD}{YELLOW}  TIERING_PARTIALLY_INVERTED{RESET}")
        _warn(f"Inversion rate: {inv_pct:.1f}%")
    else:
        print(f"{BOLD}{GREEN}  TIERING_ORDER_CORRECT{RESET}")
        _ok(f"Inversion rate: {inv_pct:.1f}%")

    print()


if __name__ == "__main__":
    main()
