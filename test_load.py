"""Test load_data function"""
import traceback
from app_flask import load_data

try:
    print("[TEST] Calling load_data()...")
    data = load_data()
    print("[TEST] SUCCESS!")
    print(f"[TEST] Keys: {data.keys()}")
    if "scan_result" in data:
        print(f"[TEST] Scan result keys: {data['scan_result'].keys()}")
except Exception as e:
    print(f"[TEST] ERROR: {e}")
    traceback.print_exc()
