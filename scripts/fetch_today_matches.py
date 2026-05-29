"""
Fetch Today's Matches Script
Retrieves today's matches from SofaScore and displays/saves them
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.sofascore_provider import SofaScoreProvider
from app.providers import MockDataProvider, ProviderConfig


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def display_match(match, index: int):
    """Display match information"""
    print(f"\n{'='*80}")
    print(f"Match #{index + 1}")
    print(f"{'='*80}")
    
    print(f"\n🏟️  {match.home_team.name} vs {match.away_team.name}")
    print(f"🏆 Competition: {match.competition.name}")
    if match.competition.country:
        print(f"🌍 Country: {match.competition.country}")
    print(f"📅 Date: {match.match_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 Status: {match.status.value}")
    
    if match.score_fulltime:
        print(f"⚽ Score FT: {match.score_fulltime.home} - {match.score_fulltime.away}")
    
    if match.score_halftime:
        print(f"⚽ Score HT: {match.score_halftime.home} - {match.score_halftime.away}")
    
    if match.venue:
        print(f"🏟️  Venue: {match.venue}")
    
    print(f"🔗 URL: {match.provider_url}")
    
    # Obscure indicator
    if match.competition.is_obscure:
        print(f"✅ Obscure league: YES")
    else:
        print(f"❌ Obscure league: NO")


def save_matches_to_file(matches, filename: str = "today_matches.json"):
    """Save matches to JSON file"""
    output_dir = Path("data/fetched")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / filename
    
    # Convert to dict
    matches_data = []
    for match in matches:
        match_dict = {
            "id": match.id,
            "home_team": {
                "id": match.home_team.id,
                "name": match.home_team.name
            },
            "away_team": {
                "id": match.away_team.id,
                "name": match.away_team.name
            },
            "competition": {
                "id": match.competition.id,
                "name": match.competition.name,
                "country": match.competition.country,
                "is_obscure": match.competition.is_obscure
            },
            "match_date": match.match_date.isoformat(),
            "status": match.status.value,
            "score_fulltime": {
                "home": match.score_fulltime.home,
                "away": match.score_fulltime.away
            } if match.score_fulltime else None,
            "score_halftime": {
                "home": match.score_halftime.home,
                "away": match.score_halftime.away
            } if match.score_halftime else None,
            "venue": match.venue,
            "provider": match.provider,
            "provider_url": match.provider_url
        }
        matches_data.append(match_dict)
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "fetched_at": datetime.utcnow().isoformat(),
            "total_matches": len(matches_data),
            "matches": matches_data
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(matches_data)} matches to {output_file}")
    return output_file


def fetch_with_sofascore():
    """Fetch matches using SofaScore provider"""
    
    print("\n" + "="*80)
    print("FETCHING TODAY'S MATCHES FROM SOFASCORE")
    print("="*80)
    
    # Create provider
    config = ProviderConfig(
        name="sofascore",
        rate_limit_per_minute=30,
        cache_enabled=True,
        cache_ttl_seconds=300
    )
    
    provider = SofaScoreProvider(config)
    
    # Fetch matches
    print("\n📥 Fetching matches...")
    response = provider.get_today_matches()
    
    if not response.success:
        print(f"\n❌ Error: {response.error}")
        return []
    
    matches = response.data
    
    print(f"\n✅ Successfully fetched {len(matches)} matches")
    
    if response.cached:
        print(f"📦 From cache (age: {response.cache_age_seconds}s)")
    else:
        print(f"🌐 Fresh from API")
    
    return matches


def fetch_with_mock():
    """Fetch matches using Mock provider (for testing)"""
    
    print("\n" + "="*80)
    print("FETCHING TODAY'S MATCHES FROM MOCK PROVIDER")
    print("="*80)
    
    provider = MockDataProvider()
    
    print("\n📥 Fetching matches...")
    response = provider.get_today_matches()
    
    if not response.success:
        print(f"\n❌ Error: {response.error}")
        return []
    
    matches = response.data
    print(f"\n✅ Successfully fetched {len(matches)} matches")
    
    return matches


def main():
    """Main function"""
    
    print("\n" + "="*80)
    print("🔍 FETCH TODAY'S MATCHES")
    print("="*80)
    
    # Ask user which provider to use
    print("\nSelect provider:")
    print("  1. SofaScore (real data)")
    print("  2. Mock (test data)")
    
    choice = input("\nChoice [1/2]: ").strip()
    
    if choice == "2":
        matches = fetch_with_mock()
    else:
        matches = fetch_with_sofascore()
    
    if not matches:
        print("\n❌ No matches fetched")
        return 1
    
    # Display matches
    print("\n" + "="*80)
    print(f"DISPLAYING {len(matches)} MATCHES")
    print("="*80)
    
    for i, match in enumerate(matches):
        display_match(match, i)
    
    # Save to file
    print("\n" + "="*80)
    print("SAVING MATCHES")
    print("="*80)
    
    output_file = save_matches_to_file(matches)
    print(f"\n✅ Matches saved to: {output_file}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print(f"\nTotal matches: {len(matches)}")
    
    # Count by competition
    competitions = {}
    for match in matches:
        comp_name = match.competition.name
        competitions[comp_name] = competitions.get(comp_name, 0) + 1
    
    print(f"\nBy competition:")
    for comp, count in sorted(competitions.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {comp}: {count} matches")
    
    # Count obscure
    obscure_count = sum(1 for m in matches if m.competition.is_obscure)
    print(f"\nObscure leagues: {obscure_count}/{len(matches)} ({obscure_count/len(matches)*100:.1f}%)")
    
    print("\n" + "="*80)
    print("✅ DONE")
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
