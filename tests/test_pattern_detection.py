"""
Tests for Pattern Detection Engine
"""

import pytest
from datetime import datetime

from app.services.analysis import (
    PatternDetectionEngine,
    PatternType,
    PatternStrength,
    PatternDetectionResult
)
from app.services.stats import TeamStats


class TestPatternDetection:
    """Test PatternDetectionEngine"""
    
    def setup_method(self):
        """Setup test engine"""
        self.engine = PatternDetectionEngine()
    
    def _create_defensive_stats(self) -> TeamStats:
        """Create stats for very defensive team"""
        return TeamStats(
            team_id=1,
            team_name="Defensive United",
            sample_size=15,
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=1.2,
            avg_goals_scored=0.6,
            avg_goals_conceded=0.6,
            under_1_5_rate=80.0,
            under_2_5_rate=93.3,
            under_3_5_rate=100.0,
            under_4_5_rate=100.0,
            under_5_5_rate=100.0,
            under_extreme_line_rate=100.0,
            over_1_5_rate=20.0,
            over_2_5_rate=6.7,
            over_3_5_rate=0.0,
            over_4_5_rate=0.0,
            over_5_5_rate=0.0,
            btts_rate=20.0,
            clean_sheets_rate=53.3,
            avg_ht_total_goals=0.3,
            avg_ht_goals_scored=0.2,
            avg_ht_goals_conceded=0.1,
            ht_00_rate=66.7,
            variance_goals_scored=0.3,
            variance_goals_conceded=0.3,
            stability_score=0.90,
            form=["W", "W", "D", "W", "D"],
            data_quality_score=1.0
        )
    
    def _create_attacking_stats(self) -> TeamStats:
        """Create stats for attacking team"""
        return TeamStats(
            team_id=2,
            team_name="Attack FC",
            sample_size=15,
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=3.5,
            avg_goals_scored=2.0,
            avg_goals_conceded=1.5,
            under_1_5_rate=10.0,
            under_2_5_rate=20.0,
            under_3_5_rate=40.0,
            under_4_5_rate=60.0,
            under_5_5_rate=80.0,
            under_extreme_line_rate=100.0,
            over_1_5_rate=90.0,
            over_2_5_rate=80.0,
            over_3_5_rate=60.0,
            over_4_5_rate=40.0,
            over_5_5_rate=20.0,
            btts_rate=80.0,
            clean_sheets_rate=13.3,
            avg_ht_total_goals=1.8,
            avg_ht_goals_scored=1.0,
            avg_ht_goals_conceded=0.8,
            ht_00_rate=13.3,
            variance_goals_scored=1.5,
            variance_goals_conceded=1.2,
            stability_score=0.40,
            form=["L", "W", "L", "W", "L"],
            data_quality_score=1.0
        )
    
    def test_engine_initialization(self):
        """Test engine initializes"""
        assert self.engine is not None
    
    def test_extreme_under_pattern(self):
        """Test detection of extreme under pattern"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        assert result.team_id == "1"
        assert len(result.patterns) > 0
        
        # Should detect EXTREME_UNDER
        under_patterns = [p for p in result.patterns if p.pattern_type == PatternType.EXTREME_UNDER]
        assert len(under_patterns) > 0
        assert under_patterns[0].strength in (PatternStrength.EXTREME, PatternStrength.STRONG)
    
    def test_low_tempo_pattern(self):
        """Test detection of low tempo first half"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        ht_patterns = [p for p in result.patterns if p.pattern_type == PatternType.LOW_TEMPO_FIRST_HALF]
        assert len(ht_patterns) > 0
        assert ht_patterns[0].score > 50
    
    def test_btts_rare_pattern(self):
        """Test detection of rare BTTS"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        btts_patterns = [p for p in result.patterns if p.pattern_type == PatternType.BTTS_RARE]
        assert len(btts_patterns) > 0
    
    def test_stable_performance_pattern(self):
        """Test detection of stable performance"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        stability_patterns = [p for p in result.patterns if p.pattern_type == PatternType.STABLE_PERFORMANCE]
        assert len(stability_patterns) > 0
    
    def test_clean_sheet_specialist(self):
        """Test detection of clean sheet specialist"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        cs_patterns = [p for p in result.patterns if p.pattern_type == PatternType.CLEAN_SHEET_SPECIALIST]
        assert len(cs_patterns) > 0
    
    def test_attacking_team_patterns(self):
        """Test detection for attacking team"""
        stats = self._create_attacking_stats()
        
        result = self.engine.analyze_team(
            team_id="2",
            team_name="Attack FC",
            overall_stats=stats
        )
        
        # Should detect over patterns
        over_patterns = [p for p in result.patterns if p.pattern_type == PatternType.EXTREME_OVER]
        assert len(over_patterns) > 0 or any(p.pattern_type == PatternType.HIGH_TEMPO_FIRST_HALF for p in result.patterns)
    
    def test_pattern_tags_generated(self):
        """Test that pattern tags are generated"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        assert len(result.pattern_tags) > 0
        assert "EXTREME_UNDER" in result.pattern_tags
        assert "LOW_TEMPO_FIRST_HALF" in result.pattern_tags
    
    def test_pattern_score_calculated(self):
        """Test that pattern score is calculated"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        assert result.pattern_score > 0
        assert 0 <= result.pattern_score <= 100
    
    def test_explanation_generated(self):
        """Test that explanation is generated"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        assert result.pattern_explanation != ""
        assert "Defensive United" in result.pattern_explanation
    
    def test_dominant_patterns(self):
        """Test dominant patterns identification"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        assert len(result.dominant_patterns) > 0
        assert len(result.dominant_patterns) <= 3
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        low_stats = TeamStats(
            team_id=3,
            team_name="New Team",
            sample_size=3,  # Too small
            home_away="all",
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=0.0,
            avg_goals_scored=0.0,
            avg_goals_conceded=0.0,
            under_1_5_rate=0.0,
            under_2_5_rate=0.0,
            under_3_5_rate=0.0,
            under_4_5_rate=0.0,
            under_5_5_rate=0.0,
            under_extreme_line_rate=0.0,
            over_1_5_rate=0.0,
            over_2_5_rate=0.0,
            over_3_5_rate=0.0,
            over_4_5_rate=0.0,
            over_5_5_rate=0.0,
            btts_rate=0.0,
            clean_sheets_rate=0.0,
            avg_ht_total_goals=0.0,
            avg_ht_goals_scored=0.0,
            avg_ht_goals_conceded=0.0,
            ht_00_rate=0.0,
            variance_goals_scored=0.0,
            variance_goals_conceded=0.0,
            stability_score=0.0,
            form=[],
            data_quality_score=0.0
        )
        
        result = self.engine.analyze_team(
            team_id="3",
            team_name="New Team",
            overall_stats=low_stats
        )
        
        assert len(result.patterns) == 0
        assert "Insufficient" in result.pattern_explanation
    
    def test_league_analysis(self):
        """Test league pattern detection"""
        defensive = self._create_defensive_stats()
        defensive2 = self._create_defensive_stats()
        
        league_patterns = self.engine.analyze_league(
            [defensive, defensive2],
            league_name="Test League"
        )
        
        assert len(league_patterns) > 0
        assert any(p.pattern_type == PatternType.LOW_SCORING_LEAGUE for p in league_patterns)
    
    def test_to_dict_serialization(self):
        """Test result serialization"""
        stats = self._create_defensive_stats()
        
        result = self.engine.analyze_team(
            team_id="1",
            team_name="Defensive United",
            overall_stats=stats
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["team_id"] == "1"
        assert result_dict["team_name"] == "Defensive United"
        assert "patterns" in result_dict
        assert "pattern_tags" in result_dict
        assert "pattern_score" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
