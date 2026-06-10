"""
Tests for Weight Optimizer
"""

import pytest

from app.services.anomaly.weight_optimizer import (
    WeightOptimizer,
    SimpleWeightOptimizer,
    ComponentAnalysis
)
from app.services.anomaly.scoring_calibration import ScoringWeights, ScoreBreakdown


class TestWeightOptimizer:
    """Test WeightOptimizer"""
    
    def setup_method(self):
        """Setup test optimizer"""
        self.weights = ScoringWeights(
            discrepancy=0.40,
            variance_safety=0.25,
            historical_hit_rate=0.20,
            stability=0.15
        )
        self.optimizer = WeightOptimizer(self.weights)
    
    def test_optimizer_initialization(self):
        """Test optimizer initializes"""
        assert self.optimizer is not None
        assert self.optimizer.current_weights == self.weights
    
    def test_optimization_with_sufficient_data(self):
        """Test optimization with enough data"""
        
        # Create winning breakdowns (high scores)
        wins = []
        for _ in range(30):
            b = ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            )
            wins.append(b)
        
        # Create losing breakdowns (low scores)
        losses = []
        for _ in range(20):
            b = ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            )
            losses.append(b)
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        assert result.total_bets == 50
        assert result.win_count == 30
        assert result.loss_count == 20
        assert len(result.component_analysis) == 4
        assert result.proposed_weights is not None
    
    def test_optimization_insufficient_data(self):
        """Test optimization with insufficient data"""
        
        wins = []
        losses = []
        
        # Only 5 bets total (below min_sample_size=10)
        for _ in range(3):
            wins.append(ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            ))
        
        for _ in range(2):
            losses.append(ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses, min_sample_size=10)
        
        assert "Insufficient" in result.explanation
    
    def test_component_analysis(self):
        """Test component analysis"""
        
        wins = []
        for _ in range(20):
            b = ScoreBreakdown(
                discrepancy_score=85.0,
                variance_safety_score=70.0,
                historical_hit_rate=65.0,
                stability_score=80.0,
                weights=self.weights
            )
            wins.append(b)
        
        losses = []
        for _ in range(15):
            b = ScoreBreakdown(
                discrepancy_score=45.0,
                variance_safety_score=50.0,
                historical_hit_rate=40.0,
                stability_score=35.0,
                weights=self.weights
            )
            losses.append(b)
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        # Check discrepancy analysis
        disc = result.component_analysis["discrepancy"]
        assert disc.win_count == 20
        assert disc.loss_count == 15
        assert disc.win_avg_score > disc.loss_avg_score
    
    def test_weights_sum_to_one(self):
        """Test that proposed weights sum to 1.0"""
        
        wins = []
        for _ in range(25):
            wins.append(ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            ))
        
        losses = []
        for _ in range(15):
            losses.append(ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        # Check weights sum to ~1.0
        total = (
            result.proposed_weights.discrepancy +
            result.proposed_weights.variance_safety +
            result.proposed_weights.historical_hit_rate +
            result.proposed_weights.stability
        )
        assert abs(total - 1.0) < 0.01
    
    def test_weights_within_bounds(self):
        """Test that weights are within min/max bounds"""
        
        wins = []
        for _ in range(30):
            wins.append(ScoreBreakdown(
                discrepancy_score=90.0,
                variance_safety_score=20.0,
                historical_hit_rate=10.0,
                stability_score=5.0,
                weights=self.weights
            ))
        
        losses = []
        for _ in range(20):
            losses.append(ScoreBreakdown(
                discrepancy_score=10.0,
                variance_safety_score=80.0,
                historical_hit_rate=90.0,
                stability_score=95.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        # Check bounds
        for attr in ["discrepancy", "variance_safety", "historical_hit_rate", "stability"]:
            val = getattr(result.proposed_weights, attr)
            assert val >= self.optimizer.min_weight
            assert val <= self.optimizer.max_weight
    
    def test_explanation_generated(self):
        """Test that explanation is generated"""
        
        wins = []
        for _ in range(20):
            wins.append(ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            ))
        
        losses = []
        for _ in range(15):
            losses.append(ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        assert result.explanation != ""
        assert "COMPONENT PERFORMANCE" in result.explanation
        assert "WEIGHT CHANGES" in result.explanation
    
    def test_recommendations_generated(self):
        """Test that recommendations are generated"""
        
        wins = []
        for _ in range(20):
            wins.append(ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            ))
        
        losses = []
        for _ in range(15):
            losses.append(ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        assert len(result.recommendations) > 0
    
    def test_to_dict_serialization(self):
        """Test result serialization"""
        
        wins = []
        for _ in range(15):
            wins.append(ScoreBreakdown(
                discrepancy_score=80.0,
                variance_safety_score=75.0,
                historical_hit_rate=70.0,
                stability_score=85.0,
                weights=self.weights
            ))
        
        losses = []
        for _ in range(10):
            losses.append(ScoreBreakdown(
                discrepancy_score=40.0,
                variance_safety_score=45.0,
                historical_hit_rate=35.0,
                stability_score=30.0,
                weights=self.weights
            ))
        
        result = self.optimizer.optimize_from_backtest(wins, losses)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "original_weights" in result_dict
        assert "proposed_weights" in result_dict
        assert "component_analysis" in result_dict


class TestSimpleWeightOptimizer:
    """Test SimpleWeightOptimizer"""
    
    def test_simple_optimize(self):
        """Test simple optimization"""
        
        optimizer = SimpleWeightOptimizer()
        
        # Winning scores (high discrepancy, high stability)
        win_scores = [
            {"discrepancy": 80, "variance_safety": 60, "historical": 70, "stability": 85},
            {"discrepancy": 85, "variance_safety": 65, "historical": 75, "stability": 80},
        ]
        
        # Losing scores (low discrepancy, low stability)
        loss_scores = [
            {"discrepancy": 40, "variance_safety": 70, "historical": 50, "stability": 35},
            {"discrepancy": 35, "variance_safety": 75, "historical": 45, "stability": 30},
        ]
        
        weights = optimizer.optimize(win_scores, loss_scores)
        
        assert len(weights) == 4
        assert sum(weights.values()) > 0.99  # Should sum to ~1.0
        
        # Discrepancy and stability should get higher weights
        assert weights["discrepancy"] > weights["variance_safety"]
        assert weights["stability"] > weights["variance_safety"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
