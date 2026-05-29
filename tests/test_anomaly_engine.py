"""
Unit tests for AnomalyEngine
Tests anomaly detection logic and edge cases
"""

import pytest
from app.services.anomaly.anomaly_engine import (
    AnomalyEngine,
    ConfidenceCategory,
    SignalStrength,
    odds_to_probability,
    normalize_probability,
    poisson_under_probability,
    poisson_pmf
)
from app.services.stats import TeamStats
from datetime import datetime


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_odds_to_probability(self):
        """Test odds to probability conversion"""
        assert odds_to_probability(2.0) == 0.5
        assert odds_to_probability(4.0) == 0.25
        assert abs(odds_to_probability(1.5) - 0.6667) < 0.001
    
    def test_odds_to_probability_edge_cases(self):
        """Test edge cases"""
        assert odds_to_probability(1.0) == 0.0
        assert odds_to_probability(0.5) == 0.0
    
    def test_normalize_probability(self):
        """Test probability normalization"""
        # 50% with 5% margin
        normalized = normalize_probability(0.5, 0.05)
        assert abs(normalized - 0.476) < 0.001
    
    def test_poisson_pmf(self):
        """Test Poisson PMF"""
        # P(X=0 | λ=2) ≈ 0.135
        prob = poisson_pmf(0, 2.0)
        assert abs(prob - 0.135) < 0.01
        
        # P(X=2 | λ=2) ≈ 0.271
        prob = poisson_pmf(2, 2.0)
        assert abs(prob - 0.271) < 0.01
    
    def test_poisson_under_probability(self):
        """Test Poisson under probability"""
        # Under 2.5 with avg 2.0 goals
        prob = poisson_under_probability(2.0, 2.5)
        assert 50 < prob < 70  # Should be around 60%


class TestAnomalyEngine:
    """Test AnomalyEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return AnomalyEngine()
    
    @pytest.fixture
    def sample_stats(self):
        """Create sample team stats"""
        return TeamStats(
            team_id=1,
            team_name="Test Team",
            sample_size=15,
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=2.5,
            avg_goals_scored=1.5,
            avg_goals_conceded=1.0,
            under_1_5_rate=30.0,
            under_2_5_rate=50.0,
            under_3_5_rate=70.0,
            under_4_5_rate=90.0,
            under_5_5_rate=100.0,
            under_extreme_line_rate=100.0,
            over_1_5_rate=70.0,
            over_2_5_rate=50.0,
            over_3_5_rate=30.0,
            over_4_5_rate=10.0,
            over_5_5_rate=0.0,
            btts_rate=60.0,
            clean_sheet_rate=20.0,
            clean_sheet_for_rate=10.0,
            clean_sheet_against_rate=10.0,
            avg_ht_goals=0.8,
            avg_ht_scored=0.5,
            avg_ht_conceded=0.3,
            ht_under_0_5_rate=40.0,
            ht_under_1_5_rate=70.0,
            ht_over_0_5_rate=60.0,
            ht_over_1_5_rate=30.0,
            ht_over_2_5_rate=10.0,
            ht_0_0_rate=40.0,
            ht_btts_rate=20.0,
            avg_second_half_goals=1.7,
            avg_second_half_scored=1.0,
            avg_second_half_conceded=0.7,
            late_goal_rate=0.0,
            goals_variance=1.5,
            goals_std_dev=1.22,
            ht_goals_variance=0.5,
            ht_goals_std_dev=0.71,
            consistency_score=0.75,
            stability_score=0.80,
            last_5_avg_goals=2.8,
            last_5_form_score=0.56,
            last_10_avg_goals=2.5,
            last_10_form_score=0.50,
            momentum_score=0.15,
            missing_ht_data_count=0,
            missing_ft_data_count=0,
            data_quality_score=1.0
        )
    
    def test_analyze_market_basic(self, engine, sample_stats):
        """Test basic market analysis"""
        result = engine.analyze_market(
            match_id=1,
            market_type="ft_under_25",
            bookmaker_odds=2.0,  # 50% implied
            home_stats=sample_stats,
            away_stats=sample_stats,
            line=2.5
        )
        
        assert result.match_id == 1
        assert result.market_type == "ft_under_25"
        assert result.line == 2.5
        assert result.bookmaker_odds == 2.0
        assert 0 <= result.anomaly_score <= 100
        assert 0 <= result.confidence_score <= 1
    
    def test_ft_under_probability(self, engine, sample_stats):
        """Test FT under probability calculation"""
        prob = engine._calculate_ft_under_probability(
            sample_stats, sample_stats, 2.5
        )
        
        assert 0 <= prob <= 1
        # Should be around 50% based on stats
        assert 0.4 < prob < 0.6
    
    def test_ht_under_probability(self, engine, sample_stats):
        """Test HT under probability calculation"""
        prob = engine._calculate_ht_under_probability(
            sample_stats, sample_stats, 0.5
        )
        
        assert 0 <= prob <= 1
        # Should be around 40% based on stats
        assert 0.3 < prob < 0.5
    
    def test_btts_probability(self, engine, sample_stats):
        """Test BTTS probability calculation"""
        prob = engine._calculate_btts_probability(
            sample_stats, sample_stats
        )
        
        assert 0 <= prob <= 1
        # Should be around 60% based on stats
        assert 0.5 < prob < 0.7
    
    def test_discrepancy_score(self, engine):
        """Test discrepancy score calculation"""
        # Small discrepancy
        score = engine._calculate_discrepancy_score(0.05)
        assert score < 20
        
        # Medium discrepancy
        score = engine._calculate_discrepancy_score(0.20)
        assert 30 < score < 50
        
        # Large discrepancy
        score = engine._calculate_discrepancy_score(0.40)
        assert score > 70
    
    def test_variance_safety_score(self, engine, sample_stats):
        """Test variance safety score"""
        score = engine._calculate_variance_safety_score(
            "ft_under_25", sample_stats, sample_stats
        )
        
        assert 0 <= score <= 100
        # Low variance should give high safety
        assert score > 40
    
    def test_confidence_categorization(self, engine):
        """Test confidence categorization"""
        assert engine._categorize_confidence(0.80) == ConfidenceCategory.HIGH
        assert engine._categorize_confidence(0.60) == ConfidenceCategory.MEDIUM
        assert engine._categorize_confidence(0.40) == ConfidenceCategory.LOW
    
    def test_positive_signals_detection(self, engine, sample_stats):
        """Test positive signals detection"""
        signals = engine._detect_positive_signals(
            market_type="ft_under_25",
            discrepancy=0.30,  # Large
            variance_safety=80.0,  # High
            stability=85.0,  # High
            home_stats=sample_stats,
            away_stats=sample_stats,
            historical_hit=70.0  # Strong
        )
        
        assert len(signals) > 0
        # Should detect extreme discrepancy
        assert any(s.type == "EXTREME_DISCREPANCY" for s in signals)
        # Should detect low variance
        assert any(s.type == "LOW_VARIANCE" for s in signals)
    
    def test_negative_signals_detection(self, engine):
        """Test negative signals detection"""
        signals = engine._detect_negative_signals(
            sample_size=5,  # Small
            data_quality=0.6,  # Poor
            variance_safety=30.0,  # Low
            stability=40.0  # Low
        )
        
        assert len(signals) > 0
        # Should detect small sample
        assert any(s.type == "SMALL_SAMPLE" for s in signals)
        # Should detect poor quality
        assert any(s.type == "POOR_DATA_QUALITY" for s in signals)
    
    def test_risk_factors_identification(self, engine):
        """Test risk factors identification"""
        risks = engine._identify_risk_factors(
            sample_size=6,
            data_quality=0.65,
            variance_safety=35.0,
            stability=45.0,
            discrepancy=0.12
        )
        
        assert len(risks) > 0
        assert any("petit" in risk.lower() for risk in risks)
    
    def test_to_dict(self, engine, sample_stats):
        """Test result conversion to dict"""
        result = engine.analyze_market(
            match_id=1,
            market_type="ft_under_25",
            bookmaker_odds=2.0,
            home_stats=sample_stats,
            away_stats=sample_stats,
            line=2.5
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == 1
        assert result_dict["market_type"] == "ft_under_25"
        assert "confidence_category" in result_dict
    
    def test_to_json(self, engine, sample_stats):
        """Test result conversion to JSON"""
        result = engine.analyze_market(
            match_id=1,
            market_type="btts",
            bookmaker_odds=1.8,
            home_stats=sample_stats,
            away_stats=sample_stats
        )
        
        result_json = result.to_json()
        
        assert isinstance(result_json, dict)
        # Should be JSON serializable
        import json
        json_str = json.dumps(result_json)
        assert isinstance(json_str, str)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def engine(self):
        return AnomalyEngine()
    
    @pytest.fixture
    def low_quality_stats(self):
        """Stats with poor quality"""
        return TeamStats(
            team_id=1,
            team_name="Low Quality Team",
            sample_size=5,  # Small
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=2.0,
            avg_goals_scored=1.0,
            avg_goals_conceded=1.0,
            under_1_5_rate=40.0,
            under_2_5_rate=60.0,
            under_3_5_rate=80.0,
            under_4_5_rate=95.0,
            under_5_5_rate=100.0,
            under_extreme_line_rate=100.0,
            over_1_5_rate=60.0,
            over_2_5_rate=40.0,
            over_3_5_rate=20.0,
            over_4_5_rate=5.0,
            over_5_5_rate=0.0,
            btts_rate=50.0,
            clean_sheet_rate=25.0,
            clean_sheet_for_rate=15.0,
            clean_sheet_against_rate=10.0,
            avg_ht_goals=0.6,
            avg_ht_scored=0.3,
            avg_ht_conceded=0.3,
            ht_under_0_5_rate=50.0,
            ht_under_1_5_rate=80.0,
            ht_over_0_5_rate=50.0,
            ht_over_1_5_rate=20.0,
            ht_over_2_5_rate=5.0,
            ht_0_0_rate=50.0,
            ht_btts_rate=15.0,
            avg_second_half_goals=1.4,
            avg_second_half_scored=0.7,
            avg_second_half_conceded=0.7,
            late_goal_rate=0.0,
            goals_variance=3.5,  # High
            goals_std_dev=1.87,
            ht_goals_variance=1.2,
            ht_goals_std_dev=1.10,
            consistency_score=0.40,  # Low
            stability_score=0.35,  # Low
            last_5_avg_goals=2.2,
            last_5_form_score=0.44,
            last_10_avg_goals=2.0,
            last_10_form_score=0.40,
            momentum_score=-0.10,
            missing_ht_data_count=2,
            missing_ft_data_count=1,
            data_quality_score=0.60  # Poor
        )
    
    def test_small_sample_analysis(self, engine, low_quality_stats):
        """Test analysis with small sample"""
        result = engine.analyze_market(
            match_id=1,
            market_type="ft_under_25",
            bookmaker_odds=2.0,
            home_stats=low_quality_stats,
            away_stats=low_quality_stats,
            line=2.5
        )
        
        # Should have low confidence
        assert result.confidence_category == ConfidenceCategory.LOW
        # Should have negative signals
        assert len(result.negative_signals) > 0
        # Should have risk factors
        assert len(result.risk_factors) > 0
    
    def test_extreme_line_analysis(self, engine, low_quality_stats):
        """Test analysis with extreme line"""
        result = engine.analyze_market(
            match_id=1,
            market_type="ft_under_125",
            bookmaker_odds=1.5,
            home_stats=low_quality_stats,
            away_stats=low_quality_stats,
            line=12.5
        )
        
        # Should calculate probability
        assert 0 <= result.model_probability <= 1
        # Extreme line should have very high probability
        assert result.model_probability > 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
