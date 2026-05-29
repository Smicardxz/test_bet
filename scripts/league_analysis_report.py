"""
League Analysis Report
Analyze and rank leagues for anomaly detection priority

Usage:
    python scripts/league_analysis_report.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers import MockDataProvider
from app.services.stats import StatsEngine
from app.services.analysis import LeagueProfileEngine


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_league_analysis():
    """Run complete league analysis"""
    
    print("\n" + "=" * 100)
    print("LEAGUE PROFILE ANALYSIS")
    print("=" * 100)
    
    # Step 1: Fetch matches and group by league
    print("\n📊 Step 1: Fetching league data...")
    
    provider = MockDataProvider()
    stats_engine = StatsEngine(db=None)
    
    matches_response = provider.get_today_matches()
    if not matches_response.success or not matches_response.data:
        print("❌ No matches available")
        return None
    
    # Group teams by league
    league_stats = {}
    
    for match in matches_response.data:
        league = match.competition.name
        
        if league not in league_stats:
            league_stats[league] = []
        
        # Get home team stats
        home_response = provider.get_team_recent_matches(match.home_team.id, 15)
        if home_response.success:
            home_stats = stats_engine.calculate_from_provider_matches(
                match.home_team.id,
                home_response.data
            )
            league_stats[league].append(home_stats)
        
        # Get away team stats
        away_response = provider.get_team_recent_matches(match.away_team.id, 15)
        if away_response.success:
            away_stats = stats_engine.calculate_from_provider_matches(
                match.away_team.id,
                away_response.data
            )
            league_stats[league].append(away_stats)
    
    print(f"   Found {len(league_stats)} leagues")
    for league, teams in league_stats.items():
        print(f"     {league}: {len(teams)} teams")
    
    # Step 2: Analyze leagues
    print("\n🔍 Step 2: Analyzing leagues...")
    
    engine = LeagueProfileEngine()
    ranking = engine.analyze_leagues(league_stats)
    
    # Step 3: Print report
    print("\n📈 Step 3: Generating report...")
    engine.print_ranking(ranking)
    
    # Step 4: Priority leagues
    print("\n🎯 PRIORITY LEAGUES (Top 5)")
    print("-" * 80)
    
    priority = engine.get_priority_leagues(ranking, min_exploitability=60.0)
    
    for i, p in enumerate(priority[:5], 1):
        print(f"\n  #{i} {p.league_name}")
        print(f"     Exploitability: {p.exploitability_score:.0f}/100")
        print(f"     Under 2.5: {p.under_2_5_rate:.1f}%")
        print(f"     HT 0-0: {p.ht_00_rate:.1f}%")
        print(f"     Stability: {p.stability_score:.0f}/100")
        print(f"     Tags: {', '.join(p.tags[:5])}")
    
    # Step 5: HT specialists
    print("\n⏱️  HT SPECIALIST LEAGUES")
    print("-" * 80)
    
    ht_leagues = engine.get_ht_specialist_leagues(ranking, min_ht_00_rate=45.0)
    
    for p in ht_leagues[:5]:
        print(f"  • {p.league_name}: HT 0-0 {p.ht_00_rate:.1f}%")
    
    # Step 6: Under specialists
    print("\n🎯 UNDER SPECIALIST LEAGUES")
    print("-" * 80)
    
    under_leagues = engine.get_under_specialist_leagues(ranking, min_under_rate=65.0)
    
    for p in under_leagues[:5]:
        print(f"  • {p.league_name}: Under 2.5 {p.under_2_5_rate:.1f}%")
    
    # Step 7: Export JSON
    import json
    
    report_data = {
        "total_leagues": ranking.total_leagues,
        "priority_leagues": [p.to_dict() for p in priority[:10]],
        "ht_specialists": [p.league_name for p in ht_leagues[:5]],
        "under_specialists": [p.league_name for p in under_leagues[:5]],
        "recommendations": ranking.recommendations
    }
    
    with open("league_analysis_report.json", 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)
    
    print("\n💾 Exported to: league_analysis_report.json")
    
    return ranking


def main():
    """Main entry point"""
    
    print("\n" + "=" * 100)
    print("🏆 LEAGUE PROFILE ANALYSIS SYSTEM")
    print("=" * 100)
    print("\nIdentifying the best obscure leagues for anomaly detection:")
    print("  • Most stable leagues")
    print("  • Most under-prone leagues")
    print("  • Best HT 0-0 trends")
    print("  • Highest exploitability")
    print("=" * 100)
    
    input("\nPress ENTER to start...")
    
    try:
        ranking = run_league_analysis()
        return 0
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
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
