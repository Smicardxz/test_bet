"""
audit_safe_selection.py
========================
Validates SAFE_SELECTION_MODE implementation.

Shows:
- total POST_RESET predictions
- live_safe_count
- research_only_count
- excluded_by_tier
- excluded_by_odd
- excluded_by_ev
- excluded_by_market
- expected historical ROI if safe filter was applied retroactively

Expected:
SAFE_SELECTION_READY

Usage:
  python audit_safe_selection.py
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


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SAFE SELECTION AUDIT{RESET}")
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

    # ── Fetch all POST_RESET predictions ───────────────────────────────────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions {'─'*38}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, status, selection_mode, selection_reason, "
                "statistical_tier, ev_tier, bookmaker_odd, market_probability, "
                "implied_probability, ev_percentage, market, league, "
                "odds_source, profit_loss, created_at"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.limit(5000).execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Count by selection_mode ─────────────────────────────────────────────────
    mode_counts = defaultdict(int)
    reason_counts = defaultdict(int)
    for r in rows:
        mode = r.get("selection_mode") or "UNKNOWN"
        reason = r.get("selection_reason") or "UNKNOWN"
        mode_counts[mode] += 1
        reason_counts[reason] += 1

    print(f"\n{BOLD}── Selection Mode Distribution {'─'*41}{RESET}")
    print(f"  {'Mode':<15} {'Count':<10} {'%':<10}")
    print(f"  {'─'*15} {'─'*10} {'─'*10}")
    total = len(rows)
    for mode in sorted(mode_counts.keys()):
        pct = mode_counts[mode] / total * 100 if total > 0 else 0
        print(f"  {mode:<15} {mode_counts[mode]:<10} {pct:>8.1f}%")

    # ── Exclusion reasons ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── Exclusion Reasons (RESEARCH only) {'─'*36}{RESET}")
    print(f"  {'Reason':<30} {'Count':<10}")
    print(f"  {'─'*30} {'─'*10}")
    for reason in sorted(reason_counts.keys()):
        if reason not in ("PASSED_SAFE_MODE", "SAFE_MODE_DISABLED", "MIGRATED_PRE_SAFE_MODE", "UNKNOWN"):
            print(f"  {reason[:30]:<30} {reason_counts[reason]:<10}")

    # ── Breakdown by exclusion type ────────────────────────────────────────────
    excluded_by_tier = 0
    excluded_by_odd_low = 0
    excluded_by_odd_high = 0
    excluded_by_ev_low = 0
    excluded_by_ev_high = 0
    excluded_by_prob_low = 0
    excluded_by_prob_high = 0
    excluded_by_market = 0
    excluded_by_odds_source = 0

    for r in rows:
        reason = r.get("selection_reason") or ""
        if "RESEARCH_TOXIC_TIER" in reason:
            excluded_by_tier += 1
        if "RESEARCH_ODD_TOO_LOW" in reason:
            excluded_by_odd_low += 1
        if "RESEARCH_ODD_TOO_HIGH" in reason:
            excluded_by_odd_high += 1
        if "RESEARCH_EV_TOO_LOW" in reason:
            excluded_by_ev_low += 1
        if "RESEARCH_EV_TOO_HIGH" in reason:
            excluded_by_ev_high += 1
        if "RESEARCH_PROB_TOO_LOW" in reason:
            excluded_by_prob_low += 1
        if "RESEARCH_PROB_TOO_HIGH" in reason:
            excluded_by_prob_high += 1
        if "RESEARCH_TOXIC_MARKET" in reason:
            excluded_by_market += 1
        if "RESEARCH_NO_ODDS_SOURCE" in reason:
            excluded_by_odds_source += 1

    print(f"\n{BOLD}── Exclusion Breakdown {'─'*48}{RESET}")
    print(f"  Excluded by tier (A_TIER, NO_VALUE)        : {excluded_by_tier}")
    print(f"  Excluded by odd too low (< 1.20)            : {excluded_by_odd_low}")
    print(f"  Excluded by odd too high (> 2.50)           : {excluded_by_odd_high}")
    print(f"  Excluded by EV too low (< 3%)              : {excluded_by_ev_low}")
    print(f"  Excluded by EV too high (> 25%)            : {excluded_by_ev_high}")
    print(f"  Excluded by prob too low (< 0.50)          : {excluded_by_prob_low}")
    print(f"  Excluded by prob too high (> 0.80)         : {excluded_by_prob_high}")
    print(f"  Excluded by toxic market                   : {excluded_by_market}")
    print(f"  Excluded by no odds source                 : {excluded_by_odds_source}")

    # ── Historical ROI comparison ───────────────────────────────────────────────
    print(f"\n{BOLD}── Historical ROI Comparison {'─'*43}{RESET}")

    # All settled
    settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
    all_wins = sum(1 for r in settled if r.get("status") == "WON")
    all_pl = sum(float(r.get("profit_loss") or 0) for r in settled)
    all_roi = all_pl / len(settled) * 100 if settled else 0

    # LIVE_SAFE settled (simulated retroactive filter)
    live_safe_settled = [r for r in settled if r.get("selection_mode") == "LIVE_SAFE"]
    live_safe_wins = sum(1 for r in live_safe_settled if r.get("status") == "WON")
    live_safe_pl = sum(float(r.get("profit_loss") or 0) for r in live_safe_settled)
    live_safe_roi = live_safe_pl / len(live_safe_settled) * 100 if live_safe_settled else 0

    # RESEARCH settled
    research_settled = [r for r in settled if r.get("selection_mode") == "RESEARCH"]
    research_wins = sum(1 for r in research_settled if r.get("status") == "WON")
    research_pl = sum(float(r.get("profit_loss") or 0) for r in research_settled)
    research_roi = research_pl / len(research_settled) * 100 if research_settled else 0

    print(f"  All settled predictions:")
    print(f"    Count   : {len(settled)}")
    print(f"    Wins    : {all_wins}")
    print(f"    ROI     : {all_roi:+.1f}%")
    print(f"\n  LIVE_SAFE (retroactive filter):")
    print(f"    Count   : {len(live_safe_settled)}")
    print(f"    Wins    : {live_safe_wins}")
    print(f"    ROI     : {live_safe_roi:+.1f}%")
    print(f"\n  RESEARCH (excluded):")
    print(f"    Count   : {len(research_settled)}")
    print(f"    Wins    : {research_wins}")
    print(f"    ROI     : {research_roi:+.1f}%")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    ready = True
    if mode_counts.get("LIVE_SAFE", 0) == 0:
        _warn("No LIVE_SAFE picks found — safe mode may be too restrictive")
        ready = False
    if live_safe_roi < all_roi:
        _warn(f"LIVE_SAFE ROI ({live_safe_roi:+.1f}%) < All ROI ({all_roi:+.1f}%)")
        ready = False
    else:
        _ok(f"LIVE_SAFE ROI ({live_safe_roi:+.1f}%) >= All ROI ({all_roi:+.1f}%)")

    if ready:
        print(f"{BOLD}{GREEN}  SAFE_SELECTION_READY{RESET}")
        _ok("Safe selection mode is ready for production")
    else:
        print(f"{BOLD}{YELLOW}  SAFE_SELECTION_NEEDS_REVIEW{RESET}")
        _warn("Review safe selection criteria before enabling")

    print()
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
