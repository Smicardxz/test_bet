"""
Inefficiency Detector
Core engine for detecting bookmaker pricing inefficiencies

Compares bookmaker lines with historical reality
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.modes import AnalysisMode
from app.services.anomaly.line_breach_analyzer import LineBreachAnalysis

logger = logging.getLogger(__name__)


class InefficiencyLevel(str, Enum):
    """Inefficiency severity levels"""
    NONE = "NONE"
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    EXTREME = "EXTREME"


class Confidence(str, Enum):
    """Confidence levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendedAction(str, Enum):
    """Recommended actions"""
    IGNORE = "IGNORE"
    WATCH = "WATCH"
    COMPARE_ODDS = "COMPARE_ODDS"
    VALIDATE = "VALIDATE"


@dataclass
class InefficiencyResult:
    """Result of inefficiency detection"""
    mode: str
    
    # Match context
    match: Dict[str, Any]
    market: Dict[str, Any]
    
    # Bookmaker (optional)
    bookmaker: Optional[Dict[str, Any]]
    
    # Historical context
    historical_context: Dict[str, Any]
    line_breach: Optional[Dict[str, Any]]
    
    # Probabilities
    bookmaker_probability: float  # 0-100
    historical_probability: float  # 0-100
    
    # Scores
    divergence_score: float  # 0-100
    edge_score: float  # 0-100
    risk_score: float  # 0-100
    
    # Assessment
    confidence: str
    inefficiency_level: str
    
    # Explanation
    why: List[str]
    risk_factors: List[str]
    recommended_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "mode": self.mode,
            "match": self.match,
            "market": self.market,
            "bookmaker": self.bookmaker,
            "historical_context": self.historical_context,
            "line_breach": self.line_breach,
            "bookmaker_probability": self.bookmaker_probability,
            "historical_probability": self.historical_probability,
            "divergence_score": self.divergence_score,
            "edge_score": self.edge_score,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "inefficiency_level": self.inefficiency_level,
            "why": self.why,
            "risk_factors": self.risk_factors,
            "recommended_action": self.recommended_action
        }


class InefficiencyDetector:
    """
    Detects bookmaker pricing inefficiencies
    
    Compares bookmaker lines with historical reality to find mispricing
    """
    
    def __init__(self):
        """Initialize detector"""
        logger.info("InefficiencyDetector initialized")
    
    def detect(
        self,
        match: Dict[str, Any],
        market_type: str,
        bookmaker_line: Optional[float] = None,
        odd: Optional[float] = None,
        bookmaker: Optional[str] = None,
        historical_stats: Optional[Dict[str, Any]] = None,
        line_breach_analysis: Optional[LineBreachAnalysis] = None,
        team_profiles: Optional[Dict[str, Any]] = None,
        league_profile: Optional[Dict[str, Any]] = None,
        data_quality_score: float = 0.5
    ) -> InefficiencyResult:
        """
        Detect inefficiency
        
        Args:
            match: Match information
            market_type: Market type (e.g., "HT Under", "FT Under")
            bookmaker_line: Bookmaker line (e.g., 2.5)
            odd: Bookmaker odd (e.g., 1.85)
            bookmaker: Bookmaker name
            historical_stats: Historical statistics
            line_breach_analysis: Line breach analysis for this line
            team_profiles: Team profiles
            league_profile: League profile
            data_quality_score: Data quality (0-1)
            
        Returns:
            InefficiencyResult
        """
        
        # If no odds, return statistical signal mode
        if bookmaker_line is None or odd is None:
            return self._statistical_signal_mode(
                match=match,
                market_type=market_type,
                historical_stats=historical_stats,
                line_breach_analysis=line_breach_analysis,
                data_quality_score=data_quality_score
            )
        
        # Inefficiency detection mode
        return self._inefficiency_detection_mode(
            match=match,
            market_type=market_type,
            bookmaker_line=bookmaker_line,
            odd=odd,
            bookmaker=bookmaker,
            historical_stats=historical_stats,
            line_breach_analysis=line_breach_analysis,
            team_profiles=team_profiles,
            league_profile=league_profile,
            data_quality_score=data_quality_score
        )
    
    def _statistical_signal_mode(
        self,
        match: Dict[str, Any],
        market_type: str,
        historical_stats: Optional[Dict[str, Any]],
        line_breach_analysis: Optional[LineBreachAnalysis],
        data_quality_score: float
    ) -> InefficiencyResult:
        """Statistical signal mode (no odds)"""
        
        # Extract historical data
        if not historical_stats:
            historical_stats = {}
        
        max_goals = historical_stats.get("max_goals", 0)
        avg_goals = historical_stats.get("avg_goals", 0)
        variance = historical_stats.get("variance", 0)
        sample_size = historical_stats.get("sample_size", 0)
        
        # Historical probability (based on patterns)
        if line_breach_analysis:
            historical_prob = line_breach_analysis.hit_rate * 100
        else:
            historical_prob = 50.0
        
        # Build context
        historical_context = {
            "max_goals": max_goals,
            "avg_goals": avg_goals,
            "variance": variance,
            "sample_size": sample_size,
            "data_quality": data_quality_score
        }
        
        # Reasons
        why = ["Statistical signal mode - odds not available"]
        if historical_prob > 80:
            why.append(f"Strong historical pattern detected ({historical_prob:.0f}% hit rate)")
        
        return InefficiencyResult(
            mode=AnalysisMode.STATISTICAL_SIGNAL.value,
            match=match,
            market={"type": market_type, "line": None},
            bookmaker=None,
            historical_context=historical_context,
            line_breach=None,
            bookmaker_probability=0,
            historical_probability=historical_prob,
            divergence_score=0,
            edge_score=0,
            risk_score=0,
            confidence=Confidence.MEDIUM.value if sample_size >= 10 else Confidence.LOW.value,
            inefficiency_level=InefficiencyLevel.NONE.value,
            why=why,
            risk_factors=[],
            recommended_action=RecommendedAction.WATCH.value
        )
    
    def _inefficiency_detection_mode(
        self,
        match: Dict[str, Any],
        market_type: str,
        bookmaker_line: float,
        odd: float,
        bookmaker: Optional[str],
        historical_stats: Optional[Dict[str, Any]],
        line_breach_analysis: Optional[LineBreachAnalysis],
        team_profiles: Optional[Dict[str, Any]],
        league_profile: Optional[Dict[str, Any]],
        data_quality_score: float
    ) -> InefficiencyResult:
        """Inefficiency detection mode (with odds)"""
        
        # Extract historical data
        if not historical_stats:
            historical_stats = {}
        
        max_goals = historical_stats.get("max_goals", 0)
        avg_goals = historical_stats.get("avg_goals", 0)
        variance = historical_stats.get("variance", 0)
        sample_size = historical_stats.get("sample_size", 0)
        
        # Bookmaker implied probability
        bookmaker_prob = self._odds_to_probability(odd)
        
        # Historical probability
        if line_breach_analysis:
            historical_prob = line_breach_analysis.hit_rate * 100
        else:
            # Estimate based on line vs average
            if "under" in market_type.lower():
                if bookmaker_line > avg_goals:
                    historical_prob = 70.0
                else:
                    historical_prob = 30.0
            else:
                historical_prob = 50.0
        
        # Calculate divergence score
        divergence_score = self._calculate_divergence(
            bookmaker_line=bookmaker_line,
            max_goals=max_goals,
            avg_goals=avg_goals,
            historical_prob=historical_prob,
            bookmaker_prob=bookmaker_prob
        )
        
        # Calculate edge score
        edge_score = self._calculate_edge(
            historical_prob=historical_prob,
            bookmaker_prob=bookmaker_prob
        )
        
        # Calculate risk score
        risk_score = self._calculate_risk(
            sample_size=sample_size,
            variance=variance,
            data_quality_score=data_quality_score
        )
        
        # Determine confidence
        confidence = self._determine_confidence(
            historical_prob=historical_prob,
            variance=variance,
            sample_size=sample_size,
            data_quality_score=data_quality_score
        )
        
        # Determine inefficiency level
        inefficiency_level = self._determine_inefficiency_level(
            divergence_score=divergence_score,
            edge_score=edge_score,
            confidence=confidence
        )
        
        # Build explanations
        why = self._build_why(
            market_type=market_type,
            bookmaker_line=bookmaker_line,
            max_goals=max_goals,
            avg_goals=avg_goals,
            historical_prob=historical_prob,
            bookmaker_prob=bookmaker_prob,
            divergence_score=divergence_score
        )
        
        risk_factors = self._build_risk_factors(
            sample_size=sample_size,
            variance=variance,
            data_quality_score=data_quality_score
        )
        
        # Recommended action
        recommended_action = self._determine_action(
            inefficiency_level=inefficiency_level,
            confidence=confidence,
            risk_score=risk_score
        )
        
        # Build result
        return InefficiencyResult(
            mode=AnalysisMode.INEFFICIENCY_DETECTION.value,
            match=match,
            market={"type": market_type, "line": bookmaker_line},
            bookmaker={"name": bookmaker or "Unknown", "odd": odd},
            historical_context={
                "max_goals": max_goals,
                "avg_goals": avg_goals,
                "variance": variance,
                "sample_size": sample_size,
                "data_quality": data_quality_score
            },
            line_breach={
                "hit_rate": line_breach_analysis.hit_rate if line_breach_analysis else 0,
                "avg_distance": line_breach_analysis.avg_distance_to_line if line_breach_analysis else 0,
                "consistency": line_breach_analysis.consistency if line_breach_analysis else 0
            } if line_breach_analysis else None,
            bookmaker_probability=bookmaker_prob,
            historical_probability=historical_prob,
            divergence_score=divergence_score,
            edge_score=edge_score,
            risk_score=risk_score,
            confidence=confidence.value,
            inefficiency_level=inefficiency_level.value,
            why=why,
            risk_factors=risk_factors,
            recommended_action=recommended_action.value
        )
    
    def _odds_to_probability(self, odd: float) -> float:
        """Convert decimal odd to probability percentage"""
        if odd <= 1.0:
            return 0.0
        return (1.0 / odd) * 100
    
    def _calculate_divergence(
        self,
        bookmaker_line: float,
        max_goals: int,
        avg_goals: float,
        historical_prob: float,
        bookmaker_prob: float
    ) -> float:
        """Calculate divergence score (0-100)"""
        
        # Factor 1: Line gap (line vs historical max)
        line_gap = bookmaker_line - max_goals
        line_gap_score = min(100, max(0, line_gap * 15))  # 15 points per goal gap
        
        # Factor 2: Probability divergence
        prob_divergence = abs(historical_prob - bookmaker_prob)
        prob_score = min(100, prob_divergence * 2)  # 2 points per % difference
        
        # Factor 3: Line vs average
        avg_gap = bookmaker_line - avg_goals
        avg_score = min(100, max(0, avg_gap * 10))  # 10 points per goal above average
        
        # Weighted average
        divergence = (line_gap_score * 0.5) + (prob_score * 0.3) + (avg_score * 0.2)
        
        return min(100, max(0, divergence))
    
    def _calculate_edge(self, historical_prob: float, bookmaker_prob: float) -> float:
        """Calculate edge score (0-100)"""
        
        # Edge is when historical probability is higher than bookmaker probability
        edge = historical_prob - bookmaker_prob
        
        # Convert to 0-100 scale
        edge_score = min(100, max(0, edge * 2))
        
        return edge_score
    
    def _calculate_risk(
        self,
        sample_size: int,
        variance: float,
        data_quality_score: float
    ) -> float:
        """Calculate risk score (0-100, higher = more risk)"""
        
        # Factor 1: Sample size risk
        if sample_size >= 15:
            sample_risk = 0
        elif sample_size >= 10:
            sample_risk = 20
        elif sample_size >= 5:
            sample_risk = 40
        else:
            sample_risk = 70
        
        # Factor 2: Variance risk
        if variance < 1.0:
            variance_risk = 0
        elif variance < 2.0:
            variance_risk = 20
        elif variance < 3.0:
            variance_risk = 40
        else:
            variance_risk = 60
        
        # Factor 3: Data quality risk
        quality_risk = (1 - data_quality_score) * 50
        
        # Weighted average
        risk = (sample_risk * 0.4) + (variance_risk * 0.3) + (quality_risk * 0.3)
        
        return min(100, max(0, risk))
    
    def _determine_confidence(
        self,
        historical_prob: float,
        variance: float,
        sample_size: int,
        data_quality_score: float
    ) -> Confidence:
        """Determine confidence level"""
        
        # High confidence requires:
        # - High historical probability (>85%)
        # - Low variance (<2.0)
        # - Good sample size (>=10)
        # - Good data quality (>0.7)
        
        if (historical_prob >= 85 and
            variance < 2.0 and
            sample_size >= 10 and
            data_quality_score > 0.7):
            return Confidence.HIGH
        
        # Medium confidence
        elif (historical_prob >= 70 and
              variance < 3.0 and
              sample_size >= 5 and
              data_quality_score > 0.5):
            return Confidence.MEDIUM
        
        # Low confidence
        else:
            return Confidence.LOW
    
    def _determine_inefficiency_level(
        self,
        divergence_score: float,
        edge_score: float,
        confidence: Confidence
    ) -> InefficiencyLevel:
        """Determine inefficiency level"""
        
        # Extreme: Very high divergence + edge + high confidence
        if divergence_score >= 80 and edge_score >= 40 and confidence == Confidence.HIGH:
            return InefficiencyLevel.EXTREME
        
        # Strong: High divergence + edge OR very high edge alone
        elif (divergence_score >= 60 and edge_score >= 30) or (edge_score >= 70 and confidence == Confidence.HIGH):
            return InefficiencyLevel.STRONG
        
        # Medium: Moderate divergence OR high edge
        elif (divergence_score >= 40 and edge_score >= 20) or (edge_score >= 50):
            return InefficiencyLevel.MEDIUM
        
        # Weak: Some divergence or edge
        elif divergence_score >= 20 or edge_score >= 10:
            return InefficiencyLevel.WEAK
        
        # None
        else:
            return InefficiencyLevel.NONE
    
    def _build_why(
        self,
        market_type: str,
        bookmaker_line: float,
        max_goals: int,
        avg_goals: float,
        historical_prob: float,
        bookmaker_prob: float,
        divergence_score: float
    ) -> List[str]:
        """Build explanation list"""
        
        why = []
        
        # Line gap
        line_gap = bookmaker_line - max_goals
        if line_gap > 5:
            why.append(f"Bookmaker line ({bookmaker_line}) is {line_gap:.1f} goals above historical max ({max_goals})")
        elif line_gap > 2:
            why.append(f"Bookmaker line is {line_gap:.1f} goals above historical max")
        
        # Probability gap
        prob_gap = historical_prob - bookmaker_prob
        if prob_gap > 30:
            why.append(f"Historical probability ({historical_prob:.0f}%) significantly higher than bookmaker ({bookmaker_prob:.0f}%)")
        elif prob_gap > 15:
            why.append(f"Historical probability higher than bookmaker implied probability")
        
        # Average gap
        avg_gap = bookmaker_line - avg_goals
        if avg_gap > 3:
            why.append(f"Line is {avg_gap:.1f} goals above historical average ({avg_goals:.1f})")
        
        # Overall assessment
        if divergence_score >= 80:
            why.append("Extreme divergence detected - potential significant mispricing")
        elif divergence_score >= 60:
            why.append("Strong divergence detected - worth investigating")
        
        if not why:
            why.append("Line appears consistent with historical data")
        
        return why
    
    def _build_risk_factors(
        self,
        sample_size: int,
        variance: float,
        data_quality_score: float
    ) -> List[str]:
        """Build risk factors list"""
        
        risks = []
        
        if sample_size < 5:
            risks.append(f"Very small sample size ({sample_size} matches)")
        elif sample_size < 10:
            risks.append(f"Small sample size ({sample_size} matches)")
        
        if variance > 3.0:
            risks.append(f"High variance ({variance:.2f}) - inconsistent scoring")
        elif variance > 2.0:
            risks.append(f"Moderate variance ({variance:.2f})")
        
        if data_quality_score < 0.5:
            risks.append(f"Low data quality ({data_quality_score:.2f})")
        elif data_quality_score < 0.7:
            risks.append(f"Moderate data quality ({data_quality_score:.2f})")
        
        if not risks:
            risks.append("No significant risk factors identified")
        
        return risks
    
    def _determine_action(
        self,
        inefficiency_level: InefficiencyLevel,
        confidence: Confidence,
        risk_score: float
    ) -> RecommendedAction:
        """Determine recommended action"""
        
        # Extreme inefficiency + high confidence + low risk
        if (inefficiency_level == InefficiencyLevel.EXTREME and
            confidence == Confidence.HIGH and
            risk_score < 30):
            return RecommendedAction.VALIDATE
        
        # Strong inefficiency
        elif inefficiency_level in [InefficiencyLevel.STRONG, InefficiencyLevel.EXTREME]:
            return RecommendedAction.COMPARE_ODDS
        
        # Medium inefficiency
        elif inefficiency_level == InefficiencyLevel.MEDIUM:
            return RecommendedAction.WATCH
        
        # Weak or none
        else:
            return RecommendedAction.IGNORE
