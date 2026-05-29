"""
Unit tests for DailyScannerService
Tests scanner logic and filtering
"""

import pytest
from datetime import datetime
from app.services.scanner.daily_scanner import (
    DailyScannerService,
    ScanResult,
    MarketPriority
)


class TestMarketPriority:
    """Test MarketPriority enum"""
    
    def test_priority_values(self):
        """Test priority values"""
        assert MarketPriority.CRITICAL.value == "CRITICAL"
        assert MarketPriority.HIGH.value == "HIGH"
        assert MarketPriority.MEDIUM.value == "MEDIUM"
        assert MarketPriority.LOW.value == "LOW"


class TestScanResult:
    """Test ScanResult dataclass"""
    
    def test_scan_result_creation(self):
        """Test creating scan result"""
        result = ScanResult(
            match_id=1,
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            match_date="2026-05-27T15:00:00",
            market_type="ft_under_25",
            market_priority=MarketPriority.HIGH,
            line=2.5,
            final_score=75.5,
            rank=1,
            scan_timestamp=datetime.utcnow().isoformat()
        )
        
        assert result.match_id == 1
        assert result.home_team == "Team A"
        assert result.market_priority == MarketPriority.HIGH
        assert result.final_score == 75.5
    
    def test_to_dict(self):
        """Test conversion to dict"""
        result = ScanResult(
            match_id=1,
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            match_date="2026-05-27T15:00:00",
            market_type="ft_under_25",
            market_priority=MarketPriority.HIGH,
            line=2.5
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == 1
        assert result_dict["market_priority"] == "HIGH"
    
    def test_to_json(self):
        """Test conversion to JSON"""
        result = ScanResult(
            match_id=1,
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            match_date="2026-05-27T15:00:00",
            market_type="btts",
            market_priority=MarketPriority.MEDIUM
        )
        
        result_json = result.to_json()
        
        assert isinstance(result_json, dict)
        # Should be JSON serializable
        import json
        json_str = json.dumps(result_json)
        assert isinstance(json_str, str)


class TestDailyScannerService:
    """Test DailyScannerService class"""
    
    def test_get_priority_bonus(self):
        """Test priority bonus calculation"""
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        scanner = DailyScannerService(db)
        
        assert scanner._get_priority_bonus(MarketPriority.CRITICAL) == 100.0
        assert scanner._get_priority_bonus(MarketPriority.HIGH) == 75.0
        assert scanner._get_priority_bonus(MarketPriority.MEDIUM) == 50.0
        assert scanner._get_priority_bonus(MarketPriority.LOW) == 25.0
        
        db.close()
    
    def test_market_config(self):
        """Test market configuration"""
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        scanner = DailyScannerService(db)
        
        config = scanner._get_market_config()
        
        # Check CRITICAL markets
        assert config["ht_under_05"]["priority"] == MarketPriority.CRITICAL
        assert config["ft_under_105"]["priority"] == MarketPriority.CRITICAL
        
        # Check HIGH markets
        assert config["ft_under_25"]["priority"] == MarketPriority.HIGH
        assert config["ft_over_25"]["priority"] == MarketPriority.HIGH
        
        # Check MEDIUM markets
        assert config["btts"]["priority"] == MarketPriority.MEDIUM
        
        # Check lines
        assert config["ft_under_25"]["line"] == 2.5
        assert config["ht_under_05"]["line"] == 0.5
        assert config["btts"]["line"] is None
        
        db.close()
    
    def test_generate_summary_empty(self):
        """Test summary generation with empty results"""
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        scanner = DailyScannerService(db)
        
        summary = scanner.generate_summary([])
        
        assert summary["total_anomalies"] == 0
        assert summary["total_matches"] == 0
        assert summary["avg_anomaly_score"] == 0.0
        
        db.close()
    
    def test_generate_summary_with_results(self):
        """Test summary generation with results"""
        from app.db.session import SessionLocal
        from app.services.anomaly import AnomalyResult, ConfidenceCategory
        
        db = SessionLocal()
        scanner = DailyScannerService(db)
        
        # Create mock results
        results = [
            ScanResult(
                match_id=1,
                home_team="Team A",
                away_team="Team B",
                league="League 1",
                match_date="2026-05-27T15:00:00",
                market_type="ft_under_25",
                market_priority=MarketPriority.HIGH,
                line=2.5,
                anomaly_result=AnomalyResult(
                    match_id=1,
                    market_type="ft_under_25",
                    line=2.5,
                    anomaly_score=75.0,
                    confidence_score=0.80,
                    confidence_category=ConfidenceCategory.HIGH
                )
            ),
            ScanResult(
                match_id=2,
                home_team="Team C",
                away_team="Team D",
                league="League 1",
                match_date="2026-05-27T16:00:00",
                market_type="ht_under_05",
                market_priority=MarketPriority.CRITICAL,
                line=0.5,
                anomaly_result=AnomalyResult(
                    match_id=2,
                    market_type="ht_under_05",
                    line=0.5,
                    anomaly_score=85.0,
                    confidence_score=0.75,
                    confidence_category=ConfidenceCategory.HIGH
                )
            )
        ]
        
        summary = scanner.generate_summary(results)
        
        assert summary["total_anomalies"] == 2
        assert summary["total_matches"] == 2
        assert summary["avg_anomaly_score"] == 80.0
        assert summary["avg_confidence_score"] == 0.775
        assert "HIGH" in summary["by_priority"]
        assert "CRITICAL" in summary["by_priority"]
        
        db.close()


class TestRanking:
    """Test ranking logic"""
    
    def test_ranking_order(self):
        """Test that results are ranked correctly"""
        from app.db.session import SessionLocal
        from app.services.anomaly import AnomalyResult, ConfidenceCategory
        
        db = SessionLocal()
        scanner = DailyScannerService(db)
        
        # Create results with different scores
        results = [
            ScanResult(
                match_id=1,
                home_team="Team A",
                away_team="Team B",
                league="League 1",
                match_date="2026-05-27T15:00:00",
                market_type="ft_under_25",
                market_priority=MarketPriority.HIGH,
                anomaly_result=AnomalyResult(
                    match_id=1,
                    market_type="ft_under_25",
                    anomaly_score=60.0,
                    confidence_score=0.60,
                    confidence_category=ConfidenceCategory.MEDIUM,
                    data_quality=0.9
                )
            ),
            ScanResult(
                match_id=2,
                home_team="Team C",
                away_team="Team D",
                league="League 1",
                match_date="2026-05-27T16:00:00",
                market_type="ht_under_05",
                market_priority=MarketPriority.CRITICAL,
                anomaly_result=AnomalyResult(
                    match_id=2,
                    market_type="ht_under_05",
                    anomaly_score=85.0,
                    confidence_score=0.85,
                    confidence_category=ConfidenceCategory.HIGH,
                    data_quality=1.0
                )
            ),
            ScanResult(
                match_id=3,
                home_team="Team E",
                away_team="Team F",
                league="League 1",
                match_date="2026-05-27T17:00:00",
                market_type="btts",
                market_priority=MarketPriority.MEDIUM,
                anomaly_result=AnomalyResult(
                    match_id=3,
                    market_type="btts",
                    anomaly_score=70.0,
                    confidence_score=0.70,
                    confidence_category=ConfidenceCategory.MEDIUM,
                    data_quality=0.85
                )
            )
        ]
        
        # Rank results
        ranked = scanner._rank_results(results)
        
        # Check that highest score is first
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3
        
        # CRITICAL priority with high score should be first
        assert ranked[0].market_priority == MarketPriority.CRITICAL
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
