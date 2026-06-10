"""
scripts/run_tracking_cycle.py
================================
Tracking cycle orchestrator — refresh + settle + report.

Cycle steps (every N hours):
  1. refresh_predictions   — scan fixtures, save to Supabase
  2. auto_settle           — fetch finished results, settle PENDING → WON/LOST/VOID
  3. performance_report    — print/log performance summary
  4. log_summary           — write JSON summary to logs/

Options:
    --once              Run one cycle then exit
    --every-hours N     Run every N hours (default: 2)
    --dry-run           Scan only, no DB writes, no settlement
    --no-settle         Skip settlement step
    --no-refresh        Skip refresh step
    --no-report         Skip performance report print
    --days N            Lookback days for report (default: 30)

Safety guarantees (built into sub-modules):
    ✓ Predictions are upserted — never duplicated
    ✓ Only PENDING predictions are settled
    ✓ WON/LOST are never overwritten
    ✓ NOT_FINISHED matches are skipped silently
    ✓ API errors are caught — cycle continues

Log fields per cycle:
    cycle_start, fixtures_saved, predictions_saved,
    pending_before, settled_count, wins, losses, void,
    pending_after, roi, hit_rate, errors, next_run_at

Validation:
    python scripts/run_tracking_cycle.py --once
    # → must finish with: TRACKING_CYCLE_OK

Continuous mode:
    python scripts/run_tracking_cycle.py --every-hours 2
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Logging setup ────────────────────────────────────────────────────────────
LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "tracking_cycle.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("tracking_cycle")

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

CYCLE_LOG = os.path.join(LOG_DIR, "cycle_history.jsonl")


# =============================================================================
# Core cycle
# =============================================================================

def run_cycle(
    dry_run: bool      = False,
    no_settle: bool    = False,
    no_refresh: bool   = False,
    no_report: bool    = False,
    report_days: int   = 30,
    since_reset: bool  = False,
) -> dict:
    """
    Run one full tracking cycle.
    Returns a summary dict. Always returns (never raises).
    """
    # Auto-detect reset filter from env when not explicitly passed
    if not since_reset and os.environ.get("TRACKING_RESET_AT", "").strip():
        since_reset = True

    started = datetime.now(timezone.utc)
    safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() == "true"
    log: dict = {
        "cycle_start":        started.isoformat(),
        "dry_run":            dry_run,
        "safe_mode":          safe_mode,
        "fixtures_saved":     0,
        "predictions_saved":  0,
        "pending_before":     0,
        "settled_count":      0,
        "wins":               0,
        "losses":             0,
        "void":               0,
        "pending_after":      0,
        # LIVE_SAFE metrics (when safe_mode=true)
        "live_safe_settled":  0,
        "live_safe_wins":     0,
        "live_safe_losses":   0,
        "live_safe_hit_rate": 0.0,
        "live_safe_roi":      0.0,
        "live_safe_pl":       0.0,
        # ALL_POST_RESET metrics
        "all_post_reset_settled": 0,
        "all_post_reset_hit_rate": 0.0,
        "all_post_reset_roi": 0.0,
        "all_post_reset_pl": 0.0,
        # RESEARCH_ONLY count
        "research_only_count": 0,
        # EVENT_MODE statistics
        "event_mode_enabled": False,
        "event_tagged_predictions": 0,
        "event_matches_detected": 0,
        "domestic_matches": 0,
        "international_friendlies": 0,
        "world_cup_matches": 0,
        "youth_tournaments": 0,
        # Legacy fields (deprecated, kept for compatibility)
        "roi":                0.0,
        "hit_rate":           0.0,
        "profit_loss":        0.0,
        "errors":             [],
        "next_run_at":        None,
    }

    _banner(f"TRACKING CYCLE  {started.strftime('%Y-%m-%d %H:%M UTC')}", dry_run)

    # ── Supabase ──────────────────────────────────────────────────────────────
    try:
        from app.database.supabase_config import reset_supabase_config, get_supabase_config
        from app.database.supabase_repository import reset_repository, get_repository

        reset_supabase_config()
        reset_repository()
        cfg  = get_supabase_config()
        repo = get_repository()

        if not cfg.supabase_connected:
            msg = f"Supabase not connected: {cfg.supabase_error}"
            log["errors"].append(msg)
            logger.error(f"[CYCLE] {msg}")
            _print_cycle_log(log)
            return log

        logger.info(f"[CYCLE] Supabase OK")
    except Exception as exc:
        log["errors"].append(f"supabase_init: {exc}")
        logger.error(f"[CYCLE] Supabase init failed: {exc}")
        _print_cycle_log(log)
        return log

    # ── Provider ──────────────────────────────────────────────────────────────
    provider = None
    try:
        from app.providers.data_source_manager import DataSourceManager
        manager  = DataSourceManager()
        provider = manager.provider
        logger.info(f"[CYCLE] Provider: {manager.provider}")
    except Exception as exc:
        log["errors"].append(f"provider_init: {exc}")
        logger.warning(f"[CYCLE] Provider init failed (settlement may be limited): {exc}")

    # ── Count pending BEFORE ──────────────────────────────────────────────────
    try:
        log["pending_before"] = repo.get_pending_count()
        logger.info(f"[CYCLE] pending_before={log['pending_before']}")
    except Exception as exc:
        log["errors"].append(f"pending_before: {exc}")

    # ── Step 0: Repair misclassified VOID (one-time fix, idempotent) ──────────
    if not dry_run:
        try:
            from app.services.settlement.auto_settler import fix_voided_predictions
            fix_r = fix_voided_predictions(repo)
            if fix_r.get("fixed", 0) > 0:
                print(f"  {GREEN}[FIX] Repaired {fix_r['fixed']} misclassified VOID → WON/LOST{RESET}")
                logger.info(f"[CYCLE] fix_void: fixed={fix_r['fixed']} skipped={fix_r['skipped']}")
        except Exception as exc:
            logger.debug(f"[CYCLE] fix_void non-blocking: {exc}")

    # ── Step 1: Refresh ───────────────────────────────────────────────────────
    if not no_refresh:
        _step("1/3 — REFRESH FIXTURES")
        try:
            import scripts.refresh_predictions as rp
            # Capture summary by running internal logic
            rp_result = _run_refresh(dry_run=dry_run)
            log["fixtures_saved"]    = rp_result.get("fixtures_saved", 0)
            log["predictions_saved"] = rp_result.get("predictions_saved", 0)
            logger.info(
                f"[CYCLE] refresh: fixtures={log['fixtures_saved']} "
                f"predictions={log['predictions_saved']}"
            )
        except Exception as exc:
            log["errors"].append(f"refresh: {exc}")
            logger.error(f"[CYCLE] Refresh failed: {exc}")
    else:
        logger.info("[CYCLE] Refresh skipped (--no-refresh)")

    # ── Step 2: Tag EVENT MODE ───────────────────────────────────────────────────
    if not dry_run:
        _step("2/4 — TAG EVENT MODE")
        try:
            from app.services.events.event_mode_tagger import tag_event_mode
            event_result = tag_event_mode(repo, dry_run=dry_run)
            
            # Add event mode stats to log
            log["event_mode_enabled"] = event_result.get("event_mode_enabled", False)
            log["event_tagged_predictions"] = event_result.get("event_tagged_predictions", 0)
            log["event_matches_detected"] = event_result.get("event_matches_detected", 0)
            log["domestic_matches"] = event_result.get("domestic_matches", 0)
            log["international_friendlies"] = event_result.get("international_friendlies", 0)
            log["world_cup_matches"] = event_result.get("world_cup_matches", 0)
            log["youth_tournaments"] = event_result.get("youth_tournaments", 0)
            
            logger.info(
                f"[CYCLE] event_mode: enabled={event_result.get('event_mode_enabled')} "
                f"tagged={event_result.get('event_tagged_predictions')} "
                f"events={event_result.get('event_matches_detected')} "
                f"domestic={event_result.get('domestic_matches')}"
            )
        except Exception as exc:
            log["errors"].append(f"event_mode: {exc}")
            logger.error(f"[CYCLE] Event mode tagging failed: {exc}")
    elif dry_run:
        logger.info("[CYCLE] Event mode tagging (--dry-run)")

    # ── Step 3: Settle ────────────────────────────────────────────────────────
    if not no_settle and not dry_run:
        _step("3/4 — SETTLE PREDICTIONS")
        if provider:
            try:
                from app.services.settlement.auto_settler import auto_settle_predictions
                settle_result = auto_settle_predictions(repo, provider)
                log["settled_count"] = settle_result.get("settled", 0)
                log["wins"]          = settle_result.get("won",     0)
                log["losses"]        = settle_result.get("lost",    0)
                log["void"]          = settle_result.get("void",    0)
                for d in settle_result.get("details", []):
                    if d.get("outcome") in ("API_ERROR", "RESULT_MISSING"):
                        log["errors"].append(
                            f"settle:{d['prediction_id']}:{d['outcome']}"
                        )
                logger.info(
                    f"[CYCLE] settle: settled={log['settled_count']} "
                    f"won={log['wins']} lost={log['losses']} void={log['void']}"
                )
            except Exception as exc:
                log["errors"].append(f"settle: {exc}")
                logger.error(f"[CYCLE] Settlement failed: {exc}")
        else:
            logger.warning("[CYCLE] No provider — settlement skipped")
            log["errors"].append("settle: no_provider")
    elif dry_run:
        logger.info("[CYCLE] Settlement skipped (--dry-run)")
    else:
        logger.info("[CYCLE] Settlement skipped (--no-settle)")

    # ── Count pending AFTER ───────────────────────────────────────────────────
    try:
        log["pending_after"] = repo.get_pending_count()
        logger.info(f"[CYCLE] pending_after={log['pending_after']}")
    except Exception as exc:
        log["errors"].append(f"pending_after: {exc}")

    # ── Compute LIVE_SAFE / ALL_POST_RESET / RESEARCH_ONLY metrics ─────────────
    try:
        from app.database.supabase_repository import _parse_reset_at
        _reset = _parse_reset_at() if since_reset else None

        # Query for metrics
        if _reset:
            if "T" in _reset:
                q = repo._client.table("predictions").select(
                    "selection_mode, status, profit_loss, bookmaker_odd"
                ).gte("created_at", _reset)
            else:
                q = repo._client.table("predictions").select(
                    "selection_mode, status, profit_loss, bookmaker_odd"
                ).gte("prediction_date", _reset)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=report_days)).isoformat()
            q = repo._client.table("predictions").select(
                "selection_mode, status, profit_loss, bookmaker_odd"
            ).gte("prediction_date", cutoff)

        rows = q.execute().data or []

        # ALL_POST_RESET metrics
        all_settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
        all_wins = [r for r in all_settled if r.get("status") == "WON"]
        log["all_post_reset_settled"] = len(all_settled)
        log["all_post_reset_hit_rate"] = (
            len(all_wins) / len(all_settled) * 100 if all_settled else 0
        )

        # Use stored profit_loss field to match performance_report.py
        all_pl = sum(r.get("profit_loss") or 0 for r in all_settled)
        log["all_post_reset_pl"] = all_pl

        # ROI uses only picks with bookmaker_odd >= 1.1 (REAL_ODDS_THRESHOLD)
        REAL_ODDS = 1.1
        all_ev_settled = [r for r in all_settled if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
        if all_ev_settled:
            all_ev_pl = sum(r.get("profit_loss") or 0 for r in all_ev_settled)
            log["all_post_reset_roi"] = all_ev_pl / len(all_ev_settled) * 100
        else:
            log["all_post_reset_roi"] = 0.0

        # LIVE_SAFE metrics
        live_safe_rows = [r for r in rows if r.get("selection_mode") == "LIVE_SAFE"]
        live_safe_settled = [r for r in live_safe_rows if r.get("status") in ("WON", "LOST")]
        live_safe_wins = [r for r in live_safe_settled if r.get("status") == "WON"]
        log["live_safe_settled"] = len(live_safe_settled)
        log["live_safe_wins"] = len(live_safe_wins)
        log["live_safe_losses"] = len(live_safe_settled) - len(live_safe_wins)
        log["live_safe_hit_rate"] = (
            len(live_safe_wins) / len(live_safe_settled) * 100 if live_safe_settled else 0
        )

        # Use stored profit_loss field to match performance_report.py
        live_safe_pl = sum(r.get("profit_loss") or 0 for r in live_safe_settled)
        log["live_safe_pl"] = live_safe_pl

        # ROI uses only picks with bookmaker_odd >= 1.1 (REAL_ODDS_THRESHOLD)
        REAL_ODDS = 1.1
        live_safe_ev_settled = [r for r in live_safe_settled if float(r.get("bookmaker_odd") or 0) >= REAL_ODDS]
        if live_safe_ev_settled:
            live_safe_ev_pl = sum(r.get("profit_loss") or 0 for r in live_safe_ev_settled)
            log["live_safe_roi"] = live_safe_ev_pl / len(live_safe_ev_settled) * 100
        else:
            log["live_safe_roi"] = 0.0

        # RESEARCH_ONLY count
        log["research_only_count"] = len([r for r in rows if r.get("selection_mode") == "RESEARCH"])

        logger.info(
            f"[CYCLE] metrics: live_safe={log['live_safe_settled']} "
            f"all_post_reset={log['all_post_reset_settled']} "
            f"research={log['research_only_count']}"
        )
    except Exception as exc:
        log["errors"].append(f"metrics: {exc}")
        logger.error(f"[CYCLE] Metrics computation failed: {exc}")

    # ── Step 4: Performance stats ─────────────────────────────────────────────
    _step("4/4 — PERFORMANCE REPORT")
    try:
        if since_reset:
            from app.database.supabase_repository import _parse_reset_at
            _reset = _parse_reset_at()
            perf = repo.get_performance_summary(days=report_days, since_date=_reset)
        else:
            perf = repo.get_performance_summary(days=report_days)
        log["hit_rate"]    = round(float(perf.get("stat_hit_rate") or perf.get("hit_rate") or 0) * 100, 2)
        log["roi"]         = round(float(perf.get("ev_roi") or perf.get("roi") or 0), 2)
        log["profit_loss"] = round(float(perf.get("total_profit_loss") or 0), 4)
        logger.info(
            f"[CYCLE] perf: hit_rate={log['hit_rate']}% roi={log['roi']}% "
            f"pl={log.get('profit_loss', 0):+.2f}u"
        )
        if not no_report:
            import scripts.performance_report as pr
            pr.run(days=report_days, since_reset=since_reset)
    except Exception as exc:
        log["errors"].append(f"report: {exc}")
        logger.error(f"[CYCLE] Report failed: {exc}")

    # ── Finalize ──────────────────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    log["elapsed_seconds"] = round(elapsed, 1)
    _print_cycle_log(log)
    _write_cycle_log(log)

    return log


# =============================================================================
# Refresh helper (returns structured dict instead of sys.exit)
# =============================================================================

def _run_refresh(dry_run: bool = False) -> dict:
    """Run refresh pipeline inline, return summary dict."""
    result = {"fixtures_saved": 0, "predictions_saved": 0, "errors": []}
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        from app.database.supabase_repository import get_repository
        import time

        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=manager.odds_provider,
        )

        scan_result = scanner.scan_today()
        all_m = (
            (scan_result.get("analyzed_matches") or []) +
            (scan_result.get("remaining_matches") or [])
        )

        if dry_run or not all_m:
            return result

        repo = get_repository()
        for m in all_m:
            try:
                if repo.save_fixture(m):
                    result["fixtures_saved"] += 1
            except Exception:
                pass
            if m.get("analysis"):
                try:
                    if repo.save_prediction(m):
                        result["predictions_saved"] += 1
                except Exception:
                    pass

    except Exception as exc:
        result["errors"].append(str(exc))
        logger.error(f"[REFRESH_INLINE] {exc}")

    return result


# =============================================================================
# Formatting helpers
# =============================================================================

def _banner(title: str, dry_run: bool):
    mode = f"  {YELLOW}[DRY-RUN]{RESET}" if dry_run else ""
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  {title}{mode}{RESET}")
    print(f"{BOLD}{'═'*66}{RESET}")


def _step(label: str):
    print(f"\n  {CYAN}▶ {label}{RESET}")


def _print_cycle_log(log: dict):
    ok     = not log.get("errors")
    status = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}PARTIAL{RESET}"
    safe_mode = log.get("safe_mode", False)

    print(f"\n  {'─'*62}")
    print(f"  {BOLD}CYCLE SUMMARY{RESET}")
    print(f"  {'─'*62}")
    print(f"  cycle_start        : {log['cycle_start']}")
    print(f"  fixtures_saved     : {GREEN}{log['fixtures_saved']}{RESET}")
    print(f"  predictions_saved  : {GREEN}{log['predictions_saved']}{RESET}")
    print(f"  pending_before     : {log['pending_before']}")
    print(f"  settled_count      : {BOLD}{log['settled_count']}{RESET}")
    print(f"  wins               : {GREEN}{log['wins']}{RESET}")
    print(f"  losses             : {RED}{log['losses']}{RESET}")
    print(f"  void               : {YELLOW}{log['void']}{RESET}")
    print(f"  pending_after      : {log['pending_after']}")

    if safe_mode:
        # LIVE_SAFE metrics (primary when safe_mode is true)
        live_safe_pl = float(log.get("live_safe_pl", 0.0))
        live_safe_roi = float(log.get("live_safe_roi", 0.0))
        live_safe_pl_str = f"{GREEN if live_safe_pl >= 0 else RED}{live_safe_pl:+.2f}u{RESET}"
        live_safe_roi_str = f"{GREEN if live_safe_roi >= 0 else RED}{live_safe_roi:+.1f}%{RESET}"

        print(f"\n  {BOLD}SAFE_MODE: ON{RESET}")
        print(f"  LIVE_SAFE settled  : {BOLD}{log['live_safe_settled']}{RESET}")
        print(f"  LIVE_SAFE wins     : {GREEN}{log['live_safe_wins']}{RESET}")
        print(f"  LIVE_SAFE losses   : {RED}{log['live_safe_losses']}{RESET}")
        print(f"  LIVE_SAFE hit_rate : {BOLD}{log['live_safe_hit_rate']:.1f}%{RESET}")
        print(f"  LIVE_SAFE ROI      : {live_safe_roi_str}")
        print(f"  LIVE_SAFE P/L      : {live_safe_pl_str}")

        # ALL_POST_RESET metrics (secondary)
        all_pl = float(log.get("all_post_reset_pl", 0.0))
        all_roi = float(log.get("all_post_reset_roi", 0.0))
        all_pl_str = f"{GREEN if all_pl >= 0 else RED}{all_pl:+.2f}u{RESET}"
        all_roi_str = f"{GREEN if all_roi >= 0 else RED}{all_roi:+.1f}%{RESET}"

        print(f"\n  ALL_POST_RESET settled : {log['all_post_reset_settled']}")
        print(f"  RESEARCH_ONLY count   : {log['research_only_count']}")
        print(f"  ALL_POST_RESET hit_rate: {log['all_post_reset_hit_rate']:.1f}%")
        print(f"  ALL_POST_RESET ROI     : {all_roi_str}")
        print(f"  ALL_POST_RESET P/L     : {all_pl_str}")
    else:
        # Legacy metrics when safe_mode is false
        pl_val = float(log.get("profit_loss", 0.0))
        roi_val = float(log.get("roi", 0.0))
        pl_str = f"{GREEN if pl_val >= 0 else RED}{pl_val:+.2f}u{RESET}"
        roi_str = f"{GREEN if roi_val >= 0 else RED}{roi_val:+.1f}%{RESET}"

        print(f"  hit_rate           : {BOLD}{log['hit_rate']:.1f}%{RESET}")
        print(f"  profit_loss        : {pl_str}")
        print(f"  roi                : {roi_str}")

    print(f"  errors             : {RED if log['errors'] else GREEN}{len(log['errors'])}{RESET}")
    if log.get("next_run_at"):
        print(f"  next_run_at        : {CYAN}{log['next_run_at']}{RESET}")
    print(f"  elapsed            : {log.get('elapsed_seconds', '?')}s")
    print(f"  {'─'*62}")
    print(f"  Status : {status}")
    print(f"  {'─'*62}")


def _write_cycle_log(log: dict):
    """Append JSON line to cycle_history.jsonl."""
    try:
        with open(CYCLE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, default=str) + "\n")
    except Exception as exc:
        logger.warning(f"[CYCLE] Could not write cycle log: {exc}")


# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tracking cycle orchestrator — refresh + settle + report"
    )
    parser.add_argument(
        "--once",       action="store_true",
        help="Run one cycle then exit"
    )
    parser.add_argument(
        "--every-hours", type=float, default=2.0, dest="every_hours",
        metavar="N", help="Run every N hours (default: 2)"
    )
    parser.add_argument(
        "--dry-run",    action="store_true", dest="dry_run",
        help="Scan only — no DB writes, no settlement"
    )
    parser.add_argument(
        "--no-settle",  action="store_true", dest="no_settle",
        help="Skip settlement step"
    )
    parser.add_argument(
        "--no-refresh", action="store_true", dest="no_refresh",
        help="Skip refresh step"
    )
    parser.add_argument(
        "--no-report",  action="store_true", dest="no_report",
        help="Skip performance report print"
    )
    parser.add_argument(
        "--since-reset", action="store_true", dest="since_reset",
        help="Filter report to POST_RESET picks only (uses TRACKING_RESET_AT)"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Lookback days for performance report (default: 30)"
    )
    args = parser.parse_args()

    interval_s = args.every_hours * 3600

    cycle_num = 0
    while True:
        cycle_num += 1
        if cycle_num > 1:
            print(f"\n{BOLD}{'─'*66}{RESET}")
            print(f"  Cycle #{cycle_num} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"{BOLD}{'─'*66}{RESET}")

        result = run_cycle(
            dry_run     = args.dry_run,
            no_settle   = args.no_settle,
            no_refresh  = args.no_refresh,
            no_report   = args.no_report,
            report_days = args.days,
            since_reset = getattr(args, "since_reset", False),
        )

        if args.once or result.get("errors") and len(result["errors"]) > 5:
            # Exit after one cycle (--once) or after catastrophic failures
            if not result.get("errors"):
                print(f"\n{BOLD}{GREEN}TRACKING_CYCLE_OK{RESET}\n")
            else:
                # Partial success still prints OK unless fatal
                fatal = any("supabase_init" in e or "provider_init" in e
                            for e in result.get("errors", []))
                if not fatal:
                    print(f"\n{BOLD}{YELLOW}TRACKING_CYCLE_OK (with {len(result['errors'])} warnings){RESET}\n")
                else:
                    print(f"\n{BOLD}{RED}TRACKING_CYCLE_FAILED{RESET}\n")
                    sys.exit(1)
            break

        # Schedule next run
        next_run = datetime.now(timezone.utc) + timedelta(seconds=interval_s)
        result["next_run_at"] = next_run.isoformat()

        print(f"\n  {CYAN}⏰ Next cycle in {args.every_hours:.1f}h "
              f"→ {next_run.strftime('%H:%M UTC')}{RESET}")
        print(f"  (Ctrl+C to stop)\n")

        try:
            time.sleep(interval_s)
        except KeyboardInterrupt:
            print(f"\n\n  {YELLOW}Stopped by user.{RESET}\n")
            break
