"""
audit_performance_report_consistency.py
======================================
Validates performance_report.py dataset consistency.

Checks:
- banner settled
- phase1 settled
- phase2 settled

must match when SAFE_SELECTION_MODE=true.

Usage:
  python audit_performance_report_consistency.py
"""

import os
import sys
from datetime import datetime

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
    print(f"{BOLD}  PERFORMANCE REPORT CONSISTENCY AUDIT{RESET}")
    print(f"{'═'*66}")

    safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
    if safe_mode:
        _info(f"SAFE_SELECTION_MODE = TRUE")
    else:
        _warn(f"SAFE_SELECTION_MODE = FALSE (consistency check not applicable)")
        print()
        sys.exit(0)

    reset_at = _parse_reset_at()
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Banner dataset (ALL settled including VOID) ───────────────────────────
    print(f"\n{BOLD}── Banner Dataset (ALL settled including VOID) {'─'*38}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select("selection_mode, status", count="exact")
            .in_("status", ["WON", "LOST", "VOID"])
        )
        if reset_at:
            cutoff = reset_at
            if "T" in cutoff:
                q = q.gte("created_at", cutoff)
            else:
                q = q.gte("prediction_date", cutoff)
        rows = q.execute().data or []
        banner_live_safe = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE")
        banner_live_safe_won = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE" and r.get("status") == "WON")
        banner_live_safe_lost = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE" and r.get("status") == "LOST")
        banner_live_safe_void = sum(1 for r in rows if r.get("selection_mode") == "LIVE_SAFE" and r.get("status") == "VOID")
        banner_research = sum(1 for r in rows if r.get("selection_mode") == "RESEARCH")
        banner_total = len(rows)
        print(f"  LIVE_SAFE: {banner_live_safe} (W:{banner_live_safe_won} L:{banner_live_safe_lost} V:{banner_live_safe_void})")
        print(f"  RESEARCH: {banner_research}")
        print(f"  ALL settled: {banner_total}")
    except Exception as exc:
        _err(f"Banner query failed: {exc}")
        sys.exit(1)

    # ── Phase 1/2 dataset (LIVE_SAFE only via get_performance_summary) ─────────
    print(f"\n{BOLD}── Phase 1/2 Dataset (LIVE_SAFE via get_performance_summary) {'─'*30}{RESET}")
    try:
        if reset_at:
            summary = repo.get_performance_summary(since_date=reset_at)
        else:
            summary = repo.get_performance_summary(days=30)

        # Apply same filtering logic as performance_report.py
        if safe_mode:
            try:
                if reset_at:
                    cutoff = reset_at
                    if "T" in cutoff:
                        q = repo._client.table("predictions").select(
                            "status, profit_loss, bookmaker_odd, statistical_tier, "
                            "match_universe, league, market, confidence_score"
                        ).in_("status", ["WON", "LOST", "VOID"]).gte("created_at", cutoff)
                    else:
                        q = repo._client.table("predictions").select(
                            "status, profit_loss, bookmaker_odd, statistical_tier, "
                            "match_universe, league, market, confidence_score"
                        ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)
                else:
                    from datetime import date, timedelta
                    cutoff = (date.today() - timedelta(days=30)).isoformat()
                    q = repo._client.table("predictions").select(
                        "status, profit_loss, bookmaker_odd, statistical_tier, "
                        "match_universe, league, market, confidence_score"
                    ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)

                q = q.eq("selection_mode", "LIVE_SAFE")
                rows = q.execute().data or []

                from app.database.supabase_repository import SupabaseRepository
                summary = SupabaseRepository._compute_stats(rows)
            except Exception:
                pass

        phase1_total_wins = int(summary.get("total_wins", 0))
        phase1_total_losses = int(summary.get("total_losses", 0))
        phase1_total_void = int(summary.get("total_void", 0))
        phase1_total_settled = phase1_total_wins + phase1_total_losses
        print(f"  Wins: {phase1_total_wins}")
        print(f"  Losses: {phase1_total_losses}")
        print(f"  Void: {phase1_total_void}")
        print(f"  Settled (W+L): {phase1_total_settled}")
    except Exception as exc:
        _err(f"Phase 1/2 query failed: {exc}")
        sys.exit(1)

    # ── Debug: Check _fetch_settled directly ───────────────────────────────────
    print(f"\n{BOLD}── Debug: Direct _fetch_settled query {'─'*41}{RESET}")
    try:
        from datetime import timedelta
        cutoff = reset_at if reset_at else (datetime.now().date() - timedelta(days=30)).isoformat()
        q = (
            repo._client.table("predictions")
            .select("status, selection_mode, profit_loss, bookmaker_odd")
            .in_("status", ["WON", "LOST", "VOID"])
        )
        if "T" in cutoff:
            q = q.gte("created_at", cutoff)
        else:
            q = q.gte("prediction_date", cutoff)
        q = q.eq("selection_mode", "LIVE_SAFE")
        rows = q.execute().data or []
        print(f"  LIVE_SAFE settled (direct query): {len(rows)}")
        for r in rows[:5]:
            print(f"    {r.get('status')} - {r.get('selection_mode')} - odd={r.get('bookmaker_odd')} - pl={r.get('profit_loss')}")
    except Exception as exc:
        _err(f"Debug query failed: {exc}")

    # ── Debug: Call _fetch_settled method directly ─────────────────────────────
    print(f"\n{BOLD}── Debug: Call repo._fetch_settled directly {'─'*39}{RESET}")
    try:
        if reset_at:
            fetch_rows = repo._fetch_settled(since_date=reset_at)
        else:
            from datetime import timedelta
            fetch_rows = repo._fetch_settled(days=30)
        print(f"  _fetch_settled returned: {len(fetch_rows)} rows")
        for r in fetch_rows[:5]:
            print(f"    {r.get('status')} - {r.get('selection_mode')} - odd={r.get('bookmaker_odd')}")
    except Exception as exc:
        _err(f"_fetch_settled failed: {exc}")

    # ── Phase 6 dataset (odds_source breakdown) ───────────────────────────────
    print(f"\n{BOLD}── Phase 6 Dataset (odds_source breakdown) {'─'*42}{RESET}")
    try:
        q = repo._client.table("predictions").select(
            "odds_source,status,bookmaker_odd,selection_mode"
        )
        # Apply selection_mode filter when safe_mode is enabled
        if safe_mode:
            q = q.eq("selection_mode", "LIVE_SAFE")
        if reset_at:
            if "T" in reset_at:
                q = q.gte("created_at", reset_at)
            else:
                q = q.gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = q.gte("prediction_date", cutoff)
        rows = q.execute().data or []
        phase6_total = len(rows)
        phase6_settled = sum(1 for r in rows if r.get("status") in ("WON", "LOST", "VOID"))
        print(f"  Total predictions: {phase6_total}")
        print(f"  Settled predictions: {phase6_settled}")
    except Exception as exc:
        _err(f"Phase 6 query failed: {exc}")
        sys.exit(1)

    # ── Consistency check ─────────────────────────────────────────────────────
    print(f"\n{BOLD}── Consistency Check{RESET}")

    # Banner shows ALL (including VOID), Phases 1-2 show LIVE_SAFE (W+L only)
    # Phase 6 shows LIVE_SAFE predictions (all statuses)
    # This is now correct after the fix
    print(f"\n  Expected behavior after fix:")
    print(f"    Banner: Shows ALL settled breakdown (W+L+V)")
    print(f"    Phase 1/2: Shows LIVE_SAFE only (W+L, labeled)")
    print(f"    Phase 6: Shows LIVE_SAFE predictions (all statuses)")

    # Verify Phase 1/2 matches LIVE_SAFE W+L count (excluding VOID)
    print(f"\n  Verifying Phase 1/2 vs LIVE_SAFE (W+L only)...")
    banner_live_safe_wl = banner_live_safe_won + banner_live_safe_lost
    if phase1_total_settled == banner_live_safe_wl:
        _ok(f"Phase 1/2 settled ({phase1_total_settled}) matches LIVE_SAFE W+L ({banner_live_safe_wl})")
    else:
        _err(f"Phase 1/2 settled ({phase1_total_settled}) != LIVE_SAFE W+L ({banner_live_safe_wl})")
        if banner_live_safe_void > 0:
            _info(f"Note: {banner_live_safe_void} LIVE_SAFE VOID picks excluded from W+L count")

    # Verify Phase 6 settled matches LIVE_SAFE settled (banner only counts settled)
    print(f"\n  Verifying Phase 6 settled vs LIVE_SAFE settled...")
    if phase6_settled == banner_live_safe:
        _ok(f"Phase 6 settled ({phase6_settled}) matches LIVE_SAFE settled ({banner_live_safe})")
    else:
        _err(f"Phase 6 settled ({phase6_settled}) != LIVE_SAFE settled ({banner_live_safe})")
        if phase6_total > phase6_settled:
            _info(f"Note: Phase 6 includes {phase6_total - phase6_settled} pending LIVE_SAFE predictions")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    consistent = (
        phase1_total_settled == banner_live_safe_wl and
        phase6_settled == banner_live_safe
    )

    if consistent:
        print(f"{BOLD}{GREEN}  PERFORMANCE_REPORT_CONSISTENT{RESET}")
        _ok("All sections use consistent LIVE_SAFE dataset (with clear labels)")
        if banner_live_safe_void > 0:
            _info(f"Note: {banner_live_safe_void} LIVE_SAFE VOID picks excluded from W+L counts")
        if phase6_total > phase6_settled:
            _info(f"Note: Phase 6 includes {phase6_total - phase6_settled} pending LIVE_SAFE predictions")
    else:
        print(f"{BOLD}{RED}  PERFORMANCE_REPORT_INCONSISTENT{RESET}")
        _err("Dataset mismatch detected")

    print()


if __name__ == "__main__":
    main()
