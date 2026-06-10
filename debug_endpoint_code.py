#!/usr/bin/env python3
"""
debug_endpoint_code.py
==================
Debug if the endpoint code was actually updated.
"""

import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def debug_endpoint_code():
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
            print(f"\n{CYAN}Function code:{RESET}")
            print(f"{'-'*60}")
            print(function_code)
            
            # Check for specific patterns
            checks = [
                ('_parse_reset_at', 'Import check'),
                ('since_reset', 'since_reset parameter'),
                ('since_date', 'since_date parameter'),
                ('TRACKING_RESET_AT', 'environment variable'),
                ('get_pending_predictions', 'repository call')
            ]
            
            print(f"\n{CYAN}Code Analysis:{RESET}")
            print(f"{'-'*60}")
            
            for check_name, check_desc in checks:
                if check_name in function_code:
                    print(f"  ✅ {check_desc}: Found")
                else:
                    print(f"  ❌ {check_desc}: NOT FOUND")
            
            # Check the exact logic
            if 'elif not since_reset:' in function_code:
                print(f"  ✅ Found 'elif not since_reset' logic")
                
                # Find the since_date handling in this block
                since_reset_block = re.search(r'elif not since_reset:(.*?)(?=\n    @|\n    def|\Z)', content, re.DOTALL)
                if since_reset_block:
                    block_content = since_reset_block.group(1)
                    print(f"\n{CYAN}since_reset=false block:{RESET}")
                    print(f"{'-'*60}")
                    print(block_content[:200])
                    
                    if 'since_date' in block_content:
                        print(f"  ✅ since_date handling found in block")
                    else:
                        print(f"  ❌ since_date handling NOT found in block")
            
            return True
        else:
            print(f"❌ Could not find api_predictions_pending function")
            return False
    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    success = debug_endpoint_code()
    sys.exit(0 if success else 1)
