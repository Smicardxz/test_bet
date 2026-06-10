"""
Tests for Market Performance Analyzer
"""

import pytest
from datetime import datetime

from app.services.analysis.market_performance_analyzer import (
    MarketPerformanceAnalyzer,
    MarketPerformanceMetrics,
    MarketRanking,
    MarketCategory
)
from app.services.backtesting.models import BacktestBet, BetOutcome, ConfidenceLevel


class TestMarketPerformanceAnalyzer:
    """Test MarketPerformanceAnalyzer"""
    
    def setup_method(self):
        """Setup test analyzer"""
        self.analyzer = MarketPerformanceAnalyzer()
    
    def _create_bet(self, market: str, outcome: BetOutcome, confidence: str = "HIGH", odds: float = 1.85) -> BacktestBet:
        """Helper to create test bet"""
        conf = ConfidenceLevel(confidence)
        return BacktestBet(
            match_id="test",
            market_type=market,
            line=2.5,
            predicted_outcome="under",
            confidence=conf,
            odds=odds,
            stake=1.0,
            actual_outcome="under",
            result=outcome,
            profit_loss=0.85 if outcome == BetOutcome.WIN else -1.0 if outcome == BetOutcome.LOSS else 0.0
        )
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes"""
        assert self.analyzer is not None
    
    def test_single_market_analysis(self):
        """Test analyzing a single market"""
        bets = [
            self._create_bet("ft_under_25", BetOutcome.WIN),
            self._create_bet("ft_under_25", BetOutcome.WIN),
            self._create_bet("ft_under_25", BetOutcome.LOSS),
            self._create_bet("ft_under_25", BetOutcome.WIN),
            self._create_bet("ft_under_25", BetOutcome.LOSS),
        ]
        
        metric = self.analyzer._analyze_single_market("ft_under_25", bets)
        
        assert metric.market_type == "ft_under_25"
        assert metric.total_bets == 5
        assert metric.wins == 3
        assert metric.losses == 2
        assert metric.hit_rate == 60.0
        assert metric.roi > 0
    
    def test_market_categorization(self):
        """Test market categorization"""
        
        assert self.analyzer._categorize_market("ft_under_25") == MarketCategory.FT_UNDER
        assert self.analyzer._categorize_market("ht_under_05") == MarketCategory.HT_UNDER
        assert self.analyzer._categorize_market("btts_yes") == MarketCategory.BTTS_YES
        assert self.analyzer._categorize_market("ft_under_125") == MarketCategory.EXTREME_UNDER
    
    def test_exploitability_calculation(self):
        """Test exploitability score calculation"""
        
        metric = MarketPerformanceMetrics(
            market_type="ft_under_25",
            category=MarketCategory.FT_UNDER,
            total_bets=20,
            wins=15,
            losses=5,
            hit_rate=75.0,
            roi=25.0,
            high_conf_bets=10,
            high_conf_wins=8,
            high_conf_hit_rate=80.0,
            false_positive_rate=15.0
        )
        
        score = self.analyzer._calculate_exploitability(metric)
        
        assert score > 60  # Should be highly exploitable
        assert score <= 100
    
    def test_exploitability_low_performance(self):
        """Test exploitability with poor performance"""
        
        metric = MarketPerformanceMetrics(
            market_type="ft_over_25",
            category=MarketCategory.FT_OVER,
            total_bets=20,
            wins=5,
            losses=15,
            hit_rate=25.0,
            roi=-30.0,
            high_conf_bets=10,
            high_conf_wins=2,
            high_conf_hit_rate=20.0,
            false_positive_rate=60.0
        )
        
        score = self.analyzer._calculate_exploitability(metric)
        
        assert score < 40  # Should be low
    
    def test_market_ranking(self):
        """Test market ranking"""
        
        metrics = [
            MarketPerformanceMetrics("ht_under_05", MarketCategory.HT_UNDER, hit_rate=80.0, roi=30.0, exploitability_score=85.0),
            MarketPerformanceMetrics("ft_under_25", MarketCategory.FT_UNDER, hit_rate=60.0, roi=10.0, exploitability_score=65.0),
            MarketPerformanceMetrics("btts_yes", MarketCategory.BTTS_YES, hit_rate=40.0, roi=-15.0, exploitability_score=25.0),
        ]
        
        ranking = self.analyzer._rank_markets(metrics)
        
        assert len(ranking.markets) == 3
        assert ranking.best_market == "ht_under_05"
        assert ranking.worst_market == "btts_yes"
        assert ranking.markets[0].exploitability_score == 85.0
    
    def test_get_exploitable_markets(self):
        """Test filtering exploitable markets"""
        
        metrics = [
            MarketPerformanceMetrics("ht_under_05", MarketCategory.HT_UNDER, total_bets=20, hit_rate=80.0, roi=30.0, exploitability_score=85.0),
            MarketPerformanceMetrics("ft_under_25", MarketCategory.FT_UNDER, total_bets=20, hit_rate=60.0, roi=10.0, exploitability_score=65.0),
            MarketPerformanceMetrics("btts_yes", MarketCategory.BTTS_YES, total_bets=20, hit_rate=40.0, roi=-15.0, exploitability_score=25.0),
        ]
        
        ranking = MarketRanking(markets=metrics)
        
        exploitable = self.analyzer.get_exploitable_markets(ranking, min_exploitability=60.0)
        
        assert len(exploitable) == 2
        assert "ht_under_05" in [m.market_type for m in exploitable]
        assert "ft_under_25" in [m.market_type for m in exploitable]
        assert "btts_yes" not in [m.market_type for m in exploitable]
    
    def test_get_avoid_markets(self):
        """Test filtering markets to avoid"""
        
        metrics = [
            MarketPerformanceMetrics("ht_under_05", MarketCategory.HT_UNDER, hit_rate=80.0, roi=30.0, exploitability_score=85.0),
            MarketPerformanceMetrics("ft_under_25", MarketCategory.FT_UNDER, hit_rate=60.0, roi=10.0, exploitability_score=65.0),
            MarketPerformanceMetrics("btts_yes", MarketCategory.BTTS_YES, hit_rate=40.0, roi=-15.0, exploitability_score=25.0),
        ]
        
        ranking = MarketRanking(markets=metrics)
        
        avoid = self.analyzer.get_avoid_markets(ranking)
        
        assert len(avoid) == 1
        assert avoid[0].market_type == "btts_yes"
    
    def test_recommendations(self):
        """Test recommendation generation"""
        
        metrics = [
            MarketPerformanceMetrics("ht_under_05", MarketCategory.HT_UNDER, total_bets=25, hit_rate=80.0, roi=30.0, exploitability_score=85.0, high_conf_bets=15, high_conf_wins=13, high_conf_hit_rate=86.7),
        ]
        
        ranking = self.analyzer._rank_markets(metrics)
        
        assert len(ranking.recommendations) > 0
        assert any("BEST" in r for r in ranking.recommendations)
    
    def test_metric_serialization(self):
        """Test metric serialization"""
        
        metric = MarketPerformanceMetrics(
            market_type="ft_under_25",
            category=MarketCategory.FT_UNDER,
            total_bets=20,
            wins=15,
            losses=5,
            hit_rate=75.0,
            roi=25.0,
            avg_odds=1.85,
            exploitability_score=85.0
        )
        
        metric_dict = metric.to_dict()
        
        assert isinstance(metric_dict, dict)
        assert metric_dict["market_type"] == "ft_under_25"
        assert metric_dict["hit_rate"] == 75.0
        assert metric_dict["exploitability_score"] == 85.0
    
    def test_ranking_serialization(self):
        """Test ranking serialization"""
        
        metrics = [
            MarketPerformanceMetrics("ht_under_05", MarketCategory.HT_UNDER, hit_rate=80.0, roi=30.0, exploitability_score=85.0),
        ]
        
        ranking = self.analyzer._rank_markets(metrics)
        
        ranking_dict = ranking.to_dict()
        
        assert isinstance(ranking_dict, dict)
        assert ranking_dict["best_market"] == "ht_under_05"
        assert len(ranking_dict["markets"]) == 1
        assert len(ranking_dict["recommendations"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
