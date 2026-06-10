"""
audit_ev_persistence.py — Phase 5 EV Persistence Audit
========================================================
Checks that EV picks computed in-memory are correctly persisted to Supabase.

Usage:
    python audit_ev_persistence.py            # query last 20 rows, no scan
    python audit_ev_persistence.py --scan     # run scanner, then verify
    python audit_ev_persistence.py --days 7   # last 7 days of predictions

Success condition:
    API_FOOTBALL_WITH_ODDS_COUNT > 0
    API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT == 0

Output metrics:
    EV_IN_MEMORY_COUNT
    EV_SAVED_COUNT
    API_FOOTBALL_WITH_ODDS_COUNT
    API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT
"""

import argparse
import os
import sys

from dotenv import load_dotenv
load_dotenv(override=True)

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ok(msg):  print(f"  {GREEN}✓{RESET}  {msg}")
def _err(msg): print(f"  {RED}✗{RESET}  {msg}")
def _warn(msg):print(f"  {YELLOW}⚠{RESET}  {msg}")
def _info(msg):print(f"  {CYAN}→{RESET}  {msg}")


# =============================================================================
# Step 1 — optional scanner run
# =============================================================================

def run_scanner_once() -> list:
    """Run a scan and return analyzed+remaining matches (in-memory, no DB write)."""
    print(f"\n{BOLD}── STEP 1 — Scanner (in-memory) {'─'*33}{RESET}")
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner

        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=getattr(manager, "odds_provider", None),
        )
        result = scanner.scan_today()
        analyzed  = result.get("analyzed_matches", []) or []
        remaining = result.get("remaining_matches", []) or []
        all_m = analyzed + remaining
        _ok(f"Scanner returned {len(all_m)} total matches  "
            f"({len(analyzed)} analyzed, {len(remaining)} remaining)")
        return all_m
    except Exception as exc:
        _err(f"Scanner failed: {exc}")
        return []


# =============================================================================
# Step 2 — inspect EV picks in memory
# =============================================================================

def inspect_ev_in_memory(analyzed: list) -> dict:
    """Count and inspect EV picks from the scanner output."""
    print(f"\n{BOLD}── STEP 2 — EV picks in memory {'─'*34}{RESET}")
    total = len(analyzed)
    ev_count = 0
    odds_source_counts: dict = {}
    sample_ev_picks = []

    for item in analyzed:
        an = item.get("analysis") or {}
        ev_qual = an.get("ev_qualified") or []
        beo     = an.get("best_ev_opportunity")
        src     = an.get("odds_source", "NO_ODDS")

        has_ev = bool(ev_qual) or isinstance(beo, dict)
        if has_ev:
            ev_count += 1
            odds_source_counts[src] = odds_source_counts.get(src, 0) + 1

        if has_ev and len(sample_ev_picks) < 3:
            pick = ev_qual[0] if ev_qual else beo
            md   = item.get("match_data", {})
            sample_ev_picks.append({
                "match":        f"{md.get('home_team')} v {md.get('away_team')}",
                "market":       pick.get("market"),
                "bookmaker_odd": pick.get("bookmaker_odd"),
                "ev_percentage": pick.get("ev_percentage") or pick.get("ev_percent"),
                "odds_source":  src,
                "bookmaker":    pick.get("bookmaker"),
            })

    _info(f"Matches analyzed  : {total}")
    _info(f"Matches with EV   : {ev_count}")
    for src, n in odds_source_counts.items():
        _info(f"  odds_source={src} : {n}")

    if sample_ev_picks:
        print(f"\n  {DIM}Sample EV picks:{RESET}")
        for s in sample_ev_picks:
            odd_str = f"@{s['bookmaker_odd']:.2f}" if s['bookmaker_odd'] else "@NULL"
            ev_str  = f"EV={s['ev_percentage']:.1f}%" if s['ev_percentage'] else "EV=None"
            print(f"    {s['match']} | {s['market']} | {odd_str} | {ev_str} | src={s['odds_source']}")

    return {"ev_in_memory_count": ev_count, "sample": sample_ev_picks}


# =============================================================================
# Step 3 — query Supabase: last N predictions
# =============================================================================

def query_supabase_predictions(days: int = 30, all_time: bool = False) -> list:
    """Fetch recent predictions from Supabase."""
    label = "all time" if all_time else f"last {days}d"
    print(f"\n{BOLD}── STEP 3 — Supabase query ({label}) {'─'*24}{RESET}")
    try:
        from app.database.supabase_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        if not repo.supabase_connected:
            _err("Supabase not connected — check SUPABASE_URL / SUPABASE_KEY in .env")
            return []

        if all_time:
            rows = repo.get_prediction_history(limit=1000)
        else:
            from datetime import date, timedelta
            since = (date.today() - timedelta(days=days)).isoformat()
            rows = repo.get_prediction_history(limit=500, since_date=since)
        _ok(f"Fetched {len(rows)} predictions ({label})")
        return rows
    except Exception as exc:
        _err(f"Supabase query failed: {exc}")
        return []


# =============================================================================
# Step 4 — verify persistence
# =============================================================================

def verify_ev_persistence(rows: list) -> dict:
    """Analyse the fetched rows for EV field completeness."""
    print(f"\n{BOLD}── STEP 4 — Persistence verification {'─'*28}{RESET}")

    if not rows:
        _warn("No rows to verify.")
        return {}

    af_rows     = [r for r in rows if r.get("odds_source") == "API_FOOTBALL"]
    af_with_odd = [r for r in af_rows if r.get("bookmaker_odd") is not None
                   and float(r.get("bookmaker_odd", 0)) >= 1.1]
    af_missing  = [r for r in af_rows if r.get("bookmaker_odd") is None
                   or float(r.get("bookmaker_odd", 0)) < 1.1]

    ev_saved    = [r for r in rows if r.get("bookmaker_odd") is not None
                   and float(r.get("bookmaker_odd", 0)) >= 1.1]

    # EV percentage field
    ev_pct_ok   = [r for r in ev_saved if r.get("ev_percentage") is not None
                   or r.get("ev_percent") is not None]

    metrics = {
        "TOTAL_ROWS":                            len(rows),
        "EV_SAVED_COUNT":                        len(ev_saved),
        "API_FOOTBALL_ROWS":                     len(af_rows),
        "API_FOOTBALL_WITH_ODDS_COUNT":          len(af_with_odd),
        "API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT": len(af_missing),
        "EV_PCT_POPULATED_COUNT":               len(ev_pct_ok),
    }

    print()
    for k, v in metrics.items():
        is_err = (k == "API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT" and v > 0)
        is_good = (k == "API_FOOTBALL_WITH_ODDS_COUNT" and v > 0)
        fn = _err if is_err else (_ok if is_good else _info)
        fn(f"{k} = {v}")

    # Show problem rows
    if af_missing:
        print(f"\n  {RED}Problem rows (API_FOOTBALL but bookmaker_odd=NULL):{RESET}")
        for r in af_missing[:5]:
            print(f"    {r.get('home_team')} v {r.get('away_team')} | {r.get('market')} "
                  f"| date={r.get('prediction_date')} | ev_tier={r.get('ev_tier')}")
        if len(af_missing) > 5:
            print(f"    ... and {len(af_missing) - 5} more")

    # Show good rows sample
    if af_with_odd:
        print(f"\n  {GREEN}Good rows (API_FOOTBALL with bookmaker_odd):{RESET}")
        for r in af_with_odd[:3]:
            ev_p = r.get("ev_percentage") or r.get("ev_percent")
            bk   = r.get("bookmaker") or "—"
            print(f"    {r.get('home_team')} v {r.get('away_team')} | {r.get('market')} "
                  f"| @{r.get('bookmaker_odd'):.2f} | EV={ev_p} | bk={bk}")

    return metrics


# =============================================================================
# Step 5 — result summary
# =============================================================================

def print_summary(ev_memory: dict, db_metrics: dict) -> bool:
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  AUDIT RESULT{RESET}")
    print(f"{'═'*60}")

    ev_in_mem   = ev_memory.get("ev_in_memory_count", "n/a")
    ev_saved    = db_metrics.get("EV_SAVED_COUNT", 0)
    af_with     = db_metrics.get("API_FOOTBALL_WITH_ODDS_COUNT", 0)
    af_missing  = db_metrics.get("API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT", 0)

    print(f"  EV_IN_MEMORY_COUNT                       = {CYAN}{ev_in_mem}{RESET}")
    print(f"  EV_SAVED_COUNT                           = {CYAN}{ev_saved}{RESET}")
    print(f"  API_FOOTBALL_WITH_ODDS_COUNT             = "
          f"{'  ' + GREEN if af_with > 0 else RED}{af_with}{RESET}")
    print(f"  API_FOOTBALL_MISSING_BOOKMAKER_ODD_COUNT = "
          f"{'  ' + GREEN if af_missing == 0 else RED}{af_missing}{RESET}")

    success = af_with > 0 and af_missing == 0
    print()
    if success:
        _ok(f"{BOLD}AUDIT PASSED{RESET}")
    else:
        if af_with == 0:
            _err("No API_FOOTBALL rows have bookmaker_odd. "
                 "Run migration 003, then do a fresh scan.")
        if af_missing > 0:
            _err(f"{af_missing} API_FOOTBALL rows still have bookmaker_odd=NULL. "
                 "Check save_prediction() mapping and run fresh scan.")
    print()
    return success


# =============================================================================
# main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="EV persistence audit")
    parser.add_argument("--scan",  action="store_true",
                        help="Run scanner once to get in-memory EV count")
    parser.add_argument("--days",  type=int, default=30,
                        help="Lookback days for Supabase query (default 30)")
    parser.add_argument("--all",   action="store_true",
                        help="Query all predictions (no date filter)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  EV PERSISTENCE AUDIT{RESET}")
    print(f"{'═'*60}")

    # Step 1+2: scanner
    ev_memory = {"ev_in_memory_count": "skipped"}
    if args.scan:
        analyzed = run_scanner_once()
        ev_memory = inspect_ev_in_memory(analyzed)
    else:
        print(f"\n  {DIM}Skipping scanner (use --scan to include in-memory check){RESET}")

    # Step 3: DB query
    rows = query_supabase_predictions(days=args.days, all_time=args.all)

    # Step 4: verify
    db_metrics = verify_ev_persistence(rows)

    # Step 5: summary
    ok = print_summary(ev_memory, db_metrics)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
