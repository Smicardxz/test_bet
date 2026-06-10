"""
Test with real API-Football data to verify GLOBAL_SCAN performance
"""
import os
import time
import requests

# Force real data
os.environ['DATA_PROVIDER'] = 'api_football'

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("TESTING WITH REAL API-FOOTBALL DATA")
print("=" * 60)

# Test 1: Health check
print("\n1. Testing /api/health...")
try:
    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Data source: {data.get('data_source')}")
    print(f"Cache age: {data.get('cache_age_seconds')}s")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Trigger data load with real data
print("\n2. Testing /api/matches with real data (this may take time)...")
print("   Timeout set to 120s to allow full scan...")
try:
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/matches", timeout=120)
    elapsed = time.time() - start
    print(f"Status: {response.status_code}")
    print(f"Time taken: {elapsed:.2f}s")

    data = response.json()
    stats = data.get('stats', {})
    print(f"\nStats:")
    print(f"  Total matches: {stats.get('total_matches', 0)}")
    print(f"  Targeted matches: {stats.get('target_count', 0)}")
    print(f"  Analyzed matches: {stats.get('analyzed_count', 0)}")
    print(f"  Scan duration: {stats.get('scan_duration', 0):.2f}s")

    # Check categories
    categories = data.get('categories', {})
    print(f"\nCategories:")
    for cat_name, cat_matches in categories.items():
        print(f"  {cat_name}: {len(cat_matches)} matches")

    # Show sample of leagues
    all_matches = []
    for cat_matches in categories.values():
        all_matches.extend(cat_matches)

    if all_matches:
        print(f"\nSample leagues from first 10 matches:")
        seen_leagues = set()
        for m in all_matches:
            league = m.get('league', 'Unknown')
            country = m.get('country', 'Unknown')
            key = f"{league} ({country})"
            if key not in seen_leagues:
                seen_leagues.add(key)
                print(f"  - {league} ({country})")
            if len(seen_leagues) >= 10:
                break

except requests.exceptions.Timeout:
    print(f"TIMEOUT after 120s - scan taking too long")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
