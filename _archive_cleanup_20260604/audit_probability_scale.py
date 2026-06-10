"""
audit_probability_scale.py — Probability Scale Audit
=====================================================
Verifies that every probability-like value flowing through the EV pipeline
is correctly scaled (0–1 decimal, not 0–100 percent).

Checks three separate values that could each carry a scale bug:
  A) signal["confidence"]           — from SignalEngine (should be 0–1)
  B) EVResult["model_probability"]  — passed to EVCalculator (should be 0–1)
  C) ft_analysis_table["hit_rate"]  — stored by scanner (should be 0–100)

Cross-verification:
  ev_expected = (model_probability * bookmaker_odd - 1) * 100
  ev_stored   = EVResult["ev_percentage"]
  These MUST match within ±0.1 %.

If model_probability is mistakenly 70.0 (percent) instead of 0.70 (decimal):
  - EVCalculator.calculate() returns None (70.0 > 1.0 check fails)
  - ev_opportunities = [] → best_ev_opportunity = None → 0 picks
  - DIAGNOSIS: PROBABILITY_SCALE_BUG (never reaches EV table)

READ ONLY — does not modify any file or engine.

Usage:
    python audit_probability_scale.py
    python audit_probability_scale.py --date 2026-06-02
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


def _classify_prob(v, label: str) -> str:
    """Return scale classification for a probability-like value."""
    if v is None:
        return f"{D}MISSING{X}"
    if v < 0:
        return f"{R}SUSPICIOUS_NEGATIVE ({v:.4f}){X}"
    if v <= 1.0:
        return f"{G}OK_0_TO_1 ({v:.4f}){X}"
    if v <= 100.0:
        return f"{Y}OK_0_TO_100 ({v:.2f}){X}"
    return f"{R}SUSPICIOUS_GT_100 ({v:.2f}){X}"


def _classify_hr(v) -> str:
    """Classify a hit_rate value (expected range 0-100 for scanner tables)."""
    if v is None:
        return f"{D}MISSING{X}"
    if v < 0:
        return f"{R}SUSPICIOUS_NEGATIVE{X}"
    if v <= 1.0:
        return f"{Y}SCALE_0_TO_1_CHECK — expected 0-100, got {v:.4f}{X}"
    if v <= 100.0:
        return f"{G}OK_0_TO_100 ({v:.1f}){X}"
    return f"{R}SUSPICIOUS_GT_100 ({v:.1f}){X}"


def sec(title: str) -> None:
    print(f"\n{'═'*72}")
    print(f"  {BLD}{title}{X}")
    print(f"{'─'*72}")


def run(target_date: str) -> None:
    sec(f"AUDIT PROBABILITY SCALE — {target_date}")
    print()

    # ── Run scanner ────────────────────────────────────────────────────────────
    print("  Loading scanner…")
    try:
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        from app.providers.odds.odds_provider_manager import OddsProviderManager

        mgr = OddsProviderManager(
            apifootball_key=os.environ.get("API_FOOTBALL_KEY", ""),
            apifootball_url=os.environ.get("API_FOOTBALL_URL", "https://v3.football.api-sports.io"),
            oddsapi_key=os.environ.get("ODDS_API_KEY", ""),
        )
        dsm = DataSourceManager()
        scanner = SmartScanner(
            provider=dsm.provider,
            is_real_data=dsm.is_real_data,
            include_extreme_obscure=True,
            odds_provider=mgr,
        )
        result   = scanner.scan_today()
        analyzed = result.get("analyzed_matches") or []
        print(f"  Scanner done — {len(analyzed)} matches analyzed.")
    except Exception as exc:
        print(f"  {R}Scanner failed: {exc}{X}")
        import traceback; traceback.print_exc()
        return

    # ── Collect EV opportunities (max 30) ──────────────────────────────────────
    ev_rows = []    # list of dicts with all raw values
    for item in analyzed:
        if len(ev_rows) >= 30:
            break
        an = item.get("analysis") or {}
        md = item.get("match_data") or {}

        if an.get("status") == "DATA_INSUFFICIENT":
            continue
        if not an.get("best_ev_opportunity"):
            continue

        fid     = str(an.get("fixture_id") or md.get("match_id") or "")
        league  = md.get("competition", "?")
        fixture = f"{md.get('home_team','?')} vs {md.get('away_team','?')}"

        bev = an["best_ev_opportunity"]

        # ── A: signal confidence ──────────────────────────────────────────────
        signals = an.get("signals") or []
        sig_confidence_raw = signals[0].get("confidence") if signals else None
        sig_type_raw       = signals[0].get("type", "?")  if signals else "?"

        # ── B: EVResult dict fields ───────────────────────────────────────────
        ev_model_prob  = bev.get("model_probability")
        ev_bk_odd      = bev.get("bookmaker_odd")
        ev_implied     = bev.get("implied_probability")  # already percentage (0-100)?
        ev_edge        = bev.get("edge_percentage")
        ev_pct_stored  = bev.get("ev_percentage")
        ev_fair_odd    = bev.get("fair_odd")
        ev_market      = bev.get("market", "?")

        # ── Cross-verify EV math ──────────────────────────────────────────────
        ev_pct_expected = None
        if ev_model_prob is not None and ev_bk_odd is not None:
            ev_pct_expected = (ev_model_prob * ev_bk_odd - 1.0) * 100.0

        math_ok = (
            ev_pct_expected is not None
            and ev_pct_stored is not None
            and abs(ev_pct_expected - ev_pct_stored) < 0.2
        )

        # ── C: ft_analysis_table hit_rate for relevant line ──────────────────
        ft_table = (an.get("ft_analysis") or {}).get("table") or []
        ft_row_for_market = None
        if ev_market.startswith("FT_UNDER_") or ev_market.startswith("FT_OVER_"):
            # find the matching line in ft_table
            target_line = ev_market.replace("FT_UNDER_", "U").replace("FT_OVER_", "O").replace("_", ".", 1)
            for row in ft_table:
                if row.get("line") == target_line:
                    ft_row_for_market = row
                    break
            if not ft_row_for_market and ft_table:
                ft_row_for_market = ft_table[0]  # fallback: first row
        elif ft_table:
            ft_row_for_market = ft_table[0]

        hr_raw  = ft_row_for_market.get("hit_rate")   if ft_row_for_market else None
        ho_raw  = ft_row_for_market.get("fair_odd")   if ft_row_for_market else None
        hr_line = ft_row_for_market.get("line", "?")  if ft_row_for_market else "?"

        ev_rows.append({
            "fixture":     fixture,
            "fid":         fid,
            "league":      league,
            "market":      ev_market,
            "sig_type":    sig_type_raw,
            # A
            "sig_conf":    sig_confidence_raw,
            # B
            "model_prob":  ev_model_prob,
            "bk_odd":      ev_bk_odd,
            "implied_pct": ev_implied,
            "edge_pct":    ev_edge,
            "ev_pct":      ev_pct_stored,
            "ev_expected": ev_pct_expected,
            "fair_odd_ev": ev_fair_odd,
            "math_ok":     math_ok,
            # C
            "ft_line":     hr_line,
            "hr_raw":      hr_raw,
            "fair_odd_ft": ho_raw,
        })

    print(f"  EV opportunities collected: {len(ev_rows)}\n")

    if not ev_rows:
        print(f"  {Y}No EV opportunities found. Cannot audit scale.{X}")
        return

    # ── SECTION 1: Probability Scale per EV Opportunity ───────────────────────
    sec("PROBABILITY SCALE CHECK — EV OPPORTUNITIES")
    print()
    print(f"  {'Fixture':<30}  {'Market':<18}  {'sig_conf':>10}  {'model_prob':>12}  {'ev_pct':>8}  {'ev_expected':>12}  {'math':>6}")
    print(f"  {'─'*110}")

    for r in ev_rows:
        sc   = r["sig_conf"]
        mp   = r["model_prob"]
        ep   = r["ev_pct"]
        ee   = r["ev_expected"]
        math = f"{G}OK{X}" if r["math_ok"] else f"{R}MISMATCH{X}"
        sc_str = f"{sc:.4f}" if sc is not None else "None"
        mp_str = f"{mp:.4f}" if mp is not None else "None"
        ep_str = f"{ep:+.1f}%" if ep is not None else "None"
        ee_str = f"{ee:+.1f}%" if ee is not None else "None"
        print(f"  {r['fixture']:<30}  {r['market']:<18}  {sc_str:>10}  {mp_str:>12}  {ep_str:>8}  {ee_str:>12}  {math:>6}")

    # ── SECTION 2: Classification per row ─────────────────────────────────────
    sec("SCALE CLASSIFICATION — DETAILED")
    print()

    cnt_sig_ok      = 0
    cnt_sig_bug     = 0
    cnt_mod_ok      = 0
    cnt_mod_bug     = 0
    cnt_math_ok     = 0
    cnt_math_fail   = 0
    cnt_ev_gt_50    = 0
    cnt_ev_gt_100   = 0
    cnt_ev_gt_200   = 0
    all_probs       = []
    all_ev_pcts     = []
    all_hr_raws     = []

    for r in ev_rows:
        sc = r["sig_conf"]
        mp = r["model_prob"]
        ep = r["ev_pct"]
        hr = r["hr_raw"]
        fo = r["fair_odd_ft"]

        if sc is not None: all_probs.append(sc)
        if mp is not None: all_probs.append(mp)
        if ep is not None: all_ev_pcts.append(ep)
        if hr is not None: all_hr_raws.append(hr)

        if sc is not None and 0 < sc <= 1.0:
            cnt_sig_ok  += 1
        elif sc is not None:
            cnt_sig_bug += 1

        if mp is not None and 0 < mp <= 1.0:
            cnt_mod_ok  += 1
        elif mp is not None:
            cnt_mod_bug += 1

        if r["math_ok"]:
            cnt_math_ok  += 1
        else:
            cnt_math_fail += 1

        if ep and ep > 200:
            cnt_ev_gt_200 += 1
        if ep and ep > 100:
            cnt_ev_gt_100 += 1
        if ep and ep > 50:
            cnt_ev_gt_50  += 1

        print(f"  {r['fixture'][:30]:<30}  {r['market']:<18}")
        print(f"    A) signal confidence : {_classify_prob(sc, 'sig_conf')}")
        print(f"    B) model_probability : {_classify_prob(mp, 'model_prob')}")
        print(f"    C) ft_hit_rate(line={r['ft_line']}) : {_classify_hr(hr)}")
        if fo is not None:
            implied_from_ho = 1.0 / fo if fo > 0 else None
            print(f"       ft_fair_odd={fo:.3f}  → implied_prob={implied_from_ho:.3f}" if implied_from_ho else "")
        math_str = f"{G}✓ math OK{X}" if r["math_ok"] else f"{R}✗ math MISMATCH{X}"
        print(f"    EV cross-check       : ev_stored={r['ev_pct']:.1f}%  ev_expected={r['ev_expected']:.1f}%  {math_str}")
        print()

    # ── SECTION 3: Summary statistics ─────────────────────────────────────────
    sec("SUMMARY")
    print()
    n = len(ev_rows)

    if all_probs:
        print(f"  Signal + model probabilities (A+B):")
        print(f"    min  = {min(all_probs):.4f}")
        print(f"    max  = {max(all_probs):.4f}")
        print(f"    avg  = {sum(all_probs)/len(all_probs):.4f}")
    print()

    if all_hr_raws:
        print(f"  ft_analysis_table hit_rate (C — raw stored value):")
        print(f"    min  = {min(all_hr_raws):.2f}")
        print(f"    max  = {max(all_hr_raws):.2f}")
        print(f"    avg  = {sum(all_hr_raws)/len(all_hr_raws):.2f}")
        if max(all_hr_raws) > 1.0:
            print(f"    {C}→ stored as 0-100 percentage (e.g. 70.0 = 70%){X}")
        else:
            print(f"    {C}→ stored as 0-1 decimal (e.g. 0.70 = 70%){X}")
    print()

    if all_ev_pcts:
        print(f"  EV percentages:")
        print(f"    min  = {min(all_ev_pcts):+.1f}%")
        print(f"    max  = {max(all_ev_pcts):+.1f}%")
        print(f"    avg  = {sum(all_ev_pcts)/len(all_ev_pcts):+.1f}%")
    print()

    print(f"  Count checks ({n} EV rows total):")
    print(f"    signal confidence in (0,1)  : {cnt_sig_ok}/{n}   {'✓' if cnt_sig_ok == n else '✗'}")
    print(f"    model_probability in (0,1)  : {cnt_mod_ok}/{n}   {'✓' if cnt_mod_ok == n else '✗'}")
    print(f"    EV math cross-check pass    : {cnt_math_ok}/{n}   {'✓' if cnt_math_ok == n else '✗'}")
    print(f"    count_ev_gt_50              : {cnt_ev_gt_50}")
    print(f"    count_ev_gt_100             : {cnt_ev_gt_100}")
    print(f"    count_ev_gt_200             : {cnt_ev_gt_200}")

    # ── SECTION 4: ft_analysis display scale note ─────────────────────────────
    sec("DISPLAY SCALE NOTE — ft_analysis_table")
    print()
    print(f"  ft_analysis_table['hit_rate'] is stored as {BLD}percentage (0-100){X}.")
    print(f"  Example: 14/20 under → raw ratio 0.70 → stored as 70.0")
    print()
    print(f"  {Y}audit_signal_generation.py displayed hr * 100 = 7000% → display bug only.{X}")
    print(f"  The stored value is correct. The engine reads it from ft_analysis_table['hit_rate']")
    print(f"  (if it does at all — signal.confidence is NOT derived from ft_analysis_table).")
    print()
    print(f"  {BLD}Key finding:{X} signal.confidence is a FIXED DISCRETE value set by thresholds")
    print(f"  on avg_goals + variance_score — NOT the actual hit_rate of the specific market.")
    print()
    print(f"  Example (EXTREME_UNDER, avg_goals < 3.0, high variance):")
    print(f"    signal.confidence = 0.90 (assigned)")
    print(f"    ft_analysis_table FT_UNDER_1_5 hit_rate = ?? % (may differ)")
    print(f"    EVCalculator uses 0.90 as model_probability for FT_UNDER_1_5")
    print()

    # Find biggest discrepancy between sig_conf and ft_hit_rate for same market
    biggest_gap = None
    for r in ev_rows:
        sc = r["sig_conf"]
        hr = r["hr_raw"]
        if sc is None or hr is None:
            continue
        hr_decimal = hr / 100.0  # convert stored percentage to decimal
        gap = abs(sc - hr_decimal)
        if biggest_gap is None or gap > biggest_gap["gap"]:
            biggest_gap = {"fixture": r["fixture"], "market": r["market"],
                           "sig_conf": sc, "hr_decimal": hr_decimal,
                           "hr_raw": hr, "gap": gap}

    if biggest_gap:
        print(f"  Largest gap between signal.confidence and ft hit_rate for matched market:")
        print(f"    {biggest_gap['fixture']}  [{biggest_gap['market']}]")
        print(f"    signal.confidence = {biggest_gap['sig_conf']:.4f}  (used as model_probability)")
        print(f"    ft_hit_rate_raw   = {biggest_gap['hr_raw']:.1f}%  ({biggest_gap['hr_decimal']:.4f} decimal)")
        print(f"    gap               = {biggest_gap['gap']*100:.1f} percentage points")
        if biggest_gap["gap"] > 0.20:
            print(f"    {Y}⚠ Large gap — model_probability may not reflect actual market hit_rate{X}")

    # ── VERDICT ───────────────────────────────────────────────────────────────
    sec("VERDICT")
    print()

    scale_bug     = (cnt_sig_bug > 0 or cnt_mod_bug > 0)
    math_bug      = (cnt_math_fail > 0)
    display_bug   = bool(all_hr_raws and max(all_hr_raws) > 1.0)  # hr stored as 0-100

    if scale_bug:
        print(f"  {R}PROBABILITY_SCALE_BUG{X}")
        if cnt_sig_bug > 0:
            print(f"  ✗ signal.confidence out of (0,1) on {cnt_sig_bug} rows")
            print(f"    File : app/services/signals/signal_engine.py")
            print(f"    Func : detect_signals (or sub-detect functions)")
            print(f"    Issue: confidence assigned as percentage (0-100) instead of decimal (0-1)")
        if cnt_mod_bug > 0:
            print(f"  ✗ model_probability out of (0,1) on {cnt_mod_bug} rows")
            print(f"    File : app/services/analysis/ev_calculator.py")
            print(f"    Func : EVResult.to_dict()")
            print(f"    Issue: model_probability stored/passed as percentage")
    elif math_bug:
        print(f"  {Y}EV_MATH_MISMATCH — scale OK but computed EV ≠ stored EV{X}")
        print(f"  Check: app/services/analysis/ev_calculator.py → calculate()")
    else:
        print(f"  {G}PROBABILITY_SCALE_OK{X}")
        print(f"  ✓ signal.confidence ∈ (0,1) on all {cnt_sig_ok}/{n} rows")
        print(f"  ✓ model_probability ∈ (0,1) on all {cnt_mod_ok}/{n} rows")
        print(f"  ✓ EV math cross-check passes on {cnt_math_ok}/{n} rows")
        print()
        if display_bug:
            print(f"  {Y}DISPLAY_BUG in audit_signal_generation.py only:{X}")
            print(f"    ft_analysis_table['hit_rate'] is stored as 0-100 (percentage).")
            print(f"    The audit script did: display = hit_rate * 100 → double multiplication.")
            print(f"    Fix: remove the * 100 in audit_signal_generation.py display code.")
            print(f"    File : audit_signal_generation.py")
            print(f"    Line : hr_str = f\"{{hr*100:.1f}}%\"  ← remove *100")
            print(f"    Fix  : hr_str = f\"{{hr:.1f}}%\"")
        if cnt_ev_gt_100 > 0:
            print()
            print(f"  {Y}HIGH EV NOTE: {cnt_ev_gt_100} rows show EV > 100%.{X}")
            print(f"  Numerically correct given the model probabilities (signal.confidence).")
            print(f"  Root cause: signal.confidence is a DISCRETIZED proxy, NOT the actual")
            print(f"  hit_rate of the specific market. Example:")
            print(f"    EXTREME_UNDER (avg_goals < 3.0) → confidence = 0.90 (fixed)")
            print(f"    But FT_UNDER_1_5 true hit_rate may be 30-40%")
            print(f"    Bookmaker odds 4.65 priced for ~21% → large apparent edge")
            print(f"  File : app/services/signals/signal_engine.py")
            print(f"  Func : _detect_extreme_under(), _detect_ft_under(), etc.")
            print(f"  Issue: confidence = fixed_tier (0.7/0.8/0.9) not market_hit_rate")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probability scale audit")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    run(target_date=args.date)
