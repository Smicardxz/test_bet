"""
Bet Portfolio Engine
Generates single bets and safe combinations from anomaly results
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import logging

from app.services.betting.bet_candidate import BetCandidate, RiskLevel


logger = logging.getLogger(__name__)


@dataclass
class BetCombination:
    """
    Represents a combination of multiple bets
    
    Rules enforced:
    - No correlated bets from same match (unless explicitly compatible)
    - Maximum 2-4 selections
    - High confidence required
    - Sufficient data quality
    - Manageable risk
    """
    
    bets: List[BetCandidate] = field(default_factory=list)
    combined_odds: float = 0.0
    combined_confidence: float = 0.0
    risk_score: float = 0.0
    explanation: str = ""
    correlation_risk: str = "LOW"  # "LOW", "MEDIUM", "HIGH"
    
    @property
    def match_ids(self) -> Set[str]:
        """Get unique match IDs in this combination"""
        return {bet.match_id for bet in self.bets}
    
    @property
    def market_types(self) -> Set[str]:
        """Get unique market types in this combination"""
        return {bet.market_type for bet in self.bets}
    
    @property
    def is_valid(self) -> bool:
        """Check if combination is valid"""
        return (
            2 <= len(self.bets) <= 4 and
            self.correlation_risk != "HIGH" and
            self.combined_confidence >= 0.60 and
            self.risk_score <= 0.70
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "bets": [bet.to_dict() for bet in self.bets],
            "combined_odds": round(self.combined_odds, 2),
            "combined_confidence": round(self.combined_confidence, 2),
            "risk_score": round(self.risk_score, 2),
            "explanation": self.explanation,
            "correlation_risk": self.correlation_risk,
            "is_valid": self.is_valid,
            "bet_count": len(self.bets)
        }


class BetPortfolioEngine:
    """
    Engine for ranking single bets and generating safe combinations
    
    Philosophy:
    - Each bet is evaluated individually
    - Market history doesn't automatically exclude strong individual bets
    - Combinations are built with correlation awareness
    - Maximum 2-4 selections per combination
    """
    
    def __init__(
        self,
        min_confidence: float = 0.60,
        min_data_quality: float = 0.65,
        max_combination_size: int = 4,
        min_combination_size: int = 2
    ):
        """
        Initialize portfolio engine
        
        Args:
            min_confidence: Minimum confidence score for bets
            min_data_quality: Minimum data quality score
            max_combination_size: Maximum bets in a combination
            min_combination_size: Minimum bets in a combination
        """
        self.min_confidence = min_confidence
        self.min_data_quality = min_data_quality
        self.max_combination_size = max_combination_size
        self.min_combination_size = min_combination_size
        
        logger.info(f"BetPortfolioEngine initialized with min_confidence={min_confidence}")
    
    def rank_single_bets(
        self,
        candidates: List[BetCandidate],
        max_results: int = 20
    ) -> List[BetCandidate]:
        """
        Rank single bets by combined score
        
        Each bet is evaluated individually, not based on market history.
        
        Args:
            candidates: List of bet candidates
            max_results: Maximum number of results to return
            
        Returns:
            Ranked list of bet candidates
        """
        logger.info(f"Ranking {len(candidates)} single bets")
        
        # Filter by minimum thresholds
        filtered = [
            bet for bet in candidates
            if bet.confidence_score >= self.min_confidence and
            bet.data_quality_score >= self.min_data_quality
        ]
        
        logger.info(f"After filtering: {len(filtered)} bets (confidence>={self.min_confidence}, quality>={self.min_data_quality})")
        
        # Sort by combined score
        ranked = sorted(filtered, key=lambda b: b.combined_score, reverse=True)
        
        return ranked[:max_results]
    
    def generate_safe_combinations(
        self,
        candidates: List[BetCandidate],
        max_combinations: int = 10
    ) -> List[BetCombination]:
        """
        Generate safe combinations from bet candidates
        
        Rules:
        - 2-4 bets per combination
        - No correlated bets from same match
        - High confidence required
        - Sufficient data quality
        - Manageable risk
        
        Args:
            candidates: List of bet candidates
            max_combinations: Maximum number of combinations to generate
            
        Returns:
            List of safe bet combinations
        """
        logger.info(f"Generating safe combinations from {len(candidates)} candidates")
        
        # Filter for high-quality bets
        high_quality = [
            bet for bet in candidates
            if bet.is_high_confidence and bet.is_safe
        ]
        
        logger.info(f"High-quality bets: {len(high_quality)}")
        
        if len(high_quality) < self.min_combination_size:
            logger.warning(f"Not enough high-quality bets for combinations (need {self.min_combination_size})")
            return []
        
        # Generate combinations
        combinations = []
        
        # Try different combination sizes
        for size in range(self.min_combination_size, min(self.max_combination_size + 1, len(high_quality) + 1)):
            combinations.extend(self._generate_combinations_of_size(high_quality, size))
        
        # Sort by combined odds and confidence
        combinations.sort(
            key=lambda c: (c.combined_confidence, c.combined_odds),
            reverse=True
        )
        
        # Filter valid combinations
        valid_combinations = [c for c in combinations if c.is_valid]
        
        logger.info(f"Generated {len(valid_combinations)} valid combinations")
        
        return valid_combinations[:max_combinations]
    
    def generate_combinations(
        self,
        candidates: List[BetCandidate],
        max_combinations: int = 10
    ) -> List[BetCombination]:
        """
        Generate combinations from bet candidates (alias for generate_safe_combinations)
        
        Args:
            candidates: List of bet candidates
            max_combinations: Maximum number of combinations to generate
            
        Returns:
            List of bet combinations
        """
        return self.generate_safe_combinations(candidates, max_combinations)
    
    def _generate_combinations_of_size(
        self,
        candidates: List[BetCandidate],
        size: int
    ) -> List[BetCombination]:
        """Generate all combinations of a specific size"""
        from itertools import combinations
        
        result = []
        
        for combo in combinations(candidates, size):
            # Check correlation risk
            correlation_risk = self.detect_correlation_risk(combo)
            
            if correlation_risk == "HIGH":
                continue  # Skip highly correlated combinations
            
            # Calculate combined metrics
            combined_odds = self.calculate_combined_odds(combo)
            combined_confidence = self.calculate_combined_confidence(combo)
            risk_score = self.calculate_combined_risk(combo)
            
            # Only include if reasonable
            if combined_confidence >= 0.55 and risk_score <= 0.75:
                combination = BetCombination(
                    bets=list(combo),
                    combined_odds=combined_odds,
                    combined_confidence=combined_confidence,
                    risk_score=risk_score,
                    explanation=self.explain_combination(combo),
                    correlation_risk=correlation_risk
                )
                result.append(combination)
        
        return result
    
    def calculate_combined_odds(self, bets: List[BetCandidate]) -> float:
        """
        Calculate combined odds for a combination
        
        Odds are multiplied for accumulator bets
        """
        if not bets:
            return 0.0
        
        # Filter bets with valid odds
        valid_odds = [bet.odd for bet in bets if bet.odd and bet.odd > 1.0]
        
        if not valid_odds:
            return 0.0
        
        # Multiply odds
        combined = 1.0
        for odd in valid_odds:
            combined *= odd
        
        return round(combined, 2)
    
    def calculate_combined_confidence(self, bets: List[BetCandidate]) -> float:
        """
        Calculate combined confidence for a combination
        
        Uses geometric mean to penalize weak links
        """
        if not bets:
            return 0.0
        
        confidences = [bet.confidence_score for bet in bets]
        
        # Geometric mean
        product = 1.0
        for conf in confidences:
            product *= conf
        
        combined = product ** (1.0 / len(confidences))
        
        return round(combined, 2)
    
    def calculate_combined_risk(self, bets: List[BetCandidate]) -> float:
        """
        Calculate combined risk score for a combination
        
        Higher score = higher risk
        """
        if not bets:
            return 1.0
        
        # Average risk score
        avg_risk = sum(bet.risk_score for bet in bets) / len(bets)
        
        # Add penalty for correlation
        correlation_risk = self.detect_correlation_risk(bets)
        if correlation_risk == "MEDIUM":
            avg_risk += 0.10
        elif correlation_risk == "HIGH":
            avg_risk += 0.25
        
        return round(min(avg_risk, 1.0), 2)
    
    def detect_correlation_risk(self, bets: List[BetCandidate]) -> str:
        """
        Detect correlation risk between bets
        
        Rules:
        - Multiple bets from same match = HIGH risk
        - Same market type across different matches = MEDIUM risk
        - Under markets in same competition = MEDIUM risk
        - No correlation = LOW risk
        """
        if len(bets) < 2:
            return "LOW"
        
        match_ids = [bet.match_id for bet in bets]
        market_types = [bet.market_type for bet in bets]
        competitions = [bet.competition for bet in bets]
        
        # Check for same match
        if len(set(match_ids)) < len(match_ids):
            return "HIGH"
        
        # Check for same market type
        if len(set(market_types)) < len(market_types):
            return "MEDIUM"
        
        # Check for under markets in same competition
        under_markets = [m for m in market_types if "under" in m.lower()]
        if len(under_markets) >= 2 and len(set(competitions)) < len(competitions):
            return "MEDIUM"
        
        return "LOW"
    
    def explain_combination(self, bets: List[BetCandidate]) -> str:
        """
        Generate explanation for a combination
        """
        if not bets:
            return "Empty combination"
        
        parts = []
        
        # Describe each bet
        for i, bet in enumerate(bets, 1):
            parts.append(
                f"{i}. {bet.home_team} vs {bet.away_team} "
                f"({bet.market_type.replace('_', ' ').upper()}) "
                f"@ {bet.odd if bet.odd else 'N/A'} "
                f"(confidence: {bet.confidence_score:.2f})"
            )
        
        # Add summary
        combined_odds = self.calculate_combined_odds(bets)
        combined_conf = self.calculate_combined_confidence(bets)
        
        explanation = " | ".join(parts)
        explanation += f" | Combined odds: {combined_odds} | Combined confidence: {combined_conf:.2f}"
        
        return explanation
    
    def generate_portfolio(
        self,
        candidates: List[BetCandidate],
        max_single_bets: int = 15,
        max_combinations: int = 8
    ) -> Dict[str, List]:
        """
        Generate complete portfolio with single bets and combinations
        
        Returns:
            Dict with "single_bets" and "combinations" keys
        """
        logger.info("Generating complete portfolio")
        
        single_bets = self.rank_single_bets(candidates, max_results=max_single_bets)
        combinations = self.generate_safe_combinations(candidates, max_combinations=max_combinations)
        
        portfolio = {
            "single_bets": [bet.to_dict() for bet in single_bets],
            "combinations": [combo.to_dict() for combo in combinations]
        }
        
        logger.info(f"Portfolio: {len(single_bets)} single bets, {len(combinations)} combinations")
        
        return portfolio
