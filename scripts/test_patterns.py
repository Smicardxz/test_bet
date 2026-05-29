"""
Pattern Detection Demo Script
Demonstrate automatic pattern detection for teams and leagues
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers import MockDataProvider
from app.services.stats import StatsEngine
from app.services.analysis import PatternDetectionEngine
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_team_patterns():
    """Test team pattern detection"""
    
    print("\n" + "="*80)
    print("TEST 1: Team Pattern Detection")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    pattern_engine = PatternDetectionEngine()
    
    # Get matches
    matches_response = data_provider.get_today_matches()
    if not matches_response.success:
        print("❌ No matches available")
        return False
    
    match = matches_response.data[0]
    
    print(f"\nAnalyzing: {match.home_team.name} vs {match.away_team.name}")
    print("")
    
    # Get home team stats
    print(f"🏠 HOME TEAM: {match.home_team.name}")
    print("-" * 80)
    
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    
    home_patterns = pattern_engine.analyze_team(
        team_id=match.home_team.id,
        team_name=match.home_team.name,
        overall_stats=home_stats
    )
    
    print(f"  Pattern Score: {home_patterns.pattern_score:.1f}/100")
    print(f"  Confidence: {home_patterns.confidence:.0%}")
    print(f"  Patterns Detected: {len(home_patterns.patterns)}")
    print(f"  Tags: {home_patterns.pattern_tags}")
    print("")
    
    for i, pattern in enumerate(home_patterns.patterns[:5], 1):
        print(f"  {i}. {pattern.pattern_type.value}")
        print(f"     Strength: {pattern.strength.value}")
        print(f"     Score: {pattern.score:.1f}/100")
        print(f"     Description: {pattern.description}")
        print("")
    
    # Get away team stats
    print(f"✈️  AWAY TEAM: {match.away_team.name}")
    print("-" * 80)
    
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    away_patterns = pattern_engine.analyze_team(
        team_id=match.away_team.id,
        team_name=match.away_team.name,
        overall_stats=away_stats
    )
    
    print(f"  Pattern Score: {away_patterns.pattern_score:.1f}/100")
    print(f"  Confidence: {away_patterns.confidence:.0%}")
    print(f"  Patterns Detected: {len(away_patterns.patterns)}")
    print(f"  Tags: {away_patterns.pattern_tags}")
    print("")
    
    for i, pattern in enumerate(away_patterns.patterns[:5], 1):
        print(f"  {i}. {pattern.pattern_type.value}")
        print(f"     Strength: {pattern.strength.value}")
        print(f"     Score: {pattern.score:.1f}/100")
        print(f"     Description: {pattern.description}")
        print("")
    
    return True


def test_league_patterns():
    """Test league pattern detection"""
    
    print("\n" + "="*80)
    print("TEST 2: League Pattern Detection")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    pattern_engine = PatternDetectionEngine()
    
    # Get multiple matches
    matches_response = data_provider.get_today_matches()
    if not matches_response.success or len(matches_response.data) < 3:
        print("⚠️  Not enough matches for league analysis")
        return True
    
    print(f"\nAnalyzing league with {len(matches_response.data)} matches...")
    
    # Collect all team stats
    all_stats = []
    
    for match in matches_response.data[:5]:  # First 5 matches
        home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
        away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
        
        home_stats = stats_engine.calculate_from_provider_matches(
            match.home_team.id,
            home_response.data
        )
        
        all_stats.append(home_stats)
    
    # Analyze league
    league_patterns = pattern_engine.analyze_league(
        all_stats,
        league_name="Test League"
    )
    
    print(f"\n✅ Found {len(league_patterns)} league patterns:")
    print("")
    
    for i, pattern in enumerate(league_patterns, 1):
        print(f"  {i}. {pattern.pattern_type.value}")
        print(f"     Strength: {pattern.strength.value}")
        print(f"     Score: {pattern.score:.1f}/100")
        print(f"     Description: {pattern.description}")
        print("")
    
    return True


def test_pattern_comparison():
    """Compare patterns between two teams"""
    
    print("\n" + "="*80)
    print("TEST 3: Pattern Comparison")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    pattern_engine = PatternDetectionEngine()
    
    # Get match
    matches_response = data_provider.get_today_matches()
    match = matches_response.data[0]
    
    # Get stats for both teams
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
    
    # Analyze both
    home_patterns = pattern_engine.analyze_team(
        team_id=match.home_team.id,
        team_name=match.home_team.name,
        overall_stats=home_stats
    )
    
    away_patterns = pattern_engine.analyze_team(
        team_id=match.away_team.id,
        team_name=match.away_team.name,
        overall_stats=away_stats
    )
    
    print(f"\nComparing patterns:")
    print(f"\n{'Team':<25} {'Tags':<60}")
    print("-" * 85)
    print(f"{match.home_team.name:<25} {str(home_patterns.pattern_tags):<60}")
    print(f"{match.away_team.name:<25} {str(away_patterns.pattern_tags):<60}")
    print("")
    
    # Find common patterns
    home_tags = set(home_patterns.pattern_tags)
    away_tags = set(away_patterns.pattern_tags)
    common = home_tags & away_tags
    
    if common:
        print(f"🎯 Common patterns: {list(common)}")
        print("   → Match likely to exhibit these patterns")
    else:
        print("⚠️  No common patterns - contrasting styles")
    
    print("")
    
    return True


def test_h2h_patterns():
    """Test H2H pattern detection"""
    
    print("\n" + "="*80)
    print("TEST 4: H2H Pattern Detection")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    pattern_engine = PatternDetectionEngine()
    
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
    
    # Analyze H2H
    h2h_patterns = pattern_engine.analyze_h2h(
        home_stats,
        away_stats,
        h2h_matches_count=8
    )
    
    print(f"\nAnalyzing H2H: {match.home_team.name} vs {match.away_team.name}")
    print(f"\n✅ Found {len(h2h_patterns)} H2H patterns:")
    print("")
    
    for i, pattern in enumerate(h2h_patterns, 1):
        print(f"  {i}. {pattern.pattern_type.value}")
        print(f"     Strength: {pattern.strength.value}")
        print(f"     Score: {pattern.score:.1f}/100")
        print(f"     Description: {pattern.description}")
        print("")
    
    if not h2h_patterns:
        print("  No significant H2H patterns detected")
    
    return True


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("🎯 PATTERN DETECTION ENGINE - TESTS")
    print("="*80)
    print("\nThis script demonstrates automatic pattern detection")
    print("\nTests:")
    print("  1. Team pattern detection")
    print("  2. League pattern detection")
    print("  3. Pattern comparison")
    print("  4. H2H pattern detection")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    # Run tests
    tests = [
        ("Team Patterns", test_team_patterns),
        ("League Patterns", test_league_patterns),
        ("Pattern Comparison", test_pattern_comparison),
        ("H2H Patterns", test_h2h_patterns)
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
