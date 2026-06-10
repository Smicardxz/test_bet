#!/usr/bin/env python3
"""
audit_live_score_fields.py
===========================
Audit live score fields in /api/matches endpoint.
"""

import sys
import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def audit_live_score_fields():
    """Audit live score fields in /api/matches endpoint."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 LIVE SCORE FIELDS AUDIT")
    print(f"{'='*80}{RESET}")
    
    print(f"\n{CYAN}Configuration:{RESET}")
    print(f"  Testing /api/matches endpoint")
    print(f"  Checking live match score fields")
    
    # Test API health first
    print(f"\n{BOLD}🔍 API HEALTH CHECK{RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=10)
        if response.status_code == 200:
            print(f"  {GREEN}✅ API health OK{RESET}")
        else:
            print(f"  {RED}❌ API health failed: {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"  {RED}❌ API health check failed: {e}{RESET}")
        return False
    
    # Get matches data
    print(f"\n{BOLD}🔍 FETCHING MATCHES DATA{RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=100", timeout=15)
        if response.status_code != 200:
            print(f"  {RED}❌ Failed to fetch matches: {response.status_code}{RESET}")
            return False
        
        data = response.json()
        matches = data.get('matches', [])
        
        print(f"  Total matches: {data.get('total', 0)}")
        print(f"  Returned matches: {len(matches)}")
        
    except Exception as e:
        print(f"  {RED}❌ Failed to fetch matches: {e}{RESET}")
        return False
    
    # Analyze matches
    print(f"\n{BOLD}🔍 ANALYZING LIVE MATCHES{RESET}")
    print(f"{'='*60}")
    
    live_matches = [m for m in matches if m.get('status') == 'LIVE']
    total_matches = len(matches)
    
    print(f"  Total matches: {total_matches}")
    print(f"  Live matches: {len(live_matches)}")
    
    if not live_matches:
        print(f"  {YELLOW}⚠️  No live matches found{RESET}")
        print(f"  Cannot audit live score fields without live matches")
        return False
    
    # Check score fields
    print(f"\n{BOLD}🔍 CHECKING SCORE FIELDS{RESET}")
    print(f"{'='*60}")
    
    required_fields = [
        'home_score', 'away_score', 'minute', 'elapsed',
        'ht_home_score', 'ht_away_score', 'status_short', 'status_long'
    ]
    
    live_matches_with_scores = []
    live_matches_with_minute = []
    
    for match in live_matches:
        has_scores = any(match.get(field) is not None for field in ['home_score', 'away_score'])
        has_minute = any(match.get(field) is not None for field in ['minute', 'elapsed'])
        
        if has_scores:
            live_matches_with_scores.append(match)
        if has_minute:
            live_matches_with_minute.append(match)
    
    print(f"  Live matches with home_score/away_score: {len(live_matches_with_scores)}")
    print(f"  Live matches with minute/elapsed: {len(live_matches_with_minute)}")
    
    # Show field presence
    print(f"\n{CYAN}Field Presence in Live Matches:{RESET}")
    for field in required_fields:
        count = sum(1 for m in live_matches if m.get(field) is not None)
        percentage = (count / len(live_matches) * 100) if live_matches else 0
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {field}: {count}/{len(live_matches)} ({percentage:.1f}%)")
    
    # Show examples
    print(f"\n{BOLD}🔍 FIRST 10 LIVE MATCHES EXAMPLES{RESET}")
    print(f"{'='*120}")
    
    header = f"{'Fixture ID':<12} {'Match':<30} {'Status':<8} {'Home':<4} {'Away':<4} {'Min':<4} {'HT_H':<4} {'HT_A':<4}"
    print(f"{header}")
    print(f"{'-'*120}")
    
    for i, match in enumerate(live_matches[:10]):
        fixture_id = str(match.get('fixture_id', 'N/A'))[:10]
        home_team = str(match.get('home_team', 'N/A'))[:14]
        away_team = str(match.get('away_team', 'N/A'))[:14]
        match_name = f"{home_team} vs {away_team}"
        status = str(match.get('status', 'N/A'))[:6]
        home_score = str(match.get('home_score', '—'))[:3]
        away_score = str(match.get('away_score', '—'))[:3]
        minute = str(match.get('minute') or match.get('elapsed') or '—')[:3]
        ht_home = str(match.get('ht_home_score', '—'))[:3]
        ht_away = str(match.get('ht_away_score', '—'))[:3]
        
        print(f"{fixture_id:<12} {match_name:<30} {status:<8} {home_score:<4} {away_score:<4} {minute:<4} {ht_home:<4} {ht_away:<4}")
    
    # Check if provider data is available in raw format
    print(f"\n{BOLD}🔍 CHECKING RAW PROVIDER DATA{RESET}")
    print(f"{'='*60}")
    
    # Try to access raw match data to see if scores are available there
    try:
        # Import scanner to check raw data
        from app.providers.data_source_manager import DataSourceManager
        from app.services.scanner.smart_scanner import SmartScanner
        from app.providers.odds.odds_provider_manager import OddsProviderManager
        
        manager = DataSourceManager()
        odds_mgr = OddsProviderManager(
            apifootball_key=os.getenv("API_FOOTBALL_KEY", ""),
            oddsapi_key=os.getenv("ODDS_API_KEY", ""),
        )
        
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            odds_provider=odds_mgr
        )
        
        # Get raw matches
        scan_result = scanner.scan_today()
        analyzed_matches = scan_result.get('analyzed_matches', [])
        
        live_raw_matches = []
        for match_data in analyzed_matches:
            analysis = match_data.get('analysis', {})
            match_info = match_data.get('match_data', {})
            
            # Check if it's live
            if match_info.get('is_live'):
                live_raw_matches.append(match_data)
        
        print(f"  Raw live matches found: {len(live_raw_matches)}")
        
        if live_raw_matches:
            sample = live_raw_matches[0]
            match_info = sample.get('match_data', {})
            
            print(f"\n{CYAN}Sample Raw Match Data:{RESET}")
            print(f"  is_live: {match_info.get('is_live')}")
            print(f"  is_finished: {match_info.get('is_finished')}")
            print(f"  score_fulltime: {match_info.get('score_fulltime')}")
            print(f"  score_halftime: {match_info.get('score_halftime')}")
            print(f"  status: {match_info.get('status')}")
            
            # Check MatchDetails object structure
            if hasattr(match_info, '__dict__'):
                print(f"\n{CYAN}MatchDetails Object Fields:{RESET}")
                for attr in ['score_fulltime', 'score_halftime', 'status', 'match_date']:
                    value = getattr(match_info, attr, None)
                    if value is not None:
                        print(f"  {attr}: {value}")
                        if hasattr(value, '__dict__'):
                            print(f"    -> {value.__dict__}")
        
    except Exception as e:
        print(f"  {YELLOW}⚠️  Could not check raw data: {e}{RESET}")
    
    # Final verdict
    print(f"\n{BOLD}🔍 FINAL VERDICT{RESET}")
    print(f"{'='*60}")
    
    issues = []
    
    if len(live_matches_with_scores) == 0:
        issues.append("No live matches with score fields")
    
    if len(live_matches_with_minute) == 0:
        issues.append("No live matches with minute/elapsed fields")
    
    # Check if any required field is completely missing
    for field in required_fields:
        count = sum(1 for m in live_matches if m.get(field) is not None)
        if count == 0:
            issues.append(f"Field '{field}' completely missing")
    
    if not issues:
        print(f"\n{GREEN}✅ LIVE_SCORE_FIELDS_OK{RESET}")
        print(f"  All required fields are present in live matches")
        return True
    else:
        print(f"\n{RED}❌ LIVE_SCORE_FIELDS_MISSING{RESET}")
        for issue in issues:
            print(f"  ❌ {issue}")
        
        # Check if raw data has the fields
        if live_raw_matches:
            sample = live_raw_matches[0]
            match_info = sample.get('match_data', {})
            has_raw_scores = (
                match_info.get('score_fulltime') or 
                match_info.get('score_halftime') or
                hasattr(match_info, 'score_fulltime') or
                hasattr(match_info, 'score_halftime')
            )
            
            if has_raw_scores:
                print(f"\n{YELLOW}⚠️  LIVE_SCORE_FIELDS_PRESENT_BUT_EMPTY{RESET}")
                print(f"  Raw provider data contains score fields but they are not exposed in API")
            else:
                print(f"\n{YELLOW}⚠️  LIVE_SCORE_FIELDS_NOT_AVAILABLE_IN_PROVIDER{RESET}")
                print(f"  Provider data does not contain live score fields")
        
        return False


if __name__ == "__main__":
    success = audit_live_score_fields()
    sys.exit(0 if success else 1)
