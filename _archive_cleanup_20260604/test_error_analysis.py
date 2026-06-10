"""
test_error_analysis.py — Phase 7 Validation
=============================================
Valide le Error Analysis Engine en 4 modes:
  1. Chargement depuis les CSVs historiques
  2. Données synthétiques si aucun CSV disponible
  3. Affichage: top failure reasons, FP leagues, marchés dangereux, penalties
  4. Démonstration de la pick explainability (WHY_PICK / RISK_FACTORS)

Usage:
    python test_error_analysis.py
    python test_error_analysis.py --demo      # force synthetic data
    python test_error_analysis.py --explain   # montrer les explications détaillées
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.services.analysis.error_analysis_engine import (
    ErrorAnalysisEngine, reset_eae,
)

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# ─── Synthetic demo data ───────────────────────────────────────────────────────
def _make_demo_rows() -> list:
    """Realistic synthetic losses with various failure patterns."""
    import random
    random.seed(99)

    base_rows = [
        # (league, country, market, tier, conf, vol, chaos, fss, small_smp, oqm, h2h_bias,
        #  wform, home_str, away_wk, league_tags, vol_tags, result)
        # Losses where model was confident (false positives)
        ("Japan J2",      "Japan",   "HT_UNDER_1_5", "S_TIER",  80, 75, 40, 20, 10, 15, 5, 60, 55, 50,
         "['HIGH_VOLATILITY_LEAGUE']",           "[]",            "LOSS"),
        ("Japan J2",      "Japan",   "HT_UNDER_1_5", "A_TIER",  72, 70, 38, 25, 15, 12, 8, 55, 52, 48,
         "['HIGH_VOLATILITY_LEAGUE']",           "[]",            "LOSS"),
        ("Japan J2",      "Japan",   "FT_UNDER_2_5", "S_TIER",  76, 72, 65, 18, 10, 10, 3, 58, 53, 50,
         "['HIGH_VOLATILITY_LEAGUE']",           "['EXPLOSIVE']", "LOSS"),
        ("Women WC",      "World",   "BTTS_NO",      "A_TIER",  68, 55, 70, 30, 20, 20, 10, 45, 60, 40,
         "['WOMEN_HIGH_VARIANCE', 'CHAOTIC_LEAGUE']", "[]",     "LOSS"),
        ("Women WC",      "World",   "BTTS_NO",      "S_TIER",  74, 60, 68, 25, 18, 22, 12, 42, 58, 38,
         "['WOMEN_HIGH_VARIANCE', 'CHAOTIC_LEAGUE']", "[]",     "LOSS"),
        ("Women WC",      "World",   "FT_UNDER_2_5", "S_TIER",  71, 58, 66, 28, 16, 18, 8,  44, 57, 40,
         "['WOMEN_HIGH_VARIANCE']",               "[]",            "LOSS"),
        ("AFC U23",       "Asia",    "FT_OVER_2_5",  "A_TIER",  66, 40, 35, 55, 65, 40, 25, 25, 45, 62,
         "['YOUTH_CHAOS']",                       "[]",            "LOSS"),
        ("AFC U23",       "Asia",    "FT_OVER_2_5",  "A_TIER",  70, 42, 38, 58, 68, 42, 30, 22, 47, 60,
         "['YOUTH_CHAOS']",                       "[]",            "LOSS"),
        ("Kenya Premier", "Kenya",   "FT_OVER_3_5",  "WATCHLIST",45, 35, 30, 25, 15, 15, 5,  65, 48, 52,
         "['STABLE_UNDER_LEAGUE']",               "[]",            "LOSS"),
        ("Ligue 2",       "France",  "FT_OVER_2_5",  "S_TIER",  75, 30, 28, 20, 12, 10, 4,  62, 50, 50,
         "['STABLE_UNDER_LEAGUE', 'LOW_SCORING_LEAGUE']", "[]", "LOSS"),
        ("Ligue 2",       "France",  "FT_OVER_2_5",  "A_TIER",  69, 28, 25, 18, 10, 8,  3,  60, 48, 52,
         "['STABLE_UNDER_LEAGUE']",               "[]",            "LOSS"),
        ("Liga MX",       "Mexico",  "FT_UNDER_1_5", "S_TIER",  77, 65, 60, 22, 12, 12, 6,  50, 54, 48,
         "['LATE_GOAL_LEAGUE']",                  "['FAKE_UNDER']","LOSS"),
        ("Liga MX",       "Mexico",  "FT_UNDER_1_5", "A_TIER",  71, 62, 58, 25, 14, 14, 8,  48, 52, 50,
         "['LATE_GOAL_LEAGUE']",                  "['FAKE_UNDER']","LOSS"),
        ("Ethiopia Premier","Ethiopia","FT_UNDER_2_5","S_TIER",  78, 35, 30, 20, 10, 10, 4,  64, 51, 49,
         "[]",                                    "[]",            "LOSS"),
        # Non-FP losses (low confidence)
        ("Japan J2",      "Japan",   "FT_OVER_2_5",  "WATCHLIST",45, 80, 70, 35, 20, 18, 8,  40, 58, 45,
         "['HIGH_VOLATILITY_LEAGUE']",             "['EXPLOSIVE']","LOSS"),
        ("AFC U23",       "Asia",    "BTTS_YES",     "WATCHLIST",50, 40, 35, 50, 60, 38, 28, 28, 46, 60,
         "['YOUTH_CHAOS']",                        "[]",           "LOSS"),
        # Wins
        ("Japan J2",      "Japan",   "FT_OVER_2_5",  "S_TIER",  75, 40, 35, 20, 10, 10, 4,  62, 50, 50,
         "[]",                                     "[]",           "WIN"),
        ("Kenya Premier", "Kenya",   "HT_UNDER_0_5", "S_TIER",  82, 20, 18, 15, 8,  8,  3,  70, 52, 48,
         "['STABLE_UNDER_LEAGUE']",                "[]",           "WIN"),
        ("Ligue 2",       "France",  "BTTS_NO",      "A_TIER",  70, 25, 22, 18, 10, 8,  2,  65, 50, 50,
         "['STABLE_UNDER_LEAGUE']",                "[]",           "WIN"),
    ]

    rows = []
    for (lg, ct, mk, tier, conf, vol, chaos, fss, ss, oqm, h2h,
         wform, home_str, away_wk, ltags, vtags, result) in base_rows:
        import random as rnd
        rows.append({
            "league":               lg,
            "country":              ct,
            "market":               mk,
            "statistical_tier":     tier,
            "confidence_score":     str(conf + rnd.uniform(-3, 3)),
            "volatility_score":     str(vol),
            "chaos_score":          str(chaos),
            "false_signal_score":   str(fss),
            "small_sample_risk":    str(ss),
            "opposition_quality_mismatch": str(oqm),
            "h2h_bias_risk":        str(h2h),
            "weighted_form_score":  str(wform),
            "home_strength_index":  str(home_str),
            "away_weakness_index":  str(away_wk),
            "league_tags":          ltags,
            "volatility_tags":      vtags,
            "result_correct":       result,
        })

    return rows


# ─── Print helpers ─────────────────────────────────────────────────────────────
def _print_section(title: str):
    w = 66
    print(f"\n{'═'*w}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{'─'*w}")


def _bar(count: int, max_count: int, width: int = 20) -> str:
    filled = int(count / max(max_count, 1) * width)
    return f"{RED}{'█' * filled}{'░' * (width - filled)}{RESET}"


# ─── Main test ─────────────────────────────────────────────────────────────────
def run_test(force_demo: bool = False, show_explain: bool = False):
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  ERROR ANALYSIS ENGINE — Phase 7 Test{RESET}")
    print(f"{'═'*66}")

    reset_eae()
    engine = ErrorAnalysisEngine()

    # ── Load data ────────────────────────────────────────────────────────────
    if not force_demo:
        n = engine.load_from_csvs(".")
        if n > 0:
            print(f"\n  {GREEN}✓ {n} rows loaded from live_test_session_*.csv{RESET}")
            source = "REAL CSV"
        else:
            print(f"\n  {YELLOW}⚠ No CSV data found — using synthetic demo data{RESET}")
            n = engine.load_from_rows(_make_demo_rows())
            source = "SYNTHETIC"
    else:
        n = engine.load_from_rows(_make_demo_rows())
        print(f"\n  {CYAN}→ Synthetic demo data forced ({n} rows){RESET}")
        source = "SYNTHETIC"

    if not engine.is_ready:
        print(f"\n  {RED}✗ Engine not ready (no LOSS rows found){RESET}")
        return

    s = engine.summary()
    print(f"\n  Source: {BOLD}{source}{RESET}")
    print(f"  Rows: {n}  |  Losses: {s['total_losses']}"
          f"  |  False Positives: {RED}{s['total_false_positives']}{RESET}"
          f"  |  FP rate: {RED}{s['total_false_positives']/max(s['total_losses'],1):.0%}{RESET}")
    print(f"  Leagues: {s['leagues_affected']}  |  Markets: {s['markets_affected']}"
          f"  |  Patterns: {s['total_patterns']}")

    # ── Phase 1+3: Top failure reasons ───────────────────────────────────────
    _print_section("PHASE 1+3 — TOP FAILURE REASONS")
    reasons = engine.top_failure_reasons(12)
    if not reasons:
        print(f"  {DIM}No failure data yet{RESET}")
    else:
        max_c = reasons[0]["fp_count"] if reasons else 1
        for r in reasons:
            bar = _bar(r["fp_count"], max_c)
            print(f"  {YELLOW}{r['reason']:<25}{RESET} {bar} {r['fp_count']}")

    # ── Phase 2: Top FP leagues ───────────────────────────────────────────────
    _print_section("PHASE 2 — TOP FALSE POSITIVE LEAGUES")
    leagues = engine.top_false_positive_leagues(10)
    if not leagues:
        print(f"  {DIM}No data{RESET}")
    else:
        max_fp = leagues[0]["fp_count"] if leagues else 1
        for lg in leagues:
            bar = _bar(lg["fp_count"], max_fp)
            fp_rate_c = RED if lg["fp_rate"] > 0.5 else YELLOW
            print(f"  {lg['league'][:28]:<28}  {bar}"
                  f"  FP={fp_rate_c}{lg['fp_count']}{RESET}"
                  f"  rate={fp_rate_c}{lg['fp_rate']:.0%}{RESET}"
                  f"  n={lg['total_losses']}")

    # ── Phase 3: Top dangerous markets ───────────────────────────────────────
    _print_section("PHASE 3 — TOP DANGEROUS MARKETS")
    markets = engine.top_dangerous_markets(10)
    if not markets:
        print(f"  {DIM}No data{RESET}")
    else:
        max_fp = markets[0]["fp_count"] if markets else 1
        for mk in markets:
            bar = _bar(mk["fp_count"], max_fp)
            fc = RED if mk["fp_rate"] > 0.5 else YELLOW
            print(f"  {mk['market']:<22}  {bar}"
                  f"  FP={fc}{mk['fp_count']}{RESET}"
                  f"  rate={fc}{mk['fp_rate']:.0%}{RESET}"
                  f"  n={mk['total_losses']}")

    # ── Phase 4: Confidence penalties applied ────────────────────────────────
    _print_section("PHASE 4 — CONFIDENCE PENALTIES (examples)")
    test_cases = [
        ("Japan J2",        "Japan",    "HT_UNDER_1_5", 75.0),
        ("Women WC",        "World",    "BTTS_NO",       70.0),
        ("Liga MX",         "Mexico",   "FT_UNDER_1_5",  72.0),
        ("Kenya Premier",   "Kenya",    "HT_UNDER_0_5",  80.0),
        ("Ligue 2",         "France",   "FT_OVER_2_5",   68.0),
        ("Ethiopia Premier","Ethiopia", "FT_UNDER_2_5",  78.0),
    ]
    for lg, ct, mk, conf in test_cases:
        mult, reason = engine.get_historical_failure_penalty(lg, ct, mk)
        adj = conf * mult
        delta = adj - conf
        sign = "▼" if delta < 0 else ("▲" if delta > 0 else "─")
        c = RED if delta < 0 else (GREEN if delta > 0 else "")
        print(f"  {c}{sign} {lg[:24]:<24} [{mk[:16]:<16}]{RESET}"
              f"  {conf:.0f}% → {adj:.1f}%  (×{mult:.2f})")
        if reason:
            print(f"    {DIM}{reason[:72]}{RESET}")

    # ── Phase 5: Pick Explanation ─────────────────────────────────────────────
    if show_explain:
        _print_section("PHASE 5 — PICK EXPLAINABILITY (3 examples)")

        explain_cases = [
            # (league, country, market, conf, vol, chaos, fss, league_tags, vol_tags,
            #  tier_downgrade, refuse_pick, refuse_reason, reliability, lse_edge, lse_prof)
            ("Japan J2", "Japan", "HT_UNDER_1_5", 80.0, 75, 40, 20,
             ["HIGH_VOLATILITY_LEAGUE"], [], False, False, "", 55.0,
             "NEUTRAL", "NO_DATA"),
            ("Kenya Premier", "Kenya", "HT_UNDER_0_5", 82.0, 20, 18, 15,
             ["STABLE_UNDER_LEAGUE"], [], False, False, "", 80.0,
             "STRONG_EDGE", "STRONG_EDGE"),
            ("AFC U23", "Asia", "FT_OVER_2_5", 70.0, 42, 38, 58,
             ["YOUTH_CHAOS"], [], True, True, "Volatilité extrême", 30.0,
             "AVOID", "NO_EDGE"),
        ]
        for (lg, ct, mk, conf, vol, chaos, fss, ltags, vtags,
             tdg, ref, ref_r, rel, lse_e, lse_p) in explain_cases:
            expl = engine.generate_pick_explanation(
                league=lg, country=ct, market=mk,
                confidence=conf, volatility=vol, chaos=chaos,
                false_signal_score=fss,
                league_tags=ltags, volatility_tags=vtags,
                tier_downgrade=tdg, refuse_pick=ref, refuse_reason=ref_r,
                league_reliability=rel,
                lse_edge_rating=lse_e, lse_market_prof=lse_p,
            )
            print(f"\n  {BOLD}{lg}{RESET} / {mk}")
            print(f"  {GREEN}WHY_PICK:{RESET}")
            for item in expl.why_pick or ["(aucune raison positive détectée)"]:
                print(f"    {GREEN}+ {item}{RESET}")
            print(f"  {YELLOW}RISK_FACTORS:{RESET}")
            for item in expl.risk_factors or ["(aucun risque détecté)"]:
                print(f"    {YELLOW}⚠ {item}{RESET}")
            print(f"  {RED}WHY_NOT_S_TIER:{RESET}")
            for item in expl.why_not_s_tier or ["(aucun obstacle identifié)"]:
                print(f"    {RED}✗ {item}{RESET}")
            if expl.failure_pattern_warning:
                print(f"  {RED}⛔ Pattern warning: {expl.failure_pattern_warning}{RESET}")
            if expl.historical_failure_penalty > 0:
                print(f"  {RED}Pénalité historique: -{expl.historical_failure_penalty:.0%}{RESET}")

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_section("SUMMARY")
    report = engine.get_error_analysis_report()
    print(f"  {'Total losses analysées':<35}: {s['total_losses']}")
    print(f"  {'False positives (haute confiance)':<35}: {RED}{s['total_false_positives']}{RESET}")
    fp_rate = s['total_false_positives'] / max(s['total_losses'], 1)
    col = RED if fp_rate > 0.4 else (YELLOW if fp_rate > 0.2 else GREEN)
    print(f"  {'FP rate global':<35}: {col}{fp_rate:.0%}{RESET}")
    print(f"  {'Patterns identifiés':<35}: {s['total_patterns']}")
    print(f"  {'Ligues affectées':<35}: {s['leagues_affected']}")
    print(f"  {'Marchés affectés':<35}: {s['markets_affected']}")
    print()

    top_r = report["top_failure_reasons"]
    if top_r:
        print(f"  {BOLD}Cause principale:{RESET} {top_r[0]['reason']} "
              f"({top_r[0]['fp_count']} FP)")
    top_l = report["top_fp_leagues"]
    if top_l:
        print(f"  {BOLD}Ligue la plus risquée:{RESET} {top_l[0]['league']} "
              f"({top_l[0]['fp_count']} FP · {top_l[0]['fp_rate']:.0%})")
    top_m = report["top_dangerous_markets"]
    if top_m:
        print(f"  {BOLD}Marché le plus dangereux:{RESET} {top_m[0]['market']} "
              f"({top_m[0]['fp_count']} FP · {top_m[0]['fp_rate']:.0%})")

    print(f"\n  {GREEN}✓ Test complet — Error Analysis Engine opérationnel{RESET}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test du Error Analysis Engine (Phases 1-7)"
    )
    parser.add_argument("--demo",    action="store_true", help="Forcer les données synthétiques")
    parser.add_argument("--explain", action="store_true", help="Afficher la pick explainability (Phase 5)")
    args = parser.parse_args()
    run_test(force_demo=args.demo, show_explain=args.explain)
