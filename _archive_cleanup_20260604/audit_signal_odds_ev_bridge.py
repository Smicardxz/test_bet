"""
audit_signal_odds_ev_bridge.py — READ-ONLY diagnostic
=======================================================
Diagnoses precisely why odds-covered fixtures produce 0 EV+ picks.

Phases:
  1 — Fixture overlap: analyzed vs odds-available
  2 — Market normalization audit (which markets land in odds_by_market?)
  3 — EV calculation path per signal
  4 — Failure reason count table
  5 — Top 20 EV comparisons (even if EV <= 0)
  6 — Final verdict with minimal correction suggestion

READ-ONLY: zero writes, zero DB calls, zero state changes.

Usage:
    python audit_signal_odds_ev_bridge.py
    python audit_signal_odds_ev_bridge.py --date 2026-06-03
    python audit_signal_odds_ev_bridge.py --max-fixtures 40
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
    print(f"\n{'═' * 72}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 72}")


def ok(msg: str)   -> None: print(f"  {G}✓{X}  {msg}")
def warn(msg: str) -> None: print(f"  {Y}⚠{X}  {msg}")
def err(msg: str)  -> None: print(f"  {R}✗{X}  {msg}")


# ─── Signal→market mapping (mirror of scanner, for inspection) ────────────────
_SIGNAL_MARKET_CANDIDATES = {
    "HT_UNDER":              ["HT_UNDER_0_5", "HT_UNDER_1_5"],
    "HT_OVER":               ["HT_OVER_0_5", "HT_OVER_1_0", "HT_OVER_1_5"],
    "FT_UNDER":              ["FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5"],
    "FT_OVER":               ["FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5"],
    "BTTS_YES":              ["BTTS_YES"],
    "BTTS_NO":               ["BTTS_NO"],
    "BTTS_PROFILE":          ["BTTS_YES"],
    "HOME_DOMINANT":         ["HOME_OVER_0_5"],
    "ASYMMETRIC_SCORING":    ["AWAY_OVER_0_5"],
    "SECOND_HALF_EXPLOSION": ["SECOND_HALF_OVER_1_5", "SECOND_HALF_OVER_0_5"],
    "EXTREME_UNDER":         ["FT_UNDER_1_5", "FT_UNDER_2_5"],
    "LOW_VARIANCE":          ["FT_UNDER_2_5", "FT_UNDER_1_5"],
}

# Markets our ApiFootballOddsProvider actually produces
_APIFB_POSSIBLE_MARKETS = {
    "FT_H2H_HOME", "FT_H2H_DRAW", "FT_H2H_AWAY",
    "FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5", "FT_OVER_4_5",
    "FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5", "FT_UNDER_4_5",
    "HT_OVER_0_5", "HT_OVER_1_5",
    "HT_UNDER_0_5", "HT_UNDER_1_5",
    "BTTS_YES", "BTTS_NO",
}

# Markets in _SIGNAL_MARKET_CANDIDATES that CANNOT come from ApiFootballOddsProvider
_GHOST_MARKETS = {
    "HT_OVER_1_0",            # not in allowed HT lines
    "HOME_OVER_0_5",          # not normalised at all
    "AWAY_OVER_0_5",          # not normalised at all
    "SECOND_HALF_OVER_1_5",   # not normalised at all
    "SECOND_HALF_OVER_0_5",   # not normalised at all
}


def _ev(model_prob: float, odd: float) -> float:
    return model_prob * odd - 1.0


def run(target_date: str, max_fixtures: int = 50) -> dict:
    t_start = time.time()
    print(f"\n{'═' * 72}")
    print(f"  {BLD}AUDIT SIGNAL ↔ ODDS ↔ EV BRIDGE — {target_date}{X}")
    print(f"{'═' * 72}")

    failures = defaultdict(int)
    ev_candidates = []

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 0 — Build OddsProviderManager + prefetch
    # ──────────────────────────────────────────────────────────────────────────
    API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
    ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
    API_URL  = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io").rstrip("/")
    ODDS_URL = os.environ.get("ODDS_API_URL", "https://api.the-odds-api.com/v4").rstrip("/")

    from app.providers.odds.odds_provider_manager import OddsProviderManager
    mgr = OddsProviderManager(
        apifootball_key=API_KEY, apifootball_url=API_URL,
        oddsapi_key=ODDS_KEY, oddsapi_url=ODDS_URL,
    )
    mgr.prefetch_for_matches([])

    # Build odds lookup: fixture_id → {market: odd}
    apifb_cache: dict = getattr(mgr._apifb, "_fixture_cache", {})
    fid_to_odds: dict = {}
    for fid, norms in apifb_cache.items():
        fid_to_odds[fid] = {n.market: n.odd for n in norms}

    apifb_fixtures = len(fid_to_odds)

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 1 — Run scanner (READ-ONLY — scan_today does not write anything)
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 1 — Fixture overlap: analyzed vs odds-available")

    from app.providers.data_source_manager import DataSourceManager
    from app.services.scanner.smart_scanner import SmartScanner

    dsm     = DataSourceManager()
    scanner = SmartScanner(
        provider=dsm.provider,
        is_real_data=dsm.is_real_data,
        include_extreme_obscure=True,
        odds_provider=mgr,
    )
    scan_result  = scanner.scan_today()
    analyzed_all = (scan_result.get("analyzed_matches") or []) + \
                   (scan_result.get("remaining_matches") or [])

    # Separate into analyzed (with analysis) and remaining (no analysis / insufficient)
    analyzed_with_analysis  = [m for m in analyzed_all if m.get("analysis")]
    analyzed_no_analysis    = [m for m in analyzed_all if not m.get("analysis")]

    # Build match_id sets
    analyzed_fids  = {str(m.get("match_id", "")) for m in analyzed_with_analysis}
    odds_fids      = set(fid_to_odds.keys())

    overlap           = analyzed_fids & odds_fids
    analyzed_no_odds  = analyzed_fids - odds_fids
    odds_not_analyzed = odds_fids - analyzed_fids

    print()
    print(f"  API-Football fixtures with odds  : {C}{apifb_fixtures:3d}{X}")
    print(f"  Scanner analyzed (with signals)  : {C}{len(analyzed_with_analysis):3d}{X}")
    print(f"  Scanner analyzed (no data/skip)  : {D}{len(analyzed_no_analysis):3d}{X}")
    print()

    col_overlap = G if overlap else R
    print(f"  Overlap  (analyzed AND has odds) : {col_overlap}{len(overlap):3d}{X}")
    print(f"  Analyzed WITHOUT odds            : {Y if analyzed_no_odds else G}{len(analyzed_no_odds):3d}{X}")
    print(f"  Odds available but NOT analyzed  : {Y if odds_not_analyzed else G}{len(odds_not_analyzed):3d}{X}")

    if not overlap:
        err("CRITICAL: Zero overlap — scanner analyzes different fixtures than those with odds!")
        err("Root cause: scanner filters by historical data; odds fixtures may be newly added.")
        failures["ODDS_FIXTURE_NOT_ANALYZED"] += apifb_fixtures
    else:
        ok(f"{len(overlap)} fixtures are both analyzed AND have odds")

    if odds_not_analyzed:
        print(f"\n  {Y}Fixtures with odds NOT analyzed (first 10):{X}")
        shown = 0
        for fid in list(odds_not_analyzed)[:10]:
            mkts = sorted(fid_to_odds[fid].keys())
            print(f"    fid={fid}  markets={mkts[:4]}")
            shown += 1

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2 — Market normalization audit
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 2 — Market normalization audit")

    print()
    print(f"  Scanner signal types mapped to market strings:")
    print(f"  {'Signal type':<28}  Candidates → {'Present in APIFB?':>18}")
    print(f"  {'─'*28}  {'─'*42}")

    all_candidate_markets: set = set()
    ghost_in_use: set = set()
    for sig_type, candidates in sorted(_SIGNAL_MARKET_CANDIDATES.items()):
        for mkt in candidates:
            all_candidate_markets.add(mkt)
            if mkt in _GHOST_MARKETS:
                ghost_in_use.add(mkt)
        coverage = [(m, m in _APIFB_POSSIBLE_MARKETS) for m in candidates]
        cov_str = ", ".join(
            f"{G}{m}{X}" if ok_flag else f"{R}{m}{X}"
            for m, ok_flag in coverage
        )
        print(f"  {sig_type:<28}  {cov_str}")

    print()
    if ghost_in_use:
        warn(f"Ghost markets (in scanner candidates but NEVER in API-Football output):")
        for m in sorted(ghost_in_use):
            print(f"    {R}{m}{X}  → scanner will always find bk_odd=None for these")
        failures["MARKET_NOT_AVAILABLE"] += len(ghost_in_use) * 10  # rough weight

    # Markets that ARE in APIFB output AND in scanner candidates
    viable_markets = all_candidate_markets & _APIFB_POSSIBLE_MARKETS
    print(f"\n  Viable markets (scanner candidate + APIFB possible) : {G}{len(viable_markets)}{X}")
    print(f"  {sorted(viable_markets)}")

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3 — EV calculation path per match in overlap
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 3 — EV calculation path (overlap fixtures)")

    print()

    overlap_matches = [
        m for m in analyzed_with_analysis
        if str(m.get("match_id", "")) in overlap
    ]

    if not overlap_matches:
        err("No overlap fixtures to analyse — skipping Phases 3-5")
        failures["ODDS_FIXTURE_NOT_ANALYZED"] += len(analyzed_with_analysis)
    else:
        ok(f"Checking EV path for {len(overlap_matches)} overlap fixtures")

    phase3_rows = []  # for Phase 5 preview
    MAX_P3 = min(max_fixtures, len(overlap_matches))

    for match in overlap_matches[:MAX_P3]:
        fid      = str(match.get("match_id", ""))
        home     = match.get("home_team", "?")
        away     = match.get("away_team", "?")
        league   = match.get("league") or match.get("competition", "?")
        analysis = match.get("analysis", {}) or {}

        # Signals from analysis
        signals_raw  = analysis.get("signals_with_value") or []
        odds_by_mkt  = {n.market: n.odd for n in (mgr._apifb._fixture_cache.get(fid) or [])}
        odds_by_mkt.update({n.market: n.odd
                            for events in getattr(mgr._oddsapi, "_event_cache", {}).values()
                            for n in []})  # OddsAPI handled below via analysis matched_odds

        # Also read from analysis.matched_odds (scanner already resolved them)
        for nd in (analysis.get("matched_odds") or []):
            mkt = nd.get("market") if isinstance(nd, dict) else getattr(nd, "market", None)
            odd = nd.get("odd") if isinstance(nd, dict) else getattr(nd, "odd", None)
            if mkt and odd:
                odds_by_mkt[mkt] = float(odd)

        available_markets = set(odds_by_mkt.keys())

        # Get EV opportunities already computed by scanner
        ev_opps = analysis.get("ev_opportunities") or []
        best_ev_opp = analysis.get("best_ev_opportunity")

        # Re-inspect signals
        for sig_dict in signals_raw:
            sig_type   = sig_dict.get("type", "")
            model_prob = float(sig_dict.get("confidence", 0))
            candidates = _SIGNAL_MARKET_CANDIDATES.get(sig_type, [])

            row = {
                "fixture":      f"{home} vs {away}",
                "fid":          fid,
                "league":       league[:30],
                "signal_type":  sig_type,
                "model_prob":   model_prob,
                "candidates":   candidates,
            }

            matched = False
            for mkt in candidates:
                bk_odd = odds_by_mkt.get(mkt)
                if bk_odd and bk_odd > 1.0:
                    impl_prob = 1.0 / bk_odd
                    ev        = _ev(model_prob, bk_odd)
                    edge      = model_prob - impl_prob

                    row.update({
                        "market":     mkt,
                        "bk_odd":     bk_odd,
                        "impl_prob":  impl_prob,
                        "edge_pct":   edge * 100,
                        "ev_pct":     ev * 100,
                        "ev_status":  "EV_POSITIVE" if ev > 0 else ("EV_NEGATIVE" if ev < -0.01 else "EV_NEUTRAL"),
                    })
                    matched = True
                    phase3_rows.append(row.copy())

                    if ev <= 0:
                        failures["EV_NEGATIVE"] += 1
                    else:
                        failures["EV_POSITIVE_FOUND"] += 1

                    break  # use first candidate with odds

            if not matched:
                # Diagnose why no odd was found
                if not candidates:
                    reason = "SIGNAL_NOT_IN_CANDIDATES"
                elif not available_markets:
                    reason = "BOOKMAKER_ODD_NULL"
                elif mkt in _GHOST_MARKETS:
                    reason = "MARKET_NAME_MISMATCH"
                else:
                    # Check if any candidate is in available_markets
                    any_in = any(c in available_markets for c in candidates)
                    reason = "MARKET_NOT_AVAILABLE" if not any_in else "BOOKMAKER_ODD_NULL"

                failures[reason] += 1
                row.update({
                    "market":    candidates[0] if candidates else "NONE",
                    "bk_odd":    None,
                    "ev_status": reason,
                })
                phase3_rows.append(row.copy())

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 4 — Failure reason table
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 4 — Failure reason count")

    print()
    total_signals = sum(failures.values())
    print(f"  {'Reason':<40}  {'Count':>5}  {'%':>5}")
    print(f"  {'─'*40}  {'─'*5}  {'─'*5}")
    for reason, cnt in sorted(failures.items(), key=lambda x: -x[1]):
        pct = cnt / max(total_signals, 1) * 100
        col = G if reason == "EV_POSITIVE_FOUND" else (R if cnt > 0 else D)
        print(f"  {col}{reason:<40}{X}  {cnt:>5}  {pct:>4.0f}%")

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 5 — Top 20 EV comparisons (even EV <= 0)
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 5 — Top 20 EV comparisons (all, sorted by EV desc)")

    # Supplement with re-computed from overlap if phase3_rows insufficient
    if len(phase3_rows) < 5 and overlap_matches:
        _supplement_rows(phase3_rows, overlap_matches, fid_to_odds)

    rows_with_odds = [r for r in phase3_rows if r.get("bk_odd")]
    rows_sorted    = sorted(rows_with_odds, key=lambda r: -r.get("ev_pct", -999))

    if not rows_with_odds:
        warn("Aucune ligne avec bookmaker_odd disponible pour comparaison EV")
        err("→ les matchs analysés n'ont pas d'odds ou les marchés ne correspondent pas")
    else:
        print()
        hdr = (f"  {'Fixture':<30}  {'League':<20}  {'Market':<18}  "
               f"{'Model%':>6}  {'BkOdd':>6}  {'Impl%':>6}  {'EV%':>6}  {'Edge%':>6}  Verdict")
        print(hdr)
        print(f"  {'─'*140}")
        for r in rows_sorted[:20]:
            model_pct = r.get("model_prob", 0) * 100
            impl_pct  = r.get("impl_prob",  0) * 100
            ev_val    = r.get("ev_pct",  None)
            edge_val  = r.get("edge_pct", None)
            bk_odd    = r.get("bk_odd",   None)
            ev_str    = f"{ev_val:+.1f}%" if ev_val is not None else "  N/A"
            edge_str  = f"{edge_val:+.1f}%" if edge_val is not None else "  N/A"
            ev_col    = G if (ev_val or -1) > 0 else (R if (ev_val or 0) < -5 else Y)
            verdict   = r.get("ev_status", "?")
            print(
                f"  {r.get('fixture','?'):<30}  {r.get('league','?'):<20}  "
                f"{r.get('market','?'):<18}  "
                f"{model_pct:>5.1f}%  {bk_odd or 0:>6.3f}  {impl_pct:>5.1f}%  "
                f"{ev_col}{ev_str:>6}{X}  {edge_str:>6}  {verdict}"
            )

        best_row = rows_sorted[0] if rows_sorted else None
        if best_row:
            print()
            ok(f"Best EV found : {best_row.get('fixture','?')}  "
               f"market={best_row.get('market','?')}  "
               f"ev={best_row.get('ev_pct',0):+.1f}%")

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 6 — Final verdict
    # ──────────────────────────────────────────────────────────────────────────
    sec("PHASE 6 — Diagnosis & correction")

    print()
    has_overlap     = bool(overlap)
    has_viable_mkts = bool(viable_markets)
    has_ev_neg      = failures.get("EV_NEGATIVE", 0) > 0
    has_mkt_miss    = failures.get("MARKET_NOT_AVAILABLE", 0) > 0
    has_not_anlyzd  = failures.get("ODDS_FIXTURE_NOT_ANALYZED", 0) > 0
    has_ev_pos      = failures.get("EV_POSITIVE_FOUND", 0) > 0

    # Q1
    if has_overlap:
        ok(f"Q1. Les matchs analysés ont-ils des odds ?  OUI — {len(overlap)} fixtures communs")
    else:
        err("Q1. Les matchs analysés ont-ils des odds ?  NON — overlap = 0")

    # Q2
    ghost_count = sum(1 for s, c in _SIGNAL_MARKET_CANDIDATES.items()
                      for m in c if m in _GHOST_MARKETS)
    if ghost_count:
        warn(f"Q2. Les marchés sélectionnés existent-ils dans les odds API-Football ?  "
             f"PARTIEL — {ghost_count} candidats fantômes")
        for m in sorted(_GHOST_MARKETS):
            print(f"       {R}{m}{X} (jamais produit par ApiFootballOddsProvider)")
    else:
        ok("Q2. Marchés sélectionnés → tous couverts par API-Football")

    # Q3
    if rows_with_odds:
        ok(f"Q3. Les odds arrivent-elles jusqu'au EVCalculator ?  OUI — {len(rows_with_odds)} paires signal/odd trouvées")
    else:
        err("Q3. Les odds arrivent-elles jusqu'au EVCalculator ?  NON — aucune paire signal/odd")

    # Q4
    print()
    print(f"  {BLD}Q4. Problème principal :{X}")
    if not has_overlap:
        err("  → COVERAGE : scanner analyse des fixtures sans odds (historique insuffisant)")
        print(f"     {Y}Les 37 fixtures avec odds sont des compétitions obscures/récentes{X}")
        print(f"     {Y}Le scanner les filtre car données historiques insuffisantes{X}")
    elif has_ev_neg and not has_ev_pos:
        err("  → EV NÉGATIVE : le modèle a des probabilités inférieures aux cotes bookmaker")
        print(f"     Exemple best: ev={rows_sorted[0].get('ev_pct',0):+.1f}% si rows_sorted else 'N/A'")
    elif has_mkt_miss:
        warn("  → MARKET MISMATCH partiel : certains signaux génèrent des marchés non disponibles")
    elif has_ev_pos:
        warn("  → EV POSITIVE TROUVÉE mais seuil interne bloque ? (vérifier ev_result.expected_value > 0)")
    else:
        warn("  → Cause non déterminée — exécuter avec --max-fixtures plus élevé")

    # Q5
    print()
    print(f"  {BLD}Q5. Correction minimale suggérée :{X}")
    if not has_overlap:
        print(f"  {C}Option A{X} — Accepter matchs avec moins d'historique (baisser le seuil MIN_MATCHES)")
        print(f"  {C}Option B{X} — Filtrer audit_odds_pipeline uniquement sur fixtures analysées")
        print(f"  {C}Option C{X} — Enrichir historique via get_historical_fixtures pour ces leagues")
        print()
        print(f"  {Y}Vérification rapide :{X}")
        print(f"    Fixtures dans odds mais pas analysées = {len(odds_not_analyzed)}")
        print(f"    Leagues concernées :")
        for fid in list(odds_not_analyzed)[:5]:
            mkts_n = len(fid_to_odds.get(fid, {}))
            print(f"      fixture_id={fid}  odds_markets={mkts_n}")
    elif ghost_count:
        print(f"  {C}Ajouter ces marchés manquants à ApiFootballOddsProvider si disponibles :{X}")
        for m in sorted(_GHOST_MARKETS):
            print(f"    {Y}{m}{X}")
        print(f"  → ou retirer ces candidats de _SIGNAL_MARKET_CANDIDATES si jamais bookés")
    elif has_ev_neg:
        print(f"  {C}EV négative = bookmakers plus précis que le modèle sur CES fixtures.{X}")
        print(f"  Aucune correction de code — c'est un résultat correct.")
        print(f"  Attendre des matchs avec un edge réel ou améliorer la précision du modèle.")

    elapsed = time.time() - t_start
    print(f"\n  {D}[elapsed: {elapsed:.1f}s]{X}\n")
    print(f"{'═' * 72}\n")

    return {
        "overlap":            len(overlap),
        "analyzed_no_odds":   len(analyzed_no_odds),
        "odds_not_analyzed":  len(odds_not_analyzed),
        "viable_markets":     len(viable_markets),
        "ghost_markets":      list(_GHOST_MARKETS),
        "ev_positive_found":  failures.get("EV_POSITIVE_FOUND", 0),
        "ev_negative":        failures.get("EV_NEGATIVE", 0),
        "failures":           dict(failures),
    }


def _supplement_rows(rows: list, overlap_matches: list, fid_to_odds: dict) -> None:
    """Build EV rows from raw fixture odds when scanner signals are unavailable."""
    for match in overlap_matches[:15]:
        fid    = str(match.get("match_id", ""))
        odds   = fid_to_odds.get(fid, {})
        league = match.get("league") or match.get("competition", "?")
        fx_str = f"{match.get('home_team','?')} vs {match.get('away_team','?')}"
        analysis = match.get("analysis", {}) or {}
        # Use ft_analysis_table to get model probability
        ft_table = analysis.get("ft_analysis_table") or []
        for entry in ft_table:
            line_str = str(entry.get("line", ""))
            if line_str.startswith("U"):
                line_val = line_str[1:]
                mkt_key  = f"FT_UNDER_{line_val.replace('.', '_')}"
            elif line_str.startswith("O"):
                line_val = line_str[1:]
                mkt_key  = f"FT_OVER_{line_val.replace('.', '_')}"
            else:
                continue
            bk_odd = odds.get(mkt_key)
            if not bk_odd or bk_odd <= 1.0:
                continue
            model_prob = float(entry.get("hit_rate", 0)) / 100.0
            if not (0 < model_prob < 1):
                continue
            ev = _ev(model_prob, bk_odd)
            rows.append({
                "fixture":     fx_str,
                "fid":         fid,
                "league":      league[:30],
                "signal_type": "ft_table",
                "model_prob":  model_prob,
                "market":      mkt_key,
                "bk_odd":      bk_odd,
                "impl_prob":   1.0 / bk_odd,
                "edge_pct":    (model_prob - 1.0 / bk_odd) * 100,
                "ev_pct":      ev * 100,
                "ev_status":   "EV_POSITIVE" if ev > 0 else "EV_NEGATIVE",
            })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Signal ↔ Odds ↔ EV bridge audit (read-only)")
    parser.add_argument("--date",         default=date.today().isoformat())
    parser.add_argument("--max-fixtures", type=int, default=50, dest="max_fixtures")
    args = parser.parse_args()
    result = run(target_date=args.date, max_fixtures=args.max_fixtures)
    sys.exit(0 if result["ev_positive_found"] > 0 else 1)
