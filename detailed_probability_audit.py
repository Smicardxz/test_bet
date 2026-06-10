#!/usr/bin/env python3
"""
detailed_probability_audit.py
=============================
Detailed probability audit to find double multiplication issue.
"""

import sys
import os
import re

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

def detailed_probability_audit():
    """Detailed probability audit to find the 4167% issue."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 DETAILED PROBABILITY AUDIT")
    print(f"{'='*80}{RESET}")
    
    print(f"\n{CYAN}Investigating:{RESET}")
    print(f"  - Odd = 2.40")
    print(f"  - Expected: 1/2.40 = 0.4167 = 41.7%")
    print(f"  - Actual: 4167% (double multiplication)")
    
    # Step 1: Check all Python files for probability calculations
    print(f"\n{BOLD}🔍 STEP 1: SEARCHING FOR PROBABILITY CALCULATIONS{RESET}")
    print(f"{'='*80}")
    
    python_files = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    probability_patterns = [
        (r'1\s*/\s*\w*odd\w*\s*\*\s*100', 'basic_calc_multiply_100'),
        (r'\w*odd\w*\s*.*\s*1\s*/\s*\w*odd\w*\s*\*\s*100', 'odd_calc_multiply_100'),
        (r'probability.*=.*1\s*/\s*\w*odd\w*\s*\*\s*100', 'prob_assignment_multiply_100'),
        (r'implied_probability.*=.*1\s*/\s*\w*odd\w*\s*\*\s*100', 'implied_multiply_100'),
        (r'bookmaker_probability.*=.*1\s*/\s*\w*odd\w*\s*\*\s*100', 'bookmaker_multiply_100'),
        (r'(\w*probability\w*)\s*\*\s*100\s*\*\s*100', 'double_multiply_100'),
        (r'100\s*\*\s*(\w*probability\w*)\s*\*\s*100', '100_double_multiply'),
        (r'round\([^)]*probability[^)]*\s*\*\s*100\s*\*\s*100', 'round_double_multiply')
    ]
    
    findings = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, description in probability_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        # Find line number
                        match_str = match if isinstance(match, str) else str(match)
                        line_num = content[:content.find(match_str)].count('\n') + 1
                        
                        # Get context
                        line_start = content.rfind('\n', 0, content.find(match_str)) + 1
                        line_end = content.find('\n', content.find(match_str))
                        line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                        
                        findings.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': description,
                            'match': match_str,
                            'full_line': line.strip()
                        })
        
        except Exception as e:
            print(f"  {YELLOW}⚠️  Error reading {file_path}: {e}{RESET}")
    
    # Display findings
    if findings:
        print(f"\n{RED}❌ FOUND {len(findings)} PROBABILITY CALCULATION ISSUES:{RESET}")
        
        for i, finding in enumerate(findings, 1):
            print(f"\n{BOLD}Issue {i}:{RESET}")
            print(f"  File: {finding['file']}")
            print(f"  Line: {finding['line']}")
            print(f"  Pattern: {finding['pattern']}")
            print(f"  Match: {finding['match']}")
            print(f"  Full line: {finding['full_line']}")
            
            # Check if this is the double multiplication issue
            if 'double_multiply' in finding['pattern']:
                print(f"  {RED}>>> THIS IS LIKELY THE 4167% ISSUE! <<<{RESET}")
    else:
        print(f"\n{GREEN}✅ No obvious double multiplication patterns found{RESET}")
    
    # Step 2: Check for percentage formatting that might cause issues
    print(f"\n{BOLD}🔍 STEP 2: CHECKING PERCENTAGE FORMATTING{RESET}")
    print(f"{'='*80}")
    
    percentage_patterns = [
        (r'probability.*\*.*100.*\%', 'probability_to_percent'),
        (r'probability.*\.format.*\%', 'probability_format_percent'),
        (r'f".*probability.*\%.*"', 'probability_f_string_percent'),
        (r'round.*probability.*\*.*100', 'probability_round_multiply')
    ]
    
    percentage_findings = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, description in percentage_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        match_str = match if isinstance(match, str) else str(match)
                        line_num = content[:content.find(match_str)].count('\n') + 1
                        
                        line_start = content.rfind('\n', 0, content.find(match_str)) + 1
                        line_end = content.find('\n', content.find(match_str))
                        line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                        
                        percentage_findings.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': description,
                            'match': match_str,
                            'full_line': line.strip()
                        })
        
        except Exception as e:
            continue
    
    if percentage_findings:
        print(f"\n{YELLOW}⚠️  FOUND {len(percentage_findings)} PERCENTAGE FORMATTING PATTERNS:{RESET}")
        
        for i, finding in enumerate(percentage_findings[:5], 1):  # Show first 5
            print(f"\n{BOLD}Pattern {i}:{RESET}")
            print(f"  File: {finding['file']}")
            print(f"  Line: {finding['line']}")
            print(f"  Pattern: {finding['pattern']}")
            print(f"  Full line: {finding['full_line']}")
    
    # Step 3: Check database schema for probability field definitions
    print(f"\n{BOLD}🔍 STEP 3: CHECKING DATABASE SCHEMA{RESET}")
    print(f"{'='*80}")
    
    schema_file = 'app/database/schema.sql'
    if os.path.exists(schema_file):
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for probability columns
            prob_column_pattern = r'(\w*probability\w*)\s+(\w+)'
            matches = re.findall(prob_column_pattern, content, re.IGNORECASE)
            
            if matches:
                print(f"\n{CYAN}Probability columns in schema:{RESET}")
                for col_name, col_type in matches:
                    print(f"  {col_name}: {col_type}")
            
            # Look for specific probability-related tables
            table_patterns = [
                r'CREATE TABLE.*predictions',
                r'CREATE TABLE.*performance',
                r'CREATE TABLE.*model_performance'
            ]
            
            for pattern in table_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"\n{CYAN}Found table: {matches[0]}{RESET}")
                    # Show some context around this table
                    table_match = re.search(pattern, content, re.IGNORECASE)
                    if table_match:
                        start = table_match.start()
                        end = content.find(');', start) + 2
                        table_def = content[start:end]
                        
                        # Look for probability fields in this table
                        prob_fields = re.findall(r'(\w*probability\w*)\s+\w+', table_def, re.IGNORECASE)
                        if prob_fields:
                            print(f"  Probability fields: {[f[0] for f in prob_fields]}")
        
        except Exception as e:
            print(f"  {RED}❌ Error reading schema: {e}{RESET}")
    else:
        print(f"  {YELLOW}⚠️  Schema file not found{RESET}")
    
    # Step 4: Check specific files that handle odds and probabilities
    print(f"\n{BOLD}🔍 STEP 4: CHECKING SPECIFIC PROBABILITY FILES{RESET}")
    print(f"{'='*80}")
    
    specific_files = [
        'app/database/supabase_repository.py',
        'app/services/scanner/smart_scanner.py',
        'app/services/odds/odds_provider_manager.py',
        'app/services/settlement/auto_settler.py'
    ]
    
    for file_path in specific_files:
        if os.path.exists(file_path):
            print(f"\n{CYAN}Checking: {file_path}{RESET}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for specific probability-related operations
                specific_patterns = [
                    (r'implied_probability', 'implied_prob_usage'),
                    (r'bookmaker_probability', 'bookmaker_prob_usage'),
                    (r'market_probability', 'market_prob_usage'),
                    (r'1\s*/\s*odd', 'inverse_odds'),
                    (r'probability.*normalize', 'probability_normalize'),
                    (r'probability.*scale', 'probability_scale')
                ]
                
                file_findings = []
                for pattern, description in specific_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        file_findings.append({
                            'pattern': description,
                            'count': len(matches)
                        })
                
                if file_findings:
                    for finding in file_findings:
                        print(f"  {finding['pattern']}: {finding['count']} occurrences")
                else:
                    print(f"  No probability patterns found")
            
            except Exception as e:
                print(f"  {RED}❌ Error reading file: {e}{RESET}")
        else:
            print(f"\n{YELLOW}⚠️  File not found: {file_path}{RESET}")
    
    # Step 5: Create a comprehensive analysis
    print(f"\n{BOLD}🔍 STEP 5: COMPREHENSIVE ANALYSIS{RESET}")
    print(f"{'='*80}")
    
    # Check if we found the double multiplication issue
    double_multiply_found = any('double_multiply' in f['pattern'] for f in findings)
    
    if double_multiply_found:
        print(f"\n{RED}❌ DOUBLE MULTIPLICATION ISSUE CONFIRMED{RESET}")
        print(f"  Found patterns that multiply by 100 twice")
        print(f"  This explains the 4167% issue (should be 41.7%)")
        
        # Show the specific files/lines
        double_finds = [f for f in findings if 'double_multiply' in f['pattern']]
        for find in double_finds:
            print(f"\n{YELLOW}Location of the bug:{RESET}")
            print(f"  File: {find['file']}")
            print(f"  Line: {find['line']}")
            print(f"  Code: {find['full_line']}")
    else:
        print(f"\n{GREEN}✅ No double multiplication found in Python code{RESET}")
        print(f"  The 4167% issue might be:")
        print(f"  1. In frontend JavaScript code")
        print(f"  2. In database query/transform")
        print(f"  3. In API response formatting")
        print(f"  4. In data visualization layer")
    
    # Step 6: Check for the specific bookmaker probability calculation
    print(f"\n{BOLD}🔍 STEP 6: SPECIFIC BOOKMAKER PROBABILITY INVESTIGATION{RESET}")
    print(f"{'='*80}")
    
    print(f"\n{CYAN}Expected calculation flow:{RESET}")
    print(f"  1. Bookmaker odd = 2.40")
    print(f"  2. Implied probability = 1 / 2.40 = 0.4167")
    print(f"  3. For display: 0.4167 * 100 = 41.7%")
    print(f"  4. Bug: 0.4167 * 100 * 100 = 4167%")
    
    # Look for the specific calculation pattern
    repo_file = 'app/database/supabase_repository.py'
    if os.path.exists(repo_file):
        try:
            with open(repo_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for the specific line where implied_probability is calculated
            calc_patterns = [
                r'implied_prob\s*=\s*round\s*\(\s*1\.0\s*/\s*bookmaker_odd\s*,\s*4\s*\)',
                r'implied_prob\s*=\s*1\.0\s*/\s*bookmaker_odd',
                r'implied_probability\s*=\s*1\s*/\s*bookmaker_odd'
            ]
            
            for pattern in calc_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    print(f"\n{GREEN}✅ Found implied_probability calculation:{RESET}")
                    for match in matches:
                        line_num = content[:content.find(match)].count('\n') + 1
                        print(f"  Line {line_num}: {match}")
                        
                        # Show surrounding context
                        line_start = content.rfind('\n', 0, content.find(match)) + 1
                        line_end = content.find('\n', content.find(match))
                        line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                        print(f"  Full line: {line.strip()}")
            
            # Check if there's any multiplication by 100 after this calculation
            implied_calc_line = None
            for pattern in calc_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    implied_calc_line = content[:content.find(matches[0])].count('\n') + 1
                    break
            
            if implied_calc_line:
                # Check next few lines for multiplication by 100
                lines = content.split('\n')
                for i in range(implied_calc_line, min(implied_calc_line + 10, len(lines))):
                    line = lines[i]
                    if re.search(r'\*.*100', line) and 'implied' in line.lower():
                        print(f"\n{RED}❌ FOUND MULTIPLICATION BY 100 AFTER IMPLIED PROBABILITY:{RESET}")
                        print(f"  Line {i+1}: {line.strip()}")
        
        except Exception as e:
            print(f"  {RED}❌ Error reading repository file: {e}{RESET}")
    
    # Export findings
    print(f"\n{BOLD}🔍 EXPORTING DETAILED FINDINGS{RESET}")
    print(f"{'='*60}")
    
    with open('detailed_probability_audit.txt', 'w', encoding='utf-8') as f:
        f.write("DETAILED PROBABILITY AUDIT RESULTS\n")
        f.write("="*50 + "\n\n")
        
        f.write("4167% vs 41.7% Issue Investigation\n")
        f.write("-"*40 + "\n")
        f.write("Expected: 1/2.40 = 0.4167 = 41.7%\n")
        f.write("Actual: 4167% (indicates double multiplication)\n\n")
        
        if double_multiply_found:
            f.write("CONFIRMED: Double multiplication found\n")
            for find in findings:
                if 'double_multiply' in find['pattern']:
                    f.write(f"File: {find['file']}\n")
                    f.write(f"Line: {find['line']}\n")
                    f.write(f"Code: {find['full_line']}\n\n")
        else:
            f.write("NOT FOUND: Double multiplication not in Python code\n")
            f.write("Issue likely in frontend or another layer\n\n")
        
        f.write("All Probability Calculation Findings:\n")
        f.write("-"*40 + "\n")
        for find in findings:
            f.write(f"File: {find['file']}\n")
            f.write(f"Line: {find['line']}\n")
            f.write(f"Pattern: {find['pattern']}\n")
            f.write(f"Code: {find['full_line']}\n")
            f.write("-"*30 + "\n")
    
    print(f"  Findings exported to: detailed_probability_audit.txt")
    
    return double_multiply_found

if __name__ == "__main__":
    success = detailed_probability_audit()
    sys.exit(0 if success else 1)
