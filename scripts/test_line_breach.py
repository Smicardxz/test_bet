"""
Test Line Breach Engine
Demonstrate historical line breach analysis
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers import MockDataProvider
from app.services.stats import StatsEngine
from app.services.analysis import HistoricalLineBreachEngine
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_extreme_lines():
    """Test extreme line analysis"""
    
    print("\n" + "="*80)
    print("TEST 1: Extreme Lines Analysis")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    breach_engine = HistoricalLineBreachEngine()
    
    # Get match
    matches_response = data_provider.get_today_matches()
    if not matches_response.success:
        print("❌ No matches available")
        return False
    
    match = matches_response.data[0]
    
    # Get stats
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    print(f"\nMatch: {match.home_team.name} vs {match.away_team.name}")
    print(f"Home avg goals: {home_stats.avg_total_goals:.2f}")
    print(f"Away avg goals: {away_stats.avg_total_goals:.2f}")
    print("")
    
    # Test extreme lines
    extreme_lines = [
        ("ft_under_125", 12.5, "Under 12.5 (Extreme)"),
        ("ft_under_85", 8.5, "Under 8.5 (Very High)"),
        ("ft_under_55", 5.5, "Under 5.5 (High)"),
        ("ft_under_25", 2.5, "Under 2.5 (Normal)"),
        ("ht_under_15", 1.5, "HT Under 1.5"),
        ("ht_under_05", 0.5, "HT Under 0.5")
    ]
    
    for market_type, line, description in extreme_lines:
        result = breach_engine.analyze_line(
            market_type=market_type,
            line=line,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        print(f"📊 {description}")
        print(f"   Line: {result.line}")
        print(f"   Breach Rate: {result.line_breach_rate:.1f}%")
        print(f"   Safe Rate: {result.line_safe_rate:.1f}%")
        print(f"   Avg Value: {result.average_value:.2f}")
        print(f"   Avg Margin: {result.average_margin_to_line:.2f}")
        print(f"   Worst Case: {result.worst_case_margin:.2f}")
        print(f"   Signal: {result.signal.value}")
        print(f"   Safety Score: {result.historical_safety_score:.1f}/100")
        print(f"   Stability: {result.stability_score:.1f}/100")
        print("")
    
    return True


def test_detailed_analysis():
    """Test detailed line breach analysis"""
    
    print("\n" + "="*80)
    print("TEST 2: Detailed Line Analysis")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    breach_engine = HistoricalLineBreachEngine()
    
    # Get match
    matches_response = data_provider.get_today_matches()
    match = matches_response.data[0]
    
    # Get stats
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    # Analyze Under 12.5
    print(f"\nDetailed Analysis: Under 12.5")
    print("="*80)
    
    result = breach_engine.analyze_line(
        market_type="ft_under_125",
        line=12.5,
        home_stats=home_stats,
        away_stats=away_stats
    )
    
    print(f"\n📊 BREACH METRICS:")
    print(f"   Total Matches: {result.total_matches}")
    print(f"   Breached: {result.line_breach_count} ({result.line_breach_rate:.1f}%)")
    print(f"   Hit Exactly: {result.line_hit_count} ({result.line_hit_rate:.1f}%)")
    print(f"   Safe: {result.line_safe_count} ({result.line_safe_rate:.1f}%)")
    
    print(f"\n📈 VALUE ANALYSIS:")
    print(f"   Average Value: {result.average_value:.2f}")
    print(f"   Average Margin to Line: {result.average_margin_to_line:.2f}")
    print(f"   Worst Case Margin: {result.worst_case_margin:.2f}")
    print(f"   Best Case Margin: {result.best_case_margin:.2f}")
    
    print(f"\n🎯 CONSISTENCY:")
    print(f"   Consistency Score: {result.consistency_score:.1f}/100")
    print(f"   Variance: {result.variance:.2f}")
    
    print(f"\n🛡️ SAFETY SCORES:")
    print(f"   Historical Safety: {result.historical_safety_score:.1f}/100")
    print(f"   Stability: {result.stability_score:.1f}/100")
    
    print(f"\n🚦 SIGNAL:")
    print(f"   Signal: {result.signal.value}")
    print(f"   Strength: {result.signal_strength:.1f}/100")
    
    if result.positive_factors:
        print(f"\n✅ POSITIVE FACTORS:")
        for factor in result.positive_factors:
            print(f"   • {factor}")
    
    if result.risk_factors:
        print(f"\n⚠️ RISK FACTORS:")
        for factor in result.risk_factors:
            print(f"   • {factor}")
    
    print(f"\n💬 EXPLANATION:")
    print(f"   {result.explanation}")
    
    return True


def test_comparison():
    """Test comparison of different lines"""
    
    print("\n" + "="*80)
    print("TEST 3: Line Comparison")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    breach_engine = HistoricalLineBreachEngine()
    
    # Get match
    matches_response = data_provider.get_today_matches()
    match = matches_response.data[0]
    
    # Get stats
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    print(f"\nComparing Under Lines:")
    print("="*80)
    
    lines_to_compare = [1.5, 2.5, 3.5, 5.5, 8.5, 12.5]
    
    print(f"\n{'Line':<8} {'Breach%':<10} {'Safe%':<10} {'AvgVal':<10} {'Safety':<10} {'Signal':<20}")
    print("-" * 80)
    
    for line in lines_to_compare:
        result = breach_engine.analyze_line(
            market_type=f"ft_under_{int(line*10)}",
            line=line,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        print(f"{line:<8.1f} {result.line_breach_rate:<10.1f} {result.line_safe_rate:<10.1f} "
              f"{result.average_value:<10.2f} {result.historical_safety_score:<10.1f} {result.signal.value:<20}")
    
    print("\n💡 INSIGHTS:")
    print("   • Lower lines = Higher breach rate")
    print("   • Higher lines = Higher safety score")
    print("   • Extreme lines (>8.5) = Very safe/inconsistent")
    
    return True


def test_ht_vs_ft():
    """Test HT vs FT line analysis"""
    
    print("\n" + "="*80)
    print("TEST 4: HT vs FT Comparison")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    breach_engine = HistoricalLineBreachEngine()
    
    # Get match
    matches_response = data_provider.get_today_matches()
    match = matches_response.data[0]
    
    # Get stats
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    print(f"\nHalf Time vs Full Time:")
    print("="*80)
    
    # HT lines
    print(f"\n🕐 HALF TIME:")
    for line in [0.5, 1.5]:
        result = breach_engine.analyze_line(
            market_type=f"ht_under_{int(line*10)}",
            line=line,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        print(f"\n   Under {line}:")
        print(f"   Breach Rate: {result.line_breach_rate:.1f}%")
        print(f"   Avg Value: {result.average_value:.2f}")
        print(f"   Safety: {result.historical_safety_score:.1f}/100")
        print(f"   Signal: {result.signal.value}")
    
    # FT lines
    print(f"\n⏱️ FULL TIME:")
    for line in [1.5, 2.5]:
        result = breach_engine.analyze_line(
            market_type=f"ft_under_{int(line*10)}",
            line=line,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        print(f"\n   Under {line}:")
        print(f"   Breach Rate: {result.line_breach_rate:.1f}%")
        print(f"   Avg Value: {result.average_value:.2f}")
        print(f"   Safety: {result.historical_safety_score:.1f}/100")
        print(f"   Signal: {result.signal.value}")
    
    return True


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("📊 HISTORICAL LINE BREACH ENGINE - TESTS")
    print("="*80)
    print("\nThis script demonstrates line breach analysis")
    print("\nTests:")
    print("  1. Extreme lines analysis")
    print("  2. Detailed line analysis")
    print("  3. Line comparison")
    print("  4. HT vs FT comparison")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    # Run tests
    tests = [
        ("Extreme Lines", test_extreme_lines),
        ("Detailed Analysis", test_detailed_analysis),
        ("Line Comparison", test_comparison),
        ("HT vs FT", test_ht_vs_ft)
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
