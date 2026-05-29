"""
Fetch Real Matches
Test script to fetch real match data from SofaScore

Usage:
    # With SofaScore (real data)
    DATA_PROVIDER=sofascore python scripts/fetch_real_matches.py
    
    # With Mock (test data)
    python scripts/fetch_real_matches.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig, DataSourceType
from app.providers.data_source_manager import DataSourceManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def save_to_cache(data: dict, filename: str):
    """Save fetched data to local cache"""
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = cache_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved to cache: {filepath}")
    return filepath


def test_fetch_today_matches():
    """Test fetching today's matches"""
    
    print("\n" + "=" * 80)
    print("TEST 1: Fetch Today's Matches")
    print("=" * 80)
    
    manager = DataSourceManager()
    
    print(f"\n📊 Data Source: {manager.source_label}")
    print(f"   Provider: {manager.provider.config.name}")
    print(f"   Real Data: {'YES ✅' if manager.is_real_data else 'NO ❌ (MOCK)'}")
    
    print("\n📥 Fetching matches...")
    response = manager.get_today_matches()
    
    if not response.success:
        print(f"\n❌ ERROR: {response.error}")
        return None
    
    matches = response.data
    print(f"\n✅ SUCCESS: Found {len(matches)} matches")
    
    # Save to cache
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "source": manager.source_label,
        "count": len(matches),
        "matches": []
    }
    
    # Display matches
    print("\n" + "-" * 80)
    for i, match in enumerate(matches[:10], 1):
        source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
        print(f"\n  {source_tag} Match #{i}")
        print(f"    {match.home_team.name} vs {match.away_team.name}")
        print(f"    League: {match.competition.name}")
        print(f"    Date: {match.match_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Status: {match.status.value}")
        
        if match.score_fulltime:
            print(f"    FT: {match.score_fulltime.home}-{match.score_fulltime.away}")
        if match.score_halftime:
            print(f"    HT: {match.score_halftime.home}-{match.score_halftime.away}")
        
        cache_data["matches"].append({
            "id": match.id,
            "home": match.home_team.name,
            "away": match.away_team.name,
            "league": match.competition.name,
            "date": match.match_date.isoformat()
        })
    
    if len(matches) > 10:
        print(f"\n  ... and {len(matches) - 10} more")
    
    # Save
    cache_file = save_to_cache(cache_data, f"matches_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    
    return matches


def test_fetch_team_history(team_id: str, team_name: str):
    """Test fetching team history"""
    
    print("\n" + "=" * 80)
    print("TEST 2: Fetch Team History")
    print("=" * 80)
    
    manager = DataSourceManager()
    
    print(f"\n📥 Fetching history for: {team_name} (ID: {team_id})")
    response = manager.get_team_recent_matches(team_id, limit=10)
    
    if not response.success:
        print(f"\n❌ ERROR: {response.error}")
        return None
    
    matches = response.data
    print(f"\n✅ SUCCESS: Found {len(matches)} recent matches")
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"\n  {source_tag} Recent matches:")
    
    for i, match in enumerate(matches[:5], 1):
        print(f"    {i}. {match.match_date.strftime('%Y-%m-%d')}: "
              f"{match.home_team} {match.score_home}-{match.score_away} {match.away_team}")
    
    return matches


def test_fetch_h2h(team_a_id: str, team_b_id: str):
    """Test fetching H2H data"""
    
    print("\n" + "=" * 80)
    print("TEST 3: Fetch Head-to-Head")
    print("=" * 80)
    
    manager = DataSourceManager()
    
    print(f"\n📥 Fetching H2H: {team_a_id} vs {team_b_id}")
    response = manager.get_head_to_head(team_a_id, team_b_id)
    
    if not response.success:
        print(f"\n❌ ERROR: {response.error}")
        return None
    
    h2h = response.data
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    
    print(f"\n✅ SUCCESS: {source_tag}")
    print(f"    Total matches: {h2h.total_matches}")
    print(f"    Home wins: {h2h.home_wins}")
    print(f"    Away wins: {h2h.away_wins}")
    print(f"    Draws: {h2h.draws}")
    
    if h2h.matches:
        print(f"\n    Recent H2H:")
        for i, match in enumerate(h2h.matches[:5], 1):
            print(f"      {i}. {match.match_date.strftime('%Y-%m-%d')}: "
                  f"{match.home_team} {match.score_home}-{match.score_away} {match.away_team}")
    
    return h2h


def test_source_status():
    """Test source status endpoint"""
    
    print("\n" + "=" * 80)
    print("TEST 4: Source Status")
    print("=" * 80)
    
    manager = DataSourceManager()
    status = manager.get_source_status()
    
    print(f"\n📊 Source Status:")
    print(f"   Source Type: {status['source_type']}")
    print(f"   Source Label: {status['source_label']}")
    print(f"   Is Real Data: {'YES ✅' if status['is_real_data'] else 'NO ❌'}")
    print(f"   Provider: {status['provider_name']}")
    print(f"   Odds Provider: {status['odds_provider']}")
    print(f"   Cache Enabled: {status['cache_enabled']}")
    
    print(f"\n📜 Provenance Log ({len(status['provenance_log'])} entries):")
    for entry in status['provenance_log']:
        real_marker = "✅" if entry['source_type'] == "REAL" else "❌"
        print(f"   {real_marker} [{entry['source_type']}] {entry['endpoint']} "
              f"({entry['provider']})")
    
    return status


def main():
    """Main entry point"""
    
    print("\n" + "=" * 80)
    print("🔍 FETCH REAL MATCHES - DATA SOURCE TEST")
    print("=" * 80)
    
    # Check configuration
    config = DataSourceConfig()
    print(f"\n📊 Configuration:")
    print(f"   DATA_PROVIDER: {config.source_type.value}")
    print(f"   Cache Enabled: {config.cache_enabled}")
    print(f"   Source Label: {config.source_label}")
    
    if config.is_mock_data:
        print(f"\n⚠️  WARNING: Currently using MOCK DATA")
        print(f"   To use real data, run with:")
        print(f"   DATA_PROVIDER=sofascore python scripts/fetch_real_matches.py")
    else:
        print(f"\n✅ Using REAL DATA from {config.source_label}")
    
    print("\n" + "=" * 80)
    input("\nPress ENTER to start tests...")
    
    try:
        # Test 1: Fetch matches
        matches = test_fetch_today_matches()
        
        if matches:
            # Test 2: Fetch team history
            test_fetch_team_history(matches[0].home_team.id, matches[0].home_team.name)
            
            # Test 3: Fetch H2H
            if len(matches) > 0:
                test_fetch_h2h(matches[0].home_team.id, matches[0].away_team.id)
        
        # Test 4: Source status
        test_source_status()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
