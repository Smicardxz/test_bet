"""
Engine Validation Script
Run functional validation suite and generate report
"""

import sys
import subprocess
from datetime import datetime
from pathlib import Path


def run_validation():
    """Run validation suite and generate report"""
    
    print("=" * 80)
    print("🧪 ENGINE FUNCTIONAL VALIDATION")
    print("=" * 80)
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Suite: 20 realistic cases")
    print("\n" + "=" * 80)
    
    # Run pytest with detailed output
    cmd = [
        "pytest",
        "tests/test_functional_validation.py",
        "-v",
        "-s",
        "--tb=short",
        "--color=yes"
    ]
    
    print("\n🚀 Running validation suite...\n")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    print("\n" + "=" * 80)
    
    if result.returncode == 0:
        print("✅ VALIDATION PASSED")
        print("\nAll 20 test cases passed successfully!")
        print("The anomaly detection engine is working as expected.")
    else:
        print("❌ VALIDATION FAILED")
        print("\nSome test cases failed. Review the output above.")
        print("The engine may need calibration or bug fixes.")
    
    print("=" * 80)
    
    return result.returncode


def print_test_summary():
    """Print summary of test cases"""
    
    print("\n📋 TEST CASES SUMMARY")
    print("=" * 80)
    
    categories = {
        "STRONG ANOMALIES (HIGH)": [
            "STRONG_01: HT Under 0.5 - Très défensif",
            "STRONG_02: Extreme Under 10.5 - Très bas scoring",
            "STRONG_03: FT Under 2.5 - Défensif stable",
            "STRONG_04: BTTS - Équipes offensives"
        ],
        "MEDIUM ANOMALIES (MEDIUM)": [
            "MEDIUM_01: FT Under 2.5 - Échantillon modéré",
            "MEDIUM_02: HT Under 0.5 - Variance moyenne",
            "MEDIUM_03: FT Over 2.5 - Écart modéré"
        ],
        "FALSE POSITIVES (LOW)": [
            "FALSE_01: FT Under 2.5 - Variance très élevée",
            "FALSE_02: BTTS - Petit échantillon + variance"
        ],
        "COHERENT LINES (No Anomaly)": [
            "COHERENT_01: FT Under 2.5 - Ligne cohérente",
            "COHERENT_02: HT Under 0.5 - Ligne correcte",
            "COHERENT_03: BTTS - Ligne équilibrée"
        ],
        "EDGE CASES": [
            "EDGE_01: Extreme Under 6.5 - Borderline",
            "EDGE_02: HT Under 1.5 - Limite haute",
            "EDGE_03: FT Under 3.5 - Variance modérée"
        ],
        "REALISTIC SCENARIOS": [
            "REAL_01: FT Under 1.5 - Très défensif",
            "REAL_02: HT Over 0.5 - Équipes offensives HT",
            "REAL_03: FT Over 3.5 - Équipes offensives"
        ]
    }
    
    for category, cases in categories.items():
        print(f"\n{category}:")
        for case in cases:
            print(f"  • {case}")
    
    print("\n" + "=" * 80)


def main():
    """Main validation script"""
    
    # Print summary first
    print_test_summary()
    
    # Ask for confirmation
    print("\n⚠️  This will run 20 functional test cases.")
    print("Each test validates anomaly detection accuracy.\n")
    
    response = input("Continue? [Y/n]: ").strip().lower()
    
    if response and response != 'y':
        print("\n❌ Validation cancelled.")
        return 1
    
    # Run validation
    exit_code = run_validation()
    
    # Additional info
    if exit_code == 0:
        print("\n📚 Next Steps:")
        print("  1. Review test output above")
        print("  2. Check anomaly scores are in expected ranges")
        print("  3. Verify confidence categories (HIGH/MEDIUM/LOW)")
        print("  4. If all passed, engine is production-ready!")
    else:
        print("\n🔧 Troubleshooting:")
        print("  1. Review failed test cases")
        print("  2. Check anomaly_engine.py scoring logic")
        print("  3. Adjust thresholds if needed")
        print("  4. Re-run validation")
    
    print("\n" + "=" * 80)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
