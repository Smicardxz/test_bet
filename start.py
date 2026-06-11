"""
start.py — Lance tout en une commande
======================================
Démarre en parallèle :
  • Flask dashboard    → http://localhost:5000
  • Tracking cycle     → toutes les 2h (thread background)

Usage :
    python start.py                    # dashboard + cycle 2h
    python start.py --no-cycle         # dashboard seul
    python start.py --cycle-hours 1    # cycle toutes les heures
    python start.py --port 5001        # dashboard sur un autre port
    python start.py --dry-run          # scan uniquement, pas d'écriture DB
"""

import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(override=True)

# ── Couleurs console ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

logging.basicConfig(
    level=logging.WARNING,          # masquer les logs verbeux en mode start
    format="%(levelname)s [%(name)s] %(message)s",
)


# =============================================================================
# Thread : Telegram Shadow Copilot
# =============================================================================

def _telegram_configured() -> bool:
    """True only if both Telegram credentials are present and alerts are enabled."""
    return bool(
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        and os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        and os.environ.get("SHADOW_ALERTS_ENABLED", "true").lower() == "true"
    )


def _run_telegram_copilot() -> None:
    """Single copilot run: new bets + settlements + divergences + morning report."""
    if not _telegram_configured():
        return

    try:
        from scripts.telegram_shadow_copilot import (
            _fetch_data,
            _generate_shadow_predictions,
            _generate_experimental_picks,
            _build_portfolio_all,
            _compute_bankroll_series,
            _do_daily_report,
            _do_new_bets,
            _do_settlements,
            _do_divergences,
        )
    except Exception as exc:
        print(f"  {YELLOW}[TELEGRAM] import error: {exc}{RESET}")
        return

    try:
        rows, fixture_lookup = _fetch_data()
        shadow_preds   = _generate_shadow_predictions(rows, fixture_lookup)
        exp_picks      = _generate_experimental_picks(rows, fixture_lookup)
        portfolio      = _build_portfolio_all(shadow_preds, exp_picks)
        current_bk, _ = _compute_bankroll_series(portfolio)

        counters = {
            "daily_reports_sent":     0,
            "new_bet_alerts_sent":    0,
            "settlement_alerts_sent": 0,
            "divergence_alerts_sent": 0,
            "skipped_duplicates":     0,
            "skipped_missing_config": 0,
        }

        # Daily report only during morning window (06:00–10:00 UTC)
        if 6 <= datetime.now(timezone.utc).hour < 10:
            _do_daily_report(portfolio, fixture_lookup, False, counters)

        _do_new_bets(portfolio, current_bk, False, counters)
        _do_settlements(portfolio, fixture_lookup, False, counters)
        _do_divergences(rows, portfolio, fixture_lookup, False, counters)

        sent = (
            counters["daily_reports_sent"]
            + counters["new_bet_alerts_sent"]
            + counters["settlement_alerts_sent"]
            + counters["divergence_alerts_sent"]
        )
        if sent:
            print(
                f"  {CYAN}[TELEGRAM]{RESET} "
                f"daily={counters['daily_reports_sent']} "
                f"new_bets={counters['new_bet_alerts_sent']} "
                f"settlements={counters['settlement_alerts_sent']} "
                f"divergences={counters['divergence_alerts_sent']}"
            )
    except Exception as exc:
        print(f"  {YELLOW}[TELEGRAM] run error: {exc}{RESET}")


def _telegram_thread(interval_minutes: float = 30.0) -> None:
    """Background thread: run Telegram copilot every N minutes."""
    time.sleep(20)          # let Flask + DB settle first
    while True:
        _run_telegram_copilot()
        time.sleep(interval_minutes * 60)


# =============================================================================
# Thread : tracking cycle
# =============================================================================

def _cycle_thread(interval_hours: float, dry_run: bool, report_days: int, since_reset: bool = False):
    """Boucle infinie : run_cycle() toutes les N heures."""
    # Attendre que Flask soit prêt
    time.sleep(5)

    from scripts.run_tracking_cycle import run_cycle

    while True:
        try:
            run_cycle(
                dry_run     = dry_run,
                no_report   = False,
                report_days = report_days,
                since_reset = since_reset,
            )
        except Exception as exc:
            print(f"\n  {YELLOW}[CYCLE ERROR] {exc}{RESET}")

        print(f"  {CYAN}[CYCLE] Prochain cycle dans {interval_hours:.1f}h{RESET}")
        time.sleep(interval_hours * 3600)


# =============================================================================
# Entrypoint
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Lance dashboard + cycle en une commande")
    parser.add_argument("--port",         type=int,   default=5000)
    parser.add_argument("--cycle-hours",  type=float, default=2.0,  dest="cycle_hours")
    parser.add_argument("--days",         type=int,   default=7,
                        help="Fenêtre d'analyse du rapport (défaut: 7 jours)")
    parser.add_argument("--no-cycle",     action="store_true",       dest="no_cycle")
    parser.add_argument("--dry-run",      action="store_true",       dest="dry_run")
    parser.add_argument("--since-reset",  action="store_true",       dest="since_reset",
                        help="Rapport filtré sur TRACKING_RESET_AT (POST_RESET uniquement)")
    parser.add_argument("--no-telegram",  action="store_true",       dest="no_telegram",
                        help="Désactiver le thread Telegram copilot")
    args = parser.parse_args()

    # Auto-enable since_reset when TRACKING_RESET_AT is set in .env
    if not args.since_reset and os.environ.get("TRACKING_RESET_AT", "").strip():
        args.since_reset = True

    # ── Bannière ──────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*58}{RESET}")
    print(f"{BOLD}  BETTING TRACKER — démarrage{RESET}")
    print(f"{'='*58}")
    print(f"  {GREEN}Dashboard{RESET}   -> http://localhost:{args.port}")
    if not args.no_cycle:
        sr_label = "  [POST_RESET ONLY]" if args.since_reset else ""
        print(f"  {GREEN}Cycle auto{RESET}  -> toutes les {args.cycle_hours:.1f}h  |  rapport sur {args.days}j{sr_label}")
    if args.dry_run:
        print(f"  {YELLOW}Mode DRY-RUN — pas d'écriture DB{RESET}")
    
    # EVENT_MODE status
    event_mode_enabled = os.getenv('EVENT_MODE_ENABLED', 'false').lower() == 'true'
    if event_mode_enabled:
        print(f"  {GREEN}Event Mode{RESET}   -> enabled")
        print(f"  {CYAN}World Cup / Friendlies tracked separately{RESET}")
    else:
        print(f"  {YELLOW}Event Mode{RESET}   -> disabled")
    
    print(f"{'='*58}\n")
    print(f"  Ctrl+C pour arrêter\n")

    # ── Thread cycle ──────────────────────────────────────────────────────────
    if not args.no_cycle:
        t = threading.Thread(
            target   = _cycle_thread,
            args     = (args.cycle_hours, args.dry_run, args.days, args.since_reset),
            daemon   = True,       # s'arrête avec le process principal
            name     = "TrackingCycle",
        )
        t.start()

    # ── Thread Telegram copilot ───────────────────────────────────────────────
    if not args.no_telegram:
        tg_status = f"{GREEN}configured{RESET}" if _telegram_configured() else f"{YELLOW}keys not set — will skip silently{RESET}"
        print(f"  {CYAN}Telegram{RESET}    -> {tg_status}")
        tg = threading.Thread(
            target = _telegram_thread,
            args   = (30.0,),
            daemon = True,
            name   = "TelegramCopilot",
        )
        tg.start()

    # ── Flask (thread principal) ───────────────────────────────────────────────
    from app_flask import app as flask_app
    flask_app.run(
        debug        = False,      # désactiver debug pour éviter double-process
        use_reloader = False,
        host         = "0.0.0.0",
        port         = args.port,
        threaded     = True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Arrêté.{RESET}\n")
        sys.exit(0)
