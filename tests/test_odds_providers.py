"""
Tests for Odds Providers
"""

import pytest
from datetime import datetime

from app.providers.odds import (
    MockOddsProvider,
    OddsProviderConfig,
    MarketType,
    OddsData
)


class TestOddsModels:
    """Test odds data models"""
    
    def test_odds_data_creation(self):
        """Test creating OddsData"""
        odds = OddsData(
            match_id="123",
            market_type=MarketType.FT_UNDER_25,
            line=2.5,
            odd=1.85,
            bookmaker="Bet365"
        )
        
        assert odds.match_id == "123"
        assert odds.market_type == MarketType.FT_UNDER_25
        assert odds.line == 2.5
        assert odds.odd == 1.85
        assert odds.bookmaker == "Bet365"
        assert isinstance(odds.timestamp, datetime)
    
    def test_odds_data_without_line(self):
        """Test OddsData for markets without line (e.g., BTTS)"""
        odds = OddsData(
            match_id="123",
            market_type=MarketType.BTTS_YES,
            odd=2.00,
            bookmaker="Pinnacle"
        )
        
        assert odds.line is None
        assert odds.market_type == MarketType.BTTS_YES


class TestMockOddsProvider:
    """Test MockOddsProvider"""
    
    def setup_method(self):
        """Setup test provider"""
        self.provider = MockOddsProvider()
    
    def test_provider_initialization(self):
        """Test provider initializes correctly"""
        assert self.provider.config.name == "mock_odds"
        assert self.provider.config.enabled is True
    
    def test_get_match_odds(self):
        """Test getting odds for a match"""
        response = self.provider.get_match_odds("match_001")
        
        assert response.success is True
        assert response.data is not None
        assert len(response.data) > 0
        assert response.provider == "mock_odds"
    
    def test_get_match_odds_specific_markets(self):
        """Test getting odds for specific markets"""
        markets = [
            MarketType.FT_UNDER_25,
            MarketType.HT_UNDER_05,
            MarketType.BTTS_YES
        ]
        
        response = self.provider.get_match_odds("match_001", markets=markets)
        
        assert response.success is True
        assert len(response.data) == len(markets)
        
        # Check all requested markets are present
        returned_markets = [odd.market_type for odd in response.data]
        for market in markets:
            assert market in returned_markets
    
    def test_get_today_odds(self):
        """Test getting odds for today's matches"""
        response = self.provider.get_today_odds()
        
        assert response.success is True
        assert response.data is not None
        assert len(response.data) > 0
    
    def test_odds_values_realistic(self):
        """Test that generated odds are realistic"""
        response = self.provider.get_match_odds("match_001")
        
        for odd in response.data:
            # Odds should be positive
            assert odd.odd > 0
            
            # Odds should be reasonable (between 1.01 and 10.0)
            assert 1.01 <= odd.odd <= 10.0
            
            # Check line values are correct
            if odd.market_type == MarketType.FT_UNDER_25:
                assert odd.line == 2.5
            elif odd.market_type == MarketType.HT_UNDER_05:
                assert odd.line == 0.5
            elif odd.market_type in [MarketType.BTTS_YES, MarketType.BTTS_NO]:
                assert odd.line is None
    
    def test_priority_markets(self):
        """Test priority markets configuration"""
        markets = self.provider.get_priority_markets()
        
        assert len(markets) > 0
        
        # Should include critical markets
        assert MarketType.HT_UNDER_05 in markets
        assert MarketType.FT_UNDER_25 in markets
        assert MarketType.BTTS_YES in markets
    
    def test_generate_anomaly_odds_overvalued(self):
        """Test generating overvalued anomaly odds"""
        normal_response = self.provider.get_match_odds("match_001", [MarketType.FT_UNDER_25])
        normal_odd = normal_response.data[0].odd
        
        anomaly_odd = self.provider.generate_anomaly_odds(
            "match_001",
            MarketType.FT_UNDER_25,
            anomaly_type="overvalued"
        )
        
        # Anomaly odd should be higher (overvalued)
        assert anomaly_odd.odd > normal_odd
        assert anomaly_odd.market_type == MarketType.FT_UNDER_25
    
    def test_generate_anomaly_odds_undervalued(self):
        """Test generating undervalued anomaly odds"""
        normal_response = self.provider.get_match_odds("match_001", [MarketType.FT_UNDER_25])
        normal_odd = normal_response.data[0].odd
        
        anomaly_odd = self.provider.generate_anomaly_odds(
            "match_001",
            MarketType.FT_UNDER_25,
            anomaly_type="undervalued"
        )
        
        # Anomaly odd should be lower (undervalued)
        assert anomaly_odd.odd < normal_odd
    
    def test_different_bookmakers(self):
        """Test that different bookmakers are used"""
        response = self.provider.get_today_odds()
        
        bookmakers = set(odd.bookmaker for odd in response.data)
        
        # Should have multiple bookmakers
        assert len(bookmakers) > 1


class TestOddsProviderConfig:
    """Test OddsProviderConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = OddsProviderConfig(name="test")
        
        assert config.name == "test"
        assert config.enabled is True
        assert config.fetch_ft_under_over is True
        assert config.fetch_ht_under_over is True
        assert config.fetch_btts is True
        assert config.fetch_extreme_under is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = OddsProviderConfig(
            name="custom",
            enabled=False,
            fetch_ft_under_over=True,
            fetch_ht_under_over=False,
            fetch_btts=True,
            fetch_extreme_under=False
        )
        
        assert config.enabled is False
        assert config.fetch_ht_under_over is False
        assert config.fetch_extreme_under is False


class TestMarketTypes:
    """Test market type definitions"""
    
    def test_all_market_types_defined(self):
        """Test all expected market types are defined"""
        expected_markets = [
            "ft_under_15", "ft_over_15",
            "ft_under_25", "ft_over_25",
            "ft_under_35", "ft_over_35",
            "ht_under_05", "ht_over_05",
            "ft_under_85", "ft_under_105",
            "btts_yes", "btts_no"
        ]
        
        for market in expected_markets:
            assert hasattr(MarketType, market.upper())
    
    def test_market_type_values(self):
        """Test market type enum values"""
        assert MarketType.FT_UNDER_25.value == "ft_under_25"
        assert MarketType.HT_UNDER_05.value == "ht_under_05"
        assert MarketType.BTTS_YES.value == "btts_yes"


class TestOddsIntegration:
    """Test odds provider integration scenarios"""
    
    def setup_method(self):
        """Setup test provider"""
        self.provider = MockOddsProvider()
    
    def test_odds_for_anomaly_detection(self):
        """Test getting odds suitable for anomaly detection"""
        # Get odds for critical markets
        critical_markets = [
            MarketType.HT_UNDER_05,
            MarketType.FT_UNDER_25,
            MarketType.FT_UNDER_85
        ]
        
        response = self.provider.get_match_odds("match_001", markets=critical_markets)
        
        assert response.success is True
        assert len(response.data) == len(critical_markets)
        
        # All odds should have required fields for anomaly detection
        for odd in response.data:
            assert odd.match_id is not None
            assert odd.market_type is not None
            assert odd.odd > 0
            assert odd.bookmaker is not None
    
    def test_missing_odds_handling(self):
        """Test handling when no odds available"""
        # Request markets that might not be available
        response = self.provider.get_match_odds("nonexistent_match", markets=[])
        
        # Should return success with empty list
        assert response.success is True
        assert response.data == []
    
    def test_odds_timestamp(self):
        """Test odds have recent timestamp"""
        response = self.provider.get_match_odds("match_001")
        
        for odd in response.data:
            # Timestamp should be recent (within last minute)
            age = (datetime.utcnow() - odd.timestamp).total_seconds()
            assert age < 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
