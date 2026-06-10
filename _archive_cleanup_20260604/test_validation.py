"""
Validation Tests for Dashboard Refactoring
Tests to verify data structure and UI consistency
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.data_source_manager import DataSourceManager
from app.services.betting.scan_result_converter import scan_results_to_bet_candidates


def test_bet_candidate_structure():
    """Test that BetCandidate has all required fields"""
    print("=" * 60)
    print("TEST 1: BetCandidate Structure")
    print("=" * 60)
    
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    scan_data = scanner.scan_today(max_results=5)
    single_bets = scan_data.get("single_bets", [])
    
    if not single_bets:
        print("❌ FAILED: No single bets found")
        return False
    
    required_fields = [
        "data_source", "match_id", "home_team", "away_team", "competition",
        "country", "kickoff_time", "market_type", "line", "odd", "bookmaker",
        "anomaly_score", "confidence_score", "confidence_category", "risk_score",
        "risk_level", "data_quality_score", "sample_size", "model_probability",
        "bookmaker_probability", "edge_percentage", "priority_score",
        "positive_signals", "risk_factors", "explanation_short", "explanation_full"
    ]
    
    all_passed = True
    for i, bet in enumerate(single_bets):
        print(f"\nBet {i+1}: {bet.get('home_team', 'Unknown')} vs {bet.get('away_team', 'Unknown')}")
        
        for field in required_fields:
            if field not in bet:
                print(f"  ❌ MISSING FIELD: {field}")
                all_passed = False
            else:
                value = bet[field]
                if value is None or value == "" or value == "Unknown":
                    if field in ["home_team", "away_team", "market_type"]:
                        print(f"  ❌ CRITICAL FIELD EMPTY: {field} = {value}")
                        all_passed = False
                    else:
                        print(f"  ⚠️  Field empty: {field} = {value}")
                else:
                    print(f"  ✓ {field}: {value}")
    
    if all_passed:
        print("\n✅ PASSED: All required fields present")
    else:
        print("\n❌ FAILED: Some required fields missing or empty")
    
    return all_passed


def test_no_unknown_display():
    """Test that 'Unknown' is not displayed when data exists"""
    print("\n" + "=" * 60)
    print("TEST 2: No 'Unknown' Display When Data Exists")
    print("=" * 60)
    
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    scan_data = scanner.scan_today(max_results=5)
    single_bets = scan_data.get("single_bets", [])
    
    if not single_bets:
        print("❌ FAILED: No single bets found")
        return False
    
    all_passed = True
    for i, bet in enumerate(single_bets):
        print(f"\nBet {i+1}:")
        
        # Check if provider has data but bet shows Unknown
        if bet.get("home_team") == "Unknown":
            print(f"  ❌ home_team is Unknown - should have data from provider")
            all_passed = False
        
        if bet.get("away_team") == "Unknown":
            print(f"  ❌ away_team is Unknown - should have data from provider")
            all_passed = False
        
        if bet.get("competition") == "Unknown":
            print(f"  ⚠️  competition is Unknown - may be missing from provider")
        
        if bet.get("bookmaker") == "Unknown":
            print(f"  ⚠️  bookmaker is Unknown - odds data may be missing")
        
        if all_passed:
            print(f"  ✓ No critical Unknown fields")
    
    if all_passed:
        print("\n✅ PASSED: No critical Unknown fields when data should exist")
    else:
        print("\n❌ FAILED: Unknown fields present when data should exist")
    
    return all_passed


def test_priority_score_consistency():
    """Test that priority_score is consistent with display"""
    print("\n" + "=" * 60)
    print("TEST 3: Priority Score Consistency")
    print("=" * 60)
    
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    scan_data = scanner.scan_today(max_results=5)
    single_bets = scan_data.get("single_bets", [])
    
    if not single_bets:
        print("❌ FAILED: No single bets found")
        return False
    
    all_passed = True
    for i, bet in enumerate(single_bets):
        priority = bet.get("priority_score", 0)
        anomaly = bet.get("anomaly_score", 0)
        confidence = bet.get("confidence_score", 0)
        
        print(f"\nBet {i+1}:")
        print(f"  Priority: {priority}")
        print(f"  Anomaly: {anomaly}")
        print(f"  Confidence: {confidence}")
        
        # Priority should not be 0 if anomaly and confidence are reasonable
        if priority == 0 and (anomaly > 50 or confidence > 0.5):
            print(f"  ❌ Priority is 0 but anomaly={anomaly} and confidence={confidence}")
            all_passed = False
        else:
            print(f"  ✓ Priority score is consistent")
    
    if all_passed:
        print("\n✅ PASSED: Priority scores are consistent")
    else:
        print("\n❌ FAILED: Priority scores inconsistent")
    
    return all_passed


def test_combinations_generation():
    """Test that combinations are generated when compatible bets exist"""
    print("\n" + "=" * 60)
    print("TEST 4: Combinations Generation")
    print("=" * 60)
    
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    scan_data = scanner.scan_today(max_results=20)
    single_bets = scan_data.get("single_bets", [])
    combinations = scan_data.get("combinations", [])
    
    print(f"Single bets found: {len(single_bets)}")
    print(f"Combinations generated: {len(combinations)}")
    
    # Check if combinations should be generated
    high_confidence_bets = [b for b in single_bets if b.get("confidence_category") == "HIGH"]
    print(f"High confidence bets: {len(high_confidence_bets)}")
    
    if len(high_confidence_bets) >= 2:
        if len(combinations) > 0:
            print("✅ PASSED: Combinations generated when enough high-confidence bets exist")
            return True
        else:
            print("❌ FAILED: No combinations generated despite enough high-confidence bets")
            return False
    else:
        print("⚠️  SKIPPED: Not enough high-confidence bets to test combination generation")
        return True


def test_source_status():
    """Test that source_status is properly returned"""
    print("\n" + "=" * 60)
    print("TEST 5: Source Status")
    print("=" * 60)
    
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    scan_data = scanner.scan_today(max_results=5)
    source_status = scan_data.get("source_status", {})
    
    required_status_fields = [
        "provider", "data_mode", "matches_found", "markets_analyzed",
        "odds_available", "missing_odds", "errors"
    ]
    
    all_passed = True
    for field in required_status_fields:
        if field not in source_status:
            print(f"  ❌ MISSING: {field}")
            all_passed = False
        else:
            print(f"  ✓ {field}: {source_status[field]}")
    
    if all_passed:
        print("\n✅ PASSED: Source status contains all required fields")
    else:
        print("\n❌ FAILED: Source status missing required fields")
    
    return all_passed


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("DASHBOARD REFACTORING VALIDATION TESTS")
    print("=" * 60)
    
    results = []
    
    results.append(("BetCandidate Structure", test_bet_candidate_structure()))
    results.append(("No Unknown Display", test_no_unknown_display()))
    results.append(("Priority Score Consistency", test_priority_score_consistency()))
    results.append(("Combinations Generation", test_combinations_generation()))
    results.append(("Source Status", test_source_status()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
