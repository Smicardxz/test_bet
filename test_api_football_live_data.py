#!/usr/bin/env python3
"""
test_api_football_live_data.py
===============================
Test API-Football live data directly.
"""

import sys
import os
import requests
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def test_api_football_live_data():
    """Test API-Football live data directly."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 API-FOOTBALL LIVE DATA TEST")
    print(f"{'='*80}{RESET}")
    
    api_key = os.getenv("API_FOOTBALL_KEY", "")
    api_url = os.getenv("API_FOOTBALL_URL", "https://v3.football.api-sports.io")
    
    if not api_key:
        print(f"  {RED}❌ API_FOOTBALL_KEY not found{RESET}")
        return False
    
    print(f"\n{CYAN}Configuration:{RESET}")
    print(f"  API Key: {'*' * 10}...{api_key[-4:]}")
    print(f"  API URL: {api_url}")
    
    # Test live fixtures endpoint
    print(f"\n{BOLD}🔍 TESTING LIVE FIXTURES ENDPOINT{RESET}")
    print(f"{'='*60}")
    
    try:
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        
        # Get live fixtures
        response = requests.get(f"{api_url}/fixtures?live=all", headers=headers, timeout=15)
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  {RED}❌ Failed to fetch live fixtures: {response.status_code}{RESET}")
            print(f"  Response: {response.text[:200]}...")
            return False
        
        data = response.json()
        
        if data.get("errors"):
            print(f"  {RED}❌ API errors: {data['errors']}{RESET}")
            return False
        
        fixtures = data.get("response", [])
        print(f"  Live fixtures found: {len(fixtures)}")
        
        if not fixtures:
            print(f"  {YELLOW}⚠️  No live fixtures found{RESET}")
            return False
        
        # Analyze first few fixtures
        print(f"\n{BOLD}🔍 ANALYZING FIRST 5 LIVE FIXTURES{RESET}")
        print(f"{'='*80}")
        
        print(f"{'Fixture ID':<12} {'Match':<30} {'Status':<8} {'Home':<4} {'Away':<4} {'Min':<4} {'HT_H':<4} {'HT_A':<4}")
        print(f"{'-'*80}")
        
        fixtures_with_scores = 0
        fixtures_with_minute = 0
        
        for i, fixture in enumerate(fixtures[:5]):
            fixture_info = fixture.get("fixture", {})
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            score = fixture.get("score", {})
            
            fixture_id = str(fixture_info.get("id", ""))[:10]
            home_team = teams.get("home", {}).get("name", "Unknown")[:14]
            away_team = teams.get("away", {}).get("name", "Unknown")[:14]
            match_name = f"{home_team} vs {away_team}"
            status = fixture_info.get("status", {}).get("short", "NS")[:6]
            
            home_score = goals.get("home")
            away_score = goals.get("away")
            ht_home = score.get("halftime", {}).get("home")
            ht_away = score.get("halftime", {}).get("away")
            minute = fixture_info.get("status", {}).get("elapsed")
            
            if home_score is not None and away_score is not None:
                fixtures_with_scores += 1
            
            if minute is not None:
                fixtures_with_minute += 1
            
            home_str = str(home_score) if home_score is not None else "—"
            away_str = str(away_score) if away_score is not None else "—"
            minute_str = str(minute) if minute is not None else "—"
            ht_home_str = str(ht_home) if ht_home is not None else "—"
            ht_away_str = str(ht_away) if ht_away is not None else "—"
            
            print(f"{fixture_id:<12} {match_name:<30} {status:<8} {home_str:<4} {away_str:<4} {minute_str:<4} {ht_home_str:<4} {ht_away_str:<4}")
        
        print(f"\n{CYAN}Summary:{RESET}")
        print(f"  Fixtures with scores: {fixtures_with_scores}/{len(fixtures[:5])}")
        print(f"  Fixtures with minute: {fixtures_with_minute}/{len(fixtures[:5])}")
        
        # Show detailed structure of one fixture
        print(f"\n{BOLD}🔍 DETAILED STRUCTURE OF FIRST FIXTURE{RESET}")
        print(f"{'='*60}")
        
        first_fixture = fixtures[0]
        
        print(f"\n{CYAN}Fixture Info:{RESET}")
        fixture_info = first_fixture.get("fixture", {})
        for key, value in fixture_info.items():
            if key in ["id", "status", "date", "elapsed"]:
                print(f"  {key}: {value}")
        
        print(f"\n{CYAN}Goals:{RESET}")
        goals = first_fixture.get("goals", {})
        for key, value in goals.items():
            print(f"  {key}: {value}")
        
        print(f"\n{CYAN}Score:{RESET}")
        score = first_fixture.get("score", {})
        for key, value in score.items():
            print(f"  {key}: {value}")
        
        # Test today's fixtures to see if they have scores
        print(f"\n{BOLD}🔍 TESTING TODAY'S FIXTUREES{RESET}")
        print(f"{'='*60}")
        
        today = date.today().isoformat()
        response = requests.get(f"{api_url}/fixtures?date={today}", headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            today_fixtures = data.get("response", [])
            print(f"  Today's fixtures: {len(today_fixtures)}")
            
            # Check live ones
            today_live = [f for f in today_fixtures if f.get("fixture", {}).get("status", {}).get("short") in ["1H", "2H", "HT", "ET", "P", "LIVE"]]
            print(f"  Today's live fixtures: {len(today_live)}")
            
            if today_live:
                print(f"\n{CYAN}Sample today live fixture:{RESET}")
                sample = today_live[0]
                print(f"  ID: {sample.get('fixture', {}).get('id')}")
                print(f"  Status: {sample.get('fixture', {}).get('status', {})}")
                print(f"  Goals: {sample.get('goals', {})}")
                print(f"  Score: {sample.get('score', {})}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}❌ Test failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_api_football_live_data()
    sys.exit(0 if success else 1)
