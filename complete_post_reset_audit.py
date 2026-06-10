#!/usr/bin/env python3
"""
complete_post_reset_audit.py
============================
Complete POST_RESET Frontend Audit with actual endpoint analysis.
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

def analyze_endpoint_function(endpoint: str, function_name: str, func_body: str) -> dict:
    """Analyze a specific endpoint function for POST_RESET compliance."""
    analysis = {
        'endpoint': endpoint,
        'function': function_name,
        'post_reset_only': 'NO',
        'legacy_data_present': 'NO',
        'fix_required': 'NO',
        'uses_tracking_reset': 'NO',
        'uses_since_reset': 'NO',
        'prediction_type_filter': 'NO',
        'uses_live_safe_only': 'NO',
        'uses_all_predictions': 'NO'
    }
    
    # Check for POST_RESET indicators
    if 'since_reset' in func_body:
        analysis['uses_since_reset'] = 'YES'
        analysis['post_reset_only'] = 'YES'
    
    if 'tracking_reset_at' in func_body:
        analysis['uses_tracking_reset'] = 'YES'
        analysis['post_reset_only'] = 'YES'
    
    # Check for legacy indicators
    if 'prediction_type' in func_body:
        analysis['prediction_type_filter'] = 'YES'
        analysis['legacy_data_present'] = 'YES'
    
    if 'LIVE_SAFE' in func_body:
        analysis['uses_live_safe_only'] = 'YES'
        analysis['legacy_data_present'] = 'YES'
    
    # Check if it mixes data types
    if 'get_pending_predictions' in func_body:
        analysis['uses_all_predictions'] = 'YES'
        # This endpoint might need since_reset filtering
    
    # Determine if fix is required
    analysis['fix_required'] = 'YES' if (
        analysis['post_reset_only'] == 'NO' and 
        (endpoint.startswith('/api/performance/') or 
         endpoint.startswith('/api/predictions/') or
         endpoint.startswith('/api/calibration/') or
         endpoint.startswith('/api/event/'))
    ) else 'NO'
    
    return analysis

def complete_audit():
    """Complete POST_RESET audit with actual endpoint analysis."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 COMPLETE POST_RESET FRONTEND AUDIT")
    print(f"{'='*80}{RESET}")
    
    # Read Flask file
    try:
        with open('app_flask.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  {RED}❌ Error reading app_flask.py: {e}{RESET}")
        return False
    
    # Find all API endpoints
    route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
    routes = re.findall(route_pattern, content)
    
    api_routes = [route for route in routes if '/api/' in route]
    print(f"  Found {len(api_routes)} API endpoints")
    
    # Page to endpoint mapping
    page_endpoint_map = {
        'BetIQ vs Market': [
            '/api/performance/summary',
            '/api/performance/by-market', 
            '/api/performance/by-league',
            '/api/predictions/history'
        ],
        'Model Transparency': [
            '/api/model/transparency',
            '/api/predictions/history',
            '/api/performance/summary'
        ],
        'Performance': [
            '/api/performance/summary',
            '/api/performance/by-league',
            '/api/performance/by-market',
            '/api/performance/by-tier'
        ],
        'Calibration': [
            '/api/calibration/metrics',
            '/api/calibration/by-probability',
            '/api/predictions/history'
        ],
        'Prediction Tracker': [
            '/api/predictions/history',
            '/api/predictions/pending',
            '/api/predictions/by-date'
        ],
        'Event Mode': [
            '/api/event-mode',
            '/api/event/predictions',
            '/api/predictions/history'
        ]
    }
    
    # Analyze each relevant endpoint
    results = []
    
    for page, endpoints in page_endpoint_map.items():
        for endpoint in endpoints:
            # Find the function for this endpoint
            func_pattern = rf'@app\.route\([\'"]{re.escape(endpoint)}[\'"][^)]*\)\s*\ndef\s+(\w+)'
            func_match = re.search(func_pattern, content)
            
            if func_match:
                func_name = func_match.group(1)
                
                # Extract function body
                func_start = content.find(func_match.group(0))
                func_body_start = content.find(':', func_start) + 1
                
                # Find next function or route
                next_pattern = r'\n(?:@app\.route|def |\nclass |$)'
                next_match = re.search(next_pattern, content[func_body_start:])
                
                if next_match:
                    func_body = content[func_body_start:func_body_start + next_match.start()]
                else:
                    func_body = content[func_body_start:]
                
                # Analyze the function
                analysis = analyze_endpoint_function(endpoint, func_name, func_body)
                analysis['page'] = page
                results.append(analysis)
            else:
                # Endpoint not found
                results.append({
                    'page': page,
                    'endpoint': endpoint,
                    'function': 'NOT_FOUND',
                    'post_reset_only': 'UNKNOWN',
                    'legacy_data_present': 'UNKNOWN',
                    'fix_required': 'UNKNOWN',
                    'uses_tracking_reset': 'UNKNOWN',
                    'uses_since_reset': 'UNKNOWN',
                    'prediction_type_filter': 'UNKNOWN',
                    'uses_live_safe_only': 'UNKNOWN',
                    'uses_all_predictions': 'UNKNOWN'
                })
    
    # Display results table
    print(f"\n{BOLD}🔍 ENDPOINT ANALYSIS TABLE{RESET}")
    print(f"{'='*140}")
    
    header = f"{'Page':<20} {'Endpoint':<30} {'Function':<25} {'Post Reset':<12} {'Legacy':<8} {'Fix Req':<8}"
    print(f"{header}")
    print(f"{'-'*140}")
    
    for result in results:
        page = result['page']
        endpoint = result['endpoint']
        func = result['function']
        post_reset = result['post_reset_only']
        legacy = result['legacy_data_present']
        fix_req = result['fix_required']
        
        # Color coding
        post_reset_colored = f"{GREEN}{post_reset}{RESET}" if post_reset == 'YES' else f"{RED}{post_reset}{RESET}"
        legacy_colored = f"{GREEN}{legacy}{RESET}" if legacy == 'NO' else f"{RED}{legacy}{RESET}"
        fix_colored = f"{GREEN}{fix_req}{RESET}" if fix_req == 'NO' else f"{YELLOW}{fix_req}{RESET}"
        
        print(f"{page:<20} {endpoint:<30} {func:<25} {post_reset_colored:<12} {legacy_colored:<8} {fix_colored:<8}")
    
    # Summary
    print(f"\n{BOLD}🔍 SUMMARY{RESET}")
    print(f"{'='*60}")
    
    total_endpoints = len(results)
    known_endpoints = len([r for r in results if r['function'] != 'NOT_FOUND'])
    post_reset_compliant = len([r for r in results if r['post_reset_only'] == 'YES'])
    legacy_free = len([r for r in results if r['legacy_data_present'] == 'NO'])
    need_fix = len([r for r in results if r['fix_required'] == 'YES'])
    
    print(f"  Total endpoints analyzed: {total_endpoints}")
    print(f"  Endpoints found in code: {known_endpoints}/{total_endpoints}")
    print(f"  POST_RESET compliant: {post_reset_compliant}/{known_endpoints} ({post_reset_compliant/known_endpoints*100:.1f}%)" if known_endpoints > 0 else "  POST_RESET compliant: N/A")
    print(f"  Legacy data free: {legacy_free}/{known_endpoints} ({legacy_free/known_endpoints*100:.1f}%)" if known_endpoints > 0 else "  Legacy data free: N/A")
    print(f"  Fixes required: {need_fix}/{known_endpoints} ({need_fix/known_endpoints*100:.1f}%)" if known_endpoints > 0 else "  Fixes required: N/A")
    
    # Detailed findings
    print(f"\n{BOLD}🔍 DETAILED FINDINGS{RESET}")
    print(f"{'='*80}")
    
    # Missing endpoints
    missing_endpoints = [r for r in results if r['function'] == 'NOT_FOUND']
    if missing_endpoints:
        print(f"\n{YELLOW}⚠️  MISSING ENDPOINTS:{RESET}")
        for result in missing_endpoints:
            print(f"  ❌ {result['page']} - {result['endpoint']} (NOT FOUND)")
    
    # Endpoints requiring fixes
    fix_required_endpoints = [r for r in results if r['fix_required'] == 'YES']
    if fix_required_endpoints:
        print(f"\n{YELLOW}⚠️  ENDPOINTS REQUIRING FIXES:{RESET}")
        for result in fix_required_endpoints:
            print(f"  ❌ {result['page']} - {result['endpoint']}")
            print(f"     Function: {result['function']}")
            if result['uses_since_reset'] == 'NO':
                print(f"     Missing: since_reset=true parameter")
            if result['uses_tracking_reset'] == 'NO':
                print(f"     Missing: tracking_reset_at filtering")
            if result['legacy_data_present'] == 'YES':
                print(f"     Issue: Contains legacy prediction_type filters")
            print()
    
    # Compliant endpoints
    compliant_endpoints = [r for r in results if r['fix_required'] == 'NO' and r['function'] != 'NOT_FOUND']
    if compliant_endpoints:
        print(f"\n{GREEN}✅ POST_RESET COMPLIANT ENDPOINTS:{RESET}")
        for result in compliant_endpoints:
            print(f"  ✅ {result['page']} - {result['endpoint']}")
            print(f"     Function: {result['function']}")
            if result['uses_since_reset'] == 'YES':
                print(f"     ✅ Uses since_reset filtering")
            if result['uses_tracking_reset'] == 'YES':
                print(f"     ✅ Uses tracking_reset_at filtering")
            print()
    
    # Export detailed results
    print(f"\n{BOLD}🔍 EXPORTING DETAILED RESULTS{RESET}")
    print(f"{'='*60}")
    
    with open('complete_post_reset_audit.txt', 'w', encoding='utf-8') as f:
        f.write("COMPLETE POST_RESET Frontend Audit Results\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"Total endpoints analyzed: {total_endpoints}\n")
        f.write(f"Endpoints found in code: {known_endpoints}/{total_endpoints}\n")
        if known_endpoints > 0:
            f.write(f"POST_RESET compliant: {post_reset_compliant}/{known_endpoints} ({post_reset_compliant/known_endpoints*100:.1f}%)\n")
            f.write(f"Legacy data free: {legacy_free}/{known_endpoints} ({legacy_free/known_endpoints*100:.1f}%)\n")
            f.write(f"Fixes required: {need_fix}/{known_endpoints} ({need_fix/known_endpoints*100:.1f}%)\n")
        
        f.write("\nDetailed Analysis:\n")
        f.write("-"*60 + "\n")
        
        for result in results:
            f.write(f"\nPage: {result['page']}\n")
            f.write(f"Endpoint: {result['endpoint']}\n")
            f.write(f"Function: {result['function']}\n")
            f.write(f"Post Reset Only: {result['post_reset_only']}\n")
            f.write(f"Legacy Data Present: {result['legacy_data_present']}\n")
            f.write(f"Fix Required: {result['fix_required']}\n")
            f.write(f"Uses Since Reset: {result['uses_since_reset']}\n")
            f.write(f"Uses Tracking Reset: {result['uses_tracking_reset']}\n")
            f.write(f"Prediction Type Filter: {result['prediction_type_filter']}\n")
            f.write(f"Uses LIVE_SAFE Only: {result['uses_live_safe_only']}\n")
            f.write(f"Uses All Predictions: {result['uses_all_predictions']}\n")
            f.write("-"*40 + "\n")
    
    print(f"  Results exported to: complete_post_reset_audit.txt")
    
    return len(fix_required_endpoints) == 0

if __name__ == "__main__":
    success = complete_audit()
    sys.exit(0 if success else 1)
