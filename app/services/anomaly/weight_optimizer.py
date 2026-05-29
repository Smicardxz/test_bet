"""
Weight Optimizer
Analyze backtest results and optimize scoring weights

Simple, interpretable statistical logic - no ML
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import statistics
import logging

from app.services.anomaly.scoring_calibration import ScoringWeights, ScoreBreakdown


logger = logging.getLogger(__name__)


@dataclass
class ComponentAnalysis:
    """Analysis of a scoring component's performance"""
    component_name: str
    weight: float
    
    # Win stats
    win_count: int = 0
    win_avg_score: float = 0.0
    win_avg_contribution: float = 0.0
    
    # Loss stats
    loss_count: int = 0
    loss_avg_score: float = 0.0
    loss_avg_contribution: float = 0.0
    
    # Performance metrics
    predictive_power: float = 0.0  # How well it separates wins from losses
    consistency: float = 0.0       # How stable it is
    
    def win_rate(self) -> float:
        """Calculate win rate for this component"""
        total = self.win_count + self.loss_count
        if total == 0:
            return 0.0
        return (self.win_count / total) * 100


@dataclass
class WeightOptimizationResult:
    """Result of weight optimization"""
    
    # Original weights
    original_weights: ScoringWeights
    
    # New proposed weights
    proposed_weights: ScoringWeights
    
    # Analysis per component
    component_analysis: Dict[str, ComponentAnalysis] = field(default_factory=dict)
    
    # Overall metrics
    win_count: int = 0
    loss_count: int = 0
    total_bets: int = 0
    
    # Before/After comparison
    original_hit_rate: float = 0.0
    estimated_hit_rate: float = 0.0
    
    # Explanation
    explanation: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "original_weights": {
                "discrepancy": self.original_weights.discrepancy,
                "variance_safety": self.original_weights.variance_safety,
                "historical": self.original_weights.historical_hit_rate,
                "stability": self.original_weights.stability
            },
            "proposed_weights": {
                "discrepancy": round(self.proposed_weights.discrepancy, 3),
                "variance_safety": round(self.proposed_weights.variance_safety, 3),
                "historical": round(self.proposed_weights.historical_hit_rate, 3),
                "stability": round(self.proposed_weights.stability, 3)
            },
            "component_analysis": {
                name: {
                    "wins": comp.win_count,
                    "losses": comp.loss_count,
                    "win_rate": round(comp.win_rate(), 2),
                    "predictive_power": round(comp.predictive_power, 2)
                }
                for name, comp in self.component_analysis.items()
            },
            "estimated_hit_rate": round(self.estimated_hit_rate, 2),
            "recommendations": self.recommendations
        }


class WeightOptimizer:
    """
    Weight Optimizer
    
    Analyzes backtest results to optimize scoring weights.
    
    Logic:
    1. For each bet, extract component scores
    2. Compare component values for winning vs losing bets
    3. Components that better separate wins/losses get higher weights
    4. Components that add noise get lower weights
    
    Simple, interpretable, no ML.
    """
    
    def __init__(self, current_weights: Optional[ScoringWeights] = None):
        """Initialize optimizer with current weights"""
        self.current_weights = current_weights or ScoringWeights()
        self.min_weight = 0.05  # Minimum weight for any component
        self.max_weight = 0.70  # Maximum weight for any component
    
    def optimize_from_backtest(
        self,
        winning_breakdowns: List[ScoreBreakdown],
        losing_breakdowns: List[ScoreBreakdown],
        min_sample_size: int = 10
    ) -> WeightOptimizationResult:
        """
        Optimize weights based on backtest results
        
        Args:
            winning_breakdowns: ScoreBreakdown for winning bets
            losing_breakdowns: ScoreBreakdown for losing bets
            min_sample_size: Minimum samples needed per component
            
        Returns:
            WeightOptimizationResult with analysis and recommendations
        """
        
        result = WeightOptimizationResult(
            original_weights=self.current_weights,
            proposed_weights=ScoringWeights(**vars(self.current_weights))
        )
        
        result.win_count = len(winning_breakdowns)
        result.loss_count = len(losing_breakdowns)
        result.total_bets = result.win_count + result.loss_count
        
        logger.info(f"Analyzing {result.total_bets} bets ({result.win_count} wins, {result.loss_count} losses)")
        
        if result.total_bets < min_sample_size:
            result.explanation = f"Insufficient data ({result.total_bets} < {min_sample_size}). Keep current weights."
            return result
        
        # Analyze each component
        components = ["discrepancy", "variance_safety", "historical", "stability"]
        
        for component in components:
            analysis = self._analyze_component(
                component,
                winning_breakdowns,
                losing_breakdowns
            )
            result.component_analysis[component] = analysis
        
        # Calculate predictive power for each component
        self._calculate_predictive_power(result)
        
        # Propose new weights
        result.proposed_weights = self._propose_weights(result)
        
        # Estimate new hit rate
        result.estimated_hit_rate = self._estimate_hit_rate(
            result,
            winning_breakdowns,
            losing_breakdowns
        )
        
        # Generate explanation
        result.explanation = self._generate_explanation(result)
        result.recommendations = self._generate_recommendations(result)
        
        return result
    
    def _analyze_component(
        self,
        component: str,
        wins: List[ScoreBreakdown],
        losses: List[ScoreBreakdown]
    ) -> ComponentAnalysis:
        """Analyze a single component's performance"""
        
        analysis = ComponentAnalysis(
            component_name=component,
            weight=getattr(self.current_weights, component)
        )
        
        # Extract scores for wins
        win_scores = []
        win_contributions = []
        for b in wins:
            score = getattr(b, f"{component}_score")
            contribution = getattr(b, f"{component}_contribution")
            win_scores.append(score)
            win_contributions.append(contribution)
        
        # Extract scores for losses
        loss_scores = []
        loss_contributions = []
        for b in losses:
            score = getattr(b, f"{component}_score")
            contribution = getattr(b, f"{component}_contribution")
            loss_scores.append(score)
            loss_contributions.append(contribution)
        
        analysis.win_count = len(win_scores)
        analysis.loss_count = len(loss_scores)
        
        if win_scores:
            analysis.win_avg_score = statistics.mean(win_scores)
            analysis.win_avg_contribution = statistics.mean(win_contributions)
        
        if loss_scores:
            analysis.loss_avg_score = statistics.mean(loss_scores)
            analysis.loss_avg_contribution = statistics.mean(loss_contributions)
        
        return analysis
    
    def _calculate_predictive_power(self, result: WeightOptimizationResult):
        """
        Calculate how well each component separates wins from losses
        
        Higher = component is more useful for predictions
        """
        
        for name, analysis in result.component_analysis.items():
            if analysis.win_count == 0 or analysis.loss_count == 0:
                analysis.predictive_power = 0.5  # Neutral
                continue
            
            # Calculate separation: difference in means
            win_avg = analysis.win_avg_score
            loss_avg = analysis.loss_avg_score
            
            # Calculate pooled standard deviation
            # For simplicity, use difference in means relative to 100-point scale
            separation = abs(win_avg - loss_avg) / 100.0
            
            # Calculate win rate for this component
            win_rate = analysis.win_rate()
            
            # Predictive power = separation * win_rate / 100
            # Components that show clear separation AND have good win rates
            analysis.predictive_power = separation * (win_rate / 100.0)
            
            # Consistency: lower variance in contributions = more consistent
            analysis.consistency = 1.0  # Simplified
    
    def _propose_weights(self, result: WeightOptimizationResult) -> ScoringWeights:
        """
        Propose new weights based on analysis
        
        Logic:
        - Increase weight for components with high predictive power
        - Decrease weight for components with low predictive power
        - Normalize to sum to 1.0
        """
        
        # Get predictive power for each component
        powers = {
            name: comp.predictive_power
            for name, comp in result.component_analysis.items()
        }
        
        # Handle case where all powers are 0
        total_power = sum(powers.values())
        if total_power == 0:
            # Keep current weights
            return ScoringWeights(**vars(self.current_weights))
        
        # Calculate new weights proportional to predictive power
        # But with smoothing to avoid extreme changes
        
        # Smoothing factor: blend current weight with power-based weight
        alpha = 0.5  # 50% current, 50% data-driven
        
        new_weights = {}
        for name in powers:
            current = getattr(self.current_weights, name)
            power_ratio = powers[name] / total_power if total_power > 0 else 0.25
            
            # Blend
            new_weight = (alpha * current) + ((1 - alpha) * power_ratio)
            new_weights[name] = new_weight
        
        # Create weights object
        proposed = ScoringWeights(
            discrepancy=new_weights.get("discrepancy", 0.25),
            variance_safety=new_weights.get("variance_safety", 0.25),
            historical_hit_rate=new_weights.get("historical", 0.25),
            stability=new_weights.get("stability", 0.25)
        )
        
        # Normalize
        proposed.normalize()
        
        # Enforce min/max bounds
        for attr in ["discrepancy", "variance_safety", "historical_hit_rate", "stability"]:
            val = getattr(proposed, attr)
            val = max(self.min_weight, min(self.max_weight, val))
            setattr(proposed, attr, val)
        
        # Renormalize after bounds
        proposed.normalize()
        
        return proposed
    
    def _estimate_hit_rate(
        self,
        result: WeightOptimizationResult,
        wins: List[ScoreBreakdown],
        losses: List[ScoreBreakdown]
    ) -> float:
        """
        Estimate hit rate with new weights
        
        Simple heuristic: recalculate final scores with new weights
        and count how many would have been detected as anomalies
        """
        
        new_weights = result.proposed_weights
        
        # Recalculate scores for wins
        win_scores_new = []
        for b in wins:
            new_score = (
                b.discrepancy_score * new_weights.discrepancy +
                b.variance_safety_score * new_weights.variance_safety +
                b.historical_hit_rate * new_weights.historical_hit_rate +
                b.stability_score * new_weights.stability
            )
            win_scores_new.append(new_score)
        
        # Recalculate scores for losses
        loss_scores_new = []
        for b in losses:
            new_score = (
                b.discrepancy_score * new_weights.discrepancy +
                b.variance_safety_score * new_weights.variance_safety +
                b.historical_hit_rate * new_weights.historical_hit_rate +
                b.stability_score * new_weights.stability
            )
            loss_scores_new.append(new_score)
        
        # Find threshold that maximizes separation
        # Use midpoint between average win and loss scores
        if win_scores_new and loss_scores_new:
            avg_win = statistics.mean(win_scores_new)
            avg_loss = statistics.mean(loss_scores_new)
            threshold = (avg_win + avg_loss) / 2
            
            # Count how many wins would be detected
            detected_wins = sum(1 for s in win_scores_new if s >= threshold)
            
            # Count how many losses would be detected (false positives)
            detected_losses = sum(1 for s in loss_scores_new if s >= threshold)
            
            total_detected = detected_wins + detected_losses
            if total_detected > 0:
                return (detected_wins / total_detected) * 100
        
        return result.original_hit_rate
    
    def _generate_explanation(self, result: WeightOptimizationResult) -> str:
        """Generate human-readable explanation of optimization"""
        
        lines = []
        lines.append("WEIGHT OPTIMIZATION ANALYSIS")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Sample: {result.total_bets} bets ({result.win_count} wins, {result.loss_count} losses)")
        lines.append("")
        
        # Component analysis
        lines.append("COMPONENT PERFORMANCE:")
        lines.append("-" * 60)
        
        for name, comp in result.component_analysis.items():
            lines.append(f"\n{name.upper()}:")
            lines.append(f"  Current weight: {comp.weight:.0%}")
            lines.append(f"  Win rate: {comp.win_rate():.1f}% ({comp.win_count}W/{comp.loss_count}L)")
            lines.append(f"  Win avg score: {comp.win_avg_score:.1f}")
            lines.append(f"  Loss avg score: {comp.loss_avg_score:.1f}")
            lines.append(f"  Predictive power: {comp.predictive_power:.3f}")
            
            if comp.predictive_power > 0.6:
                lines.append(f"  → STRONG predictor")
            elif comp.predictive_power > 0.3:
                lines.append(f"  → MODERATE predictor")
            else:
                lines.append(f"  → WEAK predictor")
        
        lines.append("")
        lines.append("WEIGHT CHANGES:")
        lines.append("-" * 60)
        
        for attr in ["discrepancy", "variance_safety", "historical_hit_rate", "stability"]:
            old_val = getattr(result.original_weights, attr)
            new_val = getattr(result.proposed_weights, attr)
            change = new_val - old_val
            direction = "↑" if change > 0 else "↓"
            lines.append(f"  {attr:<20} {old_val:.0%} → {new_val:.0%} {direction} {abs(change):.0%}")
        
        lines.append("")
        lines.append(f"Estimated hit rate improvement:")
        lines.append(f"  {result.original_hit_rate:.1f}% → {result.estimated_hit_rate:.1f}%")
        
        return "\n".join(lines)
    
    def _generate_recommendations(self, result: WeightOptimizationResult) -> List[str]:
        """Generate actionable recommendations"""
        
        recs = []
        
        # Analyze each component
        for name, comp in result.component_analysis.items():
            if comp.win_count + comp.loss_count < 5:
                recs.append(f"{name}: Insufficient data ({comp.win_count + comp.loss_count} samples). Keep current weight.")
                continue
            
            if comp.predictive_power > 0.6:
                recs.append(f"{name}: Strong predictor ({comp.predictive_power:.2f}). Consider increasing weight.")
            elif comp.predictive_power < 0.2:
                recs.append(f"{name}: Weak predictor ({comp.predictive_power:.2f}). Consider decreasing weight.")
            
            if comp.win_avg_score < comp.loss_avg_score:
                recs.append(f"{name}: Counter-intuitive - lower scores correlate with wins. Review logic.")
        
        # Overall
        if result.estimated_hit_rate > result.original_hit_rate + 5:
            recs.append(f"Estimated improvement: +{result.estimated_hit_rate - result.original_hit_rate:.1f}% hit rate. Apply new weights.")
        elif result.estimated_hit_rate < result.original_hit_rate - 5:
            recs.append(f"Estimated decline: {result.estimated_hit_rate - result.original_hit_rate:.1f}% hit rate. Keep current weights.")
        else:
            recs.append("Minimal estimated improvement. Current weights are near-optimal.")
        
        return recs


class SimpleWeightOptimizer:
    """
    Simplified weight optimizer for quick analysis
    
    Uses a simple rule-based approach:
    - Count how often each component is high (>60) in winning vs losing bets
    - Adjust weights proportionally
    """
    
    def optimize(
        self,
        winning_scores: List[Dict[str, float]],
        losing_scores: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Quick optimization based on component success rates
        
        Args:
            winning_scores: List of dicts with component scores for wins
            losing_scores: List of dicts with component scores for losses
            
        Returns:
            Dict of new weights
        """
        
        components = ["discrepancy", "variance_safety", "historical", "stability"]
        
        success_rates = {}
        
        for comp in components:
            # Count how often this component is high in wins vs losses
            win_high = sum(1 for s in winning_scores if s.get(comp, 0) > 60)
            loss_high = sum(1 for s in losing_scores if s.get(comp, 0) > 60)
            
            total_high = win_high + loss_high
            if total_high > 0:
                success_rate = win_high / total_high
            else:
                success_rate = 0.5
            
            success_rates[comp] = success_rate
        
        # Weights proportional to success rate
        total_success = sum(success_rates.values())
        if total_success == 0:
            return {c: 0.25 for c in components}
        
        weights = {
            comp: rate / total_success
            for comp, rate in success_rates.items()
        }
        
        return weights
