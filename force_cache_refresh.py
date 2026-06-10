#!/usr/bin/env python3
"""
force_cache_refresh.py
======================
Force refresh the matches cache with live score data.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner
from app_flask import cache
from datetime import datetime

def force_cache_refresh():
    """Force refresh the matches cache."""
    print(f"\n{'='*80}")
    print(f"🔄 FORCING CACHE REFRESH")
    print(f"{'='*80}")
    
    # Create manager and scanner
    manager = DataSourceManager()
    scanner = SmartScanner(
        provider=manager.provider,
        is_real_data=manager.is_real_data,
        include_extreme_obscure=True,
        odds_provider=manager.odds_provider,
    )
    
    print(f"\n🔍 RUNNING SCAN")
    print(f"{'='*60}")
    
    # Run scan
    scan_result = scanner.scan_today()
    
    analyzed_count = len(scan_result.get('analyzed_matches', []))
    remaining_count = len(scan_result.get('remaining_matches', []))
    total_count = analyzed_count + remaining_count
    
    print(f"  Analyzed matches: {analyzed_count}")
    print(f"  Remaining matches: {remaining_count}")
    print(f"  Total matches: {total_count}")
    
    # Check live matches
    all_matches = scan_result.get('analyzed_matches', []) + scan_result.get('remaining_matches', [])
    live_matches = [m for m in all_matches if m.get('match_data', {}).get('is_live')]
    
    print(f"  Live matches: {len(live_matches)}")
    
    if live_matches:
        # Check first live match for scores
        sample = live_matches[0]
        match_data = sample.get('match_data', {})
        
        print(f"\n🔍 SAMPLE LIVE MATCH")
        print(f"{'='*60}")
        print(f"  Match ID: {match_data.get('match_id')}")
        print(f"  Teams: {match_data.get('home_team')} vs {match_data.get('away_team')}")
        print(f"  Status: {match_data.get('status')}")
        print(f"  home_score: {match_data.get('home_score')}")
        print(f"  away_score: {match_data.get('away_score')}")
        print(f"  minute: {match_data.get('minute')}")
        print(f"  elapsed: {match_data.get('elapsed')}")
        print(f"  ht_home_score: {match_data.get('ht_home_score')}")
        print(f"  ht_away_score: {match_data.get('ht_away_score')}")
        print(f"  status_short: {match_data.get('status_short')}")
        print(f"  status_long: {match_data.get('status_long')}")
    
    # Save to cache
    print(f"\n🔍 SAVING TO CACHE")
    print(f"{'='*60}")
    
    data = {
        "manager": manager,
        "scanner": scanner,
        "scan_result": scan_result,
        "timestamp": datetime.now()
    }
    
    cache["data"] = data
    cache["timestamp"] = datetime.now()
    print(f"  Cache updated successfully")
    
    return True


if __name__ == "__main__":
    success = force_cache_refresh()
    sys.exit(0 if success else 1)
