#!/usr/bin/env python3
"""
check_cache.py
=============
Check what's in the matches cache.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app_flask import _get_all_matches_from_cache

def check_cache():
    """Check what's in the matches cache."""
    matches = _get_all_matches_from_cache()
    print(f'Matches in cache: {len(matches) if matches else 0}')
    
    if matches:
        sample = matches[0]
        print(f'Sample match keys: {list(sample.keys())}')
        print(f'Has home_score: {"home_score" in sample}')
        print(f'Has minute: {"minute" in sample}')
        
        # Check for live matches
        live_matches = [m for m in matches if m.get("status") == "LIVE"]
        print(f'Live matches in cache: {len(live_matches)}')
        
        if live_matches:
            live_sample = live_matches[0]
            print(f'Live sample home_score: {live_sample.get("home_score")}')
            print(f'Live sample minute: {live_sample.get("minute")}')
    else:
        print('No matches in cache')

if __name__ == "__main__":
    check_cache()
