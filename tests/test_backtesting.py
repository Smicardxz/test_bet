"""
Tests for Backtesting Engine
"""

import pytest
from datetime import datetime

from app.services.backtesting import BacktestingEngine
from app.services.backtesting.models import (
    BacktestMatch,
    BacktestBet,
    BetOutcome,
    ConfidenceLevel
)


class TestBacktestingEngine:
    """Test BacktestingEngine"""
    
    def setup_method(self):
        """Setup test engine"""
        self.engine = BacktestingEngine()
    
    def _create_test_matches(self, count: int = 20) -> list:
        """Create test matches"""
        matches = []
        
        for i in range(count):
            # Create matches with known outcomes
            # Under 2.5 will hit for most (low scoring leagues)
            ft_home = 1 if i % 3 != 0 else 2
            ft_away = 0 if i % 2 == 0 else 1
            ht_home = 0
            ht_away = 0
            
            match = BacktestMatch(
                match_id=f"test_{i}",
                home_team=f"Team {i}A",
                away_team=f"Team {i}B",
                league="Test League",
                match_date=datetime(2025, 8, 1 + i),
                ft_home_goals=ft_home,
                ft_away_goals=ft_away,
                ht_home_goals=ht_home,
                ht_away_goals=ht_away,
                ft_under_25=(ft_home + ft_away) < 2.5,
                ht_under_05=(ht_home + ht_away) < 0.5,
                ht_under_15=(ht_home + ht_away) < 1.5,
                btts=(ft_home > 0 and ft_away > 0),
                ft_under_25_odds=1.85,
                ht_under_05_odds=1.30,
                btts_yes_odds=2.00
            )
            matches.append(match)
        
        return matches
    
    def test_engine_initialization(self):
        """Test engine initializes"""
        assert self.engine is not None
        assert self.engine.anomaly_engine is not None
        assert self.engine.stats_engine is not None
    
    def test_load_historical_matches(self):
        """Test loading historical matches"""
        matches = self.engine.load_historical_matches(count=50)
        
        assert len(matches) == 50
        assert all(isinstance(m, BacktestMatch) for m in matches)
        assert matches[0].match_id is not None
    
    def test_run_backtest_basic(self):
        """Test basic backtest run"""
        matches = self._create_test_matches(30)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=40.0
        )
        
        assert results.total_matches == 30
        assert results.total_bets > 0
        assert results.hit_rate >= 0
        assert results.hit_rate <= 100
    
    def test_backtest_produces_bets(self):
        """Test that backtest produces bets"""
        matches = self._create_test_matches(50)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0  # Low threshold to ensure bets
        )
        
        assert len(results.bets) > 0
        assert all(isinstance(b, BacktestBet) for b in results.bets)
    
    def test_backtest_calculates_roi(self):
        """Test ROI calculation"""
        matches = self._create_test_matches(50)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # ROI should be calculable
        assert isinstance(results.roi, float)
        assert results.total_stake > 0
    
    def test_market_performance_tracking(self):
        """Test market performance tracking"""
        matches = self._create_test_matches(50)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # Should have market breakdown
        assert len(results.market_performance) > 0
        
        # Each market should have metrics
        for market, perf in results.market_performance.items():
            assert perf.total_bets > 0
            assert perf.win_rate >= 0
            assert perf.win_rate <= 100
    
    def test_confidence_filter(self):
        """Test confidence level filtering"""
        matches = self._create_test_matches(100)
        
        # Run with HIGH confidence filter
        results_high = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0,
            confidence_filter=ConfidenceLevel.HIGH
        )
        
        # Run without filter
        results_all = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # HIGH confidence should have fewer or equal bets
        assert results_high.total_bets <= results_all.total_bets
    
    def test_league_performance(self):
        """Test league performance tracking"""
        matches = self._create_test_matches(50)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # Should have league breakdown
        assert len(results.league_performance) > 0
    
    def test_csv_export(self):
        """Test CSV export"""
        import tempfile
        import os
        
        matches = self._create_test_matches(20)
        
        self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            self.engine.export_csv(temp_path)
            assert os.path.exists(temp_path)
            
            # Check content
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "Match ID" in content
                assert "Market" in content
        finally:
            os.unlink(temp_path)
    
    def test_json_export(self):
        """Test JSON export"""
        import tempfile
        import os
        import json
        
        matches = self._create_test_matches(20)
        
        self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.engine.export_json(temp_path)
            assert os.path.exists(temp_path)
            
            # Check valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert "summary" in data
        finally:
            os.unlink(temp_path)
    
    def test_result_serialization(self):
        """Test result serialization"""
        matches = self._create_test_matches(20)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        result_dict = results.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "summary" in result_dict
        assert "market_performance" in result_dict
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        matches = self._create_test_matches(50)
        
        results = self.engine.run_backtest(
            matches=matches,
            min_anomaly_score=30.0
        )
        
        if results.total_bets > 0:
            expected_hit_rate = (results.total_wins / results.total_bets) * 100
            assert abs(results.hit_rate - expected_hit_rate) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
