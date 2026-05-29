"""
Market Performance Report
Generate comprehensive market comparison report

Usage:
    python scripts/market_performance_report.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backtesting import BacktestingEngine
from app.services.backtesting.models import BetOutcome
from app.services.analysis.market_performance_analyzer import MarketPerformanceAnalyzer


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_full_report():
    """Run complete market performance analysis"""
    
    print("\n" + "=" * 80)
    print("MARKET PERFORMANCE REPORT")
    print("=" * 80)
    
    # Step 1: Run backtest for multiple markets
    print("\n📊 Step 1: Running backtests across markets...")
    
    engine = BacktestingEngine()
    
    # Run multiple backtests for different markets
    results = []
    
    markets = ["ft_under_25", "ht_under_05", "ht_under_15", "btts", "ft_over_25"]
    
    for market in markets:
        print(f"   Testing {market}...")
        
        # Generate matches
        matches = engine.load_historical_matches(count=100)
        
        # Run backtest
        result = engine.run_backtest(
            matches=matches,
            min_anomaly_score=50.0
        )
        
        # Override market type for classification
        for bet in result.bets:
            bet.market_type = market
        
        results.append(result)
        
        print(f"     Bets: {result.total_bets}, Wins: {result.total_wins}, "
              f"Hit: {result.hit_rate:.1f}%, ROI: {result.roi:.1f}%")
    
    # Step 2: Analyze markets
    print("\n🔍 Step 2: Analyzing market performance...")
    
    analyzer = MarketPerformanceAnalyzer()
    ranking = analyzer.analyze_markets(results, min_bets=5)
    
    # Step 3: Print report
    print("\n📈 Step 3: Generating report...")
    analyzer.print_report(ranking)
    
    # Step 4: Exploitable markets
    print("\n🎯 EXPLOITABLE MARKETS (Score ≥ 60)")
    print("-" * 80)
    
    exploitable = analyzer.get_exploitable_markets(ranking, min_exploitability=60.0)
    
    if exploitable:
        for m in exploitable:
            print(f"  ✅ {m.market_type:<20} "
                  f"Exploit: {m.exploitability_score:.0f}/100 | "
                  f"Hit: {m.hit_rate:.1f}% | ROI: {m.roi:.1f}%")
    else:
        print("  ⚠️  No markets meet exploitability criteria")
    
    # Step 5: Avoid markets
    print("\n🚫 MARKETS TO AVOID")
    print("-" * 80)
    
    avoid = analyzer.get_avoid_markets(ranking)
    
    if avoid:
        for m in avoid:
            print(f"  ❌ {m.market_type:<20} "
                  f"Exploit: {m.exploitability_score:.0f}/100 | "
                  f"Hit: {m.hit_rate:.1f}% | ROI: {m.roi:.1f}%")
    else:
        print("  ✅ No markets to avoid")
    
    # Step 6: Export JSON
    import json
    
    with open("market_performance_report.json", 'w') as f:
        json.dump(ranking.to_dict(), f, indent=2)
    
    print("\n💾 Exported to: market_performance_report.json")
    
    return ranking


def main():
    """Main entry point"""
    
    print("\n" + "=" * 80)
    print("📊 MARKET PERFORMANCE ANALYSIS SYSTEM")
    print("=" * 80)
    print("\nComparing performance across market types:")
    print("  - HT Under / HT Over")
    print("  - FT Under / FT Over")
    print("  - BTTS")
    print("  - Extreme Under")
    print("=" * 80)
    
    input("\nPress ENTER to start...")
    
    try:
        ranking = run_full_report()
        return 0
    except Exception as e:
        logger.error(f"Report failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
