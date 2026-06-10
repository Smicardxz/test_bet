#!/usr/bin/env python3
"""
final_pl_forensic_audit.py
=========================
Final P/L Forensic Audit - Direct Database Analysis
"""

import sys
import os
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

def final_pl_forensic_audit():
    """Final P/L forensic audit with direct database analysis."""
    print(f"\n{'='*80}")
    print(f"🔍 FINAL P/L FORENSIC AUDIT")
    print(f"{'='*80}")
    
    # Get repository
    try:
        from app.database.supabase_repository import SupabaseRepository, _parse_reset_at, calculate_profit_loss
        repo = SupabaseRepository()
        tracking_reset_at = _parse_reset_at()
    except Exception as e:
        print(f"❌ Failed to initialize repository: {e}")
        return
    
    # Get today's predictions with direct query
    try:
        today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
        today_end = datetime.combine(date.today(), datetime.max.time()).isoformat()
        
        # Direct query to get all predictions
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
    
    # Analyze ALL settled predictions
    print(f"\n🔍 ANALYZING ALL SETTLED PREDICTIONS")
    print(f"{'='*80}")
    
    settled_predictions = []
    for pred in predictions:
        status = pred.get("status", "").upper()
        if status in ["WON", "LOST", "VOID"]:
            settled_predictions.append(pred)
    
    print(f"📊 Found {len(settled_predictions)} settled predictions")
    
    # Manual P/L calculation for each settled prediction
    mismatches = []
    
    header = f"{'Prediction ID':<25} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'Calc PL':<11} {'Diff':<8} {'Issue':<15}"
    print(f"\n{header}")
    print(f"{'-'*100}")
    
    for pred in settled_predictions:
        prediction_id = pred.get("prediction_id", "")
        status = pred.get("status", "").upper()
        bookmaker_odd = pred.get("bookmaker_odd")
        stored_pl = pred.get("profit_loss")
        
        # Handle None values
        if bookmaker_odd is None:
            bookmaker_odd = 0.0
        else:
            bookmaker_odd = float(bookmaker_odd)
        
        if stored_pl is None:
            stored_pl = 0.0
        else:
            stored_pl = float(stored_pl)
        
        # Manual calculation (exact same as calculate_profit_loss)
        if status == "WON":
            if bookmaker_odd >= 1.01:
                calculated_pl = round((bookmaker_odd - 1.0) * 1.0, 4)
            else:
                calculated_pl = round((1.01 - 1.0) * 1.0, 4)  # Uses min odd 1.01
        elif status == "LOST":
            calculated_pl = -1.0
        else:  # VOID
            calculated_pl = 0.0
        
        difference = abs(stored_pl - calculated_pl)
        
        # Determine issue type
        issue_type = "OK"
        if difference > 0.01:
            if bookmaker_odd == 0.0:
                if status == "WON" and stored_pl == 0.01:
                    issue_type = "ZERO_ODD_WON"
                elif status == "LOST" and stored_pl == -1.00:
                    issue_type = "ZERO_ODD_LOST"
                else:
                    issue_type = "ZERO_ODD_OTHER"
            elif abs(stored_pl - (calculated_pl * 100)) < 0.01:
                issue_type = "PERCENTAGE_ERROR"
            elif abs(stored_pl - (calculated_pl * 2)) < 0.01:
                issue_type = "DOUBLE_ERROR"
            else:
                issue_type = "UNKNOWN"
            
            mismatches.append({
                'prediction_id': prediction_id,
                'status': status,
                'bookmaker_odd': bookmaker_odd,
                'stored_pl': stored_pl,
                'calculated_pl': calculated_pl,
                'difference': difference,
                'issue_type': issue_type
            })
        
        # Show all predictions with issues
        if issue_type != "OK":
            print(f"{prediction_id:<25} {status:<7} {bookmaker_odd:<6.2f} {stored_pl:<11.2f} {calculated_pl:<11.2f} {difference:<8.3f} {issue_type:<15}")
    
    print(f"\n📊 Found {len(mismatches)} P/L mismatches")
    
    # Group by issue type
    issue_counts = {}
    for mismatch in mismatches:
        issue_type = mismatch['issue_type']
        if issue_type not in issue_counts:
            issue_counts[issue_type] = 0
        issue_counts[issue_type] += 1
    
    print(f"\n📊 Issue Type Breakdown:")
    for issue_type, count in issue_counts.items():
        print(f"  {issue_type}: {count}")
    
    # Specific analysis of zero odds
    zero_odds_issues = [m for m in mismatches if m['bookmaker_odd'] == 0.0]
    if zero_odds_issues:
        print(f"\n🔍 ZERO ODDS ANALYSIS:")
        print(f"{'='*80}")
        
        print(f"📊 Found {len(zero_odds_issues)} zero odds issues")
        
        # Show patterns
        won_zero = [m for m in zero_odds_issues if m['status'] == 'WON']
        lost_zero = [m for m in zero_odds_issues if m['status'] == 'LOST']
        
        print(f"  WON with 0.00 odds: {len(won_zero)}")
        print(f"  LOST with 0.00 odds: {len(lost_zero)}")
        
        if won_zero:
            print(f"    WON pattern: stored_pl = 0.01 (should be 0.01 but with 0.00 odds)")
        if lost_zero:
            print(f"    LOST pattern: stored_pl = -1.00 (should be -1.00 but with 0.00 odds)")
    
    # Check if the issue is in the calculate_profit_loss function
    print(f"\n🔍 CALCULATE_PROFIT_LOSS FUNCTION TEST:")
    print(f"{'='*80}")
    
    test_cases = [
        ("WIN", 0.00, 1.0),
        ("LOSS", 0.00, 1.0),
        ("VOID", 0.00, 1.0),
    ]
    
    print(f"{'Result':<7} {'Odd':<6} {'Stake':<6} {'Function PL':<12} {'Manual PL':<11} {'Match':<6}")
    print(f"{'-'*50}")
    
    for result, odd, stake in test_cases:
        function_pl = calculate_profit_loss(result, odd, stake)
        
        # Manual calculation
        if result == "WON":
            if odd >= 1.01:
                manual_pl = round((odd - 1.0) * stake, 4)
            else:
                manual_pl = round((1.01 - 1.0) * stake, 4)
        elif result == "LOSS":
            manual_pl = -stake
        else:  # VOID
            manual_pl = 0.0
        
        match = "YES" if abs(function_pl - manual_pl) < 0.001 else "NO"
        print(f"{result:<7} {odd:<6.2f} {stake:<6.1f} {function_pl:<12.4f} {manual_pl:<11.4f} {match:<6}")
    
    # Final verdict
    print(f"\n🎯 FINAL VERDICT:")
    print(f"{'='*80}")
    
    if len(mismatches) == 0:
        print(f"✅ PL_STORAGE_OK: No P/L storage issues found")
        verdict = "PL_STORAGE_OK"
    else:
        print(f"❌ PL_STORAGE_BROKEN: Found {len(mismatches)} P/L storage issues")
        verdict = "PL_STORAGE_BROKEN"
        
        # Determine root cause
        if len(zero_odds_issues) > len(mismatches) / 2:
            print(f"\n🔍 ROOT CAUSE: ZERO_ODDS_SETTLEMENT")
            print(f"   - {len(zero_odds_issues)} of {len(mismatches)} issues involve 0.00 odds")
            print(f"   - Predictions with 0.00 odds are being settled with P/L values")
            print(f"   - This is likely a data quality issue, not a calculation bug")
            print(f"   - FILE: Unknown (data source issue)")
            print(f"   - FUNCTION: Unknown (settlement process)")
            print(f"   - LINE_NUMBER: Unknown")
            
        elif "PERCENTAGE_ERROR" in issue_counts:
            print(f"\n🔍 ROOT CAUSE: PERCENTAGE_CONVERSION")
            print(f"   - {issue_counts['PERCENTAGE_ERROR']} cases show 100x multiplier error")
            print(f"   - This suggests a percentage conversion bug")
            print(f"   - FILE: Likely in settlement logic")
            print(f"   - FUNCTION: Unknown")
            print(f"   - LINE_NUMBER: Unknown")
            
        else:
            print(f"\n🔍 ROOT CAUSE: UNKNOWN")
            print(f"   - Mixed issue types detected")
            print(f"   - Further investigation needed")
            print(f"   - FILE: Unknown")
            print(f"   - FUNCTION: Unknown")
            print(f"   - LINE_NUMBER: Unknown")
    
    return verdict

if __name__ == "__main__":
    verdict = final_pl_forensic_audit()
    print(f"\n{'='*80}")
    print(f"🎯 FINAL VERDICT: {verdict}")
    print(f"{'='*80}")
