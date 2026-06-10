"""
audit_overlap_fix.py — Phase 4 Validation
==========================================
Verifies that ODDS_FIRST_MODE fix resolves the overlap problem.

Success conditions:
  - overlap_percent > 50%
  - ev_candidate_count > 0

READ-ONLY. No writes, no DB, no side effects.

Usage:
    python audit_overlap_fix.py
    python audit_overlap_fix.py --date 2026-06-03
"""

import os
import sys
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

G   = "\033[92m"
Y   = "\033[93m"
R   = "\033[91m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"


def run(target_date: str) -> dict:
    print(f"\n{'═' * 66}")
    print(f"  {BLD}AUDIT OVERLAP FIX — ODDS_FIRST_MODE — {target_date}{X}")
    print(f"{'═' * 66}\n")

    API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
    ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
    API_URL  = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    ODDS_URL = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")

    # ── Build OddsProviderManager ──────────────────────────────────────────────
    from app.providers.odds.odds_provider_manager import OddsProviderManager
    mgr = OddsProviderManager(
        apifootball_key=API_KEY, apifootball_url=API_URL,
        oddsapi_key=ODDS_KEY, oddsapi_url=ODDS_URL,
    )
    mgr.prefetch_for_matches([])

    apifb_cache: dict = getattr(mgr._apifb, "_fixture_cache", {})
    n_odds_fixtures = len(apifb_cache)
    print(f"  API-Football fixtures with odds : {C}{n_odds_fixtures}{X}")

    # ── Run scanner ────────────────────────────────────────────────────────────
    from app.providers.data_source_manager import DataSourceManager
    from app.services.scanner.smart_scanner import SmartScanner

    dsm     = DataSourceManager()
    scanner = SmartScanner(
        provider=dsm.provider,
        is_real_data=dsm.is_real_data,
        include_extreme_obscure=True,
        odds_provider=mgr,
    )
    result = scanner.scan_today()

    analyzed_all = result.get("analyzed_matches") or []
    diag         = result.get("odds_first_mode_diagnostics") or {}

    n_analyzed       = len(analyzed_all)
    n_with_odds      = diag.get("analyzed_with_odds",    0)
    n_without_odds   = diag.get("analyzed_without_odds", 0)
    n_odds_not_anlyz = diag.get("odds_not_analyzed",     0)

    print(f"  Scanner analyzed total          : {C}{n_analyzed}{X}")
    print(f"  Analyzed WITH odds              : {G if n_with_odds > 0 else R}{n_with_odds}{X}")
    print(f"  Analyzed WITHOUT odds           : {D}{n_without_odds}{X}")
    print(f"  Odds available but not analyzed : {Y if n_odds_not_anlyz > 0 else G}{n_odds_not_anlyz}{X}\n")

    overlap_pct = n_with_odds / max(n_odds_fixtures, 1) * 100

    # ── EV candidates ─────────────────────────────────────────────────────────
    ev_candidates = 0
    ev_details    = []
    for m in analyzed_all:
        an = m.get("analysis", {}) or {}
        best_ev = an.get("best_ev_opportunity")
        if best_ev and best_ev.get("expected_value", 0) > 0:
            ev_candidates += 1
            ev_details.append({
                "fixture": f"{m.get('home_team','?')} vs {m.get('away_team','?')}",
                "market":  best_ev.get("market", "?"),
                "ev_pct":  round(best_ev.get("ev_percentage", 0), 2),
                "odd":     best_ev.get("bookmaker_odd", "?"),
                "source":  (an.get("matched_odds") or [{}])[0].get("source", "?")
                            if isinstance((an.get("matched_odds") or [{}])[0], dict)
                            else "?",
            })

    # ── Results table ──────────────────────────────────────────────────────────
    print(f"  {'Metric':<38}  {'Value':>10}  {'Status'}")
    print(f"  {'─'*38}  {'─'*10}  {'─'*15}")

    def row(label, val, ok_cond, fmt=str):
        col = G if ok_cond else R
        print(f"  {label:<38}  {col}{fmt(val):>10}{X}  {'OK' if ok_cond else 'FAIL'}")

    row("fixtures_with_odds",         n_odds_fixtures,  n_odds_fixtures > 0)
    row("analyzed_with_odds",         n_with_odds,      n_with_odds > 0)
    row("overlap_percent",            round(overlap_pct, 1), overlap_pct >= 50,
        lambda v: f"{v}%")
    row("ev_candidate_count",         ev_candidates,    ev_candidates > 0)

    # ── EV picks preview ──────────────────────────────────────────────────────
    if ev_details:
        print(f"\n  {G}EV+ picks found:{X}")
        for d in ev_details[:10]:
            print(f"    {d['fixture'][:36]:<36}  {d['market']:<18}  "
                  f"ev={G}{d['ev_pct']:+.1f}%{X}  odd={d['odd']}  src={C}{d['source']}{X}")
    else:
        print(f"\n  {Y}No EV+ picks yet — model prob < bookmaker implied prob on available fixtures.{X}")
        # Show best near-miss
        near_misses = []
        for m in analyzed_all:
            an = m.get("analysis", {}) or {}
            ev_opps = an.get("ev_opportunities") or []
            for opp in ev_opps:
                ev_pct = opp.get("ev_percentage", 0) if isinstance(opp, dict) else getattr(opp, "expected_value_percent", 0)
                near_misses.append({
                    "fixture": f"{m.get('home_team','?')} vs {m.get('away_team','?')}",
                    "market":  opp.get("market", "?") if isinstance(opp, dict) else opp.market_type,
                    "ev_pct":  ev_pct,
                })
        near_misses.sort(key=lambda x: -x["ev_pct"])
        if near_misses:
            print(f"\n  {D}Best near-miss EV (all, even negative):{X}")
            for nm in near_misses[:5]:
                col = G if nm["ev_pct"] > 0 else Y
                print(f"    {nm['fixture'][:36]:<36}  {nm['market']:<18}  "
                      f"ev={col}{nm['ev_pct']:+.1f}%{X}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    success = (overlap_pct >= 50) and (ev_candidates > 0)
    print(f"\n{'─' * 66}")
    if overlap_pct >= 50 and ev_candidates > 0:
        print(f"  {BLD}{G}OVERLAP_FIX_OK  — ODDS_FIRST_MODE working correctly{X}")
    elif overlap_pct >= 50:
        print(f"  {BLD}{Y}OVERLAP_FIX_PARTIAL  — Overlap OK but EV still 0{X}")
        print(f"  {D}→ Model probability < implied probability on these fixtures.{X}")
        print(f"  {D}→ This is a correct result: no edge detected today.{X}")
    else:
        print(f"  {BLD}{R}OVERLAP_FIX_FAILED  — Overlap still insufficient{X}")
        print(f"  {D}→ Fixtures may have <4 historical matches total (MISSING, not INSUFFICIENT).{X}")
        print(f"  {D}→ Only INSUFFICIENT status is relaxed; MISSING (0 matches) cannot proceed.{X}")
    print(f"{'═' * 66}\n")

    return {
        "success":          success,
        "overlap_percent":  round(overlap_pct, 1),
        "ev_candidate_count": ev_candidates,
        "analyzed_with_odds":  n_with_odds,
        "fixtures_with_odds":  n_odds_fixtures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit ODDS_FIRST_MODE overlap fix")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    result = run(target_date=args.date)
    sys.exit(0 if result["success"] else 1)
