"""
Debug Anomaly Script
Comprehensive debug mode for anomaly detection pipeline

Usage:
    python scripts/debug_anomaly.py [match_id] [market_type]
    python scripts/debug_anomaly.py --verbose
    python scripts/debug_anomaly.py --compact
    python scripts/debug_anomaly.py --json
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers import MockDataProvider
from app.providers.odds import MockOddsProvider
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine
from app.services.anomaly.scoring_calibration import ScoringCalibrator
from app.services.anomaly.score_breakdown_formatter import ScoreBreakdownFormatter
from app.services.analysis import HistoricalLineBreachEngine, PatternDetectionEngine
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def debug_full_pipeline(
    match_id: str,
    market_type: str = "ft_under_25",
    mode: str = "verbose",
    output_file: str = None
):
    """
    Run full pipeline debug for a specific match and market
    
    Args:
        match_id: Match ID to debug
        market_type: Market type to analyze
        mode: Output mode (verbose, compact, json)
        output_file: Optional file to save JSON output
    """
    
    print("\n" + "=" * 80)
    print(f"🔍 DEBUG MODE: {mode.upper()}")
    print("=" * 80)
    
    # Step 1: Data Fetching
    print("\n📥 STEP 1: Fetching Data")
    print("-" * 80)
    
    add_provider_support_to_stats_engine()
    data_provider = MockDataProvider()
    odds_provider = MockOddsProvider()
    
    # Fetch match
    matches_response = data_provider.get_today_matches()
    if not matches_response.success:
        print("❌ Failed to fetch matches")
        return
    
    # Find match
    match = None
    for m in matches_response.data:
        if m.id == match_id or m.home_team.name.lower() in match_id.lower():
            match = m
            break
    
    if not match:
        # Use first match
        match = matches_response.data[0]
        print(f"⚠️  Match not found, using: {match.home_team.name} vs {match.away_team.name}")
    else:
        print(f"✅ Match: {match.home_team.name} vs {match.away_team.name}")
    
    print(f"   League: {match.competition.name}")
    print(f"   Date: {match.match_date}")
    
    # Step 2: Fetch Team Histories
    print("\n📊 STEP 2: Fetching Team Histories")
    print("-" * 80)
    
    home_response = data_provider.get_team_recent_matches(match.home_team.id, 15)
    away_response = data_provider.get_team_recent_matches(match.away_team.id, 15)
    
    print(f"   {match.home_team.name}: {len(home_response.data)} matches")
    print(f"   {match.away_team.name}: {len(away_response.data)} matches")
    
    # Step 3: Calculate Stats
    print("\n📈 STEP 3: Calculating Statistics")
    print("-" * 80)
    
    stats_engine = StatsEngine(db=None)
    
    home_stats = stats_engine.calculate_from_provider_matches(
        match.home_team.id,
        home_response.data
    )
    away_stats = stats_engine.calculate_from_provider_matches(
        match.away_team.id,
        away_response.data
    )
    
    print(f"   Home Stats:")
    print(f"     Sample: {home_stats.sample_size}")
    print(f"     Avg Goals: {home_stats.avg_total_goals:.2f}")
    print(f"     Under 2.5: {home_stats.under_2_5_rate:.1f}%")
    print(f"     Variance: {home_stats.variance_goals_scored + home_stats.variance_goals_conceded:.2f}")
    print(f"     Stability: {home_stats.stability_score:.2f}")
    
    print(f"   Away Stats:")
    print(f"     Sample: {away_stats.sample_size}")
    print(f"     Avg Goals: {away_stats.avg_total_goals:.2f}")
    print(f"     Under 2.5: {away_stats.under_2_5_rate:.1f}%")
    print(f"     Variance: {away_stats.variance_goals_scored + away_stats.variance_goals_conceded:.2f}")
    print(f"     Stability: {away_stats.stability_score:.2f}")
    
    # Step 4: Line Breach Analysis
    print("\n🛡️  STEP 4: Line Breach Analysis")
    print("-" * 80)
    
    breach_engine = HistoricalLineBreachEngine()
    
    line = 2.5 if "under_25" in market_type else 0.5 if "under_05" in market_type else None
    
    breach = breach_engine.analyze_line(
        market_type=market_type,
        line=line,
        home_stats=home_stats,
        away_stats=away_stats
    )
    
    print(f"   Line: {breach.line}")
    print(f"   Breach Rate: {breach.line_breach_rate:.1f}%")
    print(f"   Safety Score: {breach.historical_safety_score:.1f}/100")
    print(f"   Signal: {breach.signal.value}")
    
    # Step 5: Fetch Odds
    print("\n💰 STEP 5: Fetching Odds")
    print("-" * 80)
    
    odds_response = odds_provider.get_match_odds(match.id)
    if odds_response.success and odds_response.data:
        # Find matching odd
        odd = None
        for o in odds_response.data:
            if market_type in o.market_type.value:
                odd = o
                break
        
        if not odd:
            odd = odds_response.data[0]
        
        bookmaker_odds = odd.odd
        print(f"   Market: {odd.market_type.value}")
        print(f"   Odds: {bookmaker_odds}")
        print(f"   Bookmaker: {odd.bookmaker}")
    else:
        bookmaker_odds = 1.85
        print(f"   No odds found, using default: {bookmaker_odds}")
    
    # Step 6: Anomaly Detection
    print("\n🎯 STEP 6: Anomaly Detection")
    print("-" * 80)
    
    anomaly_engine = AnomalyEngine()
    calibrator = ScoringCalibrator(anomaly_engine)
    
    numeric_id = int(match.id) if match.id.isdigit() else hash(match.id) % 1000000
    
    result, breakdown = calibrator.analyze_score_calculation(
        match_id=numeric_id,
        market_type=market_type,
        bookmaker_odds=bookmaker_odds,
        home_stats=home_stats,
        away_stats=away_stats,
        line=line,
        debug=False  # We'll format ourselves
    )
    
    # Step 7: Pattern Detection
    print("\n🧩 STEP 7: Pattern Detection")
    print("-" * 80)
    
    pattern_engine = PatternDetectionEngine()
    home_patterns = pattern_engine.analyze_team(
        match.home_team.id,
        match.home_team.name,
        overall_stats=home_stats
    )
    away_patterns = pattern_engine.analyze_team(
        match.away_team.id,
        match.away_team.name,
        overall_stats=away_stats
    )
    
    print(f"   {match.home_team.name} Patterns: {home_patterns.pattern_tags[:3]}")
    print(f"   {match.away_team.name} Patterns: {away_patterns.pattern_tags[:3]}")
    
    # Step 8: Format Output
    print("\n" + "=" * 80)
    print("SCORE BREAKDOWN")
    print("=" * 80)
    
    formatter = ScoreBreakdownFormatter(mode)
    output = formatter.format(result, breakdown)
    print(output)
    
    # Export JSON if requested
    if output_file or mode == "json":
        json_formatter = ScoreBreakdownFormatter("json")
        json_output = json_formatter.format(result, breakdown)
        
        filepath = output_file or "anomaly_debug_report.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_output)
        
        print(f"\n💾 JSON exported to: {filepath}")
    
    return result, breakdown


def debug_all_markets(match_id: str, mode: str = "compact"):
    """Debug all markets for a match"""
    
    markets = [
        "ft_under_25",
        "ft_under_35",
        "ht_under_05",
        "ht_under_15",
        "btts_yes"
    ]
    
    results = []
    
    for market in markets:
        try:
            print(f"\n{'='*80}")
            print(f"MARKET: {market}")
            print(f"{'='*80}")
            
            result, _ = debug_full_pipeline(match_id, market, mode)
            results.append(result)
        except Exception as e:
            print(f"❌ Error with {market}: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - ALL MARKETS")
    print("=" * 80)
    
    for r in results:
        print(f"{r.market_type:<20} Score: {r.anomaly_score:6.1f} | Conf: {r.confidence_category.value:<7} | Signals: +{len(r.positive_signals)}/-{len(r.negative_signals)}")
    
    return results


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Debug anomaly detection pipeline"
    )
    parser.add_argument(
        "match_id",
        nargs="?",
        default="match_001",
        help="Match ID to debug"
    )
    parser.add_argument(
        "--market",
        default="ft_under_25",
        help="Market type (default: ft_under_25)"
    )
    parser.add_argument(
        "--mode",
        choices=["verbose", "compact", "json"],
        default="verbose",
        help="Output mode"
    )
    parser.add_argument(
        "--all-markets",
        action="store_true",
        help="Debug all markets"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("🔍 ANOMALY DEBUG SYSTEM")
    print("=" * 80)
    print(f"Match: {args.match_id}")
    print(f"Market: {args.market}")
    print(f"Mode: {args.mode}")
    
    try:
        if args.all_markets:
            debug_all_markets(args.match_id, args.mode)
        else:
            debug_full_pipeline(
                args.match_id,
                args.market,
                args.mode,
                args.output
            )
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
