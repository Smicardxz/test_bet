"""
Test Scanner with Real Data
Test the complete scanner pipeline with real SofaScore data

Usage:
    # With real data
    DATA_PROVIDER=sofascore python scripts/test_scanner_real_data.py
    
    # With mock data
    python scripts/test_scanner_real_data.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main test function"""
    
    print("\n" + "=" * 80)
    print("🧪 SCANNER REAL DATA TEST")
    print("=" * 80)
    
    # Check configuration
    config = DataSourceConfig()
    print(f"\n📊 Configuration:")
    print(f"   DATA_PROVIDER: {config.source_type.value}")
    print(f"   Source Label: {config.source_label}")
    print(f"   Cache Enabled: {config.cache_enabled}")
    
    if config.is_mock_data:
        print(f"\n⚠️  WARNING: Using MOCK DATA")
        print(f"   To use real data, run with:")
        print(f"   DATA_PROVIDER=sofascore python scripts/test_scanner_real_data.py")
    else:
        print(f"\n✅ Using REAL DATA from {config.source_label}")
    
    print("\n" + "=" * 80)
    input("\nPress ENTER to start scan...")
    
    try:
        # Initialize
        add_provider_support_to_stats_engine()
        manager = DataSourceManager()
        
        source_tag = "REAL" if manager.is_real_data else "MOCK"
        print(f"\n[{source_tag}] Initializing scanner...")
        
        scanner = DailyScannerServiceV2(
            manager.provider,
            is_real_data=manager.is_real_data
        )
        
        print(f"[{source_tag}] Scanner initialized")
        print(f"[{source_tag}] Provider: {manager.provider.config.name}")
        
        # Run scan
        print(f"\n[{source_tag}] Starting daily scan...")
        print("-" * 80)
        
        results = scanner.scan_today(max_results=20)
        
        # Get statistics
        stats = scanner.get_scan_statistics()
        
        print("\n" + "=" * 80)
        print("📊 SCAN STATISTICS")
        print("=" * 80)
        print(f"\n   Matches Fetched: {stats.matches_fetched}")
        print(f"   Matches Analyzable: {stats.matches_analyzable}")
        print(f"   Ignored (No Odds): {stats.ignored_no_odds}")
        print(f"   Ignored (No History): {stats.ignored_no_history}")
        print(f"   Ignored (Low Quality): {stats.ignored_low_quality}")
        print(f"   Provider Errors: {stats.provider_errors}")
        print(f"   Total Anomalies: {stats.total_anomalies}")
        
        print("\n" + "=" * 80)
        print("🎯 ANOMALY RESULTS")
        print("=" * 80)
        
        if not results:
            print(f"\n[{source_tag}] No anomalies detected")
            
            if stats.ignored_no_odds > 0:
                print(f"\n⚠️  {stats.ignored_no_odds} matches ignored due to missing odds")
                if manager.is_real_data:
                    print("   In REAL mode, matches without odds are skipped.")
                    print("   Consider using an odds provider or switching to mock mode for testing.")
            
            if stats.ignored_no_history > 0:
                print(f"\n⚠️  {stats.ignored_no_history} matches ignored due to missing history")
            
            return 0
        
        print(f"\n[{source_tag}] Found {len(results)} anomalies")
        
        # Display top results
        print("\n" + "-" * 80)
        for i, result in enumerate(results[:5], 1):
            print(f"\n   #{i} {result.home_team} vs {result.away_team}")
            print(f"       League: {result.league}")
            print(f"       Market: {result.market_type}")
            print(f"       Line: {result.line}")
            print(f"       Anomaly Score: {result.anomaly_result.anomaly_score if result.anomaly_result else 'N/A'}")
            print(f"       Data Quality: {result.data_quality_score:.2f}")
            print(f"       Home Sample: {result.home_sample_size}")
            print(f"       Away Sample: {result.away_sample_size}")
            print(f"       H2H: {'Yes' if result.h2h_available else 'No'}")
            print(f"       Bookmaker Odds: {result.bookmaker_odds}")
        
        if len(results) > 5:
            print(f"\n   ... and {len(results) - 5} more")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ SCAN COMPLETE")
        print("=" * 80)
        
        print(f"\n   Data Source: {source_tag}")
        print(f"   Total Results: {len(results)}")
        print(f"   Success Rate: {(stats.matches_analyzable / stats.matches_fetched * 100) if stats.matches_fetched > 0 else 0:.1f}%")
        
        if manager.is_real_data:
            print(f"\n   ✅ Real data pipeline working!")
            if stats.ignored_no_odds > 0:
                print(f"   ℹ️  Some matches skipped due to missing odds (expected in real mode)")
        else:
            print(f"\n   ℹ️  Mock data pipeline working (use DATA_PROVIDER=sofascore for real)")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        return 1
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
