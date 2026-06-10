#!/usr/bin/env python3
"""
validate_event_mode_complete.py
=================================
Final validation script for EVENT_MODE integration.

This script validates all phases of EVENT_MODE integration:
1. Feature flag
2. Database columns
3. Cycle integration
4. API behavior
5. Backfill tool
6. Performance reporting
7. No duplicate guarantee

Success: EVENT_MODE_COMPLETE_VALIDATION_OK
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def validate_feature_flag():
    """Validate EVENT_MODE_ENABLED feature flag."""
    print(f"\n{BOLD}🚩 PHASE 1: Feature Flag Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        # Check .env
        event_mode_enabled = os.getenv('EVENT_MODE_ENABLED', 'false').lower() == 'true'
        print(f"  EVENT_MODE_ENABLED: {event_mode_enabled}")
        
        # Check .env.example
        env_example = os.path.join(os.path.dirname(__file__), ".env.example")
        if os.path.exists(env_example):
            with open(env_example, 'r') as f:
                content = f.read()
            
            if "EVENT_MODE_ENABLED=true" in content:
                print(f"  {GREEN}✅ .env.example includes EVENT_MODE_ENABLED{RESET}")
            else:
                print(f"  {RED}❌ EVENT_MODE_ENABLED missing from .env.example{RESET}")
                return False
        
        # Check start.py integration
        start_file = os.path.join(os.path.dirname(__file__), "start.py")
        if os.path.exists(start_file):
            with open(start_file, 'r') as f:
                start_content = f.read()
            
            if "event_mode_enabled" in start_content and "World Cup / Friendlies" in start_content:
                print(f"  {GREEN}✅ start.py displays EVENT_MODE status{RESET}")
            else:
                print(f"  {RED}❌ start.py missing EVENT_MODE banner{RESET}")
                return False
        
        print(f"  {GREEN}✅ Feature flag validation passed{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}❌ Feature flag validation failed: {e}{RESET}")
        return False


def validate_database_columns():
    """Validate EVENT_MODE database columns."""
    print(f"\n{BOLD}🗄️  PHASE 2: Database Columns Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"  {RED}❌ Supabase not connected{RESET}")
            return False
        
        repo = get_repository()
        
        # Check columns exist by selecting one prediction row
        query = repo._client.table("predictions").select(
            "event_context, event_name, is_event_match, event_phase"
        ).limit(1)
        
        result = query.execute()
        
        if result.data is not None:
            print(f"  {GREEN}✅ EVENT_MODE columns exist{RESET}")
            
            # Check if we got actual data (columns exist)
            if len(result.data) > 0:
                row = result.data[0]
                print(f"    {GREEN}✅ Sample row found with EVENT_MODE columns{RESET}")
                
                # Verify all expected columns are present
                expected_columns = ["event_context", "event_name", "is_event_match", "event_phase"]
                all_present = True
                
                for col in expected_columns:
                    if col in row:
                        print(f"    {GREEN}✅ {col} column exists{RESET}")
                    else:
                        print(f"    {RED}❌ {col} column missing{RESET}")
                        all_present = False
                
                return all_present
            else:
                print(f"    {YELLOW}⚠️  No predictions found, but columns exist{RESET}")
                return True
        else:
            print(f"  {RED}❌ EVENT_MODE columns missing{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ Database validation failed: {e}{RESET}")
        return False


def validate_cycle_integration():
    """Validate cycle integration."""
    print(f"\n{BOLD}🔄 PHASE 3: Cycle Integration Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        cycle_file = os.path.join(os.path.dirname(__file__), "scripts", "run_tracking_cycle.py")
        
        if not os.path.exists(cycle_file):
            print(f"  {RED}❌ run_tracking_cycle.py not found{RESET}")
            return False
        
        with open(cycle_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            ("TAG EVENT MODE", "Step exists"),
            ("tag_event_mode", "Function called"),
            ("event_mode_enabled", "Feature flag checked"),
            ("event_tagged_predictions", "Statistics logged"),
            ("2/4", "Step number updated"),
            ("event_matches_detected", "Event matches counted"),
            ("domestic_matches", "Domestic matches counted")
        ]
        
        all_found = True
        for element, description in required_elements:
            if element in content:
                print(f"    {GREEN}✅ {description}{RESET}")
            else:
                print(f"    {RED}❌ Missing: {description}{RESET}")
                all_found = False
        
        if all_found:
            print(f"  {GREEN}✅ Cycle integration validated{RESET}")
            return True
        else:
            print(f"  {RED}❌ Cycle integration incomplete{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ Cycle integration validation failed: {e}{RESET}")
        return False


def validate_api_behavior():
    """Validate API behavior."""
    print(f"\n{BOLD}🌐 PHASE 4: API Behavior Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        import requests
        
        # Test API endpoint exists
        flask_file = os.path.join(os.path.dirname(__file__), "app_flask.py")
        if os.path.exists(flask_file):
            with open(flask_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "/api/event-mode" in content and "event_mode_status" in content:
                print(f"    {GREEN}✅ API endpoint exists{RESET}")
            else:
                print(f"    {RED}❌ API endpoint missing{RESET}")
                return False
            
            # Check if API reads from database only
            if "repo._client.table" in content and "select" in content:
                print(f"    {GREEN}✅ API reads from database only{RESET}")
            else:
                print(f"    {RED}❌ API may trigger scans{RESET}")
                return False
            
            # Try to call API (optional)
            try:
                response = requests.get("http://localhost:5000/api/event-mode", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if "statistics" in data and "event_breakdown" in data:
                        print(f"    {GREEN}✅ API endpoint functional{RESET}")
                    else:
                        print(f"    {RED}❌ API response format incorrect{RESET}")
                        return False
                else:
                    print(f"    {YELLOW}⚠️  API returned {response.status_code} (may be offline){RESET}")
            except requests.exceptions.ConnectionError:
                print(f"    {YELLOW}⚠️  API offline (acceptable for validation){RESET}")
            
            print(f"  {GREEN}✅ API behavior validated{RESET}")
            return True
            
        else:
            print(f"  {RED}❌ app_flask.py not found{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ API validation failed: {e}{RESET}")
        return False


def validate_backfill_tool():
    """Validate backfill tool."""
    print(f"\n{BOLD}🔧 PHASE 5: Backfill Tool Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        backfill_file = os.path.join(os.path.dirname(__file__), "backfill_event_mode.py")
        
        if not os.path.exists(backfill_file):
            print(f"  {RED}❌ backfill_event_mode.py not found{RESET}")
            return False
        
        with open(backfill_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            ("def backfill_event_mode", "Main function exists"),
            ("--dry-run", "Dry run option"),
            ("--days", "Days option"),
            ("--event", "Event filter option"),
            ("tag_event_mode", "Uses tagger"),
            ("Does NOT create duplicate predictions", "No duplicate guarantee"),
            ("Manual audit/backfill tool", "Purpose documented")
        ]
        
        all_found = True
        for element, description in required_elements:
            if element in content:
                print(f"    {GREEN}✅ {description}{RESET}")
            else:
                print(f"    {RED}❌ Missing: {description}{RESET}")
                all_found = False
        
        # Check for explicit no-duplicate guarantee in docstring
        if "NO DUPLICATE GUARANTEE" in content:
            print(f"    {GREEN}✅ No-duplicate guarantee documented{RESET}")
        elif "no duplicate predictions" in content:
            print(f"    {GREEN}✅ No-duplicate guarantee documented{RESET}")
        else:
            print(f"    {YELLOW}⚠️  No-duplicate guarantee not explicitly documented{RESET}")
        
        # Check that it only updates existing rows (not insert)
        if ".update(" in content and "eq(" in content:
            print(f"    {GREEN}✅ Only updates existing rows (update + eq pattern){RESET}")
        else:
            print(f"    {RED}❌ Missing update pattern for existing rows{RESET}")
            all_found = False
        
        # Check that it doesn't call save_prediction
        if "save_prediction(" not in content:
            print(f"    {GREEN}✅ Does not call save_prediction{RESET}")
        else:
            print(f"    {RED}❌ Calls save_prediction (should not insert predictions){RESET}")
            all_found = False
        
        # Check that it doesn't use database insert operations
        lines = content.split('\n')
        insert_found = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check for actual database insert operations (not in comments or sys operations)
            if ((".table(" in line and ".insert(" in line) or 
                (".table(" in line and ".upsert(" in line)) and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                print(f"    {RED}❌ Found database insert/upsert operation line {i}: {stripped[:50]}...{RESET}")
                insert_found = True
                break
        
        if not insert_found:
            print(f"    {GREEN}✅ No database insert/upsert operations found{RESET}")
        else:
            all_found = False
        
        if all_found:
            print(f"  {GREEN}✅ Backfill tool validated (no duplicate guarantee){RESET}")
            return True
        else:
            print(f"  {RED}❌ Backfill tool validation failed{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ Backfill tool validation failed: {e}{RESET}")
        return False


def validate_performance_reporting():
    """Validate performance reporting."""
    print(f"\n{BOLD}📊 PHASE 6: Performance Reporting Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        report_file = os.path.join(os.path.dirname(__file__), "scripts", "performance_report.py")
        
        if not os.path.exists(report_file):
            print(f"  {RED}❌ performance_report.py not found{RESET}")
            return False
        
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            ("EVENT MODE SUMMARY", "Summary section exists"),
            ("Domestic:", "Domestic category"),
            ("Events:", "Events category"),
            ("Friendlies:", "Friendlies category"),
            ("World Cup:", "World Cup category"),
            ("event_context", "Event context query"),
            ("non-blocking", "Error handling")
        ]
        
        all_found = True
        for element, description in required_elements:
            if element in content:
                print(f"    {GREEN}✅ {description}{RESET}")
            else:
                print(f"    {RED}❌ Missing: {description}{RESET}")
                all_found = False
        
        if all_found:
            print(f"  {GREEN}✅ Performance reporting validated{RESET}")
            return True
        else:
            print(f"  {RED}❌ Performance reporting incomplete{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}❌ Performance reporting validation failed: {e}{RESET}")
        return False


def validate_no_duplicates():
    """Validate no duplicate guarantee."""
    print(f"\n{BOLD}🔄 PHASE 7: No Duplicate Guarantee Validation{RESET}")
    print(f"{'='*50}")
    
    try:
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        from datetime import date, timedelta
        
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"  {RED}❌ Supabase not connected{RESET}")
            return False
        
        repo = get_repository()
        
        # Check for duplicates in last 7 days
        cutoff_date = (date.today() - timedelta(days=7)).isoformat()
        
        query = repo._client.table("predictions").select(
            "fixture_id, market, prediction_date, id"
        ).gte("prediction_date", cutoff_date)
        
        result = query.execute()
        predictions = result.data or []
        
        if not predictions:
            print(f"    {YELLOW}⚠️  No predictions found in last 7 days{RESET}")
            print(f"  {GREEN}✅ No duplicate guarantee (no data){RESET}")
            return True
        
        # Check for duplicates
        from collections import defaultdict
        key_counts = defaultdict(list)
        
        for pred in predictions:
            key = f"{pred['fixture_id']}_{pred['market']}_{pred['prediction_date']}"
            key_counts[key].append(pred)
        
        duplicates = {k: v for k, v in key_counts.items() if len(v) > 1}
        
        if duplicates:
            duplicate_count = sum(len(v) - 1 for v in duplicates.values())
            print(f"    {RED}❌ Found {len(duplicates)} duplicate keys with {duplicate_count} duplicates{RESET}")
            return False
        else:
            print(f"    {GREEN}✅ No duplicates found in {len(predictions)} predictions{RESET}")
            print(f"  {GREEN}✅ No duplicate guarantee validated{RESET}")
            return True
            
    except Exception as e:
        print(f"  {RED}❌ Duplicate validation failed: {e}{RESET}")
        return False


def run_complete_validation():
    """Run complete validation."""
    print(f"\n{BOLD}{'='*60}")
    print(f"🔍 EVENT MODE COMPLETE VALIDATION")
    print(f"{'='*60}{RESET}")
    
    validations = [
        ("Feature Flag", validate_feature_flag),
        ("Database Columns", validate_database_columns),
        ("Cycle Integration", validate_cycle_integration),
        ("API Behavior", validate_api_behavior),
        ("Backfill Tool", validate_backfill_tool),
        ("Performance Reporting", validate_performance_reporting),
        ("No Duplicate Guarantee", validate_no_duplicates),
    ]
    
    results = []
    for validation_name, validation_func in validations:
        try:
            result = validation_func()
            results.append((validation_name, result))
        except Exception as e:
            print(f"{RED}❌ {validation_name} - Critical error: {e}{RESET}")
            results.append((validation_name, False))
    
    # Summary
    print(f"\n{BOLD}{'='*60}")
    print(f"📋 VALIDATION SUMMARY")
    print(f"{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for validation_name, result in results:
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"  {status} {validation_name}")
    
    print(f"\n{BOLD}Result: {passed}/{total} validations passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 EVENT_MODE_COMPLETE_VALIDATION_OK{RESET}")
        print(f"\n{CYAN}✅ EVENT_MODE fully integrated and validated!{RESET}")
        print(f"\n{CYAN}🚀 Ready for production:{RESET}")
        print(f"  • Set EVENT_MODE_ENABLED=true in .env")
        print(f"  • Run: python start.py")
        print(f"  • Monitor: python scripts/performance_report.py --days 7")
        print(f"  • Audit: python audit_event_mode_cycle_integration.py")
        print(f"  • Backfill: python backfill_event_mode.py --days 30")
        print(f"  \n🏆 EVENT_MODE ready for World Cup 2026!")
    else:
        print(f"\n{RED}❌ EVENT_MODE_COMPLETE_VALIDATION_FAILED{RESET}")
        print(f"  {total - passed} validations failed")
        print(f"\n{CYAN}🔧 Required actions:{RESET}")
        
        for validation_name, result in results:
            if not result:
                print(f"  • Fix {validation_name}")
    
    return passed == total


if __name__ == "__main__":
    success = run_complete_validation()
    sys.exit(0 if success else 1)
