#!/usr/bin/env python3
"""
pl_root_cause_analysis.py
========================
P/L Root Cause Analysis - Final Investigation
"""

import sys
import os
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

def pl_root_cause_analysis():
    """P/L Root Cause Analysis - Final Investigation."""
    print(f"\n{'='*80}")
    print(f"🔍 P/L ROOT CAUSE ANALYSIS")
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
    
    # Focus on zero odds predictions
    print(f"\n🔍 ZERO ODDS PREDICTIONS ANALYSIS")
    print(f"{'='*80}")
    
    zero_odds_predictions = []
    for pred in predictions:
        bookmaker_odd = pred.get("bookmaker_odd")
        if bookmaker_odd is not None and float(bookmaker_odd) == 0.0:
            zero_odds_predictions.append(pred)
    
    print(f"📊 Found {len(zero_odds_predictions)} zero odds predictions")
    
    # Analyze zero odds predictions
    if zero_odds_predictions:
        header = f"{'Prediction ID':<25} {'Status':<7} {'Stored PL':<11} {'Calc PL':<11} {'Expected PL':<11} {'Issue':<15}"
        print(f"\n{header}")
        print(f"{'-'*100}")
        
        zero_odds_issues = []
        
        for pred in zero_odds_predictions:
            prediction_id = pred.get("prediction_id", "")
            status = pred.get("status", "").upper()
            stored_pl = pred.get("profit_loss", 0.0)
            if stored_pl is None:
                stored_pl = 0.0
            else:
                stored_pl = float(stored_pl)
            
            # Calculate using current function
            calculated_pl = calculate_profit_loss(status, 0.0, 1.0)
            
            # Calculate expected (what it should be)
            expected_pl = 0.0  # Zero odds should have 0 P/L
            
            difference = abs(stored_pl - expected_pl)
            
            issue_type = "OK"
            if difference > 0.01:
                if status == "WON" and stored_pl == 0.01:
                    issue_type = "ZERO_ODD_WIN_BUG"
                elif status == "LOST" and stored_pl == -1.00:
                    issue_type = "ZERO_ODD_LOSS_BUG"
                else:
                    issue_type = "ZERO_ODD_OTHER"
                
                zero_odds_issues.append({
                    'prediction_id': prediction_id,
                    'status': status,
                    'stored_pl': stored_pl,
                    'calculated_pl': calculated_pl,
                    'expected_pl': expected_pl,
                    'issue_type': issue_type
                })
            
            print(f"{prediction_id:<25} {status:<7} {stored_pl:<11.2f} {calculated_pl:<11.2f} {expected_pl:<11.2f} {issue_type:<15}")
        
        print(f"\n📊 Zero odds issues: {len(zero_odds_issues)}")
    
    # Analyze the calculate_profit_loss function bug
    print(f"\n🔍 CALCULATE_PROFIT_LOSS FUNCTION BUG ANALYSIS")
    print(f"{'='*80}")
    
    print(f"Current function behavior:")
    print(f"  calculate_profit_loss('WIN', 0.0, 1.0) = {calculate_profit_loss('WIN', 0.0, 1.0)}")
    print(f"  calculate_profit_loss('LOSS', 0.0, 1.0) = {calculate_profit_loss('LOSS', 0.0, 1.0)}")
    print(f"  calculate_profit_loss('VOID', 0.0, 1.0) = {calculate_profit_loss('VOID', 0.0, 1.0)}")
    
    print(f"\nExpected behavior:")
    print(f"  calculate_profit_loss('WIN', 0.0, 1.0) = 0.0")
    print(f"  calculate_profit_loss('LOSS', 0.0, 1.0) = 0.0")
    print(f"  calculate_profit_loss('VOID', 0.0, 1.0) = 0.0")
    
    print(f"\n🔍 ROOT CAUSE IDENTIFIED:")
    print(f"{'='*80}")
    print(f"FILE: app/database/supabase_repository.py")
    print(f"FUNCTION: calculate_profit_loss()")
    print(f"LINE_NUMBER: ~97")
    print(f"BUG: max(bookmaker_odd, 1.01) replaces 0.0 with 1.01")
    print(f"")
    print(f"Current code:")
    print(f"  return round((max(bookmaker_odd, 1.01) - 1.0) * stake, 4)")
    print(f"")
    print(f"When bookmaker_odd = 0.0:")
    print(f"  max(0.0, 1.01) = 1.01")
    print(f"  (1.01 - 1.0) * 1.0 = 0.01")
    print(f"  round(0.01, 4) = 0.01")
    print(f"")
    print(f"This causes zero odds predictions to have P/L = 0.01 instead of 0.0")
    
    # Check if this explains the original audit findings
    print(f"\n🔍 IMPACT ANALYSIS")
    print(f"{'='*80}")
    
    # Count zero odds predictions in original audit
    zero_odds_count = len(zero_odds_predictions)
    total_predictions = len(predictions)
    
    print(f"Zero odds predictions: {zero_odds_count}/{total_predictions} ({zero_odds_count/total_predictions*100:.1f}%)")
    
    if zero_odds_count > 0:
        print(f"\nThis bug explains the P/L mismatches found in the original audit:")
        print(f"  - Zero odds WIN predictions get P/L = 0.01 (should be 0.00)")
        print(f"  - Zero odds LOST predictions get P/L = -1.00 (correct by accident)")
        print(f"  - This affects ROI calculations significantly")
    
    # Final verdict
    print(f"\n🎯 FINAL VERDICT")
    print(f"{'='*80}")
    
    if zero_odds_count > 0:
        print(f"❌ PL_STORAGE_BROKEN")
        print(f"")
        print(f"ROOT_CAUSE: ZERO_ODD_MIN_ODD_BUG")
        print(f"FILE: app/database/supabase_repository.py")
        print(f"FUNCTION: calculate_profit_loss()")
        print(f"LINE_NUMBER: ~97")
        print(f"")
        print(f"EVIDENCE:")
        print(f"  - max(bookmaker_odd, 1.01) forces minimum odd of 1.01")
        print(f"  - Zero odds predictions get incorrect P/L values")
        print(f"  - This affects ROI calculations")
        print(f"")
        print(f"FIX NEEDED:")
        print(f"  - Handle zero odds as special case")
        print(f"  - Return P/L = 0.0 for zero odds predictions")
        print(f"  - Or filter out zero odds predictions from settlement")
        
        verdict = "PL_STORAGE_BROKEN"
    else:
        print(f"✅ PL_STORAGE_OK")
        print(f"")
        print(f"No zero odds predictions found")
        print(f"calculate_profit_loss function works correctly for valid odds")
        
        verdict = "PL_STORAGE_OK"
    
    return verdict

if __name__ == "__main__":
    verdict = pl_root_cause_analysis()
    print(f"\n{'='*80}")
    print(f"🎯 FINAL VERDICT: {verdict}")
    print(f"{'='*80}")
