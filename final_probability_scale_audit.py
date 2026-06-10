#!/usr/bin/env python3
"""
final_probability_scale_audit.py
===============================
Final comprehensive probability scale audit.
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

def final_probability_scale_audit():
    """Final comprehensive probability scale audit."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 FINAL PROBABILITY SCALE AUDIT")
    print(f"{'='*80}{RESET}")
    
    print(f"\n{CYAN}Goal:{RESET}")
    print(f"  Verify all probability fields use the same scale")
    
    print(f"\n{CYAN}Fields to check:{RESET}")
    print(f"  - model_probability")
    print(f"  - implied_probability")
    print(f"  - market_probability")
    print(f"  - bookmaker_probability")
    print(f"  - fair_probability")
    print(f"  - confidence_score")
    
    print(f"\n{CYAN}Investigating:{RESET}")
    print(f"  - Odd = 2.40")
    print(f"  - Expected: 1/2.40 = 0.4167 = 41.7%")
    print(f"  - Actual: 4167% (double multiplication)")
    
    # Step 1: Analyze database schema
    print(f"\n{BOLD}🔍 STEP 1: DATABASE SCHEMA ANALYSIS{RESET}")
    print(f"{'='*80}")
    
    schema_file = 'app/database/schema.sql'
    if os.path.exists(schema_file):
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find probability columns
        prob_columns = re.findall(r'(\w*probability\w*)\s+(\w+)', content, re.IGNORECASE)
        
        print(f"\n{CYAN}Probability columns in schema:{RESET}")
        for col_name, col_type in prob_columns:
            print(f"  {col_name}: {col_type}")
        
        # Check predictions table specifically
        predictions_match = re.search(r'CREATE TABLE.*predictions.*?\((.*?)\);', content, re.DOTALL | re.IGNORECASE)
        if predictions_match:
            predictions_content = predictions_match.group(1)
            predictions_probs = re.findall(r'(\w*probability\w*)\s+\w+', predictions_content, re.IGNORECASE)
            print(f"\n{CYAN}Predictions table probability fields:{RESET}")
            for prob in predictions_probs:
                print(f"  {prob[0]}")
    
    # Step 2: Analyze backend probability handling
    print(f"\n{BOLD}🔍 STEP 2: BACKEND PROBABILITY HANDLING{RESET}")
    print(f"{'='*80}")
    
    backend_files = {
        'Repository': 'app/database/supabase_repository.py',
        'Scanner': 'app/services/scanner/smart_scanner.py'
    }
    
    backend_analysis = {}
    
    for name, file_path in backend_files.items():
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'file': file_path,
                'probability_fields': [],
                'scaling_operations': [],
                'normalization_logic': []
            }
            
            # Find probability field usage
            prob_fields = re.findall(r'(\w*probability\w*)', content, re.IGNORECASE)
            unique_fields = list(set([f for f in prob_fields if 'probability' in f.lower()]))
            analysis['probability_fields'] = unique_fields
            
            # Find scaling operations
            scaling_patterns = [
                (r'\w*probability\w*\s*\*\s*100', 'multiply_by_100'),
                (r'\w*probability\w*\s*/\s*100', 'divide_by_100'),
                (r'100\s*\*\s*\w*probability\w*', '100_multiply'),
                (r'round.*probability.*\*.*100', 'round_multiply_100')
            ]
            
            for pattern, desc in scaling_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    analysis['scaling_operations'].append({
                        'pattern': desc,
                        'count': len(matches),
                        'examples': matches[:3]
                    })
            
            # Find normalization logic
            normalize_patterns = [
                (r'if.*probability.*>.*1\.0', 'normalize_gt_1'),
                (r'probability.*\/.*100', 'normalize_div_100'),
                (r'normalize.*probability', 'normalize_function')
            ]
            
            for pattern, desc in normalize_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    analysis['normalization_logic'].append({
                        'pattern': desc,
                        'count': len(matches)
                    })
            
            backend_analysis[name] = analysis
            
            print(f"\n{CYAN}{name}:{RESET}")
            print(f"  Probability fields: {len(unique_fields)}")
            print(f"  Scaling operations: {len(analysis['scaling_operations'])}")
            print(f"  Normalization logic: {len(analysis['normalization_logic'])}")
            
            # Show specific findings
            if analysis['scaling_operations']:
                print(f"  {YELLOW}Scaling operations found:{RESET}")
                for op in analysis['scaling_operations']:
                    print(f"    {op['pattern']}: {op['count']} times")
            
            if analysis['normalization_logic']:
                print(f"  {GREEN}Normalization logic found:{RESET}")
                for norm in analysis['normalization_logic']:
                    print(f"    {norm['pattern']}: {norm['count']} times")
    
    # Step 3: Analyze specific bookmaker probability calculation
    print(f"\n{BOLD}🔍 STEP 3: BOOKMAKER PROBABILITY CALCULATION{RESET}")
    print(f"{'='*80}")
    
    repo_file = 'app/database/supabase_repository.py'
    if os.path.exists(repo_file):
        with open(repo_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the specific calculation
        calc_patterns = [
            r'implied_prob\s*=\s*round\s*\(\s*1\.0\s*/\s*bookmaker_odd\s*,\s*4\s*\)',
            r'implied_prob\s*=\s*1\.0\s*/\s*bookmaker_odd',
            r'implied_probability\s*=\s*1\s*/\s*bookmaker_odd'
        ]
        
        calc_found = False
        for pattern in calc_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                calc_found = True
                print(f"\n{GREEN}✅ Found implied_probability calculation:{RESET}")
                for match in matches:
                    line_num = content[:content.find(match)].count('\n') + 1
                    print(f"  Line {line_num}: {match}")
                    
                    # Show context
                    lines = content.split('\n')
                    if line_num <= len(lines):
                        print(f"  Context: {lines[line_num-1].strip()}")
                break
        
        if not calc_found:
            print(f"\n{YELLOW}⚠️  No implied_probability calculation found{RESET}")
        
        # Check for any multiplication by 100 after this calculation
        lines = content.split('\n')
        implied_calc_line = None
        
        for i, line in enumerate(lines):
            if re.search(r'implied_prob\s*=.*1\.0\s*/\s*bookmaker_odd', line, re.IGNORECASE):
                implied_calc_line = i
                break
        
        if implied_calc_line is not None:
            print(f"\n{CYAN}Checking lines after implied_prob calculation:{RESET}")
            for i in range(implied_calc_line + 1, min(implied_calc_line + 10, len(lines))):
                line = lines[i]
                if re.search(r'implied_prob.*\*.*100', line, re.IGNORECASE):
                    print(f"  {RED}❌ Line {i+1}: {line.strip()}{RESET}")
                elif re.search(r'\*.*100', line):
                    print(f"  {YELLOW}⚠️  Line {i+1}: {line.strip()}{RESET}")
    
    # Step 4: Analyze frontend probability display
    print(f"\n{BOLD}🔍 STEP 4: FRONTEND PROBABILITY DISPLAY{RESET}")
    print(f"{'='*80}")
    
    template_files = [
        'templates/dashboard.html',
        'templates/dashboard_compact.html',
        'templates/dashboard_intelligence.html'
    ]
    
    frontend_analysis = {}
    
    for template_file in template_files:
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'file': template_file,
                'probability_displays': [],
                'percentage_conversions': []
            }
            
            # Find probability displays
            prob_display_patterns = [
                (r'(\w*probability\w*)', 'probability_field'),
                (r'confidence.*\*.*100', 'confidence_percent'),
                (r'hit_rate.*\*.*100', 'hit_rate_percent'),
                (r'variance_score.*\*.*100', 'variance_percent'),
                (r'stability_score.*\*.*100', 'stability_percent')
            ]
            
            for pattern, desc in prob_display_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    analysis['probability_displays'].append({
                        'pattern': desc,
                        'count': len(matches)
                    })
            
            # Find percentage conversions
            percent_patterns = [
                (r'\*.*100.*\%', 'multiply_to_percent'),
                (r'\.toFixed.*\%', 'format_percent')
            ]
            
            for pattern, desc in percent_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    analysis['percentage_conversions'].append({
                        'pattern': desc,
                        'count': len(matches)
                    })
            
            frontend_analysis[template_file] = analysis
            
            print(f"\n{CYAN}{template_file}:{RESET}")
            print(f"  Probability displays: {len(analysis['probability_displays'])}")
            print(f"  Percentage conversions: {len(analysis['percentage_conversions'])}")
            
            # Show specific patterns
            if analysis['percentage_conversions']:
                print(f"  {YELLOW}Percentage conversions:{RESET}")
                for conv in analysis['percentage_conversions']:
                    print(f"    {conv['pattern']}: {conv['count']} times")
    
    # Step 5: Check API endpoints for probability handling
    print(f"\n{BOLD}🔍 STEP 5: API ENDPOINTS PROBABILITY HANDLING{RESET}")
    print(f"{'='*80}")
    
    flask_file = 'app_flask.py'
    if os.path.exists(flask_file):
        with open(flask_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find API endpoints that return probabilities
        api_patterns = [
            (r'@app\.route\([\'"](/api/[^\'"]*)[\'"]\)', 'endpoint'),
            (r'(\w*probability\w*)', 'probability_field')
        ]
        
        endpoints = re.findall(api_patterns[0][0], content)
        api_endpoints_with_prob = []
        
        for endpoint in endpoints:
            # Find the function body
            func_pattern = rf'@app\.route\([\'"]{re.escape(endpoint)}[\'"][^)]*\)\s*\ndef\s+(\w+)'
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
                
                # Check for probability fields in this function
                prob_fields = re.findall(api_patterns[1][0], func_body, re.IGNORECASE)
                if prob_fields:
                    api_endpoints_with_prob.append({
                        'endpoint': endpoint,
                        'function': func_match.group(1),
                        'probability_fields': list(set(prob_fields))
                    })
        
        print(f"\n{CYAN}API endpoints with probability fields:{RESET}")
        for endpoint_info in api_endpoints_with_prob:
            print(f"  {endpoint_info['endpoint']} ({endpoint_info['function']})")
            print(f"    Fields: {', '.join(endpoint_info['probability_fields'])}")
    
    # Step 6: Create comprehensive analysis table
    print(f"\n{BOLD}🔍 STEP 6: COMPREHENSIVE ANALYSIS TABLE{RESET}")
    print(f"{'='*120}")
    
    header = f"{'Field':<20} {'Backend Scale':<15} {'API Scale':<12} {'Frontend Scale':<15} {'Issues':<20}"
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
        # Backend scale analysis
        backend_scale = '0-1'  # Default assumption based on repository normalization
        
        # Check if field is found in backend
        found_in_backend = False
        for name, analysis in backend_analysis.items():
            if field in analysis['probability_fields']:
                found_in_backend = True
                # Check for normalization logic
                if analysis['normalization_logic']:
                    backend_scale = '0-1 (normalized)'
                break
        
        # API scale (usually same as backend)
        api_scale = backend_scale if found_in_backend else 'NOT_FOUND'
        
        # Frontend scale (usually converted to percentage)
        frontend_scale = '0-100 (%)' if found_in_backend else 'NOT_FOUND'
        
        # Issues
        issues = []
        
        # Check for the specific 4167% issue
        if field == 'implied_probability':
            # Look for double multiplication patterns
            double_multiply_found = False
            for name, analysis in backend_analysis.items():
                for op in analysis['scaling_operations']:
                    if 'multiply' in op['pattern'].lower() and op['count'] > 1:
                        double_multiply_found = True
                        break
            
            if double_multiply_found:
                issues.append('DOUBLE_MULTIPLICATION')
            elif not found_in_backend:
                issues.append('MISSING_IN_BACKEND')
        
        if not found_in_backend:
            issues.append('NOT_FOUND')
        
        issues_str = ', '.join(issues) if issues else 'NONE'
        
        # Color coding
        field_colored = f"{CYAN}{field}{RESET}"
        backend_colored = f"{GREEN}{backend_scale}{RESET}" if found_in_backend else f"{RED}{backend_scale}{RESET}"
        api_colored = f"{GREEN}{api_scale}{RESET}" if found_in_backend else f"{RED}{api_scale}{RESET}"
        frontend_colored = f"{GREEN}{frontend_scale}{RESET}" if found_in_backend else f"{RED}{frontend_scale}{RESET}"
        issues_colored = f"{RED}{issues_str}{RESET}" if issues else f"{GREEN}{issues_str}{RESET}"
        
        print(f"{field_colored:<20} {backend_colored:<15} {api_colored:<12} {frontend_colored:<15} {issues_colored:<20}")
    
    # Step 7: Final verdict on the 4167% issue
    print(f"\n{BOLD}🔍 STEP 7: FINAL VERDICT ON 4167% ISSUE{RESET}")
    print(f"{'='*80}")
    
    print(f"\n{CYAN}Expected calculation:{RESET}")
    print(f"  1. Bookmaker odd = 2.40")
    print(f"  2. Implied probability = 1 / 2.40 = 0.4167")
    print(f"  3. Display percentage = 0.4167 * 100 = 41.7%")
    
    print(f"\n{CYAN}Actual result (4167%):{RESET}")
    print(f"  This suggests: 0.4167 * 100 * 100 = 4167")
    print(f"  Indicates double multiplication by 100")
    
    # Check if we found the double multiplication
    double_multiply_found = False
    for name, analysis in backend_analysis.items():
        for op in analysis['scaling_operations']:
            if 'multiply' in op['pattern'].lower() and op['count'] > 0:
                # Check if it's applied to implied_probability
                if 'implied' in str(op.get('examples', [])).lower():
                    double_multiply_found = True
                    break
    
    if double_multiply_found:
        print(f"\n{RED}❌ DOUBLE MULTIPLICATION CONFIRMED{RESET}")
        print(f"  Found in backend code")
        print(f"  Location: Backend scaling operations")
        print(f"  Fix needed: Remove extra multiplication by 100")
    else:
        print(f"\n{GREEN}✅ NO DOUBLE MULTIPLICATION FOUND IN BACKEND{RESET}")
        print(f"  The 4167% issue might be:")
        print(f"  1. Frontend JavaScript double multiplication")
        print(f"  2. Data transformation layer")
        print(f"  3. Visualization library")
        print(f"  4. Client-side formatting")
    
    # Step 8: Export comprehensive findings
    print(f"\n{BOLD}🔍 STEP 8: EXPORTING COMPREHENSIVE FINDINGS{RESET}")
    print(f"{'='*60}")
    
    findings = {
        'backend_analysis': backend_analysis,
        'frontend_analysis': frontend_analysis,
        'api_endpoints': api_endpoints_with_prob,
        'double_multiply_found': double_multiply_found
    }
    
    with open('final_probability_scale_audit.txt', 'w', encoding='utf-8') as f:
        f.write("FINAL PROBABILITY SCALE AUDIT REPORT\n")
        f.write("="*50 + "\n\n")
        
        f.write("4167% vs 41.7% Issue Investigation\n")
        f.write("-"*40 + "\n")
        f.write("Expected: 1/2.40 = 0.4167 = 41.7%\n")
        f.write("Actual: 4167% (double multiplication)\n\n")
        
        f.write(f"Double multiplication found in backend: {double_multiply_found}\n\n")
        
        f.write("Backend Analysis:\n")
        f.write("-"*20 + "\n")
        for name, analysis in backend_analysis.items():
            f.write(f"{name}:\n")
            f.write(f"  Probability fields: {analysis['probability_fields']}\n")
            f.write(f"  Scaling operations: {len(analysis['scaling_operations'])}\n")
            f.write(f"  Normalization logic: {len(analysis['normalization_logic'])}\n")
            f.write("\n")
        
        f.write("Frontend Analysis:\n")
        f.write("-"*20 + "\n")
        for template, analysis in frontend_analysis.items():
            f.write(f"{template}:\n")
            f.write(f"  Probability displays: {len(analysis['probability_displays'])}\n")
            f.write(f"  Percentage conversions: {len(analysis['percentage_conversions'])}\n")
            f.write("\n")
        
        f.write("API Endpoints with Probabilities:\n")
        f.write("-"*35 + "\n")
        for endpoint in api_endpoints_with_prob:
            f.write(f"{endpoint['endpoint']}: {endpoint['probability_fields']}\n")
    
    print(f"  Findings exported to: final_probability_scale_audit.txt")
    
    return not double_multiply_found  # Return True if no issues found

if __name__ == "__main__":
    success = final_probability_scale_audit()
    sys.exit(0 if success else 1)
