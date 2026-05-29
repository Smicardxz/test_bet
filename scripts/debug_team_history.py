"""
Debug Team History - PHASE 10
Test all history fetching strategies for a specific fixture
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.providers.api_football_provider import ApiFootballProvider


def debug_team_history(fixture_id: str):
    """Debug history fetching for a specific fixture"""
    
    print("\n" + "="*80)
    print(f" DEBUG TEAM HISTORY - Fixture {fixture_id}")
    print("="*80 + "\n")
    
    # Initialize provider
    manager = DataSourceManager()
    provider = manager.provider
    
    if not isinstance(provider, ApiFootballProvider):
        print(f"[ERROR] Provider is {type(provider).__name__}, not ApiFootballProvider")
        print("   Set DATA_PROVIDER=api_football in .env")
        return False
    
    print(f"[OK] Provider: {provider.config.name}")
    print()
    
    # Fetch fixture details
    print("[INFO] Fetching today's matches to find fixture...")
    today_response = provider.get_today_matches()
    
    if not today_response or not today_response.data:
        print(f"[ERROR] Could not fetch today's matches")
        return False
    
    # Find the fixture
    fixture = None
    for match in today_response.data:
        match_id_str = str(getattr(match, 'id', getattr(match, 'match_id', '')))
        if match_id_str == str(fixture_id):
            fixture = match
            break
    
    if not fixture:
        print(f"[ERROR] Fixture {fixture_id} not found in today's matches")
        print(f"   Total matches today: {len(today_response.data)}")
        return False
    
    print(f"[OK] Fixture loaded")
    print()
    
    # Display fixture info
    print("="*80)
    print(" FIXTURE INFO")
    print("="*80)
    print(f"Match: {fixture.home_team.name} vs {fixture.away_team.name}")
    print(f"Competition: {fixture.competition.name} ({fixture.competition.country})")
    print(f"Date: {fixture.match_date}")
    status_long = getattr(fixture.status, 'long', getattr(fixture.status, 'description', '?'))
    status_short = getattr(fixture.status, 'short', '?')
    print(f"Status: {status_long} ({status_short})")
    print()
    fixture_id_val = getattr(fixture, 'id', getattr(fixture, 'match_id', '?'))
    print(f"fixture_id: {fixture_id_val}")
    print(f"home_team_id: {fixture.home_team.id}")
    print(f"away_team_id: {fixture.away_team.id}")
    print(f"league_id: {fixture.competition.id}")
    print(f"season: {getattr(fixture.competition, 'season', '?')}")
    print()
    
    # Test home team history
    print("="*80)
    print(f" HOME TEAM HISTORY - {fixture.home_team.name} (ID: {fixture.home_team.id})")
    print("="*80)
    print()
    
    print("Strategy 1: team + last + status=FT + season")
    print("-" * 80)
    home_history = provider.get_team_recent_matches(
        team_id=fixture.home_team.id,
        limit=10,
        before_date=fixture.match_date
    )
    print(f"Result: {len(home_history)} matches")
    if home_history:
        for i, match in enumerate(home_history[:3]):
            print(f"  [{i+1}] {match.match_date} - {match.home_team.name} vs {match.away_team.name} ({match.score.fulltime_home}-{match.score.fulltime_away})")
    print()
    
    # Test away team history
    print("="*80)
    print(f" AWAY TEAM HISTORY - {fixture.away_team.name} (ID: {fixture.away_team.id})")
    print("="*80)
    print()
    
    print("Strategy 1: team + last + status=FT + season")
    print("-" * 80)
    away_history = provider.get_team_recent_matches(
        team_id=fixture.away_team.id,
        limit=10,
        before_date=fixture.match_date
    )
    print(f"Result: {len(away_history)} matches")
    if away_history:
        for i, match in enumerate(away_history[:3]):
            print(f"  [{i+1}] {match.match_date} - {match.home_team.name} vs {match.away_team.name} ({match.score.fulltime_home}-{match.score.fulltime_away})")
    print()
    
    # Test H2H
    print("="*80)
    print(f" HEAD-TO-HEAD")
    print("="*80)
    print()
    
    h2h = provider.get_head_to_head(
        home_team_id=fixture.home_team.id,
        away_team_id=fixture.away_team.id,
        limit=10,
        before_date=fixture.match_date
    )
    print(f"Result: {len(h2h)} matches")
    if h2h:
        for i, match in enumerate(h2h[:3]):
            print(f"  [{i+1}] {match.match_date} - {match.home_team.name} vs {match.away_team.name} ({match.score.fulltime_home}-{match.score.fulltime_away})")
    print()
    
    # Summary
    print("="*80)
    print(" SUMMARY")
    print("="*80)
    print(f"Home history count: {len(home_history)}")
    print(f"Away history count: {len(away_history)}")
    print(f"H2H count: {len(h2h)}")
    print()
    
    if len(home_history) == 0 and len(away_history) == 0:
        print("[ERROR] NO HISTORY FOUND")
        print()
        print("Possible reasons:")
        print("  1. Teams are new (no previous matches)")
        print("  2. API doesn't have data for this league/season")
        print("  3. Wrong team IDs")
        print("  4. API parameters incorrect")
        print()
        print("Check the logs above for:")
        print("  - raw_fixtures_count (should be > 0)")
        print("  - rejected_* counts (why matches were filtered out)")
        print()
        return False
    else:
        print("[OK] HISTORY FOUND")
        print()
        if len(home_history) > 0 and len(away_history) > 0:
            print("[OK] Both teams have history - analysis should work!")
        else:
            print("[WARNING] Only one team has history - may be insufficient")
        print()
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug team history fetching")
    parser.add_argument("--fixture_id", required=True, help="Fixture ID to debug")
    
    args = parser.parse_args()
    
    success = debug_team_history(args.fixture_id)
    sys.exit(0 if success else 1)
