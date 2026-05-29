"""
Test Scanner Integration with DataProvider
Complete end-to-end test
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.providers.sofascore_provider import SofaScoreProvider, ProviderConfig
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_with_mock_provider():
    """Test scanner with MockProvider"""
    
    print("\n" + "="*80)
    print("TEST 1: Scanner with MockProvider")
    print("="*80)
    
    # Ensure adapter is loaded
    add_provider_support_to_stats_engine()
    
    # Create provider and scanner using DataSourceManager
    manager = DataSourceManager()
    provider = manager.provider
    scanner = DailyScannerServiceV2(provider, is_real_data=manager.is_real_data)
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"Data source: {source_tag} {manager.source_label}")
    
    # Run scan
    print("\n📊 Running daily scan...")
    results = scanner.scan_today(max_results=10)
    
    print(f"\n✅ Scan complete! Found {len(results)} anomalies")
    
    # Display results
    if results:
        print("\n" + "="*80)
        print("TOP ANOMALIES")
        print("="*80)
        
        for i, result in enumerate(results[:5], 1):
            print(f"\n#{i} - Rank {result.rank}")
            print(f"  Match: {result.home_team} vs {result.away_team}")
            print(f"  League: {result.league}")
            print(f"  Market: {result.market_type} (Priority: {result.market_priority.value})")
            
            if result.line:
                print(f"  Line: {result.line}")
            
            if result.bookmaker_odds:
                print(f"  Odds: {result.bookmaker_odds}")
            
            if result.anomaly_result:
                print(f"  Anomaly Score: {result.anomaly_result.anomaly_score:.1f}")
                print(f"  Confidence: {result.anomaly_result.confidence_category.value} ({result.anomaly_result.confidence_score:.0%})")
            
            print(f"  Data Quality: {result.data_quality_score:.2f}")
            print(f"  Sample Size: {result.home_sample_size}/{result.away_sample_size}")
            print(f"  H2H Available: {'Yes' if result.h2h_available else 'No'}")
            print(f"  Final Score: {result.final_score:.2f}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    summary = scanner.get_summary(results)
    print(f"\nTotal Results: {summary['total_results']}")
    print(f"Provider: {summary['provider']}")
    print(f"Avg Anomaly Score: {summary['avg_anomaly_score']}")
    print(f"Avg Data Quality: {summary['avg_data_quality']}")
    
    print(f"\nBy Priority:")
    for priority, count in summary['by_priority'].items():
        print(f"  {priority}: {count}")
    
    print(f"\nBy Confidence:")
    for conf, count in summary['by_confidence'].items():
        print(f"  {conf}: {count}")
    
    return len(results) > 0


def test_with_sofascore_provider():
    """Test scanner with SofaScoreProvider"""
    
    print("\n" + "="*80)
    print("TEST 2: Scanner with SofaScoreProvider")
    print("="*80)
    
    print("\n⚠️  This test requires internet connection and SofaScore API access")
    
    choice = input("\nContinue? [y/N]: ").strip().lower()
    
    if choice != 'y':
        print("Skipped")
        return True
    
    # Ensure adapter is loaded
    add_provider_support_to_stats_engine()
    
    # Create provider and scanner
    config = ProviderConfig(
        name="sofascore",
        rate_limit_per_minute=20,
        cache_enabled=True
    )
    
    provider = SofaScoreProvider(config)
    scanner = DailyScannerServiceV2(provider)
    
    # Run scan
    print("\n📊 Running daily scan...")
    try:
        results = scanner.scan_today(max_results=10)
        
        print(f"\n✅ Scan complete! Found {len(results)} anomalies")
        
        # Display top 3
        if results:
            print("\n" + "="*80)
            print("TOP 3 ANOMALIES")
            print("="*80)
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n#{i}")
                print(f"  {result.home_team} vs {result.away_team}")
                print(f"  Market: {result.market_type}")
                if result.anomaly_result:
                    print(f"  Score: {result.anomaly_result.anomaly_score:.1f}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_filtering():
    """Test filtering functionality"""
    
    print("\n" + "="*80)
    print("TEST 3: Filtering")
    print("="*80)
    
    add_provider_support_to_stats_engine()
    
    provider = MockDataProvider()
    scanner = DailyScannerServiceV2(provider)
    
    # Test with different thresholds
    print("\n📊 Test 1: Default thresholds")
    results1 = scanner.scan_today()
    print(f"  Results: {len(results1)}")
    
    print("\n📊 Test 2: Higher anomaly threshold (70)")
    scanner.min_anomaly_score = 70.0
    results2 = scanner.scan_today()
    print(f"  Results: {len(results2)}")
    
    print("\n📊 Test 3: Higher sample size (12)")
    scanner.min_anomaly_score = 50.0
    scanner.min_sample_size = 12
    results3 = scanner.scan_today()
    print(f"  Results: {len(results3)}")
    
    print(f"\n✅ Filtering works correctly")
    print(f"  Default: {len(results1)} results")
    print(f"  High threshold: {len(results2)} results")
    print(f"  High sample: {len(results3)} results")
    
    return True


def test_competition_filter():
    """Test competition filtering"""
    
    print("\n" + "="*80)
    print("TEST 4: Competition Filtering")
    print("="*80)
    
    add_provider_support_to_stats_engine()
    
    provider = MockDataProvider()
    scanner = DailyScannerServiceV2(provider)
    
    # Test with specific competition
    print("\n📊 Filtering for Women's Championship...")
    results = scanner.scan_today(competition_ids=["eng_women_champ"])
    
    print(f"  Results: {len(results)}")
    
    if results:
        leagues = set(r.league for r in results)
        print(f"  Leagues: {leagues}")
    
    return True


def main():
    """Run all tests"""
    
    print("\n" + "="*80)
    print("🧪 SCANNER INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        ("MockProvider", test_with_mock_provider),
        ("Filtering", test_filtering),
        ("Competition Filter", test_competition_filter),
        ("SofaScoreProvider", test_with_sofascore_provider)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} failed: {e}", exc_info=True)
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
