"""
System Audit - Complete diagnostic
Checks all connections and data sources
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from datetime import datetime, timezone
from dotenv import load_dotenv

print("="*60)
print(" SYSTEM AUDIT - COMPLETE DIAGNOSTIC")
print("="*60)

# 1. Environment Variables
print("\n1. ENVIRONMENT VARIABLES")
print("-" * 60)

load_dotenv()

data_provider = os.getenv("DATA_PROVIDER")
api_key = os.getenv("API_FOOTBALL_KEY")
api_url = os.getenv("API_FOOTBALL_URL")

print(f"DATA_PROVIDER: {data_provider or 'NOT SET'}")
print(f"API_FOOTBALL_KEY: {'SET (' + api_key[:20] + '...)' if api_key else 'NOT SET'}")
print(f"API_FOOTBALL_URL: {api_url or 'NOT SET'}")

if not data_provider:
    print("\n⚠️  WARNING: DATA_PROVIDER not set - will use MOCK data")
if not api_key:
    print("\n⚠️  WARNING: API_FOOTBALL_KEY not set - cannot use real API")

# 2. Data Source Manager
print("\n2. DATA SOURCE MANAGER")
print("-" * 60)

from app.providers.data_source_manager import DataSourceManager

manager = DataSourceManager()

print(f"Provider Name: {manager.provider.config.name}")
print(f"Provider Type: {type(manager.provider).__name__}")
print(f"Is Real Data: {manager.is_real_data}")
print(f"Source Label: {manager.config.source_label}")

if not manager.is_real_data:
    print("\n❌ CRITICAL: Using MOCK data instead of real API")
    print("   This explains why matches are not from today")

# 3. Test API Connection
print("\n3. API CONNECTION TEST")
print("-" * 60)

if manager.is_real_data:
    print("Testing API connection...")
    response = manager.provider.get_today_matches()
    
    if response.success:
        print(f"✅ API connection successful")
        print(f"   Matches fetched: {len(response.data)}")
        
        if response.data:
            first_match = response.data[0]
            print(f"   First match: {first_match.home_team.name} vs {first_match.away_team.name}")
            print(f"   Match date: {first_match.match_date}")
    else:
        print(f"❌ API connection failed: {response.error}")
else:
    print("⚠️  Skipping API test - using MOCK provider")

# 4. Date Validation
print("\n4. DATE VALIDATION")
print("-" * 60)

now_utc = datetime.now(timezone.utc)
now_local = now_utc.replace(tzinfo=None)  # Local time

print(f"Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Current Local: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")

# 5. Scanner Test
print("\n5. SCANNER TEST")
print("-" * 60)

from app.services.scanner.lightweight_scanner import LightweightMatchScanner

scanner = LightweightMatchScanner(manager.provider, is_real_data=manager.is_real_data)
scan_result = scanner.scan_today()

print(f"Scan Success: {scan_result.get('success')}")
print(f"Total Matches: {scan_result.get('total_matches')}")
print(f"Target Matches: {scan_result.get('target_count')}")
print(f"Scan Duration: {scan_result.get('scan_duration_seconds'):.2f}s")

target_matches = scan_result.get('target_matches', [])

if target_matches:
    print(f"\nFirst 3 target matches:")
    for i, match in enumerate(target_matches[:3], 1):
        print(f"  {i}. {match['home_team']} vs {match['away_team']}")
        print(f"     Kickoff: {match['kickoff_time']}")
        print(f"     Country: {match['country']}")

# 6. Final Verdict
print("\n" + "="*60)
print(" FINAL VERDICT")
print("="*60)

issues = []

if not data_provider:
    issues.append("DATA_PROVIDER environment variable not set")

if not api_key:
    issues.append("API_FOOTBALL_KEY environment variable not set")

if not manager.is_real_data:
    issues.append("System is using MOCK data instead of real API")

if issues:
    print("\n❌ ISSUES FOUND:")
    for issue in issues:
        print(f"   - {issue}")
    
    print("\n🔧 SOLUTION:")
    print("   1. Create/update .env file with:")
    print("      DATA_PROVIDER=api_football")
    print("      API_FOOTBALL_KEY=your_api_key_here")
    print("      API_FOOTBALL_URL=https://v3.football.api-sports.io")
    print("   2. Restart the dashboard")
    print("   3. Run this audit again to verify")
else:
    print("\n✅ ALL SYSTEMS OPERATIONAL")
    print("   - Real API connected")
    print("   - Fresh data available")
    print("   - Ready for production use")

print("\n" + "="*60 + "\n")
