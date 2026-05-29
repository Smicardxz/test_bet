"""
Value Detector
Distingue probabilité statistique de value bookmaker
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValueLevel(str, Enum):
    """Value levels based on gap between historical and bookmaker probability"""
    NO_VALUE = "NO_VALUE"  # Negative or very low gap
    LOW_VALUE = "LOW_VALUE"  # 5-15% gap
    MEDIUM_VALUE = "MEDIUM_VALUE"  # 15-25% gap
    HIGH_VALUE = "HIGH_VALUE"  # 25-40% gap
    EXTREME_VALUE = "EXTREME_VALUE"  # >40% gap


@dataclass
class ValueAssessment:
    """Value assessment for a betting opportunity"""
    
    # Statistical
    statistical_confidence: float  # 0-100
    historical_hit_rate: float  # 0-100
    
    # Bookmaker
    bookmaker_implied_probability: Optional[float]  # 0-100 (None if no odds)
    offered_odd: Optional[float]  # Decimal odd (None if no odds)
    
    # Value
    value_gap: Optional[float]  # Percentage gap (None if no odds)
    fair_odd_estimate: float  # Our estimate of fair odd
    value_level: str  # NO_VALUE, LOW_VALUE, etc.
    
    # Exploitability
    is_exploitable: bool
    has_odds: bool
    
    # Quality adjustments
    variance_penalty: float  # 0-1 (0 = high variance, 1 = low variance)
    sample_penalty: float  # 0-1 (0 = small sample, 1 = large sample)
    quality_penalty: float  # 0-1 (0 = poor quality, 1 = high quality)
    
    # Final
    adjusted_confidence: float  # Statistical confidence after penalties
    priority_score: float  # Final ranking score
    
    # Explanation
    reasons: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistical_confidence": self.statistical_confidence,
            "historical_hit_rate": self.historical_hit_rate,
            "bookmaker_implied_probability": self.bookmaker_implied_probability,
            "offered_odd": self.offered_odd,
            "value_gap": self.value_gap,
            "fair_odd_estimate": self.fair_odd_estimate,
            "value_level": self.value_level,
            "is_exploitable": self.is_exploitable,
            "has_odds": self.has_odds,
            "variance_penalty": self.variance_penalty,
            "sample_penalty": self.sample_penalty,
            "quality_penalty": self.quality_penalty,
            "adjusted_confidence": self.adjusted_confidence,
            "priority_score": self.priority_score,
            "reasons": self.reasons
        }


class ValueDetector:
    """
    Detects value by comparing statistical probability vs bookmaker odds
    
    Key distinction:
    - Statistical confidence: How likely the outcome is
    - Value: Whether the bookmaker odds are generous enough
    """
    
    def assess_value(
        self,
        statistical_probability: float,  # 0-1
        variance_score: float,  # 0-1 (higher = more stable)
        sample_size: int,
        data_quality: float,  # 0-1
        bookmaker_odd: Optional[float] = None,
        market_type: str = "UNDER"
    ) -> ValueAssessment:
        """
        Assess value of a betting opportunity
        
        Args:
            statistical_probability: Historical probability (0-1)
            variance_score: Stability score (0-1, higher = more stable)
            sample_size: Number of historical matches
            data_quality: Data quality score (0-1)
            bookmaker_odd: Bookmaker decimal odd (None if unavailable)
            market_type: Type of market (UNDER, OVER, BTTS, etc.)
            
        Returns:
            ValueAssessment with all metrics
        """
        
        reasons = []
        
        # Convert to percentages
        statistical_confidence = statistical_probability * 100
        historical_hit_rate = statistical_probability * 100
        
        # Calculate penalties
        variance_penalty = self._calculate_variance_penalty(variance_score)
        sample_penalty = self._calculate_sample_penalty(sample_size)
        quality_penalty = self._calculate_quality_penalty(data_quality)
        
        # Adjust confidence based on penalties
        adjusted_confidence = statistical_confidence * variance_penalty * sample_penalty * quality_penalty
        
        # Fair odd estimate (based on adjusted probability)
        adjusted_probability = adjusted_confidence / 100
        fair_odd_estimate = 1 / adjusted_probability if adjusted_probability > 0 else 999.0
        
        # Bookmaker analysis
        has_odds = bookmaker_odd is not None
        
        if has_odds:
            # Calculate bookmaker implied probability
            bookmaker_implied_probability = (1 / bookmaker_odd) * 100
            
            # Value gap (positive = value, negative = no value)
            value_gap = statistical_confidence - bookmaker_implied_probability
            
            # Determine value level
            value_level = self._determine_value_level(value_gap, variance_penalty, sample_penalty)
            
            # Exploitability
            is_exploitable = value_level in [ValueLevel.MEDIUM_VALUE, ValueLevel.HIGH_VALUE, ValueLevel.EXTREME_VALUE]
            
            # Reasons
            if value_gap < 0:
                reasons.append(f"Bookmaker implied probability ({bookmaker_implied_probability:.1f}%) higher than historical ({statistical_confidence:.1f}%)")
                reasons.append("No value - odds too low")
            elif value_gap < 5:
                reasons.append(f"Value gap too small ({value_gap:.1f}%)")
                reasons.append("Insufficient edge")
            else:
                reasons.append(f"Positive value gap: {value_gap:.1f}%")
                reasons.append(f"Historical probability ({statistical_confidence:.1f}%) vs Bookmaker ({bookmaker_implied_probability:.1f}%)")
                
                if value_level == ValueLevel.EXTREME_VALUE:
                    reasons.append("⚠️ EXTREME VALUE DETECTED - Verify data quality")
                elif value_level == ValueLevel.HIGH_VALUE:
                    reasons.append("✅ HIGH VALUE - Strong opportunity")
                elif value_level == ValueLevel.MEDIUM_VALUE:
                    reasons.append("✅ MEDIUM VALUE - Decent opportunity")
            
            # Add quality warnings
            if variance_penalty < 0.8:
                reasons.append(f"⚠️ High variance (penalty: {variance_penalty:.2f})")
            if sample_penalty < 0.8:
                reasons.append(f"⚠️ Small sample size ({sample_size} matches)")
            if quality_penalty < 0.8:
                reasons.append(f"⚠️ Data quality concerns (score: {data_quality:.2f})")
            
        else:
            # No odds available
            bookmaker_implied_probability = None
            value_gap = None
            value_level = ValueLevel.NO_VALUE
            is_exploitable = False
            
            reasons.append("No bookmaker odds available")
            reasons.append(f"Statistical confidence: {statistical_confidence:.1f}%")
            reasons.append("Mode: STATISTICAL_SIGNAL_ONLY")
        
        # Calculate priority score
        priority_score = self._calculate_priority_score(
            adjusted_confidence=adjusted_confidence,
            value_gap=value_gap,
            variance_penalty=variance_penalty,
            quality_penalty=quality_penalty
        )
        
        return ValueAssessment(
            statistical_confidence=statistical_confidence,
            historical_hit_rate=historical_hit_rate,
            bookmaker_implied_probability=bookmaker_implied_probability,
            offered_odd=bookmaker_odd,
            value_gap=value_gap,
            fair_odd_estimate=fair_odd_estimate,
            value_level=value_level.value,
            is_exploitable=is_exploitable,
            has_odds=has_odds,
            variance_penalty=variance_penalty,
            sample_penalty=sample_penalty,
            quality_penalty=quality_penalty,
            adjusted_confidence=adjusted_confidence,
            priority_score=priority_score,
            reasons=reasons
        )
    
    def _calculate_variance_penalty(self, variance_score: float) -> float:
        """
        Calculate penalty based on variance
        
        Args:
            variance_score: 0-1 (higher = more stable)
            
        Returns:
            Penalty multiplier (0-1)
        """
        # High variance = lower confidence
        if variance_score >= 0.8:
            return 1.0  # No penalty
        elif variance_score >= 0.6:
            return 0.9
        elif variance_score >= 0.4:
            return 0.8
        else:
            return 0.7
    
    def _calculate_sample_penalty(self, sample_size: int) -> float:
        """
        Calculate penalty based on sample size
        
        Args:
            sample_size: Number of matches
            
        Returns:
            Penalty multiplier (0-1)
        """
        if sample_size >= 15:
            return 1.0  # No penalty
        elif sample_size >= 10:
            return 0.95
        elif sample_size >= 7:
            return 0.9
        elif sample_size >= 5:
            return 0.85
        else:
            return 0.75  # Significant penalty
    
    def _calculate_quality_penalty(self, data_quality: float) -> float:
        """
        Calculate penalty based on data quality
        
        Args:
            data_quality: 0-1
            
        Returns:
            Penalty multiplier (0-1)
        """
        if data_quality >= 0.9:
            return 1.0
        elif data_quality >= 0.8:
            return 0.95
        elif data_quality >= 0.7:
            return 0.9
        else:
            return 0.85
    
    def _determine_value_level(
        self,
        value_gap: float,
        variance_penalty: float,
        sample_penalty: float
    ) -> ValueLevel:
        """
        Determine value level based on gap and quality
        
        Args:
            value_gap: Percentage gap
            variance_penalty: Variance quality
            sample_penalty: Sample quality
            
        Returns:
            ValueLevel
        """
        # Adjust thresholds based on quality
        quality_multiplier = (variance_penalty + sample_penalty) / 2
        
        # Require higher gap if quality is poor
        if quality_multiplier < 0.8:
            # Stricter thresholds
            if value_gap > 50:
                return ValueLevel.EXTREME_VALUE
            elif value_gap > 35:
                return ValueLevel.HIGH_VALUE
            elif value_gap > 20:
                return ValueLevel.MEDIUM_VALUE
            elif value_gap > 10:
                return ValueLevel.LOW_VALUE
            else:
                return ValueLevel.NO_VALUE
        else:
            # Normal thresholds
            if value_gap > 40:
                return ValueLevel.EXTREME_VALUE
            elif value_gap > 25:
                return ValueLevel.HIGH_VALUE
            elif value_gap > 15:
                return ValueLevel.MEDIUM_VALUE
            elif value_gap > 5:
                return ValueLevel.LOW_VALUE
            else:
                return ValueLevel.NO_VALUE
    
    def _calculate_priority_score(
        self,
        adjusted_confidence: float,
        value_gap: Optional[float],
        variance_penalty: float,
        quality_penalty: float
    ) -> float:
        """
        Calculate final priority score for ranking
        
        Args:
            adjusted_confidence: Confidence after penalties
            value_gap: Value gap (None if no odds)
            variance_penalty: Variance quality
            quality_penalty: Data quality
            
        Returns:
            Priority score (0-100+)
        """
        score = adjusted_confidence
        
        # Add value gap bonus if available
        if value_gap is not None and value_gap > 0:
            score += value_gap * 0.5  # 50% weight on value gap
        
        # Add stability bonus
        score += variance_penalty * 10
        
        # Add quality bonus
        score += quality_penalty * 10
        
        # Risk penalty (inverse of variance)
        risk_score = (1 - variance_penalty) * 10
        score -= risk_score
        
        return max(0, score)
