"""
Signal Engine - Refactored
Produces statistical signals compatible with InefficiencyDetector

Focus: Detect patterns and prepare for bookmaker comparison
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.anomaly.line_breach_analyzer import LineBreachAnalyzer

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of statistical signals"""
    EXTREME_UNDER = "EXTREME_UNDER"
    HT_UNDER = "HT_UNDER"
    FT_UNDER = "FT_UNDER"
    LOW_VARIANCE = "LOW_VARIANCE"
    SLOW_TEMPO = "SLOW_TEMPO"
    DEFENSIVE_PATTERN = "DEFENSIVE_PATTERN"
    NO_BTTS = "NO_BTTS"
    LEAGUE_LOW_SCORING = "LEAGUE_LOW_SCORING"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    EXTREME = "EXTREME"


@dataclass
class StatisticalSignal:
    """
    Statistical signal ready for bookmaker comparison
    
    This is the output of SignalEngine, designed to feed into InefficiencyDetector
    """
    # Signal identification
    signal_type: str
    signal_strength: str
    confidence: float  # 0-1
    
    # Match context
    match_id: str
    home_team: str
    away_team: str
    competition: str
    country: str
    
    # Market suggestions
    suggested_markets: List[str]  # ["UNDER_4_5", "UNDER_5_5", "HT_UNDER_1_5"]
    compatible_lines: List[float]  # [4.5, 5.5, 6.5]
    expected_goal_range: Tuple[float, float]  # (min, max)
    
    # Historical analysis
    historical_hit_rates_by_line: Dict[float, float]  # {2.5: 0.60, 3.5: 0.87, ...}
    max_observed_goals: int
    avg_goals: float
    
    # Quality metrics
    variance_score: float  # 0-1 (lower is better)
    stability_score: float  # 0-1 (higher is better)
    sample_size: int
    data_quality: float  # 0-1
    
    # Status
    waiting_for_odds: bool
    
    # Explanation
    reasons: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "signal_type": self.signal_type,
            "signal_strength": self.signal_strength,
            "confidence": self.confidence,
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "competition": self.competition,
            "country": self.country,
            "suggested_markets": self.suggested_markets,
            "compatible_lines": self.compatible_lines,
            "expected_goal_range": self.expected_goal_range,
            "historical_hit_rates_by_line": self.historical_hit_rates_by_line,
            "max_observed_goals": self.max_observed_goals,
            "avg_goals": self.avg_goals,
            "variance_score": self.variance_score,
            "stability_score": self.stability_score,
            "sample_size": self.sample_size,
            "data_quality": self.data_quality,
            "waiting_for_odds": self.waiting_for_odds,
            "reasons": self.reasons
        }


class SignalEngine:
    """
    Detects statistical patterns and produces signals
    
    Refactored to be compatible with InefficiencyDetector
    """
    
    def __init__(self):
        """Initialize signal engine"""
        self.line_analyzer = LineBreachAnalyzer()
        logger.info("SignalEngine initialized (refactored)")
    
    def detect_signals(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        ht_goal_history: Optional[List[int]] = None,
        league_profile: Optional[Dict[str, Any]] = None
    ) -> List[StatisticalSignal]:
        """
        Detect all signals for a match
        
        Args:
            match: Match information
            goal_history: Full-time goals history
            ht_goal_history: Half-time goals history (optional)
            league_profile: League profile (optional)
            
        Returns:
            List of StatisticalSignal
        """
        signals = []
        
        if not goal_history or len(goal_history) < 3:
            logger.warning(f"Insufficient data for match {match.get('match_id')}")
            return signals
        
        # Analyze all lines
        line_analyses = self.line_analyzer.analyze_all_lines(goal_history)
        
        # Build historical hit rates
        hit_rates_by_line = {
            line: analysis.hit_rate
            for line, analysis in line_analyses.items()
        }
        
        # Calculate metrics
        max_goals = max(goal_history)
        avg_goals = sum(goal_history) / len(goal_history)
        variance = self._calculate_variance(goal_history)
        variance_score = self._variance_to_score(variance)
        stability_score = self._calculate_stability(goal_history)
        sample_size = len(goal_history)
        data_quality = self._calculate_data_quality(sample_size, variance)
        
        # Detect extreme under profile
        extreme_under = self._detect_extreme_under(
            match=match,
            goal_history=goal_history,
            line_analyses=line_analyses,
            max_goals=max_goals,
            avg_goals=avg_goals,
            hit_rates_by_line=hit_rates_by_line,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality
        )
        if extreme_under:
            signals.append(extreme_under)
        
        # Detect HT under profile
        if ht_goal_history and len(ht_goal_history) >= 5:
            ht_under = self._detect_ht_under(
                match=match,
                ht_goal_history=ht_goal_history,
                variance_score=variance_score,
                stability_score=stability_score,
                data_quality=data_quality
            )
            if ht_under:
                signals.append(ht_under)
        
        # Detect FT under profile
        ft_under = self._detect_ft_under(
            match=match,
            goal_history=goal_history,
            line_analyses=line_analyses,
            avg_goals=avg_goals,
            hit_rates_by_line=hit_rates_by_line,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality
        )
        if ft_under:
            signals.append(ft_under)
        
        # Detect low variance
        if variance_score >= 0.7:  # Low variance
            low_var = self._detect_low_variance(
                match=match,
                goal_history=goal_history,
                variance=variance,
                variance_score=variance_score,
                stability_score=stability_score,
                hit_rates_by_line=hit_rates_by_line,
                sample_size=sample_size,
                data_quality=data_quality
            )
            if low_var:
                signals.append(low_var)
        
        return signals
    
    def _detect_extreme_under(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        line_analyses: Dict[float, Any],
        max_goals: int,
        avg_goals: float,
        hit_rates_by_line: Dict[float, float],
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect extreme under profile"""
        
        # Criteria: Very low scoring with high consistency
        if avg_goals > 5.0:
            return None
        
        # Find lines with 100% hit rate
        perfect_lines = [
            line for line, analysis in line_analyses.items()
            if analysis.hit_rate >= 0.95 and line > max_goals
        ]
        
        if not perfect_lines:
            return None
        
        # Determine strength
        if avg_goals < 3.0 and variance_score >= 0.8:
            strength = SignalStrength.EXTREME
            confidence = 0.9
        elif avg_goals < 4.0 and variance_score >= 0.7:
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.7
        
        # Suggested markets
        suggested_markets = []
        compatible_lines = []
        
        # Suggest lines above max
        for line in [4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 12.5]:
            if line > max_goals:
                suggested_markets.append(f"UNDER_{line}")
                compatible_lines.append(line)
                if len(compatible_lines) >= 5:
                    break
        
        # Reasons
        reasons = [
            f"Extreme under profile detected",
            f"Average goals: {avg_goals:.1f}",
            f"Historical max: {max_goals}",
            f"Low variance: {variance_score:.2f}",
            f"{len(perfect_lines)} lines with 95%+ hit rate"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.EXTREME_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.7, max_goals * 1.2),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max_goals,
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            waiting_for_odds=True,
            reasons=reasons
        )
    
    def _detect_ht_under(
        self,
        match: Dict[str, Any],
        ht_goal_history: List[int],
        variance_score: float,
        stability_score: float,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect HT under profile"""
        
        if len(ht_goal_history) < 5:
            return None
        
        # Analyze HT lines
        ht_line_analyses = self.line_analyzer.analyze_all_lines(ht_goal_history)
        ht_hit_rates = {
            line: analysis.hit_rate
            for line, analysis in ht_line_analyses.items()
        }
        
        max_ht_goals = max(ht_goal_history)
        avg_ht_goals = sum(ht_goal_history) / len(ht_goal_history)
        
        # Check for strong HT under pattern
        under_1_5_rate = ht_hit_rates.get(1.5, 0)
        
        if under_1_5_rate < 0.70:
            return None
        
        # Determine strength
        if under_1_5_rate >= 0.90:
            strength = SignalStrength.EXTREME
            confidence = 0.9
        elif under_1_5_rate >= 0.80:
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.7
        
        # Suggested markets
        suggested_markets = ["HT_UNDER_0_5", "HT_UNDER_1_5"]
        compatible_lines = [0.5, 1.5]
        
        if max_ht_goals <= 1:
            suggested_markets.append("HT_UNDER_2_5")
            compatible_lines.append(2.5)
        
        reasons = [
            f"Strong HT under profile",
            f"HT Under 1.5: {under_1_5_rate*100:.0f}% hit rate",
            f"HT average: {avg_ht_goals:.1f} goals",
            f"HT max: {max_ht_goals} goals"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.HT_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(0, max_ht_goals * 1.2),
            historical_hit_rates_by_line=ht_hit_rates,
            max_observed_goals=max_ht_goals,
            avg_goals=avg_ht_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=len(ht_goal_history),
            data_quality=data_quality,
            waiting_for_odds=True,
            reasons=reasons
        )
    
    def _detect_ft_under(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        line_analyses: Dict[float, Any],
        avg_goals: float,
        hit_rates_by_line: Dict[float, float],
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect FT under profile"""
        
        # Check for moderate under pattern
        under_2_5_rate = hit_rates_by_line.get(2.5, 0)
        under_3_5_rate = hit_rates_by_line.get(3.5, 0)
        
        if under_2_5_rate < 0.60:
            return None
        
        # Determine strength
        if under_2_5_rate >= 0.85:
            strength = SignalStrength.STRONG
            confidence = 0.85
        elif under_2_5_rate >= 0.75:
            strength = SignalStrength.MODERATE
            confidence = 0.75
        else:
            strength = SignalStrength.WEAK
            confidence = 0.65
        
        # Suggested markets
        suggested_markets = ["UNDER_2_5"]
        compatible_lines = [2.5]
        
        if under_3_5_rate >= 0.80:
            suggested_markets.append("UNDER_3_5")
            compatible_lines.append(3.5)
        
        reasons = [
            f"FT under profile detected",
            f"Under 2.5: {under_2_5_rate*100:.0f}% hit rate",
            f"Average: {avg_goals:.1f} goals"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.FT_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.6, avg_goals * 1.4),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max(goal_history),
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            waiting_for_odds=True,
            reasons=reasons
        )
    
    def _detect_low_variance(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        variance: float,
        variance_score: float,
        stability_score: float,
        hit_rates_by_line: Dict[float, float],
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect low variance pattern"""
        
        avg_goals = sum(goal_history) / len(goal_history)
        max_goals = max(goal_history)
        
        # Determine strength
        if variance < 0.5:
            strength = SignalStrength.EXTREME
            confidence = 0.95
        elif variance < 1.0:
            strength = SignalStrength.STRONG
            confidence = 0.85
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.75
        
        # Suggested markets based on average
        suggested_markets = []
        compatible_lines = []
        
        target_line = avg_goals + 1.5
        for line in [2.5, 3.5, 4.5, 5.5]:
            if line >= target_line:
                suggested_markets.append(f"UNDER_{line}")
                compatible_lines.append(line)
                if len(compatible_lines) >= 3:
                    break
        
        reasons = [
            f"Very low variance detected ({variance:.2f})",
            f"Consistent scoring pattern",
            f"Average: {avg_goals:.1f} goals",
            f"Stability score: {stability_score:.2f}"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.LOW_VARIANCE.value,
            signal_strength=strength.value,
            confidence=confidence,
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.8, avg_goals * 1.2),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max_goals,
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            waiting_for_odds=True,
            reasons=reasons
        )
    
    def _calculate_variance(self, values: List[int]) -> float:
        """Calculate variance"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def _variance_to_score(self, variance: float) -> float:
        """Convert variance to 0-1 score (lower variance = higher score)"""
        # Variance < 1.0 = excellent (0.9+)
        # Variance 1.0-2.0 = good (0.7-0.9)
        # Variance 2.0-3.0 = moderate (0.5-0.7)
        # Variance > 3.0 = poor (< 0.5)
        
        if variance < 1.0:
            return 0.9 + (1.0 - variance) * 0.1
        elif variance < 2.0:
            return 0.7 + (2.0 - variance) * 0.2
        elif variance < 3.0:
            return 0.5 + (3.0 - variance) * 0.2
        else:
            return max(0.0, 0.5 - (variance - 3.0) * 0.1)
    
    def _calculate_stability(self, values: List[int]) -> float:
        """Calculate stability score (0-1)"""
        if len(values) < 5:
            return 0.5
        
        # Check consistency in recent vs older matches
        recent = values[-5:]
        older = values[:-5] if len(values) > 5 else values
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg
        
        # Lower difference = higher stability
        diff = abs(recent_avg - older_avg)
        
        if diff < 0.5:
            return 0.95
        elif diff < 1.0:
            return 0.85
        elif diff < 1.5:
            return 0.75
        elif diff < 2.0:
            return 0.65
        else:
            return 0.50
    
    def _calculate_data_quality(self, sample_size: int, variance: float) -> float:
        """Calculate overall data quality (0-1)"""
        
        # Sample size component
        if sample_size >= 15:
            size_score = 1.0
        elif sample_size >= 10:
            size_score = 0.8
        elif sample_size >= 5:
            size_score = 0.6
        else:
            size_score = 0.4
        
        # Variance component
        variance_score = self._variance_to_score(variance)
        
        # Weighted average
        quality = (size_score * 0.6) + (variance_score * 0.4)
        
        return quality
