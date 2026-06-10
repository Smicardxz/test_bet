#!/usr/bin/env python3
"""
debug_cache_format.py
=====================
Debug the cache format used by _get_all_matches_from_cache.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app_flask import _get_all_matches_from_cache

def debug_cache_format():
    """Debug the cache format."""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING CACHE FORMAT")
    print(f"{'='*80}")
    
    # Get matches from cache
    matches = _get_all_matches_from_cache()
    
    print(f"\n🔍 CACHE ANALYSIS")
    print(f"{'='*60}")
    print(f"  Total matches: {len(matches) if matches else 0}")
    
    if not matches:
        print(f"  ❌ No matches in cache")
        return False
    
    # Find live matches
    live_matches = [m for m in matches if m.get("match_data", {}).get("is_live")]
    print(f"  Live matches: {len(live_matches)}")
    
    if not live_matches:
        print(f"  ❌ No live matches found")
        return False
    
    # Analyze first live match structure
    print(f"\n🔍 FIRST LIVE MATCH STRUCTURE")
    print(f"{'='*60}")
    
    sample = live_matches[0]
    print(f"  Match keys: {list(sample.keys())}")
    
    match_data = sample.get("match_data", {})
    print(f"  Match data keys: {list(match_data.keys())}")
    print(f"  Has home_score: {'home_score' in match_data}")
    print(f"  Has minute: {'minute' in match_data}")
    
    # Check if the fields exist
    score_fields = ['home_score', 'away_score', 'minute', 'elapsed', 'ht_home_score', 'ht_away_score', 'status_short', 'status_long']
    
    print(f"\n🔍 SCORE FIELDS PRESENCE")
    print(f"{'='*60}")
    
    for field in score_fields:
        value = match_data.get(field)
        has_field = field in match_data
        print(f"  {field}: {'✅' if has_field else '❌'} = {value}")
    
    # Test _normalize_match directly
    print(f"\n🔍 TESTING _normalize_match")
    print(f"{'='*60}")
    
    try:
        from app_flask import _normalize_match
        
        # Create proper match item structure
        match_item = {
            "match_data": match_data,
            "profile": sample.get("profile", {}),
            "analysis": sample.get("analysis", {})
        }
        
        normalized = _normalize_match(match_item)
        
        print(f"  Normalized keys: {list(normalized.keys())}")
        print(f"  Normalized home_score: {normalized.get('home_score')}")
        print(f"  Normalized away_score: {normalized.get('away_score')}")
        print(f"  Normalized minute: {normalized.get('minute')}")
        print(f"  Normalized elapsed: {normalized.get('elapsed')}")
        print(f"  Normalized ht_home_score: {normalized.get('ht_home_score')}")
        print(f"  Normalized ht_away_score: {normalized.get('ht_away_score')}")
        print(f"  Normalized status_short: {normalized.get('status_short')}")
        print(f"  Normalized status_long: {normalized.get('status_long')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in _normalize_match: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_cache_format()
    sys.exit(0 if success else 1)
