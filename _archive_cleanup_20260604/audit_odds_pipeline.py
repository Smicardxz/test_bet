"""
audit_odds_pipeline.py — Phase 7 Validation
=============================================
Validates the full odds pipeline end-to-end.

Displays:
  - Fixtures today (API-Football)
  - Odds from API-Football
  - Odds from The Odds API
  - Coverage %
  - Matched odds per provider
  - EV-eligible picks (fixtures with odds + signal)
  - Top leagues with odds

Success conditions:
  - coverage > 30%
  - ev_eligible_picks > 0

Usage:
    python audit_odds_pipeline.py
    python audit_odds_pipeline.py --date 2026-06-03
    python audit_odds_pipeline.py --no-scan   (skip scanner, odds-only check)
"""

import os
import sys
import argparse
import time
from collections import defaultdict
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def sec(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 70}")


def ok(msg: str) -> None:
    print(f"  {G}✓{X}  {msg}")


def warn(msg: str) -> None:
    print(f"  {Y}⚠{X}  {msg}")


def err(msg: str) -> None:
    print(f"  {R}✗{X}  {msg}")


def pct(n: int, d: int) -> str:
    return f"{n/d*100:.1f}%" if d else "N/A"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def fetch_fixtures(target_date: str) -> list:
    api_key = os.environ.get("API_FOOTBALL_KEY", "")
    api_url = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    if not api_key:
        return []
    import requests
    try:
        r = requests.get(
            f"{api_url}/fixtures",
            params={"date": target_date, "timezone": "UTC"},
            headers={"x-apisports-key": api_key},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as exc:
        err(f"API-Football fixtures: {exc}")
        return []


# ─── Main audit ───────────────────────────────────────────────────────────────

def run(target_date: str, no_scan: bool = False) -> dict:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 70}")
    print(f"  {BLD}AUDIT ODDS PIPELINE — {target_date}  (run: {now_str}){X}")
    print(f"{'═' * 70}")

    results = {
        "success":           False,
        "fixtures_today":    0,
        "odds_apifootball":  0,
        "odds_oddsapi":      0,
        "coverage_pct":      0.0,
        "ev_eligible_picks": 0,
        "errors":            [],
    }

    # ─── STEP 1 — Keys ────────────────────────────────────────────────────────
    sec("STEP 1 — KEY STATUS")

    API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
    API_URL  = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
    ODDS_URL = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")

    print()
    if API_KEY:
        ok(f"API_FOOTBALL_KEY present")
    else:
        err("API_FOOTBALL_KEY manquant — fixtures et odds API-Football désactivés")
        results["errors"].append("NO_API_FOOTBALL_KEY")

    if ODDS_KEY:
        ok(f"ODDS_API_KEY present")
    else:
        warn("ODDS_API_KEY absent — The Odds API désactivé")

    # ─── STEP 2 — Fixtures ────────────────────────────────────────────────────
    sec("STEP 2 — FIXTURES TODAY")

    fixtures = fetch_fixtures(target_date)
    n_fix = len(fixtures)
    results["fixtures_today"] = n_fix

    if n_fix == 0:
        err(f"Aucun fixture trouvé pour {target_date}")
        results["errors"].append("NO_FIXTURES")
    else:
        ok(f"{n_fix} fixtures trouvés")

    # Build fixture_id → fixture map
    fx_by_id: dict = {}
    for fix in fixtures:
        fid = str(fix.get("fixture", {}).get("id", ""))
        lg  = fix.get("league", {})
        teams = fix.get("teams", {})
        fx_by_id[fid] = {
            "league":  lg.get("name", "?"),
            "country": lg.get("country", "?"),
            "home":    teams.get("home", {}).get("name", "?"),
            "away":    teams.get("away", {}).get("name", "?"),
        }

    # ─── STEP 3 — Build OddsProviderManager ───────────────────────────────────
    sec("STEP 3 — ODDS PROVIDER MANAGER INIT")

    try:
        from app.providers.odds.odds_provider_manager import OddsProviderManager
        mgr = OddsProviderManager(
            apifootball_key=API_KEY,
            apifootball_url=API_URL,
            oddsapi_key=ODDS_KEY,
            oddsapi_url=ODDS_URL,
        )
        ok(f"OddsProviderManager créé — primary={'API_FOOTBALL' if API_KEY else 'ODDS_API'}")
    except Exception as exc:
        err(f"OddsProviderManager init failed: {exc}")
        results["errors"].append(f"OPM_INIT_FAILED: {exc}")
        _print_verdict(results)
        return results

    # ─── STEP 4 — Prefetch ────────────────────────────────────────────────────
    sec("STEP 4 — PREFETCH ODDS")

    t0 = time.time()
    try:
        match_list = [{"competition": d["league"], "country": d["country"]}
                      for d in fx_by_id.values()]
        mgr.prefetch_for_matches(match_list)
        elapsed = time.time() - t0
        ok(f"Prefetch terminé en {elapsed:.1f}s")
    except Exception as exc:
        err(f"Prefetch failed: {exc}")
        results["errors"].append(f"PREFETCH_FAILED: {exc}")

    # Sub-provider stats
    apifb_fixtures  = getattr(mgr._apifb,   "events_fetched", 0)
    oddsapi_events  = getattr(mgr._oddsapi,  "events_fetched", 0)
    results["odds_apifootball"] = apifb_fixtures
    results["odds_oddsapi"]     = oddsapi_events

    print()
    print(f"  API-Football /odds  : {C}{apifb_fixtures}{X} fixtures avec odds")
    print(f"  The Odds API        : {C}{oddsapi_events}{X} events chargés")

    if apifb_fixtures == 0 and oddsapi_events == 0:
        warn("Aucun odds chargé. Vérifier les clés API et le plan.")

    # ─── STEP 5 — Match odds per fixture ──────────────────────────────────────
    sec("STEP 5 — ODDS MATCHING PAR FIXTURE")

    matched_apifb   = 0
    matched_oddsapi = 0
    matched_none    = 0
    ev_eligible     = 0

    league_coverage: dict = defaultdict(lambda: {"total": 0, "with_odds": 0})

    for fid, fx in fx_by_id.items():
        odds, mapping = mgr.get_match_odds_normalized(
            match_id=fid,
            home_team=fx["home"],
            away_team=fx["away"],
        )
        lg = fx["league"]
        league_coverage[lg]["total"] += 1

        if odds:
            source = odds[0].source if odds else "unknown"
            league_coverage[lg]["with_odds"] += 1
            if source == "API_FOOTBALL":
                matched_apifb += 1
            else:
                matched_oddsapi += 1

            # EV-eligible: has at least FT_OVER or FT_UNDER odds
            has_ev_mkt = any(
                o.market.startswith(("FT_OVER", "FT_UNDER", "HT_OVER", "HT_UNDER", "BTTS"))
                for o in odds
            )
            if has_ev_mkt:
                ev_eligible += 1
        else:
            matched_none += 1

    total_matched = matched_apifb + matched_oddsapi
    coverage_pct  = total_matched / max(n_fix, 1) * 100
    results["odds_apifootball"]  = matched_apifb
    results["odds_oddsapi"]      = matched_oddsapi
    results["coverage_pct"]      = round(coverage_pct, 1)
    results["ev_eligible_picks"] = ev_eligible

    print()
    print(f"  Matched via API-Football : {G}{matched_apifb}{X}")
    print(f"  Matched via The Odds API : {G}{matched_oddsapi}{X}")
    print(f"  No odds                  : {Y if matched_none > 0 else G}{matched_none}{X}")
    print(f"  Total coverage           : {G if coverage_pct >= 30 else R}"
          f"{total_matched}/{n_fix}  ({coverage_pct:.1f}%){X}")
    print(f"  EV-eligible fixtures     : {G if ev_eligible > 0 else Y}{ev_eligible}{X}")

    # ─── STEP 6 — Top leagues with odds ───────────────────────────────────────
    sec("STEP 6 — TOP LEAGUES WITH ODDS")

    sorted_leagues = sorted(
        league_coverage.items(),
        key=lambda x: (-x[1]["with_odds"], -x[1]["total"])
    )
    print()
    print(f"  {'League':<38}  {'Total':>5}  {'WithOdds':>8}  {'Cov%':>5}")
    print(f"  {'─'*38}  {'─'*5}  {'─'*8}  {'─'*5}")
    for lg, d in sorted_leagues[:20]:
        cov = pct(d["with_odds"], d["total"])
        col = G if d["with_odds"] > 0 else D
        print(f"  {col}{lg:<38}{X}  {d['total']:>5}  {d['with_odds']:>8}  {cov:>5}")

    # ─── STEP 7 — Diagnostics ─────────────────────────────────────────────────
    sec("STEP 7 — PROVIDER DIAGNOSTICS")
    try:
        diag = mgr.get_diagnostics()
        print()
        print(f"  primary   : {G}{diag.get('odds_provider_primary', '?')}{X}")
        print(f"  secondary : {C}{diag.get('odds_provider_secondary', '?')}{X}")
        print(f"  status    : {diag.get('odds_provider_status', '?')}")
        apifb_bks = diag.get("apifootball", {}).get("bookmakers_available", [])
        if apifb_bks:
            print(f"  API-Football bookmakers : {', '.join(apifb_bks[:6])}")
        apifb_mkts = diag.get("apifootball", {}).get("markets_available", [])
        if apifb_mkts:
            print(f"  API-Football markets    : {', '.join(sorted(apifb_mkts)[:6])}")
    except Exception as exc:
        warn(f"Diagnostics non-disponibles: {exc}")

    # ─── STEP 8 — Scanner EV check (optional) ─────────────────────────────────
    if not no_scan and n_fix > 0 and total_matched > 0:
        sec("STEP 8 — SCANNER EV SPOT CHECK (3 fixtures)")
        try:
            from app.providers.data_source_manager import DataSourceManager
            from app.services.scanner.smart_scanner import SmartScanner

            dsm     = DataSourceManager()
            scanner = SmartScanner(
                provider=dsm.provider,
                is_real_data=dsm.is_real_data,
                include_extreme_obscure=True,
                odds_provider=mgr,
            )

            # Run a minimal scan (3 matches max for speed)
            scan_result = scanner.scan_today()
            analyzed = scan_result.get("analyzed_matches") or []

            ev_picks = [
                m for m in analyzed
                if m.get("analysis", {}).get("best_ev_opportunity")
                and m["analysis"]["best_ev_opportunity"].get("ev_percentage", 0) > 0
            ]
            results["ev_eligible_picks"] = len(ev_picks)
            print()
            ok(f"Scanner: {len(analyzed)} matchs analysés")
            if ev_picks:
                ok(f"{len(ev_picks)} picks EV+ trouvés")
                for pick in ev_picks[:3]:
                    bev = pick["analysis"]["best_ev_opportunity"]
                    an  = pick.get("analysis", {})
                    src = (an.get("matched_odds") or [{}])[0].get("source", "?")
                    print(f"    {pick.get('home_team','?')} vs {pick.get('away_team','?')}")
                    print(f"      market={bev.get('market','?')}  "
                          f"ev={bev.get('ev_percentage',0):.1f}%  "
                          f"odd={bev.get('bookmaker_odd','?')}  "
                          f"source={C}{src}{X}")
            else:
                warn("Aucun pick EV+ détecté (normal si odds insuffisants ou signal faible)")
        except Exception as exc:
            warn(f"Scanner check non-blocking: {exc}")
            results["errors"].append(f"SCANNER: {exc}")
    elif no_scan:
        print(f"\n  {D}(--no-scan: scanner check ignoré){X}")

    # ─── VERDICT ──────────────────────────────────────────────────────────────
    _print_verdict(results)
    return results


def _print_verdict(results: dict) -> None:
    sec("VERDICT")
    print()

    n_fix    = results["fixtures_today"]
    cov_pct  = results["coverage_pct"]
    ev_picks = results["ev_eligible_picks"]
    errors   = results["errors"]

    conditions = [
        (n_fix > 0,      f"Fixtures today > 0  ({n_fix})",            True),
        (cov_pct >= 30,  f"Coverage >= 30%     ({cov_pct:.1f}%)",     True),
        (ev_picks > 0,   f"EV eligible > 0     ({ev_picks} picks)",   True),
        (not errors,     f"No errors            ({len(errors)} found)", False),
    ]

    all_ok = True
    for passed, label, required in conditions:
        if passed:
            ok(label)
        elif required:
            err(label)
            all_ok = False
        else:
            warn(label)

    if errors:
        print(f"\n  {R}Erreurs:{X}")
        for e in errors:
            print(f"    {D}{e}{X}")

    results["success"] = all_ok
    print()
    if all_ok:
        print(f"  {BLD}{G}ODDS_PIPELINE_OK{X}")
    else:
        print(f"  {BLD}{R}ODDS_PIPELINE_NEEDS_ATTENTION{X}")
        if results["coverage_pct"] == 0:
            print(f"\n  {Y}Suggestions:{X}")
            print(f"    1. Vérifier que API_FOOTBALL_KEY est dans .env")
            print(f"    2. Vérifier que le plan API-Football inclut /odds")
            print(f"    3. Lancer d'abord : python audit_odds_sources.py")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit odds pipeline end-to-end")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date ISO (default: today)")
    parser.add_argument("--no-scan", action="store_true", dest="no_scan",
                        help="Skip scanner EV check (faster)")
    args = parser.parse_args()
    result = run(target_date=args.date, no_scan=args.no_scan)
    sys.exit(0 if result["success"] else 1)
