"""
False Positive Analyzer
Identify and analyze cases where HIGH confidence predictions failed

Goal: Reduce incorrect HIGH confidence anomalies
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging

from app.services.anomaly.scoring_calibration import ScoreBreakdown, ScoringWeights
from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory


logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Type of false positive failure"""
    OVERCONFIDENT_DISCREPANCY = "OVERCONFIDENT_DISCREPANCY"    # Discrepancy overvalued
    MISLEADING_STABILITY = "MISLEADING_STABILITY"                # Stability signal wrong
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"                    # Small sample size
    WRONG_PATTERN = "WRONG_PATTERN"                            # Pattern misapplied
    VARIANCE_BLINDNESS = "VARIANCE_BLINDNESS"                  # High variance ignored
    BOOKMAKER_TRAP = "BOOKMAKER_TRAP"                         # Line was actually correct
    H2H_IGNORED = "H2H_IGNORED"                               # H2H contradicted signal
    FORM_BLINDNESS = "FORM_BLINDNESS"                         # Recent form ignored


@dataclass
class FalsePositiveCase:
    """A single false positive case"""
    match_id: str
    market_type: str
    
    # What was predicted
    predicted_score: float
    predicted_confidence: str
    
    # What actually happened
    actual_outcome: str
    
    # Analysis
    failure_type: FailureType
    failure_explanation: str
    
    # Component analysis
    discrepancy_score: float
    variance_safety_score: float
    historical_hit_rate: float
    stability_score: float
    
    # Signals that misled
    misleading_signals: List[str] = field(default_factory=list)
    
    # Missing signals
    missing_signals: List[str] = field(default_factory=list)
    
    # Risk factors that were ignored
    ignored_risks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "match_id": self.match_id,
            "market_type": self.market_type,
            "predicted_score": self.predicted_score,
            "predicted_confidence": self.predicted_confidence,
            "actual_outcome": self.actual_outcome,
            "failure_type": self.failure_type.value,
            "failure_explanation": self.failure_explanation,
            "misleading_signals": self.misleading_signals,
            "missing_signals": self.missing_signals,
            "ignored_risks": self.ignored_risks
        }


@dataclass
class FalsePositiveAnalysis:
    """Complete false positive analysis"""
    
    # Summary
    total_high_confidence_bets: int = 0
    high_confidence_wins: int = 0
    high_confidence_losses: int = 0
    false_positive_rate: float = 0.0
    
    # Cases
    cases: List[FalsePositiveCase] = field(default_factory=list)
    
    # Breakdown
    failure_type_counts: Dict[str, int] = field(default_factory=dict)
    
    # Component issues
    problematic_components: Dict[str, float] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Protections to add
    suggested_protections: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_high_confidence": self.total_high_confidence_bets,
                "wins": self.high_confidence_wins,
                "losses": self.high_confidence_losses,
                "false_positive_rate": round(self.false_positive_rate, 2)
            },
            "failure_breakdown": self.failure_type_counts,
            "problematic_components": self.problematic_components,
            "cases": [c.to_dict() for c in self.cases[:10]],  # Top 10
            "recommendations": self.recommendations,
            "suggested_protections": self.suggested_protections
        }


class FalsePositiveAnalyzer:
    """
    False Positive Analyzer
    
    Analyzes cases where HIGH confidence predictions failed
    to identify systematic issues and recommend corrections.
    """
    
    def __init__(self):
        """Initialize analyzer"""
        self.min_high_confidence_score = 65.0
    
    def analyze(
        self,
        high_confidence_wins: List[Tuple[AnomalyResult, ScoreBreakdown]],
        high_confidence_losses: List[Tuple[AnomalyResult, ScoreBreakdown]]
    ) -> FalsePositiveAnalysis:
        """
        Analyze false positives
        
        Args:
            high_confidence_wins: Winning HIGH confidence bets
            high_confidence_losses: Losing HIGH confidence bets (false positives)
            
        Returns:
            FalsePositiveAnalysis with findings and recommendations
        """
        
        result = FalsePositiveAnalysis()
        result.total_high_confidence_bets = len(high_confidence_wins) + len(high_confidence_losses)
        result.high_confidence_wins = len(high_confidence_wins)
        result.high_confidence_losses = len(high_confidence_losses)
        
        if result.total_high_confidence_bets > 0:
            result.false_positive_rate = (result.high_confidence_losses / result.total_high_confidence_bets) * 100
        
        logger.info(f"Analyzing {result.total_high_confidence_bets} HIGH confidence bets")
        logger.info(f"Wins: {result.high_confidence_wins}, Losses: {result.high_confidence_losses}")
        logger.info(f"False positive rate: {result.false_positive_rate:.1f}%")
        
        # Analyze each false positive
        for anomaly_result, breakdown in high_confidence_losses:
            case = self._classify_failure(anomaly_result, breakdown)
            result.cases.append(case)
            
            # Count failure types
            ft = case.failure_type.value
            result.failure_type_counts[ft] = result.failure_type_counts.get(ft, 0) + 1
        
        # Identify problematic components
        result.problematic_components = self._identify_problematic_components(high_confidence_losses)
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        # Suggest protections
        result.suggested_protections = self._suggest_protections(result)
        
        return result
    
    def _classify_failure(
        self,
        result: AnomalyResult,
        breakdown: ScoreBreakdown
    ) -> FalsePositiveCase:
        """Classify why this prediction failed"""
        
        case = FalsePositiveCase(
            match_id=str(result.match_id),
            market_type=result.market_type,
            predicted_score=result.anomaly_score,
            predicted_confidence=result.confidence_category.value,
            actual_outcome="LOSS",
            failure_type=FailureType.OVERCONFIDENT_DISCREPANCY,
            failure_explanation="Unknown",
            discrepancy_score=result.discrepancy_score,
            variance_safety_score=result.variance_safety_score,
            historical_hit_rate=result.historical_hit_rate,
            stability_score=result.stability_score
        )
        
        # Analyze misleading signals
        for signal in result.positive_signals:
            case.misleading_signals.append(f"{signal.type}: {signal.description}")
        
        # Analyze ignored risks
        case.ignored_risks = result.risk_factors.copy()
        
        # Classify failure type
        
        # Case 1: Discrepancy was high but wrong direction
        if (result.discrepancy_score > 70 and 
            result.variance_safety_score < 50):
            case.failure_type = FailureType.VARIANCE_BLINDNESS
            case.failure_explanation = (
                f"High discrepancy ({result.discrepancy_score:.0f}) but low variance safety "
                f"({result.variance_safety_score:.0f}). The model detected a gap but variance "
                f"was too high for confidence."
            )
            case.missing_signals.append("Low variance safety should have reduced confidence")
        
        # Case 2: Small sample size
        elif result.sample_size < 10:
            case.failure_type = FailureType.INSUFFICIENT_DATA
            case.failure_explanation = (
                f"Sample size too small ({result.sample_size}). "
                f"High confidence based on insufficient data."
            )
            case.ignored_risks.append(f"Small sample: {result.sample_size}")
        
        # Case 3: Stability was misleading
        elif (result.stability_score > 80 and 
              result.historical_hit_rate < 50):
            case.failure_type = FailureType.MISLEADING_STABILITY
            case.failure_explanation = (
                f"High stability ({result.stability_score:.0f}) but poor historical hit rate "
                f"({result.historical_hit_rate:.0f}). Stability signal was misleading."
            )
            case.misleading_signals.append("Stability score overvalued")
        
        # Case 4: Bookmaker was actually right
        elif result.discrepancy_score < 60:
            case.failure_type = FailureType.BOOKMAKER_TRAP
            case.failure_explanation = (
                f"Discrepancy was moderate ({result.discrepancy_score:.0f}). "
                f"Bookmaker line may have been correct."
            )
            case.missing_signals.append("Low discrepancy should not trigger HIGH confidence")
        
        # Case 5: Historical hit rate was wrong
        elif result.historical_hit_rate < 40:
            case.failure_type = FailureType.WRONG_PATTERN
            case.failure_explanation = (
                f"Historical hit rate low ({result.historical_hit_rate:.0f}). "
                f"Pattern did not apply to this match."
            )
            case.missing_signals.append("Historical pattern mismatch")
        
        # Default: Overconfident discrepancy
        else:
            case.failure_type = FailureType.OVERCONFIDENT_DISCREPANCY
            case.failure_explanation = (
                f"Discrepancy score ({result.discrepancy_score:.0f}) was high but "
                f"the anomaly was not real. Bookmaker may have had insider info "
                f"or the statistical model missed context."
            )
        
        return case
    
    def _identify_problematic_components(
        self,
        losses: List[Tuple[AnomalyResult, ScoreBreakdown]]
    ) -> Dict[str, float]:
        """Identify which components contributed most to false positives"""
        
        if not losses:
            return {}
        
        # Calculate average scores for losses
        avg_disc = statistics.mean(r.discrepancy_score for r, _ in losses)
        avg_var = statistics.mean(r.variance_safety_score for r, _ in losses)
        avg_hist = statistics.mean(r.historical_hit_rate for r, _ in losses)
        avg_stab = statistics.mean(r.stability_score for r, _ in losses)
        
        return {
            "discrepancy": round(avg_disc, 1),
            "variance_safety": round(avg_var, 1),
            "historical_hit": round(avg_hist, 1),
            "stability": round(avg_stab, 1)
        }
    
    def _generate_recommendations(self, analysis: FalsePositiveAnalysis) -> List[str]:
        """Generate recommendations based on analysis"""
        
        recs = []
        
        # Based on false positive rate
        if analysis.false_positive_rate > 40:
            recs.append(
                f"CRITICAL: False positive rate is {analysis.false_positive_rate:.1f}%. "
                f"Consider raising the minimum anomaly score threshold for HIGH confidence."
            )
        elif analysis.false_positive_rate > 25:
            recs.append(
                f"WARNING: False positive rate is {analysis.false_positive_rate:.1f}%. "
                f"Review component weights and signal thresholds."
            )
        
        # Based on failure types
        failure_counts = analysis.failure_type_counts
        
        if failure_counts.get(FailureType.VARIANCE_BLINDNESS.value, 0) > len(analysis.cases) * 0.3:
            recs.append(
                "Many failures due to variance blindness. Consider adding a minimum variance safety "
                "threshold (e.g., >60) for HIGH confidence."
            )
        
        if failure_counts.get(FailureType.INSUFFICIENT_DATA.value, 0) > len(analysis.cases) * 0.2:
            recs.append(
                "Many failures on small samples. Require minimum sample size of 12 for HIGH confidence."
            )
        
        if failure_counts.get(FailureType.MISLEADING_STABILITY.value, 0) > len(analysis.cases) * 0.2:
            recs.append(
                "Stability signal is misleading. Consider reducing stability weight or adding "
                "a consistency check with historical hit rate."
            )
        
        if failure_counts.get(FailureType.BOOKMAKER_TRAP.value, 0) > 0:
            recs.append(
                "Some bookmaker lines were actually correct. Consider checking external "
                "factors (injuries, form) before assigning HIGH confidence."
            )
        
        # Component-specific
        comp = analysis.problematic_components
        if comp.get("discrepancy", 0) > 75:
            recs.append(
                f"Discrepancy scores are high ({comp['discrepancy']:.0f}) even in losses. "
                f"The gap calculation may be overvaluing small differences."
            )
        
        if comp.get("variance_safety", 0) < 50:
            recs.append(
                f"Variance safety is low ({comp['variance_safety']:.0f}) in losses. "
                f"This component needs more weight or a minimum threshold."
            )
        
        return recs
    
    def _suggest_protections(self, analysis: FalsePositiveAnalysis) -> List[str]:
        """Suggest concrete protections to add"""
        
        protections = []
        
        # Sample size protection
        protections.append(
            "PROTECTION: Require sample_size >= 12 for HIGH confidence (currently >= 8)"
        )
        
        # Variance safety minimum
        protections.append(
            "PROTECTION: Require variance_safety_score >= 60 for HIGH confidence"
        )
        
        # Historical hit minimum
        protections.append(
            "PROTECTION: Require historical_hit_rate >= 50 for HIGH confidence"
        )
        
        # Discrepancy sanity check
        protections.append(
            "PROTECTION: If discrepancy > 80 but variance_safety < 50, downgrade confidence"
        )
        
        # Stability check
        protections.append(
            "PROTECTION: If stability > 80 but historical_hit < 40, reduce stability weight by 50%"
        )
        
        # Form check
        protections.append(
            "PROTECTION: Check recent form (last 3 matches) - if contradicts pattern, downgrade"
        )
        
        # H2H check
        protections.append(
            "PROTECTION: If H2H data contradicts anomaly (e.g., H2H is over-prone but under recommended), downgrade"
        )
        
        # Maximum false positive rate
        if analysis.false_positive_rate > 30:
            protections.append(
                f"PROTECTION: Current FP rate {analysis.false_positive_rate:.1f}% exceeds 30%. "
                f"Temporarily raise all thresholds by 10 points until FP rate < 25%."
            )
        
        return protections
    
    def print_report(self, analysis: FalsePositiveAnalysis):
        """Print detailed console report"""
        
        print("\n" + "=" * 80)
        print("FALSE POSITIVE ANALYSIS REPORT")
        print("=" * 80)
        
        # Summary
        print("\n📊 SUMMARY")
        print(f"  Total HIGH confidence bets: {analysis.total_high_confidence_bets}")
        print(f"  Wins: {analysis.high_confidence_wins}")
        print(f"  Losses (False Positives): {analysis.high_confidence_losses}")
        print(f"  False Positive Rate: {analysis.false_positive_rate:.1f}%")
        
        # Problematic components
        print("\n📉 PROBLEMATIC COMPONENTS (in losses)")
        for comp, avg in analysis.problematic_components.items():
            print(f"  {comp:<20}: {avg:.1f}/100 (average)")
        
        # Failure breakdown
        print("\n🔍 FAILURE BREAKDOWN")
        for failure_type, count in sorted(
            analysis.failure_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            pct = (count / len(analysis.cases)) * 100 if analysis.cases else 0
            print(f"  {failure_type:<30}: {count:3d} ({pct:.1f}%)")
        
        # Detailed cases
        print("\n📋 DETAILED CASES (Top 5)")
        for i, case in enumerate(analysis.cases[:5], 1):
            print(f"\n  {i}. {case.match_id} - {case.market_type}")
            print(f"     Score: {case.predicted_score:.1f} | Type: {case.failure_type.value}")
            print(f"     Why: {case.failure_explanation}")
            if case.misleading_signals:
                print(f"     Misleading: {', '.join(case.misleading_signals[:2])}")
            if case.ignored_risks:
                print(f"     Ignored: {', '.join(case.ignored_risks[:2])}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"  {i}. {rec}")
        
        # Protections
        print("\n🛡️  SUGGESTED PROTECTIONS")
        for i, prot in enumerate(analysis.suggested_protections, 1):
            print(f"  {i}. {prot}")
        
        print("\n" + "=" * 80)
    
    def get_adjusted_thresholds(self, analysis: FalsePositiveAnalysis) -> Dict[str, float]:
        """
        Calculate adjusted thresholds based on false positive analysis
        
        Returns:
            Dict of adjusted thresholds
        """
        
        # Base thresholds
        thresholds = {
            "min_sample_size": 8.0,
            "min_variance_safety": 0.0,
            "min_historical_hit": 0.0,
            "min_anomaly_score": 65.0
        }
        
        # Adjust based on false positive rate
        fp_rate = analysis.false_positive_rate
        
        if fp_rate > 40:
            # Critical: raise all thresholds
            thresholds["min_sample_size"] = 15.0
            thresholds["min_variance_safety"] = 65.0
            thresholds["min_historical_hit"] = 55.0
            thresholds["min_anomaly_score"] = 75.0
        elif fp_rate > 25:
            # Warning: moderate raise
            thresholds["min_sample_size"] = 12.0
            thresholds["min_variance_safety"] = 55.0
            thresholds["min_historical_hit"] = 45.0
            thresholds["min_anomaly_score"] = 70.0
        elif fp_rate > 15:
            # Minor adjustment
            thresholds["min_sample_size"] = 10.0
            thresholds["min_variance_safety"] = 50.0
            thresholds["min_anomaly_score"] = 68.0
        
        return thresholds
