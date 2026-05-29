"""
Verify Real Data Pipeline
Tests if real data from SofaScore or other providers is working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine
from app.services.diagnostics import get_data_source_diagnostics, print_diagnostics


def main():
    """Run real data pipeline verification"""
    
    print("\n🔍 Verifying Real Data Pipeline...\n")
    
    # Initialize
    add_provider_support_to_stats_engine()
    manager = DataSourceManager()
    scanner = DailyScannerServiceV2(manager.provider, is_real_data=manager.is_real_data)
    
    print(f"Provider: {manager.provider.config.name}")
    print(f"Is Real Data: {manager.is_real_data}")
    print(f"Source Label: {manager.source_label}\n")
    
    # Run scan
    print("Running scan...")
    scan_data = scanner.scan_today(max_results=30)
    
    # Get diagnostics
    diagnostics = get_data_source_diagnostics(manager, scan_data)
    
    # Print results
    print_diagnostics(diagnostics)
    
    # Final verdict
    if diagnostics.is_real_data_working():
        print("✅ REAL DATA PIPELINE OK")
        print("   - Provider is reachable")
        print("   - Real matches retrieved")
        print("   - Data is current")
        return 0
    elif diagnostics.api_status == "FORBIDDEN":
        print("❌ REAL DATA NOT CONNECTED")
        print("   - API returned 403 Forbidden")
        print("   - SofaScore blocks non-browser requests")
        print("   - Recommendation: Use MOCK mode or official API")
        return 1
    elif not diagnostics.provider_reachable:
        print("❌ REAL DATA NOT CONNECTED")
        print("   - Provider is not reachable")
        print(f"   - Errors: {len(diagnostics.provider_errors)}")
        return 1
    elif diagnostics.data_mode == "MOCK":
        print("🔴 MOCK DATA ONLY")
        print("   - Running in demo mode")
        print("   - Set DATA_PROVIDER=sofascore for real data")
        return 0
    else:
        print("⚠️ REAL DATA UNCERTAIN")
        print("   - Check diagnostics above")
        return 1


if __name__ == "__main__":
    exit(main())
