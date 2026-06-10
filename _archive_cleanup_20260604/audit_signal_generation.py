"""
audit_signal_generation.py — Signal Generation Diagnostic
==========================================================
For every match analyzed WITH odds (has_real_odds=True), traces
the full path: historical data → signal engine → probability → EV.

READ ONLY — does not modify any file or engine.

Counters:
  NO_SIGNALS                  : scanner produced 0 signals
  SIGNALS_NO_PROBABILITY      : signals list non-empty but confidence = 0 or null
  PROBABILITY_NULL            : confidence field missing / None on every signal
  PROBABILITY_ZERO            : confidence = 0.0 on every signal
  TABLES_AVAILABLE_BUT_NO_SIG : ft/ht tables have rows, yet signals = 0
  SIGNAL_MARKET_MISMATCH      : signal type not in _SIGNAL_MARKET_CANDIDATES
                                 or no market key found in odds_by_market

Usage:
    python audit_signal_generation.py
    python audit_signal_generation.py --date 2026-06-02
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
B   = "\033[94m"
C   = "\033[96m"
D   = "\033[90m"
X   = "\033[0m"
BLD = "\033[1m"

# Mirrors _SIGNAL_MARKET_CANDIDATES from smart_scanner.py (READ ONLY copy)
_SIGNAL_CANDIDATES = {
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

_EV_DISABLED = {
    "HOME_OVER_0_5", "AWAY_OVER_0_5",
    "HT_OVER_1_0",
    "SECOND_HALF_OVER_0_5", "SECOND_HALF_OVER_1_5",
}


def sec(title: str) -> None:
    print(f"\n{'═' * 72}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─' * 72}")


def run(target_date: str) -> None:
    sec(f"AUDIT SIGNAL GENERATION — {target_date}")

    # ── Run scanner ────────────────────────────────────────────────────────────
    print(f"\n  Loading scanner (this calls scan_today)…")
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        from app.providers.odds.odds_provider_manager import OddsProviderManager

        apifb_key   = os.environ.get("API_FOOTBALL_KEY", "")
        apifb_url   = os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io")
        odds_api_key = os.environ.get("ODDS_API_KEY", "")
        mgr = OddsProviderManager(
            apifootball_key=apifb_key,
            apifootball_url=apifb_url,
            oddsapi_key=odds_api_key,
        )

        dsm     = DataSourceManager()
        scanner = SmartScanner(
            provider=dsm.provider,
            is_real_data=dsm.is_real_data,
            include_extreme_obscure=True,
            odds_provider=mgr,
        )
        result   = scanner.scan_today()
        analyzed = result.get("analyzed_matches") or []
        print(f"  Scanner done — {len(analyzed)} matches analyzed total.")
    except Exception as exc:
        print(f"  {R}Scanner failed: {exc}{X}")
        import traceback; traceback.print_exc()
        return

    # ── Filter: matches WITH odds ──────────────────────────────────────────────
    with_odds = []
    data_insuf = 0
    for item in analyzed:
        an = item.get("analysis") or {}
        if an.get("status") == "DATA_INSUFFICIENT":
            data_insuf += 1
            continue
        if an.get("has_real_odds") or an.get("odds_count", 0) > 0:
            with_odds.append(item)

    print(f"  DATA_INSUFFICIENT skipped : {data_insuf}")
    print(f"  Matches WITH odds          : {len(with_odds)}")
    print(f"  Matches WITHOUT odds       : {len(analyzed) - data_insuf - len(with_odds)}")

    if not with_odds:
        print(f"\n  {Y}No matches with odds found. Nothing to audit.{X}")
        return

    # ── Per-match diagnostics ──────────────────────────────────────────────────
    counters = defaultdict(int)
    all_breakpoints = []

    sec("PER-MATCH ODDS × SIGNAL TRACE")
    print()

    for item in with_odds:
        md  = item.get("match_data") or {}
        an  = item.get("analysis")   or {}

        fid     = str(an.get("fixture_id") or md.get("match_id") or "")
        home    = md.get("home_team",  "?")
        away    = md.get("away_team",  "?")
        league  = md.get("competition", "?")
        fixture = f"{home} vs {away}"
        odds_cnt = an.get("odds_count", 0)
        odds_src = an.get("odds_source", "?")

        # Signals (key = "signals" in analysis dict)
        signals_raw = an.get("signals") or []
        sigs_count  = len(signals_raw)

        # ft / ht tables
        ft_table = (an.get("ft_analysis") or {}).get("table") or []
        ht_table = (an.get("ht_analysis") or {}).get("table") or []

        # odds_by_market (dict of market → {odd, bookmaker, ...})
        obm = an.get("odds_by_market") or {}
        obm_keys = set(obm.keys())

        # ── Print match header ────────────────────────────────────────────────
        print(f"  {'─'*70}")
        print(f"  {BLD}{fixture}{X}  [{fid}]")
        print(f"  league={D}{league}{X}  odds_count={G if odds_cnt>0 else R}{odds_cnt}{X}"
              f"  odds_source={C}{odds_src}{X}"
              f"  ft_rows={len(ft_table)}  ht_rows={len(ht_table)}")

        # ── Markets available ─────────────────────────────────────────────────
        useful_mkts = [k for k in sorted(obm_keys)
                       if any(k.startswith(p) for p in ("FT_", "HT_", "BTTS_"))]
        print(f"  Available markets ({len(obm_keys)} total, {len(useful_mkts)} EV-relevant): "
              f"{', '.join(useful_mkts[:8]) or D+'(none)'+X}")

        # ── Signals ──────────────────────────────────────────────────────────
        if sigs_count == 0:
            counters["NO_SIGNALS"] += 1
            print(f"  {R}signals = 0{X}  ← BREAKPOINT")
            # Check if tables exist but no signal
            if ft_table or ht_table:
                counters["TABLES_AVAILABLE_BUT_NO_SIG"] += 1
                print(f"  {Y}  ⚠ ft_table={len(ft_table)} rows, ht_table={len(ht_table)} rows — "
                      f"tables exist but signal engine produced nothing{X}")
        else:
            print(f"  signals={G}{sigs_count}{X}")

        prob_null_all  = True
        prob_zero_all  = True
        sig_mkt_miss   = 0
        sig_mkt_hit    = 0

        for sig in signals_raw:
            sig_type = sig.get("type", "?")
            conf     = sig.get("confidence")
            strength = sig.get("strength", "?")
            suggested = sig.get("suggested_markets") or []
            sample   = sig.get("sample_size", 0)
            quality  = sig.get("data_quality", "?")

            if conf is not None:
                prob_null_all = False
            if conf and float(conf) > 0:
                prob_zero_all = False

            # Market candidate lookup
            candidates = _SIGNAL_CANDIDATES.get(sig_type, [])
            ev_candidates = [m for m in candidates if m not in _EV_DISABLED]
            matched_mkts  = [m for m in ev_candidates if m in obm_keys]
            missing_mkts  = [m for m in ev_candidates if m not in obm_keys]

            if matched_mkts:
                sig_mkt_hit += 1
            else:
                sig_mkt_miss += 1

            _conf_str = (f"{G}{conf*100:.1f}%{X}" if conf and float(conf) > 0.5
                         else f"{Y}{conf*100:.1f}%{X}" if conf
                         else f"{R}None{X}")
            print(
                f"    signal: {BLD}{sig_type:<26}{X}"
                f" conf={_conf_str:>14}  strength={strength}  sample={sample}"
            )
            print(
                f"      candidates={ev_candidates or ['(none)']}"
                f"  matched={G if matched_mkts else R}{matched_mkts or []}{X}"
            )
            if missing_mkts:
                print(f"      {Y}missing from odds_by_market:{X} {missing_mkts}")

        # Update counters
        if sigs_count > 0 and prob_null_all:
            counters["PROBABILITY_NULL"] += 1
        if sigs_count > 0 and not prob_null_all and prob_zero_all:
            counters["PROBABILITY_ZERO"] += 1
        if sigs_count > 0 and (prob_null_all or prob_zero_all):
            counters["SIGNALS_NO_PROBABILITY"] += 1
        if sigs_count > 0 and sig_mkt_miss > 0 and sig_mkt_hit == 0:
            counters["SIGNAL_MARKET_MISMATCH"] += 1

        # ── FT table ─────────────────────────────────────────────────────────
        if ft_table:
            print(f"  ft_analysis_table ({len(ft_table)} rows):")
            for row in ft_table[:5]:
                mkt = row.get("market", "?")
                hr  = row.get("hit_rate")
                ss  = row.get("sample_size", "?")
                hr_str = f"{hr*100:.1f}%" if hr is not None else "None"
                _hr_col = G if hr and hr >= 0.5 else (Y if hr else R)
                print(f"    {mkt:<20}  hit_rate={_hr_col}{hr_str:>7}{X}  sample={ss}")
            if len(ft_table) > 5:
                print(f"    … {len(ft_table)-5} more rows")

        # ── HT table ─────────────────────────────────────────────────────────
        if ht_table:
            print(f"  ht_analysis_table ({len(ht_table)} rows):")
            for row in ht_table[:4]:
                mkt = row.get("market", "?")
                hr  = row.get("hit_rate")
                ss  = row.get("sample_size", "?")
                hr_str = f"{hr*100:.1f}%" if hr is not None else "None"
                _hr_col = G if hr and hr >= 0.5 else (Y if hr else R)
                print(f"    {mkt:<20}  hit_rate={_hr_col}{hr_str:>7}{X}  sample={ss}")
            if len(ht_table) > 4:
                print(f"    … {len(ht_table)-4} more rows")

        # ── Breakpoint classification ─────────────────────────────────────────
        if sigs_count == 0:
            bp = "NO_SIGNALS"
        elif prob_null_all or prob_zero_all:
            bp = "PROBABILITY_NULL_OR_ZERO"
        elif sig_mkt_miss > 0 and sig_mkt_hit == 0:
            bp = "SIGNAL_MARKET_MISMATCH"
        elif not obm_keys:
            bp = "ODDS_BY_MARKET_EMPTY"
        else:
            bp = "OK_SIGNALS_AND_ODDS"

        _bp_col = G if bp.startswith("OK") else R
        print(f"  {_bp_col}BREAKPOINT → {bp}{X}")
        all_breakpoints.append(bp)
        print()

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    sec("SUMMARY — FAILURE COUNTERS")
    print()
    total = len(with_odds)
    rows = [
        ("NO_SIGNALS",                 counters["NO_SIGNALS"],               "signal engine produced 0 signals"),
        ("TABLES_AVAILABLE_BUT_NO_SIG",counters["TABLES_AVAILABLE_BUT_NO_SIG"],"ft/ht tables exist but 0 signals"),
        ("PROBABILITY_NULL",           counters["PROBABILITY_NULL"],          "signal.confidence is None on all signals"),
        ("PROBABILITY_ZERO",           counters["PROBABILITY_ZERO"],          "signal.confidence = 0.0 on all signals"),
        ("SIGNALS_NO_PROBABILITY",     counters["SIGNALS_NO_PROBABILITY"],    "signals exist but all confidence null/zero"),
        ("SIGNAL_MARKET_MISMATCH",     counters["SIGNAL_MARKET_MISMATCH"],    "no candidate market found in odds_by_market"),
    ]
    for key, count, desc in rows:
        col = R if count > 0 else G
        print(f"  {col}{key:<36}{X}  {count:>3}/{total:<3}  — {D}{desc}{X}")

    # ── DIAGNOSIS ─────────────────────────────────────────────────────────────
    sec("DIAGNOSIS — FIRST BREAKPOINT")
    print()

    from collections import Counter
    bp_counts = Counter(all_breakpoints)
    for bp, n in bp_counts.most_common():
        col = G if bp.startswith("OK") else R
        print(f"  {col}{bp:<36}{X}  {n}/{total} matches")

    dominant_bp = bp_counts.most_common(1)[0][0] if bp_counts else "UNKNOWN"
    print()
    if dominant_bp == "NO_SIGNALS":
        print(f"  {R}DIAGNOSIS: Signal engine produces 0 signals.{X}")
        print(f"  Causes:")
        print(f"    1. Historical data too sparse (< 5 FT matches) — check ft_table rows")
        print(f"    2. Goal patterns too chaotic — no clear UNDER/OVER/BTTS regime")
        print(f"    3. SignalEngine confidence threshold not met for these leagues")
        print(f"  Action:")
        print(f"    → Inspect ft_analysis_table hit_rates above")
        print(f"    → If tables are empty, history is insufficient for signal generation")
        print(f"    → If tables populated, signal engine filter is too strict")
    elif dominant_bp == "SIGNAL_MARKET_MISMATCH":
        print(f"  {R}DIAGNOSIS: Signals generated but no matching market in odds_by_market.{X}")
        print(f"  Causes:")
        print(f"    1. _SIGNAL_MARKET_CANDIDATES keys don't match API-Football market names")
        print(f"    2. API-Football only provides 1X2/Match Winner for these leagues")
        print(f"  Action:")
        print(f"    → Check 'Available markets' rows above for real market names")
        print(f"    → Compare with candidates column per signal")
    elif dominant_bp == "PROBABILITY_NULL_OR_ZERO":
        print(f"  {R}DIAGNOSIS: Signals exist but confidence is null/zero.{X}")
        print(f"  Action: Check SignalEngine output; signal.confidence must be in (0,1)")
    elif dominant_bp == "OK_SIGNALS_AND_ODDS":
        print(f"  {G}DIAGNOSIS: Signals + odds both present. EV may be negative (bookmaker efficient).{X}")
        print(f"  → Run audit_real_ev.py to see EV values — may all be < 0%")
        print(f"  → This is normal for efficient markets with small history samples")
    else:
        print(f"  {Y}DIAGNOSIS: {dominant_bp}{X}")

    print()
    ok_count = bp_counts.get("OK_SIGNALS_AND_ODDS", 0)
    if ok_count > 0:
        print(f"  {G}{ok_count}/{total} matches have both signals and matching odds → EV computable{X}")
    else:
        print(f"  {R}0/{total} matches reached a computable EV state.{X}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Signal generation diagnostic")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date ISO (default: today)")
    args = parser.parse_args()
    run(target_date=args.date)
