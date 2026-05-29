"""
Test API-Football Connection
Validates API connection and displays real data coverage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
from app.providers.api_football_provider import ApiFootballProvider
from app.services.targeting import LeagueTargetingService, TargetMode

# Load environment variables
load_dotenv()


def print_section(title: str):
    """Print section header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def main():
    """Test API-Football connection and coverage"""
    
    print("\n🔍 Testing API-Football Connection...\n")
    
    # Check API key
    api_key = os.getenv("API_FOOTBALL_KEY", "")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found in .env file")
        print("\nCreate .env file with:")
        print("API_FOOTBALL_KEY=your_key_here")
        print("API_FOOTBALL_URL=https://v3.football.api-sports.io")
        return 1
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Initialize provider
    try:
        provider = ApiFootballProvider()
        print(f"✅ Provider initialized: {provider.base_url}")
    except Exception as e:
        print(f"❌ Failed to initialize provider: {e}")
        return 1
    
    # =========================================================================
    # TEST CONNECTION
    # =========================================================================
    
    print_section("API STATUS")
    
    status = provider.test_connection()
    
    if status.get("api_reachable"):
        print("✅ API reachable")
    else:
        print("❌ API not reachable")
        print(f"   Error: {status.get('error')}")
        return 1
    
    if status.get("key_valid"):
        print("✅ Key valid")
    else:
        print("❌ Key invalid")
        print(f"   Error: {status.get('error')}")
        return 1
    
    # Display quota info
    requests_info = status.get("requests", {})
    if requests_info:
        print(f"\nQuota Information:")
        print(f"  Current: {requests_info.get('current', 'N/A')}")
        print(f"  Limit: {requests_info.get('limit_day', 'N/A')} per day")
    
    subscription = status.get("subscription", {})
    if subscription:
        print(f"\nSubscription:")
        print(f"  Plan: {subscription.get('plan', 'N/A')}")
        print(f"  End: {subscription.get('end', 'N/A')}")
    
    # =========================================================================
    # GET TODAY'S MATCHES
    # =========================================================================
    
    print_section("TODAY MATCHES")
    
    print("Fetching today's matches...")
    response = provider.get_today_matches()
    
    if not response.success:
        print(f"❌ Failed to fetch matches: {response.error}")
        return 1
    
    matches = response.data
    print(f"✅ {len(matches)} matches retrieved")
    
    if not matches:
        print("\n⚠️  No matches today")
        print("   This is normal if there are no scheduled games")
        return 0
    
    # Analyze matches
    countries = set()
    competitions = {}
    
    for match in matches:
        country = match.competition.country
        comp_name = match.competition.name
        
        countries.add(country)
        
        if country not in competitions:
            competitions[country] = set()
        competitions[country].add(comp_name)
    
    print(f"\nCountries: {len(countries)}")
    print(f"Competitions: {sum(len(comps) for comps in competitions.values())}")
    
    # Show top competitions
    print("\nTop 20 Competitions:")
    all_comps = []
    for country, comps in competitions.items():
        for comp in comps:
            all_comps.append(f"{country} - {comp}")
    
    for i, comp in enumerate(sorted(all_comps)[:20], 1):
        print(f"  {i:2d}. {comp}")
    
    # =========================================================================
    # TARGET LEAGUES ANALYSIS
    # =========================================================================
    
    print_section("TARGET LEAGUES")
    
    targeting = LeagueTargetingService(TargetMode.ALL_MINOR)
    
    target_matches = []
    for match in matches:
        profile = targeting.analyze_competition(
            match.competition.name,
            match.competition.country
        )
        
        if targeting.should_include(profile):
            target_matches.append({
                "match": match,
                "profile": profile
            })
    
    print(f"✅ {len(target_matches)} matches match targeting strategy")
    
    # Categorize
    women = sum(1 for m in target_matches if m["profile"].is_women)
    youth = sum(1 for m in target_matches if m["profile"].is_youth)
    reserve = sum(1 for m in target_matches if m["profile"].is_reserve)
    lower = sum(1 for m in target_matches if m["profile"].is_lower_league)
    obscure = sum(1 for m in target_matches if m["profile"].is_obscure)
    
    print(f"\nCategories:")
    print(f"  Women: {women}")
    print(f"  Youth: {youth}")
    print(f"  Reserve: {reserve}")
    print(f"  Lower Division: {lower}")
    print(f"  Obscure Country: {obscure}")
    
    # Show target countries
    target_countries = {
        "Kazakhstan", "Uzbekistan", "Georgia", "Armenia",
        "Vietnam", "Thailand", "Indonesia",
        "Bolivia", "Paraguay", "Ecuador", "Peru"
    }
    
    detected_targets = countries & target_countries
    if detected_targets:
        print(f"\n✅ Target countries detected: {', '.join(sorted(detected_targets))}")
    else:
        print(f"\n⚠️  No priority target countries detected today")
    
    # =========================================================================
    # ODDS CHECK
    # =========================================================================
    
    print_section("ODDS")
    
    if matches:
        print("Checking odds for first match...")
        first_match = matches[0]
        odds_response = provider.get_odds_for_fixture(first_match.id)
        
        if odds_response.success and odds_response.data:
            print(f"✅ Odds available")
            print(f"   Bookmakers: {len(odds_response.data)}")
            
            # Show available markets
            markets = set()
            for odds_data in odds_response.data:
                for bet in odds_data.get("bets", []):
                    markets.add(bet.get("name", ""))
            
            print(f"   Markets: {len(markets)}")
            if markets:
                print(f"   Available: {', '.join(sorted(list(markets))[:10])}")
        else:
            print(f"⚠️  Odds not available")
            print(f"   Error: {odds_response.error}")
    
    # =========================================================================
    # SAMPLE MATCHES
    # =========================================================================
    
    print_section("SAMPLE MATCHES")
    
    print("\nShowing 10 real matches:\n")
    
    for i, match in enumerate(matches[:10], 1):
        kickoff = match.match_date.strftime("%H:%M")
        print(f"{i:2d}. {match.home_team.name} vs {match.away_team.name}")
        print(f"    {match.competition.name} ({match.competition.country})")
        print(f"    Kickoff: {kickoff} UTC")
        print()
    
    # =========================================================================
    # FINAL VERDICT
    # =========================================================================
    
    print_section("FINAL VERDICT")
    
    print("\n✅ REAL DATA CONNECTED")
    print(f"   - API is reachable and key is valid")
    print(f"   - {len(matches)} matches retrieved for today")
    print(f"   - {len(target_matches)} matches match targeting strategy")
    print(f"   - {len(countries)} countries covered")
    
    if len(target_matches) == 0:
        print("\n⚠️  WARNING: No target matches found today")
        print("   This may be normal depending on the day")
        print("   Try again on a day with more matches")
    
    print("\n" + "="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
