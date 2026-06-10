#!/usr/bin/env python3
"""
check_direct_cache.py
=====================
Check the direct cache content.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app_flask import cache

def check_direct_cache():
    """Check the direct cache content."""
    print(f"\n{'='*80}")
    print(f"🔍 CHECKING DIRECT CACHE")
    print(f"{'='*80}")
    
    print(f"\n🔍 CACHE KEYS")
    print(f"{'='*60}")
    print(f"  Cache keys: {list(cache.keys())}")
    
    has_data = cache.get("data") is not None
    has_timestamp = cache.get("timestamp") is not None
    
    print(f"  Has data: {has_data}")
    print(f"  Has timestamp: {has_timestamp}")
    
    if has_data:
        data = cache["data"]
        print(f"  Data keys: {list(data.keys())}")
        
        scan_result = data.get("scan_result", {})
        print(f"  Scan result keys: {list(scan_result.keys())}")
        
        analyzed = scan_result.get("analyzed_matches", [])
        remaining = scan_result.get("remaining_matches", [])
        
        print(f"  Analyzed matches: {len(analyzed)}")
        print(f"  Remaining matches: {len(remaining)}")
        
        all_matches = analyzed + remaining
        print(f"  Total matches: {len(all_matches)}")
        
        if all_matches:
            live_matches = [m for m in all_matches if m.get("match_data", {}).get("is_live")]
            print(f"  Live matches: {len(live_matches)}")
            
            if live_matches:
                sample = live_matches[0]
                match_data = sample.get("match_data", {})
                print(f"  Sample live match:")
                print(f"    Match ID: {match_data.get('match_id')}")
                print(f"    Teams: {match_data.get('home_team')} vs {match_data.get('away_team')}")
                print(f"    home_score: {match_data.get('home_score')}")
                print(f"    away_score: {match_data.get('away_score')}")
                print(f"    minute: {match_data.get('minute')}")
                print(f"    elapsed: {match_data.get('elapsed')}")
                print(f"    ht_home_score: {match_data.get('ht_home_score')}")
                print(f"    ht_away_score: {match_data.get('ht_away_score')}")
                print(f"    status_short: {match_data.get('status_short')}")
                print(f"    status_long: {match_data.get('status_long')}")
    
    return True


if __name__ == "__main__":
    success = check_direct_cache()
    sys.exit(0 if success else 1)
