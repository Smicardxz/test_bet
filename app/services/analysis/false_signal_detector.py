"""
False Signal Detection Layer — STEP 3
Réduit les faux positifs en détectant les pièges statistiques.

Détecte :
- Opposition quality mismatch (hit rate gonflé contre équipes faibles)
- Small sample traps (< 6 matchs)
- Misleading averages (outliers qui faussent la moyenne)
- Asymmetric team history bias
- H2H misleading (trop peu de confrontations)
- Volatile league masking
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FalseSignalResult:
    """Résultat de la détection de faux signaux"""

    # Score global (0 = aucun risque, 100 = faux signal certain)
    false_signal_score: float

    # Composantes
    small_sample_risk: float           # 0-100: échantillon trop petit
    opposition_quality_mismatch: float # 0-100: sous-estimation du niveau
    recency_bias: float                # 0-100: tendance récente vs historique
    asymmetric_history_bias: float     # 0-100: biais home vs away
    misleading_average_risk: float     # 0-100: outliers faussant la moyenne
    h2h_bias_risk: float               # 0-100: H2H trop peu représentatif

    # Ajustements à appliquer sur confidence_score (0.0-1.0 multiplicateur)
    confidence_penalty: float          # Ex: 0.75 = -25% de confiance

    # Downgrade du tier si false_signal_score dépasse le seuil
    tier_downgrade: bool
    ranking_penalty: float             # Soustrait du ranking_score

    # Verbosity
    warnings: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "false_signal_score":            round(self.false_signal_score, 1),
            "small_sample_risk":             round(self.small_sample_risk, 1),
            "opposition_quality_mismatch":   round(self.opposition_quality_mismatch, 1),
            "recency_bias":                  round(self.recency_bias, 1),
            "asymmetric_history_bias":       round(self.asymmetric_history_bias, 1),
            "misleading_average_risk":       round(self.misleading_average_risk, 1),
            "h2h_bias_risk":                 round(self.h2h_bias_risk, 1),
            "confidence_penalty":            round(self.confidence_penalty, 3),
            "tier_downgrade":                self.tier_downgrade,
            "ranking_penalty":               round(self.ranking_penalty, 3),
            "warnings":                      self.warnings,
            "tags":                          self.tags,
        }


class FalseSignalDetector:
    """
    False Signal Detector — Phase STEP 3

    Analyse le contexte du pick pour détecter les signaux trompeurs.
    Applique des pénalités proportionnelles au risque détecté.
    """

    # Seuils de décision
    TIER_DOWNGRADE_THRESHOLD = 55.0  # false_signal_score > 55 → downgrade tier
    HARD_PENALTY_THRESHOLD = 70.0    # > 70 → pénalité forte (-35%)

    def analyze(
        self,
        ft_goals: List[int],
        ht_goals: Optional[List[int]] = None,
        match_history: Optional[List[Dict[str, Any]]] = None,
        home_goals_list: Optional[List[int]] = None,
        away_goals_list: Optional[List[int]] = None,
        h2h_count: int = 0,
        sample_size: int = 0,
        home_sample: int = 0,
        away_sample: int = 0,
    ) -> FalseSignalResult:
        """
        Analyse le risque de faux signal pour un matchup.

        Args:
            ft_goals:          Historique FT buts (combiné)
            ht_goals:          Historique HT buts
            match_history:     Dicts avec home_goals/away_goals
            home_goals_list:   Goals marqués à domicile (équipe home)
            away_goals_list:   Goals marqués à l'extérieur (équipe away)
            h2h_count:         Nombre de confrontations directes
            sample_size:       Taille totale de l'échantillon FT
            home_sample:       Nb matchs home history
            away_sample:       Nb matchs away history
        """
        n = sample_size or len(ft_goals)

        # Composantes
        small_sample_risk = self._check_small_sample(n, home_sample, away_sample)
        misleading_avg_risk = self._check_misleading_averages(ft_goals)
        asymmetric_bias = self._check_asymmetric_bias(
            home_goals_list, away_goals_list, match_history
        )
        opposition_mismatch = self._check_opposition_mismatch(
            ft_goals, match_history
        )
        recency_bias = self._check_recency_bias(ft_goals)
        h2h_bias = self._check_h2h_bias(h2h_count, n)

        # Score global pondéré
        false_signal_score = (
            small_sample_risk      * 0.28 +
            misleading_avg_risk    * 0.22 +
            asymmetric_bias        * 0.18 +
            opposition_mismatch    * 0.16 +
            recency_bias           * 0.10 +
            h2h_bias               * 0.06
        )
        false_signal_score = min(100.0, false_signal_score)

        # Pénalité de confiance
        confidence_penalty = self._compute_confidence_penalty(false_signal_score)

        # Downgrade tier
        tier_downgrade = false_signal_score >= self.TIER_DOWNGRADE_THRESHOLD

        # Pénalité ranking (0.0-0.3 soustrait)
        ranking_penalty = min(0.30, false_signal_score / 100 * 0.40)

        # Warnings + tags
        warnings, tags = self._generate_warnings(
            small_sample_risk, misleading_avg_risk, asymmetric_bias,
            opposition_mismatch, recency_bias, h2h_bias, n
        )

        return FalseSignalResult(
            false_signal_score=round(false_signal_score, 1),
            small_sample_risk=round(small_sample_risk, 1),
            opposition_quality_mismatch=round(opposition_mismatch, 1),
            recency_bias=round(recency_bias, 1),
            asymmetric_history_bias=round(asymmetric_bias, 1),
            misleading_average_risk=round(misleading_avg_risk, 1),
            h2h_bias_risk=round(h2h_bias, 1),
            confidence_penalty=round(confidence_penalty, 3),
            tier_downgrade=tier_downgrade,
            ranking_penalty=round(ranking_penalty, 3),
            warnings=warnings,
            tags=tags,
        )

    # ------------------------------------------------------------------
    # Composantes
    # ------------------------------------------------------------------

    def _check_small_sample(
        self, n: int, home_sample: int, away_sample: int
    ) -> float:
        """Risque lié à un échantillon insuffisant."""
        if n < 5:
            return 90.0
        if n < 8:
            return 70.0
        if n < 12:
            return 45.0
        if n < 18:
            return 25.0
        return max(0.0, 20.0 - (n - 18) * 0.5)

    def _check_misleading_averages(self, ft_goals: List[int]) -> float:
        """
        Détecte si la moyenne est faussée par des outliers.
        Exemple: [0, 0, 0, 1, 0, 8] → moyenne 1.5 mais fausse
        """
        if len(ft_goals) < 5:
            return 40.0

        mean = sum(ft_goals) / len(ft_goals)
        variance = sum((g - mean) ** 2 for g in ft_goals) / len(ft_goals)
        std = variance ** 0.5

        # Outlier = valeur > mean + 2.5*std
        outliers = [g for g in ft_goals if g > mean + 2.5 * std]
        outlier_ratio = len(outliers) / len(ft_goals)

        # Si outliers représentent > 10% du sample → risque
        if outlier_ratio > 0.20:
            return 75.0
        if outlier_ratio > 0.10:
            return 55.0

        # Coefficient de variation élevé = données peu fiables
        cv = std / max(mean, 0.01)
        if cv > 1.5:
            return 65.0
        if cv > 1.0:
            return 40.0
        if cv > 0.7:
            return 20.0

        return 5.0

    def _check_asymmetric_bias(
        self,
        home_goals: Optional[List[int]],
        away_goals: Optional[List[int]],
        match_history: Optional[List[Dict]],
    ) -> float:
        """
        Détecte si l'historique est fortement biaisé home vs away.
        Ex: équipe qui marque beaucoup à domicile mais pas à l'extérieur.
        """
        if match_history and len(match_history) >= 4:
            home_avg = sum(m.get("home_goals", 0) for m in match_history) / len(match_history)
            away_avg = sum(m.get("away_goals", 0) for m in match_history) / len(match_history)
            if away_avg == 0:
                return 60.0
            ratio = home_avg / max(away_avg, 0.01)
            if ratio > 3.0 or ratio < 0.33:
                return 70.0
            if ratio > 2.0 or ratio < 0.5:
                return 45.0
            return 10.0

        if home_goals and away_goals and len(home_goals) >= 3 and len(away_goals) >= 3:
            h_avg = sum(home_goals) / len(home_goals)
            a_avg = sum(away_goals) / len(away_goals)
            if a_avg == 0:
                return 50.0
            ratio = h_avg / max(a_avg, 0.01)
            if ratio > 3.0 or ratio < 0.33:
                return 65.0
            if ratio > 2.0 or ratio < 0.5:
                return 40.0

        return 15.0

    def _check_opposition_mismatch(
        self,
        ft_goals: List[int],
        match_history: Optional[List[Dict]],
    ) -> float:
        """
        Approximation: si tous les matchs concèdent très peu → opposition faible.
        (Sans données adversaires directes, on utilise l'écart-type des buts concédés)
        Ex: équipe qui fait beaucoup d'UNDER mais uniquement contre des équipes faibles.
        """
        if not ft_goals or len(ft_goals) < 5:
            return 30.0

        mean = sum(ft_goals) / len(ft_goals)

        # Signal d'alerte: tous les matchs sous 2 buts MAIS avec forte dispersion
        under_count = sum(1 for g in ft_goals if g <= 1)
        under_ratio = under_count / len(ft_goals)

        variance = sum((g - mean) ** 2 for g in ft_goals) / len(ft_goals)

        # Profil suspect: many 0-0/0-1 mais quelques scores élevés
        if under_ratio > 0.7 and variance > 1.5:
            return 60.0  # Hit rate under gonflé par opposition faible
        if under_ratio > 0.6 and variance > 1.0:
            return 40.0

        return 10.0

    def _check_recency_bias(self, ft_goals: List[int]) -> float:
        """
        Détecte si les 5 derniers matchs sont très différents du reste.
        Indique un changement de forme qui invalide l'historique.
        """
        if len(ft_goals) < 8:
            return 20.0

        recent = ft_goals[:5]
        older = ft_goals[5:]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if older_avg == 0:
            return 30.0

        change_ratio = abs(recent_avg - older_avg) / max(older_avg, 0.01)

        # Changement > 60% = équipe en transformation → historique peu fiable
        if change_ratio > 0.80:
            return 70.0
        if change_ratio > 0.50:
            return 50.0
        if change_ratio > 0.30:
            return 30.0
        return 5.0

    def _check_h2h_bias(self, h2h_count: int, total_sample: int) -> float:
        """
        H2H avec peu de confrontations directes = biais de petite taille.
        """
        if h2h_count == 0:
            return 40.0  # Pas de H2H du tout
        if h2h_count < 3:
            return 55.0
        if h2h_count < 5:
            return 30.0
        return 10.0

    # ------------------------------------------------------------------
    # Pénalités et output
    # ------------------------------------------------------------------

    def _compute_confidence_penalty(self, false_signal_score: float) -> float:
        """Multipliateur de confiance basé sur le false_signal_score."""
        if false_signal_score >= self.HARD_PENALTY_THRESHOLD:
            return 0.65  # -35%
        if false_signal_score >= self.TIER_DOWNGRADE_THRESHOLD:
            return 0.78  # -22%
        if false_signal_score >= 35.0:
            return 0.88  # -12%
        if false_signal_score >= 20.0:
            return 0.94  # -6%
        return 1.0

    def _generate_warnings(
        self,
        small_sample: float, misleading: float, asymmetric: float,
        opposition: float, recency: float, h2h: float, n: int,
    ):
        warnings = []
        tags = []

        if small_sample >= 70:
            warnings.append(f"SMALL_SAMPLE: seulement {n} matchs — statistiques peu fiables")
            tags.append("SMALL_SAMPLE_TRAP")
        elif small_sample >= 45:
            warnings.append(f"SAMPLE_LIMITE: {n} matchs — confiance réduite")

        if misleading >= 55:
            warnings.append("MISLEADING_AVERAGE: outliers faussent la moyenne historique")
            tags.append("MISLEADING_AVERAGE")

        if asymmetric >= 65:
            warnings.append("ASYMMETRIC_HISTORY: fort déséquilibre home vs away dans l'historique")
            tags.append("ASYMMETRIC_BIAS")

        if opposition >= 55:
            warnings.append("OPPOSITION_MISMATCH: hit rate possiblement gonflé par opposition faible")
            tags.append("OPPOSITION_QUALITY_SUSPECT")

        if recency >= 50:
            warnings.append("RECENCY_SHIFT: forme récente très différente de l'historique")
            tags.append("FORM_BREAK")

        if h2h >= 50:
            warnings.append("H2H_INSUFFICIENT: peu de confrontations directes — H2H peu représentatif")
            tags.append("H2H_WEAK")

        return warnings, tags
