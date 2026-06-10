"""
scripts/refresh_predictions.py
================================
Phase 2 runner — real scan + persist to Supabase.
Displays:
  fixtures_saved_count
  predictions_saved_count
  odds_saved_count
  failed_inserts
  duplicate_predictions_skipped

Usage:
    python scripts/refresh_predictions.py
    python scripts/refresh_predictions.py --dry-run   # scan only, no DB write
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def run(dry_run: bool = False):
    print(f"\n{BOLD}{'═'*62}{RESET}")
    print(f"{BOLD}  REFRESH PIPELINE — Phase 2{RESET}")
    print(f"{'═'*62}")
    print(f"  Mode: {'DRY-RUN (no DB writes)' if dry_run else 'LIVE'}\n")

    # ── 1. Supabase status ────────────────────────────────────────────────────
    from app.database.supabase_config import get_supabase_config
    from app.database.supabase_repository import get_repository, reset_repository

    reset_repository()
    cfg  = get_supabase_config()
    repo = get_repository()

    print(f"  {'─'*58}")
    print(f"  Supabase status : {BOLD}{cfg.supabase_status}{RESET}")
    print(f"  Connected       : {'✓' if cfg.supabase_connected else '✗'}")
    if cfg.supabase_error:
        print(f"  Error           : {RED}{cfg.supabase_error}{RESET}")
    print(f"  {'─'*58}\n")

    if not cfg.supabase_connected and not dry_run:
        print(f"  {RED}BLOCKED — Supabase not connected. Check .env SUPABASE_URL/KEY.{RESET}\n")
        sys.exit(1)

    # ── 2. Scanner setup ──────────────────────────────────────────────────────
    print(f"  Initializing scanner…")
    from app.providers.data_source_manager import DataSourceManager
    from app.services.scanner.smart_scanner import SmartScanner

    try:
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=manager.odds_provider,
        )
        print(f"  Provider        : {BOLD}{manager.provider}{RESET}")
        print(f"  Real data       : {manager.is_real_data}")
    except Exception as e:
        print(f"  {RED}FAIL — Scanner init: {e}{RESET}")
        sys.exit(1)

    # ── 3. Scan ───────────────────────────────────────────────────────────────
    print(f"\n  Scanning today's fixtures…")
    t0 = time.time()
    try:
        scan_result = scanner.scan_today()
    except Exception as e:
        print(f"  {RED}FAIL — scan_today(): {e}{RESET}")
        sys.exit(1)
    scan_elapsed = time.time() - t0

    total    = scan_result.get("total_matches", 0)
    analyzed = scan_result.get("analyzed_count", 0)
    all_m    = (scan_result.get("analyzed_matches", []) or []) + \
               (scan_result.get("remaining_matches", []) or [])

    print(f"  Total matches   : {BOLD}{total}{RESET}")
    print(f"  Analyzed        : {BOLD}{analyzed}{RESET}")
    print(f"  Scan time       : {scan_elapsed:.1f}s")

    if not all_m:
        print(f"\n  {YELLOW}No matches returned by scanner — check data provider.{RESET}\n")
        _summary(0, 0, 0, 0, 0, dry_run)
        return

    if dry_run:
        print(f"\n  {YELLOW}DRY-RUN: skipping DB writes.{RESET}")
        _summary(len(all_m), analyzed, 0, 0, 0, dry_run=True)
        return

    # ── 4. Persist ────────────────────────────────────────────────────────────
    print(f"\n  Persisting to Supabase…")
    t1 = time.time()

    fixtures_saved  = 0
    predictions_new = 0
    predictions_dup = 0
    odds_saved      = 0
    failed_inserts  = 0

    for m in all_m:
        md = m.get("match_data") or m
        fid = str(md.get("match_id") or md.get("fixture_id") or "")

        # Fixture
        try:
            if repo.save_fixture(m):
                fixtures_saved += 1
            else:
                failed_inserts += 1
        except Exception:
            failed_inserts += 1

        # Prediction
        if m.get("analysis"):
            try:
                ok = repo.save_prediction(m)
                if ok:
                    predictions_new += 1
                else:
                    predictions_dup += 1
            except Exception:
                failed_inserts += 1

            # Odds snapshots
            odds = (m.get("analysis") or {}).get("matched_odds", []) or []
            if odds and fid:
                try:
                    n = repo.save_odds_snapshots(fid, odds)
                    odds_saved += n
                except Exception:
                    failed_inserts += 1

    persist_elapsed = time.time() - t1

    _summary(fixtures_saved, predictions_new, odds_saved,
             failed_inserts, predictions_dup, dry_run=False,
             persist_time=persist_elapsed)


def _summary(fix, preds, odds, fails, dups, dry_run, persist_time=0):
    print(f"\n  {'─'*58}")
    print(f"  {BOLD}RÉSULTATS REFRESH PIPELINE{RESET}")
    print(f"  {'─'*58}")
    print(f"  fixtures_saved_count           : {GREEN}{fix}{RESET}")
    print(f"  predictions_saved_count        : {GREEN}{preds}{RESET}")
    print(f"  odds_saved_count               : {GREEN}{odds}{RESET}")
    print(f"  failed_inserts                 : {RED if fails else GREEN}{fails}{RESET}")
    print(f"  duplicate_predictions_skipped  : {YELLOW}{dups}{RESET}")
    if persist_time:
        print(f"  persist_time                   : {persist_time:.2f}s")
    status = "DRY-RUN" if dry_run else ("OK" if fails == 0 else "PARTIAL")
    color  = YELLOW if dry_run else (GREEN if fails == 0 else YELLOW)
    print(f"  {'─'*58}")
    print(f"  Status : {color}{BOLD}{status}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
