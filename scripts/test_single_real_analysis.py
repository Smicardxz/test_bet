"""
Test Single Real Analysis
Valide l'analyse complète d'UN match réel avec API-Football
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner


def test_single_real_analysis():
    """Test complete real analysis of ONE match"""
    
    print("\n" + "="*60)
    print(" TEST SINGLE REAL MATCH ANALYSIS")
    print("="*60 + "\n")
    
    # Check environment
    api_key = os.getenv('API_FOOTBALL_KEY', '')
    provider_type = os.getenv('DATA_PROVIDER', 'api_football')
    
    print(f"📋 Configuration:")
    print(f"   DATA_PROVIDER: {provider_type}")
    print(f"   API_KEY: {'SET' if api_key else 'NOT SET'}")
    print()
    
    if not api_key:
        print("❌ ANALYSIS FAILED:")
        print("   API_FOOTBALL_KEY not set")
        return False
    
    # Initialize
    try:
        manager = DataSourceManager()
        provider = manager.provider
        
        print(f"🔌 Provider: {provider.config.name}")
        print(f"   Is Real: {manager.is_real_data}")
        print()
        
        if not manager.is_real_data:
            print("❌ ANALYSIS FAILED:")
            print("   Using MOCK data instead of REAL")
            return False
            
    except Exception as e:
        print(f"❌ ANALYSIS FAILED:")
        print(f"   Failed to initialize: {e}")
        return False
    
    # Step 1: Get today's fixtures
    print("Step 1: Fetching fixtures...")
    try:
        from datetime import timedelta
        
        # Try today
        response = provider.get_today_matches()
        fixtures = response.data if response and response.data else []
        
        # If no fixtures today, try yesterday
        if not fixtures or len(fixtures) == 0:
            print("   No fixtures today, trying yesterday...")
            yesterday = datetime.now() - timedelta(days=1)
            response = provider.get_competition_matches(competition_id="", match_date=yesterday.date())
            fixtures = response.data if response and response.data else []
        
        if not fixtures or len(fixtures) == 0:
            print("   ❌ No fixtures found")
            return False
        
        print(f"   ✅ Found {len(fixtures)} fixtures")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 2: Select ONE match
    print("\nStep 2: Selecting ONE match for analysis...")
    try:
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
        
        print(f"   ✅ Selected:")
        print(f"      {target_match.home_team.name} vs {target_match.away_team.name}")
        print(f"      Fixture ID: {target_match.id}")
        print(f"      Home ID: {target_match.home_team.id}")
        print(f"      Away ID: {target_match.away_team.id}")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 3: Initialize scanner
    print("\nStep 3: Initializing SmartScanner...")
    try:
        scanner = SmartScanner(
            provider=provider,
            max_analysis=1  # Only analyze ONE match
        )
        print(f"   ✅ Scanner initialized")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False
    
    # Step 4: Analyze the match
    print("\nStep 4: Analyzing match with REAL data...")
    try:
        # Create a simple profile for the match
        from app.services.analysis.league_profile_engine import LeagueProfile
        
        profile = LeagueProfile(
            league_name=target_match.competition.name if hasattr(target_match, 'competition') else 'Test League',
            country=target_match.competition.country if hasattr(target_match, 'competition') else 'Test',
        )
        
        analysis = scanner._analyze_match(target_match, profile)
        
        if not analysis:
            print(f"   ❌ Analysis returned None")
            return False
        
        # Check if it's DATA_INSUFFICIENT
        if analysis.get("status") == "DATA_INSUFFICIENT":
            print(f"   ⚠️  DATA_INSUFFICIENT")
            print(f"      Reason: {analysis.get('reason')}")
            print(f"      This is NORMAL if historical data is missing")
            print(f"      Data origin: {analysis.get('data_origin', 'UNKNOWN')}")
            return True  # Still valid - just no data available
        
        print(f"   ✅ Analysis complete")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Validate data origin
    print("\nStep 5: Validating data origin...")
    debug = analysis.get("debug", {})
    data_origin = debug.get("data_origin", "UNKNOWN")
    
    if data_origin != "REAL":
        print(f"   ❌ FAIL: Data origin is {data_origin}, expected REAL")
        return False
    
    print(f"   ✅ Data origin: REAL")
    
    # Step 6: Check for mock usage
    print("\nStep 6: Checking for mock usage...")
    mock_usage = debug.get("mock_usage", True)
    
    if mock_usage:
        print(f"   ❌ FAIL: Mock usage detected")
        return False
    
    print(f"   ✅ No mock usage detected")
    
    # Step 7: Validate historical data
    print("\nStep 7: Validating historical data...")
    home_count = debug.get("home_history_count", 0)
    away_count = debug.get("away_history_count", 0)
    h2h_count = debug.get("h2h_count", 0)
    
    print(f"   Home history: {home_count} matches")
    print(f"   Away history: {away_count} matches")
    print(f"   H2H: {h2h_count} matches")
    print(f"   Total: {home_count + away_count} matches")
    
    if home_count + away_count == 0:
        print(f"   ⚠️  No historical data (may be normal for some teams)")
    else:
        print(f"   ✅ Historical data loaded")
    
    # Step 8: Validate HT/FT data
    print("\nStep 8: Validating HT/FT data...")
    ht_available = debug.get("ht_data_available", False)
    ft_available = debug.get("ft_data_available", False)
    
    print(f"   HT data: {'✅ AVAILABLE' if ht_available else '⚠️  MISSING'}")
    print(f"   FT data: {'✅ AVAILABLE' if ft_available else '❌ MISSING'}")
    
    # Step 9: Check analysis tables
    print("\nStep 9: Checking analysis tables...")
    
    ht_analysis = analysis.get("ht_analysis", {})
    ft_analysis = analysis.get("ft_analysis", {})
    
    ht_table = ht_analysis.get("table", [])
    ft_table = ft_analysis.get("table", [])
    
    print(f"   HT table: {len(ht_table)} lines")
    print(f"   FT table: {len(ft_table)} lines")
    
    if ft_table:
        print(f"   ✅ FT analysis table generated")
        # Show sample
        if len(ft_table) > 0:
            sample = ft_table[0]
            print(f"      Sample: {sample.get('line')} - Hit rate: {sample.get('hit_rate', 0):.1f}%")
    
    # Step 10: Check signals
    print("\nStep 10: Checking signals...")
    signals = analysis.get("signals", [])
    
    print(f"   Signals detected: {len(signals)}")
    
    if signals:
        print(f"   ✅ Signals generated")
        for i, signal in enumerate(signals[:2], 1):
            print(f"      Signal {i}: {signal.get('type')}")
            print(f"         Confidence: {signal.get('confidence', 0)*100:.0f}%")
            print(f"         Sample size: {signal.get('sample_size', 0)}")
    
    # Final summary
    print("\n" + "="*60)
    print(" ANALYSIS SUMMARY")
    print("="*60 + "\n")
    
    print(f"Match: {target_match.home_team.name} vs {target_match.away_team.name}")
    print()
    print(f"DATA ORIGIN: {data_origin}")
    print(f"MOCK USAGE: {mock_usage}")
    print()
    print(f"HISTORY:")
    print(f"  Home: {home_count}")
    print(f"  Away: {away_count}")
    print(f"  H2H: {h2h_count}")
    print()
    print(f"DATA AVAILABILITY:")
    print(f"  HT: {'YES' if ht_available else 'NO'}")
    print(f"  FT: {'YES' if ft_available else 'NO'}")
    print()
    print(f"ANALYSIS:")
    print(f"  HT lines: {len(ht_table)}")
    print(f"  FT lines: {len(ft_table)}")
    print(f"  Signals: {len(signals)}")
    print()
    
    if debug.get("errors"):
        print(f"ERRORS:")
        for error in debug.get("errors", []):
            print(f"  - {error}")
        print()
    
    if debug.get("warnings"):
        print(f"WARNINGS:")
        for warning in debug.get("warnings", []):
            print(f"  - {warning}")
        print()
    
    # Final validation
    checks = {
        "API Key configured": api_key != '',
        "Provider is REAL": manager.is_real_data,
        "Match selected": target_match is not None,
        "Analysis completed": analysis is not None,
        "Data origin REAL": data_origin == "REAL",
        "No mock usage": not mock_usage,
    }
    
    all_passed = all(checks.values())
    
    print("="*60)
    print(" VALIDATION CHECKS")
    print("="*60 + "\n")
    
    for check, passed in checks.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {check}")
    
    print("\n" + "="*60)
    if all_passed:
        print(" ✅ REAL MATCH ANALYSIS OK")
    else:
        print(" ❌ REAL MATCH ANALYSIS FAILED")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = test_single_real_analysis()
    sys.exit(0 if success else 1)
