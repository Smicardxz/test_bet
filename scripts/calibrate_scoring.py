"""
Scoring Calibration Script
Analyze and calibrate anomaly scoring system
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine
from app.services.anomaly.scoring_calibration import ScoringCalibrator
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_single_market_detailed():
    """Test single market with detailed breakdown"""
    
    print("\n" + "="*80)
    print("TEST 1: Single Market Detailed Analysis")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    manager = DataSourceManager()
    data_provider = manager.provider
    odds_provider = manager.odds_provider
    calibrator = ScoringCalibrator()
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"Data source: {source_tag} {manager.source_label}")
    
    # Get match
    matches_response = data_provider.get_today_matches()
    if not matches_response.success or not matches_response.data:
        print("❌ No matches available")
        return False
    
    match = matches_response.data[0]
    
    # Get stats
    stats_engine = StatsEngine(db=None)
    
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
    
    # Get odds
    odds_response = odds_provider.get_match_odds(match.id)
    if not odds_response.success or not odds_response.data:
        print("❌ No odds available")
        return False
    
    odd = odds_response.data[0]
    
    # Analyze with detailed breakdown
    print(f"\nAnalyzing: {match.home_team.name} vs {match.away_team.name}")
    print(f"Market: {odd.market_type.value}")
    print(f"Bookmaker Odds: {odd.odd}")
    print("")
    
    result, breakdown = calibrator.analyze_score_calculation(
        match_id=int(match.id) if match.id.isdigit() else hash(match.id) % 1000000,
        market_type=odd.market_type.value,
        bookmaker_odds=odd.odd,
        home_stats=home_stats,
        away_stats=away_stats,
        line=odd.line,
        debug=True
    )
    
    return True


def test_multiple_markets():
    """Test multiple markets and analyze distribution"""
    
    print("\n" + "="*80)
    print("TEST 2: Multiple Markets Analysis")
    print("="*80)
    
    # Setup
    add_provider_support_to_stats_engine()
    manager = DataSourceManager()
    data_provider = manager.provider
    odds_provider = manager.odds_provider
    calibrator = ScoringCalibrator()
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"Data source: {source_tag} {manager.source_label}")
    stats_engine = StatsEngine(db=None)
    
    # Get matches
    matches_response = data_provider.get_today_matches()
    if not matches_response.success:
        print("❌ No matches available")
        return False
    
    matches = matches_response.data[:3]  # Test first 3 matches
    
    print(f"\nAnalyzing {len(matches)} matches...")
    
    results = []
    
    for match in matches:
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
        
        # Get odds
        odds_response = odds_provider.get_match_odds(match.id)
        if not odds_response.success:
            continue
        
        # Analyze each market
        for odd in odds_response.data[:3]:  # First 3 markets per match
            try:
                result, breakdown = calibrator.analyze_score_calculation(
                    match_id=int(match.id) if match.id.isdigit() else hash(match.id) % 1000000,
                    market_type=odd.market_type.value,
                    bookmaker_odds=odd.odd,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    line=odd.line,
                    debug=False
                )
                
                results.append((result, breakdown))
            
            except Exception as e:
                logger.warning(f"Error analyzing market: {e}")
    
    print(f"\n✅ Analyzed {len(results)} markets")
    
    # Visualize distribution
    print("\n" + "="*80)
    print("SCORE DISTRIBUTION")
    print("="*80)
    
    visualization = calibrator.visualize_score_distribution(results)
    print(visualization)
    
    return results


def detect_inconsistencies(results):
    """Detect inconsistent scores"""
    
    print("\n" + "="*80)
    print("TEST 3: Detect Inconsistencies")
    print("="*80)
    
    calibrator = ScoringCalibrator()
    
    inconsistencies = calibrator.detect_inconsistent_scores(results)
    
    if not inconsistencies:
        print("\n✅ No inconsistencies detected")
        return True
    
    print(f"\n⚠️  Found {len(inconsistencies)} inconsistencies:")
    
    for inc in inconsistencies:
        print(f"\n  Market: {inc['market_type']}")
        print(f"  Anomaly Score: {inc['anomaly_score']:.1f}")
        print(f"  Issues:")
        
        for issue in inc['issues']:
            print(f"    • {issue['description']}")
            for key, value in issue.items():
                if key not in ['type', 'description']:
                    print(f"      {key}: {value}")
    
    return True


def get_calibration_recommendations(results):
    """Get calibration recommendations"""
    
    print("\n" + "="*80)
    print("TEST 4: Calibration Recommendations")
    print("="*80)
    
    calibrator = ScoringCalibrator()
    
    recommendations = calibrator.recommend_calibration(results)
    
    print("\n📊 CURRENT WEIGHTS:")
    for component, weight in recommendations["current_weights"].items():
        print(f"  {component}: {weight:.0%}")
    
    print("\n📈 AVERAGE COMPONENT SCORES:")
    for component, score in recommendations["average_scores"].items():
        print(f"  {component}: {score:.1f}/100")
    
    print("\n💥 AVERAGE COMPONENT IMPACT:")
    for component, impact in recommendations["average_impact"].items():
        print(f"  {component}: {impact:.1f}%")
    
    if recommendations["suggestions"]:
        print("\n💡 SUGGESTIONS:")
        for i, suggestion in enumerate(recommendations["suggestions"], 1):
            print(f"\n  {i}. {suggestion['type'].upper()}")
            print(f"     {suggestion['description']}")
            print(f"     → {suggestion['suggestion']}")
            
            for key, value in suggestion.items():
                if key not in ['type', 'description', 'suggestion']:
                    print(f"     {key}: {value}")
    else:
        print("\n✅ No calibration suggestions - weights appear balanced")
    
    return True


def test_extreme_cases():
    """Test extreme cases to validate scoring"""
    
    print("\n" + "="*80)
    print("TEST 5: Extreme Cases Validation")
    print("="*80)
    
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    odds_provider = MockOddsProvider()
    calibrator = ScoringCalibrator()
    stats_engine = StatsEngine(db=None)
    
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
    
    # Test cases
    test_cases = [
        {
            "name": "Very High Odds (Overvalued)",
            "market": "ft_under_25",
            "odds": 3.50,
            "line": 2.5
        },
        {
            "name": "Very Low Odds (Undervalued)",
            "market": "ft_under_25",
            "odds": 1.20,
            "line": 2.5
        },
        {
            "name": "Extreme Under",
            "market": "ft_under_85",
            "odds": 1.05,
            "line": 8.5
        },
        {
            "name": "HT Under 0.5",
            "market": "ht_under_05",
            "odds": 1.30,
            "line": 0.5
        }
    ]
    
    print("\nTesting extreme cases:\n")
    
    for case in test_cases:
        print(f"Case: {case['name']}")
        print(f"  Market: {case['market']}")
        print(f"  Odds: {case['odds']}")
        
        result, breakdown = calibrator.analyze_score_calculation(
            match_id=1,
            market_type=case['market'],
            bookmaker_odds=case['odds'],
            home_stats=home_stats,
            away_stats=away_stats,
            line=case.get('line'),
            debug=False
        )
        
        print(f"  → Anomaly Score: {result.anomaly_score:.1f}")
        print(f"  → Confidence: {result.confidence_category.value}")
        print(f"  → Probability Gap: {breakdown.probability_gap:.1%}")
        print("")
    
    return True


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("🎯 SCORING CALIBRATION SYSTEM")
    print("="*80)
    print("\nThis script analyzes and calibrates the anomaly scoring system")
    print("\nTests:")
    print("  1. Single market detailed analysis")
    print("  2. Multiple markets distribution")
    print("  3. Detect inconsistencies")
    print("  4. Calibration recommendations")
    print("  5. Extreme cases validation")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    # Run tests
    tests = [
        ("Single Market Detailed", test_single_market_detailed),
        ("Multiple Markets", test_multiple_markets),
    ]
    
    results = None
    
    for name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"Running: {name}")
            print(f"{'='*80}")
            
            result = test_func()
            
            if name == "Multiple Markets":
                results = result
            
            if not result:
                print(f"\n❌ Test failed: {name}")
        
        except Exception as e:
            logger.error(f"Test {name} failed: {e}", exc_info=True)
            print(f"\n❌ Test failed with exception: {name}")
    
    # Run analysis tests if we have results
    if results:
        try:
            detect_inconsistencies(results)
            get_calibration_recommendations(results)
            test_extreme_cases()
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
    
    print("\n" + "="*80)
    print("✅ CALIBRATION COMPLETE")
    print("="*80)
    
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
