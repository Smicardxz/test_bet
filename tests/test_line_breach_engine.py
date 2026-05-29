"""
Tests for Historical Line Breach Engine
"""

import pytest

from app.services.analysis import HistoricalLineBreachEngine, LineBreachSignal
from app.services.stats import TeamStats
from datetime import datetime


class TestLineBreachEngine:
    """Test HistoricalLineBreachEngine"""
    
    def setup_method(self):
        """Setup test engine"""
        self.engine = HistoricalLineBreachEngine()
    
    def _create_defensive_stats(self) -> TeamStats:
        """Create stats for defensive team (low goals)"""
        return TeamStats(
            team_id=1,
            team_name="Defensive Team",
            sample_size=15,
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=1.5,
            avg_goals_scored=0.8,
            avg_goals_conceded=0.7,
            under_1_5_rate=73.3,
            under_2_5_rate=86.7,
            under_3_5_rate=93.3,
            under_4_5_rate=100.0,
            under_5_5_rate=100.0,
            under_extreme_line_rate=100.0,
            over_1_5_rate=26.7,
            over_2_5_rate=13.3,
            over_3_5_rate=6.7,
            over_4_5_rate=0.0,
            over_5_5_rate=0.0,
            btts_rate=33.3,
            clean_sheets_rate=46.7,
            avg_ht_total_goals=0.5,
            avg_ht_goals_scored=0.3,
            avg_ht_goals_conceded=0.2,
            ht_00_rate=60.0,
            variance_goals_scored=0.4,
            variance_goals_conceded=0.3,
            stability_score=0.85,
            form=["W", "D", "L", "W", "D"],
            data_quality_score=1.0
        )
    
    def test_engine_initialization(self):
        """Test engine initializes"""
        assert self.engine is not None
    
    def test_analyze_extreme_under_line(self):
        """Test analysis of extreme under line (12.5)"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_125",
            line=12.5,
            home_stats=stats,
            away_stats=stats
        )
        
        # Should be extremely safe
        assert result.line == 12.5
        assert result.total_matches > 0
        assert result.line_breach_rate < 10  # Should rarely/never breach
        assert result.signal in [LineBreachSignal.EXTREMELY_SAFE, LineBreachSignal.VERY_SAFE, LineBreachSignal.INCONSISTENT]
        assert result.historical_safety_score > 80
    
    def test_analyze_normal_under_line(self):
        """Test analysis of normal under line (2.5)"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert result.line == 2.5
        assert result.total_matches > 0
        # Should be safe for defensive teams
        assert result.line_breach_rate < 50
        assert result.average_value < 2.5
    
    def test_analyze_ht_under_line(self):
        """Test analysis of HT under line"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ht_under_05",
            line=0.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert result.line == 0.5
        assert result.total_matches > 0
        # HT 0-0 rate is 60%, so should be safe
        assert result.signal in [LineBreachSignal.SAFE, LineBreachSignal.VERY_SAFE, LineBreachSignal.EXTREMELY_SAFE]
    
    def test_breach_metrics_sum_to_total(self):
        """Test that breach + hit + safe = total"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        total = result.line_breach_count + result.line_hit_count + result.line_safe_count
        assert total == result.total_matches
    
    def test_rates_sum_to_100(self):
        """Test that rates sum to 100%"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        total_rate = result.line_breach_rate + result.line_hit_rate + result.line_safe_rate
        assert abs(total_rate - 100.0) < 0.1  # Allow small floating point error
    
    def test_consistency_score_range(self):
        """Test consistency score is in valid range"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert 0 <= result.consistency_score <= 100
    
    def test_safety_scores_range(self):
        """Test safety scores are in valid range"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert 0 <= result.historical_safety_score <= 100
        assert 0 <= result.stability_score <= 100
    
    def test_signal_strength_range(self):
        """Test signal strength is in valid range"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert 0 <= result.signal_strength <= 100
    
    def test_explanation_generated(self):
        """Test explanation is generated"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        assert result.explanation != ""
        assert "Line" in result.explanation
        assert "Breached" in result.explanation
    
    def test_factors_identified(self):
        """Test risk and positive factors are identified"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_125",
            line=12.5,
            home_stats=stats,
            away_stats=stats
        )
        
        # Extreme line should have positive factors
        assert len(result.positive_factors) > 0
    
    def test_to_dict_serialization(self):
        """Test result can be serialized to dict"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_line(
            market_type="ft_under_25",
            line=2.5,
            home_stats=stats,
            away_stats=stats
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "market_type" in result_dict
        assert "line" in result_dict
        assert "line_breach_rate" in result_dict
        assert "signal" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
