#!/usr/bin/env python3
"""Validate CORS configuration for Lovable + Cloudflare tunnel."""
import requests

BASE = "http://127.0.0.1:5000"
LOVABLE = "https://833ac7a4-8511-4c83-895c-10d51e8607be.lovableproject.com"

all_ok = True

# 1. OPTIONS preflight
print("=== OPTIONS PREFLIGHT /api/shadow-lab ===")
r = requests.options(f"{BASE}/api/shadow-lab", headers={
    "Origin": LOVABLE,
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "ngrok-skip-browser-warning, Accept",
})
acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
acam = r.headers.get("Access-Control-Allow-Methods", "MISSING")
acah = r.headers.get("Access-Control-Allow-Headers", "MISSING")
print(f"  Status: {r.status_code}")
print(f"  Access-Control-Allow-Origin: {acao}")
print(f"  Access-Control-Allow-Methods: {acam}")
print(f"  Access-Control-Allow-Headers: {acah}")
if LOVABLE not in acao:
    all_ok = False
    print("  FAIL")
else:
    print("  PASS")

# 2. GET /api/health
print("\n=== GET /api/health ===")
r = requests.get(f"{BASE}/api/health", headers={"Origin": LOVABLE, "Accept": "application/json"})
acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
print(f"  Status: {r.status_code}")
print(f"  Access-Control-Allow-Origin: {acao}")
print(f"  JSON keys: {list(r.json().keys())[:5]}")
if r.status_code != 200 or LOVABLE not in acao:
    all_ok = False
    print("  FAIL")
else:
    print("  PASS")

# 3. GET /api/shadow-lab?since_reset=true
print("\n=== GET /api/shadow-lab?since_reset=true ===")
r = requests.get(f"{BASE}/api/shadow-lab?since_reset=true", headers={"Origin": LOVABLE, "Accept": "application/json"})
acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
print(f"  Status: {r.status_code}")
print(f"  Access-Control-Allow-Origin: {acao}")
if r.status_code == 200:
    print(f"  JSON keys: {list(r.json().keys())[:6]}")
else:
    print(f"  Body: {r.text[:100]}")
if r.status_code != 200 or LOVABLE not in acao:
    all_ok = False
    print("  FAIL")
else:
    print("  PASS")

# 4. GET /api/diagnostics
print("\n=== GET /api/diagnostics ===")
r = requests.get(f"{BASE}/api/diagnostics", headers={"Origin": LOVABLE, "Accept": "application/json"})
acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
print(f"  Status: {r.status_code}")
print(f"  Access-Control-Allow-Origin: {acao}")
if r.status_code == 200:
    print(f"  JSON keys: {list(r.json().keys())[:6]}")
else:
    print(f"  Body: {r.text[:100]}")
if r.status_code != 200 or LOVABLE not in acao:
    all_ok = False
    print("  FAIL")
else:
    print("  PASS")

# 5. Disallowed origin
print("\n=== DISALLOWED ORIGIN (evil.com) ===")
r = requests.get(f"{BASE}/api/health", headers={"Origin": "https://evil.com"})
acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
print(f"  Access-Control-Allow-Origin: {acao}")
if "evil.com" in acao:
    all_ok = False
    print("  FAIL (should not allow evil.com)")
else:
    print("  PASS (correctly blocked)")

# Verdict
print(f"\n{'='*60}")
if all_ok:
    print("CLOUDFLARED_BACKEND_OK")
else:
    print("CLOUDFLARED_BACKEND_FAIL")
print(f"{'='*60}")
