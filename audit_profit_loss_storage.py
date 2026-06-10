#!/usr/bin/env python3
"""
audit_profit_loss_storage.py
============================
Profit/Loss Storage Forensic Audit
"""

import sys
import os
import re
import argparse
from datetime import datetime, date, timezone
from typing import Dict, List, Tuple, Any, Optional

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

class ProfitLossStorageAudit:
    def __init__(self):
        self.repo = None
        self.today = date.today().isoformat()
        self.tracking_reset_at = None
        self.mismatches = []
        
    def _get_repo(self):
        """Get repository instance."""
        if self.repo is None:
            try:
                from app.database.supabase_repository import SupabaseRepository, _parse_reset_at
                self.repo = SupabaseRepository()
                self.tracking_reset_at = _parse_reset_at()
            except Exception as e:
                print(f"❌ Failed to initialize repository: {e}")
                return None
        return self.repo
    
    def _get_today_predictions(self) -> List[dict]:
        """Get all predictions created today (POST_RESET only)."""
        repo = self._get_repo()
        if not repo:
            return []
        
        try:
            # Get predictions created today
            today_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
            today_end = datetime.combine(date.today(), datetime.max.time()).isoformat()
            
            q = (
                repo._client.table("predictions")
                .select("*")
                .gte("prediction_date", today_start)
                .lte("prediction_date", today_end)
                .order("prediction_date", desc=True)
            )
            
            # Apply POST_RESET filter if available
            if self.tracking_reset_at:
                from app.database.supabase_repository import _apply_since_filter
                q = _apply_since_filter(q, self.tracking_reset_at)
            
            predictions = q.execute().data or []
            print(f"📊 Found {len(predictions)} predictions today")
            
            # Filter by status
            filtered_predictions = []
            for pred in predictions:
                status = pred.get("status", "").upper()
                if status in ["WON", "LOST", "VOID", "PENDING"]:
                    filtered_predictions.append(pred)
            
            print(f"📊 Filtered to {len(filtered_predictions)} valid status predictions")
            return filtered_predictions
            
        except Exception as e:
            print(f"❌ Error fetching today's predictions: {e}")
            return []
    
    def _recompute_profit_loss(self, prediction: dict) -> float:
        """Recompute profit/loss for a prediction."""
        status = prediction.get("status", "").upper()
        bookmaker_odd = prediction.get("bookmaker_odd")
        
        if bookmaker_odd is None or bookmaker_odd < 1.1:
            return 0.0
        
        if status == "WON":
            return float(bookmaker_odd) - 1.0
        elif status == "LOST":
            return -1.0
        elif status == "VOID":
            return 0.0
        elif status == "PENDING":
            return 0.0  # Exclude from ROI
        else:
            return 0.0
    
    def find_mismatches(self, predictions: List[dict]) -> List[dict]:
        """Find all P/L mismatches."""
        print(f"\n{BOLD}🔍 FINDING P/L MISMATCHES{RESET}")
        print(f"{'='*80}")
        
        mismatches = []
        
        header = f"{'Prediction ID':<25} {'Match':<20} {'Market':<15} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'Recomp PL':<11} {'Diff':<8} {'Flag':<12}"
        print(f"{header}")
        print(f"{'-'*130}")
        
        for pred in predictions:
            status = pred.get("status", "").upper()
            if status not in ["WON", "LOST", "VOID"]:
                continue  # Only settled predictions
            
            prediction_id = pred.get("prediction_id", "") or ""
            match = pred.get("fixture_id", "") or ""
            market = pred.get("market", "") or ""
            bookmaker_odd = pred.get("bookmaker_odd") or 0.0
            
            stored_pl = pred.get("profit_loss", 0.0)
            if stored_pl is None:
                stored_pl = 0.0
            else:
                stored_pl = float(stored_pl)
            
            recomputed_pl = self._recompute_profit_loss(pred)
            difference = abs(stored_pl - recomputed_pl)
            
            flag = "PL_MISMATCH" if difference > 0.01 else "OK"
            
            if flag == "PL_MISMATCH" or difference > 0.001:  # Show small differences too
                mismatches.append({
                    'prediction_id': prediction_id,
                    'match': match,
                    'market': market,
                    'status': status,
                    'bookmaker_odd': bookmaker_odd,
                    'stored_profit_loss': stored_pl,
                    'recomputed_profit_loss': recomputed_pl,
                    'difference': difference,
                    'flag': flag
                })
                
                print(f"{prediction_id:<25} {match:<20} {market:<15} {status:<7} {bookmaker_odd:<6.2f} {stored_pl:<11.2f} {recomputed_pl:<11.2f} {difference:<8.3f} {flag:<12}")
        
        print(f"\n📊 Found {len(mismatches)} P/L mismatches")
        self.mismatches = mismatches
        return mismatches
    
    def trace_profit_loss_storage(self) -> Dict[str, Any]:
        """Trace where profit_loss is stored and calculated."""
        print(f"\n{BOLD}🔍 TRACING PROFIT/LOSS STORAGE{RESET}")
        print(f"{'='*80}")
        
        trace_info = {}
        
        # Step 1: Find all files that write profit_loss
        print(f"\n{CYAN}Step 1: Finding profit_loss write operations{RESET}")
        print(f"{'-'*60}")
        
        profit_loss_writes = []
        
        # Search in key files
        key_files = [
            'app/database/supabase_repository.py',
            'app/services/settlement/auto_settler.py',
            'app_flask.py',
            'app/pipelines/settlement_pipeline.py'
        ]
        
        for file_path in key_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for profit_loss assignments
                    patterns = [
                        (r'profit_loss\s*=\s*([^,;)]+)', 'assignment'),
                        (r'profit_loss\s*:\s*([^,;)]+)', 'type_hint'),
                        (r'["\']profit_loss["\']\s*:\s*([^,;)]+)', 'json_assignment'),
                        (r'\.update\([^)]*profit_loss[^)]*\)', 'update_call'),
                        (r'\.upsert\([^)]*profit_loss[^)]*\)', 'upsert_call')
                    ]
                    
                    for pattern, pattern_type in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_start = content.rfind('\n', 0, match.start()) + 1
                            line_end = content.find('\n', match.start())
                            line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                            
                            profit_loss_writes.append({
                                'file': file_path,
                                'line': line_num,
                                'pattern_type': pattern_type,
                                'match': match.group(1),
                                'full_line': line.strip()
                            })
                
                except Exception as e:
                    print(f"  ❌ Error reading {file_path}: {e}")
        
        # Display profit_loss write operations
        print(f"\n📊 Found {len(profit_loss_writes)} profit_loss write operations:")
        for i, write in enumerate(profit_loss_writes, 1):
            print(f"  {i}. {write['file']}:{write['line']} ({write['pattern_type']})")
            print(f"     {write['full_line']}")
        
        trace_info['profit_loss_writes'] = profit_loss_writes
        
        # Step 2: Find settlement calculation functions
        print(f"\n{CYAN}Step 2: Finding settlement calculation functions{RESET}")
        print(f"{'-'*60}")
        
        settlement_functions = []
        
        # Focus on auto_settler.py
        settler_file = 'app/services/settlement/auto_settler.py'
        if os.path.exists(settler_file):
            try:
                with open(settler_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find function definitions
                function_patterns = [
                    (r'def\s+(\w+).*?profit_loss', 'function_with_pl'),
                    (r'def\s+(\w+).*?settle', 'settlement_function'),
                    (r'def\s+(\w+).*?calculate', 'calculation_function')
                ]
                
                for pattern, func_type in function_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        func_name = match.group(1)
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Get function body
                        func_start = match.end()
                        func_body_start = content.find(':', func_start) + 1
                        
                        # Find next function or class
                        next_pattern = r'\n(?:def |\nclass |\n# |\Z)'
                        next_match = re.search(next_pattern, content[func_body_start:])
                        
                        if next_match:
                            func_body = content[func_body_start:func_body_start + next_match.start()]
                        else:
                            func_body = content[func_body_start:]
                        
                        settlement_functions.append({
                            'function_name': func_name,
                            'file': settler_file,
                            'line': line_num,
                            'function_type': func_type,
                            'function_body': func_body[:500] + "..." if len(func_body) > 500 else func_body
                        })
                
            except Exception as e:
                print(f"  ❌ Error reading {settler_file}: {e}")
        
        # Display settlement functions
        print(f"\n📊 Found {len(settlement_functions)} settlement-related functions:")
        for i, func in enumerate(settlement_functions, 1):
            print(f"  {i}. {func['function_name']}() at {func['file']}:{func['line']} ({func['function_type']})")
        
        trace_info['settlement_functions'] = settlement_functions
        
        # Step 3: Analyze specific P/L calculation formulas
        print(f"\n{CYAN}Step 3: Analyzing P/L calculation formulas{RESET}")
        print(f"{'-'*60}")
        
        pl_formulas = []
        
        for func in settlement_functions:
            func_body = func['function_body']
            
            # Look for P/L calculation patterns
            formula_patterns = [
                (r'profit_loss\s*=\s*([^,\n]+)', 'pl_assignment'),
                (r'bookmaker_odd\s*-\s*1', 'won_formula'),
                (r'-1', 'lost_formula'),
                (r'0', 'void_formula'),
                (r'if.*WON', 'won_condition'),
                (r'if.*LOST', 'lost_condition'),
                (r'if.*VOID', 'void_condition')
            ]
            
            for pattern, formula_type in formula_patterns:
                matches = re.finditer(pattern, func_body, re.IGNORECASE)
                for match in matches:
                    formula = match.group(1) if match.groups() else match.group(0)
                    pl_formulas.append({
                        'function': func['function_name'],
                        'file': func['file'],
                        'formula_type': formula_type,
                        'formula': formula,
                        'context': func_body[max(0, match.start()-50):match.end()+50]
                    })
        
        # Display P/L formulas
        print(f"\n📊 Found {len(pl_formulas)} P/L calculation formulas:")
        for i, formula in enumerate(pl_formulas, 1):
            print(f"  {i}. {formula['function']}() - {formula['formula_type']}")
            print(f"     Formula: {formula['formula']}")
            print(f"     Context: ...{formula['context']}...")
        
        trace_info['pl_formulas'] = pl_formulas
        
        # Step 4: Check for specific issues
        print(f"\n{CYAN}Step 4: Checking for specific issues{RESET}")
        print(f"{'-'*60}")
        
        issues = []
        
        # Check all files for common issues
        all_files = []
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
            for file in files:
                if file.endswith('.py'):
                    all_files.append(os.path.join(root, file))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for specific issues
                issue_patterns = [
                    (r'profit_loss.*\*.*100', 'percentage_conversion'),
                    (r'profit_loss.*\/.*100', 'percentage_division'),
                    (r'profit_loss.*\*.*stake', 'stake_applied'),
                    (r'profit_loss.*\/.*stake', 'stake_division'),
                    (r'profit_loss.*\*.*2', 'double_multiplier'),
                    (r'profit_loss.*\+.*profit_loss', 'double_addition'),
                    (r'profit_loss.*=.*profit_loss', 'self_reference'),
                    (r'bookmaker_odd.*\*.*100', 'odds_percentage'),
                    (r'ROI.*profit_loss', 'roi_calculation')
                ]
                
                for pattern, issue_type in issue_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.start())
                        line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                        
                        issues.append({
                            'file': file_path,
                            'line': line_num,
                            'issue_type': issue_type,
                            'pattern': match.group(0),
                            'full_line': line.strip()
                        })
                
            except Exception as e:
                continue
        
        # Display issues
        print(f"\n📊 Found {len(issues)} potential issues:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue['file']}:{issue['line']} ({issue['issue_type']})")
            print(f"     {issue['full_line']}")
        
        trace_info['issues'] = issues
        
        return trace_info
    
    def verify_pl_calculations(self, predictions: List[dict]) -> Dict[str, Any]:
        """Verify P/L calculations against expected formulas."""
        print(f"\n{BOLD}🔍 VERIFYING P/L CALCULATIONS{RESET}")
        print(f"{'='*80}")
        
        verification_results = {
            'won_correct': 0,
            'won_incorrect': 0,
            'lost_correct': 0,
            'lost_incorrect': 0,
            'void_correct': 0,
            'void_incorrect': 0,
            'details': []
        }
        
        header = f"{'Prediction ID':<25} {'Status':<7} {'Odd':<6} {'Stored PL':<11} {'Expected PL':<11} {'Correct':<8} {'Issue':<15}"
        print(f"{header}")
        print(f"{'-'*100}")
        
        for pred in predictions:
            status = pred.get("status", "").upper()
            if status not in ["WON", "LOST", "VOID"]:
                continue
            
            prediction_id = pred.get("prediction_id", "") or ""
            bookmaker_odd = pred.get("bookmaker_odd") or 0.0
            stored_pl = pred.get("profit_loss", 0.0)
            if stored_pl is None:
                stored_pl = 0.0
            else:
                stored_pl = float(stored_pl)
            
            # Calculate expected P/L
            expected_pl = 0.0
            if status == "WON":
                expected_pl = float(bookmaker_odd) - 1.0
            elif status == "LOST":
                expected_pl = -1.0
            elif status == "VOID":
                expected_pl = 0.0
            
            # Check if correct
            is_correct = abs(stored_pl - expected_pl) < 0.01
            issue = ""
            
            if not is_correct:
                if status == "WON":
                    verification_results['won_incorrect'] += 1
                    if abs(stored_pl - (expected_pl * 100)) < 0.01:
                        issue = "PERCENTAGE_ERROR"
                    elif abs(stored_pl - (expected_pl * 2)) < 0.01:
                        issue = "DOUBLE_ERROR"
                    elif abs(stored_pl - (expected_pl / 10)) < 0.01:
                        issue = "DIVISION_ERROR"
                    else:
                        issue = "UNKNOWN_ERROR"
                elif status == "LOST":
                    verification_results['lost_incorrect'] += 1
                    if abs(stored_pl - (-100)) < 0.01:
                        issue = "PERCENTAGE_ERROR"
                    elif abs(stored_pl - (-2)) < 0.01:
                        issue = "DOUBLE_ERROR"
                    elif abs(stored_pl - (-0.1)) < 0.01:
                        issue = "DIVISION_ERROR"
                    else:
                        issue = "UNKNOWN_ERROR"
                elif status == "VOID":
                    verification_results['void_incorrect'] += 1
                    if abs(stored_pl) > 0.01:
                        issue = "VOID_NOT_ZERO"
                    else:
                        issue = "UNKNOWN_ERROR"
            else:
                if status == "WON":
                    verification_results['won_correct'] += 1
                elif status == "LOST":
                    verification_results['lost_correct'] += 1
                elif status == "VOID":
                    verification_results['void_correct'] += 1
            
            # Show mismatches
            if not is_correct:
                verification_results['details'].append({
                    'prediction_id': prediction_id,
                    'status': status,
                    'bookmaker_odd': bookmaker_odd,
                    'stored_pl': stored_pl,
                    'expected_pl': expected_pl,
                    'is_correct': is_correct,
                    'issue': issue
                })
                
                print(f"{prediction_id:<25} {status:<7} {bookmaker_odd:<6.2f} {stored_pl:<11.2f} {expected_pl:<11.2f} {is_correct:<8} {issue:<15}")
        
        # Summary
        total_correct = verification_results['won_correct'] + verification_results['lost_correct'] + verification_results['void_correct']
        total_incorrect = verification_results['won_incorrect'] + verification_results['lost_incorrect'] + verification_results['void_incorrect']
        
        print(f"\n📊 Verification Summary:")
        print(f"  WON: {verification_results['won_correct']} correct, {verification_results['won_incorrect']} incorrect")
        print(f"  LOST: {verification_results['lost_correct']} correct, {verification_results['lost_incorrect']} incorrect")
        print(f"  VOID: {verification_results['void_correct']} correct, {verification_results['void_incorrect']} incorrect")
        print(f"  TOTAL: {total_correct} correct, {total_incorrect} incorrect")
        
        return verification_results
    
    def analyze_root_cause(self, trace_info: Dict[str, Any], verification_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze root cause of P/L mismatches."""
        print(f"\n{BOLD}🔍 ANALYZING ROOT CAUSE{RESET}")
        print(f"{'='*80}")
        
        root_cause = {
            'primary_issue': 'UNKNOWN',
            'file': 'UNKNOWN',
            'function': 'UNKNOWN',
            'line_number': 'UNKNOWN',
            'evidence': []
        }
        
        # Analyze verification results
        issue_types = {}
        for detail in verification_results['details']:
            issue = detail['issue']
            if issue not in issue_types:
                issue_types[issue] = 0
            issue_types[issue] += 1
        
        print(f"\n📊 Issue Type Analysis:")
        for issue_type, count in issue_types.items():
            print(f"  {issue_type}: {count} occurrences")
        
        # Determine primary issue
        if 'PERCENTAGE_ERROR' in issue_types and issue_types['PERCENTAGE_ERROR'] > 0:
            root_cause['primary_issue'] = 'PERCENTAGE_CONVERSION'
            root_cause['evidence'].append('Multiple P/L values are 100x expected')
        
        if 'DOUBLE_ERROR' in issue_types and issue_types['DOUBLE_ERROR'] > 0:
            root_cause['primary_issue'] = 'DOUBLE_MULTIPLICATION'
            root_cause['evidence'].append('Multiple P/L values are 2x expected')
        
        # Analyze trace info for source
        for write in trace_info['profit_loss_writes']:
            if 'profit_loss' in write['full_line'].lower():
                if '100' in write['full_line']:
                    root_cause['file'] = write['file']
                    root_cause['function'] = 'UNKNOWN'
                    root_cause['line_number'] = write['line']
                    root_cause['evidence'].append(f"Found 100 in profit_loss calculation at {write['file']}:{write['line']}")
                    break
        
        # Check settlement functions
        for func in trace_info['settlement_functions']:
            func_body = func['function_body']
            if 'profit_loss' in func_body and '100' in func_body:
                root_cause['file'] = func['file']
                root_cause['function'] = func['function_name']
                root_cause['evidence'].append(f"Found 100 in {func['function_name']}() in {func['file']}")
        
        # Check specific issues
        for issue in trace_info['issues']:
            if issue['issue_type'] == 'percentage_conversion':
                root_cause['file'] = issue['file']
                root_cause['line_number'] = issue['line']
                root_cause['evidence'].append(f"Found percentage conversion at {issue['file']}:{issue['line']}")
                break
        
        return root_cause
    
    def final_verdict(self, trace_info: Dict[str, Any], verification_results: Dict[str, Any], root_cause: Dict[str, Any]) -> str:
        """Generate final verdict."""
        print(f"\n{BOLD}🔍 FINAL VERDICT{RESET}")
        print(f"{'='*80}")
        
        total_incorrect = (verification_results['won_incorrect'] + 
                          verification_results['lost_incorrect'] + 
                          verification_results['void_incorrect'])
        
        if total_incorrect == 0:
            verdict = "PL_STORAGE_OK"
            print(f"{GREEN}✅ PL_STORAGE_OK: No P/L storage issues found{RESET}")
        else:
            verdict = "PL_STORAGE_BROKEN"
            print(f"{RED}❌ PL_STORAGE_BROKEN: Found {total_incorrect} P/L storage issues{RESET}")
            
            print(f"\n{CYAN}Root Cause Analysis:{RESET}")
            print(f"  Primary Issue: {root_cause['primary_issue']}")
            print(f"  File: {root_cause['file']}")
            print(f"  Function: {root_cause['function']}")
            print(f"  Line Number: {root_cause['line_number']}")
            
            print(f"\n{CYAN}Evidence:{RESET}")
            for evidence in root_cause['evidence']:
                print(f"  - {evidence}")
        
        return verdict

def main():
    """Main audit function."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 PROFIT/LOSS STORAGE FORENSIC AUDIT")
    print(f"{'='*80}{RESET}")
    
    audit = ProfitLossStorageAudit()
    
    # Get today's predictions
    predictions = audit._get_today_predictions()
    
    if not predictions:
        print(f"❌ No predictions found for today")
        return
    
    # Find mismatches
    mismatches = audit.find_mismatches(predictions)
    
    if not mismatches:
        print(f"✅ No P/L mismatches found")
        print(f"✅ PL_STORAGE_OK")
        return
    
    # Trace profit_loss storage
    trace_info = audit.trace_profit_loss_storage()
    
    # Verify P/L calculations
    verification_results = audit.verify_pl_calculations(predictions)
    
    # Analyze root cause
    root_cause = audit.analyze_root_cause(trace_info, verification_results)
    
    # Generate final verdict
    verdict = audit.final_verdict(trace_info, verification_results, root_cause)
    
    print(f"\n{BOLD}🎯 AUDIT COMPLETE{RESET}")
    print(f"{'='*80}")
    print(f"Final Verdict: {verdict}")

if __name__ == "__main__":
    main()
