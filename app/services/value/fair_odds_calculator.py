"""
Fair Odds Calculator
Transforme probabilité historique → cote théorique
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class FairOddsAssessment:
    """Assessment des cotes justes"""
    
    historical_probability: float  # 0-1
    fair_odd: float  # Cote théorique juste
    bookmaker_odd: Optional[float] = None
    bookmaker_implied_probability: Optional[float] = None
    value_gap_percentage: Optional[float] = None
    has_value: bool = False
    value_level: str = "WAITING_FOR_ODDS"
    
    def to_dict(self):
        return {
            "historical_probability": self.historical_probability,
            "fair_odd": self.fair_odd,
            "bookmaker_odd": self.bookmaker_odd,
            "bookmaker_implied_probability": self.bookmaker_implied_probability,
            "value_gap_percentage": self.value_gap_percentage,
            "has_value": self.has_value,
            "value_level": self.value_level
        }


class FairOddsCalculator:
    """
    Calcule les cotes justes basées sur probabilité historique
    
    Formule: fair_odd = 1 / probability
    
    Exemple: 95% → 1.05, 70% → 1.42
    """
    
    def calculate_fair_odds(
        self,
        historical_probability: float,  # 0-1
        bookmaker_odd: Optional[float] = None
    ) -> FairOddsAssessment:
        """
        Calcule cote juste et compare avec bookmaker
        
        Args:
            historical_probability: Probabilité historique (0-1)
            bookmaker_odd: Cote bookmaker (optionnel)
            
        Returns:
            FairOddsAssessment
        """
        
        # Clamp probability
        prob = max(0.01, min(0.99, historical_probability))
        
        # Calculer fair odd
        fair_odd = 1 / prob
        
        # Si bookmaker odd disponible, comparer
        if bookmaker_odd:
            # Probabilité implicite bookmaker
            bookmaker_implied_prob = 1 / bookmaker_odd
            
            # Value gap en pourcentage
            # Positif = value (notre proba > proba bookmaker)
            value_gap = (historical_probability - bookmaker_implied_prob) * 100
            
            # Déterminer si value
            has_value = value_gap > 0
            
            # Niveau de value
            if value_gap <= 0:
                value_level = "NO_VALUE"
            elif value_gap < 5:
                value_level = "LOW_VALUE"
            elif value_gap < 15:
                value_level = "MEDIUM_VALUE"
            elif value_gap < 25:
                value_level = "HIGH_VALUE"
            else:
                value_level = "EXTREME_VALUE"
            
            return FairOddsAssessment(
                historical_probability=historical_probability,
                fair_odd=fair_odd,
                bookmaker_odd=bookmaker_odd,
                bookmaker_implied_probability=bookmaker_implied_prob,
                value_gap_percentage=value_gap,
                has_value=has_value,
                value_level=value_level
            )
        else:
            # Pas de bookmaker odd → WAITING_FOR_ODDS
            return FairOddsAssessment(
                historical_probability=historical_probability,
                fair_odd=fair_odd,
                bookmaker_odd=None,
                bookmaker_implied_probability=None,
                value_gap_percentage=None,
                has_value=False,
                value_level="WAITING_FOR_ODDS"
            )
