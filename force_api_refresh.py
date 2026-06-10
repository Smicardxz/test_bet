#!/usr/bin/env python3
"""
force_api_refresh.py
====================
Force refresh the API matches data.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app_flask import cache

def force_api_refresh():
    """Force refresh the API matches data."""
    print(f"\n{'='*80}")
    print(f"🔄 FORCING API REFRESH")
    print(f"{'='*80}")
    
    # Use the cache we already populated
    print(f"\n🔍 USING EXISTING CACHE")
    print(f"{'='*60}")
    
    if not cache.get("data"):
        print("  Cache is empty, running force_cache_refresh first...")
        from force_cache_refresh import force_cache_refresh
        force_cache_refresh()
    
    # Check final state
    print(f"\n🔍 FINAL STATE")
    print(f"{'='*60}")
    
    if cache.get("data") and cache.get("timestamp"):
        print(f"  ✅ Cache populated")
        
        # Import and test
        from app_flask import _get_all_matches_from_cache
        
        matches = _get_all_matches_from_cache()
        print(f"  Total matches: {len(matches) if matches else 0}")
        
        if matches:
            live_matches = [m for m in matches if m.get("match_data", {}).get("is_live")]
            print(f"  Live matches: {len(live_matches)}")
            
            if live_matches:
                sample = live_matches[0]
                match_data = sample.get("match_data", {})
                print(f"  Sample live match scores:")
                print(f"    home_score: {match_data.get('home_score')}")
                print(f"    away_score: {match_data.get('away_score')}")
                print(f"    minute: {match_data.get('minute')}")
                print(f"    elapsed: {match_data.get('elapsed')}")
                print(f"    ht_home_score: {match_data.get('ht_home_score')}")
                print(f"    ht_away_score: {match_data.get('ht_away_score')}")
                print(f"    status_short: {match_data.get('status_short')}")
                print(f"    status_long: {match_data.get('status_long')}")
    else:
        print(f"  ❌ Cache still empty")
    
    return True


if __name__ == "__main__":
    success = force_api_refresh()
    sys.exit(0 if success else 1)
