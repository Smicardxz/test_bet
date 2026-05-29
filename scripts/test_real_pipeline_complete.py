"""
Test Real Data Pipeline - Complete End-to-End
Validates that the entire pipeline works with real API-Football data
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.providers.data_source_manager import DataSourceManager
from app.services.data.match_data_loader import MatchDataLoader


def test_real_data_pipeline():
    """Test complete real data pipeline"""
    
    print("\n" + "="*60)
    print(" TEST REAL DATA PIPELINE")
    print("="*60 + "\n")
    
    # Check environment
    api_key = os.getenv('API_FOOTBALL_KEY', '')
    provider_type = os.getenv('DATA_PROVIDER', 'api_football')
    
    print(f"📋 Configuration:")
    print(f"   DATA_PROVIDER: {provider_type}")
    print(f"   API_KEY: {'SET' if api_key else 'NOT SET'}")
    print()
    
    if not api_key:
        print("❌ PIPELINE BROKEN:")
        print("   API_FOOTBALL_KEY not set")
        print("   Set it in .env file")
        return False
    
    # Initialize provider
    try:
        manager = DataSourceManager()
        provider = manager.provider
        
        print(f"🔌 Provider: {provider.config.name}")
        print(f"   Is Real: {manager.is_real_data}")
        print()
        
        if not manager.is_real_data:
            print("❌ PIPELINE BROKEN:")
            print("   Using MOCK data instead of REAL")
            return False
            
    except Exception as e:
        print(f"❌ PIPELINE BROKEN:")
        print(f"   Failed to initialize provider: {e}")
        return False
    
    # Step 1: Get fixtures
    print("Step 1: Fetching today's fixtures...")
    try:
        fixtures = provider.get_today_fixtures()
        if not fixtures or len(fixtures) == 0:
            print("   ⚠️  No fixtures today (may be normal)")
            print("   Trying yesterday's fixtures...")
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            fixtures = provider.get_fixtures_by_date(yesterday.date())
        
        if not fixtures or len(fixtures) == 0:
            print("   ❌ No fixtures found")
            return False
        
        print(f"   ✅ Found {len(fixtures)} fixtures")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 2: Select a target match
    print("\nStep 2: Selecting target match...")
    try:
        # Find an upcoming match with teams
        target_match = None
        for fixture in fixtures:
            if (hasattr(fixture, 'home_team') and 
                hasattr(fixture, 'away_team') and
                hasattr(fixture.home_team, 'id')):
                target_match = fixture
                break
        
        if not target_match:
            print("   ❌ No valid match found")
            return False
        
        print(f"   ✅ Selected: {target_match.home_team.name} vs {target_match.away_team.name}")
        print(f"      Fixture ID: {target_match.id}")
        print(f"      Home ID: {target_match.home_team.id}")
        print(f"      Away ID: {target_match.away_team.id}")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 3: Load match data bundle
    print("\nStep 3: Loading match data bundle...")
    try:
        loader = MatchDataLoader(provider)
        
        bundle = loader.load_match_data(
            fixture_id=target_match.id,
            home_team_id=target_match.home_team.id,
            away_team_id=target_match.away_team.id,
            home_team_name=target_match.home_team.name,
            away_team_name=target_match.away_team.name,
            match_date=target_match.match_date,
            history_limit=10
        )
        
        print(f"   ✅ Bundle loaded")
        print(f"      Home history: {bundle.home_history_count}")
        print(f"      Away history: {bundle.away_history_count}")
        print(f"      H2H: {bundle.h2h_count}")
        print(f"      History status: {bundle.history_status}")
        print(f"      Data origin: {bundle.data_origin}")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Validate data origin
    print("\nStep 4: Validating data origin...")
    if bundle.data_origin != "REAL":
        print(f"   ❌ FAIL: Data origin is {bundle.data_origin}, expected REAL")
        return False
    print(f"   ✅ Data origin: REAL")
    
    # Step 5: Check for mock usage
    print("\nStep 5: Checking for mock usage...")
    mock_detected = False
    for match in bundle.home_history + bundle.away_history:
        if match.data_origin != "REAL":
            mock_detected = True
            break
    
    if mock_detected:
        print(f"   ❌ FAIL: Mock data detected in history")
        return False
    print(f"   ✅ No mock data detected")
    
    # Step 6: Extract goal histories
    print("\nStep 6: Extracting goal histories...")
    try:
        ft_goals = bundle.get_ft_goal_history()
        ht_goals = bundle.get_ht_goal_history()
        
        print(f"   ✅ FT goals: {len(ft_goals)} matches")
        if ft_goals:
            print(f"      Sample: {ft_goals[:5]}")
        
        print(f"   ✅ HT goals: {len(ht_goals)} matches")
        if ht_goals:
            print(f"      Sample: {ht_goals[:5]}")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 7: Check data quality
    print("\nStep 7: Checking data quality...")
    
    if bundle.history_status == "MISSING":
        print(f"   ⚠️  WARNING: No historical data available")
    elif bundle.history_status == "INSUFFICIENT":
        print(f"   ⚠️  WARNING: Insufficient data ({bundle.home_history_count + bundle.away_history_count} matches)")
    else:
        print(f"   ✅ Data quality: {bundle.history_status}")
    
    if bundle.errors:
        print(f"   ⚠️  Errors: {bundle.errors}")
    
    if bundle.warnings:
        print(f"   ⚠️  Warnings: {bundle.warnings}")
    
    # Step 8: Check HT/FT availability
    print("\nStep 8: Checking HT/FT data availability...")
    print(f"   HT data available: {bundle.ht_data_available} ({bundle.ht_sample_size} matches)")
    print(f"   FT data available: {bundle.ft_data_available} ({bundle.ft_sample_size} matches)")
    
    # Step 9: Check odds
    print("\nStep 9: Checking odds availability...")
    if bundle.odds_available:
        print(f"   ✅ Odds available: {len(bundle.odds_markets)} markets")
        print(f"      Markets: {list(bundle.odds_markets.keys())[:5]}")
    else:
        print(f"   ⚠️  Odds not available (normal for some fixtures)")
    
    # Final validation
    print("\n" + "="*60)
    print(" VALIDATION SUMMARY")
    print("="*60 + "\n")
    
    checks = {
        "API Key configured": api_key != '',
        "Provider is REAL": manager.is_real_data,
        "Fixtures loaded": len(fixtures) > 0,
        "Match data loaded": bundle is not None,
        "Data origin REAL": bundle.data_origin == "REAL",
        "No mock detected": not mock_detected,
        "FT data available": bundle.ft_data_available,
    }
    
    all_passed = all(checks.values())
    
    for check, passed in checks.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {check}")
    
    print("\n" + "="*60)
    if all_passed:
        print(" ✅ REAL DATA PIPELINE OK")
    else:
        print(" ❌ REAL DATA PIPELINE BROKEN")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = test_real_data_pipeline()
    sys.exit(0 if success else 1)
