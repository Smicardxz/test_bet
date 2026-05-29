"""
Scoring Calibration System
Analyze, visualize and calibrate anomaly scoring weights
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import logging

from app.services.stats import TeamStats
from app.services.anomaly.anomaly_engine import AnomalyEngine, AnomalyResult


logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """Current scoring weights"""
    discrepancy: float = 0.40
    variance_safety: float = 0.25
    historical_hit_rate: float = 0.20
    stability: float = 0.15
    
    def total(self) -> float:
        """Get total weight (should be 1.0)"""
        return (
            self.discrepancy +
            self.variance_safety +
            self.historical_hit_rate +
            self.stability
        )
    
    def normalize(self):
        """Normalize weights to sum to 1.0"""
        total = self.total()
        if total > 0:
            self.discrepancy /= total
            self.variance_safety /= total
            self.historical_hit_rate /= total
            self.stability /= total


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of anomaly score calculation"""
    
    # Component scores (0-100)
    discrepancy_score: float
    variance_safety_score: float
    historical_hit_rate: float
    stability_score: float
    
    # Weights applied
    weights: ScoringWeights
    
    # Weighted contributions
    discrepancy_contribution: float = 0.0
    variance_contribution: float = 0.0
    historical_contribution: float = 0.0
    stability_contribution: float = 0.0
    
    # Final score
    final_score: float = 0.0
    
    # Probabilities
    bookmaker_probability: float = 0.0
    model_probability: float = 0.0
    probability_gap: float = 0.0
    
    # Data quality
    sample_size: int = 0
    data_quality: float = 0.0
    
    # Metadata
    market_type: str = ""
    line: Optional[float] = None
    
    def __post_init__(self):
        """Calculate contributions and final score"""
        self.discrepancy_contribution = self.discrepancy_score * self.weights.discrepancy
        self.variance_contribution = self.variance_safety_score * self.weights.variance_safety
        self.historical_contribution = self.historical_hit_rate * self.weights.historical_hit_rate
        self.stability_contribution = self.stability_score * self.weights.stability
        
        self.final_score = (
            self.discrepancy_contribution +
            self.variance_contribution +
            self.historical_contribution +
            self.stability_contribution
        )
    
    def get_component_impact(self) -> Dict[str, float]:
        """Get impact percentage of each component"""
        if self.final_score == 0:
            return {
                "discrepancy": 0.0,
                "variance_safety": 0.0,
                "historical": 0.0,
                "stability": 0.0
            }
        
        return {
            "discrepancy": (self.discrepancy_contribution / self.final_score) * 100,
            "variance_safety": (self.variance_contribution / self.final_score) * 100,
            "historical": (self.historical_contribution / self.final_score) * 100,
            "stability": (self.stability_contribution / self.final_score) * 100
        }
    
    def get_explanation(self) -> str:
        """Get detailed explanation of score"""
        lines = []
        lines.append(f"Market: {self.market_type}")
        if self.line:
            lines.append(f"Line: {self.line}")
        lines.append("")
        
        lines.append("PROBABILITIES:")
        lines.append(f"  Bookmaker: {self.bookmaker_probability:.1%}")
        lines.append(f"  Model: {self.model_probability:.1%}")
        lines.append(f"  Gap: {self.probability_gap:.1%}")
        lines.append("")
        
        lines.append("COMPONENT SCORES:")
        lines.append(f"  Discrepancy: {self.discrepancy_score:.1f}/100")
        lines.append(f"  Variance Safety: {self.variance_safety_score:.1f}/100")
        lines.append(f"  Historical Hit: {self.historical_hit_rate:.1f}/100")
        lines.append(f"  Stability: {self.stability_score:.1f}/100")
        lines.append("")
        
        lines.append("WEIGHTED CONTRIBUTIONS:")
        lines.append(f"  Discrepancy: {self.discrepancy_contribution:.2f} (weight: {self.weights.discrepancy:.0%})")
        lines.append(f"  Variance Safety: {self.variance_contribution:.2f} (weight: {self.weights.variance_safety:.0%})")
        lines.append(f"  Historical: {self.historical_contribution:.2f} (weight: {self.weights.historical_hit_rate:.0%})")
        lines.append(f"  Stability: {self.stability_contribution:.2f} (weight: {self.weights.stability:.0%})")
        lines.append("")
        
        impact = self.get_component_impact()
        lines.append("COMPONENT IMPACT:")
        lines.append(f"  Discrepancy: {impact['discrepancy']:.1f}%")
        lines.append(f"  Variance Safety: {impact['variance_safety']:.1f}%")
        lines.append(f"  Historical: {impact['historical']:.1f}%")
        lines.append(f"  Stability: {impact['stability']:.1f}%")
        lines.append("")
        
        lines.append(f"FINAL SCORE: {self.final_score:.2f}/100")
        lines.append("")
        
        lines.append("DATA QUALITY:")
        lines.append(f"  Sample Size: {self.sample_size}")
        lines.append(f"  Quality Score: {self.data_quality:.2f}")
        
        return "\n".join(lines)


class ScoringCalibrator:
    """
    Scoring calibration system
    
    Analyzes and visualizes scoring calculations
    """
    
    def __init__(self, engine: Optional[AnomalyEngine] = None):
        """Initialize calibrator"""
        self.engine = engine or AnomalyEngine()
        self.current_weights = self._extract_current_weights()
    
    def _extract_current_weights(self) -> ScoringWeights:
        """Extract current weights from engine"""
        # Default weights from AnomalyEngine._calculate_anomaly_score
        return ScoringWeights(
            discrepancy=0.40,
            variance_safety=0.25,
            historical_hit_rate=0.20,
            stability=0.15
        )
    
    def analyze_score_calculation(
        self,
        match_id: int,
        market_type: str,
        bookmaker_odds: float,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float] = None,
        debug: bool = True
    ) -> Tuple[AnomalyResult, ScoreBreakdown]:
        """
        Analyze score calculation with detailed breakdown
        
        Args:
            match_id: Match ID
            market_type: Market type
            bookmaker_odds: Bookmaker odds
            home_stats: Home team stats
            away_stats: Away team stats
            line: Line value
            debug: Enable debug logging
            
        Returns:
            Tuple of (AnomalyResult, ScoreBreakdown)
        """
        
        if debug:
            logger.info("="*80)
            logger.info("SCORE CALCULATION ANALYSIS")
            logger.info("="*80)
        
        # Run anomaly detection
        result = self.engine.analyze_market(
            match_id=match_id,
            market_type=market_type,
            bookmaker_odds=bookmaker_odds,
            home_stats=home_stats,
            away_stats=away_stats,
            line=line
        )
        
        # Create breakdown
        breakdown = ScoreBreakdown(
            discrepancy_score=result.discrepancy_score,
            variance_safety_score=result.variance_safety_score,
            historical_hit_rate=result.historical_hit_rate,
            stability_score=result.stability_score,
            weights=self.current_weights,
            bookmaker_probability=result.normalized_bookmaker_probability,
            model_probability=result.model_probability,
            probability_gap=abs(result.normalized_bookmaker_probability - result.model_probability),
            sample_size=result.sample_size,
            data_quality=result.data_quality,
            market_type=market_type,
            line=line
        )
        
        if debug:
            logger.info(breakdown.get_explanation())
        
        return result, breakdown
    
    def detect_inconsistent_scores(
        self,
        results: List[Tuple[AnomalyResult, ScoreBreakdown]]
    ) -> List[Dict]:
        """
        Detect inconsistent or suspicious scores
        
        Args:
            results: List of (AnomalyResult, ScoreBreakdown) tuples
            
        Returns:
            List of inconsistencies found
        """
        inconsistencies = []
        
        for i, (result, breakdown) in enumerate(results):
            issues = []
            
            # Check 1: High score but low discrepancy
            if result.anomaly_score >= 70 and breakdown.discrepancy_score < 50:
                issues.append({
                    "type": "high_score_low_discrepancy",
                    "description": "High anomaly score despite low discrepancy",
                    "anomaly_score": result.anomaly_score,
                    "discrepancy_score": breakdown.discrepancy_score
                })
            
            # Check 2: High discrepancy but low final score
            if breakdown.discrepancy_score >= 80 and result.anomaly_score < 60:
                issues.append({
                    "type": "high_discrepancy_low_score",
                    "description": "High discrepancy but low final score",
                    "discrepancy_score": breakdown.discrepancy_score,
                    "anomaly_score": result.anomaly_score
                })
            
            # Check 3: Poor data quality but high confidence
            if breakdown.data_quality < 0.6 and result.confidence_score > 0.7:
                issues.append({
                    "type": "poor_quality_high_confidence",
                    "description": "Poor data quality but high confidence",
                    "data_quality": breakdown.data_quality,
                    "confidence_score": result.confidence_score
                })
            
            # Check 4: Small sample but high score
            if breakdown.sample_size < 8 and result.anomaly_score >= 70:
                issues.append({
                    "type": "small_sample_high_score",
                    "description": "Small sample size but high anomaly score",
                    "sample_size": breakdown.sample_size,
                    "anomaly_score": result.anomaly_score
                })
            
            # Check 5: Extreme probability gap but low score
            if breakdown.probability_gap >= 0.30 and result.anomaly_score < 70:
                issues.append({
                    "type": "extreme_gap_low_score",
                    "description": "Extreme probability gap but low score",
                    "probability_gap": breakdown.probability_gap,
                    "anomaly_score": result.anomaly_score
                })
            
            if issues:
                inconsistencies.append({
                    "index": i,
                    "market_type": breakdown.market_type,
                    "anomaly_score": result.anomaly_score,
                    "issues": issues
                })
        
        return inconsistencies
    
    def recommend_calibration(
        self,
        results: List[Tuple[AnomalyResult, ScoreBreakdown]]
    ) -> Dict:
        """
        Analyze results and recommend calibration adjustments
        
        Args:
            results: List of (AnomalyResult, ScoreBreakdown) tuples
            
        Returns:
            Calibration recommendations
        """
        if not results:
            return {"error": "No results to analyze"}
        
        # Analyze component distributions
        discrepancy_scores = [b.discrepancy_score for _, b in results]
        variance_scores = [b.variance_safety_score for _, b in results]
        historical_scores = [b.historical_hit_rate for _, b in results]
        stability_scores = [b.stability_score for _, b in results]
        
        avg_discrepancy = sum(discrepancy_scores) / len(discrepancy_scores)
        avg_variance = sum(variance_scores) / len(variance_scores)
        avg_historical = sum(historical_scores) / len(historical_scores)
        avg_stability = sum(stability_scores) / len(stability_scores)
        
        # Analyze impact
        impacts = [b.get_component_impact() for _, b in results]
        avg_impact = {
            "discrepancy": sum(i["discrepancy"] for i in impacts) / len(impacts),
            "variance_safety": sum(i["variance_safety"] for i in impacts) / len(impacts),
            "historical": sum(i["historical"] for i in impacts) / len(impacts),
            "stability": sum(i["stability"] for i in impacts) / len(impacts)
        }
        
        recommendations = {
            "current_weights": {
                "discrepancy": self.current_weights.discrepancy,
                "variance_safety": self.current_weights.variance_safety,
                "historical_hit_rate": self.current_weights.historical_hit_rate,
                "stability": self.current_weights.stability
            },
            "average_scores": {
                "discrepancy": round(avg_discrepancy, 2),
                "variance_safety": round(avg_variance, 2),
                "historical": round(avg_historical, 2),
                "stability": round(avg_stability, 2)
            },
            "average_impact": {
                "discrepancy": round(avg_impact["discrepancy"], 1),
                "variance_safety": round(avg_impact["variance_safety"], 1),
                "historical": round(avg_impact["historical"], 1),
                "stability": round(avg_impact["stability"], 1)
            },
            "suggestions": []
        }
        
        # Generate suggestions
        
        # Suggestion 1: Discrepancy dominance
        if avg_impact["discrepancy"] > 60:
            recommendations["suggestions"].append({
                "type": "discrepancy_dominance",
                "description": "Discrepancy dominates scoring (>60% impact)",
                "current_impact": round(avg_impact["discrepancy"], 1),
                "suggestion": "Consider reducing discrepancy weight or increasing other weights"
            })
        
        # Suggestion 2: Low variance impact
        if avg_impact["variance_safety"] < 15:
            recommendations["suggestions"].append({
                "type": "low_variance_impact",
                "description": "Variance safety has low impact (<15%)",
                "current_impact": round(avg_impact["variance_safety"], 1),
                "suggestion": "Consider increasing variance_safety weight if stability is important"
            })
        
        # Suggestion 3: Component imbalance
        max_impact = max(avg_impact.values())
        min_impact = min(avg_impact.values())
        if max_impact / min_impact > 5:
            recommendations["suggestions"].append({
                "type": "component_imbalance",
                "description": "Large imbalance between component impacts",
                "max_impact": round(max_impact, 1),
                "min_impact": round(min_impact, 1),
                "ratio": round(max_impact / min_impact, 2),
                "suggestion": "Consider rebalancing weights for more even contribution"
            })
        
        # Suggestion 4: Low scores overall
        avg_final_score = sum(r.anomaly_score for r, _ in results) / len(results)
        if avg_final_score < 40:
            recommendations["suggestions"].append({
                "type": "low_scores_overall",
                "description": "Average anomaly score is low (<40)",
                "average_score": round(avg_final_score, 2),
                "suggestion": "Scores may be too conservative - consider adjusting thresholds"
            })
        
        # Suggestion 5: High scores overall
        if avg_final_score > 75:
            recommendations["suggestions"].append({
                "type": "high_scores_overall",
                "description": "Average anomaly score is high (>75)",
                "average_score": round(avg_final_score, 2),
                "suggestion": "Scores may be too aggressive - consider tightening criteria"
            })
        
        return recommendations
    
    def visualize_score_distribution(
        self,
        results: List[Tuple[AnomalyResult, ScoreBreakdown]]
    ) -> str:
        """
        Create text visualization of score distribution
        
        Args:
            results: List of (AnomalyResult, ScoreBreakdown) tuples
            
        Returns:
            Text visualization
        """
        if not results:
            return "No results to visualize"
        
        lines = []
        lines.append("="*80)
        lines.append("SCORE DISTRIBUTION ANALYSIS")
        lines.append("="*80)
        lines.append("")
        
        # Final scores distribution
        final_scores = [r.anomaly_score for r, _ in results]
        lines.append("Final Anomaly Scores:")
        lines.append(self._create_histogram(final_scores, 0, 100, 10))
        lines.append("")
        
        # Component scores
        for component, label in [
            ("discrepancy_score", "Discrepancy"),
            ("variance_safety_score", "Variance Safety"),
            ("historical_hit_rate", "Historical Hit Rate"),
            ("stability_score", "Stability")
        ]:
            scores = [getattr(b, component) for _, b in results]
            lines.append(f"{label} Scores:")
            lines.append(self._create_histogram(scores, 0, 100, 10))
            lines.append("")
        
        return "\n".join(lines)
    
    def _create_histogram(
        self,
        values: List[float],
        min_val: float,
        max_val: float,
        bins: int
    ) -> str:
        """Create simple text histogram"""
        bin_size = (max_val - min_val) / bins
        counts = [0] * bins
        
        for val in values:
            bin_idx = min(int((val - min_val) / bin_size), bins - 1)
            if 0 <= bin_idx < bins:
                counts[bin_idx] += 1
        
        max_count = max(counts) if counts else 1
        lines = []
        
        for i, count in enumerate(counts):
            bin_start = min_val + i * bin_size
            bin_end = bin_start + bin_size
            bar_length = int((count / max_count) * 40) if max_count > 0 else 0
            bar = "█" * bar_length
            lines.append(f"  {bin_start:5.1f}-{bin_end:5.1f}: {bar} ({count})")
        
        return "\n".join(lines)
