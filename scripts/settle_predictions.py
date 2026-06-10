"""
scripts/settle_predictions.py
================================
Phase 3 runner — settle all PENDING predictions.
Displays:
  settled_predictions
  won_count
  lost_count
  void_count
  total_profit_loss

Usage:
    python scripts/settle_predictions.py
    python scripts/settle_predictions.py --dry-run   # evaluate only, no DB write
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
    print(f"{BOLD}  SETTLEMENT PIPELINE — Phase 3{RESET}")
    print(f"{'═'*62}")
    print(f"  Mode: {'DRY-RUN (no DB writes)' if dry_run else 'LIVE'}\n")

    # ── 1. Supabase status ────────────────────────────────────────────────────
    from app.database.supabase_config import get_supabase_config
    from app.database.supabase_repository import (
        get_repository, reset_repository, evaluate_market_result, calculate_profit_loss
    )

    reset_repository()
    cfg  = get_supabase_config()
    repo = get_repository()

    print(f"  Supabase status : {BOLD}{cfg.supabase_status}{RESET}")
    print(f"  Connected       : {'✓' if cfg.supabase_connected else '✗'}")
    if cfg.supabase_error:
        print(f"  Error           : {RED}{cfg.supabase_error}{RESET}")
    print()

    if not cfg.supabase_connected:
        print(f"  {RED}BLOCKED — Supabase not connected.{RESET}\n")
        sys.exit(1)

    # ── 2. Fetch pending predictions ──────────────────────────────────────────
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=110)

    print(f"  Fetching PENDING predictions (kickoff < now + 110min)…")
    pending = repo.get_pending_predictions(before_kickoff=cutoff, limit=300)
    print(f"  Pending found   : {BOLD}{len(pending)}{RESET}")

    if not pending:
        print(f"\n  {YELLOW}No pending predictions to settle.{RESET}")
        _summary(0, 0, 0, 0, 0.0, dry_run)
        return

    # ── 3. Data provider (for final scores) ───────────────────────────────────
    print(f"  Initializing data provider…")
    try:
        from app.providers.data_source_manager import DataSourceManager
        manager = DataSourceManager()
        print(f"  Provider        : {manager.provider}")
    except Exception as e:
        print(f"  {YELLOW}Provider init failed (settlement may be limited): {e}{RESET}")
        manager = None

    # ── 4. Settle ─────────────────────────────────────────────────────────────
    from app.pipelines.settlement_pipeline import SettlementPipeline

    if dry_run:
        # Dry-run: evaluate only, no DB writes
        print(f"\n  {YELLOW}DRY-RUN: evaluating without writing…{RESET}")
        won = lost = void_ = 0
        total_pl = 0.0
        for pred in pending[:20]:  # sample 20
            fid    = pred.get("fixture_id", "")
            market = pred.get("market", "")
            result = _try_fetch_result(manager, fid)
            if not result:
                continue
            outcome = evaluate_market_result(
                market,
                result.get("home_score", 0), result.get("away_score", 0),
                result.get("ht_home_score", 0), result.get("ht_away_score", 0),
            )
            odd = float(pred.get("bookmaker_odd") or 1.85)
            pl  = calculate_profit_loss(outcome, odd)
            total_pl += pl
            if outcome == "WIN":   won += 1
            elif outcome == "LOSS": lost += 1
            else:                   void_ += 1
        _summary(won + lost + void_, won, lost, void_, total_pl, dry_run=True)
        return

    t0       = time.time()
    pipeline = SettlementPipeline(
        repository=repo,
        provider=manager,
    )
    result   = pipeline.run()
    elapsed  = time.time() - t0

    settled  = result.get("settled", 0)
    won      = result.get("won",     0)
    lost     = result.get("lost",    0)
    void_    = result.get("void",    0)
    errors   = result.get("errors",  [])

    # Compute total P/L from settled predictions
    total_pl = _compute_pl(repo, won, lost)

    if errors:
        print(f"\n  {YELLOW}Pipeline warnings:{RESET}")
        for e in errors[:5]:
            print(f"    {YELLOW}⚠{RESET} {e[:80]}")

    _summary(settled, won, lost, void_, total_pl, dry_run=False,
             elapsed=elapsed, errors=len(errors))


def _try_fetch_result(manager, fixture_id: str):
    if not manager or not fixture_id:
        return None
    try:
        match = manager.get_match_result(fixture_id) \
            if hasattr(manager, "get_match_result") else None
        if not match:
            return None
        if isinstance(match, dict):
            return match
        return {
            "home_score":     getattr(match, "home_score", 0),
            "away_score":     getattr(match, "away_score", 0),
            "ht_home_score":  getattr(match, "ht_home_score", 0),
            "ht_away_score":  getattr(match, "ht_away_score", 0),
        }
    except Exception:
        return None


def _compute_pl(repo, won: int, lost: int) -> float:
    """Approximate total P/L from recent settled history."""
    try:
        history = repo.get_prediction_history(limit=500, status="")
        settled = [r for r in history if r.get("status") in ("WON", "LOST")]
        return sum(float(r.get("profit_loss") or 0) for r in settled)
    except Exception:
        # Estimate from win/loss counts and average odd ~1.85
        return round(won * 0.85 - lost * 1.0, 4)


def _summary(settled, won, lost, void_, total_pl, dry_run,
             elapsed=0, errors=0):
    print(f"\n  {'─'*58}")
    print(f"  {BOLD}RÉSULTATS SETTLEMENT PIPELINE{RESET}")
    print(f"  {'─'*58}")
    print(f"  settled_predictions  : {BOLD}{settled}{RESET}")
    print(f"  won_count            : {GREEN}{won}{RESET}")
    print(f"  lost_count           : {RED}{lost}{RESET}")
    print(f"  void_count           : {YELLOW}{void_}{RESET}")
    print(f"  total_profit_loss    : "
          + (f"{GREEN}+{total_pl:.4f}u{RESET}" if total_pl >= 0
             else f"{RED}{total_pl:.4f}u{RESET}"))
    if elapsed:
        print(f"  elapsed              : {elapsed:.2f}s")
    if errors:
        print(f"  pipeline_errors      : {YELLOW}{errors}{RESET}")
    status = "DRY-RUN" if dry_run else ("OK" if errors == 0 else "PARTIAL")
    color  = YELLOW if dry_run else (GREEN if errors == 0 else YELLOW)
    print(f"  {'─'*58}")
    print(f"  Status : {color}{BOLD}{status}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
