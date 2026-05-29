"""
Test Analyze Endpoint
Test direct de l'endpoint HTTP /api/analyze_match
"""

import requests
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_analyze_endpoint():
    """Test l'endpoint /api/analyze_match directement"""
    
    print("\n" + "="*60)
    print(" TEST ANALYZE ENDPOINT")
    print("="*60 + "\n")
    
    # URL de l'endpoint
    url = "http://localhost:5000/api/analyze_match"
    
    # Données de test (match réel)
    test_data = {
        "fixture_id": "1524613",
        "home_team_id": "23116",
        "away_team_id": "23111",
        "home_team_name": "Dothan United",
        "away_team_name": "Birmingham Legion II",
        "league_name": "USL League Two",
        "country": "USA"
    }
    
    print("📋 Test Data:")
    print(json.dumps(test_data, indent=2))
    print()
    
    print("🔌 Calling endpoint...")
    print(f"   URL: {url}")
    print(f"   Method: POST")
    print()
    
    try:
        # Appel HTTP
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📊 HTTP Response:")
        print(f"   Status Code: {response.status_code}")
        print()
        
        # Parse JSON
        data = response.json()
        
        print("📦 Response Data:")
        print(json.dumps(data, indent=2))
        print()
        
        # Validation
        print("="*60)
        print(" VALIDATION")
        print("="*60 + "\n")
        
        checks = {
            "HTTP 200": response.status_code == 200,
            "success field": "success" in data,
            "analysis_status field": "analysis_status" in data,
        }
        
        if data.get("success"):
            checks["data_origin field"] = "data_origin" in data
            checks["data_origin = REAL"] = data.get("data_origin") == "REAL"
            checks["mock_usage field"] = "mock_usage" in data
            checks["mock_usage = False"] = data.get("mock_usage") == False
            
            if data.get("analysis_status") == "ANALYZED":
                checks["ht_analysis present"] = "ht_analysis" in data
                checks["ft_analysis present"] = "ft_analysis" in data
                checks["signals present"] = "signals" in data
            elif data.get("analysis_status") == "DATA_INSUFFICIENT":
                checks["reason present"] = "reason" in data
                checks["home_history_count present"] = "home_history_count" in data
                checks["away_history_count present"] = "away_history_count" in data
        
        all_passed = all(checks.values())
        
        for check, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"{icon} {check}")
        
        print()
        print("="*60)
        if all_passed:
            print(" ✅ ANALYZE ENDPOINT OK")
        else:
            print(" ❌ ANALYZE ENDPOINT FAILED")
        print("="*60 + "\n")
        
        # Summary
        if data.get("success"):
            print("📊 Analysis Summary:")
            print(f"   Status: {data.get('analysis_status')}")
            print(f"   Data Origin: {data.get('data_origin', 'N/A')}")
            print(f"   Mock Usage: {data.get('mock_usage', 'N/A')}")
            print(f"   Home History: {data.get('home_history_count', 0)}")
            print(f"   Away History: {data.get('away_history_count', 0)}")
            print(f"   H2H: {data.get('h2h_count', 0)}")
            
            if data.get("analysis_status") == "ANALYZED":
                ht_rows = len(data.get("ht_analysis", {}).get("table", []))
                ft_rows = len(data.get("ft_analysis", {}).get("table", []))
                signals = len(data.get("signals", []))
                print(f"   HT Analysis: {ht_rows} lines")
                print(f"   FT Analysis: {ft_rows} lines")
                print(f"   Signals: {signals}")
            elif data.get("analysis_status") == "DATA_INSUFFICIENT":
                print(f"   Reason: {data.get('reason', 'N/A')}")
        
        return all_passed
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server")
        print("   Make sure Flask is running: python app_flask.py")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timeout")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_analyze_endpoint()
    sys.exit(0 if success else 1)
