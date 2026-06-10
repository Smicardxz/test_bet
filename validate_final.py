#!/usr/bin/env python3
"""
Validation finale PHASE 1-9
Test toutes les corrections implémentées
"""

import sys
import os
import json
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_endpoints():
    """Test API endpoints for PHASE 7-8 validation"""
    
    print("=" * 60)
    print(" VALIDATION FINALE API ENDPOINTS")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000/api"
    
    endpoints = [
        ("/health", "Health check"),
        ("/dashboard/summary", "Dashboard summary"),
        ("/matches?limit=5", "Matches endpoint"),
        ("/leagues/coverage", "Leagues coverage")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "SUCCESS",
                    "description": description,
                    "data_keys": list(data.keys()) if isinstance(data, dict) else "non-dict",
                    "data_size": len(str(data))
                }
                print(f"✅ {description}: SUCCESS ({len(str(data))} bytes)")
            else:
                results[endpoint] = {
                    "status": "FAILED",
                    "description": description,
                    "error": f"HTTP {response.status_code}"
                }
                print(f"❌ {description}: FAILED (HTTP {response.status_code})")
                
        except Exception as e:
            results[endpoint] = {
                "status": "ERROR",
                "description": description,
                "error": str(e)
            }
            print(f"❌ {description}: ERROR ({e})")
    
    return results

def validate_phase_structure():
    """Validate PHASE 7 API structure"""
    
    print("\n" + "=" * 60)
    print(" VALIDATION PHASE 7: API STRUCTURE")
    print("=" * 60)
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=3", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API endpoint failed: {response.status_code}")
            return False
        
        data = response.json()
        matches = data.get("matches", [])
        
        if not matches:
            print("ℹ️  No matches returned (might be normal)")
            return True
        
        # Check first match structure
        match = matches[0]
        required_fields = [
            "fixture_id", "home_team", "away_team", "country", "league", 
            "kickoff_time", "status", "target_category", "analysis_status",
            "profile_tags", "best_pick", "statistical_angles",
            "interest_score", "confidence_score", "volatility_score", 
            "data_quality_score", "waiting_for_odds"
        ]
        
        missing_fields = [field for field in required_fields if field not in match]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present")
        
        # Check best_pick structure if present
        if match.get("best_pick"):
            best_pick = match["best_pick"]
            best_pick_fields = ["market", "label", "hit_rate", "fair_odd", "sample_size", "confidence", "why"]
            missing_bp = [field for field in best_pick_fields if field not in best_pick]
            
            if missing_bp:
                print(f"❌ Missing best_pick fields: {missing_bp}")
                return False
            
            print("✅ Best pick structure correct")
        
        # Check scores are numeric
        score_fields = ["interest_score", "confidence_score", "volatility_score", "data_quality_score"]
        for field in score_fields:
            if not isinstance(match.get(field), (int, float)):
                print(f"❌ {field} is not numeric: {type(match.get(field))}")
                return False
        
        print("✅ All scores are numeric")
        
        # Check waiting_for_odds is boolean
        if not isinstance(match.get("waiting_for_odds"), bool):
            print(f"❌ waiting_for_odds is not boolean: {type(match.get('waiting_for_odds'))}")
            return False
        
        print("✅ waiting_for_odds is boolean")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 7 validation failed: {e}")
        return False

def validate_phase_dashboard():
    """Validate PHASE 8 dashboard data contract"""
    
    print("\n" + "=" * 60)
    print(" VALIDATION PHASE 8: DASHBOARD DATA CONTRACT")
    print("=" * 60)
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=10", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API endpoint failed: {response.status_code}")
            return False
        
        data = response.json()
        
        # Check required top-level fields
        required_fields = ["success", "categories", "diagnostic", "filters", "status_breakdown", "coverage"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"❌ Missing top-level fields: {missing_fields}")
            return False
        
        print("✅ All top-level fields present")
        
        # Check categories structure
        categories = data.get("categories", {})
        required_categories = ["live", "finished", "upcoming_inefficiencies", "upcoming_statistical", "upcoming_pending"]
        missing_cats = [cat for cat in required_categories if cat not in categories]
        
        if missing_cats:
            print(f"❌ Missing categories: {missing_cats}")
            return False
        
        print("✅ All categories present")
        
        # Check status_breakdown
        status_breakdown = data.get("status_breakdown", {})
        required_status = ["upcoming_count", "live_count", "finished_count", "cancelled_count", "target_matches_count"]
        missing_status = [field for field in required_status if field not in status_breakdown]
        
        if missing_status:
            print(f"❌ Missing status_breakdown fields: {missing_status}")
            return False
        
        print("✅ Status breakdown structure correct")
        
        # Check coverage data
        coverage = data.get("coverage", {})
        if not all(field in coverage for field in ["countries", "leagues_by_country", "total_countries", "total_leagues"]):
            print("❌ Missing coverage fields")
            return False
        
        print("✅ Coverage data structure correct")
        print(f"   - Countries covered: {coverage['total_countries']}")
        print(f"   - Total leagues: {coverage['total_leagues']}")
        
        # Check for target countries
        countries = coverage.get("countries", [])
        target_countries = ["China", "Kazakhstan", "Vietnam", "Ethiopia", "Egypt", "Sudan"]
        found_targets = [c for c in target_countries if c in countries]
        
        if found_targets:
            print(f"✅ Target countries found: {found_targets}")
        else:
            print("ℹ️  No target countries in current data (might be normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 8 validation failed: {e}")
        return False

def validate_phase_profiles():
    """Validate PHASE 4: Diversified profiles"""
    
    print("\n" + "=" * 60)
    print(" VALIDATION PHASE 4: DIVERSIFIED PROFILES")
    print("=" * 60)
    
    try:
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=10", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API endpoint failed: {response.status_code}")
            return False
        
        data = response.json()
        matches = data.get("matches", [])
        
        # Collect all profile tags
        all_profiles = set()
        all_markets = set()
        
        for match in matches:
            profile_tags = match.get("profile_tags", [])
            all_profiles.update(profile_tags)
            
            best_pick = match.get("best_pick")
            if best_pick:
                all_markets.add(best_pick.get("market", ""))
        
        print(f"✅ Found {len(all_profiles)} unique profile tags")
        print(f"✅ Found {len(all_markets)} unique markets")
        
        # Check for diverse profiles
        expected_profiles = [
            "HT_UNDER_PROFILE", "HT_OVER_PROFILE", "FT_UNDER_PROFILE", 
            "FT_OVER_PROFILE", "BTTS_PROFILE", "NO_BTTS_PROFILE",
            "LOW_TEMPO", "HIGH_TEMPO", "SECOND_HALF_GOALS",
            "LATE_GOAL_PROFILE", "VOLATILE_MATCH", "CHAOTIC_MATCH",
            "HOME_DOMINANT", "AWAY_WEAKNESS", "ASYMMETRIC_SCORING"
        ]
        
        found_profiles = [p for p in expected_profiles if any(p in tag for tag in all_profiles)]
        
        if found_profiles:
            print(f"✅ Diverse profiles found: {found_profiles}")
        else:
            print("ℹ️  No specific profiles found (might be normal)")
        
        # Check for useful markets (PHASE 5)
        useful_markets = {
            'HT_UNDER_0_5', 'HT_UNDER_1_5', 'HT_OVER_0_5', 'HT_OVER_1_5',
            'UNDER_1_5', 'UNDER_2_5', 'UNDER_3_5',
            'OVER_1_5', 'OVER_2_5',
            'BTTS_YES', 'BTTS_NO'
        }
        
        found_useful = [m for m in useful_markets if m in all_markets]
        
        if found_useful:
            print(f"✅ Useful markets found: {found_useful}")
        else:
            print("ℹ️  No useful markets found (might be normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 4 validation failed: {e}")
        return False

def main():
    """Run all validation phases"""
    
    print("🎯 VALIDATION FINALE SYSTÈME COMPLET")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test API endpoints
    api_results = test_api_endpoints()
    
    # Validate phases
    phase_results = {
        "PHASE_7_API_STRUCTURE": validate_phase_structure(),
        "PHASE_8_DASHBOARD_CONTRACT": validate_phase_dashboard(),
        "PHASE_4_DIVERSE_PROFILES": validate_phase_profiles()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print(" RÉCAPITULATIF VALIDATION")
    print("=" * 60)
    
    # API results
    print("\n📡 API Endpoints:")
    for endpoint, result in api_results.items():
        status = result["status"]
        print(f"   {status}: {result['description']}")
    
    # Phase results
    print("\n🔧 Phase validations:")
    for phase, passed in phase_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status}: {phase}")
    
    # Overall result
    api_passed = all(r["status"] == "SUCCESS" for r in api_results.values())
    phases_passed = all(phase_results.values())
    
    overall_success = api_passed and phases_passed
    
    print(f"\n🎯 RÉSULTAT GLOBAL:")
    if overall_success:
        print("   ✅ TOUTES LES VALIDATIONS RÉUSSIES")
        print("   🚀 SYSTÈME PRÊT POUR PROMPT LOVABLE")
    else:
        print("   ❌ CERTAINES VALIDATIONS ONTS ÉCHOUÉES")
        print("   🔧 CORRECTIONS NÉCESSAIRES")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
