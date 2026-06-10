#!/usr/bin/env python3
"""
final_audit_test.py
===================
Final audit test using fresh scan data.
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

def final_audit_test():
    """Final audit test using fresh scan data."""
    print(f"\n{'='*80}")
    print(f"🔍 FINAL AUDIT TEST")
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
    
    # Normalize all live matches
    print(f"\n🔍 NORMALIZING LIVE MATCHES")
    print(f"{'='*60}")
    
    normalized_live = []
    for match in live_matches:
        try:
            normalized = _normalize_match(match)
            normalized_live.append(normalized)
        except Exception as e:
            print(f"  ❌ Error normalizing match: {e}")
            continue
    
    print(f"  Successfully normalized: {len(normalized_live)}/{len(live_matches)}")
    
    # Check required fields
    print(f"\n🔍 CHECKING REQUIRED FIELDS")
    print(f"{'='*60}")
    
    required_fields = [
        'home_score', 'away_score', 'minute', 'elapsed',
        'ht_home_score', 'ht_away_score', 'status_short', 'status_long'
    ]
    
    field_stats = {}
    for field in required_fields:
        count = sum(1 for m in normalized_live if m.get(field) is not None)
        percentage = (count / len(normalized_live) * 100) if normalized_live else 0
        field_stats[field] = {
            'count': count,
            'percentage': percentage
        }
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {field}: {count}/{len(normalized_live)} ({percentage:.1f}%)")
    
    # Show examples
    print(f"\n🔍 FIRST 5 LIVE MATCHES")
    print(f"{'='*120}")
    
    header = f"{'Fixture ID':<12} {'Match':<30} {'Status':<8} {'Home':<4} {'Away':<4} {'Min':<4} {'HT_H':<4} {'HT_A':<4}"
    print(f"{header}")
    print(f"{'-'*120}")
    
    for match in normalized_live[:5]:
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
    
    # Final verdict
    print(f"\n🔍 FINAL VERDICT")
    print(f"{'='*60}")
    
    issues = []
    
    if len(normalized_live) == 0:
        issues.append("No live matches found")
    
    for field, stats in field_stats.items():
        if stats['count'] == 0:
            issues.append(f"Field '{field}' completely missing")
    
    if not issues:
        print(f"\n✅ LIVE_SCORE_FIELDS_OK")
        print(f"  All required fields are present in live matches")
        print(f"  Total live matches with scores: {len(normalized_live)}")
        return True
    else:
        print(f"\n❌ LIVE_SCORE_FIELDS_MISSING")
        for issue in issues:
            print(f"  ❌ {issue}")
        return False


if __name__ == "__main__":
    success = final_audit_test()
    sys.exit(0 if success else 1)
