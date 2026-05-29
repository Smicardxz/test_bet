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
    """Profil complet d'un match"""
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
    
    # Métadonnées
    sample_size: int
    data_quality: str  # EXCELLENT, GOOD, FAIR, LIMITED
    
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
        confidence_score = self._calculate_confidence_score(len(ft_goals), variance)
        volatility_score = self._calculate_volatility_score(variance, ft_goals)
        
        # 7. DATA QUALITY
        data_quality = self._assess_data_quality(len(ft_goals), len(ht_goals))
        
        profile = MatchProfile(
            tempo_profile=tempo_profile,
            scoring_profile=scoring_profile,
            specific_profiles=specific_profiles,
            characteristics=characteristics,
            statistical_angles=statistical_angles,
            interest_score=interest_score,
            confidence_score=confidence_score,
            volatility_score=volatility_score,
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
        """Détecte les profils spécifiques"""
        profiles = []
        
        # HT_GOAL_PROFILE
        if ht_goals and len(ht_goals) >= 3:
            avg_ht = sum(ht_goals) / len(ht_goals)
            ht_over_0_5 = sum(1 for g in ht_goals if g > 0.5) / len(ht_goals)
            
            if avg_ht >= 1.0 and ht_over_0_5 >= 0.70:
                profiles.append("HT_GOAL_PROFILE")
            elif avg_ht <= 0.5:
                profiles.append("SLOW_START_PROFILE")
        
        # BTTS_PROFILE
        if match_history and len(match_history) >= 3:
            btts_count = sum(
                1 for m in match_history
                if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
            )
            btts_rate = btts_count / len(match_history)
            
            if btts_rate >= 0.60:
                profiles.append("BTTS_PROFILE")
        
        # EXTREME_UNDER_PROFILE
        avg_goals = sum(ft_goals) / len(ft_goals)
        if avg_goals <= 1.5:
            profiles.append("EXTREME_UNDER_PROFILE")
        
        # EXTREME_OVER_PROFILE
        if avg_goals >= 3.5:
            profiles.append("EXTREME_OVER_PROFILE")
        
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
        """Calcule le score d'intérêt (0-100)"""
        score = 50.0  # Base
        
        # Bonus pour profils extrêmes
        if scoring_profile in ["EXTREME_UNDER", "EXTREME_OVER"]:
            score += 20
        elif scoring_profile in ["LOW_SCORING", "HIGH_SCORING"]:
            score += 10
        
        # Bonus pour profils spécifiques
        score += len(specific_profiles) * 5
        
        # Bonus pour caractéristiques
        if "high_stability" in characteristics:
            score += 10
        if "chaotic_match" in characteristics:
            score += 15  # Chaos = intéressant
        
        # Pénalité pour variance trop faible (ennuyeux)
        if variance < 0.5:
            score -= 10
        
        return min(100, max(0, score))
    
    def _calculate_confidence_score(self, sample_size: int, variance: float) -> float:
        """Calcule le score de confiance (0-100)"""
        score = 0.0
        
        # Sample size
        if sample_size >= 15:
            score += 50
        elif sample_size >= 10:
            score += 40
        elif sample_size >= 5:
            score += 25
        else:
            score += 10
        
        # Variance (stabilité)
        if variance <= 1.0:
            score += 30
        elif variance <= 2.0:
            score += 20
        elif variance <= 3.0:
            score += 10
        
        # Bonus pour gros sample + faible variance
        if sample_size >= 10 and variance <= 1.5:
            score += 20
        
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
            sample_size=0,
            data_quality="INSUFFICIENT"
        )
