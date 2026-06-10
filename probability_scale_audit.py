#!/usr/bin/env python3
"""
probability_scale_audit.py
===========================
Probability Scale Audit
Verify all probability fields use the same scale.
"""

import sys
import os
import re
import json
from typing import Dict, List, Tuple, Any

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

def find_probability_fields_in_file(file_path: str) -> Dict[str, List[Dict]]:
    """Find probability fields and their usage in a file."""
    findings = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Probability field patterns
        probability_fields = [
            'model_probability',
            'implied_probability', 
            'market_probability',
            'bookmaker_probability',
            'fair_probability',
            'confidence_score'
        ]
        
        for field in probability_fields:
            field_findings = []
            
            # Find all occurrences of the field
            pattern = rf'{re.escape(field)}[^\w]'
            matches = list(re.finditer(pattern, content))
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.start())
                line = content[line_start:line_end] if line_end != -1 else content[line_start:]
                
                # Look for scaling operations near this field
                scaling_context = []
                
                # Check for multiplication/division by 100 in the same line
                if re.search(r'\*.*100|100.*\*|/.*100|100.*/', line):
                    scaling_context.append('multiplication_by_100')
                
                # Check for percentage conversion
                if re.search(r'round.*\%|\.format.*\%|f".*%\|.*percentage', line):
                    scaling_context.append('percentage_formatting')
                
                # Look for assignment patterns
                assignment_pattern = rf'{re.escape(field)}\s*=\s*([^,;)]+)'
                assignment_match = re.search(assignment_pattern, line)
                if assignment_match:
                    value = assignment_match.group(1).strip()
                    scaling_context.append(f'assignment:{value}')
                
                field_findings.append({
                    'line': line_num,
                    'line_content': line.strip(),
                    'scaling_context': scaling_context
                })
            
            if field_findings:
                findings[field] = field_findings
    
    except Exception as e:
        print(f"  {YELLOW}⚠️  Error reading {file_path}: {e}{RESET}")
    
    return findings

def analyze_api_endpoints():
    """Analyze API endpoints for probability scaling."""
    print(f"\n{BOLD}🔍 ANALYZING API ENDPOINTS{RESET}")
    print(f"{'='*80}")
    
    try:
        with open('app_flask.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find API endpoint functions
        endpoint_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]\)\s*\ndef\s+(\w+)'
        endpoints = re.findall(endpoint_pattern, content)
        
        api_endpoints = [(route, func) for route, func in endpoints if '/api/' in route]
        
        print(f"  Found {len(api_endpoints)} API endpoints")
        
        # Analyze each endpoint for probability fields
        endpoint_analysis = {}
        
        for route, func_name in api_endpoints:
            # Find function body
            func_pattern = rf'@app\.route\([\'"]{re.escape(route)}[\'"][^)]*\)\s*\ndef\s+{func_name}'
            func_match = re.search(func_pattern, content)
            
            if func_match:
                func_start = func_match.end()
                func_body_start = content.find(':', func_start) + 1
                
                # Find next function or route
                next_pattern = r'\n(?:@app\.route|def |\nclass |$)'
                next_match = re.search(next_pattern, content[func_body_start:])
                
                if next_match:
                    func_body = content[func_body_start:func_body_start + next_match.start()]
                else:
                    func_body = content[func_body_start:]
                
                # Find probability fields in this function
                prob_findings = find_probability_fields_in_content(func_body)
                
                if prob_findings:
                    endpoint_analysis[route] = {
                        'function': func_name,
                        'probability_fields': prob_findings
                    }
        
        return endpoint_analysis
    
    except Exception as e:
        print(f"  {RED}❌ Error analyzing API endpoints: {e}{RESET}")
        return {}

def find_probability_fields_in_content(content: str) -> Dict[str, List[str]]:
    """Find probability fields in content."""
    findings = {}
    
    probability_fields = [
        'model_probability',
        'implied_probability', 
        'market_probability',
        'bookmaker_probability',
        'fair_probability',
        'confidence_score'
    ]
    
    for field in probability_fields:
        if field in content:
            # Find lines containing this field
            lines = content.split('\n')
            field_lines = []
            
            for i, line in enumerate(lines):
                if field in line:
                    field_lines.append(f"Line {i+1}: {line.strip()}")
            
            findings[field] = field_lines
    
    return findings

def analyze_database_schema():
    """Analyze database schema for probability field definitions."""
    print(f"\n{BOLD}🔍 ANALYZING DATABASE SCHEMA{RESET}")
    print(f"{'='*80}")
    
    schema_file = 'app/database/schema.sql'
    if not os.path.exists(schema_file):
        print(f"  {YELLOW}⚠️  Schema file not found: {schema_file}{RESET}")
        return {}
    
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find probability-related columns
        probability_fields = [
            'model_probability',
            'implied_probability', 
            'market_probability',
            'bookmaker_probability',
            'fair_probability',
            'confidence_score'
        ]
        
        schema_findings = {}
        
        for field in probability_fields:
            # Look for column definitions
            pattern = rf'{re.escape(field)}\s+(\w+)'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            if matches:
                schema_findings[field] = matches
        
        return schema_findings
    
    except Exception as e:
        print(f"  {RED}❌ Error reading schema: {e}{RESET}")
        return {}

def analyze_supabase_repository():
    """Analyze Supabase repository for probability scaling."""
    print(f"\n{BOLD}🔍 ANALYZING SUPABASE REPOSITORY{RESET}")
    print(f"{'='*80}")
    
    repo_file = 'app/database/supabase_repository.py'
    if not os.path.exists(repo_file):
        print(f"  {YELLOW}⚠️  Repository file not found: {repo_file}{RESET}")
        return {}
    
    try:
        with open(repo_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find probability scaling operations
        scaling_patterns = [
            (r'(\w*probability\w*)\s*\*\s*100', 'multiply_by_100'),
            (r'(\w*probability\w*)\s*/\s*100', 'divide_by_100'),
            (r'100\s*\*\s*(\w*probability\w*)', '100_multiply'),
            (r'100\s*/\s*(\w*probability\w*)', '100_divide'),
            (r'round\([^)]*probability[^)]*\s*\*\s*100', 'round_multiply_100'),
            (r'round\([^)]*probability[^)]*\s*/\s*100', 'round_divide_100')
        ]
        
        scaling_findings = {}
        
        for pattern, operation in scaling_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                scaling_findings[operation] = matches
        
        # Look for specific bookmaker probability calculation
        bookmaker_patterns = [
            r'bookmaker.*probability.*=.*1\s*/\s*odd',
            r'probability.*=.*1\s*/\s*bookmaker.*odd',
            r'implied_probability.*=.*1\s*/\s*odd'
        ]
        
        bookmaker_findings = []
        for pattern in bookmaker_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                bookmaker_findings.extend(matches)
        
        # Find the specific issue: 1/2.40 = 41.7% but showing 4167%
        error_patterns = [
            r'1\s*/\s*odd\s*\*\s*100\s*\*\s*100',  # Double multiplication
            r'probability.*\*\s*100\s*\*\s*100',     # Double multiplication
        ]
        
        error_findings = []
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                error_findings.extend(matches)
        
        return {
            'scaling_operations': scaling_findings,
            'bookmaker_calculations': bookmaker_findings,
            'double_multiplication_errors': error_findings,
            'full_content': content  # For detailed analysis
        }
    
    except Exception as e:
        print(f"  {RED}❌ Error reading repository: {e}{RESET}")
        return {}

def analyze_smart_scanner():
    """Analyze SmartScanner for probability scaling."""
    print(f"\n{BOLD}🔍 ANALYZING SMART SCANNER{RESET}")
    print(f"{'='*80}")
    
    scanner_file = 'app/services/scanner/smart_scanner.py'
    if not os.path.exists(scanner_file):
        print(f"  {YELLOW}⚠️  Scanner file not found: {scanner_file}{RESET}")
        return {}
    
    try:
        with open(scanner_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find EV candidate creation and probability scaling
        findings = find_probability_fields_in_content(content)
        
        # Look for specific scaling operations in EV candidate creation
        ev_patterns = [
            r'market_probability.*=',
            r'implied_probability.*=',
            r'fair_odd.*=',
            r'edge_percent.*=',
            r'ev_percent.*='
        ]
        
        ev_findings = {}
        for pattern in ev_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                ev_findings[pattern] = matches
        
        return {
            'probability_fields': findings,
            'ev_calculations': ev_findings,
            'full_content': content
        }
    
    except Exception as e:
        print(f"  {RED}❌ Error reading scanner: {e}{RESET}")
        return {}

def probability_scale_audit():
    """Main probability scale audit."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 PROBABILITY SCALE AUDIT")
    print(f"{'='*80}{RESET}")
    
    print(f"\n{CYAN}Goal:{RESET}")
    print(f"  Verify all probability fields use the same scale")
    
    print(f"\n{CYAN}Checking:{RESET}")
    print(f"  - model_probability")
    print(f"  - implied_probability")
    print(f"  - market_probability")
    print(f"  - bookmaker_probability")
    print(f"  - fair_probability")
    print(f"  - confidence_score")
    
    print(f"\n{CYAN}Investigating:{RESET}")
    print(f"  - Odd = 2.40")
    print(f"  - Book P = 4167% (should be 41.7%)")
    print(f"  - Double multiplication by 100")
    
    # Step 1: Analyze database schema
    schema_findings = analyze_database_schema()
    
    # Step 2: Analyze Supabase repository
    repo_findings = analyze_supabase_repository()
    
    # Step 3: Analyze SmartScanner
    scanner_findings = analyze_smart_scanner()
    
    # Step 4: Analyze API endpoints
    endpoint_findings = analyze_api_endpoints()
    
    # Step 5: Detailed analysis of the bookmaker probability issue
    print(f"\n{BOLD}🔍 DETAILED BOOKMAKER PROBABILITY ANALYSIS{RESET}")
    print(f"{'='*80}")
    
    if repo_findings.get('full_content'):
        repo_content = repo_findings['full_content']
        
        # Look for bookmaker probability calculation
        bookmaker_patterns = [
            (r'(\w*bookmaker.*probability\w*)\s*=\s*(.+)', 'assignment'),
            (r'(\w*implied.*probability\w*)\s*=\s*(.+)', 'assignment'),
            (r'1\s*/\s*(\w*odd\w*)', 'calculation'),
            (r'(\w*odd\w*)\s*.*\s*(\w*probability\w*)', 'relationship')
        ]
        
        print(f"\n{CYAN}Bookmaker Probability Calculations Found:{RESET}")
        
        for pattern, type_name in bookmaker_patterns:
            matches = re.findall(pattern, repo_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                print(f"\n{YELLOW}{type_name.upper()} PATTERNS:{RESET}")
                for match in matches:
                    if isinstance(match, tuple):
                        print(f"  {match[0]} = {match[1]}")
                    else:
                        print(f"  {match}")
        
        # Look for the specific error pattern
        print(f"\n{CYAN}Looking for Double Multiplication Error:{RESET}")
        
        error_patterns = [
            r'(1\s*/\s*\w*odd\w*)\s*\*\s*100\s*\*\s*100',
            r'(\w*probability\w*)\s*\*\s*100\s*\*\s*100',
            r'round\([^)]*\*\s*100\s*\*\s*100'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, repo_content, re.IGNORECASE)
            if matches:
                print(f"\n{RED}❌ DOUBLE MULTIPLICATION FOUND:{RESET}")
                for match in matches:
                    # Find line number
                    line_num = repo_content[:repo_content.find(match)].count('\n') + 1
                    print(f"  Line {line_num}: {match}")
                    
                    # Show context
                    line_start = repo_content.rfind('\n', 0, repo_content.find(match)) + 1
                    line_end = repo_content.find('\n', repo_content.find(match))
                    line = repo_content[line_start:line_end] if line_end != -1 else repo_content[line_start:]
                    print(f"  Full line: {line.strip()}")
    
    # Step 6: Analyze SmartScanner EV candidate creation
    if scanner_findings.get('full_content'):
        scanner_content = scanner_findings['full_content']
        
        print(f"\n{BOLD}🔍 SMARTSCANNER PROBABILITY ANALYSIS{RESET}")
        print(f"{'='*80}")
        
        # Look for EV candidate creation
        ev_pattern = r'_pick\s*=\s*\{([^}]+)\}'
        ev_matches = re.findall(ev_pattern, scanner_content)
        
        if ev_matches:
            print(f"\n{CYAN}EV Candidate Definitions Found:{RESET}")
            for i, match in enumerate(ev_matches[:3]):  # Show first 3
                print(f"\nEV Candidate {i+1}:")
                print(f"  {match[:200]}..." if len(match) > 200 else f"  {match}")
        
        # Look for probability scaling in EV candidates
        prob_scaling_patterns = [
            r'market_probability.*=.*round.*\*.*100',
            r'implied_probability.*=.*round.*\*.*100',
            r'probability.*normalize.*scale'
        ]
        
        for pattern in prob_scaling_patterns:
            matches = re.findall(pattern, scanner_content, re.IGNORECASE)
            if matches:
                print(f"\n{YELLOW}PROBABILITY SCALING FOUND:{RESET}")
                for match in matches:
                    line_num = scanner_content[:scanner_content.find(match)].count('\n') + 1
                    print(f"  Line {line_num}: {match}")
    
    # Step 7: Create summary table
    print(f"\n{BOLD}🔍 PROBABILITY FIELD ANALYSIS SUMMARY{RESET}")
    print(f"{'='*120}")
    
    header = f"{'Field':<20} {'Found In':<15} {'Scale Issue':<12} {'File Location':<50}"
    print(f"{header}")
    print(f"{'-'*120}")
    
    probability_fields = [
        'model_probability',
        'implied_probability', 
        'market_probability',
        'bookmaker_probability',
        'fair_probability',
        'confidence_score'
    ]
    
    for field in probability_fields:
        # Check where this field is found
        locations = []
        
        if scanner_findings.get('probability_fields', {}).get(field):
            locations.append('SmartScanner')
        
        if repo_findings.get('scaling_operations'):
            for op, matches in repo_findings['scaling_operations'].items():
                if any(field.lower() in match.lower() for match in matches):
                    locations.append('Repository')
        
        # Check for scaling issues
        scale_issue = 'UNKNOWN'
        
        if repo_findings.get('double_multiplication_errors'):
            if any(field.lower() in str(error).lower() for error in repo_findings['double_multiplication_errors']):
                scale_issue = 'DOUBLE_MULT'
        
        location_str = ', '.join(locations) if locations else 'NOT_FOUND'
        
        # Color coding
        field_colored = f"{CYAN}{field}{RESET}"
        location_colored = f"{GREEN}{location_str}{RESET}" if locations else f"{RED}{location_str}{RESET}"
        scale_colored = f"{RED}{scale_issue}{RESET}" if scale_issue != 'UNKNOWN' else f"{YELLOW}{scale_issue}{RESET}"
        
        print(f"{field_colored:<20} {len(locations):<15} {scale_colored:<12} {location_colored:<50}")
    
    # Step 8: Specific investigation of the 4167% issue
    print(f"\n{BOLD}🔍 INVESTIGATION: 4167% vs 41.7% ISSUE{RESET}")
    print(f"{'='*80}")
    
    print(f"\n{CYAN}Expected Calculation:{RESET}")
    print(f"  Odd = 2.40")
    print(f"  Bookmaker Probability = 1 / 2.40 = 0.4167")
    print(f"  Percentage = 0.4167 * 100 = 41.7%")
    
    print(f"\n{CYAN}Actual Result (4167%):{RESET}")
    print(f"  This suggests: 0.4167 * 100 * 100 = 4167")
    print(f"  Indicates double multiplication by 100")
    
    if repo_findings.get('double_multiplication_errors'):
        print(f"\n{RED}❌ CONFIRMED: Double multiplication error detected{RESET}")
        print(f"  Check repository file for patterns like:")
        print(f"    - probability * 100 * 100")
        print(f"    - (1/odd) * 100 * 100")
    else:
        print(f"\n{YELLOW}⚠️  Double multiplication not found in repository{RESET}")
        print(f"  Issue might be in frontend or another layer")
    
    # Step 9: Export findings
    print(f"\n{BOLD}🔍 EXPORTING FINDINGS{RESET}")
    print(f"{'='*60}")
    
    findings = {
        'schema_findings': schema_findings,
        'repository_findings': repo_findings,
        'scanner_findings': scanner_findings,
        'endpoint_findings': endpoint_findings
    }
    
    with open('probability_scale_audit_results.txt', 'w', encoding='utf-8') as f:
        f.write("PROBABILITY SCALE AUDIT RESULTS\n")
        f.write("="*50 + "\n\n")
        
        f.write("ISSUE INVESTIGATION: 4167% vs 41.7%\n")
        f.write("-"*40 + "\n")
        f.write("Expected: 1/2.40 = 0.4167 = 41.7%\n")
        f.write("Actual: 4167% (indicates double multiplication)\n\n")
        
        if repo_findings.get('double_multiplication_errors'):
            f.write("CONFIRMED ERRORS:\n")
            for error in repo_findings['double_multiplication_errors']:
                f.write(f"  {error}\n")
        
        f.write("\nSCHEMA FINDINGS:\n")
        f.write("-"*20 + "\n")
        for field, types in schema_findings.items():
            f.write(f"{field}: {types}\n")
        
        f.write("\nREPOSITORY SCALING OPERATIONS:\n")
        f.write("-"*35 + "\n")
        for op, matches in repo_findings.get('scaling_operations', {}).items():
            f.write(f"{op}: {matches}\n")
    
    print(f"  Findings exported to: probability_scale_audit_results.txt")
    
    return len(repo_findings.get('double_multiplication_errors', [])) > 0

if __name__ == "__main__":
    success = probability_scale_audit()
    sys.exit(0 if success else 1)
