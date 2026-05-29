"""
Backtesting Script
Run historical backtest and generate report
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backtesting import BacktestingEngine
from app.services.backtesting.models import ConfidenceLevel


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_basic_backtest():
    """Run basic backtest with all matches"""
    
    print("\n" + "="*80)
    print("BACKTEST 1: Basic (All Matches)")
    print("="*80)
    
    # Create engine
    engine = BacktestingEngine()
    
    # Load historical matches
    print("\n📥 Loading historical matches...")
    matches = engine.load_historical_matches(count=150)
    print(f"✅ Loaded {len(matches)} matches")
    
    # Run backtest
    print("\n🔄 Running backtest...")
    results = engine.run_backtest(
        matches=matches,
        min_anomaly_score=55.0
    )
    
    # Print report
    engine.print_report()
    
    # Print chart
    engine.print_simple_chart()
    
    # Export
    engine.export_csv("backtest_basic.csv")
    print("\n💾 Exported to backtest_basic.csv")
    
    return results


def run_confidence_filtered_backtest():
    """Run backtest filtered by confidence"""
    
    print("\n" + "="*80)
    print("BACKTEST 2: High Confidence Only")
    print("="*80)
    
    engine = BacktestingEngine()
    matches = engine.load_historical_matches(count=150)
    
    print("\n🔄 Running backtest (HIGH confidence only)...")
    results = engine.run_backtest(
        matches=matches,
        min_anomaly_score=55.0,
        confidence_filter=ConfidenceLevel.HIGH
    )
    
    engine.print_report()
    engine.export_csv("backtest_high_conf.csv")
    print("\n💾 Exported to backtest_high_conf.csv")
    
    return results


def run_market_comparison():
    """Compare performance across markets"""
    
    print("\n" + "="*80)
    print("BACKTEST 3: Market Comparison")
    print("="*80)
    
    engine = BacktestingEngine()
    matches = engine.load_historical_matches(count=200)
    
    print("\n🔄 Running full backtest for market comparison...")
    results = engine.run_backtest(
        matches=matches,
        min_anomaly_score=50.0
    )
    
    print("\n📊 MARKET COMPARISON")
    print("="*80)
    
    if results.market_performance:
        print(f"\n{'Market':<20} {'Bets':<8} {'Wins':<8} {'Losses':<8} {'Win%':<8} {'ROI':<8}")
        print("-"*60)
        
        for market, perf in sorted(
            results.market_performance.items(),
            key=lambda x: x[1].roi,
            reverse=True
        ):
            print(f"{perf.market_type:<20} {perf.total_bets:<8} {perf.wins:<8} "
                  f"{perf.losses:<8} {perf.win_rate:<8.1f} {perf.roi:<8.1f}")
    
    return results


def run_roi_analysis():
    """Analyze ROI by different parameters"""
    
    print("\n" + "="*80)
    print("BACKTEST 4: ROI Analysis")
    print("="*80)
    
    engine = BacktestingEngine()
    matches = engine.load_historical_matches(count=200)
    
    print("\nTesting different anomaly score thresholds...")
    
    thresholds = [40, 50, 60, 70, 80]
    
    print(f"\n{'Threshold':<12} {'Bets':<8} {'Hit%':<8} {'ROI':<8}")
    print("-"*36)
    
    for threshold in thresholds:
        results = engine.run_backtest(
            matches=matches,
            min_anomaly_score=threshold
        )
        
        print(f"{threshold:<12} {results.total_bets:<8} {results.hit_rate:<8.1f} {results.roi:<8.1f}")
    
    print("\n💡 Finding optimal threshold...")
    print("  Lower threshold = More bets, potentially lower ROI")
    print("  Higher threshold = Fewer bets, potentially higher ROI")


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("🧪 BACKTESTING ENGINE - TESTS")
    print("="*80)
    print("\nThis script runs historical backtests")
    print("\nTests:")
    print("  1. Basic backtest (all matches)")
    print("  2. High confidence filter")
    print("  3. Market comparison")
    print("  4. ROI analysis")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    # Run tests
    tests = [
        ("Basic Backtest", run_basic_backtest),
        ("High Confidence", run_confidence_filtered_backtest),
        ("Market Comparison", run_market_comparison),
        ("ROI Analysis", run_roi_analysis)
    ]
    
    for name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"Running: {name}")
            print(f"{'='*80}")
            test_func()
        except Exception as e:
            logger.error(f"Test {name} failed: {e}", exc_info=True)
            print(f"\n❌ Test failed: {name}")
    
    print("\n" + "="*80)
    print("✅ BACKTESTING COMPLETE")
    print("="*80)
    print("\nFiles generated:")
    print("  - backtest_basic.csv")
    print("  - backtest_high_conf.csv")
    print("  - backtest_results.json")
    print("\nReview CSV files for detailed bet history")
    
    return 0


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
