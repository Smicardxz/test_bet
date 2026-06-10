"""
pre_run_ev_check.py — Pre-Run EV Readiness Check (READ-ONLY)
=============================================================
Runs all prerequisite checks before a serious tracking cycle.
Answers: is the system ready for real EV exploitation today?

Usage:
    python pre_run_ev_check.py
    python pre_run_ev_check.py --date 2026-06-03
"""

import os
import sys
import argparse
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Console colors ────────────────────────────────────────────────────────────
G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def _ok(label: str, detail: str = "") -> None:
    print(f"  {G}✓{X}  {label:<50} {D}{detail}{X}")


def _warn(label: str, detail: str = "") -> None:
    print(f"  {Y}⚠{X}  {label:<50} {Y}{detail}{X}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  {R}✗{X}  {label:<50} {R}{detail}{X}")


def _info(label: str, detail: str = "") -> None:
    print(f"  {B}ℹ{X}  {label:<50} {D}{detail}{X}")


def sec(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 60}")


# ─── Individual checks ─────────────────────────────────────────────────────────

def check_env() -> dict:
    """Check required environment variables."""
    sec("ENV VARIABLES")
    results = {}

    supabase_url  = os.environ.get("SUPABASE_URL", "")
    supabase_key  = os.environ.get("SUPABASE_KEY", "")
    api_football  = os.environ.get("API_FOOTBALL_KEY", "")
    odds_api      = os.environ.get("ODDS_API_KEY", "")
    reset_at      = os.environ.get("TRACKING_RESET_AT", "")

    if supabase_url and supabase_key:
        _ok("SUPABASE_URL + SUPABASE_KEY", supabase_url[:40] + "...")
        results["supabase_env"] = True
    else:
        _fail("SUPABASE_URL / SUPABASE_KEY manquant")
        results["supabase_env"] = False

    if api_football:
        _ok("API_FOOTBALL_KEY", "configuré")
        results["api_football_key"] = True
    else:
        _warn("API_FOOTBALL_KEY absent", "fixtures non récupérables")
        results["api_football_key"] = False

    if odds_api:
        _ok("ODDS_API_KEY", "configuré — EV réel activé")
        results["odds_api_key"] = True
    else:
        _warn("ODDS_API_KEY absent", "EV réel désactivé — tracking statistique seulement")
        results["odds_api_key"] = False

    if reset_at:
        _ok("TRACKING_RESET_AT", reset_at)
        results["tracking_reset_at"] = reset_at
    else:
        _info("TRACKING_RESET_AT non défini", "rapport sur toutes les données historiques")
        results["tracking_reset_at"] = ""

    return results


def check_supabase() -> dict:
    """Check Supabase connection and settlement readiness."""
    sec("SUPABASE CONNECTION + SETTLEMENT")
    results = {}

    try:
        from app.database.supabase_config import get_supabase_config
        cfg = get_supabase_config()
        if cfg.supabase_connected:
            _ok("Supabase connected")
            results["supabase_ok"] = True
        else:
            _fail("Supabase non connecté", str(cfg.supabase_error or ""))
            results["supabase_ok"] = False
            return results
    except Exception as exc:
        _fail("Supabase import error", str(exc))
        results["supabase_ok"] = False
        return results

    try:
        from app.database.supabase_repository import get_repository
        repo = get_repository()
        pending = repo.get_pending_count()
        _ok("Repository OK", f"{pending} predictions PENDING à régler")
        results["pending_count"] = pending
        results["settlement_ok"] = True
    except Exception as exc:
        _warn("Repository / settlement non testable", str(exc))
        results["settlement_ok"] = False

    return results


def check_today_fixtures(target_date: str) -> dict:
    """Fetch today's fixtures and check volumes."""
    sec(f"FIXTURES DU JOUR — {target_date}")
    results = {"total_fixtures": 0, "bettable": 0, "limited": 0, "research": 0}

    api_key = os.environ.get("API_FOOTBALL_KEY", "")
    api_url = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")

    if not api_key:
        _warn("API_FOOTBALL_KEY absent", "vérification des fixtures ignorée")
        return results

    try:
        import requests
        resp = requests.get(
            f"{api_url}/fixtures",
            params={"date": target_date, "timezone": "UTC"},
            headers={"x-apisports-key": api_key},
            timeout=12,
        )
        resp.raise_for_status()
        fixtures = resp.json().get("response", [])
        total = len(fixtures)
        results["total_fixtures"] = total
        results["raw_fixtures"] = fixtures

        if total >= 30:
            _ok(f"Volume fixtures suffisant", f"{total} matchs")
        elif total >= 10:
            _warn(f"Volume fixtures faible", f"{total} matchs (cible ≥ 30)")
        else:
            _fail(f"Volume fixtures très bas", f"{total} matchs")

    except Exception as exc:
        _fail("Erreur API-Football", str(exc))
        return results

    # Classify fixtures
    try:
        from app.services.targeting.league_targeting_service import LeagueTargetingService
        svc = LeagueTargetingService()
        bettable = limited = research = 0
        leagues_bettable = []

        for fix in fixtures[:200]:
            lg_obj  = fix.get("league", {})
            league  = lg_obj.get("name", "?")
            country = lg_obj.get("country", "?")
            profile = svc.analyze_competition(league, country)
            prio    = profile.coverage_priority
            if prio == "A":
                bettable += 1
                leagues_bettable.append(f"{country} — {league}")
            elif prio == "B":
                limited += 1
            else:
                research += 1

        results["bettable"] = bettable
        results["limited"]  = limited
        results["research"] = research

        if bettable >= 10:
            _ok(f"Fixtures BETTABLE (PRIORITY_A)", f"{bettable}")
        elif bettable >= 3:
            _warn(f"Fixtures BETTABLE faibles", f"{bettable}  (cible ≥ 10)")
        else:
            _fail(f"Fixtures BETTABLE insuffisants", f"{bettable}")

        _info(f"Fixtures LIMITED (PRIORITY_B)", f"{limited}")
        _info(f"Fixtures RESEARCH_ONLY (PRIORITY_C)", f"{research}")

        if leagues_bettable:
            print(f"\n    {G}Ligues BETTABLE candidates :{X}")
            for lg in sorted(set(leagues_bettable))[:12]:
                print(f"      {D}{lg}{X}")

    except Exception as exc:
        _warn("Classification LeagueTargetingService", str(exc))

    return results


def check_odds_coverage() -> dict:
    """Check The Odds API event count."""
    sec("ODDS API COVERAGE")
    results = {"odds_events": 0, "odds_api_ok": False}

    odds_key = os.environ.get("ODDS_API_KEY", "")
    odds_url = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")

    if not odds_key:
        _warn("ODDS_API_KEY absent", "EV réel impossible — tracking statistique seulement")
        results["reason"] = "MISSING_KEY"
        return results

    try:
        import requests
        from app.providers.odds.external_odds_provider import SOCCER_SPORT_KEYS
        total = 0
        sport_count = 0
        quota_remaining = None

        # Check a few key sport keys
        priority_keys = [
            "soccer_japan_j_league", "soccer_sweden_allsvenskan",
            "soccer_norway_eliteserien", "soccer_poland_ekstraklasa",
            "soccer_brazil_campeonato", "soccer_denmark_superliga",
        ]
        for sk in priority_keys:
            try:
                r = requests.get(
                    f"{odds_url}/sports/{sk}/odds",
                    params={"regions": "eu", "markets": "totals", "oddsFormat": "decimal"},
                    headers={"x-api-key": odds_key},
                    timeout=6,
                )
                qr = r.headers.get("x-requests-remaining")
                if qr:
                    quota_remaining = int(qr)
                if r.status_code == 200:
                    events = r.json() or []
                    if events:
                        total += len(events)
                        sport_count += 1
                        print(f"    {G}✓{X}  {sk:<45} {len(events)} events")
                    else:
                        print(f"    {Y}−{X}  {sk:<45} 0 events today")
                elif r.status_code == 422:
                    print(f"    {D}−{X}  {sk:<45} not listed today")
            except Exception:
                pass

        results["odds_events"]   = total
        results["quota_remaining"] = quota_remaining

        if quota_remaining is not None:
            qcol = G if quota_remaining > 50 else (Y if quota_remaining > 10 else R)
            _info("Quota Odds API restant", f"{qcol}{quota_remaining}{X}")

        if total >= 10:
            _ok("Volume odds suffisant", f"{total} events sur {sport_count} sports")
            results["odds_api_ok"] = True
        elif total >= 1:
            _warn("Volume odds faible", f"{total} events")
            results["odds_api_ok"] = True
        else:
            _warn("Aucun event odds trouvé", "journée creuse ou clé quota épuisé")
            results["reason"] = "NO_EV_MARKET_AVAILABLE_TODAY"

    except Exception as exc:
        _fail("Odds API erreur", str(exc))

    return results


def check_market_diversity(fixtures_result: dict) -> dict:
    """Estimate market diversity from bettable fixture count."""
    sec("DIVERSITÉ DES MARCHÉS")
    bettable = fixtures_result.get("bettable", 0)
    results = {}

    # Each BETTABLE fixture can generate ~3-5 markets (FT_UNDER/OVER, HT, BTTS)
    est_markets = bettable * 3
    results["estimated_markets"] = est_markets
    results["market_diversity_ok"] = est_markets >= 3

    if est_markets >= 15:
        _ok("Diversité marchés estimée", f"~{est_markets} candidats (≥3 types)")
    elif est_markets >= 6:
        _warn("Diversité marchés limitée", f"~{est_markets} candidats")
    elif bettable == 0:
        _fail("Aucun match BETTABLE → 0 marché exploitable")
    else:
        _warn("Diversité très faible", f"~{est_markets} candidats")

    return results


def check_reset_filter() -> dict:
    """Verify TRACKING_RESET_AT filter is operational."""
    sec("TRACKING RESET FILTER")
    results = {}
    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()

    if reset_at:
        _ok("TRACKING_RESET_AT configuré", reset_at)
        _ok("Rapport filtré depuis", reset_at)
        _info("Commande", "python scripts/performance_report.py --since-reset")
        results["reset_filter_ok"] = True
        results["reset_date"] = reset_at
    else:
        _warn("TRACKING_RESET_AT non défini",
              "ajouter dans .env : TRACKING_RESET_AT=2026-06-02T08:00:00Z")
        _info("Commande", "python scripts/performance_report.py --days 1")
        results["reset_filter_ok"] = False

    return results


# ─── Main ──────────────────────────────────────────────────────────────────────

def run(target_date: str) -> bool:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 60}")
    print(f"  {BLD}PRE-RUN EV CHECK — {target_date}  ({now_str}){X}")
    print(f"{'═' * 60}")

    # Run checks
    env_r      = check_env()
    sb_r       = check_supabase()
    fix_r      = check_today_fixtures(target_date)
    odds_r     = check_odds_coverage()
    mkt_r      = check_market_diversity(fix_r)
    reset_r    = check_reset_filter()

    # ── Final verdict ──────────────────────────────────────────────────────────
    total_fx   = fix_r.get("total_fixtures", 0)
    bettable   = fix_r.get("bettable", 0)
    odds_ok    = odds_r.get("odds_api_ok", False)
    odds_ev    = odds_r.get("odds_events", 0)
    supabase_ok = sb_r.get("supabase_ok", False)
    mkt_ok     = mkt_r.get("market_diversity_ok", False)
    reset_ok   = reset_r.get("reset_filter_ok", False)

    ready = (
        supabase_ok
        and env_r.get("api_football_key", False)
        and total_fx >= 30
        and bettable >= 10
        and odds_ev >= 5
        and mkt_ok
    )

    print(f"\n{'═' * 60}")
    print(f"  {BLD}VERDICT FINAL{X}")
    print(f"{'═' * 60}\n")

    checks = [
        (supabase_ok,                         "Supabase OK"),
        (env_r.get("api_football_key", False), "API-Football KEY"),
        (total_fx >= 30,                      f"Fixtures today ({total_fx} / 30)"),
        (bettable >= 10,                      f"BETTABLE fixtures ({bettable} / 10)"),
        (odds_ev >= 5,                        f"Odds events ({odds_ev} / 5)"),
        (mkt_ok,                              "Market diversity ≥ 3 types"),
        (reset_ok,                            "Report reset filter actif"),
    ]

    for ok, label in checks:
        sym = f"{G}✓{X}" if ok else f"{R}✗{X}"
        print(f"  {sym}  {label}")

    print()

    if ready:
        print(f"  {G}{BLD}READY_FOR_SERIOUS_RUN = true{X}")
        print(f"\n  Commande :")
        print(f"  {C}python start.py --cycle-hours 2{X}")
    else:
        print(f"  {R}{BLD}READY_FOR_SERIOUS_RUN = false{X}")

        # Specific diagnosis
        if odds_ev == 0 and not odds_r.get("odds_api_ok", False):
            if not env_r.get("odds_api_key", False):
                print(f"\n  {Y}→ ODDS_API_KEY manquant.{X}")
                print(f"  {Y}   Ajouter ODDS_API_KEY dans .env pour activer l'EV réel.{X}")
            else:
                print(f"\n  {R}→ NO_EV_MARKET_AVAILABLE_TODAY{X}")
                print(f"  {R}   Aucun odds trouvé sur les ligues BETTABLE ce jour.{X}")
                print(f"  {R}   Ce n'est PAS un problème de modèle — c'est le calendrier.{X}")

        if bettable < 10 and total_fx > 0:
            print(f"\n  {Y}→ Peu de matchs BETTABLE ({bettable}).{X}")
            print(f"  {Y}   Journée dominée par les ligues RESEARCH_ONLY.{X}")
            print(f"  {Y}   Retry demain ou en weekend.{X}")

        if total_fx < 30:
            print(f"\n  {Y}→ Volume de matchs insuffisant ({total_fx}).{X}")
            print(f"  {Y}   Journée creuse — tracking statistique OK mais EV limité.{X}")

        if not reset_ok:
            print(f"\n  {D}→ Pour un rapport propre, ajouter dans .env :{X}")
            print(f"  {C}   TRACKING_RESET_AT={date.today().isoformat()}T08:00:00Z{X}")

        print(f"\n  {D}Quand même lancer le tracking statistique :{X}")
        print(f"  {C}python start.py --cycle-hours 2{X}")
        print(f"  {D}(Les prédictions seront sauvegardées même sans odds réels){X}")

    print(f"\n  {'─'*58}")
    print(f"  {D}Audit complet : python audit_today_market_availability.py{X}")
    print(f"  {D}Distribution  : python audit_targeting_distribution.py{X}")
    print(f"  {D}Universe      : python audit_bettable_universe.py{X}")
    print(f"{'═' * 60}\n")

    return ready


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-run EV readiness check")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date ISO à vérifier (default: today)")
    args = parser.parse_args()
    ready = run(args.date)
    sys.exit(0 if ready else 1)
