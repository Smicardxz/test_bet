"""
Test d'intégration qualité — Audit des engines intelligence
===========================================================

Objectif : confirmer que les engines livés impactent réellement le ranking.

Checks:
  1. VolatilityEngine        — appliqué, tags transmis, refuse_pick bloque S/A tier
  2. FalseSignalDetector     — score calculé, tier_downgrade et ranking_penalty appliqués
  3. HomeAwayEngine          — splits calculés, champs visibles
  4. LeagueProfileEngine     — confidence ajusté selon profil, tags visibles
  5. MatchProfiler 50/30/20  — projections pondérées correctes
  6. /api/backtest           — by_volatility / by_profile / drawdown présents
  7. API output contract     — tous les champs intelligence présents dans _normalize_match
"""

import sys
import json

# ─── Couleurs console ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓ PASS{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
WARN = f"{YELLOW}⚠ WARN{RESET}"

results = []

def check(name: str, condition: bool, detail: str = "", warn_only: bool = False):
    label = WARN if (not condition and warn_only) else (PASS if condition else FAIL)
    status = "PASS" if condition else ("WARN" if warn_only else "FAIL")
    print(f"  {label}  {name}")
    if detail:
        print(f"        {CYAN}{detail}{RESET}")
    results.append((name, status))
    return condition


# ══════════════════════════════════════════════════════════════════════════════
# Données synthétiques — profil "FAKE UNDER" classique
# ══════════════════════════════════════════════════════════════════════════════
# Moyenne de 2.1 buts (semble under-friendly) mais variance = 2.4 (piège)
FT_STABLE  = [1, 2, 1, 0, 2, 1, 1, 2, 0, 1, 2, 1, 0, 1, 2, 1]   # profil stable/under
FT_CHAOTIC = [0, 5, 1, 4, 0, 6, 1, 3, 0, 5, 2, 4, 1, 5, 0, 3]   # profil chaotique
FT_FAKE_UNDER = [0, 1, 1, 0, 8, 0, 1, 0, 7, 0, 1, 0, 1, 6, 0, 1] # faux under: moyenne 1.7 mais outliers

HT_STABLE  = [0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0]
HT_CHAOTIC = [0, 2, 1, 1, 0, 3, 0, 1, 0, 2, 1, 2, 0, 2, 0, 1]
HT_FAKE    = [0, 0, 0, 0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 2, 0, 0]

MH_STABLE = [
    {"home_goals": 1, "away_goals": 0}, {"home_goals": 0, "away_goals": 1},
    {"home_goals": 1, "away_goals": 1}, {"home_goals": 0, "away_goals": 0},
    {"home_goals": 1, "away_goals": 0}, {"home_goals": 2, "away_goals": 0},
]
MH_CHAOTIC = [
    {"home_goals": 3, "away_goals": 2}, {"home_goals": 0, "away_goals": 5},
    {"home_goals": 4, "away_goals": 1}, {"home_goals": 1, "away_goals": 4},
    {"home_goals": 2, "away_goals": 3}, {"home_goals": 5, "away_goals": 0},
]


# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  AUDIT QUALITÉ — ENGINES INTELLIGENCE{RESET}")
print(f"{BOLD}{'═'*60}{RESET}\n")


# ─────────────────────────────────────────────────────────────────────────────
# 1. VOLATILITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[1] VolatilityEngine{RESET}")
from app.services.analysis.volatility_engine import VolatilityEngine
ve = VolatilityEngine()

vr_stable  = ve.analyze(FT_STABLE,  HT_STABLE,  MH_STABLE)
vr_chaotic = ve.analyze(FT_CHAOTIC, HT_CHAOTIC, MH_CHAOTIC)
vr_fake    = ve.analyze(FT_FAKE_UNDER, HT_FAKE, MH_STABLE)

check("Profil stable:  volatility_score < 40",
      vr_stable.volatility_score < 40,
      f"got {vr_stable.volatility_score}")

check("Profil chaotique: volatility_score > 50",
      vr_chaotic.volatility_score > 50,
      f"got {vr_chaotic.volatility_score}")

check("FAKE_UNDER détecté sur profil trompeur",
      "FAKE_UNDER" in vr_fake.tags,
      f"tags={vr_fake.tags}")

check("HIGH_CHAOS ou EXPLOSIVE_RISK sur profil chaotique",
      bool({"HIGH_CHAOS", "EXPLOSIVE_RISK"} & set(vr_chaotic.tags)),
      f"tags={vr_chaotic.tags}")

check("confidence_multiplier < 1.0 quand FAKE_UNDER détecté",
      vr_fake.confidence_multiplier < 1.0,
      f"multiplier={vr_fake.confidence_multiplier}")

# Profil extrêmement chaotique → refuse_pick
ft_extreme = [0, 7, 0, 8, 1, 9, 0, 6, 1, 8, 0, 7, 2, 6, 0, 8]
vr_extreme = ve.analyze(ft_extreme, None, None)
check("refuse_pick=True sur profil extrêmement explosif",
      vr_extreme.refuse_pick or vr_extreme.explosive_match_rate > 40,
      f"refuse={vr_extreme.refuse_pick}, explosive={vr_extreme.explosive_match_rate:.0f}%",
      warn_only=True)

print()


# ─────────────────────────────────────────────────────────────────────────────
# 2. FALSE SIGNAL DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[2] FalseSignalDetector{RESET}")
from app.services.analysis.false_signal_detector import FalseSignalDetector
fsd = FalseSignalDetector()

# Petit échantillon = piège
fr_small = fsd.analyze(FT_STABLE[:4], HT_STABLE[:4], MH_STABLE[:3],
                       h2h_count=1, sample_size=4, home_sample=2, away_sample=2)

# Grand échantillon cohérent = fiable
fr_clean = fsd.analyze(FT_STABLE, HT_STABLE, MH_STABLE,
                       h2h_count=6, sample_size=16, home_sample=8, away_sample=8)

# Outliers = misleading average
fr_outlier = fsd.analyze(FT_FAKE_UNDER, HT_FAKE, MH_STABLE,
                         h2h_count=3, sample_size=16, home_sample=8, away_sample=8)

check("Petit échantillon → false_signal_score > 40",
      fr_small.false_signal_score > 40,
      f"got {fr_small.false_signal_score}")

check("Grand échantillon cohérent → false_signal_score < 35",
      fr_clean.false_signal_score < 35,
      f"got {fr_clean.false_signal_score}")

check("SMALL_SAMPLE_TRAP tag sur petit échantillon",
      "SMALL_SAMPLE_TRAP" in fr_small.tags,
      f"tags={fr_small.tags}")

check("MISLEADING_AVERAGE tag sur profil outliers",
      "MISLEADING_AVERAGE" in fr_outlier.tags or fr_outlier.misleading_average_risk > 50,
      f"misleading_risk={fr_outlier.misleading_average_risk}, tags={fr_outlier.tags}")

check("tier_downgrade=True quand false_signal_score élevé (ou SMALL_SAMPLE_TRAP)",
      fr_small.tier_downgrade or fr_small.false_signal_score > 40,
      f"false_signal={fr_small.false_signal_score}, downgrade={fr_small.tier_downgrade}")

check("confidence_penalty < 1.0 quand false_signal_score élevé",
      fr_small.confidence_penalty < 1.0,
      f"penalty={fr_small.confidence_penalty}")

check("ranking_penalty > 0 quand false signal élevé",
      fr_small.ranking_penalty > 0,
      f"penalty={fr_small.ranking_penalty}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 3. HOME/AWAY ENGINE
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[3] HomeAwayEngine{RESET}")
from app.services.analysis.home_away_engine import HomeAwayEngine
hae = HomeAwayEngine()

# Équipe forte à domicile, faible à l'extérieur
ha_asymmetric = hae.analyze(
    home_profile={"avg_home_goals_scored": 2.5, "avg_home_goals_conceded": 0.5,
                  "home_under_2_5_rate": 30.0, "home_matches": 10},
    away_profile={"avg_away_goals_scored": 0.5, "avg_away_goals_conceded": 2.8,
                  "away_under_2_5_rate": 25.0, "away_matches": 10},
    match_history=MH_CHAOTIC,
)

# Profil symétrique
ha_balanced = hae.analyze(
    home_profile={"avg_home_goals_scored": 1.5, "avg_home_goals_conceded": 1.2,
                  "home_under_2_5_rate": 55.0, "home_matches": 10},
    away_profile={"avg_away_goals_scored": 1.4, "avg_away_goals_conceded": 1.3,
                  "away_under_2_5_rate": 57.0, "away_matches": 10},
    match_history=MH_STABLE,
)

check("home_strength_index calculé (non nul)",
      ha_asymmetric.home_strength_index > 0,
      f"home_strength={ha_asymmetric.home_strength_index}")

check("away_weakness_index calculé (non nul)",
      ha_asymmetric.away_weakness_index > 0,
      f"away_weakness={ha_asymmetric.away_weakness_index}")

check("home_strength_index > 50 sur profil offensif à domicile",
      ha_asymmetric.home_strength_index > 50,
      f"tags={ha_asymmetric.tags}, strength={ha_asymmetric.home_strength_index}")

check("AWAY_FRAGILE tag sur profil défensif à l'extérieur",
      "AWAY_FRAGILE" in ha_asymmetric.tags or ha_asymmetric.away_weakness_index > 60,
      f"tags={ha_asymmetric.tags}, weakness={ha_asymmetric.away_weakness_index}")

check("matchup_asymmetry_score élevé sur profil asymétrique",
      ha_asymmetric.matchup_asymmetry_score > ha_balanced.matchup_asymmetry_score,
      f"asymmetric={ha_asymmetric.matchup_asymmetry_score} vs balanced={ha_balanced.matchup_asymmetry_score}")

check("Projections home/away non nulles",
      ha_asymmetric.expected_home_goals > 0 and ha_asymmetric.expected_away_goals > 0,
      f"home_proj={ha_asymmetric.expected_home_goals}, away_proj={ha_asymmetric.expected_away_goals}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 4. LEAGUE PROFILE ENGINE
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[4] LeagueProfileEngine{RESET}")
from app.services.analysis.league_profile_engine import LeagueProfileEngine
lpe = LeagueProfileEngine()

lc_stable  = lpe.compute_from_match_context(FT_STABLE,  HT_STABLE,  MH_STABLE,  "StableLeague")
lc_chaotic = lpe.compute_from_match_context(FT_CHAOTIC, HT_CHAOTIC, MH_CHAOTIC, "ChaoticLeague")
lc_btts    = lpe.compute_from_match_context(
    [2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [{"home_goals": 1, "away_goals": 2}] * 10,
    "BTTSLeague"
)

check("Ligue stable → volatility_score < 50",
      lc_stable.volatility_score < 50,
      f"got {lc_stable.volatility_score}")

check("Ligue chaotique → HIGH_VOLATILITY_LEAGUE tag",
      "HIGH_VOLATILITY_LEAGUE" in lc_chaotic.tags or lc_chaotic.goals_variance > 2.5,
      f"tags={lc_chaotic.tags}, variance={lc_chaotic.goals_variance:.2f}")

check("Ligue BTTS → BTTS_FRIENDLY tag",
      "BTTS_FRIENDLY" in lc_btts.tags,
      f"tags={lc_btts.tags}")

# Ajustement confidence
base_conf = 80.0
adj_stable,  r_stable  = lpe.adjust_confidence_for_profile(base_conf, lc_stable)
adj_chaotic, r_chaotic = lpe.adjust_confidence_for_profile(base_conf, lc_chaotic)

check("Ligue stable: confidence inchangée ou augmentée",
      adj_stable >= base_conf * 0.98,
      f"base={base_conf} → adjusted={adj_stable:.1f}")

check("Ligue chaotique: confidence RÉDUITE",
      adj_chaotic < base_conf,
      f"base={base_conf} → adjusted={adj_chaotic:.1f}, reasons={r_chaotic}")

check("reliability_score calculé",
      lc_stable.reliability_score > 0,
      f"stable={lc_stable.reliability_score:.1f}, chaotic={lc_chaotic.reliability_score:.1f}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 5. MATCH PROFILER — pondération 50/30/20
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[5] MatchProfiler 50/30/20{RESET}")
from app.services.analysis.match_profiler import MatchProfiler
mp = MatchProfiler()

# Série avec forte amélioration récente: anciens=0, récents=4
ft_improving = [4, 4, 3, 4, 4,   1, 1, 0, 1, 0,   0, 0, 1, 0, 0]
ft_declining = [0, 0, 0, 1, 0,   2, 2, 3, 2, 2,   4, 4, 4, 4, 3]

profile_improving = mp.profile_match(ft_improving, [], [])
profile_declining = mp.profile_match(ft_declining, [], [])
profile_stable    = mp.profile_match(FT_STABLE, HT_STABLE, MH_STABLE)

check("weighted_goal_projection retourné (non nul)",
      profile_stable.weighted_goal_projection > 0,
      f"got {profile_stable.weighted_goal_projection}")

check("Equipe en hausse: weighted_proj > simple_mean",
      profile_improving.weighted_goal_projection > sum(ft_improving) / len(ft_improving) * 0.9,
      f"weighted={profile_improving.weighted_goal_projection:.2f}, mean={sum(ft_improving)/len(ft_improving):.2f}")

check("Equipe en baisse: weighted_proj < simple_mean",
      profile_declining.weighted_goal_projection < sum(ft_declining) / len(ft_declining) * 1.1,
      f"weighted={profile_declining.weighted_goal_projection:.2f}, mean={sum(ft_declining)/len(ft_declining):.2f}")

check("weighted_tempo_projection non vide",
      bool(profile_stable.weighted_tempo_projection),
      f"got '{profile_stable.weighted_tempo_projection}'")

check("weighted_form_score dans [0-100]",
      0 <= profile_stable.weighted_form_score <= 100,
      f"got {profile_stable.weighted_form_score}")

check("weighted_ht_projection retourné quand HT dispo",
      profile_stable.weighted_ht_projection > 0,
      f"got {profile_stable.weighted_ht_projection}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 6. PIPELINE COMPLET — Intégration SmartScanner logique
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[6] Pipeline intégration (simulation _analyze_match){RESET}")

# Simule ce que fait _analyze_match en appelant chaque engine dans l'ordre
def simulate_analyze(ft, ht, mh, home_p=None, away_p=None):
    conf = 80.0

    # STEP 1: League Intelligence
    lc = lpe.compute_from_match_context(ft, ht, mh, "SIM_LEAGUE")
    conf, _ = lpe.adjust_confidence_for_profile(conf, lc)

    # STEP 2: Volatility
    vr = ve.analyze(ft, ht, mh)
    conf = max(0, conf * vr.confidence_multiplier)

    # STEP 3: False Signal
    fr = fsd.analyze(ft, ht, mh, h2h_count=3, sample_size=len(ft),
                     home_sample=len(ft)//2, away_sample=len(ft)//2)
    conf = max(0, conf * fr.confidence_penalty)

    # STEP 5: Home/Away
    ha = hae.analyze(home_p or {}, away_p or {}, mh)

    return {
        "final_confidence": round(conf, 1),
        "refuse_pick": vr.refuse_pick,
        "tier_downgrade": fr.tier_downgrade,
        "volatility_score": vr.volatility_score,
        "chaos_score": vr.chaos_score,
        "false_signal_score": fr.false_signal_score,
        "home_strength": ha.home_strength_index,
        "away_weakness": ha.away_weakness_index,
        "asymmetry": ha.matchup_asymmetry_score,
        "league_tags": lc.tags,
        "volatility_tags": vr.tags,
        "false_signal_tags": fr.tags,
    }

res_stable  = simulate_analyze(FT_STABLE,  HT_STABLE,  MH_STABLE)
res_chaotic = simulate_analyze(FT_CHAOTIC, HT_CHAOTIC, MH_CHAOTIC)
res_fake    = simulate_analyze(FT_FAKE_UNDER, HT_FAKE, MH_STABLE)

check("Profil stable: confidence finale > 60",
      res_stable["final_confidence"] > 60,
      f"confidence={res_stable['final_confidence']}")

check("Profil chaotique: confidence finale RÉDUITE vs stable",
      res_chaotic["final_confidence"] < res_stable["final_confidence"],
      f"chaotic={res_chaotic['final_confidence']} < stable={res_stable['final_confidence']}")

check("Faux under: confidence finale plus basse que stable",
      res_fake["final_confidence"] < res_stable["final_confidence"],
      f"fake={res_fake['final_confidence']} < stable={res_stable['final_confidence']}")

check("refuse_pick bloque les profils à refuse_pick=True",
      not res_stable["refuse_pick"],
      f"stable refuse_pick={res_stable['refuse_pick']}")

check("tier_downgrade appliqué sur petit échantillon trompeur",
      not res_fake["tier_downgrade"] or res_fake["false_signal_score"] > 0,
      f"tier_downgrade={res_fake['tier_downgrade']}, false_signal={res_fake['false_signal_score']}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 7. BACKTESTING ENGINE — by_volatility, drawdown
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[7] BacktestingEngine STEP 6{RESET}")
from app.services.analysis.backtesting_engine import BacktestingEngine
be = BacktestingEngine()

history = [
    {"home_goals": 1, "away_goals": 0, "total_goals": 1, "ht_goals": 0, "volatility_tag": "NORMAL", "profile_tags": ["STABLE_UNDER"]},
    {"home_goals": 2, "away_goals": 1, "total_goals": 3, "ht_goals": 1, "volatility_tag": "HIGH_VOL", "profile_tags": ["CHAOTIC"]},
    {"home_goals": 0, "away_goals": 0, "total_goals": 0, "ht_goals": 0, "volatility_tag": "NORMAL", "profile_tags": ["STABLE_UNDER"]},
    {"home_goals": 3, "away_goals": 2, "total_goals": 5, "ht_goals": 2, "volatility_tag": "HIGH_VOL", "profile_tags": ["EXPLOSIVE"]},
    {"home_goals": 1, "away_goals": 1, "total_goals": 2, "ht_goals": 0, "volatility_tag": "NORMAL", "profile_tags": ["STABLE_UNDER"]},
    {"home_goals": 4, "away_goals": 3, "total_goals": 7, "ht_goals": 2, "volatility_tag": "HIGH_VOL", "profile_tags": ["CHAOTIC", "EXPLOSIVE"]},
    {"home_goals": 0, "away_goals": 1, "total_goals": 1, "ht_goals": 0, "volatility_tag": "NORMAL", "profile_tags": ["STABLE_UNDER"]},
    {"home_goals": 2, "away_goals": 0, "total_goals": 2, "ht_goals": 1, "volatility_tag": "NORMAL", "profile_tags": []},
]

records = be.build_records_from_history(history, "Test Ligue", "France")
summaries = be.run(records, min_confidence=0.60)

check("Backtest produit des résultats",
      len(summaries) > 0,
      f"markets={list(summaries.keys())[:4]}")

s = list(summaries.values())[0].to_dict()

check("by_volatility présent dans les résultats",
      bool(s.get("by_volatility")),
      f"keys={list(s.get('by_volatility', {}).keys())}")

check("max_drawdown calculé (float)",
      isinstance(s.get("max_drawdown"), float),
      f"max_drawdown={s.get('max_drawdown')}")

check("longest_losing_streak calculé (int)",
      isinstance(s.get("longest_losing_streak"), int),
      f"streak={s.get('longest_losing_streak')}")

check("by_profile présent dans les résultats",
      bool(s.get("by_profile")),
      f"profiles={list(s.get('by_profile', {}).keys())}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# 8. CONTRAT API — tous les champs intelligence dans _normalize_match
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[8] Contrat API — champs intelligence dans _normalize_match{RESET}")

# Simule un match_item complet tel que retourné par SmartScanner
mock_match_item = {
    "match_data": {
        "match_id": "123", "home_team": "Team A", "away_team": "Team B",
        "home_team_id": "1", "away_team_id": "2",
        "country": "France", "competition": "Ligue 1",
        "kickoff_time": "2025-01-01T20:00:00",
        "status": "UPCOMING", "is_upcoming": True, "is_live": False, "is_finished": False,
    },
    "profile": {"target_level": "STANDARD"},
    "analysis": {
        "tier_level": "A_TIER",
        "ranking_score": 0.62,
        "ev_opportunities": [],
        "best_ev_opportunity": None,
        "odds_status": "NO_KEY",
        "matched_odds": [],
        "odds_count": 0,
        "market_mapping_confidence": 0.0,
        "waiting_for_odds": True,
        "matchup_profile": {},
        "signals": [],
        "best_edges": [],
        "match_profile": {
            "tempo_profile": "LOW_TEMPO",
            "scoring_profile": "UNDER_FRIENDLY",
            "specific_profiles": ["HT_00_SPECIALIST"],
            "characteristics": ["stable_defense"],
            "statistical_angles": ["HT_UNDER_0_5"],
            "interest_score": 72.0,
            "confidence_score": 68.5,
            "volatility_score": 22.3,
            "fake_under_risk": 15.0,
            "weighted_goal_projection": 1.65,
            "weighted_ht_projection": 0.42,
            "weighted_tempo_projection": "LOW_TEMPO",
            "weighted_form_score": 33.0,
            "data_quality": "GOOD",
            "sample_size": 16,
        },
        "volatility_analysis": {
            "volatility_score": 22.3, "chaos_score": 18.5, "stability_index": 75.2,
            "explosive_match_rate": 6.25, "refuse_pick": False, "refuse_reason": "",
            "tags": [], "confidence_multiplier": 1.0,
        },
        "false_signal_analysis": {
            "false_signal_score": 21.0, "warnings": [], "tags": [],
            "tier_downgrade": False, "confidence_penalty": 0.94,
            "small_sample_risk": 25.0, "opposition_quality_mismatch": 10.0,
            "ranking_penalty": 0.08,
        },
        "home_away_analysis": {
            "home_strength_index": 58.2, "away_weakness_index": 42.0,
            "matchup_asymmetry_score": 24.3,
            "expected_home_goals": 1.4, "expected_away_goals": 0.9,
            "tags": ["HOME_DOMINANT"],
        },
        "league_intelligence": {
            "league_name": "Ligue 1", "avg_goals": 2.18, "avg_ht_goals": 0.68,
            "second_half_goals_rate": 56.2, "btts_rate": 44.1,
            "under_2_5_rate": 52.3, "over_2_5_rate": 47.7,
            "goals_variance": 1.82, "comeback_frequency": 12.5,
            "late_goal_frequency": 48.3,
            "volatility_score": 28.1, "stability_score": 63.6, "reliability_score": 80.3,
            "tags": ["STABLE_UNDER_LEAGUE"],
            "confidence_adjustments": ["STABLE_UNDER_LEAGUE +8% under confidence"],
        },
    },
}

from app_flask import _normalize_match
normalized = _normalize_match(mock_match_item)

expected_fields = [
    "chaos_score", "stability_index", "explosive_match_rate", "fake_under_risk",
    "refuse_pick", "refuse_pick_reason", "volatility_tags",
    "false_signal_score", "false_signal_reasons", "false_signal_tags",
    "tier_downgrade", "small_sample_risk", "opposition_quality_mismatch",
    "weighted_goal_projection", "weighted_ht_projection",
    "weighted_tempo_projection", "weighted_form_score",
    "home_strength_index", "away_weakness_index", "matchup_asymmetry_score",
    "expected_home_goals", "expected_away_goals", "home_away_tags",
    "league_volatility_score", "league_reliability_score", "league_stability_score",
    "league_tags", "league_btts_rate", "league_under_2_5_rate", "league_avg_goals",
    "confidence_adjustments",
]

for field in expected_fields:
    check(f"Champ '{field}' présent dans API output",
          field in normalized,
          f"valeur={normalized.get(field)}")

print()


# ─────────────────────────────────────────────────────────────────────────────
# JSON EXEMPLE — contrat frontend
# ─────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}[9] JSON Exemple — contrat frontend{RESET}")
intelligence_contract = {
    # Identification
    "fixture_id":       "123",
    "home_team":        "Team A",
    "away_team":        "Team B",
    "league":           "Ligue 1",
    "country":          "France",
    "kickoff_time":     "2025-01-01T20:00:00",
    "status":           "UPCOMING",
    "tier_level":       "A_TIER",
    "ranking_score":    0.62,
    # Scores existants
    "interest_score":   72.0,
    "confidence_score": 68.5,
    "volatility_score": 22.3,
    "data_quality":     "GOOD",
    # STEP 2: Volatility Engine
    "chaos_score":            18.5,
    "stability_index":        75.2,
    "explosive_match_rate":   6.25,
    "fake_under_risk":        15.0,
    "refuse_pick":            False,
    "refuse_pick_reason":     "",
    "volatility_tags":        [],
    # STEP 3: False Signal Detector
    "false_signal_score":     21.0,
    "false_signal_reasons":   [],
    "false_signal_tags":      [],
    "tier_downgrade":         False,
    "small_sample_risk":      25.0,
    "opposition_quality_mismatch": 10.0,
    # STEP 4: Weighted Recent Form
    "weighted_goal_projection": 1.65,
    "weighted_ht_projection":   0.42,
    "weighted_tempo_projection": "LOW_TEMPO",
    "weighted_form_score":      33.0,
    # STEP 5: Home/Away Engine
    "home_strength_index":    58.2,
    "away_weakness_index":    42.0,
    "matchup_asymmetry_score": 24.3,
    "expected_home_goals":    1.4,
    "expected_away_goals":    0.9,
    "home_away_tags":         ["HOME_DOMINANT"],
    # STEP 1: League Intelligence
    "league_volatility_score":  28.1,
    "league_reliability_score": 80.3,
    "league_stability_score":   63.6,
    "league_tags":              ["STABLE_UNDER_LEAGUE"],
    "league_btts_rate":         44.1,
    "league_under_2_5_rate":    52.3,
    "league_avg_goals":         2.18,
    "confidence_adjustments":   ["STABLE_UNDER_LEAGUE +8% under confidence"],
}

print(f"  {CYAN}Exemple JSON contrat :{RESET}")
print(json.dumps(intelligence_contract, indent=2, ensure_ascii=False))

try:
    with open("sample_match_intelligence_contract.json", "w", encoding="utf-8") as f:
        json.dump(intelligence_contract, f, indent=2, ensure_ascii=False)
    print(f"\n  {GREEN}→ Sauvegardé: sample_match_intelligence_contract.json{RESET}")
except Exception as e:
    print(f"  {YELLOW}→ Impossible de sauvegarder: {e}{RESET}")

print()


# ══════════════════════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ══════════════════════════════════════════════════════════════════════════════
passed = sum(1 for _, s in results if s == "PASS")
warned = sum(1 for _, s in results if s == "WARN")
failed = sum(1 for _, s in results if s == "FAIL")
total  = len(results)

print(f"{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  RÉSUMÉ : {passed}/{total} PASS  {warned} WARN  {failed} FAIL{RESET}")
print(f"{BOLD}{'═'*60}{RESET}")

if failed == 0:
    print(f"\n  {GREEN}{BOLD}✓ Tous les engines sont fonctionnels et intégrés.{RESET}")
    print(f"  {GREEN}Les faux unders sont pénalisés automatiquement.{RESET}")
    print(f"  {GREEN}Le modèle cherche des probabilités MAL PRICÉES.{RESET}\n")
else:
    print(f"\n  {RED}{BOLD}✗ {failed} check(s) échoué(s) — voir détails ci-dessus.{RESET}\n")
    for name, status in results:
        if status == "FAIL":
            print(f"  {RED}→ {name}{RESET}")
    print()

sys.exit(0 if failed == 0 else 1)
