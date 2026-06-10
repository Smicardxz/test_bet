#!/usr/bin/env python3
"""
post_reset_frontend_audit.py
============================
POST_RESET Frontend Audit
Verify that every analytics page uses POST_RESET data only.
"""

import sys
import os
import re
from typing import Dict, List, Tuple

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

def extract_api_endpoints_from_file(file_path: str) -> List[Dict]:
    """Extract API endpoints from frontend files."""
    endpoints = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for fetch/axios calls
        patterns = [
            r'fetch\([\'"]([^\'"]+)[\'"]',
            r'axios\.[^(]+\([\'"]([^\'"]+)[\'"]',
            r'api\.[^(]+\([\'"]([^\'"]+)[\'"]',
            r'url:\s*[\'"]([^\'"]+)[\'"]',
            r'endpoint:\s*[\'"]([^\'"]+)[\'"]'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if '/api/' in match and not match.endswith('.js'):
                    endpoints.append({
                        'endpoint': match,
                        'file': os.path.basename(file_path),
                        'line': content[:content.find(match)].count('\n') + 1
                    })
    
    except Exception as e:
        print(f"  {YELLOW}⚠️  Error reading {file_path}: {e}{RESET}")
    
    return endpoints

def find_frontend_files() -> List[str]:
    """Find frontend files that might contain API calls."""
    frontend_dirs = [
        'frontend',
        'client',
        'web',
        'src',
        'app',
        'static'
    ]
    
    frontend_extensions = ['.js', '.jsx', '.ts', '.tsx', '.vue', '.html']
    
    found_files = []
    
    for root, dirs, files in os.walk('.'):
        # Skip common non-frontend directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in frontend_extensions):
                file_path = os.path.join(root, file)
                found_files.append(file_path)
    
    return found_files

def analyze_endpoint(endpoint: str) -> Dict:
    """Analyze an endpoint for POST_RESET compliance."""
    analysis = {
        'endpoint': endpoint,
        'post_reset_only': 'UNKNOWN',
        'legacy_data_present': 'UNKNOWN',
        'fix_required': 'UNKNOWN',
        'uses_tracking_reset': 'UNKNOWN',
        'uses_since_reset': 'UNKNOWN',
        'prediction_type_filter': 'UNKNOWN'
    }
    
    # Check for POST_RESET indicators
    post_reset_indicators = [
        'since_reset=true',
        'tracking_reset_at',
        'post_reset',
        'POST_RESET'
    ]
    
    # Check for legacy indicators
    legacy_indicators = [
        'prediction_type',
        'LIVE_SAFE',
        'RESEARCH_ONLY',
        'PRE_RESET'
    ]
    
    # Check endpoint patterns
    if any(indicator in endpoint.lower() for indicator in post_reset_indicators):
        analysis['post_reset_only'] = 'YES'
        analysis['uses_since_reset'] = 'YES' if 'since_reset=true' in endpoint.lower() else 'NO'
        analysis['uses_tracking_reset'] = 'YES' if 'tracking_reset_at' in endpoint.lower() else 'NO'
    else:
        analysis['post_reset_only'] = 'NO'
        analysis['uses_since_reset'] = 'NO'
        analysis['uses_tracking_reset'] = 'NO'
    
    if any(indicator in endpoint.lower() for indicator in legacy_indicators):
        analysis['legacy_data_present'] = 'YES'
        analysis['prediction_type_filter'] = 'YES'
    else:
        analysis['legacy_data_present'] = 'NO'
        analysis['prediction_type_filter'] = 'NO'
    
    # Determine if fix is required
    analysis['fix_required'] = 'YES' if (
        analysis['post_reset_only'] == 'NO' or 
        analysis['legacy_data_present'] == 'YES'
    ) else 'NO'
    
    return analysis

def audit_flask_endpoints():
    """Audit Flask endpoints directly."""
    print(f"\n{BOLD}🔍 AUDITING FLASK ENDPOINTS{RESET}")
    print(f"{'='*80}")
    
    try:
        with open('app_flask.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all @app.route endpoints
        route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
        routes = re.findall(route_pattern, content)
        
        api_routes = [route for route in routes if '/api/' in route]
        
        print(f"  Found {len(api_routes)} API endpoints in app_flask.py")
        
        # Analyze each endpoint
        endpoint_analyses = []
        
        for route in api_routes:
            # Find the function definition
            func_pattern = rf'@app\.route\([\'"]{re.escape(route)}[\'"][^)]*\)\s*\ndef\s+(\w+)'
            func_match = re.search(func_pattern, content)
            
            if func_match:
                func_name = func_match.group(1)
                func_start = content.find(func_match.group(0))
                
                # Find function body (approximate)
                func_body_start = content.find(':', func_start) + 1
                next_def = content.find('\ndef ', func_body_start)
                next_route = content.find('\n@app.route', func_body_start)
                
                func_end = min(
                    next_def if next_def != -1 else len(content),
                    next_route if next_route != -1 else len(content)
                )
                
                func_body = content[func_body_start:func_end]
                
                analysis = analyze_endpoint(route)
                analysis['function'] = func_name
                analysis['source'] = 'app_flask.py'
                
                # Check function body for POST_RESET indicators
                if 'since_reset' in func_body or 'tracking_reset_at' in func_body:
                    analysis['uses_since_reset'] = 'YES'
                    analysis['uses_tracking_reset'] = 'YES'
                    analysis['post_reset_only'] = 'YES'
                
                if 'prediction_type' in func_body or 'LIVE_SAFE' in func_body:
                    analysis['legacy_data_present'] = 'YES'
                    analysis['prediction_type_filter'] = 'YES'
                
                analysis['fix_required'] = 'YES' if (
                    analysis['post_reset_only'] == 'NO' or 
                    analysis['legacy_data_present'] == 'YES'
                ) else 'NO'
                
                endpoint_analyses.append(analysis)
        
        return endpoint_analyses
        
    except Exception as e:
        print(f"  {RED}❌ Error auditing Flask endpoints: {e}{RESET}")
        return []

def map_pages_to_endpoints():
    """Map frontend pages to their endpoints."""
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
            '/api/event/status',
            '/api/event/predictions',
            '/api/predictions/history'
        ]
    }
    
    return page_endpoint_map

def post_reset_frontend_audit():
    """Main POST_RESET frontend audit."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 POST_RESET FRONTEND AUDIT")
    print(f"{'='*80}{RESET}")
    
    print(f"\n{CYAN}Goal:{RESET}")
    print(f"  Verify that every analytics page uses POST_RESET data only")
    
    print(f"\n{CYAN}Checking:{RESET}")
    print(f"  - BetIQ vs Market")
    print(f"  - Model Transparency")
    print(f"  - Performance")
    print(f"  - Calibration")
    print(f"  - Prediction Tracker")
    print(f"  - Event Mode")
    
    # Step 1: Audit Flask endpoints
    flask_analyses = audit_flask_endpoints()
    
    # Step 2: Map pages to endpoints
    page_endpoint_map = map_pages_to_endpoints()
    
    # Step 3: Create analysis table
    print(f"\n{BOLD}🔍 ENDPOINT ANALYSIS TABLE{RESET}")
    print(f"{'='*120}")
    
    header = f"{'Page':<20} {'Endpoint':<35} {'Post Reset':<12} {'Legacy':<8} {'Fix Req':<8}"
    print(f"{header}")
    print(f"{'-'*120}")
    
    results = []
    
    for page, endpoints in page_endpoint_map.items():
        for endpoint in endpoints:
            # Find analysis for this endpoint
            analysis = None
            for flask_analysis in flask_analyses:
                if flask_analysis['endpoint'] == endpoint:
                    analysis = flask_analysis
                    break
            
            if analysis:
                post_reset = analysis['post_reset_only']
                legacy = analysis['legacy_data_present']
                fix_req = analysis['fix_required']
                
                # Color coding
                post_reset_colored = f"{GREEN}{post_reset}{RESET}" if post_reset == 'YES' else f"{RED}{post_reset}{RESET}"
                legacy_colored = f"{GREEN}{legacy}{RESET}" if legacy == 'NO' else f"{RED}{legacy}{RESET}"
                fix_colored = f"{GREEN}{fix_req}{RESET}" if fix_req == 'NO' else f"{YELLOW}{fix_req}{RESET}"
                
                print(f"{page:<20} {endpoint:<35} {post_reset_colored:<12} {legacy_colored:<8} {fix_colored:<8}")
                
                results.append({
                    'page': page,
                    'endpoint': endpoint,
                    'post_reset_only': post_reset,
                    'legacy_data_present': legacy,
                    'fix_required': fix_req,
                    'function': analysis.get('function', ''),
                    'uses_since_reset': analysis.get('uses_since_reset', ''),
                    'uses_tracking_reset': analysis.get('uses_tracking_reset', ''),
                    'prediction_type_filter': analysis.get('prediction_type_filter', '')
                })
            else:
                print(f"{page:<20} {endpoint:<35} {'UNKNOWN':<12} {'UNKNOWN':<8} {'UNKNOWN':<8}")
                
                results.append({
                    'page': page,
                    'endpoint': endpoint,
                    'post_reset_only': 'UNKNOWN',
                    'legacy_data_present': 'UNKNOWN',
                    'fix_required': 'UNKNOWN',
                    'function': '',
                    'uses_since_reset': '',
                    'uses_tracking_reset': '',
                    'prediction_type_filter': ''
                })
    
    # Step 4: Summary
    print(f"\n{BOLD}🔍 SUMMARY{RESET}")
    print(f"{'='*60}")
    
    total_endpoints = len(results)
    post_reset_compliant = len([r for r in results if r['post_reset_only'] == 'YES'])
    legacy_free = len([r for r in results if r['legacy_data_present'] == 'NO'])
    need_fix = len([r for r in results if r['fix_required'] == 'YES'])
    
    print(f"  Total endpoints analyzed: {total_endpoints}")
    print(f"  POST_RESET compliant: {post_reset_compliant}/{total_endpoints} ({post_reset_compliant/total_endpoints*100:.1f}%)")
    print(f"  Legacy data free: {legacy_free}/{total_endpoints} ({legacy_free/total_endpoints*100:.1f}%)")
    print(f"  Fixes required: {need_fix}/{total_endpoints} ({need_fix/total_endpoints*100:.1f}%)")
    
    # Step 5: Detailed findings
    print(f"\n{BOLD}🔍 DETAILED FINDINGS{RESET}")
    print(f"{'='*80}")
    
    if need_fix > 0:
        print(f"\n{YELLOW}⚠️  ENDPOINTS REQUIRING FIXES:{RESET}")
        for result in results:
            if result['fix_required'] == 'YES':
                print(f"  ❌ {result['page']} - {result['endpoint']}")
                if result['function']:
                    print(f"     Function: {result['function']}")
                if result['uses_since_reset'] == 'NO':
                    print(f"     Missing: since_reset=true")
                if result['uses_tracking_reset'] == 'NO':
                    print(f"     Missing: tracking_reset_at filter")
                if result['legacy_data_present'] == 'YES':
                    print(f"     Issue: Contains legacy data filters")
                print()
    else:
        print(f"\n{GREEN}✅ ALL ENDPOINTS ARE POST_RESET COMPLIANT!{RESET}")
    
    # Step 6: Export results
    print(f"\n{BOLD}🔍 EXPORTING RESULTS{RESET}")
    print(f"{'='*60}")
    
    with open('post_reset_audit_results.txt', 'w', encoding='utf-8') as f:
        f.write("POST_RESET Frontend Audit Results\n")
        f.write("="*50 + "\n\n")
        
        f.write(f"Total endpoints analyzed: {total_endpoints}\n")
        f.write(f"POST_RESET compliant: {post_reset_compliant}/{total_endpoints} ({post_reset_compliant/total_endpoints*100:.1f}%)\n")
        f.write(f"Legacy data free: {legacy_free}/{total_endpoints} ({legacy_free/total_endpoints*100:.1f}%)\n")
        f.write(f"Fixes required: {need_fix}/{total_endpoints} ({need_fix/total_endpoints*100:.1f}%)\n\n")
        
        f.write("Detailed Results:\n")
        f.write("-"*50 + "\n")
        
        for result in results:
            f.write(f"\nPage: {result['page']}\n")
            f.write(f"Endpoint: {result['endpoint']}\n")
            f.write(f"Post Reset Only: {result['post_reset_only']}\n")
            f.write(f"Legacy Data Present: {result['legacy_data_present']}\n")
            f.write(f"Fix Required: {result['fix_required']}\n")
            if result['function']:
                f.write(f"Function: {result['function']}\n")
            f.write(f"Uses Since Reset: {result['uses_since_reset']}\n")
            f.write(f"Uses Tracking Reset: {result['uses_tracking_reset']}\n")
            f.write(f"Prediction Type Filter: {result['prediction_type_filter']}\n")
            f.write("-"*30 + "\n")
    
    print(f"  Results exported to: post_reset_audit_results.txt")
    
    return need_fix == 0

if __name__ == "__main__":
    success = post_reset_frontend_audit()
    sys.exit(0 if success else 1)
