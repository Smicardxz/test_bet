"""
Match Profiler - Détection de profils de matchs

Génère des profils intelligents pour TOUS les matchs analysés
Ne filtre PAS, mais CLASSE et PROFILE
"""

import logging
from typing import List, Dict, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchProfile:
    """Profil complet d'un match - Phase 4: Contextual Match Intelligence Engine"""
    # Profils principaux
    tempo_profile: str  # LOW_TEMPO, MEDIUM_TEMPO, HIGH_TEMPO
    scoring_profile: str  # EXTREME_UNDER, LOW_SCORING, BALANCED, HIGH_SCORING, EXTREME_OVER

    # Profils spécifiques
    specific_profiles: List[str]  # BTTS_PROFILE, HT_GOAL_PROFILE, etc.

    # Caractéristiques
    characteristics: List[str]  # defensive_clash, chaotic_match, etc.

    # Angles statistiques
    statistical_angles: List[str]  # HT U1.5, FT U2.5, BTTS YES, etc.

    # Scores
    interest_score: float  # 0-100 (à quel point c'est intéressant)
    confidence_score: float  # 0-100 (confiance dans l'analyse)
    volatility_score: float  # 0-100 (variance/chaos)

    # Phase 4: Contextual Intelligence Metrics
    recent_form_weighted: float  # 0-100 (forme récente pondérée)
    home_away_split_score: float  # 0-100 (cohérence home/away)
    opposition_strength: float  # 0-100 (force de l'opposition)
    league_tempo_score: float  # 0-100 (tempo de la ligue)
    real_variance: float  # 0-100 (variance réelle)
    explosive_match_rate: float  # 0-100 (taux de matchs explosifs)
    late_goals_tendency: float  # 0-100 (tendance aux buts tardifs)
    fake_under_risk: float  # 0-100 (risque de faux under)
    btts_tendency: float  # 0-100 (tendance BTTS)
    over_tendency: float  # 0-100 (tendance over)
    defensive_stability: float  # 0-100 (stabilité défensive)
    attacking_consistency: float  # 0-100 (consistance offensive)

    # Phase 4: Signal Explanations
    signal_explanations: List[str]  # Pourquoi chaque signal existe

    # STEP 4: Weighted Recent Form projections
    weighted_goal_projection: float = 0.0   # Projection buts pondérée 50/30/20
    weighted_ht_projection: float = 0.0     # Projection HT buts pondérée
    weighted_tempo_projection: str = ""     # LOW/MEDIUM/HIGH basé sur forme récente
    weighted_form_score: float = 0.0        # Score de forme pondéré 0-100

    # Métadonnées
    sample_size: int = 0
    data_quality: str = "UNKNOWN"  # EXCELLENT, GOOD, FAIR, LIMITED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tempo_profile": self.tempo_profile,
            "scoring_profile": self.scoring_profile,
            "specific_profiles": self.specific_profiles,
            "characteristics": self.characteristics,
            "statistical_angles": self.statistical_angles,
            "interest_score": self.interest_score,
            "confidence_score": self.confidence_score,
            "volatility_score": self.volatility_score,
            # Phase 4: Contextual Intelligence
            "recent_form_weighted": self.recent_form_weighted,
            "home_away_split_score": self.home_away_split_score,
            "opposition_strength": self.opposition_strength,
            "league_tempo_score": self.league_tempo_score,
            "real_variance": self.real_variance,
            "explosive_match_rate": self.explosive_match_rate,
            "late_goals_tendency": self.late_goals_tendency,
            "fake_under_risk": self.fake_under_risk,
            "btts_tendency": self.btts_tendency,
            "over_tendency": self.over_tendency,
            "defensive_stability": self.defensive_stability,
            "attacking_consistency": self.attacking_consistency,
            "signal_explanations": self.signal_explanations,
            # STEP 4: Weighted Recent Form projections
            "weighted_goal_projection": self.weighted_goal_projection,
            "weighted_ht_projection": self.weighted_ht_projection,
            "weighted_tempo_projection": self.weighted_tempo_projection,
            "weighted_form_score": self.weighted_form_score,
            # Metadata
            "sample_size": self.sample_size,
            "data_quality": self.data_quality
        }


class MatchProfiler:
    """
    Génère des profils intelligents pour tous les matchs
    
    Philosophie: ANALYSER TOUT, RANKER INTELLIGEMMENT
    Ne filtre PAS, mais PROFILE et CLASSE
    """
    
    def __init__(self):
        """Initialize profiler"""
        pass
    
    def profile_match(
        self,
        ft_goals: List[int],
        ht_goals: List[int],
        match_history: List[Dict[str, Any]] = None
    ) -> MatchProfile:
        """
        Génère un profil complet pour un match
        
        Args:
            ft_goals: FT goal history
            ht_goals: HT goal history
            match_history: Optional detailed match history
            
        Returns:
            MatchProfile complet
        """
        if not ft_goals or len(ft_goals) < 3:
            return self._create_limited_profile()
        
        # Calculs de base
        avg_goals = sum(ft_goals) / len(ft_goals)
        avg_ht_goals = sum(ht_goals) / len(ht_goals) if ht_goals else 0
        variance = self._calculate_variance(ft_goals)
        
        # 1. TEMPO PROFILE
        tempo_profile = self._detect_tempo_profile(avg_goals, avg_ht_goals)
        
        # 2. SCORING PROFILE
        scoring_profile = self._detect_scoring_profile(avg_goals, ft_goals)
        
        # 3. SPECIFIC PROFILES
        specific_profiles = self._detect_specific_profiles(
            ft_goals, ht_goals, match_history
        )
        
        # 4. CHARACTERISTICS
        characteristics = self._detect_characteristics(
            ft_goals, ht_goals, variance, match_history
        )
        
        # 5. STATISTICAL ANGLES
        statistical_angles = self._detect_statistical_angles(
            ft_goals, ht_goals, avg_goals, avg_ht_goals
        )
        
        # 6. SCORES
        interest_score = self._calculate_interest_score(
            scoring_profile, specific_profiles, characteristics, variance
        )
        confidence_score = self._calculate_confidence_score(len(ft_goals), variance, ht_goals, ft_goals)
        volatility_score = self._calculate_volatility_score(variance, ft_goals)

        # Phase 4: Contextual Intelligence Metrics
        recent_form_weighted = self._calculate_recent_form_weighted(ft_goals)
        home_away_split_score = self._calculate_home_away_split_score(match_history)
        opposition_strength = self._calculate_opposition_strength(match_history)
        league_tempo_score = self._calculate_league_tempo_score(avg_goals, avg_ht_goals)
        real_variance = self._calculate_real_variance(ft_goals, variance)
        explosive_match_rate = self._calculate_explosive_match_rate(ft_goals)
        late_goals_tendency = self._calculate_late_goals_tendency(ht_goals, ft_goals)
        fake_under_risk = self._calculate_fake_under_risk(ft_goals, avg_goals)
        btts_tendency = self._calculate_btts_tendency(match_history)
        over_tendency = self._calculate_over_tendency(ft_goals)
        defensive_stability = self._calculate_defensive_stability(ft_goals, variance)
        attacking_consistency = self._calculate_attacking_consistency(ft_goals)

        # Phase 4: Signal Explanations
        signal_explanations = self._generate_signal_explanations(
            scoring_profile, specific_profiles, characteristics,
            recent_form_weighted, explosive_match_rate, late_goals_tendency,
            btts_tendency, over_tendency, ft_goals
        )
        
        # 7. DATA QUALITY
        data_quality = self._assess_data_quality(len(ft_goals), len(ht_goals))
        
        # STEP 4: Weighted Recent Form (50/30/20)
        weighted_goal_projection = self._calculate_weighted_goal_projection(ft_goals)
        weighted_ht_projection = self._calculate_weighted_goal_projection(ht_goals) if ht_goals else 0.0
        weighted_tempo_projection = self._classify_tempo(weighted_goal_projection)
        weighted_form_score = self._calculate_weighted_form_score(ft_goals, ht_goals)

        profile = MatchProfile(
            tempo_profile=tempo_profile,
            scoring_profile=scoring_profile,
            specific_profiles=specific_profiles,
            characteristics=characteristics,
            statistical_angles=statistical_angles,
            interest_score=interest_score,
            confidence_score=confidence_score,
            volatility_score=volatility_score,
            # Phase 4: Contextual Intelligence
            recent_form_weighted=recent_form_weighted,
            home_away_split_score=home_away_split_score,
            opposition_strength=opposition_strength,
            league_tempo_score=league_tempo_score,
            real_variance=real_variance,
            explosive_match_rate=explosive_match_rate,
            late_goals_tendency=late_goals_tendency,
            fake_under_risk=fake_under_risk,
            btts_tendency=btts_tendency,
            over_tendency=over_tendency,
            defensive_stability=defensive_stability,
            attacking_consistency=attacking_consistency,
            signal_explanations=signal_explanations,
            # STEP 4: Weighted projections
            weighted_goal_projection=round(weighted_goal_projection, 2),
            weighted_ht_projection=round(weighted_ht_projection, 2),
            weighted_tempo_projection=weighted_tempo_projection,
            weighted_form_score=round(weighted_form_score, 1),
            # Metadata
            sample_size=len(ft_goals),
            data_quality=data_quality
        )
        
        logger.info(f"[PROFILE] Generated: {scoring_profile}, {tempo_profile}, interest={interest_score:.0f}")
        
        return profile
    
    def _detect_tempo_profile(self, avg_goals: float, avg_ht_goals: float) -> str:
        """Détecte le profil de tempo"""
        if avg_goals <= 1.8:
            return "LOW_TEMPO"
        elif avg_goals >= 3.2:
            return "HIGH_TEMPO"
        else:
            return "MEDIUM_TEMPO"
    
    def _detect_scoring_profile(self, avg_goals: float, ft_goals: List[int]) -> str:
        """Détecte le profil de scoring"""
        over_2_5 = sum(1 for g in ft_goals if g > 2.5) / len(ft_goals)
        
        if avg_goals <= 1.5:
            return "EXTREME_UNDER"
        elif avg_goals <= 2.2:
            return "LOW_SCORING"
        elif avg_goals >= 3.8:
            return "EXTREME_OVER"
        elif avg_goals >= 3.0:
            return "HIGH_SCORING"
        else:
            return "BALANCED"
    
    def _detect_specific_profiles(
        self,
        ft_goals: List[int],
        ht_goals: List[int],
        match_history: List[Dict[str, Any]] = None
    ) -> List[str]:
        """Détecte les profils spécifiques diversifiés"""
        profiles = []

        if not ft_goals or len(ft_goals) < 3:
            return profiles

        avg_goals = sum(ft_goals) / len(ft_goals)
        avg_ht = sum(ht_goals) / len(ht_goals) if ht_goals else 0

        # HIGH_TEMPO_PROFILE
        if avg_goals >= 3.0:
            profiles.append("HIGH_TEMPO")

        # BTTS_PROFILE
        if match_history and len(match_history) >= 3:
            btts_count = sum(
                1 for m in match_history
                if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
            )
            btts_rate = btts_count / len(match_history)
            if btts_rate >= 0.60:
                profiles.append("BTTS_PROFILE")

        # LATE_GOAL_PROFILE (goals concentrated in second half)
        if ht_goals and len(ht_goals) >= 3:
            second_half_goals = [ft - ht for ft, ht in zip(ft_goals, ht_goals)]
            avg_second_half = sum(second_half_goals) / len(second_half_goals)
            if avg_second_half > avg_ht * 1.5:
                profiles.append("LATE_GOAL_PROFILE")

        # SECOND_HALF_EXPLOSION (very active second half)
        if ht_goals and len(ht_goals) >= 3:
            second_half_goals = [ft - ht for ft, ht in zip(ft_goals, ht_goals)]
            avg_second_half = sum(second_half_goals) / len(second_half_goals)
            if avg_second_half >= 2.0:
                profiles.append("SECOND_HALF_EXPLOSION")

        # OVER_ACCELERATION (increasing goals over time)
        if len(ft_goals) >= 5:
            first_half_avg = sum(ft_goals[:len(ft_goals)//2]) / (len(ft_goals)//2)
            second_half_avg = sum(ft_goals[len(ft_goals)//2:]) / (len(ft_goals) - len(ft_goals)//2)
            if second_half_avg > first_half_avg * 1.3:
                profiles.append("OVER_ACCELERATION")

        # DEAD_FIRST_HALF (very low HT activity)
        if ht_goals and len(ht_goals) >= 3:
            if avg_ht <= 0.4:
                profiles.append("DEAD_FIRST_HALF")

        # LOW_FIRST_HALF_HIGH_SECOND (contrast between halves)
        if ht_goals and len(ht_goals) >= 3:
            second_half_goals = [ft - ht for ft, ht in zip(ft_goals, ht_goals)]
            avg_second_half = sum(second_half_goals) / len(second_half_goals)
            if avg_ht <= 0.5 and avg_second_half >= 1.5:
                profiles.append("LOW_FIRST_HALF_HIGH_SECOND")

        # HOME_DOMINANT (home scores heavily)
        if match_history and len(match_history) >= 3:
            home_avg = sum(m.get("home_goals", 0) for m in match_history) / len(match_history)
            away_avg = sum(m.get("away_goals", 0) for m in match_history) / len(match_history)
            if home_avg > away_avg * 1.5:
                profiles.append("HOME_DOMINANT")

        # AWAY_COLLAPSE (away concedes heavily)
        if match_history and len(match_history) >= 3:
            away_conceded = sum(m.get("home_goals", 0) for m in match_history) / len(match_history)
            if away_conceded >= 2.0:
                profiles.append("AWAY_COLLAPSE")

        # COMEBACK_PROFILE (high volatility in scoring)
        if len(ft_goals) >= 5:
            goal_variance = self._calculate_variance(ft_goals)
            if goal_variance >= 2.5:
                profiles.append("COMEBACK_PROFILE")

        # EXTREME_UNDER_PROFILE
        if avg_goals <= 1.5:
            profiles.append("EXTREME_UNDER_PROFILE")

        # EXTREME_OVER_PROFILE
        if avg_goals >= 3.5:
            profiles.append("EXTREME_OVER_PROFILE")

        # ASYMMETRIC_SCORING (high variance in goal distribution)
        if len(ft_goals) >= 5:
            goal_range = max(ft_goals) - min(ft_goals)
            if goal_range >= 4:
                profiles.append("ASYMMETRIC_SCORING")

        return profiles
    
    def _detect_characteristics(
        self,
        ft_goals: List[int],
        ht_goals: List[int],
        variance: float,
        match_history: List[Dict[str, Any]] = None
    ) -> List[str]:
        """Détecte les caractéristiques du match"""
        characteristics = []
        
        avg_goals = sum(ft_goals) / len(ft_goals)
        
        # DEFENSIVE_CLASH
        if avg_goals <= 1.8:
            characteristics.append("defensive_clash")
        
        # CHAOTIC_MATCH
        if variance >= 3.0:
            characteristics.append("chaotic_match")
        
        # HIGH_STABILITY
        if variance <= 1.0:
            characteristics.append("high_stability")
        
        # CONSISTENT_PATTERN
        if variance <= 1.5 and len(ft_goals) >= 5:
            characteristics.append("consistent_pattern")
        
        # VOLATILE_MATCH
        if variance >= 2.5:
            characteristics.append("volatile_match")
        
        return characteristics
    
    def _detect_statistical_angles(
        self,
        ft_goals: List[int],
        ht_goals: List[int],
        avg_goals: float,
        avg_ht_goals: float
    ) -> List[str]:
        """Détecte les angles statistiques intéressants"""
        angles = []
        
        # HT angles
        if ht_goals and len(ht_goals) >= 3:
            ht_under_0_5 = sum(1 for g in ht_goals if g < 0.5) / len(ht_goals)
            ht_under_1_5 = sum(1 for g in ht_goals if g < 1.5) / len(ht_goals)
            
            if ht_under_0_5 >= 0.60:
                angles.append("HT U0.5")
            if ht_under_1_5 >= 0.70:
                angles.append("HT U1.5")
            if avg_ht_goals >= 1.2:
                angles.append("HT O0.5")
        
        # FT angles
        under_1_5 = sum(1 for g in ft_goals if g < 1.5) / len(ft_goals)
        under_2_5 = sum(1 for g in ft_goals if g < 2.5) / len(ft_goals)
        over_2_5 = sum(1 for g in ft_goals if g > 2.5) / len(ft_goals)
        over_3_5 = sum(1 for g in ft_goals if g > 3.5) / len(ft_goals)
        
        if under_1_5 >= 0.60:
            angles.append("FT U1.5")
        if under_2_5 >= 0.70:
            angles.append("FT U2.5")
        if over_2_5 >= 0.70:
            angles.append("FT O2.5")
        if over_3_5 >= 0.60:
            angles.append("FT O3.5")
        
        return angles
    
    def _calculate_interest_score(
        self,
        scoring_profile: str,
        specific_profiles: List[str],
        characteristics: List[str],
        variance: float
    ) -> float:
        """Calcule le score d'intérêt (0-100) - Enhanced with pattern rarity"""
        score = 50.0  # Base

        # Bonus pour profils extrêmes (rare patterns)
        if scoring_profile in ["EXTREME_UNDER", "EXTREME_OVER"]:
            score += 25  # Increased for rarity
        elif scoring_profile in ["LOW_SCORING", "HIGH_SCORING"]:
            score += 15

        # Bonus pour profils spécifiques diversifiés
        rare_profiles = ["BTTS_PROFILE", "SECOND_HALF_EXPLOSION", "LATE_GOAL_PROFILE",
                         "DEAD_FIRST_HALF", "LOW_FIRST_HALF_HIGH_SECOND", "HOME_DOMINANT",
                         "AWAY_COLLAPSE", "COMEBACK_PROFILE", "ASYMMETRIC_SCORING"]
        for profile in specific_profiles:
            if profile in rare_profiles:
                score += 8  # Bonus for rare patterns
            else:
                score += 4

        # Bonus pour caractéristiques
        if "high_stability" in characteristics:
            score += 12  # High stability = reliable pattern
        if "chaotic_match" in characteristics:
            score += 15  # Chaos = interesting
        if "consistent_pattern" in characteristics:
            score += 10  # Consistency = value

        # Pénalité pour variance trop faible (ennuyeux)
        if variance < 0.3:
            score -= 15  # Too predictable = boring
        elif variance < 0.5:
            score -= 5

        # Bonus pour variance modérée (sweet spot)
        if 0.8 <= variance <= 2.0:
            score += 8  # Interesting but not chaotic

        return min(100, max(0, score))
    
    def _calculate_confidence_score(
        self,
        sample_size: int,
        variance: float,
        ht_goals: List[int] = None,
        ft_goals: List[int] = None
    ) -> float:
        """Calcule le score de confiance (0-100) - Enhanced with HT/FT coherence"""
        score = 0.0

        # Sample size (repeatability)
        if sample_size >= 20:
            score += 55  # Excellent repeatability
        elif sample_size >= 15:
            score += 45
        elif sample_size >= 10:
            score += 35
        elif sample_size >= 5:
            score += 20
        else:
            score += 5  # Low repeatability

        # Variance (stability)
        if variance <= 0.8:
            score += 25  # Very stable
        elif variance <= 1.5:
            score += 20  # Stable
        elif variance <= 2.5:
            score += 10  # Moderate
        elif variance <= 4.0:
            score += 5  # Some variance

        # HT/FT coherence (if both available)
        if ht_goals and ft_goals and len(ht_goals) >= 3 and len(ft_goals) >= 3:
            # Calculate correlation between HT and FT
            ht_avg = sum(ht_goals) / len(ht_goals)
            ft_avg = sum(ft_goals) / len(ft_goals)
            second_half_avg = sum([ft - ht for ft, ht in zip(ft_goals, ht_goals)]) / len(ft_goals)

            # Bonus for coherent patterns
            if ht_avg <= 0.5 and ft_avg <= 2.0:
                score += 10  # Consistent low scoring
            elif second_half_avg > ht_avg * 1.5:
                score += 8  # Clear second half pattern
            elif abs(ht_avg - second_half_avg) <= 0.5:
                score += 8  # Balanced halves

        # Bonus pour gros sample + faible variance (high repeatability)
        if sample_size >= 15 and variance <= 1.0:
            score += 15
        elif sample_size >= 10 and variance <= 1.5:
            score += 10

        return min(100, score)
    
    def _calculate_volatility_score(self, variance: float, ft_goals: List[int]) -> float:
        """Calcule le score de volatilité (0-100)"""
        # Plus la variance est élevée, plus c'est volatil
        volatility = min(100, variance * 20)
        
        # Ajuster avec range
        goal_range = max(ft_goals) - min(ft_goals)
        volatility += min(30, goal_range * 3)
        
        return min(100, volatility)
    
    def _assess_data_quality(self, ft_sample: int, ht_sample: int) -> str:
        """Évalue la qualité des données"""
        if ft_sample >= 15 and ht_sample >= 15:
            return "EXCELLENT"
        elif ft_sample >= 10 and ht_sample >= 10:
            return "GOOD"
        elif ft_sample >= 5:
            return "FAIR"
        else:
            return "LIMITED"
    
    def _calculate_variance(self, goals: List[int]) -> float:
        """Calcule la variance"""
        if len(goals) < 2:
            return 0.0
        
        mean = sum(goals) / len(goals)
        variance = sum((x - mean) ** 2 for x in goals) / len(goals)
        return variance
    
    def _create_limited_profile(self) -> MatchProfile:
        """Crée un profil limité pour données insuffisantes"""
        return MatchProfile(
            tempo_profile="UNKNOWN",
            scoring_profile="UNKNOWN",
            specific_profiles=[],
            characteristics=["limited_data"],
            statistical_angles=[],
            interest_score=20.0,
            confidence_score=10.0,
            volatility_score=50.0,
            # Phase 4: Contextual Intelligence (default values)
            recent_form_weighted=0.0,
            home_away_split_score=0.0,
            opposition_strength=0.0,
            league_tempo_score=0.0,
            real_variance=0.0,
            explosive_match_rate=0.0,
            late_goals_tendency=0.0,
            fake_under_risk=0.0,
            btts_tendency=0.0,
            over_tendency=0.0,
            defensive_stability=0.0,
            attacking_consistency=0.0,
            signal_explanations=["Insufficient data for contextual analysis"],
            # STEP 4: Weighted projections (defaults)
            weighted_goal_projection=0.0,
            weighted_ht_projection=0.0,
            weighted_tempo_projection="",
            weighted_form_score=0.0,
            sample_size=0,
            data_quality="INSUFFICIENT"
        )

    # ==========================================
    # PHASE 4: CONTEXTUAL INTELLIGENCE METHODS
    # ==========================================

    def _calculate_recent_form_weighted(self, ft_goals: List[int]) -> float:
        """
        Weighted recent form score (0-100).
        Utilise la pondération 50/30/20 : derniers 5 matchs = 50%, 6-10 = 30%, anciens = 20%.
        """
        if len(ft_goals) < 3:
            return 0.0

        recent  = ft_goals[:5]            # poids 50%
        medium  = ft_goals[5:10]          # poids 30%
        older   = ft_goals[10:]           # poids 20%

        avg_recent = sum(recent) / len(recent) if recent else 0.0
        avg_medium = sum(medium) / len(medium) if medium else avg_recent
        avg_older  = sum(older)  / len(older)  if older  else avg_medium

        weighted_avg = avg_recent * 0.50 + avg_medium * 0.30 + avg_older * 0.20
        return min(100.0, weighted_avg * 20)  # 5 buts/match → score 100

    def _calculate_weighted_goal_projection(self, goals: List[int]) -> float:
        """
        Projection pondérée des buts avec 50/30/20.
        Retourne le nombre de buts projeté pour le prochain match.
        """
        if not goals or len(goals) < 3:
            return sum(goals) / len(goals) if goals else 0.0

        recent = goals[:5]
        medium = goals[5:10]
        older  = goals[10:]

        avg_recent = sum(recent) / len(recent)
        avg_medium = sum(medium) / len(medium) if medium else avg_recent
        avg_older  = sum(older)  / len(older)  if older  else avg_medium

        return round(avg_recent * 0.50 + avg_medium * 0.30 + avg_older * 0.20, 2)

    def _classify_tempo(self, avg_goals: float) -> str:
        """Classifie le tempo basé sur la projection pondérée."""
        if avg_goals <= 1.8:
            return "LOW_TEMPO"
        elif avg_goals >= 3.2:
            return "HIGH_TEMPO"
        return "MEDIUM_TEMPO"

    def _calculate_weighted_form_score(self, ft_goals: List[int], ht_goals: List[int] = None) -> float:
        """
        Score de forme pondéré global (0-100).
        Combine la tendance FT et HT avec pondération 50/30/20.
        """
        if not ft_goals or len(ft_goals) < 3:
            return 0.0

        ft_proj = self._calculate_weighted_goal_projection(ft_goals)
        ht_proj = self._calculate_weighted_goal_projection(ht_goals) if ht_goals else ft_proj / 2

        # Normalise 0-100: 3 buts FT = 60, 5 buts = 100
        ft_score = min(100, ft_proj * 20)
        ht_score = min(100, ht_proj * 40)

        return round(ft_score * 0.60 + ht_score * 0.40, 1)

    def _calculate_home_away_split_score(self, match_history: List[Dict[str, Any]]) -> float:
        """Calculate home/away split coherence score"""
        if not match_history or len(match_history) < 3:
            return 0.0

        home_goals = [m.get("home_goals", 0) for m in match_history]
        away_goals = [m.get("away_goals", 0) for m in match_history]

        if not home_goals or not away_goals:
            return 0.0

        home_avg = sum(home_goals) / len(home_goals)
        away_avg = sum(away_goals) / len(away_goals)

        # Score based on split consistency
        split_ratio = home_avg / away_avg if away_avg > 0 else 0
        if 0.8 <= split_ratio <= 1.2:
            return 80.0  # Balanced split
        elif 0.6 <= split_ratio <= 1.4:
            return 60.0  # Moderate split
        else:
            return 40.0  # Extreme split

    def _calculate_opposition_strength(self, match_history: List[Dict[str, Any]]) -> float:
        """Calculate opposition strength based on goals conceded"""
        if not match_history or len(match_history) < 3:
            return 0.0

        goals_conceded = [m.get("away_goals", 0) for m in match_history]  # Goals conceded at home
        avg_conceded = sum(goals_conceded) / len(goals_conceded)

        # Lower conceded = stronger opposition faced
        if avg_conceded <= 0.5:
            return 90.0
        elif avg_conceded <= 1.0:
            return 75.0
        elif avg_conceded <= 1.5:
            return 60.0
        elif avg_conceded <= 2.0:
            return 45.0
        else:
            return 30.0

    def _calculate_league_tempo_score(self, avg_goals: float, avg_ht_goals: float) -> float:
        """Calculate league tempo score based on average goals"""
        if avg_goals == 0:
            return 0.0

        # Higher goals = higher tempo
        if avg_goals >= 3.5:
            return 90.0
        elif avg_goals >= 3.0:
            return 75.0
        elif avg_goals >= 2.5:
            return 60.0
        elif avg_goals >= 2.0:
            return 45.0
        elif avg_goals >= 1.5:
            return 30.0
        else:
            return 15.0

    def _calculate_real_variance(self, ft_goals: List[int], variance: float) -> float:
        """Calculate real variance score normalized to 0-100"""
        if len(ft_goals) < 2:
            return 0.0

        # Normalize variance to 0-100
        return min(100, variance * 25)

    def _calculate_explosive_match_rate(self, ft_goals: List[int]) -> float:
        """Calculate rate of explosive matches (4+ goals)"""
        if len(ft_goals) < 3:
            return 0.0

        explosive_count = sum(1 for g in ft_goals if g >= 4)
        explosive_rate = explosive_count / len(ft_goals)
        return explosive_rate * 100

    def _calculate_late_goals_tendency(self, ht_goals: List[int], ft_goals: List[int]) -> float:
        """Calculate tendency for late goals (second half activity)"""
        if not ht_goals or not ft_goals or len(ht_goals) < 3:
            return 0.0

        second_half_goals = [ft - ht for ft, ht in zip(ft_goals, ht_goals)]
        avg_second_half = sum(second_half_goals) / len(second_half_goals)
        avg_first_half = sum(ht_goals) / len(ht_goals)

        if avg_first_half == 0:
            return 100.0

        second_half_ratio = avg_second_half / avg_first_half
        return min(100, second_half_ratio * 50)

    def _calculate_fake_under_risk(self, ft_goals: List[int], avg_goals: float) -> float:
        """Calculate risk of fake under (low scoring but high variance)"""
        if len(ft_goals) < 5:
            return 0.0

        variance = self._calculate_variance(ft_goals)

        # Fake under = low average but high variance
        if avg_goals <= 2.0 and variance >= 2.0:
            return 80.0
        elif avg_goals <= 2.5 and variance >= 1.5:
            return 60.0
        elif avg_goals <= 3.0 and variance >= 1.0:
            return 40.0
        else:
            return 20.0

    def _calculate_btts_tendency(self, match_history: List[Dict[str, Any]]) -> float:
        """Calculate BTTS tendency"""
        if not match_history or len(match_history) < 3:
            return 0.0

        btts_count = sum(
            1 for m in match_history
            if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
        )
        btts_rate = btts_count / len(match_history)
        return btts_rate * 100

    def _calculate_over_tendency(self, ft_goals: List[int]) -> float:
        """Calculate over tendency (2.5+ goals)"""
        if len(ft_goals) < 3:
            return 0.0

        over_count = sum(1 for g in ft_goals if g >= 3)
        over_rate = over_count / len(ft_goals)
        return over_rate * 100

    def _calculate_defensive_stability(self, ft_goals: List[int], variance: float) -> float:
        """Calculate defensive stability (inverse of variance)"""
        if len(ft_goals) < 2:
            return 0.0

        # Lower variance = higher stability
        if variance <= 0.5:
            return 95.0
        elif variance <= 1.0:
            return 80.0
        elif variance <= 1.5:
            return 65.0
        elif variance <= 2.0:
            return 50.0
        elif variance <= 3.0:
            return 35.0
        else:
            return 20.0

    def _calculate_attacking_consistency(self, ft_goals: List[int]) -> float:
        """Calculate attacking consistency (goal scoring regularity)"""
        if len(ft_goals) < 3:
            return 0.0

        # Check if team scores consistently (not too many 0-goal matches)
        zero_goal_count = sum(1 for g in ft_goals if g == 0)
        zero_goal_rate = zero_goal_count / len(ft_goals)

        # Lower zero-goal rate = higher consistency
        if zero_goal_rate <= 0.1:
            return 90.0
        elif zero_goal_rate <= 0.2:
            return 75.0
        elif zero_goal_rate <= 0.3:
            return 60.0
        elif zero_goal_rate <= 0.4:
            return 45.0
        else:
            return 30.0

    def _generate_signal_explanations(
        self,
        scoring_profile: str,
        specific_profiles: List[str],
        characteristics: List[str],
        recent_form_weighted: float,
        explosive_match_rate: float,
        late_goals_tendency: float,
        btts_tendency: float,
        over_tendency: float,
        ft_goals: List[int]
    ) -> List[str]:
        """Generate human-readable explanations for why signals exist"""
        explanations = []

        # Scoring profile explanation
        if scoring_profile == "EXTREME_UNDER":
            explanations.append(f"Extreme under pattern: {len(ft_goals)} matches avg {sum(ft_goals)/len(ft_goals):.1f} goals")
        elif scoring_profile == "EXTREME_OVER":
            explanations.append(f"Extreme over pattern: {len(ft_goals)} matches avg {sum(ft_goals)/len(ft_goals):.1f} goals")

        # Specific profile explanations
        if "BTTS_PROFILE" in specific_profiles:
            explanations.append(f"BTTS tendency: {btts_tendency:.0f}% of matches have both teams score")
        if "SECOND_HALF_EXPLOSION" in specific_profiles:
            explanations.append(f"Second half explosion: {late_goals_tendency:.0f}% late goals tendency")
        if "HIGH_TEMPO" in specific_profiles:
            explanations.append(f"High tempo: {explosive_match_rate:.0f}% explosive matches")

        # Recent form explanation
        if recent_form_weighted >= 70:
            explanations.append(f"Strong recent form: weighted score {recent_form_weighted:.0f}/100")
        elif recent_form_weighted <= 30:
            explanations.append(f"Weak recent form: weighted score {recent_form_weighted:.0f}/100")

        # Characteristics explanations
        if "high_stability" in characteristics:
            explanations.append("High stability: consistent defensive pattern")
        if "chaotic_match" in characteristics:
            explanations.append("Chaotic pattern: high variance in results")

        return explanations
