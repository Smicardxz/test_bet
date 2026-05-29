"""
Test API Data Endpoint
Teste rapidement l'endpoint /api/data
"""

import requests
import json

url = "http://localhost:5000/api/data"

print("\n" + "="*60)
print(" TEST /api/data")
print("="*60 + "\n")

try:
    print(f"Calling {url}...")
    response = requests.get(url, timeout=30)
    
    print(f"Status: {response.status_code}")
    print()
    
    data = response.json()
    
    print("Response:")
    print(json.dumps(data, indent=2, default=str)[:2000])  # First 2000 chars
    print()
    
    if data.get("success"):
        print("✅ SUCCESS")
        print(f"   Total matches: {data['stats']['total_matches']}")
        print(f"   Target: {data['stats']['target_count']}")
        print(f"   Analyzed: {data['stats']['analyzed_count']}")
        print()
        print(f"   Upcoming statistical: {len(data['categories']['upcoming_statistical'])}")
        print(f"   Upcoming pending: {len(data['categories']['upcoming_pending'])}")
        print(f"   Live: {len(data['categories']['live'])}")
        print(f"   Finished: {len(data['categories']['finished'])}")
    else:
        print("❌ ERROR")
        print(f"   {data.get('error', 'Unknown error')}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to Flask server")
    print("   Make sure Flask is running: python app_flask.py")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
