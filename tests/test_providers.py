"""
Tests for Data Providers
"""

import pytest
from datetime import datetime, date
from app.providers import MockDataProvider, ProviderConfig
from app.providers.models import MatchStatus


class TestMockProvider:
    """Test MockDataProvider"""
    
    def setup_method(self):
        """Setup test provider"""
        self.provider = MockDataProvider()
    
    def test_get_today_matches(self):
        """Test getting today's matches"""
        response = self.provider.get_today_matches()
        
        assert response.success is True
        assert response.provider == "mock"
        assert len(response.data) > 0
        
        # Check first match structure
        match = response.data[0]
        assert hasattr(match, 'id')
        assert hasattr(match, 'home_team')
        assert hasattr(match, 'away_team')
        assert hasattr(match, 'competition')
        assert match.status == MatchStatus.SCHEDULED
    
    def test_get_today_matches_filtered(self):
        """Test filtering matches by competition"""
        response = self.provider.get_today_matches(
            competition_ids=["eng_women_champ"]
        )
        
        assert response.success is True
        assert all(
            m.competition.id == "eng_women_champ"
            for m in response.data
        )
    
    def test_get_match_details(self):
        """Test getting match details"""
        response = self.provider.get_match_details("match_001")
        
        assert response.success is True
        assert response.data.id == "match_001"
        assert response.data.home_team.name == "London City Lionesses"
        assert response.data.away_team.name == "Bristol City Women"
    
    def test_get_match_details_not_found(self):
        """Test getting non-existent match"""
        response = self.provider.get_match_details("nonexistent")
        
        assert response.success is False
        assert "not found" in response.error.lower()
    
    def test_get_team_recent_matches(self):
        """Test getting team recent matches"""
        response = self.provider.get_team_recent_matches("london_city", limit=5)
        
        assert response.success is True
        assert len(response.data) == 5
        
        # Check all matches involve the team
        for match in response.data:
            assert (
                match.home_team.id == "london_city" or
                match.away_team.id == "london_city"
            )
            assert match.status == MatchStatus.FINISHED
            assert match.score_fulltime is not None
    
    def test_get_head_to_head(self):
        """Test getting head-to-head"""
        response = self.provider.get_head_to_head("london_city", "bristol_city")
        
        assert response.success is True
        assert response.data.team_a.id == "london_city"
        assert response.data.team_b.id == "bristol_city"
        assert response.data.total_matches > 0
    
    def test_get_competition_matches(self):
        """Test getting competition matches"""
        response = self.provider.get_competition_matches("eng_women_champ")
        
        assert response.success is True
        assert all(
            m.competition.id == "eng_women_champ"
            for m in response.data
        )
    
    def test_get_odds(self):
        """Test getting odds"""
        response = self.provider.get_odds("match_001")
        
        assert response.success is True
        assert len(response.data) > 0
        
        # Check odds structure
        odds = response.data[0]
        assert hasattr(odds, 'bookmaker')
        assert hasattr(odds, 'market_type')
        assert odds.bookmaker == "Mock Bookmaker"


class TestProviderConfig:
    """Test ProviderConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ProviderConfig(name="test")
        
        assert config.name == "test"
        assert config.enabled is True
        assert config.cache_enabled is True
        assert config.rate_limit_per_minute == 60
        assert config.timeout_seconds == 10
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ProviderConfig(
            name="custom",
            enabled=False,
            rate_limit_per_minute=30,
            cache_ttl_seconds=600
        )
        
        assert config.name == "custom"
        assert config.enabled is False
        assert config.rate_limit_per_minute == 30
        assert config.cache_ttl_seconds == 600


class TestProviderCaching:
    """Test provider caching functionality"""
    
    def setup_method(self):
        """Setup test provider with caching"""
        config = ProviderConfig(
            name="test_cache",
            cache_enabled=True,
            cache_ttl_seconds=60
        )
        self.provider = MockDataProvider(config)
    
    def teardown_method(self):
        """Cleanup cache"""
        self.provider.clear_cache()
    
    def test_cache_stats(self):
        """Test cache statistics"""
        stats = self.provider.get_cache_stats()
        
        assert stats["enabled"] is True
        assert "total_files" in stats
        assert "total_size_bytes" in stats
    
    def test_clear_cache(self):
        """Test clearing cache"""
        # Make a request to populate cache
        self.provider.get_today_matches()
        
        # Clear cache
        self.provider.clear_cache()
        
        # Check cache is empty
        stats = self.provider.get_cache_stats()
        assert stats["total_files"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
