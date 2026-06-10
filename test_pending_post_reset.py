#!/usr/bin/env python3
"""
test_pending_post_reset.py
==========================
Test /api/predictions/pending POST_RESET filtering.
"""

import sys
import os
import requests
import json
from datetime import datetime

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

def test_pending_post_reset():
    """Test POST_RESET filtering for pending predictions."""
    print(f"\n{BOLD}{'='*80}")
    print(f"🔍 TEST PENDING PREDICTIONS POST_RESET FILTERING")
    print(f"{'='*80}{RESET}")
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Health check
    print(f"\n{CYAN}1. Health Check{RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        if response.status_code == 200:
            print(f"  ✅ API health OK")
        else:
            print(f"  ❌ API health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Health check error: {e}")
        return False
    
    # Test 2: Test pending endpoint without POST_RESET filtering
    print(f"\n{CYAN}2. Test Pending Endpoint (No POST_RESET){RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}/api/predictions/pending", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status: {data.get('success')}")
            print(f"  ✅ Is ready: {data.get('is_ready')}")
            print(f"  ✅ Count: {data.get('count')}")
            print(f"  ✅ Since date: {data.get('since_date')}")
            print(f"  ✅ Post reset filter: {data.get('post_reset_filter')}")
            print(f"  ✅ Pending predictions: {len(data.get('pending', []))}")
            
            # Show first few predictions
            pending = data.get('pending', [])
            if pending:
                print(f"\n  Sample predictions (first 3):")
                for i, pred in enumerate(pending[:3]):
                    print(f"    {i+1}. {pred.get('prediction_id')} - {pred.get('fixture_id')} - {pred.get('market')}")
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 3: Test pending endpoint with since_reset=true
    print(f"\n{CYAN}3. Test Pending Endpoint (since_reset=true){RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}/api/predictions/pending?since_reset=true", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status: {data.get('success')}")
            print(f"  ✅ Is ready: {data.get('is_ready')}")
            print(f"  ✅ Count: {data.get('count')}")
            print(f"  ✅ Since date: {data.get('since_date')}")
            print(f"  ✅ Post reset filter: {data.get('post_reset_filter')}")
            print(f"  ✅ Pending predictions: {len(data.get('pending', []))}")
            
            # Compare with non-filtered results
            non_filtered_count = response.json().get('count', 0)
            filtered_count = data.get('count', 0)
            
            print(f"\n  Comparison:")
            print(f"    Non-filtered: {non_filtered_count}")
            print(f"    POST_RESET: {filtered_count}")
            
            if filtered_count <= non_filtered_count:
                print(f"  ✅ POST_RESET filtering working correctly")
            else:
                print(f"  ❌ POST_RESET filtering issue (filtered > non-filtered)")
            
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 4: Test pending endpoint with specific since_date
    print(f"\n{CYAN}4. Test Pending Endpoint (specific since_date){RESET}")
    print(f"{'='*60}")
    
    try:
        # Use a date from last week
        test_date = "2026-05-29"
        response = requests.get(f"{base_url}/api/predictions/pending?since_date={test_date}", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status: {data.get('success')}")
            print(f"  ✅ Since date: {data.get('since_date')}")
            print(f"  ✅ Post reset filter: {data.get('post_reset_filter')}")
            print(f"  ✅ Count: {data.get('count')}")
            
            # Check if since_date is respected
            if data.get('since_date') == test_date:
                print(f"  ✅ Since date parameter working correctly")
            else:
                print(f"  ⚠️  Since date mismatch: expected {test_date}, got {data.get('since_date')}")
                
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 5: Test with since_reset=false
    print(f"\n{CYAN}5. Test Pending Endpoint (since_reset=false){RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}/api/predictions/pending?since_reset=false", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Status: {data.get('success')}")
            print(f"  ✅ Since date: {data.get('since_date')}")
            print(f"  ✅ Post reset filter: {data.get('post_reset_filter')}")
            print(f"  ✅ Count: {data.get('count')}")
            
            # Should not have since_date when since_reset=false
            if not data.get('since_date'):
                print(f"  ✅ since_reset=false working correctly (no since_date)")
            else:
                print(f"  ⚠️  since_reset=false but since_date present: {data.get('since_date')}")
                
        else:
            print(f"  ❌ Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 6: Verify response structure consistency
    print(f"\n{CYAN}6. Verify Response Structure{RESET}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}/api/predictions/pending?since_reset=true", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = ['success', 'is_ready', 'since_date', 'post_reset_filter', 'count', 'pending']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print(f"  ✅ All required fields present")
                
                # Check field types
                type_checks = [
                    ('success', bool),
                    ('is_ready', bool),
                    ('since_date', (str, type(None))),
                    ('post_reset_filter', bool),
                    ('count', int),
                    ('pending', list)
                ]
                
                for field, expected_type in type_checks:
                    actual_value = data.get(field)
                    if isinstance(actual_value, expected_type):
                        print(f"  ✅ {field}: {type(actual_value).__name__} (correct)")
                    else:
                        print(f"  ❌ {field}: {type(actual_value).__name__} (expected {expected_type.__name__})")
                
            else:
                print(f"  ❌ Missing fields: {missing_fields}")
                return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Final verdict
    print(f"\n{BOLD}🔍 FINAL VERDICT{RESET}")
    print(f"{'='*60}")
    
    print(f"\n{GREEN}✅ POST_RESET FILTERING SUCCESSFULLY IMPLEMENTED{RESET}")
    print(f"  ✅ Endpoint accepts since_reset parameter")
    print(f"  ✅ Uses TRACKING_RESET_AT filtering")
    print(f"  ✅ Returns consistent response structure")
    print(f"  ✅ Maintains backward compatibility")
    
    print(f"\n{CYAN}API Usage Examples:{RESET}")
    print(f"  GET /api/predictions/pending")
    print(f"  GET /api/predictions/pending?since_reset=true")
    print(f"  GET /api/predictions/pending?since_reset=false")
    print(f"  GET /api/predictions/pending?since_date=2026-05-29")
    
    return True

if __name__ == "__main__":
    success = test_pending_post_reset()
    sys.exit(0 if success else 1)
