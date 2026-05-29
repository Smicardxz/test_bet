"""
Data Providers Usage Examples
"""

from app.providers import MockDataProvider, ProviderConfig
from app.providers.sofascore_provider import SofaScoreProvider
from datetime import date


def example_mock_provider():
    """Example using MockDataProvider"""
    
    print("\n" + "="*80)
    print("EXAMPLE 1: Mock Provider")
    print("="*80)
    
    # Create provider
    provider = MockDataProvider()
    
    # Get today's matches
    print("\n📅 Today's Matches:")
    response = provider.get_today_matches()
    
    if response.success:
        print(f"   Found {len(response.data)} matches")
        for match in response.data:
            print(f"   • {match.home_team.name} vs {match.away_team.name}")
            print(f"     Competition: {match.competition.name}")
            print(f"     Time: {match.match_date.strftime('%H:%M')}")
    else:
        print(f"   Error: {response.error}")
    
    # Get match details
    print("\n🔍 Match Details:")
    response = provider.get_match_details("match_001")
    
    if response.success:
        match = response.data
        print(f"   Match: {match.home_team.name} vs {match.away_team.name}")
        print(f"   Competition: {match.competition.name}")
        print(f"   Status: {match.status.value}")
        print(f"   Date: {match.match_date}")
    
    # Get team recent matches
    print("\n📊 Team Recent Matches:")
    response = provider.get_team_recent_matches("london_city", limit=5)
    
    if response.success:
        print(f"   Found {len(response.data)} recent matches")
        for match in response.data:
            home = match.home_team.name
            away = match.away_team.name
            score = f"{match.score_fulltime.home}-{match.score_fulltime.away}"
            print(f"   • {home} {score} {away}")
    
    # Get odds
    print("\n💰 Match Odds:")
    response = provider.get_odds("match_001")
    
    if response.success:
        print(f"   Found {len(response.data)} markets")
        for odds in response.data:
            print(f"   • {odds.market_type}:")
            if odds.under_odds:
                print(f"     Under {odds.line}: {odds.under_odds}")
            if odds.over_odds:
                print(f"     Over {odds.line}: {odds.over_odds}")
            if odds.yes_odds:
                print(f"     Yes: {odds.yes_odds}, No: {odds.no_odds}")


def example_filtered_matches():
    """Example filtering matches"""
    
    print("\n" + "="*80)
    print("EXAMPLE 2: Filtered Matches")
    print("="*80)
    
    provider = MockDataProvider()
    
    # Filter by competition
    print("\n🏆 Women's Championship Matches:")
    response = provider.get_today_matches(
        competition_ids=["eng_women_champ"]
    )
    
    if response.success:
        for match in response.data:
            print(f"   • {match.home_team.name} vs {match.away_team.name}")
    
    # Get competition matches
    print("\n🏆 All U21 Matches:")
    response = provider.get_competition_matches("eng_u21")
    
    if response.success:
        print(f"   Found {len(response.data)} matches")


def example_head_to_head():
    """Example head-to-head"""
    
    print("\n" + "="*80)
    print("EXAMPLE 3: Head-to-Head")
    print("="*80)
    
    provider = MockDataProvider()
    
    response = provider.get_head_to_head("london_city", "bristol_city")
    
    if response.success:
        h2h = response.data
        print(f"\n🔄 {h2h.team_a.name} vs {h2h.team_b.name}")
        print(f"   Total matches: {h2h.total_matches}")
        print(f"   {h2h.team_a.name} wins: {h2h.team_a_wins}")
        print(f"   {h2h.team_b.name} wins: {h2h.team_b_wins}")
        print(f"   Draws: {h2h.draws}")


def example_cache_usage():
    """Example cache usage"""
    
    print("\n" + "="*80)
    print("EXAMPLE 4: Cache Usage")
    print("="*80)
    
    # Create provider with cache
    config = ProviderConfig(
        name="cached_provider",
        cache_enabled=True,
        cache_ttl_seconds=300
    )
    provider = MockDataProvider(config)
    
    # First request (not cached)
    print("\n📥 First request (fetching)...")
    response = provider.get_today_matches()
    print(f"   Cached: {response.cached}")
    
    # Second request (cached)
    print("\n📥 Second request (from cache)...")
    response = provider.get_today_matches()
    print(f"   Cached: {response.cached}")
    if response.cache_age_seconds:
        print(f"   Cache age: {response.cache_age_seconds}s")
    
    # Cache stats
    print("\n📊 Cache Statistics:")
    stats = provider.get_cache_stats()
    print(f"   Enabled: {stats['enabled']}")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    
    # Clear cache
    print("\n🗑️ Clearing cache...")
    provider.clear_cache()
    
    stats = provider.get_cache_stats()
    print(f"   Total files: {stats['total_files']}")


def example_sofascore_provider():
    """Example SofaScore provider (template)"""
    
    print("\n" + "="*80)
    print("EXAMPLE 5: SofaScore Provider (Template)")
    print("="*80)
    
    print("\n⚠️ NOTE: This is a template structure.")
    print("   Before using SofaScore provider:")
    print("   1. Review SofaScore Terms of Service")
    print("   2. Obtain proper API access")
    print("   3. Implement authentication")
    print("   4. Test with rate limiting")
    
    # Example configuration
    config = ProviderConfig(
        name="sofascore",
        enabled=True,
        base_url="https://api.sofascore.com/api/v1",
        rate_limit_per_minute=30,
        cache_enabled=True,
        cache_ttl_seconds=300
    )
    
    print(f"\n📝 Configuration:")
    print(f"   Name: {config.name}")
    print(f"   Base URL: {config.base_url}")
    print(f"   Rate limit: {config.rate_limit_per_minute}/min")
    print(f"   Cache TTL: {config.cache_ttl_seconds}s")
    
    # Uncomment to use (requires proper setup)
    # provider = SofaScoreProvider(config)
    # response = provider.get_today_matches()


def example_error_handling():
    """Example error handling"""
    
    print("\n" + "="*80)
    print("EXAMPLE 6: Error Handling")
    print("="*80)
    
    provider = MockDataProvider()
    
    # Try to get non-existent match
    print("\n❌ Requesting non-existent match:")
    response = provider.get_match_details("nonexistent_id")
    
    if not response.success:
        print(f"   Error: {response.error}")
        print(f"   Provider: {response.provider}")
    
    # Try to get non-existent team
    print("\n❌ Requesting non-existent team:")
    response = provider.get_team_recent_matches("nonexistent_team")
    
    if not response.success:
        print(f"   Error: {response.error}")


def main():
    """Run all examples"""
    
    print("\n" + "="*80)
    print("DATA PROVIDERS USAGE EXAMPLES")
    print("="*80)
    
    example_mock_provider()
    example_filtered_matches()
    example_head_to_head()
    example_cache_usage()
    example_sofascore_provider()
    example_error_handling()
    
    print("\n" + "="*80)
    print("✅ All examples completed")
    print("="*80)


if __name__ == "__main__":
    main()
