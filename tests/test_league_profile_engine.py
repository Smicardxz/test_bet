"""
Tests for League Profile Engine
"""

import pytest

from app.services.analysis.league_profile_engine import (
    LeagueProfileEngine,
    LeagueProfile,
    LeagueRanking,
    LeagueCategory
)
from app.services.stats import TeamStats
from datetime import datetime


class TestLeagueProfileEngine:
    """Test LeagueProfileEngine"""
    
    def setup_method(self):
        """Setup test engine"""
        self.engine = LeagueProfileEngine()
    
    def _create_defensive_stats(self) -> TeamStats:
        """Create very defensive team stats"""
        return TeamStats(
            team_id=1,
            team_name="Defensive Team",
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
        """Create attacking team stats"""
        return TeamStats(
            team_id=2,
            team_name="Attacking Team",
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
    
    def test_profile_creation_defensive_league(self):
        """Test profile for defensive league"""
        teams = [self._create_defensive_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("England Women", teams)
        
        assert profile.league_name == "England Women"
        assert profile.total_teams == 5
        assert profile.avg_goals_per_match < 2.0
        assert profile.under_2_5_rate > 80
        assert profile.ht_00_rate > 60
        assert profile.category == LeagueCategory.EXTREMELY_DEFENSIVE
    
    def test_profile_creation_attacking_league(self):
        """Test profile for attacking league"""
        teams = [self._create_attacking_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("Test Open League", teams)
        
        assert profile.avg_goals_per_match > 3.0
        assert profile.under_2_5_rate < 30
        assert profile.category == LeagueCategory.HIGH_SCORING
    
    def test_exploitability_calculation_defensive(self):
        """Test exploitability for defensive league"""
        teams = [self._create_defensive_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("England Women", teams)
        
        assert profile.exploitability_score > 70  # Very exploitable
        assert profile.stability_score > 70
    
    def test_exploitability_calculation_open(self):
        """Test exploitability for open league"""
        teams = [self._create_attacking_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("Open League", teams)
        
        assert profile.exploitability_score < 50  # Less exploitable for under
    
    def test_tags_generation(self):
        """Test tag generation"""
        teams = [self._create_defensive_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("England Women", teams)
        
        assert "VERY_UNDER" in profile.tags
        assert "HT_00_SPECIALIST" in profile.tags
        assert "LOW_SCORING" in profile.tags
        assert "STABLE" in profile.tags
        assert "HIGHLY_EXPLOITABLE" in profile.tags
    
    def test_league_ranking(self):
        """Test league ranking"""
        league_stats = {
            "England Women": [self._create_defensive_stats() for _ in range(5)],
            "Open League": [self._create_attacking_stats() for _ in range(5)],
            "Balanced League": [
                self._create_defensive_stats(),
                self._create_attacking_stats(),
                self._create_defensive_stats(),
                self._create_attacking_stats(),
            ]
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        
        assert len(ranking.by_exploitability) == 3
        assert ranking.best_overall is not None
        assert ranking.by_exploitability[0].exploitability_score >= ranking.by_exploitability[1].exploitability_score
    
    def test_priority_list(self):
        """Test priority league list"""
        league_stats = {
            "England Women": [self._create_defensive_stats() for _ in range(5)],
            "Open League": [self._create_attacking_stats() for _ in range(5)],
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        
        assert len(ranking.priority_scan_list) > 0
        assert "England Women" in ranking.priority_scan_list
    
    def test_avoid_list(self):
        """Test avoid list"""
        league_stats = {
            "Open League": [self._create_attacking_stats() for _ in range(5)],
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        
        assert len(ranking.avoid_list) > 0
        assert "Open League" in ranking.avoid_list
    
    def test_ht_specialists(self):
        """Test HT specialist identification"""
        league_stats = {
            "England Women": [self._create_defensive_stats() for _ in range(5)],
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        ht_specialists = self.engine.get_ht_specialist_leagues(ranking)
        
        assert len(ht_specialists) > 0
        assert ht_specialists[0].ht_00_rate > 45
    
    def test_under_specialists(self):
        """Test under specialist identification"""
        league_stats = {
            "England Women": [self._create_defensive_stats() for _ in range(5)],
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        under_leagues = self.engine.get_under_specialist_leagues(ranking)
        
        assert len(under_leagues) > 0
        assert under_leagues[0].under_2_5_rate > 65
    
    def test_profile_serialization(self):
        """Test profile serialization"""
        teams = [self._create_defensive_stats() for _ in range(5)]
        
        profile = self.engine._create_profile("England Women", teams)
        profile_dict = profile.to_dict()
        
        assert isinstance(profile_dict, dict)
        assert profile_dict["league_name"] == "England Women"
        assert profile_dict["avg_goals"] < 2.0
        assert "tags" in profile_dict
        assert "VERY_UNDER" in profile_dict["tags"]
    
    def test_recommendations(self):
        """Test recommendation generation"""
        league_stats = {
            "England Women": [self._create_defensive_stats() for _ in range(5)],
            "Open League": [self._create_attacking_stats() for _ in range(5)],
        }
        
        ranking = self.engine.analyze_leagues(league_stats)
        
        assert len(ranking.recommendations) > 0
        assert any("PRIORITY" in r for r in ranking.recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
