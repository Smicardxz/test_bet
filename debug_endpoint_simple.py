#!/usr/bin/env python3
"""
debug_endpoint_simple.py
==================
Simple debug of the endpoint code.
"""

import sys
import os
import re

def debug_endpoint_simple():
    """Debug if the endpoint code was updated."""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG ENDPOINT CODE")
    print(f"{'='*80}")
    
    flask_file = 'app_flask.py'
    
    try:
        with open(flask_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the api_predictions_pending function
        pattern = r'@app\.route\("/api/predictions/pending"\)\s*\ndef\s+api_predictions_pending\(\):(.*?)\n(?=@app\.route|\ndef\s+\w+|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        
        if match:
            function_code = match.group(1)
            print(f"✅ Found api_predictions_pending function")
            print(f"\nFunction code:")
            print(f"{'-'*60}")
            print(function_code)
            
            # Check for specific patterns
            checks = [
                ('_parse_reset_at', 'Import check'),
                ('since_reset', 'since_reset parameter'),
                ('since_date', 'since_date parameter'),
                ('TRACKING_RESET_AT', 'environment variable'),
                ('get_pending_predictions', 'repository call'),
                ('elif not since_reset', 'elif not since_reset logic')
            ]
            
            print(f"\nCode Analysis:")
            print(f"{'-'*60}")
            
            for check_name, check_desc in checks:
                if check_name in function_code:
                    print(f"  ✅ {check_desc}: Found")
                else:
                    print(f"  ❌ {check_desc}: NOT FOUND")
            
            return True
        else:
            print(f"❌ Could not find api_predictions_pending function")
            return False
    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    success = debug_endpoint_simple()
    sys.exit(0 if success else 1)
