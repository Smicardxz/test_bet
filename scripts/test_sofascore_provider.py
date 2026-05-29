"""
Test SofaScore Provider
Quick test script to validate provider functionality
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.sofascore_provider import SofaScoreProvider
from app.providers import ProviderConfig


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)


def test_today_matches():
    """Test fetching today's matches"""
    
    print("\n" + "="*80)
    print("TEST 1: Fetch Today's Matches")
    print("="*80)
    
    provider = SofaScoreProvider()
    
    print("\n📥 Fetching today's matches...")
    response = provider.get_today_matches()
    
    if response.success:
        print(f"✅ Success! Found {len(response.data)} matches")
        
        if response.data:
            match = response.data[0]
            print(f"\nExample match:")
            print(f"  {match.home_team.name} vs {match.away_team.name}")
            print(f"  Competition: {match.competition.name}")
            print(f"  Date: {match.match_date}")
    else:
        print(f"❌ Error: {response.error}")
    
    return response.success


def test_match_details():
    """Test fetching match details"""
    
    print("\n" + "="*80)
    print("TEST 2: Fetch Match Details")
    print("="*80)
    
    provider = SofaScoreProvider()
    
    # First get a match ID
    response = provider.get_today_matches()
    
    if not response.success or not response.data:
        print("⚠️  Skipping (no matches available)")
        return True
    
    match_id = response.data[0].id
    
    print(f"\n📥 Fetching details for match {match_id}...")
    response = provider.get_match_details(match_id)
    
    if response.success:
        match = response.data
        print(f"✅ Success!")
        print(f"  {match.home_team.name} vs {match.away_team.name}")
        print(f"  Status: {match.status.value}")
        if match.score_fulltime:
            print(f"  Score: {match.score_fulltime.home}-{match.score_fulltime.away}")
    else:
        print(f"❌ Error: {response.error}")
    
    return response.success


def test_team_recent():
    """Test fetching team recent matches"""
    
    print("\n" + "="*80)
    print("TEST 3: Fetch Team Recent Matches")
    print("="*80)
    
    provider = SofaScoreProvider()
    
    # Get a team ID from today's matches
    response = provider.get_today_matches()
    
    if not response.success or not response.data:
        print("⚠️  Skipping (no matches available)")
        return True
    
    team_id = response.data[0].home_team.id
    team_name = response.data[0].home_team.name
    
    print(f"\n📥 Fetching recent matches for {team_name}...")
    response = provider.get_team_recent_matches(team_id, limit=5)
    
    if response.success:
        print(f"✅ Success! Found {len(response.data)} recent matches")
        
        for i, match in enumerate(response.data[:3], 1):
            print(f"  {i}. {match.home_team.name} vs {match.away_team.name}")
            if match.score_fulltime:
                print(f"     Score: {match.score_fulltime.home}-{match.score_fulltime.away}")
    else:
        print(f"❌ Error: {response.error}")
    
    return response.success


def test_cache():
    """Test caching functionality"""
    
    print("\n" + "="*80)
    print("TEST 4: Cache Functionality")
    print("="*80)
    
    provider = SofaScoreProvider()
    
    # First request (not cached)
    print("\n📥 First request (should fetch from API)...")
    response1 = provider.get_today_matches()
    print(f"  Cached: {response1.cached}")
    
    # Second request (cached)
    print("\n📥 Second request (should use cache)...")
    response2 = provider.get_today_matches()
    print(f"  Cached: {response2.cached}")
    
    if response2.cached:
        print(f"  Cache age: {response2.cache_age_seconds}s")
    
    # Cache stats
    print("\n📊 Cache statistics:")
    stats = provider.get_cache_stats()
    print(f"  Total files: {stats.get('total_files', 0)}")
    print(f"  Total size: {stats.get('total_size_mb', 0)} MB")
    
    return response1.success and response2.success and response2.cached


def test_error_handling():
    """Test error handling"""
    
    print("\n" + "="*80)
    print("TEST 5: Error Handling")
    print("="*80)
    
    provider = SofaScoreProvider()
    
    # Try to fetch non-existent match
    print("\n📥 Fetching non-existent match...")
    response = provider.get_match_details("nonexistent_id_12345")
    
    if not response.success:
        print(f"✅ Error handled correctly: {response.error}")
        return True
    else:
        print(f"❌ Should have failed but succeeded")
        return False


def main():
    """Run all tests"""
    
    print("\n" + "="*80)
    print("🧪 SOFASCORE PROVIDER TESTS")
    print("="*80)
    
    tests = [
        ("Today's Matches", test_today_matches),
        ("Match Details", test_match_details),
        ("Team Recent", test_team_recent),
        ("Cache", test_cache),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
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
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
