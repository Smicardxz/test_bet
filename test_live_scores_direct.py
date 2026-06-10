#!/usr/bin/env python3
"""
test_live_scores_direct.py
===========================
Test live scores directly by creating a test endpoint.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner
from app_flask import _normalize_match

def test_live_scores_direct():
    """Test live scores directly."""
    print(f"\n{'='*80}")
    print(f"🔍 TESTING LIVE SCORES DIRECT")
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
    
    analyzed_matches = scan_result.get('analyzed_matches', [])
    remaining_matches = scan_result.get('remaining_matches', [])
    all_matches = analyzed_matches + remaining_matches
    
    print(f"  Analyzed matches: {len(analyzed_matches)}")
    print(f"  Remaining matches: {len(remaining_matches)}")
    print(f"  Total matches: {len(all_matches)}")
    
    # Find live matches
    live_matches = [m for m in all_matches if m.get('match_data', {}).get('is_live')]
    print(f"  Live matches: {len(live_matches)}")
    
    if not live_matches:
        print(f"  ❌ No live matches found")
        return False
    
    # Test first live match
    print(f"\n🔍 TESTING FIRST LIVE MATCH")
    print(f"{'='*60}")
    
    sample = live_matches[0]
    match_data = sample.get('match_data', {})
    
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
    
    # Test _normalize_match
    print(f"\n🔍 TESTING _normalize_match")
    print(f"{'='*60}")
    
    try:
        normalized = _normalize_match(sample)
        
        print(f"  Normalized home_score: {normalized.get('home_score')}")
        print(f"  Normalized away_score: {normalized.get('away_score')}")
        print(f"  Normalized minute: {normalized.get('minute')}")
        print(f"  Normalized elapsed: {normalized.get('elapsed')}")
        print(f"  Normalized ht_home_score: {normalized.get('ht_home_score')}")
        print(f"  Normalized ht_away_score: {normalized.get('ht_away_score')}")
        print(f"  Normalized status_short: {normalized.get('status_short')}")
        print(f"  Normalized status_long: {normalized.get('status_long')}")
        print(f"  Normalized status: {normalized.get('status')}")
        
        # Check if all required fields are present
        required_fields = ['home_score', 'away_score', 'minute', 'elapsed', 'ht_home_score', 'ht_away_score', 'status_short', 'status_long']
        missing_fields = []
        
        for field in required_fields:
            if normalized.get(field) is None:
                missing_fields.append(field)
        
        if not missing_fields:
            print(f"\n  ✅ ALL REQUIRED FIELDS PRESENT!")
            return True
        else:
            print(f"\n  ❌ Missing fields: {missing_fields}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error in _normalize_match: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_live_scores_direct()
    sys.exit(0 if success else 1)
