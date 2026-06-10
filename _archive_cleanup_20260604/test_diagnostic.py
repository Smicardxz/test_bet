"""
Diagnostic test to identify performance bottleneck
"""
import time
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

print("=" * 60)
print("DIAGNOSTIC TEST - Performance Bottleneck")
print("=" * 60)

# Step 1: Initialize data manager
print("\n1. Initializing DataSourceManager...")
start = time.time()
manager = DataSourceManager()
print(f"   Took {time.time() - start:.2f}s")

# Step 2: Fetch today's matches
print("\n2. Fetching today's matches...")
start = time.time()
response = manager.provider.get_today_matches()
print(f"   Took {time.time() - start:.2f}s")
print(f"   Success: {response.success}")
print(f"   Total matches: {len(response.data) if response.success else 0}")

if response.success:
    all_matches = response.data
    print(f"\n3. Sample of first 5 matches:")
    for i, m in enumerate(all_matches[:5]):
        comp = m.competition.name if hasattr(m, 'competition') else "Unknown"
        country = m.competition.country if hasattr(m, 'competition') else "Unknown"
        status = getattr(m, 'status', 'Unknown')
        print(f"   {i+1}. {comp} ({country}) - {status}")

    # Step 3: Test scanner initialization
    print("\n4. Initializing SmartScanner...")
    start = time.time()
    scanner = SmartScanner(provider=manager.provider, is_real_data=True, max_analysis=5)
    print(f"   Took {time.time() - start:.2f}s")

    # Step 4: Test targeting only (no analysis)
    print("\n5. Testing targeting only (no analysis)...")
    start = time.time()
    from app.services.targeting.league_targeting_service import LeagueTargetingService, TargetMode
    targeting = LeagueTargetingService(target_mode=TargetMode.ALL_MINOR)

    target_count = 0
    for i, match in enumerate(all_matches[:50]):  # Test first 50 only
        profile = targeting.analyze_competition(
            competition_name=match.competition.name if hasattr(match, 'competition') else "",
            country=match.competition.country if hasattr(match, 'competition') else ""
        )
        if targeting.should_include(profile):
            target_count += 1

    print(f"   Took {time.time() - start:.2f}s")
    print(f"   Targeted {target_count}/50 matches")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
