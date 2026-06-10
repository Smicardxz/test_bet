"""
audit_cycle_summary_consistency.py
===================================
Verifies that Cycle Summary values match performance_report.py --since-reset.

Compares:
- LIVE_SAFE metrics from cycle summary vs performance_report
- ALL_POST_RESET metrics from cycle summary vs performance_report

Usage:
  python audit_cycle_summary_consistency.py
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


def _parse_reset_at_local() -> str:
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
    print(f"{BOLD}  CYCLE SUMMARY CONSISTENCY AUDIT{RESET}")
    print(f"{'═'*66}")

    reset_at = _parse_reset_at_local()
    safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() == "true"

    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — using last 30 days")

    _info(f"SAFE_SELECTION_MODE = {safe_mode}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch POST_RESET predictions (same as run_tracking_cycle.py) ───────────
    print(f"\n{BOLD}── Fetching POST_RESET predictions {'─'*43}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                q = repo._client.table("predictions").select(
                    "selection_mode, status, profit_loss, bookmaker_odd"
                ).gte("created_at", reset_at)
            else:
                q = repo._client.table("predictions").select(
                    "selection_mode, status, profit_loss, bookmaker_odd"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = repo._client.table("predictions").select(
                "selection_mode, status, profit_loss, bookmaker_odd"
            ).gte("prediction_date", cutoff)

        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    # ── Compute metrics (same as run_tracking_cycle.py) ───────────────────────
    print(f"\n{BOLD}── Computing Cycle Summary metrics {'─'*40}{RESET}")

    # ALL_POST_RESET metrics
    all_settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
    all_wins = [r for r in all_settled if r.get("status") == "WON"]
    cycle_all_post_reset_settled = len(all_settled)
    cycle_all_post_reset_hit_rate = (
        len(all_wins) / len(all_settled) * 100 if all_settled else 0
    )

    # Use stored profit_loss field to match performance_report.py
    cycle_all_post_reset_pl = sum(r.get("profit_loss") or 0 for r in all_settled)

    # ROI uses only picks with bookmaker_odd >= 1.1 (REAL_ODDS_THRESHOLD)
    REAL_ODDS = 1.1
    all_ev_settled = [r for r in all_settled if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
    if all_ev_settled:
        all_ev_pl = sum(r.get("profit_loss") or 0 for r in all_ev_settled)
        cycle_all_post_reset_roi = all_ev_pl / len(all_ev_settled) * 100
    else:
        cycle_all_post_reset_roi = 0.0

    # LIVE_SAFE metrics
    live_safe_rows = [r for r in rows if r.get("selection_mode") == "LIVE_SAFE"]
    live_safe_settled = [r for r in live_safe_rows if r.get("status") in ("WON", "LOST")]
    live_safe_wins = [r for r in live_safe_settled if r.get("status") == "WON"]
    cycle_live_safe_settled = len(live_safe_settled)
    cycle_live_safe_wins = len(live_safe_wins)
    cycle_live_safe_losses = len(live_safe_settled) - len(live_safe_wins)
    cycle_live_safe_hit_rate = (
        len(live_safe_wins) / len(live_safe_settled) * 100 if live_safe_settled else 0
    )

    # Use stored profit_loss field to match performance_report.py
    cycle_live_safe_pl = sum(r.get("profit_loss") or 0 for r in live_safe_settled)

    # ROI uses only picks with bookmaker_odd >= 1.1 (REAL_ODDS_THRESHOLD)
    REAL_ODDS = 1.1
    live_safe_ev_settled = [r for r in live_safe_settled if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
    if live_safe_ev_settled:
        live_safe_ev_pl = sum(r.get("profit_loss") or 0 for r in live_safe_ev_settled)
        cycle_live_safe_roi = live_safe_ev_pl / len(live_safe_ev_settled) * 100
    else:
        cycle_live_safe_roi = 0.0

    # RESEARCH_ONLY count
    cycle_research_only_count = len([r for r in rows if r.get("selection_mode") == "RESEARCH"])

    print(f"\n  Cycle Summary metrics:")
    print(f"    LIVE_SAFE settled  : {cycle_live_safe_settled}")
    print(f"    LIVE_SAFE wins     : {cycle_live_safe_wins}")
    print(f"    LIVE_SAFE losses   : {cycle_live_safe_losses}")
    print(f"    LIVE_SAFE hit_rate : {cycle_live_safe_hit_rate:.1f}%")
    print(f"    LIVE_SAFE ROI      : {cycle_live_safe_roi:.1f}%")
    print(f"    LIVE_SAFE P/L      : {cycle_live_safe_pl:.2f}u")
    print(f"    ALL_POST_RESET settled : {cycle_all_post_reset_settled}")
    print(f"    ALL_POST_RESET hit_rate: {cycle_all_post_reset_hit_rate:.1f}%")
    print(f"    ALL_POST_RESET ROI     : {cycle_all_post_reset_roi:.1f}%")
    print(f"    ALL_POST_RESET P/L     : {cycle_all_post_reset_pl:.2f}u")
    print(f"    RESEARCH_ONLY count   : {cycle_research_only_count}")

    # ── Fetch performance_report.py metrics ───────────────────────────────────
    print(f"\n{BOLD}── Fetching performance_report.py metrics {'─'*38}{RESET}")
    try:
        # Use the exact same logic as performance_report.py
        if reset_at:
            from app.database.supabase_repository import _parse_reset_at
            _reset = _parse_reset_at()
            perf = repo.get_performance_summary(days=30, since_date=_reset)
        else:
            perf = repo.get_performance_summary(days=30)

        # Filter to LIVE_SAFE manually (same as performance_report.py)
        if safe_mode:
            try:
                if reset_at:
                    cutoff = reset_at
                    if "T" in cutoff:
                        q = repo._client.table("predictions").select(
                            "status, profit_loss, bookmaker_odd"
                        ).in_("status", ["WON", "LOST", "VOID"]).gte("created_at", cutoff)
                    else:
                        q = repo._client.table("predictions").select(
                            "status, profit_loss, bookmaker_odd"
                        ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)
                else:
                    from datetime import date, timedelta
                    cutoff = (date.today() - timedelta(days=30)).isoformat()
                    q = repo._client.table("predictions").select(
                        "status, profit_loss, bookmaker_odd"
                    ).in_("status", ["WON", "LOST", "VOID"]).gte("prediction_date", cutoff)

                q = q.eq("selection_mode", "LIVE_SAFE")
                rows = q.execute().data or []

                from app.database.supabase_repository import SupabaseRepository
                perf = SupabaseRepository._compute_stats(rows)
            except Exception:
                pass

        report_total_wins = int(perf.get("total_wins", 0))
        report_total_losses = int(perf.get("total_losses", 0))
        report_total_void = int(perf.get("total_void", 0))
        report_total_settled = report_total_wins + report_total_losses
        report_pl = float(perf.get("total_profit_loss") or 0)
        report_roi = float(perf.get("ev_roi") or 0)  # Use ev_roi from _compute_stats

        report_hit_rate = (report_total_wins / report_total_settled * 100) if report_total_settled > 0 else 0.0

    except Exception as exc:
        _err(f"Performance report query failed: {exc}")
        sys.exit(1)

    print(f"\n  Performance report metrics:")
    if safe_mode:
        print(f"    LIVE_SAFE settled  : {report_total_settled}")
        print(f"    LIVE_SAFE wins     : {report_total_wins}")
        print(f"    LIVE_SAFE losses   : {report_total_losses}")
        print(f"    LIVE_SAFE hit_rate : {report_hit_rate:.1f}%")
        print(f"    LIVE_SAFE ROI      : {report_roi:.1f}%")
        print(f"    LIVE_SAFE P/L      : {report_pl:.2f}u")
    else:
        print(f"    ALL settled  : {report_total_settled}")
        print(f"    wins        : {report_total_wins}")
        print(f"    losses      : {report_total_losses}")
        print(f"    hit_rate    : {report_hit_rate:.1f}%")
        print(f"    ROI         : {report_roi:.1f}%")
        print(f"    P/L         : {report_pl:.2f}u")

    # ── Compare metrics ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Consistency Check{RESET}")

    if safe_mode:
        # Compare LIVE_SAFE metrics
        if cycle_live_safe_settled == report_total_settled:
            _ok(f"LIVE_SAFE settled: Cycle={cycle_live_safe_settled} Report={report_total_settled}")
        else:
            _err(f"LIVE_SAFE settled: Cycle={cycle_live_safe_settled} Report={report_total_settled}")

        if cycle_live_safe_wins == report_total_wins:
            _ok(f"LIVE_SAFE wins: Cycle={cycle_live_safe_wins} Report={report_total_wins}")
        else:
            _err(f"LIVE_SAFE wins: Cycle={cycle_live_safe_wins} Report={report_total_wins}")

        if abs(cycle_live_safe_hit_rate - report_hit_rate) < 0.1:
            _ok(f"LIVE_SAFE hit_rate: Cycle={cycle_live_safe_hit_rate:.1f}% Report={report_hit_rate:.1f}%")
        else:
            _err(f"LIVE_SAFE hit_rate: Cycle={cycle_live_safe_hit_rate:.1f}% Report={report_hit_rate:.1f}%")

        if abs(cycle_live_safe_roi - report_roi) < 0.1:
            _ok(f"LIVE_SAFE ROI: Cycle={cycle_live_safe_roi:.1f}% Report={report_roi:.1f}%")
        else:
            _err(f"LIVE_SAFE ROI: Cycle={cycle_live_safe_roi:.1f}% Report={report_roi:.1f}%")

        if abs(cycle_live_safe_pl - report_pl) < 0.01:
            _ok(f"LIVE_SAFE P/L: Cycle={cycle_live_safe_pl:.2f}u Report={report_pl:.2f}u")
        else:
            _err(f"LIVE_SAFE P/L: Cycle={cycle_live_safe_pl:.2f}u Report={report_pl:.2f}u")
    else:
        # Compare ALL_POST_RESET metrics
        if cycle_all_post_reset_settled == report_total_settled:
            _ok(f"ALL settled: Cycle={cycle_all_post_reset_settled} Report={report_total_settled}")
        else:
            _err(f"ALL settled: Cycle={cycle_all_post_reset_settled} Report={report_total_settled}")

        if abs(cycle_all_post_reset_hit_rate - report_hit_rate) < 0.1:
            _ok(f"hit_rate: Cycle={cycle_all_post_reset_hit_rate:.1f}% Report={report_hit_rate:.1f}%")
        else:
            _err(f"hit_rate: Cycle={cycle_all_post_reset_hit_rate:.1f}% Report={report_hit_rate:.1f}%")

        if abs(cycle_all_post_reset_roi - report_roi) < 0.1:
            _ok(f"ROI: Cycle={cycle_all_post_reset_roi:.1f}% Report={report_roi:.1f}%")
        else:
            _err(f"ROI: Cycle={cycle_all_post_reset_roi:.1f}% Report={report_roi:.1f}%")

        if abs(cycle_all_post_reset_pl - report_pl) < 0.01:
            _ok(f"P/L: Cycle={cycle_all_post_reset_pl:.2f}u Report={report_pl:.2f}u")
        else:
            _err(f"P/L: Cycle={cycle_all_post_reset_pl:.2f}u Report={report_pl:.2f}u")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    if safe_mode:
        consistent = (
            cycle_live_safe_settled == report_total_settled and
            cycle_live_safe_wins == report_total_wins and
            abs(cycle_live_safe_hit_rate - report_hit_rate) < 0.1 and
            abs(cycle_live_safe_roi - report_roi) < 0.1 and
            abs(cycle_live_safe_pl - report_pl) < 0.01
        )
    else:
        consistent = (
            cycle_all_post_reset_settled == report_total_settled and
            abs(cycle_all_post_reset_hit_rate - report_hit_rate) < 0.1 and
            abs(cycle_all_post_reset_roi - report_roi) < 0.1 and
            abs(cycle_all_post_reset_pl - report_pl) < 0.01
        )

    if consistent:
        print(f"{BOLD}{GREEN}  CYCLE_SUMMARY_CONSISTENT{RESET}")
        _ok("Cycle Summary matches performance_report.py")
    else:
        print(f"{BOLD}{RED}  CYCLE_SUMMARY_INCONSISTENT{RESET}")
        _err("Cycle Summary does not match performance_report.py")

    print()


if __name__ == "__main__":
    main()
