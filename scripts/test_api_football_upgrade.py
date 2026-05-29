"""
Test API-Football Upgrade
Diagnostic complet des capacités après upgrade
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.providers.api_football_provider import ApiFootballProvider


def test_fixture(provider: ApiFootballProvider, fixture, test_num: int, total: int) -> Dict[str, Any]:
    """Test a single fixture comprehensively"""
    
    fixture_id = getattr(fixture, 'id', '?')
    home_team = fixture.home_team.name
    away_team = fixture.away_team.name
    
    print("\n" + "="*100)
    print(f" TEST {test_num}/{total} - Fixture {fixture_id}")
    print("="*100)
    
    result = {
        "fixture_id": fixture_id,
        "home_team": home_team,
        "away_team": away_team,
        "country": fixture.competition.country,
        "league": fixture.competition.name,
        "status": getattr(fixture.status, 'short', '?'),
        "kickoff": str(fixture.match_date),
        "home_history_count": 0,
        "away_history_count": 0,
        "h2h_count": 0,
        "home_ht_scores": False,
        "away_ht_scores": False,
        "odds_available": False,
        "odds_bookmakers": 0,
        "odds_markets": [],
        "analyzable_status": "UNKNOWN",
        "errors": []
    }
    
    # 1. FIXTURE INFO
    print(f"\n[1] FIXTURE INFO")
    print(f"    Match: {home_team} vs {away_team}")
    print(f"    Country: {result['country']}")
    print(f"    League: {result['league']}")
    print(f"    Status: {result['status']}")
    print(f"    Kickoff: {result['kickoff']}")
    
    # 2. HOME TEAM HISTORY
    print(f"\n[2] HOME TEAM HISTORY - {home_team} (ID: {fixture.home_team.id})")
    try:
        home_history = provider.get_team_recent_matches(
            team_id=fixture.home_team.id,
            limit=10,
            before_date=fixture.match_date
        )
        result["home_history_count"] = len(home_history)
        print(f"    Raw count: {len(home_history)}")
        
        if home_history:
            # Check HT scores
            ht_scores_present = sum(1 for m in home_history if m.score_halftime is not None)
            result["home_ht_scores"] = ht_scores_present > 0
            print(f"    HT scores present: {ht_scores_present}/{len(home_history)}")
            print(f"    Latest match: {home_history[0].match_date}")
            if home_history[0].score_fulltime:
                print(f"    Sample: {home_history[0].home_team.name} {home_history[0].score_fulltime.home}-{home_history[0].score_fulltime.away} {home_history[0].away_team.name}")
            if home_history[0].score_halftime:
                print(f"    HT score: {home_history[0].score_halftime.home}-{home_history[0].score_halftime.away}")
        else:
            print(f"    [WARNING] No history found")
            
    except Exception as e:
        print(f"    [ERROR] {e}")
        result["errors"].append(f"home_history: {e}")
    
    # 3. AWAY TEAM HISTORY
    print(f"\n[3] AWAY TEAM HISTORY - {away_team} (ID: {fixture.away_team.id})")
    try:
        away_history = provider.get_team_recent_matches(
            team_id=fixture.away_team.id,
            limit=10,
            before_date=fixture.match_date
        )
        result["away_history_count"] = len(away_history)
        print(f"    Raw count: {len(away_history)}")
        
        if away_history:
            # Check HT scores
            ht_scores_present = sum(1 for m in away_history if m.score_halftime is not None)
            result["away_ht_scores"] = ht_scores_present > 0
            print(f"    HT scores present: {ht_scores_present}/{len(away_history)}")
            print(f"    Latest match: {away_history[0].match_date}")
        else:
            print(f"    [WARNING] No history found")
            
    except Exception as e:
        print(f"    [ERROR] {e}")
        result["errors"].append(f"away_history: {e}")
    
    # 4. HEAD-TO-HEAD
    print(f"\n[4] HEAD-TO-HEAD")
    try:
        h2h = provider.get_head_to_head(
            home_team_id=fixture.home_team.id,
            away_team_id=fixture.away_team.id,
            limit=10,
            before_date=fixture.match_date
        )
        result["h2h_count"] = len(h2h)
        print(f"    Raw count: {len(h2h)}")
        
        if h2h:
            print(f"    Latest H2H: {h2h[0].match_date}")
            if h2h[0].score_fulltime:
                print(f"    Sample: {h2h[0].home_team.name} {h2h[0].score_fulltime.home}-{h2h[0].score_fulltime.away} {h2h[0].away_team.name}")
        else:
            print(f"    [INFO] No H2H found (not critical)")
            
    except Exception as e:
        print(f"    [ERROR] {e}")
        result["errors"].append(f"h2h: {e}")
    
    # 5. ODDS
    print(f"\n[5] ODDS")
    try:
        odds = provider.get_fixture_odds(int(fixture_id))
        
        if odds:
            result["odds_available"] = True
            result["odds_bookmakers"] = len(odds.bookmakers) if hasattr(odds, 'bookmakers') else 0
            
            # Check available markets
            markets = []
            if hasattr(odds, 'match_winner'):
                markets.append("match_winner")
            if hasattr(odds, 'over_under'):
                markets.append("over_under")
            if hasattr(odds, 'both_teams_score'):
                markets.append("btts")
            
            result["odds_markets"] = markets
            
            print(f"    [OK] Odds available")
            print(f"    Bookmakers: {result['odds_bookmakers']}")
            print(f"    Markets: {', '.join(markets)}")
        else:
            print(f"    [WARNING] No odds available")
            
    except Exception as e:
        print(f"    [ERROR] {e}")
        result["errors"].append(f"odds: {e}")
    
    # 6. ANALYSIS
    print(f"\n[6] ANALYSIS")
    
    # Determine analyzable status
    has_home_history = result["home_history_count"] > 0
    has_away_history = result["away_history_count"] > 0
    has_ht_scores = result["home_ht_scores"] and result["away_ht_scores"]
    has_odds = result["odds_available"]
    
    if not has_home_history or not has_away_history:
        result["analyzable_status"] = "HISTORY_MISSING"
        print(f"    Status: HISTORY_MISSING")
        print(f"    Reason: home={result['home_history_count']}, away={result['away_history_count']}")
    elif not has_ht_scores:
        result["analyzable_status"] = "HT_MISSING"
        print(f"    Status: HT_MISSING")
        print(f"    Reason: HT scores not available in history")
    elif not has_odds:
        result["analyzable_status"] = "ANALYZABLE_NO_ODDS"
        print(f"    Status: ANALYZABLE_NO_ODDS")
        print(f"    Can analyze: YES (without odds)")
    else:
        result["analyzable_status"] = "ANALYZABLE_FULL"
        print(f"    Status: ANALYZABLE_FULL")
        print(f"    Can analyze: YES (with odds)")
    
    # Report what can be analyzed
    if has_home_history and has_away_history:
        print(f"    Data available for:")
        print(f"      - FT analysis: YES ({result['home_history_count'] + result['away_history_count']} matches)")
        
        if has_ht_scores:
            print(f"      - HT analysis: YES")
        else:
            print(f"      - HT analysis: NO (HT scores missing)")
        
        if has_odds:
            print(f"      - Fair odds calculation: YES")
            print(f"      - Signal generation: YES")
        else:
            print(f"      - Fair odds calculation: NO (odds missing)")
            print(f"      - Signal generation: PARTIAL (statistical only)")
    
    return result


def main():
    """Main test function"""
    
    print("\n" + "="*100)
    print(" API-FOOTBALL UPGRADE TEST")
    print("="*100)
    
    # Initialize provider
    print("\n[INIT] Initializing provider...")
    manager = DataSourceManager()
    provider = manager.provider
    
    if not isinstance(provider, ApiFootballProvider):
        print(f"[ERROR] Provider is {type(provider).__name__}, not ApiFootballProvider")
        print("   Set DATA_PROVIDER=api_football in .env")
        return False
    
    print(f"[OK] Provider: {provider.config.name}")
    
    # Get today's matches
    print(f"\n[FETCH] Fetching today's matches...")
    today_response = provider.get_today_matches()
    
    if not today_response or not today_response.data:
        print(f"[ERROR] Could not fetch today's matches")
        return False
    
    all_matches = today_response.data
    print(f"[OK] Found {len(all_matches)} matches today")
    
    # Select 5-10 target matches (prefer upcoming, diverse leagues)
    test_matches = []
    seen_leagues = set()
    
    for match in all_matches:
        # Prefer upcoming matches
        status = getattr(match.status, 'short', '?')
        if status in ['NS', 'TBD']:  # Not started
            league = match.competition.name
            # Diversify leagues
            if league not in seen_leagues or len(test_matches) < 5:
                test_matches.append(match)
                seen_leagues.add(league)
                if len(test_matches) >= 10:
                    break
    
    # If not enough upcoming, add some live/finished
    if len(test_matches) < 5:
        for match in all_matches:
            if match not in test_matches:
                test_matches.append(match)
                if len(test_matches) >= 10:
                    break
    
    print(f"\n[SELECT] Testing {len(test_matches)} matches")
    
    # Test each match
    results = []
    for i, match in enumerate(test_matches, 1):
        result = test_fixture(provider, match, i, len(test_matches))
        results.append(result)
    
    # FINAL SUMMARY
    print("\n" + "="*100)
    print(" FINAL SUMMARY")
    print("="*100)
    
    total_tested = len(results)
    with_home_history = sum(1 for r in results if r["home_history_count"] > 0)
    with_away_history = sum(1 for r in results if r["away_history_count"] > 0)
    with_both_history = sum(1 for r in results if r["home_history_count"] > 0 and r["away_history_count"] > 0)
    with_ht_scores = sum(1 for r in results if r["home_ht_scores"] and r["away_ht_scores"])
    with_h2h = sum(1 for r in results if r["h2h_count"] > 0)
    with_odds = sum(1 for r in results if r["odds_available"])
    
    analyzable_full = sum(1 for r in results if r["analyzable_status"] == "ANALYZABLE_FULL")
    analyzable_no_odds = sum(1 for r in results if r["analyzable_status"] == "ANALYZABLE_NO_ODDS")
    history_missing = sum(1 for r in results if r["analyzable_status"] == "HISTORY_MISSING")
    ht_missing = sum(1 for r in results if r["analyzable_status"] == "HT_MISSING")
    
    print(f"\nMatches Tested: {total_tested}")
    print(f"\nData Availability:")
    print(f"  - Home history:      {with_home_history}/{total_tested} ({with_home_history*100//total_tested if total_tested else 0}%)")
    print(f"  - Away history:      {with_away_history}/{total_tested} ({with_away_history*100//total_tested if total_tested else 0}%)")
    print(f"  - Both histories:    {with_both_history}/{total_tested} ({with_both_history*100//total_tested if total_tested else 0}%)")
    print(f"  - HT scores:         {with_ht_scores}/{total_tested} ({with_ht_scores*100//total_tested if total_tested else 0}%)")
    print(f"  - H2H:               {with_h2h}/{total_tested} ({with_h2h*100//total_tested if total_tested else 0}%)")
    print(f"  - Odds:              {with_odds}/{total_tested} ({with_odds*100//total_tested if total_tested else 0}%)")
    
    print(f"\nAnalyzable Status:")
    print(f"  - ANALYZABLE_FULL:    {analyzable_full}/{total_tested} (history + HT + odds)")
    print(f"  - ANALYZABLE_NO_ODDS: {analyzable_no_odds}/{total_tested} (history + HT, no odds)")
    print(f"  - HT_MISSING:         {ht_missing}/{total_tested} (history OK, no HT scores)")
    print(f"  - HISTORY_MISSING:    {history_missing}/{total_tested} (no history)")
    
    # Detailed breakdown
    print(f"\nDetailed Results:")
    print(f"{'Fixture':<10} {'Match':<40} {'League':<25} {'Hist':<6} {'HT':<4} {'Odds':<5} {'Status':<20}")
    print("-" * 120)
    
    for r in results:
        match_str = f"{r['home_team'][:15]} vs {r['away_team'][:15]}"
        hist_str = f"{r['home_history_count']}/{r['away_history_count']}"
        ht_str = "YES" if r['home_ht_scores'] and r['away_ht_scores'] else "NO"
        odds_str = "YES" if r['odds_available'] else "NO"
        
        print(f"{r['fixture_id']:<10} {match_str:<40} {r['league'][:24]:<25} {hist_str:<6} {ht_str:<4} {odds_str:<5} {r['analyzable_status']:<20}")
    
    # Errors
    errors_count = sum(len(r["errors"]) for r in results)
    if errors_count > 0:
        print(f"\n[WARNING] {errors_count} errors encountered")
        for r in results:
            if r["errors"]:
                print(f"  Fixture {r['fixture_id']}: {', '.join(r['errors'])}")
    
    # Success criteria
    print(f"\n" + "="*100)
    print(" UPGRADE ASSESSMENT")
    print("="*100)
    
    if with_both_history >= total_tested * 0.7:  # 70%+
        print(f"\n[OK] History availability: EXCELLENT ({with_both_history}/{total_tested})")
    elif with_both_history >= total_tested * 0.5:  # 50%+
        print(f"\n[OK] History availability: GOOD ({with_both_history}/{total_tested})")
    else:
        print(f"\n[WARNING] History availability: LIMITED ({with_both_history}/{total_tested})")
    
    if with_ht_scores >= with_both_history * 0.8:  # 80% of those with history
        print(f"[OK] HT scores availability: EXCELLENT ({with_ht_scores}/{with_both_history})")
    else:
        print(f"[WARNING] HT scores availability: LIMITED ({with_ht_scores}/{with_both_history})")
    
    if with_odds >= total_tested * 0.5:  # 50%+
        print(f"[OK] Odds availability: GOOD ({with_odds}/{total_tested})")
    else:
        print(f"[INFO] Odds availability: LIMITED ({with_odds}/{total_tested}) - May require specific tier")
    
    if analyzable_full + analyzable_no_odds >= total_tested * 0.5:
        print(f"\n[SUCCESS] Upgrade is EFFECTIVE - {analyzable_full + analyzable_no_odds}/{total_tested} matches analyzable")
        return True
    else:
        print(f"\n[WARNING] Upgrade has LIMITED impact - Only {analyzable_full + analyzable_no_odds}/{total_tested} matches analyzable")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
