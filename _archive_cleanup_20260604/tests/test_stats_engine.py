"""
Unit tests for StatsEngine
Tests pure functions and edge cases
"""

import pytest
from app.services.stats.stats_engine import (
    safe_mean,
    safe_variance,
    safe_stdev,
    percentage,
    calculate_form_score,
    calculate_momentum
)


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_safe_mean_normal(self):
        """Test safe_mean with normal values"""
        assert safe_mean([1, 2, 3, 4, 5]) == 3.0
        assert safe_mean([2.5, 3.5]) == 3.0
    
    def test_safe_mean_empty(self):
        """Test safe_mean with empty list"""
        assert safe_mean([]) == 0.0
    
    def test_safe_mean_single(self):
        """Test safe_mean with single value"""
        assert safe_mean([5.0]) == 5.0
    
    def test_safe_variance_normal(self):
        """Test safe_variance with normal values"""
        result = safe_variance([1, 2, 3, 4, 5])
        assert result > 0
    
    def test_safe_variance_empty(self):
        """Test safe_variance with empty list"""
        assert safe_variance([]) == 0.0
    
    def test_safe_variance_single(self):
        """Test safe_variance with single value"""
        assert safe_variance([5.0]) == 0.0
    
    def test_safe_stdev_normal(self):
        """Test safe_stdev with normal values"""
        result = safe_stdev([1, 2, 3, 4, 5])
        assert result > 0
    
    def test_safe_stdev_empty(self):
        """Test safe_stdev with empty list"""
        assert safe_stdev([]) == 0.0
    
    def test_percentage_normal(self):
        """Test percentage calculation"""
        assert percentage(5, 10) == 50.0
        assert percentage(3, 12) == 25.0
        assert percentage(0, 10) == 0.0
    
    def test_percentage_zero_total(self):
        """Test percentage with zero total"""
        assert percentage(5, 0) == 0.0
    
    def test_calculate_form_score(self):
        """Test form score calculation"""
        # High scoring
        assert calculate_form_score([4, 5, 4, 5]) > 0.8
        
        # Low scoring
        assert calculate_form_score([0, 1, 0, 1]) < 0.3
        
        # Empty
        assert calculate_form_score([]) == 0.0
    
    def test_calculate_momentum_improving(self):
        """Test momentum with improving trend"""
        # Recent better than older
        goals = [4, 5, 4, 5, 1, 2, 1, 2]
        momentum = calculate_momentum(goals)
        assert momentum > 0
    
    def test_calculate_momentum_declining(self):
        """Test momentum with declining trend"""
        # Recent worse than older
        goals = [1, 2, 1, 2, 4, 5, 4, 5]
        momentum = calculate_momentum(goals)
        assert momentum < 0
    
    def test_calculate_momentum_stable(self):
        """Test momentum with stable trend"""
        goals = [2, 3, 2, 3, 2, 3, 2, 3]
        momentum = calculate_momentum(goals)
        assert abs(momentum) < 0.2
    
    def test_calculate_momentum_insufficient_data(self):
        """Test momentum with insufficient data"""
        assert calculate_momentum([1, 2, 3]) == 0.0


class TestTeamStatsDataclass:
    """Test TeamStats dataclass"""
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        from app.services.stats.stats_engine import TeamStats
        
        stats = TeamStats(
            team_id=1,
            team_name="Test Team",
            sample_size=10,
            home_away="home",
            last_updated="2026-05-27T12:00:00",
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
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result["team_id"] == 1
        assert result["team_name"] == "Test Team"
        assert result["avg_total_goals"] == 2.5
        assert result["data_quality_score"] == 1.0
    
    def test_to_json(self):
        """Test conversion to JSON"""
        from app.services.stats.stats_engine import TeamStats
        
        stats = TeamStats(
            team_id=1,
            team_name="Test Team",
            sample_size=10,
            home_away="all",
            last_updated="2026-05-27T12:00:00",
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
        
        result = stats.to_json()
        
        assert isinstance(result, dict)
        # Should be JSON serializable
        import json
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_all_zeros(self):
        """Test with all zero goals"""
        goals = [0, 0, 0, 0, 0]
        
        assert safe_mean(goals) == 0.0
        assert safe_variance(goals) == 0.0
        assert calculate_form_score(goals) == 0.0
    
    def test_very_high_variance(self):
        """Test with very high variance"""
        goals = [0, 10, 0, 10, 0, 10]
        
        variance = safe_variance(goals)
        assert variance > 20  # High variance
    
    def test_negative_momentum_edge(self):
        """Test momentum doesn't exceed bounds"""
        # Extreme decline
        goals = [0, 0, 0, 10, 10, 10]
        momentum = calculate_momentum(goals)
        
        assert momentum >= -1.0
        assert momentum <= 1.0
    
    def test_positive_momentum_edge(self):
        """Test momentum doesn't exceed bounds"""
        # Extreme improvement
        goals = [10, 10, 10, 0, 0, 0]
        momentum = calculate_momentum(goals)
        
        assert momentum >= -1.0
        assert momentum <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
