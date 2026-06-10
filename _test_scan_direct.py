"""Run scan_today() directly and time it"""
from dotenv import load_dotenv; load_dotenv(override=True)
import logging, time
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

manager = DataSourceManager()
scanner = SmartScanner(
    provider=manager.provider,
    is_real_data=manager.is_real_data,
    include_extreme_obscure=True,
    odds_provider=manager.odds_provider,
)

print("Starting scan_today()...")
t0 = time.time()
result = scanner.scan_today()
elapsed = time.time() - t0

print(f"\nScan completed in {elapsed:.1f}s")
print(f"  total_matches:   {result.get('total_matches', 0)}")
print(f"  target_count:    {result.get('target_count', 0)}")
print(f"  analyzed_count:  {result.get('analyzed_count', 0)}")
analyzed = result.get('analyzed_matches', [])
print(f"  analyzed_list:   {len(analyzed)}")

# Quick tier check
tiers = {}
for m in analyzed:
    t = m.get('analysis', {}).get('tier_level', 'UNKNOWN')
    tiers[t] = tiers.get(t, 0) + 1
print(f"  tier distribution: {tiers}")
