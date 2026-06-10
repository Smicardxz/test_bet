"""
Volatility Engine — STEP 2
Détecte les matchs statistiquement dangereux même si les hit rates semblent bons.
Peut refuser un pick même avec un bon hit rate si la volatilité est trop élevée.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class VolatilityResult:
    """Résultat complet de l'analyse de volatilité"""

    # Métriques brutes
    score_variance: float           # Variance des scores totaux
    explosive_match_rate: float     # % matchs avec 4+ buts
    matches_above_4: int            # Count matchs > 4 buts
    matches_above_5: int            # Count matchs > 5 buts
    comeback_rate: float            # % matchs à forte remontée
    goal_clustering: float          # Dispersion normalisée (CV)
    late_goal_rate: float           # % buts en 2ème mi-temps
    ht_to_ft_expansion: float       # Ratio goals 2H / goals 1H
    unexpected_score_rate: float    # % scores > mean + 2*std

    # Scores synthétiques (0-100)
    volatility_score: float
    chaos_score: float
    stability_index: float          # Inverse du chaos

    # Décision
    tags: List[str] = field(default_factory=list)
    refuse_pick: bool = False
    refuse_reason: str = ""
    confidence_multiplier: float = 1.0  # Appliqué au confidence_score
    # Phase 2 — Regime detection
    chaos_type: str = "NEUTRAL"              # OFFENSIVE | DEFENSIVE | NEUTRAL
    recommended_market_direction: str = "NEUTRAL"  # OVER | UNDER | BOTH | AVOID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_variance":        round(self.score_variance, 3),
            "explosive_match_rate":  round(self.explosive_match_rate, 1),
            "matches_above_4":       self.matches_above_4,
            "matches_above_5":       self.matches_above_5,
            "comeback_rate":         round(self.comeback_rate, 1),
            "goal_clustering":       round(self.goal_clustering, 3),
            "late_goal_rate":        round(self.late_goal_rate, 1),
            "ht_to_ft_expansion":    round(self.ht_to_ft_expansion, 2),
            "unexpected_score_rate": round(self.unexpected_score_rate, 1),
            "volatility_score":      round(self.volatility_score, 1),
            "chaos_score":           round(self.chaos_score, 1),
            "stability_index":       round(self.stability_index, 1),
            "tags":                  self.tags,
            "refuse_pick":                   self.refuse_pick,
            "refuse_reason":                 self.refuse_reason,
            "confidence_multiplier":         round(self.confidence_multiplier, 3),
            "chaos_type":                    self.chaos_type,
            "recommended_market_direction":  self.recommended_market_direction,
        }


class VolatilityEngine:
    """
    Volatility Engine — Phase STEP 2

    Calcule la dangerosité statistique d'un matchup.
    Un pick peut être refusé même avec un bon hit rate si la volatilité
    dépasse les seuils de sécurité.
    """

    REFUSE_VOLATILITY_THRESHOLD = 78.0
    REFUSE_CHAOS_THRESHOLD = 82.0
    REFUSE_EXPLOSIVE_THRESHOLD = 42.0   # % matchs avec 4+ buts

    def analyze(
        self,
        ft_goals: List[int],
        ht_goals: Optional[List[int]] = None,
        match_history: Optional[List[Dict[str, Any]]] = None,
    ) -> VolatilityResult:
        """
        Analyse complète de la volatilité d'un matchup.

        Args:
            ft_goals:      Historique buts FT (combiné home+away)
            ht_goals:      Historique buts HT
            match_history: Dicts avec home_goals/away_goals

        Returns:
            VolatilityResult
        """
        n = len(ft_goals)
        if n < 3:
            return self._empty_result()

        mean_goals = sum(ft_goals) / n

        # 1. Variance des scores
        score_variance = sum((g - mean_goals) ** 2 for g in ft_goals) / n

        # 2. Matchs explosifs
        above_4 = sum(1 for g in ft_goals if g >= 4)
        above_5 = sum(1 for g in ft_goals if g >= 5)
        explosive_rate = above_4 / n * 100

        # 3. Comeback rate
        comeback_rate = self._calculate_comeback_rate(match_history, ft_goals, ht_goals)

        # 4. Goal clustering (coefficient of variation)
        std = score_variance ** 0.5
        goal_clustering = std / max(mean_goals, 0.01)

        # 5. Buts en 2ème mi-temps + expansion
        late_goal_rate, ht_to_ft_expansion = self._calculate_half_metrics(
            ft_goals, ht_goals
        )

        # 6. Scores inattendus (> mean + 2*std)
        unexpected_threshold = mean_goals + 2 * std
        unexpected_rate = sum(1 for g in ft_goals if g >= unexpected_threshold) / n * 100

        # 7. Scores synthétiques
        volatility_score = self._compute_volatility_score(
            score_variance, explosive_rate, goal_clustering, unexpected_rate
        )
        chaos_score = self._compute_chaos_score(
            comeback_rate, late_goal_rate, ht_to_ft_expansion, explosive_rate
        )
        stability_index = max(0.0, 100.0 - (volatility_score * 0.6 + chaos_score * 0.4))

        # 8. Tags
        tags = self._generate_tags(
            volatility_score, chaos_score, explosive_rate, late_goal_rate,
            ht_to_ft_expansion, comeback_rate, mean_goals, score_variance
        )

        # 9. Décision de refus + multiplicateur de confiance + type de chaos
        refuse_pick, refuse_reason, confidence_multiplier = self._decide_refusal(
            volatility_score, chaos_score, explosive_rate, tags
        )
        chaos_type, recommended_dir = self._classify_chaos(
            tags, mean_goals, explosive_rate, late_goal_rate, ht_to_ft_expansion
        )

        return VolatilityResult(
            score_variance=round(score_variance, 4),
            explosive_match_rate=round(explosive_rate, 1),
            matches_above_4=above_4,
            matches_above_5=above_5,
            comeback_rate=round(comeback_rate, 1),
            goal_clustering=round(goal_clustering, 3),
            late_goal_rate=round(late_goal_rate, 1),
            ht_to_ft_expansion=round(ht_to_ft_expansion, 2),
            unexpected_score_rate=round(unexpected_rate, 1),
            volatility_score=round(volatility_score, 1),
            chaos_score=round(chaos_score, 1),
            stability_index=round(stability_index, 1),
            tags=tags,
            refuse_pick=refuse_pick,
            refuse_reason=refuse_reason,
            confidence_multiplier=round(confidence_multiplier, 3),
            chaos_type=chaos_type,
            recommended_market_direction=recommended_dir,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_comeback_rate(
        self,
        match_history: Optional[List[Dict]],
        ft_goals: List[int],
        ht_goals: Optional[List[int]],
    ) -> float:
        if ht_goals and len(ht_goals) >= 3 and len(ft_goals) >= 3:
            nh = min(len(ht_goals), len(ft_goals))
            strong_2h = sum(
                1 for i in range(nh)
                if (ft_goals[i] - ht_goals[i]) >= ht_goals[i] + 2
            )
            return strong_2h / nh * 100

        if match_history and len(match_history) >= 3:
            high_variance_matches = sum(
                1 for m in match_history
                if abs(m.get("home_goals", 0) - m.get("away_goals", 0)) >= 3
            )
            return high_variance_matches / len(match_history) * 100

        return 20.0  # neutre

    def _calculate_half_metrics(
        self,
        ft_goals: List[int],
        ht_goals: Optional[List[int]],
    ):
        if not ht_goals or len(ht_goals) < 3:
            return 50.0, 1.0

        nh = min(len(ht_goals), len(ft_goals))
        sh_goals = [ft_goals[i] - ht_goals[i] for i in range(nh)]
        total_1h = sum(ht_goals[:nh])
        total_2h = sum(sh_goals)
        total_all = total_1h + total_2h

        late_goal_rate = (total_2h / total_all * 100) if total_all > 0 else 50.0
        ht_to_ft_expansion = total_2h / max(total_1h, 0.01)

        return round(late_goal_rate, 1), round(ht_to_ft_expansion, 2)

    def _compute_volatility_score(
        self, variance: float, explosive_rate: float,
        clustering: float, unexpected_rate: float
    ) -> float:
        v = min(100, variance * 20)
        e = min(100, explosive_rate * 2)
        c = min(100, clustering * 35)
        u = min(100, unexpected_rate * 3)
        return min(100.0, v * 0.35 + e * 0.30 + c * 0.20 + u * 0.15)

    def _compute_chaos_score(
        self, comeback_rate: float, late_goal_rate: float,
        expansion: float, explosive_rate: float
    ) -> float:
        c = min(100, comeback_rate)
        # Late goal rate > 55% = déséquilibre 2H
        l = min(100, max(0.0, (late_goal_rate - 50) * 4))
        # expansion > 1.5 = 2H beaucoup plus actif que 1H
        e = min(100, max(0.0, (expansion - 1.0) * 55))
        x = min(100, explosive_rate * 2)
        return min(100.0, c * 0.28 + l * 0.27 + e * 0.25 + x * 0.20)

    def _generate_tags(
        self,
        volatility: float, chaos: float, explosive_rate: float,
        late_goal_rate: float, expansion: float, comeback_rate: float,
        avg_goals: float, variance: float,
    ) -> List[str]:
        tags = []
        if chaos > 70:
            tags.append("HIGH_CHAOS")
        if explosive_rate > 30:
            tags.append("EXPLOSIVE_RISK")
        # FAKE_UNDER: moyenne basse mais variance élevée = piège classique
        if avg_goals <= 2.5 and variance >= 2.0:
            tags.append("FAKE_UNDER")
        if volatility > 65 or (variance >= 1.8 and explosive_rate > 20):
            tags.append("UNSTABLE_PROFILE")
        if late_goal_rate > 65:
            tags.append("LATE_GOAL_HEAVY")
        if expansion > 2.5:
            tags.append("SECOND_HALF_EXPLOSION")
        if comeback_rate > 38:
            tags.append("HIGH_COMEBACK_RISK")
        return tags

    def _classify_chaos(
        self,
        tags: List[str],
        avg_goals: float,
        explosive_rate: float,
        late_goal_rate: float,
        expansion: float,
    ) -> tuple:
        """
        Classify chaos as OFFENSIVE or DEFENSIVE and return recommended direction.

        OFFENSIVE chaos  → avg_goals high, explosions frequent   → boost OVER, avoid UNDER
        DEFENSIVE chaos  → FAKE_UNDER pattern, comeback risk      → avoid UNDER picks
        NEUTRAL          → no strong bias

        Returns (chaos_type, recommended_market_direction)
        """
        is_explosive = "EXPLOSIVE_RISK" in tags or explosive_rate > 25
        is_fake_under = "FAKE_UNDER" in tags
        is_late_heavy = "LATE_GOAL_HEAVY" in tags or late_goal_rate > 60
        is_sh_explosion = "SECOND_HALF_EXPLOSION" in tags or expansion > 2.0

        # OFFENSIVE CHAOS: high scoring environment
        if avg_goals >= 2.8 and is_explosive:
            return "OFFENSIVE", "OVER"
        if is_sh_explosion and avg_goals >= 2.5:
            return "OFFENSIVE", "OVER"
        if avg_goals >= 3.2:
            return "OFFENSIVE", "OVER"

        # DEFENSIVE CHAOS: trap — looks defensive but isn't
        if is_fake_under:
            return "DEFENSIVE", "AVOID_UNDER"
        if is_late_heavy and avg_goals < 2.5:
            return "DEFENSIVE", "AVOID_UNDER"

        # High chaos but unclear direction → avoid extreme lines
        if "HIGH_CHAOS" in tags and avg_goals >= 2.0:
            return "NEUTRAL", "OVER"

        return "NEUTRAL", "NEUTRAL"

    def _decide_refusal(
        self,
        volatility: float, chaos: float,
        explosive_rate: float, tags: List[str],
    ):
        """
        Retourne (refuse_pick, reason, confidence_multiplier).
        Phase 3: Refuser UNDER sur chaos offensif; refuser UNDER sur FAKE_UNDER.
        Ne plus refuser en cas de chaos OFFENSIF — promouvoir OVER à la place.
        """
        # FAKE_UNDER + EXPLOSIVE → refuse UNDER but signal OVER, don't block entirely
        if "FAKE_UNDER" in tags and "EXPLOSIVE_RISK" in tags:
            return False, "FAKE_UNDER+EXPLOSIVE: redirect to OVER", 0.60

        # Refus total: double seuil volatilité + chaos (aucune direction fiable)
        if volatility > self.REFUSE_VOLATILITY_THRESHOLD and chaos > self.REFUSE_CHAOS_THRESHOLD:
            return (
                True,
                f"Volatilité extrême ({volatility:.0f}/100) + Chaos ({chaos:.0f}/100)",
                0.50,
            )

        # Matchs explosifs très fréquents → refuse UNDER, allow OVER
        if explosive_rate > self.REFUSE_EXPLOSIVE_THRESHOLD:
            return (
                False,
                f"{explosive_rate:.0f}% matchs 4+ buts: redirect to OVER",
                0.70,
            )

        # Pas de refus total → pénalités progressives
        multiplier = 1.0
        if "HIGH_CHAOS" in tags:
            multiplier *= 0.85
        if "FAKE_UNDER" in tags:
            multiplier *= 0.82
        if "UNSTABLE_PROFILE" in tags:
            multiplier *= 0.90
        if "EXPLOSIVE_RISK" in tags:
            multiplier *= 0.88

        return False, "", round(multiplier, 3)

    def _empty_result(self) -> VolatilityResult:
        return VolatilityResult(
            score_variance=0.0,
            explosive_match_rate=0.0,
            matches_above_4=0,
            matches_above_5=0,
            comeback_rate=0.0,
            goal_clustering=0.0,
            late_goal_rate=50.0,
            ht_to_ft_expansion=1.0,
            unexpected_score_rate=0.0,
            volatility_score=0.0,
            chaos_score=0.0,
            stability_index=50.0,
            tags=[],
            refuse_pick=False,
            refuse_reason="",
            confidence_multiplier=1.0,
        )
