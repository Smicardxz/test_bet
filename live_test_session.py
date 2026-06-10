"""
LiveTestSession — Mode test live contrôlé
==========================================

DEUX UNIVERS OFFICIELS:
  UNIVERSE_A = STATISTICAL_ONLY
    · ligues non couvertes odds / clé absente
    · moteur statistique uniquement
    · S/A/B/WATCHLIST tiers possibles
    · Objectif: détecter patterns rares

  UNIVERSE_B = MARKET_EV
    · odds disponibles + EV calculable
    · implied probabilities + market comparison
    · S/A/WATCHLIST EV tiers

COVERAGE_QUALITY:
  FULL    — odds matchées avec haute confiance (≥0.80)
  PARTIAL — odds matchées mais incertaines (<0.80)
  NONE    — pas d'odds / clé absente

Règle fondamentale : un CSV vide signifie un bug, pas l'absence d'odds.

Usage:
    python live_test_session.py              # Snapshot (picks du jour)
    python live_test_session.py --refresh    # Force rescan puis snapshot
    python live_test_session.py --fill       # Remplir les résultats réels
    python live_test_session.py --report     # Audit qualité sur CSV existant
    python live_test_session.py --min-conf 50  # Seuil conf minimum (défaut: 40)
    python live_test_session.py --url http://localhost:5001

Sorties:
    live_test_session_YYYYMMDD.csv      — tous les picks (stat + EV, 2 univers)
    live_test_session_YYYYMMDD.json     — version riche avec diagnostics
"""

import argparse
import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Config ───────────────────────────────────────────────────────────────────
DEFAULT_API      = "http://localhost:5000"
MIN_CONFIDENCE   = 40.0          # seuil minimum pour apparaître dans le CSV
STATUSES_TO_TRACK = {"UPCOMING", "LIVE"}

# Univers officiels
UNIVERSE_A = "STATISTICAL_ONLY"
UNIVERSE_B = "MARKET_EV"

# Coverage quality
COVERAGE_FULL    = "FULL"
COVERAGE_PARTIAL = "PARTIAL"
COVERAGE_NONE    = "NONE"

# Tiers statistiques valables pour export (sans odds requis)
STAT_TIERS_EXPORT = {"S_TIER", "A_TIER", "B_TIER", "WATCHLIST"}
# Tiers EV valables pour export (avec odds)
EV_TIERS_EXPORT   = {"S_TIER", "A_TIER"}

CSV_COLUMNS = [
    # Identification
    "fixture_id",
    "match",
    "league",
    "country",
    "kickoff",
    "status",
    # ── Universe classification ────────────────────────────
    "match_universe",             # STATISTICAL_ONLY | MARKET_EV
    "coverage_quality",           # FULL | PARTIAL | NONE
    # ── Dual-tier architecture ─────────────────────────────
    "statistical_tier",           # modèle pur, sans odds
    "statistical_ranking_score",  # score composite 0-1
    "ev_tier",                    # S/A/WATCHLIST si odds, sinon WAITING_FOR_ODDS
    "has_odds",                   # bool
    "is_statistical_pick",        # stat_tier in S/A/B
    "is_ev_pick",                 # ev_tier in S/A
    "odds_status",                # ODDS_MISSING | NO_KEY | FOUND | ...
    # ── Market ────────────────────────────────────────────
    "market",
    "model_probability",
    "fair_odd",
    "bookmaker_odd",
    "edge_percent",
    "ev_percent",
    # ── Scores modèle ─────────────────────────────────────
    "confidence_score",
    "volatility_score",
    "chaos_score",
    "stability_index",
    "false_signal_score",
    "league_reliability_score",
    "weighted_goal_projection",
    "weighted_tempo",
    "home_strength_index",
    "away_weakness_index",
    "matchup_asymmetry_score",
    "refuse_pick",
    "tier_downgrade",
    "volatility_tags",
    "false_signal_tags",
    "league_tags",
    "confidence_adjustments",
    "reasons",
    "session_time",
    "final_result",      # vide à la capture → à remplir après
    "result_correct",    # vide à la capture
    "result_notes",      # vide à la capture
]

# ─── Couleurs ─────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

STAT_TIER_COLOR = {
    "S_TIER":    f"{BOLD}{GREEN}",
    "A_TIER":    f"{GREEN}",
    "B_TIER":    f"{CYAN}",
    "WATCHLIST": f"{YELLOW}",
    "NO_VALUE":  "",
}
EV_TIER_COLOR = {
    "S_TIER":           f"{BOLD}{GREEN}",
    "A_TIER":           f"{GREEN}",
    "WATCHLIST":        f"{YELLOW}",
    "WAITING_FOR_ODDS": f"{YELLOW}",
    "NO_EV":            "",
}
TIER_ORDER = {"S_TIER": 0, "A_TIER": 1, "B_TIER": 2, "WATCHLIST": 3, "NO_VALUE": 9}

UNIVERSE_COLOR = {
    UNIVERSE_A: f"{CYAN}",
    UNIVERSE_B: f"{BOLD}{GREEN}",
}
COVERAGE_COLOR = {
    COVERAGE_FULL:    f"{GREEN}",
    COVERAGE_PARTIAL: f"{YELLOW}",
    COVERAGE_NONE:    f"",
}


# ─── HTTP helper ──────────────────────────────────────────────────────────────
def _api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─── Fetch ────────────────────────────────────────────────────────────────────
def fetch_matches(api_base: str) -> list:
    """Récupère tous les matchs analysés (UPCOMING + LIVE)."""
    all_matches = []
    for status in ("upcoming", "live"):
        try:
            url = f"{api_base}/api/matches?status={status}&limit=500&analyzed=true"
            data = _api_get(url)
            if data.get("success") and data.get("matches"):
                all_matches.extend(data["matches"])
        except Exception as e:
            print(f"  {YELLOW}⚠ Impossible de récupérer '{status}': {e}{RESET}")

    if not all_matches:
        try:
            data = _api_get(f"{api_base}/api/matches?limit=500")
            if data.get("success"):
                all_matches = [m for m in (data.get("matches") or [])
                               if m.get("status") in STATUSES_TO_TRACK]
        except Exception as e:
            print(f"  {RED}✗ Fallback échoué: {e}{RESET}")

    return all_matches


# ─── Filter ───────────────────────────────────────────────────────────────────
def _should_export(m: dict, min_conf: float) -> tuple:
    """
    Retourne (include: bool, reason: str) selon les nouvelles règles d'inclusion.

    Inclure si :
      - statistical_tier in S/A/B/WATCHLIST  (modèle pur, sans odds)
      OR
      - ev_tier in S/A  (avec odds + EV)
      OR
      - confidence_score >= min_conf
    Exclure si :
      - status not in UPCOMING/LIVE
      - refuse_pick = True
    """
    if m.get("status") not in STATUSES_TO_TRACK:
        return False, "wrong_status"
    if m.get("refuse_pick"):
        return False, "refused"

    stat_tier = m.get("statistical_tier", "NO_VALUE")
    ev_tier   = m.get("ev_tier", "WAITING_FOR_ODDS")
    conf      = m.get("confidence_score", 0.0) or 0.0

    if stat_tier in STAT_TIERS_EXPORT:
        return True, f"stat_tier={stat_tier}"
    if ev_tier in EV_TIERS_EXPORT:
        return True, f"ev_tier={ev_tier}"
    if conf >= min_conf:
        return True, f"conf={conf:.0f}%"

    return False, "below_threshold"


# ─── Extract ──────────────────────────────────────────────────────────────────
def extract_pick(m: dict, session_time: str) -> dict:
    """Extrait tous les champs d'un match normalisé vers une ligne de pick."""

    best_angle = m.get("best_angle") or {}
    best_stat  = m.get("best_statistical_angle") or {}
    market = (best_angle.get("market") or best_stat.get("market") or "")

    conf       = float(m.get("confidence_score", 0.0) or 0.0)
    model_prob = round(conf / 100.0, 4) if conf > 0 else None

    fair_odd = best_angle.get("fair_odd")
    if fair_odd is None and model_prob and model_prob > 0:
        fair_odd = round(1.0 / model_prob, 3)

    bookmaker_odd = best_angle.get("market_odd")
    edge_pct      = float(best_angle.get("edge_percent", 0.0) or 0.0)

    best_ev = m.get("best_ev_opportunity") or {}
    ev_pct  = float(best_ev.get("expected_value_percent", 0.0)) if best_ev else 0.0

    reasons_parts = []
    for item in (m.get("confidence_adjustments") or []):
        reasons_parts.append(str(item))
    for item in (m.get("false_signal_reasons") or []):
        reasons_parts.append(str(item))
    if m.get("refuse_pick_reason"):
        reasons_parts.append(f"REFUSED: {m['refuse_pick_reason']}")
    reasons_str = " | ".join(reasons_parts) if reasons_parts else ""

    return {
        # Identification
        "fixture_id":                m.get("fixture_id", ""),
        "match":                     f"{m.get('home_team','')} vs {m.get('away_team','')}",
        "league":                    m.get("league", ""),
        "country":                   m.get("country", ""),
        "kickoff":                   m.get("kickoff_time", ""),
        "status":                    m.get("status", ""),
        # Universe
        "match_universe":            m.get("match_universe", UNIVERSE_A),
        "coverage_quality":          m.get("coverage_quality", COVERAGE_NONE),
        # Dual-tier
        "statistical_tier":          m.get("statistical_tier", "NO_VALUE"),
        "statistical_ranking_score": round(float(m.get("statistical_ranking_score", 0.0) or 0.0), 3),
        "ev_tier":                   m.get("ev_tier", "WAITING_FOR_ODDS"),
        "has_odds":                  bool(m.get("has_odds")),
        "is_statistical_pick":       bool(m.get("is_statistical_pick")),
        "is_ev_pick":                bool(m.get("is_ev_pick")),
        "odds_status":               m.get("odds_status", "ODDS_MISSING"),
        # Market
        "market":                    market,
        "model_probability":         model_prob,
        "fair_odd":                  fair_odd,
        "bookmaker_odd":             bookmaker_odd,
        "edge_percent":              round(edge_pct, 2),
        "ev_percent":                round(ev_pct, 2),
        # Scores
        "confidence_score":          round(conf, 1),
        "volatility_score":          float(m.get("volatility_score", 0.0) or 0.0),
        "chaos_score":               float(m.get("chaos_score", 0.0) or 0.0),
        "stability_index":           float(m.get("stability_index", 50.0) or 50.0),
        "false_signal_score":        float(m.get("false_signal_score", 0.0) or 0.0),
        "league_reliability_score":  float(m.get("league_reliability_score", 0.0) or 0.0),
        "weighted_goal_projection":  float(m.get("weighted_goal_projection", 0.0) or 0.0),
        "weighted_tempo":            m.get("weighted_tempo_projection", ""),
        "home_strength_index":       float(m.get("home_strength_index", 50.0) or 50.0),
        "away_weakness_index":       float(m.get("away_weakness_index", 50.0) or 50.0),
        "matchup_asymmetry_score":   float(m.get("matchup_asymmetry_score", 0.0) or 0.0),
        "refuse_pick":               bool(m.get("refuse_pick")),
        "tier_downgrade":            bool(m.get("tier_downgrade")),
        "volatility_tags":           "|".join(m.get("volatility_tags") or []),
        "false_signal_tags":         "|".join(m.get("false_signal_tags") or []),
        "league_tags":               "|".join(m.get("league_tags") or []),
        "confidence_adjustments":    "|".join(m.get("confidence_adjustments") or []),
        "reasons":                   reasons_str,
        "session_time":              session_time,
        "final_result":              "",
        "result_correct":            "",
        "result_notes":              "",
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────
def force_refresh(api_base: str, timeout_s: int = 300, poll_interval_s: int = 15):
    """Force un nouveau scan via /api/refresh et attend sa complétion."""
    import time

    print(f"  {YELLOW}→ Forçage du rescan...{RESET}")
    try:
        _api_get(f"{api_base}/api/refresh")
        print(f"  {GREEN}✓ Rescan déclenché.{RESET}")
    except Exception as e:
        print(f"  {YELLOW}⚠ /api/refresh indisponible: {e}{RESET}")
        return

    print(f"  {YELLOW}  En attente de la fin du scan (max {timeout_s}s)...{RESET}")
    elapsed = 0
    while elapsed < timeout_s:
        time.sleep(poll_interval_s)
        elapsed += poll_interval_s
        try:
            data = _api_get(f"{api_base}/api/matches?limit=5")
            n = len(data.get("matches") or [])
            if n > 0:
                print(f"  {GREEN}✓ Scan terminé ({elapsed}s) — {n} matchs disponibles.{RESET}")
                return
            print(f"  {YELLOW}  [{elapsed}s] scan en cours...{RESET}")
        except Exception:
            pass

    print(f"  {YELLOW}⚠ Timeout atteint ({timeout_s}s) — le scan n'est peut-être pas terminé.{RESET}")


def _build_diagnostics(all_matches: list, picks: list, refused: list) -> dict:
    """Calcule les compteurs de diagnostic, incluant les 2 univers."""
    upcoming_live = [m for m in all_matches if m.get("status") in STATUSES_TO_TRACK]
    total_analyzed = sum(1 for m in upcoming_live if m.get("analyzed"))

    def _count_stat(tier):
        return sum(1 for m in upcoming_live if m.get("statistical_tier") == tier)

    def _count_ev(tier):
        return sum(1 for m in upcoming_live if m.get("ev_tier") == tier)

    def _count_universe(u):
        return sum(1 for m in upcoming_live if m.get("match_universe") == u)

    def _count_coverage(q):
        return sum(1 for m in upcoming_live if m.get("coverage_quality") == q)

    ua_picks = [p for p in picks if p.get("match_universe") == UNIVERSE_A]
    ub_picks = [p for p in picks if p.get("match_universe") == UNIVERSE_B]

    return {
        "total_matches":           len(all_matches),
        "upcoming_live":           len(upcoming_live),
        "total_analyzed":          total_analyzed,
        # Universe counts
        "universe_a_count":        _count_universe(UNIVERSE_A),
        "universe_b_count":        _count_universe(UNIVERSE_B),
        "universe_a_picks":        len(ua_picks),
        "universe_b_picks":        len(ub_picks),
        # Coverage quality
        "coverage_full":           _count_coverage(COVERAGE_FULL),
        "coverage_partial":        _count_coverage(COVERAGE_PARTIAL),
        "coverage_none":           _count_coverage(COVERAGE_NONE),
        # Statistical tier
        "statistical_s_tier":      _count_stat("S_TIER"),
        "statistical_a_tier":      _count_stat("A_TIER"),
        "statistical_b_tier":      _count_stat("B_TIER"),
        "statistical_watchlist":   _count_stat("WATCHLIST"),
        # EV tier
        "ev_s_tier":               _count_ev("S_TIER"),
        "ev_a_tier":               _count_ev("A_TIER"),
        # Odds
        "odds_missing":            sum(1 for m in upcoming_live if not m.get("has_odds")),
        "odds_matched":            sum(1 for m in upcoming_live if m.get("has_odds")),
        "refused_picks":           len(refused),
        "exported_picks":          len(picks),
        "stale_intelligence":      all(
            (m.get("false_signal_score") or 0) == 0 and (m.get("chaos_score") or 0) == 0
            for m in picks
        ) if picks else False,
    }


def _print_diagnostics(diag: dict):
    """Affiche le tableau de bord diagnostics — 2 univers."""
    print(f"\n  {BOLD}── Diagnostics ─────────────────────────────────────{RESET}")
    print(f"  Total matchs:   {diag['total_matches']:<5}  Analysés: {diag['total_analyzed']}")
    print(f"  Upcoming+Live:  {diag['upcoming_live']}")

    # ── Univers ──────────────────────────────────────────────────────────────
    ua   = diag.get("universe_a_count", 0)
    ub   = diag.get("universe_b_count", 0)
    ua_p = diag.get("universe_a_picks", 0)
    ub_p = diag.get("universe_b_picks", 0)
    cf   = diag.get("coverage_full", 0)
    cp   = diag.get("coverage_partial", 0)

    print(f"\n  {BOLD}◆ UNIVERSE A — STATISTICAL_ONLY{RESET}  ({CYAN}{ua} matchs, {ua_p} picks{RESET})")
    print(f"    Coverage NONE  : {diag.get('coverage_none', 0)}  (pas d'odds)")
    for tier, key in [("S_TIER","statistical_s_tier"),("A_TIER","statistical_a_tier"),
                      ("B_TIER","statistical_b_tier"),("WATCHLIST","statistical_watchlist")]:
        c = STAT_TIER_COLOR.get(tier, "")
        n = diag[key]
        bar = "█" * min(n, 20)
        print(f"    {c}{tier:<12}{RESET}: {n:>3}  {bar}")

    print(f"\n  {BOLD}◆ UNIVERSE B — MARKET_EV{RESET}  ({GREEN}{ub} matchs, {ub_p} picks{RESET})")
    print(f"    Coverage FULL  : {GREEN}{cf}{RESET}  |  PARTIAL: {YELLOW}{cp}{RESET}")
    for tier, key in [("S_TIER","ev_s_tier"),("A_TIER","ev_a_tier")]:
        c = EV_TIER_COLOR.get(tier, "")
        n = diag[key]
        print(f"    {c}{tier:<12}{RESET}: {n:>3}")

    print(f"\n  Refusés (VolatilityEngine): {diag['refused_picks']}")
    print(f"  Exportés dans CSV:          {BOLD}{diag['exported_picks']}{RESET}  "
          f"({CYAN}A:{ua_p}{RESET} + {GREEN}B:{ub_p}{RESET})")

    if diag.get("stale_intelligence"):
        print(f"\n  {YELLOW}⚠  Intelligence stale: chaos=0 et fss=0 partout.{RESET}")
        print(f"  {YELLOW}   Fix: python live_test_session.py --refresh{RESET}")
    print(f"  {'─'*50}")


# ─── Snapshot ─────────────────────────────────────────────────────────────────
def snapshot(api_base: str, date_str: str, min_conf: float = MIN_CONFIDENCE) -> int:
    """Capture les picks du jour et exporte CSV + JSON. Jamais vide si bons profils."""

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  LIVE TEST SESSION v3 — {date_str}{RESET}")
    print(f"{BOLD}  {CYAN}Universe A: STATISTICAL_ONLY{RESET}{BOLD}  |  {GREEN}Universe B: MARKET_EV{RESET}")
    print(f"{BOLD}{'═'*66}{RESET}")
    print(f"  API: {CYAN}{api_base}{RESET}  |  min_conf={min_conf}%")

    try:
        health = _api_get(f"{api_base}/api/health")
        print(f"  {GREEN}✓ API ({health.get('status','?')}){RESET}")
    except Exception as e:
        print(f"  {RED}✗ API inaccessible: {e}{RESET}")
        print(f"  {YELLOW}Lance 'python app_flask.py' puis réessaie.{RESET}\n")
        return 0

    print(f"\n  Fetching matches...")
    all_matches = fetch_matches(api_base)

    session_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    picks, refused, excluded = [], [], []

    for m in all_matches:
        include, reason = _should_export(m, min_conf)
        if not include:
            if reason == "refused":
                refused.append(m)
            else:
                excluded.append(m)
            continue
        picks.append(extract_pick(m, session_time))

    # Tri: stat_tier primaire, puis confidence desc
    picks.sort(key=lambda p: (
        TIER_ORDER.get(p["statistical_tier"], 9),
        -(p["confidence_score"] or 0),
    ))

    # Diagnostics
    diag = _build_diagnostics(all_matches, picks, refused)
    _print_diagnostics(diag)

    if not picks:
        print(f"\n  {RED}✗ AUCUN PICK EXPORTÉ{RESET}")
        print(f"  Vérifications:")
        print(f"    1. Le scan a-t-il tourné ? → python live_test_session.py --refresh")
        print(f"    2. Des matchs sont-ils analysés ? (total_analyzed={diag['total_analyzed']})")
        print(f"    3. Trop strict ? → python live_test_session.py --min-conf 20\n")
        return 0

    # CSV
    csv_path = f"live_test_session_{date_str}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(picks)
    print(f"\n  {GREEN}✓ CSV: {csv_path}  ({len(picks)} picks){RESET}")

    # JSON (riche avec diagnostics)
    json_path = f"live_test_session_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "session_date":  date_str,
            "session_time":  session_time,
            "api_base":      api_base,
            "min_conf":      min_conf,
            "universes": {
                "universe_a": {"name": UNIVERSE_A, "picks": [p for p in picks if p.get("match_universe") == UNIVERSE_A]},
                "universe_b": {"name": UNIVERSE_B, "picks": [p for p in picks if p.get("match_universe") == UNIVERSE_B]},
            },
            "diagnostics":   diag,
            "picks":         picks,
            "refused_details": [
                {
                    "match":         f"{m.get('home_team','')} vs {m.get('away_team','')}",
                    "league":        m.get("league", ""),
                    "stat_tier":     m.get("statistical_tier", ""),
                    "refuse_reason": m.get("refuse_pick_reason", ""),
                    "volatility":    m.get("volatility_score", 0),
                    "chaos":         m.get("chaos_score", 0),
                }
                for m in refused
            ],
        }, f, indent=2, ensure_ascii=False)
    print(f"  {GREEN}✓ JSON: {json_path}{RESET}")

    _print_picks_table(picks, refused)
    return len(picks)


# ─── Table ────────────────────────────────────────────────────────────────────
def _print_one_pick(p: dict):
    """Affiche une ligne de pick détaillée."""
    st   = p["statistical_tier"]
    evt  = p["ev_tier"]
    cov  = p.get("coverage_quality", COVERAGE_NONE)
    sc   = STAT_TIER_COLOR.get(st, "")
    ec   = EV_TIER_COLOR.get(evt, "")
    cc   = COVERAGE_COLOR.get(cov, "")
    match  = p["match"][:32].ljust(32)
    league = p["league"][:18].ljust(18)
    market = p["market"][:16].ljust(16)
    conf   = p["confidence_score"]
    ev     = p["ev_percent"]
    vol    = p["volatility_score"]
    fss    = p["false_signal_score"]
    flags  = ""
    if p["tier_downgrade"]: flags += " ⚠TDWN"
    if p["volatility_tags"]: flags += f" [{p['volatility_tags'][:20]}]"
    cov_str = f" cov:{cc}{cov}{RESET}" if cov != COVERAGE_NONE else ""

    print(f"  {sc}{st:<10}{RESET} ev:{ec}{evt:<18}{RESET}{cov_str} conf={conf:.0f}%")
    print(f"    {match} {CYAN}{league}{RESET}")
    print(f"    {market} vol={vol:.0f} fss={fss:.0f} EV={ev:+.1f}%{flags}")
    if p["confidence_adjustments"]:
        print(f"    {CYAN}→ {p['confidence_adjustments'][:80]}{RESET}")
    if p["league_tags"]:
        print(f"    {YELLOW}⚑ {p['league_tags']}{RESET}")


def _print_picks_table(picks: list, refused: list):
    """Affiche les picks séparés en 2 univers officiels."""
    ua_picks = [p for p in picks if p.get("match_universe") == UNIVERSE_A]
    ub_picks = [p for p in picks if p.get("match_universe") == UNIVERSE_B]

    # ── UNIVERSE A ────────────────────────────────────────────────────────────
    print(f"\n{'═'*66}")
    print(f"{BOLD}{CYAN}  ◆ UNIVERSE A — STATISTICAL_ONLY  ({len(ua_picks)} picks){RESET}")
    print(f"{CYAN}    Modèle statistique pur · Pas d'odds requis · S/A/B/WATCHLIST tiers{RESET}")
    print(f"{'─'*66}")
    if ua_picks:
        for p in ua_picks:
            _print_one_pick(p)
    else:
        print(f"  {YELLOW}Aucun pick Universe A{RESET}")

    # ── UNIVERSE B ────────────────────────────────────────────────────────────
    print(f"\n{'═'*66}")
    print(f"{BOLD}{GREEN}  ◆ UNIVERSE B — MARKET_EV  ({len(ub_picks)} picks){RESET}")
    print(f"{GREEN}    EV calculé · Implied probabilities · Market comparison{RESET}")
    print(f"{'─'*66}")
    if ub_picks:
        for p in ub_picks:
            _print_one_pick(p)
    else:
        print(f"  {YELLOW}Aucun pick Universe B  (pas d'odds disponibles){RESET}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*66}")
    stat_picks = sum(1 for p in picks if p["is_statistical_pick"])
    ev_picks   = sum(1 for p in picks if p["is_ev_pick"])
    print(f"  Total: {len(picks)} picks  |  "
          f"{CYAN}A:{len(ua_picks)}{RESET} + {GREEN}B:{len(ub_picks)}{RESET}  |  "
          f"is_stat={stat_picks}  is_ev={ev_picks}")

    if refused:
        print(f"\n{'─'*66}")
        print(f"  {RED}REFUSÉS PAR VOLATILITYENGINE ({len(refused)}){RESET}")
        for m in refused:
            name = f"{m.get('home_team','')} vs {m.get('away_team','')} ({m.get('league','')})"
            print(f"  {RED}✗{RESET} {name[:55]}  vol={m.get('volatility_score',0):.0f}")

    print(f"{'═'*66}\n")


# ─── Provider / Repo helpers ──────────────────────────────────────────────────
def _get_provider():
    """Load ApiFootballProvider (needs API_FOOTBALL_KEY in .env)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dotenv import load_dotenv
        load_dotenv(override=True)
        from app.providers.api_football_provider import ApiFootballProvider
        return ApiFootballProvider()
    except Exception as exc:
        print(f"  {YELLOW}⚠ Provider non disponible: {exc}{RESET}")
        return None


def _get_repo():
    """Load SupabaseRepository — returns None if not configured."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        from app.database.supabase_config import reset_supabase_config, get_supabase_config
        from app.database.supabase_repository import reset_repository, get_repository
        reset_supabase_config()
        reset_repository()
        repo = get_repository()
        return repo if repo.supabase_connected else None
    except Exception:
        return None


# ─── Auto-fill ────────────────────────────────────────────────────────────────
def auto_fill_results(date_str: str, interactive: bool = True):
    """
    Auto-fill résultats via API-Football.

    interactive=True  → demande manuelle si API indisponible ou match non terminé
    interactive=False → --auto-fill strict, aucune question
    """
    csv_path = f"live_test_session_{date_str}.csv"
    if not os.path.exists(csv_path):
        print(f"{RED}Fichier {csv_path} introuvable.{RESET}")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    pending = [r for r in rows if not r.get("final_result")]
    if not pending:
        print(f"{YELLOW}Tous les résultats déjà remplis.{RESET}")
        _print_report(rows)
        return

    mode = "AUTO-FILL" if not interactive else "AUTO-FILL + fallback manuel"
    print(f"\n{BOLD}REMPLISSAGE RÉSULTATS — {date_str}  [{mode}]{RESET}")
    print(f"  {len(pending)} picks à traiter\n")

    provider = _get_provider()
    repo     = _get_repo()

    if provider:
        from app.services.settlement.auto_settler import settle_csv_row
    else:
        settle_csv_row = None
        if not interactive:
            print(f"  {RED}✗ Provider indisponible et mode non-interactif — abandon.{RESET}")
            return
        print(f"  {YELLOW}⚠ Provider indisponible — mode manuel activé.{RESET}\n")

    auto_ok = 0
    manual_needed = []

    for row in rows:
        if row.get("final_result"):
            continue

        st     = row.get("statistical_tier", "?")
        sc     = STAT_TIER_COLOR.get(st, "")
        market = row.get("market", "")
        match  = row.get("match", "?")

        if settle_csv_row:
            settled = settle_csv_row(row, provider)

            if settled["settled"]:
                row["final_result"]   = settled["final_result"]
                row["result_correct"] = settled["result_correct"]
                row["result_notes"]   = settled["result_notes"]
                auto_ok += 1
                rc = settled["result_correct"]
                color = GREEN if rc == "WIN" else RED if rc == "LOSS" else YELLOW
                print(f"  {color}✓ {rc}{RESET}  {sc}{st}{RESET} | {match[:32]} | {market} "
                      f"({settled['final_result']}) HT:{settled.get('ht_score','')}")

                # Supabase Phase 4: update prediction status
                if repo:
                    try:
                        from app.services.settlement.auto_settler import fetch_final_result
                        result = fetch_final_result(row.get("fixture_id", ""), provider)
                        if result["status"] == "FINISHED":
                            from app.database.supabase_repository import _extract_primary_market  # noqa
                            # Find the prediction_id by fixture+market+date
                            pred_date = date_str[:4]+"-"+date_str[4:6]+"-"+date_str[6:]
                            pred_id   = f"{row.get('fixture_id','')}_{market}_{pred_date}"
                            repo.settle_prediction(
                                prediction_id = pred_id,
                                home_score    = result["ft_home_goals"],
                                away_score    = result["ft_away_goals"],
                                ht_home       = result["ht_home_goals"],
                                ht_away       = result["ht_away_goals"],
                                bookmaker_odd = float(row.get("bookmaker_odd") or 1.0),
                                notes         = f"auto_settled csv HT:{result['ht_home_goals']}-{result['ht_away_goals']}",
                            )
                            repo.update_fixture_result(
                                fixture_id = str(row.get("fixture_id", "")),
                                home_score = result["ft_home_goals"],
                                away_score = result["ft_away_goals"],
                                ht_home    = result["ht_home_goals"],
                                ht_away    = result["ht_away_goals"],
                            )
                    except Exception:
                        pass
                continue

            notes = settled.get("result_notes", "")
            if notes == "NOT_FINISHED":
                print(f"  {YELLOW}⏳ PENDING{RESET}  {match[:35]} | {market}")
                continue

            # RESULT_MISSING or API_ERROR → manual fallback
            if not interactive:
                print(f"  {YELLOW}⚠ SKIP{RESET}  {match[:35]} | {notes}")
                continue

        manual_needed.append(row)

    # ── Manual fallback ──────────────────────────────────────────────────────
    if manual_needed and interactive:
        print(f"\n  {YELLOW}{len(manual_needed)} picks nécessitent saisie manuelle:{RESET}\n")
        for row in manual_needed:
            st      = row.get("statistical_tier", "?")
            evt     = row.get("ev_tier", "?")
            sc      = STAT_TIER_COLOR.get(st, "")
            market  = row.get("market", "")
            kickoff = row.get("kickoff", "")
            is_ht   = "HT" in market.upper()

            print(f"\n  {sc}{st}{RESET} ev:{evt} | {row.get('match','?')} | {CYAN}{market}{RESET} | {kickoff}")
            print(f"  Conf={row.get('confidence_score',0)}% | Vol={row.get('volatility_score',0)} "
                  f"| FSS={row.get('false_signal_score',0)}")

            score = input("  Score FT (ex: 1-2, CANCELLED) [Entrée=skip]: ").strip()
            if not score:
                continue

            ht_score = ""
            if is_ht:
                ht_score = input("  Score HT (ex: 0-0) [requis pour marché HT]: ").strip()

            row["final_result"]   = score
            row["result_correct"] = _evaluate_result(market, score, ht_score)
            row["result_notes"]   = input("  Notes (optionnel): ").strip()

            ok = row["result_correct"]
            print(f"  → {GREEN+'✓ WIN'+RESET if ok=='WIN' else RED+'✗ LOSS'+RESET if ok=='LOSS' else YELLOW+ok+RESET}")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    total_auto = auto_ok
    total_manual = len([r for r in rows if r.get("final_result") and
                        r.get("result_notes","") and "auto" not in r.get("result_notes","")])
    print(f"\n  {GREEN}✓ CSV mis à jour: {csv_path}{RESET}  "
          f"(auto={total_auto}  manuel={total_manual})")
    _print_report(rows)


# ─── Fill ─────────────────────────────────────────────────────────────────────
def fill_results(date_str: str):
    """Mode interactif: auto-fill d'abord, puis saisie manuelle pour les cas restants."""
    auto_fill_results(date_str, interactive=True)


# ─── Evaluate ─────────────────────────────────────────────────────────────────
def _evaluate_result(market: str, score_str: str, ht_score_str: str = "") -> str:
    """
    Evaluate market outcome.
    Handles both FT_UNDER_2_5 and 'UNDER 2.5' formats, and HT markets.
    """
    try:
        parts = score_str.replace(" ", "").split("-")
        if len(parts) != 2:
            return "UNKNOWN"
        home_g, away_g = int(parts[0]), int(parts[1])
        total_ft = home_g + away_g

        # Parse HT score
        total_ht = ht_home_g = ht_away_g = 0
        if ht_score_str:
            ht_parts = ht_score_str.replace(" ", "").split("-")
            if len(ht_parts) == 2:
                try:
                    ht_home_g, ht_away_g = int(ht_parts[0]), int(ht_parts[1])
                    total_ht = ht_home_g + ht_away_g
                except ValueError:
                    pass

        # Normalise: upper + spaces/dots → underscores
        m = market.upper().replace(" ", "_").replace(".", "_")

        # HT markets (evaluated on HT goals)
        if "HT_UNDER_0_5" in m: return "WIN" if total_ht == 0  else "LOSS"
        if "HT_UNDER_1_5" in m: return "WIN" if total_ht <= 1  else "LOSS"
        if "HT_UNDER_2_5" in m: return "WIN" if total_ht <= 2  else "LOSS"
        if "HT_OVER_0_5"  in m: return "WIN" if total_ht >= 1  else "LOSS"
        if "HT_OVER_1_5"  in m: return "WIN" if total_ht >= 2  else "LOSS"

        # FT markets (evaluated on FT goals)
        if "UNDER_0_5" in m: return "WIN" if total_ft == 0  else "LOSS"
        if "UNDER_1_5" in m: return "WIN" if total_ft <= 1  else "LOSS"
        if "UNDER_2_5" in m: return "WIN" if total_ft <= 2  else "LOSS"
        if "UNDER_3_5" in m: return "WIN" if total_ft <= 3  else "LOSS"
        if "OVER_0_5"  in m: return "WIN" if total_ft >= 1  else "LOSS"
        if "OVER_1_5"  in m: return "WIN" if total_ft >= 2  else "LOSS"
        if "OVER_2_5"  in m: return "WIN" if total_ft >= 3  else "LOSS"
        if "OVER_3_5"  in m: return "WIN" if total_ft >= 4  else "LOSS"
        if "BTTS_YES"  in m or m == "BTTS": return "WIN" if (home_g>0 and away_g>0) else "LOSS"
        if "BTTS_NO"   in m: return "WIN" if not (home_g>0 and away_g>0) else "LOSS"
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


# ─── Report ───────────────────────────────────────────────────────────────────
def _print_report(rows: list):
    """Rapport d'audit qualité complet: par univers, tier, marché, ligue, P/L."""
    all_with_result = [r for r in rows if r.get("final_result")]
    filled  = [r for r in all_with_result if r.get("result_correct") in ("WIN","LOSS","VOID")]
    pending = [r for r in rows if not r.get("final_result")]
    void_r  = [r for r in filled if r.get("result_correct") == "VOID"]

    print(f"\n{'═'*66}")
    print(f"{BOLD}  RAPPORT QUALITÉ — 2 UNIVERS{RESET}")
    print(f"{'═'*66}")

    if not filled and not pending:
        print(f"  {YELLOW}Aucun résultat à analyser encore.{RESET}")
        print(f"{'═'*66}\n")
        return

    def _hr(wins, total):
        return f"{wins}/{total} ({wins/total*100:.0f}%)" if total > 0 else "—"

    def _pl(result_rows):
        total = 0.0
        for r in result_rows:
            rc  = r.get("result_correct", "")
            odd = float(r.get("bookmaker_odd") or 0)
            if rc == "WIN" and odd > 1.0:
                total += odd - 1.0
            elif rc == "LOSS":
                total -= 1.0
        return round(total, 2)

    total   = len(filled)
    wins    = sum(1 for r in filled if r["result_correct"] == "WIN")
    losses  = sum(1 for r in filled if r["result_correct"] == "LOSS")
    voids   = len(void_r)
    pl      = _pl(filled)
    roi_pct = (pl / max(total - voids, 1)) * 100

    print(f"  Settled: {BOLD}{total}{RESET}  |  "
          f"{GREEN}W:{wins}{RESET}  {RED}L:{losses}{RESET}  "
          f"{YELLOW}V:{voids}{RESET}  |  "
          f"{YELLOW}Pending:{len(pending)}{RESET}")
    if total > 0:
        print(f"  Hit rate: {BOLD}{wins/total*100:.1f}%{RESET}  |  "
              f"P/L: {GREEN if pl>=0 else RED}{pl:+.2f}u{RESET}  |  "
              f"ROI: {GREEN if roi_pct>=0 else RED}{roi_pct:+.1f}%{RESET}")

    # ── UNIVERSE A ────────────────────────────────────────────────────────────
    ua_rows = [r for r in filled if r.get("match_universe") == UNIVERSE_A]
    print(f"\n  {BOLD}{CYAN}◆ UNIVERSE A — STATISTICAL_ONLY  ({len(ua_rows)} évalués){RESET}")
    for tier in ("S_TIER", "A_TIER", "B_TIER", "WATCHLIST"):
        t_rows = [r for r in ua_rows if r.get("statistical_tier") == tier]
        if not t_rows:
            continue
        tw  = sum(1 for r in t_rows if r["result_correct"] == "WIN")
        tpl = _pl(t_rows)
        c   = STAT_TIER_COLOR.get(tier, "")
        print(f"    {c}{tier:<12}{RESET}: {_hr(tw, len(t_rows))}  P/L:{GREEN if tpl>=0 else RED}{tpl:+.2f}u{RESET}")

    # ── UNIVERSE B ────────────────────────────────────────────────────────────
    ub_rows = [r for r in filled if r.get("match_universe") == UNIVERSE_B]
    print(f"\n  {BOLD}{GREEN}◆ UNIVERSE B — MARKET_EV  ({len(ub_rows)} évalués){RESET}")
    for tier in ("S_TIER", "A_TIER"):
        t_rows = [r for r in ub_rows if r.get("ev_tier") == tier]
        if not t_rows:
            continue
        tw  = sum(1 for r in t_rows if r["result_correct"] == "WIN")
        tpl = _pl(t_rows)
        c   = EV_TIER_COLOR.get(tier, "")
        print(f"    EV {c}{tier:<12}{RESET}: {_hr(tw, len(t_rows))}  P/L:{GREEN if tpl>=0 else RED}{tpl:+.2f}u{RESET}")
    if not ub_rows:
        print(f"    {YELLOW}Pas encore de picks Universe B (attente d'odds){RESET}")

    # ── Par marché ────────────────────────────────────────────────────────────
    mkt_stats: dict = {}
    for r in filled:
        mk = r.get("market", "UNKNOWN")
        mkt_stats.setdefault(mk, {"w": 0, "l": 0, "v": 0, "pl": 0.0})
        rc  = r.get("result_correct", "")
        odd = float(r.get("bookmaker_odd") or 0)
        if rc == "WIN":  mkt_stats[mk]["w"] += 1; mkt_stats[mk]["pl"] += (odd-1) if odd>1 else 0
        elif rc=="LOSS": mkt_stats[mk]["l"] += 1; mkt_stats[mk]["pl"] -= 1
        elif rc=="VOID": mkt_stats[mk]["v"] += 1
    if mkt_stats:
        print(f"\n  {BOLD}Par marché:{RESET}")
        for mk, s in sorted(mkt_stats.items(), key=lambda x: -(x[1]["w"]+x[1]["l"])):
            t_mk = s["w"]+s["l"]
            hr   = f"{s['w']}/{t_mk} ({s['w']/t_mk*100:.0f}%)" if t_mk else "—"
            tpl  = round(s["pl"], 2)
            print(f"    {mk:<22}: {hr:<14}  P/L:{GREEN if tpl>=0 else RED}{tpl:+.2f}u{RESET}")

    # ── Par ligue ─────────────────────────────────────────────────────────────
    lg_stats: dict = {}
    for r in filled:
        lg = r.get("league", "?")
        lg_stats.setdefault(lg, {"w": 0, "l": 0, "v": 0, "pl": 0.0,
                                  "univ": r.get("match_universe", "?")})
        rc  = r.get("result_correct", "")
        odd = float(r.get("bookmaker_odd") or 0)
        if rc == "WIN":  lg_stats[lg]["w"] += 1; lg_stats[lg]["pl"] += (odd-1) if odd>1 else 0
        elif rc=="LOSS": lg_stats[lg]["l"] += 1; lg_stats[lg]["pl"] -= 1
        elif rc=="VOID": lg_stats[lg]["v"] += 1
    if lg_stats:
        print(f"\n  {BOLD}Par ligue:{RESET}")
        for lg, s in sorted(lg_stats.items(), key=lambda x: -(x[1]["w"]+x[1]["l"])):
            t_lg = s["w"]+s["l"]
            hr   = f"{s['w']}/{t_lg} ({s['w']/t_lg*100:.0f}%)" if t_lg else "—"
            tpl  = round(s["pl"], 2)
            flag = f" {RED}⚠{RESET}" if s["l"] > s["w"] else ""
            print(f"    [{s['univ'][:1]}] {lg[:28]:<30}: {hr:<12}  P/L:{GREEN if tpl>=0 else RED}{tpl:+.2f}u{RESET}{flag}")

    # ── Faux positifs ─────────────────────────────────────────────────────────
    false_pos = [r for r in filled
                 if r["result_correct"] == "LOSS" and float(r.get("false_signal_score") or 0) < 30]
    if false_pos:
        print(f"\n  {RED}{BOLD}Faux positifs potentiels ({len(false_pos)}):{RESET}")
        for r in false_pos:
            univ = r.get("match_universe", "?")
            conf = r.get("confidence_score", "?")
            print(f"    [{univ[:1]}] {r.get('match','?')[:35]} | {r.get('market','')} "
                  f"| conf={conf} fss={r.get('false_signal_score',0)}")

    # ── Picks encore pending ──────────────────────────────────────────────────
    if pending:
        print(f"\n  {YELLOW}⏳ {len(pending)} picks en attente de résultat{RESET}")
        for r in pending[:5]:
            print(f"    {r.get('match','?')[:35]} | {r.get('market','')}")
        if len(pending) > 5:
            print(f"    … +{len(pending)-5} autres")

    print(f"{'═'*66}\n")


def report(date_str: str):
    csv_path = f"live_test_session_{date_str}.csv"
    if not os.path.exists(csv_path):
        print(f"{RED}Fichier {csv_path} introuvable.{RESET}")
        return
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    _print_report(rows)


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LiveTestSession v2 — Mode test live contrôlé (dual-tier)"
    )
    parser.add_argument("--refresh",   action="store_true", help="Forcer un rescan avant snapshot")
    parser.add_argument("--fill",      action="store_true", help="Auto-fill résultats (+ fallback manuel)")
    parser.add_argument("--auto-fill", action="store_true", dest="auto_fill",
                        help="Auto-fill via API-Football uniquement — aucune question")
    parser.add_argument("--report",    action="store_true", help="Rapport qualité sur CSV existant")
    parser.add_argument("--date",     default=None,        help="Date YYYYMMDD (défaut: aujourd'hui)")
    parser.add_argument("--url",      default=DEFAULT_API, help="URL de l'API Flask")
    parser.add_argument("--min-conf", default=MIN_CONFIDENCE, type=float,
                        dest="min_conf", help=f"Seuil conf minimum (défaut: {MIN_CONFIDENCE})")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y%m%d")

    if args.auto_fill:
        auto_fill_results(date_str, interactive=False)
    elif args.fill:
        fill_results(date_str)
    elif args.report:
        report(date_str)
    else:
        if args.refresh:
            force_refresh(args.url)
        count = snapshot(args.url, date_str, min_conf=args.min_conf)
        if count == 0:
            sys.exit(1)
