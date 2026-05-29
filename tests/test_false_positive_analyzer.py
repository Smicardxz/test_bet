"""
Tests for False Positive Analyzer
"""

import pytest

from app.services.anomaly.false_positive_analyzer import (
    FalsePositiveAnalyzer,
    FalsePositiveAnalysis,
    FalsePositiveCase,
    FailureType
)
from app.services.anomaly.scoring_calibration import ScoreBreakdown, ScoringWeights
from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory


class TestFalsePositiveAnalyzer:
    """Test FalsePositiveAnalyzer"""
    
    def setup_method(self):
        """Setup test analyzer"""
        self.analyzer = FalsePositiveAnalyzer()
        self.weights = ScoringWeights()
    
    def _create_result(self, **kwargs) -> AnomalyResult:
        """Helper to create AnomalyResult"""
        defaults = {
            "match_id": 1,
            "market_type": "ft_under_25",
            "line": 2.5,
            "bookmaker_odds": 1.85,
            "bookmaker_probability": 0.54,
            "normalized_bookmaker_probability": 0.58,
            "model_probability": 0.75,
            "discrepancy_score": 70.0,
            "variance_safety_score": 70.0,
            "historical_hit_rate": 70.0,
            "stability_score": 70.0,
            "anomaly_score": 70.0,
            "confidence_category": ConfidenceCategory.HIGH,
            "confidence_score": 0.70,
            "positive_signals": [],
            "negative_signals": [],
            "risk_factors": [],
            "explanation_summary": "Test",
            "sample_size": 15,
            "data_quality": 1.0
        }
        defaults.update(kwargs)
        return AnomalyResult(**defaults)
    
    def _create_breakdown(self, **kwargs) -> ScoreBreakdown:
        """Helper to create ScoreBreakdown"""
        defaults = {
            "discrepancy_score": 70.0,
            "variance_safety_score": 70.0,
            "historical_hit_rate": 70.0,
            "stability_score": 70.0,
            "weights": self.weights
        }
        defaults.update(kwargs)
        return ScoreBreakdown(**defaults)
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes"""
        assert self.analyzer is not None
    
    def test_variance_blindness_detection(self):
        """Test detection of variance blindness"""
        # High discrepancy, low variance safety
        result = self._create_result(
            discrepancy_score=85,
            variance_safety_score=35,
            risk_factors=["High variance"]
        )
        breakdown = self._create_breakdown(
            discrepancy_score=85,
            variance_safety_score=35
        )
        
        case = self.analyzer._classify_failure(result, breakdown)
        
        assert case.failure_type == FailureType.VARIANCE_BLINDNESS
        assert "variance" in case.failure_explanation.lower()
        assert len(case.missing_signals) > 0
    
    def test_insufficient_data_detection(self):
        """Test detection of insufficient data"""
        result = self._create_result(
            sample_size=6,
            risk_factors=["Small sample"]
        )
        breakdown = self._create_breakdown()
        
        case = self.analyzer._classify_failure(result, breakdown)
        
        assert case.failure_type == FailureType.INSUFFICIENT_DATA
        assert case.sample_size == 6
    
    def test_misleading_stability(self):
        """Test detection of misleading stability"""
        result = self._create_result(
            stability_score=85,
            historical_hit_rate=35
        )
        breakdown = self._create_breakdown(
            stability_score=85,
            historical_hit_rate=35
        )
        
        case = self.analyzer._classify_failure(result, breakdown)
        
        assert case.failure_type == FailureType.MISLEADING_STABILITY
        assert "stability" in case.failure_explanation.lower()
    
    def test_full_analysis(self):
        """Test full analysis with wins and losses"""
        wins = []
        for _ in range(10):
            result = self._create_result(anomaly_score=80)
            breakdown = self._create_breakdown(discrepancy_score=80)
            wins.append((result, breakdown))
        
        losses = []
        for _ in range(5):
            result = self._create_result(
                anomaly_score=70,
                discrepancy_score=85,
                variance_safety_score=35
            )
            breakdown = self._create_breakdown(
                discrepancy_score=85,
                variance_safety_score=35
            )
            losses.append((result, breakdown))
        
        analysis = self.analyzer.analyze(wins, losses)
        
        assert analysis.total_high_confidence_bets == 15
        assert analysis.high_confidence_wins == 10
        assert analysis.high_confidence_losses == 5
        assert analysis.false_positive_rate == (5/15)*100
        assert len(analysis.cases) == 5
    
    def test_problematic_components(self):
        """Test problematic component identification"""
        losses = []
        for _ in range(5):
            result = self._create_result(
                discrepancy_score=85,
                variance_safety_score=35
            )
            breakdown = self._create_breakdown(
                discrepancy_score=85,
                variance_safety_score=35
            )
            losses.append((result, breakdown))
        
        problematic = self.analyzer._identify_problematic_components(losses)
        
        assert "discrepancy" in problematic
        assert "variance_safety" in problematic
        assert problematic["discrepancy"] > problematic["variance_safety"]
    
    def test_recommendations(self):
        """Test recommendation generation"""
        analysis = FalsePositiveAnalysis()
        analysis.false_positive_rate = 35.0
        analysis.cases = [FalsePositiveCase(
            match_id="1",
            market_type="ft_under_25",
            predicted_score=75.0,
            predicted_confidence="HIGH",
            actual_outcome="LOSS",
            failure_type=FailureType.VARIANCE_BLINDNESS,
            failure_explanation="Test"
        )]
        analysis.problematic_components = {"discrepancy": 80.0}
        
        recs = self.analyzer._generate_recommendations(analysis)
        
        assert len(recs) > 0
        assert any("CRITICAL" in r for r in recs)
    
    def test_protections(self):
        """Test protection suggestions"""
        analysis = FalsePositiveAnalysis()
        analysis.false_positive_rate = 35.0
        
        protections = self.analyzer._suggest_protections(analysis)
        
        assert len(protections) > 0
        assert any("sample_size" in p for p in protections)
        assert any("variance" in p for p in protections)
    
    def test_adjusted_thresholds(self):
        """Test threshold adjustment"""
        analysis = FalsePositiveAnalysis()
        analysis.false_positive_rate = 35.0
        
        thresholds = self.analyzer.get_adjusted_thresholds(analysis)
        
        assert thresholds["min_sample_size"] == 15.0  # Raised for high FP
        assert thresholds["min_variance_safety"] == 65.0
        assert thresholds["min_anomaly_score"] == 75.0
    
    def test_adjusted_thresholds_low_fp(self):
        """Test thresholds with low false positive rate"""
        analysis = FalsePositiveAnalysis()
        analysis.false_positive_rate = 10.0
        
        thresholds = self.analyzer.get_adjusted_thresholds(analysis)
        
        assert thresholds["min_sample_size"] == 8.0  # Default (low FP)
    
    def test_case_serialization(self):
        """Test case serialization"""
        case = FalsePositiveCase(
            match_id="test_1",
            market_type="ft_under_25",
            predicted_score=75.0,
            predicted_confidence="HIGH",
            actual_outcome="LOSS",
            failure_type=FailureType.VARIANCE_BLINDNESS,
            failure_explanation="Test case",
            discrepancy_score=80.0,
            variance_safety_score=35.0,
            historical_hit_rate=50.0,
            stability_score=70.0
        )
        
        case_dict = case.to_dict()
        
        assert isinstance(case_dict, dict)
        assert case_dict["match_id"] == "test_1"
        assert case_dict["failure_type"] == "VARIANCE_BLINDNESS"
    
    def test_analysis_serialization(self):
        """Test full analysis serialization"""
        analysis = FalsePositiveAnalysis()
        analysis.total_high_confidence_bets = 15
        analysis.high_confidence_wins = 10
        analysis.high_confidence_losses = 5
        analysis.false_positive_rate = 33.3
        
        analysis_dict = analysis.to_dict()
        
        assert isinstance(analysis_dict, dict)
        assert analysis_dict["summary"]["total_high_confidence"] == 15
        assert analysis_dict["summary"]["false_positive_rate"] == 33.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
