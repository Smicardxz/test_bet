"""
Coverage Inspector
Analyzes which target leagues and countries are covered by the provider
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
from collections import defaultdict

from app.providers.api_football_provider import ApiFootballProvider
from app.services.targeting import LeagueTargetingService, TargetMode

load_dotenv()


def main():
    """Inspect coverage of target leagues"""
    
    print("\n" + "="*60)
    print(" COVERAGE INSPECTOR")
    print("="*60 + "\n")
    
    # Check API key
    api_key = os.getenv("API_FOOTBALL_KEY", "")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found in .env")
        return 1
    
    # Initialize
    provider = ApiFootballProvider()
    targeting = LeagueTargetingService(TargetMode.ALL_MINOR)
    
    # Get today's matches
    print("Fetching today's matches...\n")
    response = provider.get_today_matches()
    
    if not response.success:
        print(f"❌ Failed: {response.error}")
        return 1
    
    matches = response.data
    print(f"✅ {len(matches)} matches retrieved\n")
    
    if not matches:
        print("⚠️  No matches today")
        return 0
    
    # Analyze coverage
    print("="*60)
    print(" TARGET COVERAGE ANALYSIS")
    print("="*60 + "\n")
    
    # Target countries
    target_countries = {
        "Kazakhstan", "Uzbekistan", "Georgia", "Armenia", "Azerbaijan",
        "Estonia", "Latvia", "Lithuania",
        "Vietnam", "Thailand", "Indonesia", "Malaysia",
        "Bolivia", "Paraguay", "Ecuador", "Peru", "Venezuela",
        "Albania", "Belarus", "Moldova"
    }
    
    # Categorize matches
    by_category = defaultdict(list)
    by_country = defaultdict(list)
    
    for match in matches:
        country = match.competition.country
        comp_name = match.competition.name
        
        profile = targeting.analyze_competition(comp_name, country)
        
        # Track by country
        by_country[country].append(match)
        
        # Track by category
        if profile.is_women:
            by_category["Women"].append(match)
        if profile.is_youth:
            by_category["Youth"].append(match)
        if profile.is_reserve:
            by_category["Reserve"].append(match)
        if profile.is_lower_league:
            by_category["Lower Division"].append(match)
        if profile.is_obscure:
            by_category["Obscure Country"].append(match)
    
    # Display categories
    print("BY CATEGORY:")
    for category in ["Women", "Youth", "Reserve", "Lower Division", "Obscure Country"]:
        count = len(by_category.get(category, []))
        if count > 0:
            print(f"  ✅ {category}: {count} matches")
        else:
            print(f"  ⚠️  {category}: 0 matches")
    
    # Display target countries
    print(f"\nTARGET COUNTRIES ({len(target_countries)} total):")
    detected = []
    missing = []
    
    for country in sorted(target_countries):
        if country in by_country:
            count = len(by_country[country])
            detected.append(country)
            print(f"  ✅ {country}: {count} matches")
        else:
            missing.append(country)
    
    if missing:
        print(f"\n⚠️  NOT COVERED TODAY ({len(missing)}):")
        for country in missing[:10]:
            print(f"  - {country}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    
    # Display all countries
    print(f"\nALL COUNTRIES COVERED ({len(by_country)}):")
    for country in sorted(by_country.keys())[:20]:
        count = len(by_country[country])
        is_target = "🎯" if country in target_countries else "  "
        print(f"  {is_target} {country}: {count} matches")
    
    if len(by_country) > 20:
        print(f"  ... and {len(by_country) - 20} more countries")
    
    # Women's football
    print("\nWOMEN'S FOOTBALL:")
    women_comps = set()
    for match in matches:
        comp_name = match.competition.name.lower()
        if any(kw in comp_name for kw in ["women", "féminin", "feminine", "frauen", "kvinde"]):
            women_comps.add(f"{match.competition.country} - {match.competition.name}")
    
    if women_comps:
        print(f"  ✅ {len(women_comps)} women's competitions detected:")
        for comp in sorted(women_comps)[:10]:
            print(f"    - {comp}")
    else:
        print("  ⚠️  No women's competitions today")
    
    # Youth football
    print("\nYOUTH FOOTBALL:")
    youth_comps = set()
    for match in matches:
        comp_name = match.competition.name.lower()
        if any(kw in comp_name for kw in ["u21", "u19", "u20", "u23", "u18"]):
            youth_comps.add(f"{match.competition.country} - {match.competition.name}")
    
    if youth_comps:
        print(f"  ✅ {len(youth_comps)} youth competitions detected:")
        for comp in sorted(youth_comps)[:10]:
            print(f"    - {comp}")
    else:
        print("  ⚠️  No youth competitions today")
    
    # Lower divisions
    print("\nLOWER DIVISIONS:")
    lower_comps = set()
    for match in matches:
        comp_name = match.competition.name.lower()
        if any(kw in comp_name for kw in ["division 2", "division 3", "league two", "segunda", "serie b"]):
            lower_comps.add(f"{match.competition.country} - {match.competition.name}")
    
    if lower_comps:
        print(f"  ✅ {len(lower_comps)} lower division competitions:")
        for comp in sorted(lower_comps)[:10]:
            print(f"    - {comp}")
    else:
        print("  ⚠️  No clear lower divisions today")
    
    # Summary
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60 + "\n")
    
    target_match_count = sum(
        len(by_country.get(c, []))
        for c in target_countries
    )
    
    print(f"Total matches: {len(matches)}")
    print(f"Target country matches: {target_match_count}")
    print(f"Target countries detected: {len(detected)}/{len(target_countries)}")
    print(f"Women's competitions: {len(women_comps)}")
    print(f"Youth competitions: {len(youth_comps)}")
    print(f"Lower divisions: {len(lower_comps)}")
    
    if target_match_count > 0:
        print(f"\n✅ STRATEGY VIABLE - {target_match_count} target matches available")
    else:
        print(f"\n⚠️  LOW COVERAGE - Consider checking on match days")
    
    print("\n" + "="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
