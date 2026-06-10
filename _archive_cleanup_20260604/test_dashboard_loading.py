"""
Test Dashboard Loading
Debug script to identify loading issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print(" DASHBOARD LOADING TEST")
print("="*60)

try:
    print("\n1. Testing imports...")
    
    from app.providers.data_source_manager import DataSourceManager
    print("   ✅ DataSourceManager")
    
    from app.services.scanner.smart_scanner import SmartScanner
    print("   ✅ SmartScanner")
    
    from app.services.value.value_detector import ValueDetector
    print("   ✅ ValueDetector")
    
    from app.utils.match_status import MatchStatusHelper
    print("   ✅ MatchStatusHelper")
    
    print("\n2. Creating manager...")
    start = datetime.now()
    manager = DataSourceManager()
    duration = (datetime.now() - start).total_seconds()
    print(f"   ✅ Manager created in {duration:.2f}s")
    print(f"   Provider: {manager.provider.config.name}")
    print(f"   Real data: {manager.is_real_data}")
    
    print("\n3. Creating scanner...")
    start = datetime.now()
    scanner = SmartScanner(
        provider=manager.provider,
        is_real_data=manager.is_real_data,
        include_extreme_obscure=False,
        max_analysis=5
    )
    duration = (datetime.now() - start).total_seconds()
    print(f"   ✅ Scanner created in {duration:.2f}s")
    
    print("\n4. Scanning today's matches...")
    print("   (This may take a few seconds...)")
    start = datetime.now()
    scan_result = scanner.scan_today()
    duration = (datetime.now() - start).total_seconds()
    
    print(f"\n   ✅ Scan complete in {duration:.2f}s")
    print(f"   Success: {scan_result.get('success')}")
    print(f"   Total matches: {scan_result.get('total_matches')}")
    print(f"   Target matches: {scan_result.get('target_count')}")
    print(f"   Analyzed: {scan_result.get('analyzed_count')}")
    
    if scan_result.get("analyzed_matches"):
        print(f"\n5. Sample analyzed match:")
        sample = scan_result["analyzed_matches"][0]
        print(f"   Match: {sample['match_data']['home_team']} vs {sample['match_data']['away_team']}")
        print(f"   Status: {sample['match_data'].get('status', 'N/A')}")
        print(f"   Target Level: {sample['profile']['target_level']}")
        print(f"   Target Score: {sample['profile']['target_score']:.0f}/100")
        print(f"   Coverage: {sample['profile']['bookmaker_coverage']['coverage_score']:.0f}%")
        
        if sample.get("analysis") and sample["analysis"].get("signals"):
            signal = sample["analysis"]["signals"][0]
            print(f"   Signal: {signal['type']}")
            print(f"   Confidence: {signal['confidence']:.0%}")
            
            value = signal.get("value_assessment", {})
            print(f"   Value Level: {value.get('value_level', 'N/A')}")
            print(f"   Has Odds: {value.get('has_odds', False)}")
    
    print("\n" + "="*60)
    print(" ✅ ALL TESTS PASSED")
    print("="*60)
    print("\nDashboard should work fine!")
    print("Run: streamlit run dashboard.py")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\nPlease fix the error above before running dashboard.")
