"""
test_league_specialization.py — Phase 8 Validation
=====================================================
Valide le League Specialization Engine en 4 modes:

  1. Chargement depuis les CSVs historiques (live_test_session_*.csv)
  2. Données synthétiques réalistes si aucun CSV disponible
  3. Affichage complet: meilleures/pires ligues, marchés, edge scores
  4. Démonstration de l'ajustement dynamique de confiance

Usage:
    python test_league_specialization.py
    python test_league_specialization.py --demo     # force synthetic data
    python test_league_specialization.py --verbose  # full matrix
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.analysis.league_specialization_engine import (
    LeagueSpecializationEngine, reset_engine,
)

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

EDGE_COLOR = {
    "STRONG_EDGE": f"{BOLD}{GREEN}",
    "EDGE":        f"{GREEN}",
    "NEUTRAL":     f"{CYAN}",
    "WEAK":        f"{YELLOW}",
    "NO_EDGE":     f"{RED}",
    "UNKNOWN":     f"{DIM}",
    "AVOID":       f"{BOLD}{RED}",
}


# ─── Synthetic demo data ───────────────────────────────────────────────────────
def _make_demo_rows() -> list:
    """
    Build realistic synthetic prediction + result rows.
    Simulates 3 months of data across several leagues and markets.
    """
    import random
    random.seed(42)

    scenarios = [
        # (league, country, market, hit_prob, n, ev_avg, conf_avg, vol_avg, bk_odd)
        ("Japan J2",        "Japan",    "FT_OVER_2_5",   0.70, 40, 4.2,  72, 30, 1.85),
        ("Japan J2",        "Japan",    "BTTS_YES",      0.65, 30, 3.8,  68, 35, 1.90),
        ("Japan J2",        "Japan",    "HT_UNDER_1_5",  0.30, 20, -2.5, 55, 45, 1.75),
        ("Ethiopia Premier","Ethiopia", "FT_UNDER_2_5",  0.68, 35, 5.1,  70, 28, 1.80),
        ("Ethiopia Premier","Ethiopia", "BTTS_NO",       0.60, 25, 2.9,  64, 32, 1.88),
        ("Ethiopia Premier","Ethiopia", "FT_OVER_2_5",   0.28, 18, -3.2, 50, 55, 2.10),
        ("Women WC",        "World",    "BTTS_YES",      0.72, 45, 6.3,  75, 22, 1.78),
        ("Women WC",        "World",    "FT_OVER_2_5",   0.67, 38, 4.5,  71, 25, 1.83),
        ("Women WC",        "World",    "HT_UNDER_1_5",  0.35, 20, -1.8, 58, 40, 1.72),
        ("AFC U23",         "Asia",     "FT_OVER_2_5",   0.25, 22, -4.1, 48, 62, 2.20),
        ("AFC U23",         "Asia",     "BTTS_YES",      0.45, 18, -0.8, 52, 58, 1.92),
        ("AFC U23",         "Asia",     "FT_UNDER_2_5",  0.70, 30, 3.9,  69, 30, 1.82),
        ("Kenya Premier",   "Kenya",    "HT_UNDER_0_5",  0.80, 25, 7.2,  78, 20, 1.75),
        ("Kenya Premier",   "Kenya",    "FT_UNDER_2_5",  0.65, 20, 3.1,  66, 30, 1.85),
        ("Kenya Premier",   "Kenya",    "FT_OVER_3_5",   0.22, 15, -5.8, 45, 65, 2.40),
        ("Liga MX",         "Mexico",   "BTTS_YES",      0.55, 50, 1.2,  60, 40, 1.95),
        ("Liga MX",         "Mexico",   "FT_UNDER_2_5",  0.40, 45, -2.0, 55, 45, 1.88),
        ("Liga MX",         "Mexico",   "FT_OVER_2_5",   0.58, 50, 2.1,  62, 42, 1.90),
        ("Ligue 2",         "France",   "BTTS_NO",       0.62, 30, 3.3,  67, 33, 1.87),
        ("Ligue 2",         "France",   "HT_UNDER_1_5",  0.70, 35, 4.8,  73, 27, 1.78),
        ("Ligue 2",         "France",   "FT_OVER_2_5",   0.35, 28, -2.9, 52, 48, 1.93),
    ]

    rows = []
    for lg, ct, mk, p_win, n, ev_avg, conf_avg, vol_avg, bk_odd in scenarios:
        tier = "S_TIER" if p_win >= 0.65 else ("A_TIER" if p_win >= 0.55 else "WATCHLIST")
        for _ in range(n):
            result = "WIN" if random.random() < p_win else "LOSS"
            ev_pct = round(ev_avg + random.gauss(0, 2), 1)
            conf   = round(max(20, min(95, conf_avg + random.gauss(0, 8))), 1)
            vol    = round(max(10, min(90, vol_avg + random.gauss(0, 5))), 1)
            bk     = round(bk_odd + random.gauss(0, 0.08), 2)
            rows.append({
                "league":                 lg,
                "country":                ct,
                "market":                 mk,
                "statistical_tier":       tier,
                "result_correct":         result,
                "ev_percent":             str(ev_pct),
                "confidence_score":       str(conf),
                "volatility_score":       str(vol),
                "bookmaker_odd":          str(max(1.05, bk)),
            })
    return rows


# ─── Print helpers ─────────────────────────────────────────────────────────────
def _ec(label: str) -> str:
    return EDGE_COLOR.get(label, "")


def _print_section(title: str):
    w = 66
    print(f"\n{'═'*w}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{'─'*w}")


def _print_matrix_row(s: dict):
    ec = _ec(s["edge_label"])
    roi_c = GREEN if s["roi"] >= 0 else RED
    print(
        f"  {ec}{s['edge_label']:<13}{RESET}"
        f"  {s['league'][:24]:<24}"
        f"  {s['market'][:16]:<16}"
        f"  n={s['total_predictions']:<3}"
        f"  HR={s['hit_rate']:.0%}"
        f"  ROI={roi_c}{s['roi']:+.1f}%{RESET}"
        f"  edge={s['edge_score']:+.2f}"
    )


def _print_league_ranking(r: dict):
    roi_c = GREEN if r["overall_roi"] >= 0 else RED
    print(
        f"  {r['league'][:28]:<28}"
        f"  {r['country'][:12]:<12}"
        f"  ROI={roi_c}{r['overall_roi']:+.1f}%{RESET}"
        f"  HR={r['overall_hit_rate']:.0%}"
        f"  n={r['total_predictions']:<3}"
    )
    if r["best_markets"]:
        print(f"    {GREEN}+ best : {', '.join(r['best_markets'])}{RESET}")
    if r["worst_markets"]:
        print(f"    {RED}- worst: {', '.join(r['worst_markets'])}{RESET}")


# ─── Main test ────────────────────────────────────────────────────────────────
def run_test(force_demo: bool = False, verbose: bool = False):
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  LEAGUE SPECIALIZATION ENGINE — Phase 8 Test{RESET}")
    print(f"{'═'*66}")

    reset_engine()
    engine = LeagueSpecializationEngine()

    # ── Load data ─────────────────────────────────────────────────────────────
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
        print(f"\n  {RED}✗ Engine not ready (insufficient data){RESET}")
        return

    summary = engine.summary()
    print(f"\n  Source: {BOLD}{source}{RESET}")
    print(f"  Rows: {n}  |  Combinations: {summary['total_combinations']}"
          f"  |  Evaluated (n≥{5}): {summary['evaluated']}")

    # ── Phase 1: Top matrix entries ───────────────────────────────────────────
    _print_section("PHASE 1 — LEAGUE PROFITABILITY MATRIX (top 15)")
    matrix = engine.get_profitability_matrix()
    for row in matrix[:15]:
        _print_matrix_row(row)
    if len(matrix) > 15:
        print(f"  {DIM}... and {len(matrix)-15} more combinations{RESET}")

    # ── Phase 2: League rankings ───────────────────────────────────────────────
    _print_section("PHASE 2 — LEAGUE MARKET RANKINGS")
    rankings = engine.get_league_rankings()
    print(f"\n  {BOLD}Meilleures ligues:{RESET}")
    for r in rankings[:8]:
        _print_league_ranking(r)
    print(f"\n  {BOLD}Pires ligues:{RESET}")
    for r in reversed(rankings[-5:]):
        _print_league_ranking(r)

    # ── Phase 3: Edge discovery ────────────────────────────────────────────────
    _print_section("PHASE 3 — EDGE DISCOVERY")
    disc = engine.get_edge_discovery()

    print(f"\n  {BOLD}{GREEN}Marchés rentables (global):{RESET}")
    for m in disc["profitable_markets"]:
        print(f"    {GREEN}+ {m['market']:<20}{RESET}  avg_edge={m['avg_edge']:+.3f}  ROI={m['roi']:+.1f}%"
              f"  n={m['n']}")

    print(f"\n  {BOLD}{RED}Marchés dangereux (global):{RESET}")
    for m in disc["unprofitable_markets"]:
        print(f"    {RED}✗ {m['market']:<20}{RESET}  avg_edge={m['avg_edge']:+.3f}  ROI={m['roi']:+.1f}%"
              f"  n={m['n']}")

    print(f"\n  {BOLD}Ligues rentables:{RESET}")
    for lg in disc["profitable_leagues"][:6]:
        print(f"    {GREEN}▲ {lg['league']:<28}{RESET}  edge={lg['avg_edge']:+.3f}  ROI={lg['roi']:+.1f}%")

    print(f"\n  {BOLD}Ligues non rentables:{RESET}")
    for lg in disc["unprofitable_leagues"][:6]:
        print(f"    {RED}▼ {lg['league']:<28}{RESET}  edge={lg['avg_edge']:+.3f}  ROI={lg['roi']:+.1f}%")

    # ── Phase 4: Confidence adjustment demo ───────────────────────────────────
    _print_section("PHASE 4 — DYNAMIC CONFIDENCE ADJUSTMENT")
    test_cases = []
    for row in matrix[:4]:
        test_cases.append((row["league"], row["country"], row["market"], 70.0))
    danger = engine.get_danger_report()
    for bl in list(danger["BLACKLIST_LEAGUE"])[:2]:
        lg, ct = (bl.split("|") + [""])[:2]
        test_cases.append((lg, ct, "FT_OVER_2_5", 70.0))

    print()
    for lg, ct, mk, conf in test_cases:
        mult, reason = engine.adjust_confidence(conf, lg, ct, mk)
        adj = conf * mult
        delta = adj - conf
        sign = "▲" if delta > 0 else ("▼" if delta < 0 else "─")
        c = GREEN if delta > 0 else (RED if delta < 0 else "")
        print(f"  {c}{sign} {lg[:24]:<24} [{mk[:16]:<16}]{RESET}"
              f"  {conf:.0f}% → {adj:.1f}%  (×{mult:.2f})")
        if reason:
            print(f"    {DIM}{reason[:70]}{RESET}")

    # ── Phase 5: Danger report ────────────────────────────────────────────────
    _print_section("PHASE 5 — DANGEROUS LEAGUE / MARKET DETECTION")
    for label, items in danger.items():
        c = RED if items else DIM
        print(f"  {c}{label:<30}{RESET}: {len(items)}")
        for item in list(items)[:4]:
            print(f"    {RED}⚠ {item}{RESET}")

    # ── Phase 6: Smart recommendation demo ───────────────────────────────────
    _print_section("PHASE 6 — SMART RECOMMENDATIONS (3 examples)")
    demo_matches = []
    for row in matrix[:2]:
        demo_matches.append((row["league"], row["country"], row["market"]))
    if danger["BLACKLIST_LEAGUE"]:
        bl = list(danger["BLACKLIST_LEAGUE"])[0]
        lg, ct = (bl.split("|") + [""])[:2]
        demo_matches.append((lg, ct, "FT_OVER_2_5"))

    for lg, ct, mk in demo_matches[:3]:
        rec = engine.get_smart_recommendations(lg, ct, mk)
        ec = _ec(rec.league_edge_rating)
        print(f"\n  {ec}{rec.league_edge_rating:<14}{RESET}  {BOLD}{lg}{RESET} / {mk}")
        print(f"    market_profitability : {rec.market_historical_profitability}")
        print(f"    performance          : {rec.historical_model_performance}")
        if rec.recommended_market_priority:
            print(f"    recommended          : {', '.join(rec.recommended_market_priority)}")
        if rec.market_warning:
            print(f"    {RED}⚠ warning: {rec.market_warning}{RESET}")
        if rec.confidence_adjustment_reason:
            print(f"    conf_adj: ×{rec.confidence_adjustment:.2f}  ({rec.confidence_adjustment_reason[:60]})")

    # ── Verbose: full matrix ──────────────────────────────────────────────────
    if verbose:
        _print_section(f"VERBOSE — FULL MATRIX ({len(matrix)} entries)")
        for row in matrix:
            _print_matrix_row(row)

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_section("SUMMARY")
    print(f"  {'Evaluated combinations':<35}: {summary['evaluated']}")
    print(f"  {'Profitable leagues':<35}: {GREEN}{summary['profitable_leagues_count']}{RESET}")
    print(f"  {'Unprofitable leagues':<35}: {RED}{summary['unprofitable_leagues_count']}{RESET}")
    print(f"  {'Blacklisted leagues':<35}: {RED}{summary['blacklisted_leagues']}{RESET}")
    print(f"  {'High FPR leagues':<35}: {RED}{summary['high_fpr_leagues']}{RESET}")
    print(f"  {'Unstable markets':<35}: {YELLOW}{summary['unstable_markets']}{RESET}")
    print(f"  {'No-edge combinations':<35}: {YELLOW}{summary['no_edge_combinations']}{RESET}")
    print(f"\n  {GREEN}✓ Test complet — League Specialization Engine opérationnel{RESET}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test du League Specialization Engine (Phases 1-8)"
    )
    parser.add_argument("--demo",    action="store_true", help="Forcer les données synthétiques")
    parser.add_argument("--verbose", action="store_true", help="Afficher la matrice complète")
    args = parser.parse_args()
    run_test(force_demo=args.demo, verbose=args.verbose)
