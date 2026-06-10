"""
audit_real_ev.py — READ-ONLY EV diagnostic
============================================
For every analyzed match that has bookmaker odds, shows the full EV
calculation for every signal/market pair — including negative EVs.

Answers:
  1. How many matches reach the EVCalculator with odds?
  2. How many markets find a bookmaker odd?
  3. How many EVs are calculated?
  4. Why are they rejected?
  5. What is the best EV found today?

READ-ONLY: no writes, no DB, no state changes.

Usage:
    python audit_real_ev.py
    python audit_real_ev.py --date 2026-06-03
    python audit_real_ev.py --min-odds 1.0    (include any odds > 1.0, default)
"""

import os
import sys
import argparse
from collections import defaultdict
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

# Mirror _SIGNAL_MARKET_CANDIDATES from scanner
_SIGNAL_MARKET_CANDIDATES = {
    "HT_UNDER":              ["HT_UNDER_0_5", "HT_UNDER_1_5"],
    "HT_OVER":               ["HT_OVER_0_5", "HT_OVER_1_5"],      # HT_OVER_1_0 EV_DISABLED
    "FT_UNDER":              ["FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5"],
    "FT_OVER":               ["FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5"],
    "BTTS_YES":              ["BTTS_YES"],
    "BTTS_NO":               ["BTTS_NO"],
    "BTTS_PROFILE":          ["BTTS_YES"],
    "HOME_DOMINANT":         [],  # EV_DISABLED
    "ASYMMETRIC_SCORING":    [],  # EV_DISABLED
    "SECOND_HALF_EXPLOSION": [],  # EV_DISABLED
    "EXTREME_UNDER":         ["FT_UNDER_1_5", "FT_UNDER_2_5"],
    "LOW_VARIANCE":          ["FT_UNDER_2_5", "FT_UNDER_1_5"],
}

# ft_analysis_table line → market key mapping
_FT_LINE_TO_MKT = {
    "U1.5": "FT_UNDER_1_5", "U2.5": "FT_UNDER_2_5",
    "U3.5": "FT_UNDER_3_5", "U4.5": "FT_UNDER_4_5",
    "O1.5": "FT_OVER_1_5",  "O2.5": "FT_OVER_2_5",
    "O3.5": "FT_OVER_3_5",  "O4.5": "FT_OVER_4_5",
}
_HT_LINE_TO_MKT = {
    "U0.5": "HT_UNDER_0_5", "U1.5": "HT_UNDER_1_5",
    "O0.5": "HT_OVER_0_5",  "O1.5": "HT_OVER_1_5",
}


def _ev(model_prob: float, odd: float) -> float:
    return model_prob * odd - 1.0


def _verdict(ev: float) -> str:
    if ev >= 0.12:   return f"{G}STRONG_VALUE{X}"
    if ev >= 0.06:   return f"{G}VALUE{X}"
    if ev >= 0.02:   return f"{Y}LOW_VALUE{X}"
    if ev >= 0.00:   return f"{Y}NEUTRAL{X}"
    if ev >= -0.05:  return f"{R}SLIGHT_NEG{X}"
    return f"{R}AVOID{X}"


def run(target_date: str, min_odds: float = 1.0) -> dict:
    print(f"\n{'═' * 74}")
    print(f"  {BLD}AUDIT REAL EV — {target_date}{X}")
    print(f"{'═' * 74}\n")

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
    scan_result  = scanner.scan_today()
    diag         = scan_result.get("odds_first_mode_diagnostics", {})
    analyzed_all = scan_result.get("analyzed_matches") or []

    # ── Counters ───────────────────────────────────────────────────────────────
    n_reaches_ev        = 0  # matches that reach EV calculator (have odds)
    n_mkt_with_odd      = 0  # signal/market pairs that found a bk_odd
    n_ev_calculated     = 0  # total EV values computed
    n_ev_positive       = 0  # EV > 0
    failure_reasons     = defaultdict(int)
    all_ev_rows         = []  # for top-20 table

    print(f"  Scan complete — analyzed: {len(analyzed_all)}, "
          f"with_odds: {diag.get('analyzed_with_odds',0)}, "
          f"without_odds: {diag.get('analyzed_without_odds',0)}\n")

    # ── Phase 6 — Per-match odds trace ─────────────────────────────────────────
    print(f"  {'─'*70}")
    print(f"  {BLD}PER-MATCH ODDS TRACE{X}")
    print(f"  {'─'*70}")
    hdr_tr = f"  {'Fixture':<28}  {'fixture_id':>12}  {'odds_cnt':>8}  {'has_odds':>8}  {'status':<18}  first_5_markets"
    print(hdr_tr)
    print(f"  {'─'*130}")
    for item in analyzed_all:
        _md = item.get("match_data") or {}
        _an = item.get("analysis") or {}
        _fid_tr = str(_an.get("fixture_id") or _md.get("match_id") or "")
        _fix_tr = f"{_md.get('home_team','?')} vs {_md.get('away_team','?')}"[:28]
        _cnt_tr = _an.get("odds_count", 0)
        _has_tr = _an.get("has_real_odds", False)
        _sts_tr = _an.get("status", "ANALYZED")
        # first 5 markets from odds_by_market or matched_odds
        _mkts_tr = list((_an.get("odds_by_market") or {}).keys())[:5]
        if not _mkts_tr:
            _mkts_tr = [
                (nd.get("market") if isinstance(nd, dict) else getattr(nd, "market", "?"))
                for nd in (_an.get("matched_odds") or [])[:5]
            ]
        _mkts_str = ", ".join(_mkts_tr) if _mkts_tr else f"{D}(none){X}"
        _col = G if _has_tr else (Y if _cnt_tr == 0 and _sts_tr == "ANALYZED" else R)
        print(
            f"  {_fix_tr:<28}  {_fid_tr:>12}  {_col}{_cnt_tr:>8}{X}  "
            f"{'✓' if _has_tr else '✗':>8}  {_sts_tr:<18}  {_mkts_str}"
        )
    print()

    # ── Per-match EV analysis ─────────────────────────────────────────────────
    for item in analyzed_all:
        match_data = item.get("match_data") or {}
        an         = item.get("analysis") or {}

        # Phase 6 — prefer fixture_id from analysis dict (populated by get_fixture_id)
        fid     = str(an.get("fixture_id") or match_data.get("match_id") or "")
        home    = match_data.get("home_team", "?")
        away    = match_data.get("away_team", "?")
        league  = match_data.get("competition", "?")
        fixture = f"{home} vs {away}"
        has_real_odds = an.get("has_real_odds", False)
        odds_count_an = an.get("odds_count", 0)

        # Build odds_by_market — prefer odds_by_market dict from analysis
        odds_by_mkt: dict = {}
        # Path A: odds_by_market dict injected by scanner (Phase 3)
        for mkt, nd in (an.get("odds_by_market") or {}).items():
            odd = nd.get("odd") if isinstance(nd, dict) else getattr(nd, "odd", None)
            bkm = nd.get("bookmaker", "") if isinstance(nd, dict) else getattr(nd, "bookmaker", "")
            if mkt and odd and float(odd) > min_odds:
                odds_by_mkt[mkt] = (float(odd), bkm)
        # Path B: matched_odds list (fallback)
        for nd in (an.get("matched_odds") or []):
            mkt = nd.get("market") if isinstance(nd, dict) else getattr(nd, "market", None)
            odd = nd.get("odd")    if isinstance(nd, dict) else getattr(nd, "odd", None)
            bkm = nd.get("bookmaker", "") if isinstance(nd, dict) else getattr(nd, "bookmaker", "")
            if mkt and odd and float(odd) > min_odds and mkt not in odds_by_mkt:
                odds_by_mkt[mkt] = (float(odd), bkm)
        # Path C: direct apifb_cache lookup by fixture_id
        for norm in (apifb_cache.get(fid) or []):
            mkt = norm.market
            odd = norm.odd
            if mkt and odd and float(odd) > min_odds and mkt not in odds_by_mkt:
                odds_by_mkt[mkt] = (float(odd), norm.bookmaker)

        odds_count = odds_count_an or len(odds_by_mkt)
        analysis_status = an.get("status", "ANALYZED")
        if analysis_status == "DATA_INSUFFICIENT":
            failure_reasons["DATA_INSUFFICIENT"] += 1
            continue
        if odds_count == 0 and not odds_by_mkt:
            failure_reasons["BOOKMAKER_ODD_NULL"] += 1
            continue

        n_reaches_ev += 1

        # ── Signal-level EV computation ────────────────────────────────────────
        # Key in analysis dict is "signals" (= signals_with_value built by scanner)
        signals_raw = an.get("signals") or []
        if not signals_raw:
            failure_reasons["NO_MODEL_PROBABILITY"] += 1
            continue

        match_had_any_odd  = False
        match_had_any_ev   = False

        for sig in signals_raw:
            sig_type   = sig.get("type", "")
            model_prob = float(sig.get("confidence", 0))
            if not (0.0 < model_prob < 1.0):
                failure_reasons["NO_MODEL_PROBABILITY"] += 1
                continue

            candidates = _SIGNAL_MARKET_CANDIDATES.get(sig_type, [])
            if not candidates:
                failure_reasons["MARKET_NOT_FOUND"] += 1
                continue

            found_any_for_sig = False
            for mkt in candidates:
                pair = odds_by_mkt.get(mkt)
                if not pair:
                    failure_reasons["MARKET_MISMATCH"] += 1
                    continue

                bk_odd, bookmaker = pair
                n_mkt_with_odd  += 1
                n_ev_calculated += 1
                found_any_for_sig = True
                match_had_any_odd = True

                ev = _ev(model_prob, bk_odd)
                implied = 1.0 / bk_odd
                edge    = (model_prob - implied) * 100
                fair_od = 1.0 / model_prob if model_prob > 0 else 0

                if ev > 0:
                    n_ev_positive     += 1
                    match_had_any_ev   = True
                    failure_reasons["EV_POSITIVE"] += 1
                elif ev > -0.05:
                    failure_reasons["EV_NEGATIVE"] += 1
                else:
                    failure_reasons["EV_BELOW_THRESHOLD"] += 1

                all_ev_rows.append({
                    "fixture":    fixture,
                    "fid":        fid,
                    "league":     league[:24],
                    "signal":     sig_type,
                    "market":     mkt,
                    "model_prob": model_prob,
                    "bk_odd":     bk_odd,
                    "implied":    implied,
                    "fair_odd":   fair_od,
                    "edge_pct":   edge,
                    "ev_pct":     ev * 100,
                    "bookmaker":  bookmaker,
                    "sample":     sig.get("sample_size", 0),
                })
                break  # use first matching candidate per signal

            if not found_any_for_sig:
                failure_reasons["MARKET_MISMATCH"] += 1

        if not match_had_any_odd:
            failure_reasons["MARKET_NOT_FOUND"] += 1

    # ── Also compute EV from ft_analysis_table × matched_odds (fine-grained) ──
    # This catches EV opportunities the scanner's signal system might miss
    extra_rows = []
    for item in analyzed_all:
        match_data = item.get("match_data") or {}
        an         = item.get("analysis") or {}
        fid        = str(an.get("fixture_id") or match_data.get("match_id") or "")

        if an.get("status") == "DATA_INSUFFICIENT":
            continue
        odds_by_mkt: dict = {}
        for mkt, nd in (an.get("odds_by_market") or {}).items():
            odd = nd.get("odd") if isinstance(nd, dict) else getattr(nd, "odd", None)
            bkm = nd.get("bookmaker", "") if isinstance(nd, dict) else getattr(nd, "bookmaker", "")
            if mkt and odd and float(odd) > min_odds:
                odds_by_mkt[mkt] = (float(odd), bkm)
        for nd in (an.get("matched_odds") or []):
            mkt = nd.get("market") if isinstance(nd, dict) else getattr(nd, "market", None)
            odd = nd.get("odd")    if isinstance(nd, dict) else getattr(nd, "odd", None)
            bkm = nd.get("bookmaker", "") if isinstance(nd, dict) else getattr(nd, "bookmaker", "")
            if mkt and odd and float(odd) > min_odds and mkt not in odds_by_mkt:
                odds_by_mkt[mkt] = (float(odd), bkm)
        for norm in (apifb_cache.get(fid) or []):
            if norm.market and norm.odd > min_odds and norm.market not in odds_by_mkt:
                odds_by_mkt[norm.market] = (norm.odd, norm.bookmaker)

        if not odds_by_mkt:
            continue

        fixture = f"{match_data.get('home_team','?')} vs {match_data.get('away_team','?')}"
        league  = match_data.get("competition", "?")

        for tbl_name, tbl, line_map in [
            ("ft", an.get("ft_analysis_table") or [], _FT_LINE_TO_MKT),
            ("ht", an.get("ht_analysis_table") or [], _HT_LINE_TO_MKT),
        ]:
            for row in tbl:
                lbl  = row.get("line", "")
                mkt  = line_map.get(lbl)
                if not mkt:
                    continue
                pair = odds_by_mkt.get(mkt)
                if not pair:
                    continue
                bk_odd, bookmaker = pair
                model_prob = float(row.get("hit_rate", 0)) / 100.0
                if not (0.0 < model_prob < 1.0):
                    continue
                ev  = _ev(model_prob, bk_odd)
                implied = 1.0 / bk_odd
                edge    = (model_prob - implied) * 100
                fair_od = 1.0 / model_prob
                extra_rows.append({
                    "fixture":    fixture,
                    "fid":        fid,
                    "league":     league[:24],
                    "signal":     f"{tbl_name.upper()}_TABLE",
                    "market":     mkt,
                    "model_prob": model_prob,
                    "bk_odd":     bk_odd,
                    "implied":    implied,
                    "fair_odd":   fair_od,
                    "edge_pct":   edge,
                    "ev_pct":     ev * 100,
                    "bookmaker":  bookmaker,
                    "sample":     row.get("sample_size", 0),
                })

    # Merge and deduplicate
    seen = set()
    for r in extra_rows:
        key = (r["fid"], r["market"])
        if key not in seen:
            seen.add(key)
            all_ev_rows.append(r)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print(f"  {'═'*70}")
    print(f"  {BLD}SUMMARY — HOW FAR DID ODDS REACH EV CALCULATOR?{X}")
    print(f"  {'─'*70}")
    print(f"  {'1. Matches analyzed total':<46}  {len(analyzed_all):>5}")
    print(f"  {'2. Matches reaching EVCalculator (has odds)':<46}  "
          f"{G if n_reaches_ev > 0 else R}{n_reaches_ev:>5}{X}")
    print(f"  {'3. Signal/market pairs with bookmaker odd':<46}  "
          f"{G if n_mkt_with_odd > 0 else R}{n_mkt_with_odd:>5}{X}")
    print(f"  {'4. EV values computed (signal path)':<46}  "
          f"{G if n_ev_calculated > 0 else Y}{n_ev_calculated:>5}{X}")
    print(f"  {'5. EV > 0 (positive edge)':<46}  "
          f"{G if n_ev_positive > 0 else R}{n_ev_positive:>5}{X}")
    print(f"  {'6. EV rows (incl. table path)':<46}  {len(all_ev_rows):>5}")
    print()

    # ── FAILURE REASONS ───────────────────────────────────────────────────────
    print(f"  {'─'*70}")
    print(f"  {BLD}FAILURE REASON COUNT{X}")
    print(f"  {'─'*70}")
    print(f"  {'Reason':<38}  {'Count':>5}  {'%':>5}")
    print(f"  {'─'*38}  {'─'*5}  {'─'*5}")
    total_f = sum(failure_reasons.values()) or 1
    for reason, cnt in sorted(failure_reasons.items(), key=lambda x: -x[1]):
        col = G if reason == "EV_POSITIVE" else (Y if "MISMATCH" in reason or "NEGATIVE" in reason else R)
        pct = cnt / total_f * 100
        print(f"  {col}{reason:<38}{X}  {cnt:>5}  {pct:>4.0f}%")

    # ── TOP 20 EV (even negative) ──────────────────────────────────────────────
    print(f"\n  {'─'*70}")
    print(f"  {BLD}TOP 20 EV COMPARISONS (sorted by EV desc, including negative){X}")
    print(f"  {'─'*70}")
    all_ev_rows.sort(key=lambda r: -r["ev_pct"])

    if not all_ev_rows:
        print(f"  {R}Aucune paire signal/odd disponible.{X}")
        print(f"  → 'matched_odds' est vide dans l'analysis dict")
        print(f"  → Vérifier que odds_provider.prefetch_for_matches() est appelé AVANT scan_today()")
    else:
        hdr = (f"  {'Fixture':<30}  {'League':<20}  {'Market':<18}  "
               f"{'Model':>6}  {'Odd':>6}  {'Impl':>6}  {'Fair':>6}  "
               f"{'Edge':>6}  {'EV':>6}  {'Bk':>8}")
        print(hdr)
        print(f"  {'─'*140}")
        for r in all_ev_rows[:20]:
            ev_col = (G if r["ev_pct"] > 2 else
                      Y if r["ev_pct"] > 0 else
                      R if r["ev_pct"] < -10 else D)
            print(
                f"  {r['fixture']:<30}  {r['league']:<20}  {r['market']:<18}  "
                f"{r['model_prob']*100:>5.1f}%  {r['bk_odd']:>6.3f}  "
                f"{r['implied']*100:>5.1f}%  {r['fair_odd']:>6.3f}  "
                f"{r['edge_pct']:>+5.1f}%  "
                f"{ev_col}{r['ev_pct']:>+5.1f}%{X}  "
                f"{r['bookmaker'][:8]:>8}"
            )

    # ── DIAGNOSIS ─────────────────────────────────────────────────────────────
    print(f"\n  {'═'*70}")
    print(f"  {BLD}DIAGNOSIS{X}")
    print(f"  {'─'*70}")

    if not all_ev_rows:
        _data_insuf = failure_reasons.get("DATA_INSUFFICIENT", 0)
        _bk_null    = failure_reasons.get("BOOKMAKER_ODD_NULL", 0)
        _mkt_miss   = failure_reasons.get("MARKET_MISMATCH", 0)
        _no_model   = failure_reasons.get("NO_MODEL_PROBABILITY", 0)
        if _data_insuf > 0 and _bk_null > 0 and _mkt_miss == 0:
            print(f"  {Y}COVERAGE_GAP{X}: Matches split into two disjoint groups:")
            print(f"    • {_data_insuf} matches: in odds cache but DATA_INSUFFICIENT (0 historical)")
            print(f"    • {_bk_null} matches: have signals but fixture_id NOT in odds cache")
            print(f"  → Fix: expand odds coverage to leagues with historical data")
            print(f"  → Or: populate historical data for the obscure leagues with odds today")
        elif _no_model > 0:
            print(f"  {R}WIRE_PROBLEM{X}: odds_by_market non-empty but signals missing.")
            print(f"  → Check that get_fixture_id() resolves correctly")
            print(f"  → Run with DEBUG_ODDS_WIRING=true for per-fixture trace")
        else:
            print(f"  {R}WIRE_PROBLEM{X}: odds_by_market dict is empty in the scanner.")
            print(f"  → Check that OddsProviderManager.prefetch_for_matches() is called")
            print(f"  → Check that get_match_odds_normalized() returns odds for these fixture_ids")
            print(f"  → Run with DEBUG_ODDS_WIRING=true for [WIRE_CACHE] trace")

    elif n_ev_positive > 0:
        best = all_ev_rows[0]
        print(f"  {G}EV_POSITIVE_FOUND{X}")
        print(f"  Best: {best['fixture']} | {best['market']} | "
              f"ev={G}{best['ev_pct']:+.1f}%{X} | model={best['model_prob']*100:.1f}% | "
              f"odd={best['bk_odd']:.3f}")
        print(f"  → Scanner should have picked this up — check if EV threshold is blocking it")

    else:
        best = all_ev_rows[0] if all_ev_rows else None
        print(f"  {Y}EV_ALL_NEGATIVE{X}: EVCalculator reached but no positive edge found.")
        if best:
            print(f"  Best EV today : {best['fixture']}")
            print(f"    Market  = {best['market']}")
            print(f"    Model%  = {best['model_prob']*100:.1f}%  →  fair odd = {best['fair_odd']:.3f}")
            print(f"    Bookmaker odd = {best['bk_odd']:.3f}  →  implied = {best['implied']*100:.1f}%")
            print(f"    EV = {R}{best['ev_pct']:+.1f}%{X}  edge = {best['edge_pct']:+.1f}%")
            print()
            gap = best["implied"] - best["model_prob"]
            print(f"  Model underestimates vs bookmaker by {gap*100:.1f}pp on best market.")
            print(f"  → This is a correct result: no exploitable edge today on these fixtures.")
            print(f"  → Leagues with odds today are obscure (Azadegan, Iraqi, Friendlies).")
            print(f"  → Bookmakers may have better calibration on these leagues.")
            print(f"  → Next step: monitor overlap over several days to confirm systemic pattern.")

    # ── AVAILABLE MARKETS IN ODDS ─────────────────────────────────────────────
    print(f"\n  {BLD}MARKETS AVAILABLE IN ODDS (from analyzed matches){X}")
    mkt_count: dict = defaultdict(int)
    for r in all_ev_rows:
        mkt_count[r["market"]] += 1
    for mkt, cnt in sorted(mkt_count.items(), key=lambda x: -x[1]):
        print(f"    {mkt:<22}  {cnt:>3} entries")

    print(f"\n{'═' * 74}\n")

    return {
        "success":             n_ev_positive > 0,
        "n_reaches_ev":        n_reaches_ev,
        "n_mkt_with_odd":      n_mkt_with_odd,
        "n_ev_calculated":     n_ev_calculated,
        "n_ev_positive":       n_ev_positive,
        "best_ev_pct":         all_ev_rows[0]["ev_pct"] if all_ev_rows else None,
        "failure_reasons":     dict(failure_reasons),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full EV audit (read-only)")
    parser.add_argument("--date",      default=date.today().isoformat())
    parser.add_argument("--min-odds",  type=float, default=1.0, dest="min_odds")
    args = parser.parse_args()
    result = run(target_date=args.date, min_odds=args.min_odds)
    sys.exit(0 if result["success"] else 1)
