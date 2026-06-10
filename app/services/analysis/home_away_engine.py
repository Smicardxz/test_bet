"""
Home/Away Context Engine — STEP 5
Sépare les stats home et away pour détecter les asymétries.

Certaines équipes sont très différentes à domicile vs à l'extérieur.
Le moteur doit comprendre cet asymétrie pour projeter correctement.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HomeAwayResult:
    """Analyse contextuelle home/away"""

    # Indices home (0-100)
    home_strength_index: float      # Force offensive + défensive à domicile
    home_scoring_rate: float        # Buts marqués / match à domicile
    home_conceding_rate: float      # Buts concédés / match à domicile
    home_clean_sheet_rate: float    # % clean sheets à domicile
    home_btts_rate: float           # % BTTS à domicile
    home_under_2_5_rate: float      # % under 2.5 à domicile
    home_ht_under_rate: float       # % HT under 0.5 à domicile

    # Indices away (0-100)
    away_weakness_index: float      # Fragilité défensive à l'extérieur
    away_scoring_rate: float
    away_conceding_rate: float
    away_clean_sheet_rate: float
    away_btts_rate: float
    away_under_2_5_rate: float
    away_ht_under_rate: float

    # Asymétrie (0-100: 0 = symétrique, 100 = extrêmement asymétrique)
    matchup_asymmetry_score: float

    # Projections basées sur home/away
    expected_home_goals: float
    expected_away_goals: float
    expected_total_goals: float

    # Tags
    tags: List[str] = field(default_factory=list)

    # Qualité des données
    home_sample: int = 0
    away_sample: int = 0
    data_quality: str = "LIMITED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "home_strength_index":    round(self.home_strength_index, 1),
            "home_scoring_rate":      round(self.home_scoring_rate, 2),
            "home_conceding_rate":    round(self.home_conceding_rate, 2),
            "home_clean_sheet_rate":  round(self.home_clean_sheet_rate, 1),
            "home_btts_rate":         round(self.home_btts_rate, 1),
            "home_under_2_5_rate":    round(self.home_under_2_5_rate, 1),
            "home_ht_under_rate":     round(self.home_ht_under_rate, 1),
            "away_weakness_index":    round(self.away_weakness_index, 1),
            "away_scoring_rate":      round(self.away_scoring_rate, 2),
            "away_conceding_rate":    round(self.away_conceding_rate, 2),
            "away_clean_sheet_rate":  round(self.away_clean_sheet_rate, 1),
            "away_btts_rate":         round(self.away_btts_rate, 1),
            "away_under_2_5_rate":    round(self.away_under_2_5_rate, 1),
            "away_ht_under_rate":     round(self.away_ht_under_rate, 1),
            "matchup_asymmetry_score": round(self.matchup_asymmetry_score, 1),
            "expected_home_goals":    round(self.expected_home_goals, 2),
            "expected_away_goals":    round(self.expected_away_goals, 2),
            "expected_total_goals":   round(self.expected_total_goals, 2),
            "tags":                   self.tags,
            "home_sample":            self.home_sample,
            "away_sample":            self.away_sample,
            "data_quality":           self.data_quality,
        }


class HomeAwayEngine:
    """
    Home/Away Context Engine — STEP 5

    Construit des profils séparés home/away et calcule :
    - home_strength_index
    - away_weakness_index
    - matchup_asymmetry_score
    - Projections de buts basées sur le vrai contexte home/away
    """

    def analyze(
        self,
        home_profile: Optional[Dict[str, Any]] = None,
        away_profile: Optional[Dict[str, Any]] = None,
        match_history: Optional[List[Dict[str, Any]]] = None,
    ) -> HomeAwayResult:
        """
        Analyse home/away complète.

        Args:
            home_profile: Sortie de SmartScanner._calculate_home_profile()
                         Keys: avg_home_goals_scored, avg_home_goals_conceded,
                               home_under_2_5_rate, home_ht_avg_goals, etc.
            away_profile: Sortie de SmartScanner._calculate_away_profile()
                         Keys: avg_away_goals_scored, avg_away_goals_conceded, ...
            match_history: Dicts avec home_goals/away_goals (pour calculs BTTS)
        """
        if not home_profile and not away_profile:
            return self._empty_result()

        hp = home_profile or {}
        ap = away_profile or {}

        # --- HOME stats ---
        h_scored   = hp.get("avg_home_goals_scored", hp.get("avg_goals_scored", 0.0))
        h_conceded = hp.get("avg_home_goals_conceded", hp.get("avg_goals_conceded", 0.0))
        h_under    = hp.get("home_under_2_5_rate", hp.get("under_2_5_rate", 50.0))
        h_ht_avg   = hp.get("home_ht_avg_goals", hp.get("avg_ht_goals", 0.5))
        h_sample   = hp.get("home_matches", hp.get("matches", 0))

        # --- AWAY stats ---
        a_scored   = ap.get("avg_away_goals_scored", ap.get("avg_goals_scored", 0.0))
        a_conceded = ap.get("avg_away_goals_conceded", ap.get("avg_goals_conceded", 0.0))
        a_under    = ap.get("away_under_2_5_rate", ap.get("under_2_5_rate", 50.0))
        a_ht_avg   = ap.get("away_ht_avg_goals", ap.get("avg_ht_goals", 0.5))
        a_sample   = ap.get("away_matches", ap.get("matches", 0))

        # --- BTTS + clean sheets depuis match_history ---
        h_clean, h_btts, a_clean, a_btts = self._compute_btts_and_clean(match_history)

        # --- HT under rates ---
        h_ht_under = (1 - h_ht_avg / max(h_ht_avg + 0.5, 1)) * 100 if h_ht_avg < 1.5 else 30.0
        a_ht_under = (1 - a_ht_avg / max(a_ht_avg + 0.5, 1)) * 100 if a_ht_avg < 1.5 else 30.0
        h_ht_under = max(0.0, min(100.0, h_ht_under))
        a_ht_under = max(0.0, min(100.0, a_ht_under))

        # --- Indices synthétiques ---
        home_strength = self._compute_home_strength(h_scored, h_conceded, h_under, h_clean)
        away_weakness = self._compute_away_weakness(a_conceded, a_scored, a_under)

        # --- Projections ---
        exp_home = (h_scored + a_conceded) / 2.0
        exp_away = (a_scored + h_conceded) / 2.0
        exp_total = exp_home + exp_away

        # --- Asymétrie ---
        asymmetry = self._compute_asymmetry(
            h_scored, h_conceded, a_scored, a_conceded,
            h_under, a_under, h_btts, a_btts,
        )

        # --- Data quality ---
        min_sample = min(h_sample, a_sample) if h_sample > 0 and a_sample > 0 else max(h_sample, a_sample)
        data_quality = (
            "EXCELLENT" if min_sample >= 15
            else "GOOD"     if min_sample >= 10
            else "FAIR"     if min_sample >= 6
            else "LIMITED"
        )

        # --- Tags ---
        tags = self._generate_tags(
            home_strength, away_weakness, asymmetry,
            h_scored, a_conceded, h_under, a_under, h_btts, a_btts,
        )

        return HomeAwayResult(
            home_strength_index=round(home_strength, 1),
            home_scoring_rate=round(h_scored, 2),
            home_conceding_rate=round(h_conceded, 2),
            home_clean_sheet_rate=round(h_clean, 1),
            home_btts_rate=round(h_btts, 1),
            home_under_2_5_rate=round(h_under, 1),
            home_ht_under_rate=round(h_ht_under, 1),
            away_weakness_index=round(away_weakness, 1),
            away_scoring_rate=round(a_scored, 2),
            away_conceding_rate=round(a_conceded, 2),
            away_clean_sheet_rate=round(a_clean, 1),
            away_btts_rate=round(a_btts, 1),
            away_under_2_5_rate=round(a_under, 1),
            away_ht_under_rate=round(a_ht_under, 1),
            matchup_asymmetry_score=round(asymmetry, 1),
            expected_home_goals=round(exp_home, 2),
            expected_away_goals=round(exp_away, 2),
            expected_total_goals=round(exp_total, 2),
            tags=tags,
            home_sample=int(h_sample),
            away_sample=int(a_sample),
            data_quality=data_quality,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_btts_and_clean(self, match_history: Optional[List[Dict]]):
        if not match_history or len(match_history) < 3:
            return 30.0, 40.0, 20.0, 45.0

        n = len(match_history)
        h_clean = sum(1 for m in match_history if m.get("away_goals", 0) == 0) / n * 100
        a_clean = sum(1 for m in match_history if m.get("home_goals", 0) == 0) / n * 100
        btts = sum(
            1 for m in match_history
            if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
        ) / n * 100
        return round(h_clean, 1), round(btts, 1), round(a_clean, 1), round(btts, 1)

    def _compute_home_strength(
        self, scored: float, conceded: float, under_rate: float, clean_rate: float
    ) -> float:
        """Home strength: 0-100 (offensive + défensive)"""
        off_score = min(100, scored * 25)           # 4 buts/match = 100
        def_score = max(0, 100 - conceded * 30)     # 0 concédé = 100
        und_score = min(100, under_rate)
        cln_score = min(100, clean_rate)
        return off_score * 0.30 + def_score * 0.35 + und_score * 0.20 + cln_score * 0.15

    def _compute_away_weakness(
        self, conceded: float, scored: float, under_rate: float
    ) -> float:
        """Away weakness: 0-100 (0 = équipe forte à l'ext, 100 = très fragile)"""
        # Plus l'équipe concède à l'extérieur, plus la weakness est élevée
        weakness = min(100, conceded * 30)
        # Tempérée par la capacité offensive away
        strength = min(100, scored * 25)
        return max(0.0, weakness - strength * 0.20)

    def _compute_asymmetry(
        self,
        h_scored: float, h_conceded: float,
        a_scored: float, a_conceded: float,
        h_under: float, a_under: float,
        h_btts: float, a_btts: float,
    ) -> float:
        """Asymétrie home/away (0 = symétrique, 100 = extrême)"""
        diffs = []

        if h_scored + a_scored > 0:
            diffs.append(abs(h_scored - a_scored) / max(h_scored + a_scored, 0.01) * 100)
        if h_conceded + a_conceded > 0:
            diffs.append(abs(h_conceded - a_conceded) / max(h_conceded + a_conceded, 0.01) * 100)
        if abs(h_under - a_under) > 0:
            diffs.append(abs(h_under - a_under))
        if abs(h_btts - a_btts) > 0:
            diffs.append(abs(h_btts - a_btts) * 0.5)

        return min(100.0, sum(diffs) / len(diffs)) if diffs else 0.0

    def _generate_tags(
        self,
        home_strength: float, away_weakness: float, asymmetry: float,
        h_scored: float, a_conceded: float,
        h_under: float, a_under: float,
        h_btts: float, a_btts: float,
    ) -> List[str]:
        tags = []

        if home_strength > 70:
            tags.append("HOME_DOMINANT")
        if away_weakness > 70:
            tags.append("AWAY_FRAGILE")
        if asymmetry > 60:
            tags.append("HIGH_ASYMMETRY")
        if h_under > 65 and a_under > 65:
            tags.append("MUTUAL_UNDER")
        if h_btts > 60 and a_btts > 60:
            tags.append("BTTS_LIKELY")
        if h_scored > 2.0 and a_conceded > 1.5:
            tags.append("GOAL_FEAST_RISK")
        if home_strength > 60 and away_weakness > 60:
            tags.append("MISMATCH_EXPECTED")
        if h_under > 65 and away_weakness < 30:
            tags.append("AWAY_RESILIENT_TRAP")

        return tags

    def _empty_result(self) -> HomeAwayResult:
        return HomeAwayResult(
            home_strength_index=50.0,
            home_scoring_rate=1.2,
            home_conceding_rate=1.2,
            home_clean_sheet_rate=25.0,
            home_btts_rate=45.0,
            home_under_2_5_rate=50.0,
            home_ht_under_rate=60.0,
            away_weakness_index=50.0,
            away_scoring_rate=1.0,
            away_conceding_rate=1.4,
            away_clean_sheet_rate=20.0,
            away_btts_rate=45.0,
            away_under_2_5_rate=50.0,
            away_ht_under_rate=60.0,
            matchup_asymmetry_score=0.0,
            expected_home_goals=1.2,
            expected_away_goals=1.0,
            expected_total_goals=2.2,
            tags=[],
            home_sample=0,
            away_sample=0,
            data_quality="LIMITED",
        )
