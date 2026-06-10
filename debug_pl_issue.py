#!/usr/bin/env python3
"""
debug_pl_issue.py
================
Debug specific P/L calculation issues.
"""

import sys
import os
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

def debug_pl_issue():
    """Debug specific P/L calculation issues."""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG P/L ISSUE")
    print(f"{'='*80}")
    
    # Get repository
    try:
        from app.database.supabase_repository import SupabaseRepository, _parse_reset_at, calculate_profit_loss
        repo = SupabaseRepository()
        tracking_reset_at = _parse_reset_at()
    except Exception as e:
        print(f"❌ Failed to initialize repository: {e}")
        return
    
    # Get today's predictions
    try:
        today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
        today_end = datetime.combine(date.today(), datetime.max.time()).isoformat()
        
        q = (
            repo._client.table("predictions")
            .select("*")
            .gte("prediction_date", today_start)
            .lte("prediction_date", today_end)
            .order("prediction_date", desc=True)
        )
        
        if tracking_reset_at:
            from app.database.supabase_repository import _apply_since_filter
            q = _apply_since_filter(q, tracking_reset_at)
        
        predictions = q.execute().data or []
        print(f"📊 Found {len(predictions)} predictions today")
        
    except Exception as e:
        print(f"❌ Error fetching predictions: {e}")
        return
    
    # Analyze P/L issues
    print(f"\n🔍 ANALYZING P/L ISSUES")
    print(f"{'='*80}")
    
    issues = []
    
    for pred in predictions:
        status = pred.get("status", "").upper()
        if status not in ["WON", "LOST", "VOID"]:
            continue
        
        prediction_id = pred.get("prediction_id", "")
        market = pred.get("market", "")
        bookmaker_odd = pred.get("bookmaker_odd", 0.0)
        stored_pl = pred.get("profit_loss", 0.0)
        
        if stored_pl is None:
            stored_pl = 0.0
        else:
            stored_pl = float(stored_pl)
        
        # Calculate expected P/L
        if status == "WON":
            expected_pl = calculate_profit_loss("WIN", bookmaker_odd or 0.0, 1.0)
        elif status == "LOST":
            expected_pl = calculate_profit_loss("LOSS", bookmaker_odd or 0.0, 1.0)
        elif status == "VOID":
            expected_pl = calculate_profit_loss("VOID", bookmaker_odd or 0.0, 1.0)
        else:
            expected_pl = 0.0
        
        difference = abs(stored_pl - expected_pl)
        
        if difference > 0.01:
            issues.append({
                'prediction_id': prediction_id,
                'market': market,
                'status': status,
                'bookmaker_odd': bookmaker_odd,
                'stored_pl': stored_pl,
                'expected_pl': expected_pl,
                'difference': difference
            })
    
    print(f"📊 Found {len(issues)} P/L issues")
    
    # Group by issue type
    issue_types = {
        'zero_odds': [],
        'normal_odds': [],
        'other': []
    }
    
    for issue in issues:
        if issue['bookmaker_odd'] == 0.0:
            issue_types['zero_odds'].append(issue)
        elif issue['bookmaker_odd'] >= 1.1:
            issue_types['normal_odds'].append(issue)
        else:
            issue_types['other'].append(issue)
    
    print(f"\n📊 Issue Breakdown:")
    print(f"  Zero odds (0.00): {len(issue_types['zero_odds'])}")
    print(f"  Normal odds (≥1.1): {len(issue_types['normal_odds'])}")
    print(f"  Other odds: {len(issue_types['other'])}")
    
    # Analyze zero odds issues
    if issue_types['zero_odds']:
        print(f"\n🔍 ZERO ODDS ISSUES:")
        print(f"{'='*80}")
        
        header = f"{'Prediction ID':<25} {'Market':<15} {'Status':<7} {'Stored PL':<11} {'Expected PL':<11} {'Issue':<15}"
        print(f"{header}")
        print(f"{'-'*100}")
        
        for issue in issue_types['zero_odds'][:10]:  # Show first 10
            prediction_id = issue['prediction_id']
            market = issue['market']
            status = issue['status']
            stored_pl = issue['stored_pl']
            expected_pl = issue['expected_pl']
            
            # Determine issue type
            if status == "WON" and stored_pl == 0.01:
                issue_type = "WON_BUT_ZERO_ODDS"
            elif status == "LOST" and stored_pl == -1.00:
                issue_type = "LOST_BUT_ZERO_ODDS"
            else:
                issue_type = "UNKNOWN"
            
            print(f"{prediction_id:<25} {market:<15} {status:<7} {stored_pl:<11.2f} {expected_pl:<11.2f} {issue_type:<15}")
    
    # Analyze normal odds issues
    if issue_types['normal_odds']:
        print(f"\n🔍 NORMAL ODDS ISSUES:")
        print(f"{'='*80}")
        
        header = f"{'Prediction ID':<25} {'Market':<15} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'Expected PL':<11} {'Issue':<15}"
        print(f"{header}")
        print(f"{'-'*110}")
        
        for issue in issue_types['normal_odds'][:10]:  # Show first 10
            prediction_id = issue['prediction_id']
            market = issue['market']
            status = issue['status']
            bookmaker_odd = issue['bookmaker_odd']
            stored_pl = issue['stored_pl']
            expected_pl = issue['expected_pl']
            
            # Determine issue type
            if abs(stored_pl - (expected_pl * 100)) < 0.01:
                issue_type = "PERCENTAGE_ERROR"
            elif abs(stored_pl - (expected_pl * 2)) < 0.01:
                issue_type = "DOUBLE_ERROR"
            else:
                issue_type = "UNKNOWN"
            
            print(f"{prediction_id:<25} {market:<15} {status:<7} {bookmaker_odd:<6.2f} {stored_pl:<11.2f} {expected_pl:<11.2f} {issue_type:<15}")
    
    # Test the calculate_profit_loss function directly
    print(f"\n🔍 TESTING CALCULATE_PROFIT_LOSS FUNCTION:")
    print(f"{'='*80}")
    
    test_cases = [
        ("WIN", 2.50, 1.0),
        ("WIN", 1.95, 1.0),
        ("WIN", 0.00, 1.0),
        ("LOSS", 2.50, 1.0),
        ("LOSS", 0.00, 1.0),
        ("VOID", 2.50, 1.0),
        ("VOID", 0.00, 1.0),
    ]
    
    header = f"{'Result':<7} {'Odd':<6} {'Stake':<6} {'Calculated PL':<15} {'Expected PL':<12}"
    print(f"{header}")
    print(f"{'-'*60}")
    
    for result, odd, stake in test_cases:
        calculated_pl = calculate_profit_loss(result, odd, stake)
        
        if result == "WIN":
            if odd >= 1.01:
                expected_pl = round((odd - 1.0) * stake, 4)
            else:
                expected_pl = round((1.01 - 1.0) * stake, 4)  # Uses min odd 1.01
        elif result == "LOSS":
            expected_pl = -stake
        else:  # VOID
            expected_pl = 0.0
        
        print(f"{result:<7} {odd:<6.2f} {stake:<6.1f} {calculated_pl:<15.4f} {expected_pl:<12.4f}")
    
    # Conclusion
    print(f"\n🎯 CONCLUSION:")
    print(f"{'='*80}")
    
    if len(issue_types['zero_odds']) > len(issue_types['normal_odds']):
        print(f"🔍 PRIMARY ISSUE: Zero odds (0.00) predictions")
        print(f"   - {len(issue_types['zero_odds'])} predictions have 0.00 odds")
        print(f"   - These should probably be filtered out or handled differently")
        print(f"   - The calculate_profit_loss function handles 0.00 odds correctly")
        print(f"   - Issue may be in data collection or prediction creation")
    
    elif len(issue_types['normal_odds']) > 0:
        print(f"🔍 PRIMARY ISSUE: Normal odds calculation errors")
        print(f"   - {len(issue_types['normal_odds'])} predictions with odds ≥ 1.1 have wrong P/L")
        print(f"   - This indicates a calculation bug in the settlement logic")
    
    else:
        print(f"🔍 PRIMARY ISSUE: Other odds calculation errors")
        print(f"   - {len(issue_types['other'])} predictions with odds < 1.1 have wrong P/L")
    
    print(f"\n📋 ROOT CAUSE ANALYSIS:")
    print(f"   - calculate_profit_loss() function appears correct")
    print(f"   - Zero odds predictions are being settled with P/L values")
    print(f"   - This suggests the issue is in the settlement process, not the P/L calculation")
    print(f"   - Zero odds should probably not be settled or should have P/L = 0")

if __name__ == "__main__":
    debug_pl_issue()
