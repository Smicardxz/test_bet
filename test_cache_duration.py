"""
test_cache_duration.py
=======================
Test that cache duration is now 30 minutes.
"""

import requests
import time

def main():
    print(f"\n{'='*66}")
    print(f"  TESTING CACHE DURATION (30 MINUTES)")
    print(f"{'='*66}")
    
    # First call - trigger scan by calling matches endpoint
    print(f"\n1. Triggering scan via /api/matches...")
    try:
        response = requests.get("http://localhost:5000/api/matches?limit=1", timeout=60)
        if response.status_code == 200:
            print(f"   ✓ Scan triggered")
        else:
            print(f"   ERROR: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Wait for scan to complete
    print(f"\n2. Waiting 10 seconds for scan to complete...")
    time.sleep(10)
    
    # Check health endpoint
    print(f"\n3. Checking cache status via /api/health...")
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache_age = data.get("cache_age_seconds")
            cache_active = data.get("cache_active")
            print(f"   Cache age: {cache_age}s")
            print(f"   Cache active: {cache_active}")
            
            if cache_active:
                print(f"\n   ✓ Cache is active (cache_age < 1800s)")
            else:
                print(f"\n   ✗ Cache is not active (cache_age >= 1800s)")
        else:
            print(f"   ERROR: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print(f"\n{'='*66}\n")


if __name__ == "__main__":
    main()
