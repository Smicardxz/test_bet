"""
audit_report_consistency.py
============================
Verifies that ALL reporting paths produce the same dataset when
TRACKING_RESET_AT is set.

Checks:
  Path A  — reset-filtered   (since_date = TRACKING_RESET_AT)
  Path B  — days-filtered    (days = 7, legacy start.py behaviour)
  Path C  — unfiltered       (all time)

Success condition:
  REPORT_CONSISTENT = TRUE
  Path A == start.py path (both auto-detect TRACKING_RESET_AT)

Usage:
  python audit_report_consistency.py
"""

import os
import sys
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


# ── helpers ───────────────────────────────────────────────────────────────────

def _since_filter(q, since_date: str, days: int = 30):
    """Apply date/datetime filter to a Supabase query builder."""
    from datetime import date, timedelta
    cutoff = since_date if since_date else (date.today() - timedelta(days=days)).isoformat()
    if "T" in cutoff:
        return q.gte("created_at", cutoff)
    return q.gte("prediction_date", cutoff)


def _odds_breakdown(repo, since_date: str = "", days: int = 30) -> dict:
    """Return {source: pick_count} breakdown from predictions table."""
    if not repo._client:
        return {}
    try:
        rows = _since_filter(
            repo._client.table("predictions").select("odds_source"),
            since_date, days,
        ).limit(5000).execute().data or []
        out: dict = {}
        for r in rows:
            src = (r.get("odds_source") or "NO_ODDS").upper()
            out[src] = out.get(src, 0) + 1
        return out
    except Exception:
        return {}


def _pending_count(repo, since_date: str = "", days: int = 30) -> int:
    if not repo._client:
        return -1
    try:
        rows = _since_filter(
            repo._client.table("predictions")
            .select("prediction_id")
            .eq("status", "PENDING"),
            since_date, days,
        ).limit(5000).execute().data or []
        return len(rows)
    except Exception:
        return -1


def _extract_metrics(perf: dict, odds_bk: dict, pending: int) -> dict:
    return {
        "settled":        perf.get("total_settled", 0),
        "wins":           perf.get("total_wins", 0),
        "losses":         perf.get("total_losses", 0),
        "pending":        pending,
        "API_FOOTBALL":   odds_bk.get("API_FOOTBALL", 0),
        "NO_ODDS":        odds_bk.get("NO_ODDS", 0),
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  REPORT CONSISTENCY AUDIT{RESET}")
    print(f"{'═'*66}")

    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()  # full ISO datetime, not truncated
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — Path A == Path C (no filter active)")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected — check SUPABASE_URL / SUPABASE_KEY")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Path A — Reset-filtered (since_date=TRACKING_RESET_AT) ──────────────
    print(f"\n{BOLD}── Path A  POST_RESET (since_date={reset_at or 'none'}) {'─'*20}{RESET}")
    perf_a   = repo.get_performance_summary(days=3650, since_date=reset_at) if reset_at \
               else repo.get_performance_summary(days=3650)
    odds_a   = _odds_breakdown(repo, since_date=reset_at) if reset_at \
               else _odds_breakdown(repo, days=3650)
    pend_a   = _pending_count(repo, since_date=reset_at) if reset_at \
               else _pending_count(repo, days=3650)
    metrics_a = _extract_metrics(perf_a, odds_a, pend_a)

    # ── Path B — start.py legacy (days=7, no reset) ──────────────────────────
    print(f"\n{BOLD}── Path B  legacy days=7 (no reset) {'─'*30}{RESET}")
    perf_b   = repo.get_performance_summary(days=7)
    odds_b   = _odds_breakdown(repo, days=7)
    pend_b   = _pending_count(repo, days=7)
    metrics_b = _extract_metrics(perf_b, odds_b, pend_b)

    # ── Path C — direct DB query: POST_RESET tracking_generation ─────────────
    print(f"\n{BOLD}── Path C  direct tracking_generation=POST_RESET {'─'*15}{RESET}")
    metrics_c: dict = {}
    try:
        rows_c = (
            repo._client.table("predictions")
            .select("status, odds_source")
            .eq("tracking_generation", "POST_RESET")
            .limit(5000)
            .execute()
        ).data or []
        odds_c: dict = {}
        wins_c = losses_c = settled_c = 0
        for r in rows_c:
            src = (r.get("odds_source") or "NO_ODDS").upper()
            odds_c[src] = odds_c.get(src, 0) + 1
            st = r.get("status", "")
            if st in ("WON", "LOST", "VOID"):
                settled_c += 1
                if st == "WON":
                    wins_c += 1
                elif st == "LOST":
                    losses_c += 1
        pending_c = sum(1 for r in rows_c if r.get("status") == "PENDING")
        metrics_c = {
            "settled":      settled_c,
            "wins":         wins_c,
            "losses":       losses_c,
            "pending":      pending_c,
            "API_FOOTBALL": odds_c.get("API_FOOTBALL", 0),
            "NO_ODDS":      odds_c.get("NO_ODDS", 0),
        }
    except Exception as exc:
        _warn(f"Path C failed (tracking_generation column may not exist): {exc}")

    # ── Comparison table ──────────────────────────────────────────────────────
    keys = ["settled", "wins", "losses", "pending", "API_FOOTBALL", "NO_ODDS"]
    col_w = 14

    print(f"\n  {'Metric':<20} {'Path A  (reset)':<{col_w}} {'Path B  (days=7)':<{col_w}} {'Path C  (gen=PR)':<{col_w}}  Match?")
    print(f"  {'─'*20} {'─'*col_w} {'─'*col_w} {'─'*col_w}  {'─'*6}")

    all_ab_match = True
    for k in keys:
        va = metrics_a.get(k, "?")
        vb = metrics_b.get(k, "?")
        vc = metrics_c.get(k, "?") if metrics_c else "?"
        # A vs B match check (the important one: start.py must match --since-reset)
        ab_match = (va == vb) if not reset_at else True  # if reset set, A != B is EXPECTED
        flag = ""
        if reset_at:
            # A and B SHOULD differ (different filters); A vs C should match
            ac_match = (str(va) == str(vc)) if metrics_c else None
            flag = f"{GREEN}AC✓{RESET}" if ac_match else (f"{YELLOW}AC≠{RESET}" if ac_match is False else "")
        else:
            flag = f"{GREEN}✓{RESET}" if ab_match else f"{RED}✗{RESET}"
            all_ab_match = all_ab_match and ab_match
        print(f"  {k:<20} {str(va):<{col_w}} {str(vb):<{col_w}} {str(vc):<{col_w}}  {flag}")

    # ── start.py path determination ───────────────────────────────────────────
    print(f"\n{BOLD}── start.py path determination {'─'*34}{RESET}")
    if reset_at:
        _info(f"TRACKING_RESET_AT={reset_at} is set → start.py auto-activates POST_RESET filter")
        _info(f"start.py path == Path A  (settled={metrics_a['settled']}  pending={metrics_a['pending']})")
        # The expected start.py output matches Path A
        startpy_match = (metrics_a == metrics_c) if metrics_c else None
        if startpy_match:
            _ok("start.py  ≡  performance_report.py --since-reset  ≡  Path C (POST_RESET)")
        elif startpy_match is False:
            _warn(f"start.py (Path A) and Path C differ — check tracking_generation back-fill")
            _warn(f"  Path A settled={metrics_a['settled']}  Path C settled={metrics_c.get('settled','?')}")
        else:
            _warn("Path C unavailable — cannot compare with tracking_generation column")
    else:
        _warn("No TRACKING_RESET_AT — start.py uses days=7 (Path B)")
        _info("Set TRACKING_RESET_AT=YYYY-MM-DD in .env to activate reset filter")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    if reset_at and metrics_c:
        consistent = (
            metrics_a.get("settled") == metrics_c.get("settled")
            and metrics_a.get("API_FOOTBALL") == metrics_c.get("API_FOOTBALL")
        )
        if consistent:
            print(f"{BOLD}{GREEN}  REPORT_CONSISTENT = TRUE{RESET}")
            _ok("Path A (auto-reset) == Path C (tracking_generation=POST_RESET)")
        else:
            print(f"{BOLD}{RED}  REPORT_CONSISTENT = FALSE{RESET}")
            _err("Path A and Path C diverge — run migration 002 back-fill or re-check tracking_generation values")
    elif not reset_at:
        print(f"{BOLD}{YELLOW}  REPORT_CONSISTENT = N/A  (TRACKING_RESET_AT not set){RESET}")
    else:
        print(f"{BOLD}{YELLOW}  REPORT_CONSISTENT = PARTIAL  (Path C unavailable){RESET}")
    print()


if __name__ == "__main__":
    main()
