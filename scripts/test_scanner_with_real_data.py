"""Test Scanner with Real API-Football Data"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

load_dotenv()

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


def main():
    """Test scanner with real data"""
    
    print("\n" + "="*60)
    print(" SCANNER TEST WITH REAL DATA")
    print("="*60 + "\n")
    
    # Check environment
    env_provider = os.getenv("DATA_PROVIDER", "not set")
    print(f"DATA_PROVIDER: {env_provider}\n")
    
    # Initialize
    add_provider_support_to_stats_engine()
    manager = DataSourceManager()
    
    print(f"Provider: {manager.provider.__class__.__name__}")
    print(f"Source Label: {manager.source_label}")
    print(f"Is Real Data: {manager.is_real_data}\n")
    
    # Initialize scanner
    scanner = DailyScannerServiceV2(
        provider=manager.provider,
        is_real_data=manager.is_real_data
    )
    
    print("Running scan...")
    print("(This may take a moment with real data)\n")
    
    # Run scan
    scan_result = scanner.scan_today(max_results=10)
    
    # Display results
    print("="*60)
    print(" SCAN RESULTS")
    print("="*60 + "\n")
    
    source_status = scan_result.get("source_status", {})
    print(f"Provider: {source_status.get('provider', 'Unknown')}")
    print(f"Data Source: {source_status.get('data_source', 'Unknown')}")
    print(f"Matches Fetched: {source_status.get('matches_fetched', 0)}")
    print(f"Scan Duration: {source_status.get('scan_duration_seconds', 0):.2f}s\n")
    
    # Errors
    errors = source_status.get("errors", [])
    if errors:
        print(f"⚠️  Errors: {len(errors)}")
        for error in errors[:3]:
            print(f"   - {error}")
        print()
    
    # Single bets
    single_bets = scan_result.get("single_bets", [])
    print(f"Single Bets: {len(single_bets)}")
    
    if single_bets:
        print("\nTop 5 Bets:")
        for i, bet in enumerate(single_bets[:5], 1):
            print(f"\n{i}. {bet.get('home_team')} vs {bet.get('away_team')}")
            print(f"   Competition: {bet.get('competition')} ({bet.get('country')})")
            print(f"   Market: {bet.get('market_type')}")
            print(f"   Confidence: {bet.get('confidence_score', 0):.2f}")
            print(f"   Priority: {bet.get('priority_score', 0):.2f}")
            print(f"   Data Source: {bet.get('data_source', 'Unknown')}")
    
    # Combinations
    combinations = scan_result.get("combinations", [])
    print(f"\nCombinations: {len(combinations)}")
    
    # Summary
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60 + "\n")
    
    if manager.is_real_data and len(single_bets) > 0:
        print("✅ REAL DATA SCANNER WORKING")
        print(f"   - {len(single_bets)} bets generated from real matches")
        print(f"   - Provider: {source_status.get('provider')}")
        print(f"   - Data is genuine from API-Football")
    elif manager.is_mock_data:
        print("🔴 MOCK DATA MODE")
        print("   - Set DATA_PROVIDER=api_football for real data")
    else:
        print("⚠️  REAL DATA MODE BUT NO BETS")
        print("   - This may be normal if no anomalies detected")
    
    print("\n" + "="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
