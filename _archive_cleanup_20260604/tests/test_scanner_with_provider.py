"""
Tests for DailyScannerServiceV2 with DataProvider
"""

import pytest
from datetime import datetime

from app.providers import MockDataProvider
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2, MarketPriority
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


class TestDailyScannerWithProvider:
    """Test DailyScannerServiceV2 with MockProvider"""
    
    def setup_method(self):
        """Setup test scanner"""
        # Ensure provider adapter is loaded
        add_provider_support_to_stats_engine()
        
        # Create mock provider
        self.provider = MockDataProvider()
        
        # Create scanner
        self.scanner = DailyScannerServiceV2(self.provider)
    
    def test_scanner_initialization(self):
        """Test scanner initializes correctly"""
        assert self.scanner.provider is not None
        assert self.scanner.stats_engine is not None
        assert self.scanner.anomaly_engine is not None
        assert self.scanner.min_sample_size == 8
        assert self.scanner.min_anomaly_score == 50.0
    
    def test_scan_today_basic(self):
        """Test basic scan functionality"""
        results = self.scanner.scan_today()
        
        # Should return results
        assert isinstance(results, list)
        
        # Results should have required fields
        if results:
            result = results[0]
            assert hasattr(result, 'match_id')
            assert hasattr(result, 'home_team')
            assert hasattr(result, 'away_team')
            assert hasattr(result, 'market_type')
            assert hasattr(result, 'anomaly_result')
            assert hasattr(result, 'data_quality_score')
            assert hasattr(result, 'final_score')
            assert hasattr(result, 'rank')
    
    def test_scan_with_competition_filter(self):
        """Test scanning with competition filter"""
        results = self.scanner.scan_today(
            competition_ids=["eng_women_champ"]
        )
        
        assert isinstance(results, list)
        
        # All results should be from filtered competition
        for result in results:
            assert "women" in result.league.lower() or "championship" in result.league.lower()
    
    def test_scan_with_max_results(self):
        """Test limiting results"""
        results = self.scanner.scan_today(max_results=5)
        
        assert len(results) <= 5
    
    def test_results_are_ranked(self):
        """Test results are properly ranked"""
        results = self.scanner.scan_today()
        
        if len(results) > 1:
            # Check ranks are sequential
            for i, result in enumerate(results, 1):
                assert result.rank == i
            
            # Check scores are descending
            for i in range(len(results) - 1):
                assert results[i].final_score >= results[i + 1].final_score
    
    def test_data_quality_scores(self):
        """Test data quality scores are calculated"""
        results = self.scanner.scan_today()
        
        for result in results:
            assert 0.0 <= result.data_quality_score <= 1.0
            assert result.home_sample_size >= 0
            assert result.away_sample_size >= 0
    
    def test_market_priorities(self):
        """Test market priorities are assigned"""
        results = self.scanner.scan_today()
        
        for result in results:
            assert result.market_priority in [
                MarketPriority.CRITICAL,
                MarketPriority.HIGH,
                MarketPriority.MEDIUM,
                MarketPriority.LOW
            ]
    
    def test_anomaly_results_present(self):
        """Test anomaly results are included"""
        results = self.scanner.scan_today()
        
        for result in results:
            if result.anomaly_result:
                assert hasattr(result.anomaly_result, 'anomaly_score')
                assert hasattr(result.anomaly_result, 'confidence_category')
                assert hasattr(result.anomaly_result, 'confidence_score')
    
    def test_filtering_weak_anomalies(self):
        """Test weak anomalies are filtered out"""
        results = self.scanner.scan_today()
        
        for result in results:
            if result.anomaly_result:
                # Should meet minimum thresholds
                assert result.anomaly_result.anomaly_score >= self.scanner.min_anomaly_score
                
                # Should have minimum sample size
                min_sample = min(result.home_sample_size, result.away_sample_size)
                assert min_sample >= self.scanner.min_sample_size
    
    def test_summary_generation(self):
        """Test summary statistics generation"""
        results = self.scanner.scan_today()
        summary = self.scanner.get_summary(results)
        
        assert "total_results" in summary
        assert "by_priority" in summary
        assert "by_confidence" in summary
        assert "avg_anomaly_score" in summary
        assert "avg_data_quality" in summary
        assert "provider" in summary
        
        assert summary["total_results"] == len(results)
        assert summary["provider"] == "mock"
    
    def test_result_to_dict(self):
        """Test result serialization"""
        results = self.scanner.scan_today()
        
        if results:
            result_dict = results[0].to_dict()
            
            assert isinstance(result_dict, dict)
            assert "match_id" in result_dict
            assert "home_team" in result_dict
            assert "market_type" in result_dict
            assert "final_score" in result_dict
    
    def test_handles_missing_odds(self):
        """Test scanner handles missing odds gracefully"""
        # Scanner should use default odds when provider odds unavailable
        results = self.scanner.scan_today()
        
        # Should still return results even if some odds missing
        assert isinstance(results, list)
    
    def test_handles_insufficient_data(self):
        """Test scanner handles insufficient data"""
        # With mock provider, should have sufficient data
        # But test that low quality data is filtered
        
        results = self.scanner.scan_today()
        
        for result in results:
            # All returned results should meet quality threshold
            assert result.data_quality_score >= self.scanner.min_data_quality
    
    def test_provider_metadata(self):
        """Test provider metadata is included"""
        results = self.scanner.scan_today()
        
        for result in results:
            assert result.provider == "mock"
            assert result.scan_timestamp != ""
    
    def test_market_config(self):
        """Test market configuration"""
        config = self.scanner.market_config
        
        # Should have priority markets
        assert "ht_under_05" in config
        assert "ft_under_25" in config
        assert "btts" in config
        
        # Each market should have required fields
        for market, info in config.items():
            assert "priority" in info
            assert "weight" in info


class TestScannerEdgeCases:
    """Test edge cases and error handling"""
    
    def setup_method(self):
        """Setup test scanner"""
        add_provider_support_to_stats_engine()
        self.provider = MockDataProvider()
        self.scanner = DailyScannerServiceV2(self.provider)
    
    def test_empty_matches(self):
        """Test handling of empty match list"""
        # This would require mocking provider to return empty list
        # For now, just ensure scanner doesn't crash
        results = self.scanner.scan_today(competition_ids=["nonexistent"])
        assert isinstance(results, list)
    
    def test_custom_thresholds(self):
        """Test scanner with custom thresholds"""
        self.scanner.min_anomaly_score = 70.0
        self.scanner.min_sample_size = 12
        
        results = self.scanner.scan_today()
        
        # Results should meet higher thresholds
        for result in results:
            if result.anomaly_result:
                assert result.anomaly_result.anomaly_score >= 70.0
            
            min_sample = min(result.home_sample_size, result.away_sample_size)
            assert min_sample >= 12
    
    def test_max_results_limit(self):
        """Test max results configuration"""
        self.scanner.max_results = 3
        results = self.scanner.scan_today()
        
        assert len(results) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
