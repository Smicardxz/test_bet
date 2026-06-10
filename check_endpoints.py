#!/usr/bin/env python3
import requests, json, sys

BASE = "http://127.0.0.1:5000"
endpoints = [
    "/api/health",
    "/api/matches",
    "/api/dashboard/summary",
    "/api/performance/summary",
    "/api/performance/by-league",
    "/api/performance/by-market",
    "/api/predictions/pending",
    "/api/predictions/history",
]

print(f"{'ENDPOINT':<35} {'STATUS':<8} {'SIZE':<10} {'KEYS / ERROR'}")
print("-" * 100)

for ep in endpoints:
    try:
        r = requests.get(f"{BASE}{ep}", timeout=15)
        try:
            data = r.json()
            keys = list(data.keys())
            # Extract useful counts
            extras = []
            for k in ["total", "count", "returned", "success", "is_ready"]:
                if k in data:
                    extras.append(f"{k}={data[k]}")
            info = ", ".join(extras) if extras else str(keys)
        except Exception:
            info = r.text[:80]
        print(f"{ep:<35} {r.status_code:<8} {len(r.content):<10} {info}")
    except Exception as e:
        print(f"{ep:<35} {'ERR':<8} {'':<10} {e}")
