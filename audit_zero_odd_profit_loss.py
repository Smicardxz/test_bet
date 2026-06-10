#!/usr/bin/env python3
"""
audit_zero_odd_profit_loss.py
=============================
Zero Odd Profit Loss Safety Audit
"""

import sys
import os
from datetime import datetime, date

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

def audit_zero_odd_profit_loss():
    """Zero Odd Profit Loss Safety Audit."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 ZERO ODD PROFIT LOSS SAFETY AUDIT")
    print(f"{'='*80}{RESET}")
    
    # Test the patched calculate_profit_loss function
    print(f"\n{CYAN}Testing patched calculate_profit_loss function{RESET}")
    print(f"{'-'*60}")
    
    try:
        from app.database.supabase_repository import calculate_profit_loss
    except Exception as e:
        print(f"❌ Failed to import calculate_profit_loss: {e}")
        return "ZERO_ODD_PL_BROKEN"
    
    # Test cases covering all scenarios
    test_cases = [
        # (result, bookmaker_odd, stake, expected_pl, description)
        ("WIN", 2.50, 1.0, 1.50, "Normal WIN with valid odds"),
        ("WIN", 1.95, 1.0, 0.95, "WIN with odds just above minimum"),
        ("WIN", 1.01, 1.0, 0.01, "WIN with minimum valid odds"),
        ("WIN", 1.00, 1.0, 0.0, "WIN with odds below minimum"),
        ("WIN", 0.50, 1.0, 0.0, "WIN with very low odds"),
        ("WIN", 0.00, 1.0, 0.0, "WIN with zero odds"),
        ("WIN", None, 1.0, 0.0, "WIN with None odds"),
        ("LOSS", 2.50, 1.0, -1.00, "Normal LOSS with valid odds"),
        ("LOSS", 1.95, 1.0, -1.00, "LOSS with odds just above minimum"),
        ("LOSS", 1.01, 1.0, -1.00, "LOSS with minimum valid odds"),
        ("LOSS", 1.00, 1.0, 0.0, "LOSS with odds below minimum"),
        ("LOSS", 0.50, 1.0, 0.0, "LOSS with very low odds"),
        ("LOSS", 0.00, 1.0, 0.0, "LOSS with zero odds"),
        ("LOSS", None, 1.0, 0.0, "LOSS with None odds"),
        ("VOID", 2.50, 1.0, 0.0, "VOID with valid odds"),
        ("VOID", 1.00, 1.0, 0.0, "VOID with invalid odds"),
        ("VOID", 0.00, 1.0, 0.0, "VOID with zero odds"),
        ("VOID", None, 1.0, 0.0, "VOID with None odds"),
    ]
    
    header = f"{'Result':<7} {'Odd':<6} {'Stake':<6} {'Expected':<10} {'Actual':<10} {'Status':<8} {'Description':<25}"
    print(f"{header}")
    print(f"{'-'*80}")
    
    all_passed = True
    failed_tests = []
    
    for result, odd, stake, expected, description in test_cases:
        try:
            actual = calculate_profit_loss(result, odd, stake)
            status = "PASS" if abs(actual - expected) < 0.001 else "FAIL"
            
            if status == "FAIL":
                all_passed = False
                failed_tests.append({
                    'result': result,
                    'odd': odd,
                    'stake': stake,
                    'expected': expected,
                    'actual': actual,
                    'description': description
                })
            
            # Format odd for display
            odd_display = f"{odd}" if odd is not None else "None"
            
            print(f"{result:<7} {odd_display:<6} {stake:<6.1f} {expected:<10.2f} {actual:<10.2f} {status:<8} {description:<25}")
            
        except Exception as e:
            print(f"{result:<7} {odd:<6} {stake:<6.1f} {expected:<10.2f} {'ERROR':<10} {'FAIL':<8} {description:<25}")
            all_passed = False
            failed_tests.append({
                'result': result,
                'odd': odd,
                'stake': stake,
                'expected': expected,
                'actual': f"ERROR: {e}",
                'description': description
            })
    
    print(f"\n{CYAN}Test Results Summary{RESET}")
    print(f"{'-'*60}")
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {len(test_cases) - len(failed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n{RED}Failed Tests:{RESET}")
        for i, test in enumerate(failed_tests, 1):
            print(f"  {i}. {test['description']}")
            print(f"     Expected: {test['expected']}, Got: {test['actual']}")
    
    # Test with real data if available
    print(f"\n{CYAN}Testing with real prediction data{RESET}")
    print(f"{'-'*60}")
    
    try:
        from app.database.supabase_repository import SupabaseRepository, _parse_reset_at
        repo = SupabaseRepository()
        tracking_reset_at = _parse_reset_at()
        
        # Get today's predictions
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
        
        # Test edge cases in real data
        edge_cases = []
        for pred in predictions:
            status = pred.get("status", "").upper()
            bookmaker_odd = pred.get("bookmaker_odd")
            
            if status in ["WON", "LOST", "VOID"]:
                if bookmaker_odd is None or bookmaker_odd <= 1.0:
                    edge_cases.append({
                        'prediction_id': pred.get("prediction_id", ""),
                        'status': status,
                        'bookmaker_odd': bookmaker_odd,
                        'stored_pl': pred.get("profit_loss", 0.0)
                    })
        
        print(f"📊 Found {len(edge_cases)} edge cases (invalid odds)")
        
        if edge_cases:
            header = f"{'Prediction ID':<25} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'New PL':<10} {'Status':<8}"
            print(f"\n{header}")
            print(f"{'-'*80}")
            
            for case in edge_cases[:10]:  # Show first 10
                prediction_id = case['prediction_id']
                status = case['status']
                odd = case['bookmaker_odd']
                stored_pl = case['stored_pl'] or 0.0
                
                new_pl = calculate_profit_loss(status, odd, 1.0)
                pl_status = "OK" if abs(new_pl - 0.0) < 0.001 else "ISSUE"
                
                odd_display = f"{odd}" if odd is not None else "None"
                print(f"{prediction_id:<25} {status:<7} {odd_display:<6} {stored_pl:<11.2f} {new_pl:<10.2f} {pl_status:<8}")
        
    except Exception as e:
        print(f"❌ Error testing with real data: {e}")
    
    # Final verdict
    print(f"\n{BOLD}🎯 FINAL VERDICT{RESET}")
    print(f"{'='*80}")
    
    if all_passed:
        print(f"{GREEN}✅ ZERO_ODD_PL_SAFE{RESET}")
        print(f"All test cases passed")
        print(f"Zero odd profit loss safety fix is working correctly")
        verdict = "ZERO_ODD_PL_SAFE"
    else:
        print(f"{RED}❌ ZERO_ODD_PL_BROKEN{RESET}")
        print(f"Failed tests detected")
        print(f"Zero odd profit loss safety fix needs attention")
        verdict = "ZERO_ODD_PL_BROKEN"
    
    return verdict

if __name__ == "__main__":
    verdict = audit_zero_odd_profit_loss()
    print(f"\n{BOLD}FINAL VERDICT: {verdict}{RESET}")
    print(f"{'='*80}")
