"""
Tests for Priority Ranking Engine
"""

import pytest

from app.services.analysis.priority_ranking_engine import (
    PriorityRankingEngine,
    PriorityAnomaly,
    PriorityRanking,
    RiskLevel
)
from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory


class TestPriorityRankingEngine:
    """Test PriorityRankingEngine"""
    
    def setup_method(self):
        """Setup test engine"""
        self.engine = PriorityRankingEngine()
    
    def _create_anomaly(self, **kwargs) -> AnomalyResult:
        """Helper to create anomaly"""
        defaults = {
            "match_id": 1,
            "market_type": "ft_under_25",
            "line": 2.5,
            "bookmaker_odds": 1.85,
            "bookmaker_probability": 0.54,
            "normalized_bookmaker_probability": 0.58,
            "model_probability": 0.75,
            "discrepancy_score": 75.0,
            "variance_safety_score": 70.0,
            "historical_hit_rate": 70.0,
            "stability_score": 75.0,
            "anomaly_score": 72.0,
            "confidence_category": ConfidenceCategory.HIGH,
            "confidence_score": 0.72,
            "positive_signals": [],
            "negative_signals": [],
            "risk_factors": [],
            "explanation_summary": "Test anomaly",
            "sample_size": 15,
            "data_quality": 1.0
        }
        defaults.update(kwargs)
        return AnomalyResult(**defaults)
    
    def test_engine_initialization(self):
        """Test engine initializes"""
        assert self.engine is not None
        assert self.engine.weights["anomaly"] == 0.30
    
    def test_basic_ranking(self):
        """Test basic ranking functionality"""
        anomalies = [
            self._create_anomaly(match_id=1, anomaly_score=85.0),
            self._create_anomaly(match_id=2, anomaly_score=70.0),
            self._create_anomaly(match_id=3, anomaly_score=60.0),
        ]
        
        ranking = self.engine.rank_anomalies(
            anomalies=anomalies,
            min_anomaly_score=60.0
        )
        
        assert ranking.total_anomalies == 3
        assert len(ranking.top_picks) == 3
        assert ranking.top_picks[0].anomaly_score == 85.0
        assert ranking.top_picks[1].anomaly_score == 70.0
    
    def test_filtering_below_threshold(self):
        """Test filtering anomalies below threshold"""
        anomalies = [
            self._create_anomaly(match_id=1, anomaly_score=85.0),
            self._create_anomaly(match_id=2, anomaly_score=55.0),  # Below
        ]
        
        ranking = self.engine.rank_anomalies(
            anomalies=anomalies,
            min_anomaly_score=60.0
        )
        
        assert ranking.total_anomalies == 2
        assert len(ranking.top_picks) == 1  # Only 85
        assert ranking.filtered_out == 1
    
    def test_variance_safety_boost(self):
        """Test that high variance safety boosts priority"""
        high_var = self._create_anomaly(
            match_id=1,
            anomaly_score=75.0,
            variance_safety_score=90.0
        )
        low_var = self._create_anomaly(
            match_id=2,
            anomaly_score=75.0,
            variance_safety_score=40.0
        )
        
        ranking = self.engine.rank_anomalies([high_var, low_var])
        
        # High variance should rank higher
        assert ranking.top_picks[0].match_id == "1"
    
    def test_sample_size_penalty(self):
        """Test penalty for low sample size"""
        large_sample = self._create_anomaly(
            match_id=1,
            anomaly_score=75.0,
            sample_size=15
        )
        small_sample = self._create_anomaly(
            match_id=2,
            anomaly_score=75.0,
            sample_size=6
        )
        
        ranking = self.engine.rank_anomalies([small_sample, large_sample])
        
        # Large sample should have higher priority
        high_priority = ranking.top_picks[0]
        assert high_priority.sample_size >= 10
    
    def test_risk_adjustment(self):
        """Test risk-adjusted scoring"""
        safe = self._create_anomaly(
            match_id=1,
            anomaly_score=80.0,
            variance_safety_score=85.0,
            sample_size=15
        )
        risky = self._create_anomaly(
            match_id=2,
            anomaly_score=80.0,
            variance_safety_score=35.0,
            sample_size=6
        )
        
        ranking = self.engine.rank_anomalies([safe, risky])
        
        # Safe anomaly should have higher risk-adjusted score
        safe_pa = next(pa for pa in ranking.risk_adjusted_ranking if pa.match_id == "1")
        risky_pa = next(pa for pa in ranking.risk_adjusted_ranking if pa.match_id == "2")
        
        assert safe_pa.risk_adjusted_score > risky_pa.risk_adjusted_score
    
    def test_risk_levels(self):
        """Test risk level determination"""
        anomalies = [
            self._create_anomaly(match_id=1, anomaly_score=85, variance_safety_score=85, sample_size=15),
            self._create_anomaly(match_id=2, anomaly_score=70, variance_safety_score=40, sample_size=8),
            self._create_anomaly(match_id=3, anomaly_score=65, variance_safety_score=30, sample_size=6,
                                  stability_score=30),
        ]
        
        ranking = self.engine.rank_anomalies(anomalies)
        
        # Should have different risk levels
        risk_levels = {pa.risk_level for pa in ranking.top_picks}
        assert len(risk_levels) >= 2  # At least 2 different levels
    
    def test_line_breach_incorporation(self):
        """Test line breach results incorporated"""
        from app.services.analysis import LineBreachResult
        
        anomaly = self._create_anomaly(match_id=1, anomaly_score=80.0)
        
        breach_result = LineBreachResult(
            market_type="ft_under_25",
            line=2.5,
            historical_safety_score=90.0,
            line_breach_rate=5.0
        )
        
        line_breach_map = {"1": breach_result}
        
        ranking = self.engine.rank_anomalies(
            [anomaly],
            line_breach_results=line_breach_map
        )
        
        pa = ranking.top_picks[0]
        assert pa.line_breach_safety == 90.0
    
    def test_max_results_limit(self):
        """Test max results limit"""
        anomalies = [self._create_anomaly(match_id=i, anomaly_score=60 + i) for i in range(25)]
        
        ranking = self.engine.rank_anomalies(anomalies, max_results=10)
        
        assert len(ranking.top_picks) == 10
    
    def test_safe_picks_filter(self):
        """Test filtering safe picks"""
        anomalies = [
            self._create_anomaly(match_id=1, anomaly_score=85, variance_safety_score=85, sample_size=15),
            self._create_anomaly(match_id=2, anomaly_score=80, variance_safety_score=35, sample_size=6),
        ]
        
        ranking = self.engine.rank_anomalies(anomalies)
        safe = self.engine.get_safe_picks(ranking, max_risk=RiskLevel.LOW)
        
        assert len(safe) >= 1
        for pa in safe:
            assert pa.risk_level in (RiskLevel.VERY_LOW, RiskLevel.LOW)
    
    def test_explanation_generation(self):
        """Test explanation generation"""
        anomaly = self._create_anomaly(match_id=1, anomaly_score=80.0)
        
        ranking = self.engine.rank_anomalies([anomaly])
        pa = ranking.top_picks[0]
        
        assert pa.explanation != ""
        assert "Score" in pa.explanation
    
    def test_serialization(self):
        """Test serialization"""
        anomalies = [self._create_anomaly(match_id=1, anomaly_score=80.0)]
        
        ranking = self.engine.rank_anomalies(anomalies)
        ranking_dict = ranking.to_dict()
        
        assert isinstance(ranking_dict, dict)
        assert "summary" in ranking_dict
        assert "top_picks" in ranking_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
