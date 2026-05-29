"""
Audit Real Data Endpoints
Vérifie que AUCUNE donnée mockée n'est utilisée en mode API réel
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.providers.data_source_manager import DataSourceManager


def audit_endpoints():
    """Audit all endpoints and mock usage"""
    
    print("\n" + "="*60)
    print(" AUDIT REAL DATA ENDPOINTS")
    print("="*60 + "\n")
    
    # Check config
    provider_type = os.getenv('DATA_PROVIDER', 'api_football')
    api_key = os.getenv('API_FOOTBALL_KEY', '')
    
    print(f"📋 Configuration:")
    print(f"   DATA_PROVIDER: {provider_type}")
    print(f"   API_KEY: {'SET' if api_key else 'NOT SET'}")
    print()
    
    # Initialize manager
    manager = DataSourceManager()
    provider = manager.provider
    
    print(f"🔌 Provider: {provider.config.name}")
    print(f"   Is Real: {manager.is_real_data}")
    print()
    
    # Test endpoints
    results = {}
    
    print("🧪 Testing Endpoints:\n")
    
    # 1. Fixtures endpoint
    print("1. Fixtures du jour...")
    try:
        fixtures = provider.get_today_fixtures()
        if fixtures and len(fixtures) > 0:
            print(f"   ✅ OK - {len(fixtures)} fixtures récupérées")
            results['fixtures'] = 'OK'
        else:
            print(f"   ⚠️  EMPTY - Aucune fixture (peut être normal)")
            results['fixtures'] = 'EMPTY'
    except Exception as e:
        print(f"   ❌ FAIL - {str(e)}")
        results['fixtures'] = 'FAIL'
    
    # 2. Live status
    print("\n2. Live status...")
    try:
        # Check if fixtures have live status
        if fixtures and len(fixtures) > 0:
            has_status = hasattr(fixtures[0], 'status')
            if has_status:
                print(f"   ✅ OK - Status disponible sur fixtures")
                results['live_status'] = 'OK'
            else:
                print(f"   ❌ FAIL - Pas de status sur fixtures")
                results['live_status'] = 'FAIL'
        else:
            print(f"   ⚠️  SKIP - Pas de fixtures pour tester")
            results['live_status'] = 'SKIP'
    except Exception as e:
        print(f"   ❌ FAIL - {str(e)}")
        results['live_status'] = 'FAIL'
    
    # 3. Team history endpoint
    print("\n3. Team history endpoint...")
    try:
        # Check if method exists
        if hasattr(provider, 'get_team_history'):
            print(f"   ⚠️  METHOD EXISTS but not tested (need team_id)")
            results['team_history'] = 'NOT_TESTED'
        else:
            print(f"   ❌ FAIL - Method get_team_history NOT FOUND")
            results['team_history'] = 'NOT_IMPLEMENTED'
    except Exception as e:
        print(f"   ❌ FAIL - {str(e)}")
        results['team_history'] = 'FAIL'
    
    # 4. H2H endpoint
    print("\n4. H2H endpoint...")
    try:
        if hasattr(provider, 'get_h2h'):
            print(f"   ⚠️  METHOD EXISTS but not tested (need team_ids)")
            results['h2h'] = 'NOT_TESTED'
        else:
            print(f"   ❌ FAIL - Method get_h2h NOT FOUND")
            results['h2h'] = 'NOT_IMPLEMENTED'
    except Exception as e:
        print(f"   ❌ FAIL - {str(e)}")
        results['h2h'] = 'FAIL'
    
    # 5. Odds endpoint
    print("\n5. Odds endpoint...")
    try:
        if hasattr(provider, 'get_odds'):
            print(f"   ⚠️  METHOD EXISTS but not tested (need fixture_id)")
            results['odds'] = 'NOT_TESTED'
        else:
            print(f"   ❌ FAIL - Method get_odds NOT FOUND")
            results['odds'] = 'NOT_IMPLEMENTED'
    except Exception as e:
        print(f"   ❌ FAIL - {str(e)}")
        results['odds'] = 'FAIL'
    
    # 6. Check for mock usage in code
    print("\n6. Mock usage detection...")
    mock_files = []
    
    # Check smart_scanner.py
    scanner_file = project_root / "app" / "services" / "scanner" / "smart_scanner.py"
    if scanner_file.exists():
        content = scanner_file.read_text()
        if "goal_history = [" in content and "# Mock" in content:
            mock_files.append("smart_scanner.py")
            print(f"   ❌ MOCK DETECTED in smart_scanner.py")
    
    if mock_files:
        results['mock_usage'] = 'YES'
        print(f"\n   🚨 MOCK DATA DETECTED IN:")
        for f in mock_files:
            print(f"      - {f}")
    else:
        results['mock_usage'] = 'NO'
        print(f"   ✅ NO MOCK DATA DETECTED")
    
    # Summary
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60 + "\n")
    
    for endpoint, status in results.items():
        icon = "✅" if status == "OK" else "❌" if status in ["FAIL", "YES", "NOT_IMPLEMENTED"] else "⚠️"
        print(f"{icon} {endpoint:20s} : {status}")
    
    # Validation
    print("\n" + "="*60)
    print(" VALIDATION")
    print("="*60 + "\n")
    
    is_valid = (
        results.get('fixtures') == 'OK' and
        results.get('mock_usage') == 'NO'
    )
    
    if is_valid:
        print("✅ SYSTEM VALID")
        print("   - Fixtures endpoint OK")
        print("   - No mock data detected")
    else:
        print("❌ SYSTEM INVALID")
        if results.get('fixtures') != 'OK':
            print("   - Fixtures endpoint not working")
        if results.get('mock_usage') == 'YES':
            print("   - MOCK DATA DETECTED - Must be removed!")
    
    print("\n" + "="*60)
    print(" ACTIONS REQUIRED")
    print("="*60 + "\n")
    
    if results.get('mock_usage') == 'YES':
        print("🚨 CRITICAL: Remove all mock data from smart_scanner.py")
        print("   Replace with:")
        print("   - provider.get_team_history(team_id)")
        print("   - provider.get_h2h(team1_id, team2_id)")
        print("   - If data unavailable: return DATA_INSUFFICIENT")
    
    if results.get('team_history') == 'NOT_IMPLEMENTED':
        print("\n⚠️  Implement provider.get_team_history()")
    
    if results.get('h2h') == 'NOT_IMPLEMENTED':
        print("⚠️  Implement provider.get_h2h()")
    
    if results.get('odds') == 'NOT_IMPLEMENTED':
        print("⚠️  Implement provider.get_odds()")
    
    print()
    
    return results


if __name__ == "__main__":
    results = audit_endpoints()
    
    # Exit code
    if results.get('mock_usage') == 'YES':
        sys.exit(1)  # Fail if mock detected
    else:
        sys.exit(0)
