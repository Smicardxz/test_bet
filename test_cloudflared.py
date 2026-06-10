#!/usr/bin/env python3
"""Test cloudflared tunnel endpoints and CORS."""
import requests

TUNNEL_URL = "https://minimum-amendments-flows-research.trycloudflare.com"
LOVABLE_ORIGIN = "https://833ac7a4-8511-4c83-895c-10d51e8607be.lovableproject.com"

print(f"TUNNEL: {TUNNEL_URL}")
print(f"{'='*80}")

# Test endpoints
endpoints = [
    "/api/health",
    "/api/shadow-lab?since_reset=true",
    "/api/diagnostics",
]

all_ok = True

for ep in endpoints:
    url = f"{TUNNEL_URL}{ep}"
    print(f"\n--- {ep} ---")
    try:
        r = requests.get(url, timeout=20)
        print(f"  STATUS: {r.status_code}")
        print(f"  SIZE: {len(r.content)}b")
        ct = r.headers.get("Content-Type", "?")
        print(f"  Content-Type: {ct}")
        if r.status_code == 200 and "json" in ct:
            keys = list(r.json().keys())[:6]
            print(f"  KEYS: {keys}")
            print(f"  RESULT: OK")
        elif r.status_code == 200:
            print(f"  BODY (first 200): {r.text[:200]}")
            print(f"  RESULT: OK (non-JSON)")
        else:
            print(f"  BODY: {r.text[:200]}")
            print(f"  RESULT: FAIL")
            all_ok = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_ok = False

# Test CORS preflight
print(f"\n{'='*80}")
print(f"CORS PREFLIGHT TEST")
print(f"{'='*80}")

try:
    r = requests.options(
        f"{TUNNEL_URL}/api/health",
        headers={
            "Origin": LOVABLE_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "ngrok-skip-browser-warning, Accept",
        },
        timeout=20,
    )
    print(f"  STATUS: {r.status_code}")
    acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
    acam = r.headers.get("Access-Control-Allow-Methods", "MISSING")
    acah = r.headers.get("Access-Control-Allow-Headers", "MISSING")
    print(f"  Access-Control-Allow-Origin: {acao}")
    print(f"  Access-Control-Allow-Methods: {acam}")
    print(f"  Access-Control-Allow-Headers: {acah}")
    if LOVABLE_ORIGIN in acao:
        print(f"  CORS PREFLIGHT: PASS")
    else:
        print(f"  CORS PREFLIGHT: FAIL")
        all_ok = False
except Exception as e:
    print(f"  ERROR: {e}")
    all_ok = False

# Test CORS on GET
print(f"\n{'='*80}")
print(f"CORS GET TEST")
print(f"{'='*80}")

try:
    r = requests.get(
        f"{TUNNEL_URL}/api/health",
        headers={
            "Origin": LOVABLE_ORIGIN,
            "Accept": "application/json",
        },
        timeout=20,
    )
    print(f"  STATUS: {r.status_code}")
    acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
    print(f"  Access-Control-Allow-Origin: {acao}")
    if LOVABLE_ORIGIN in acao:
        print(f"  CORS GET: PASS")
    else:
        print(f"  CORS GET: FAIL")
        all_ok = False
except Exception as e:
    print(f"  ERROR: {e}")
    all_ok = False

# Final verdict
print(f"\n{'='*80}")
if all_ok:
    print("CLOUDFLARED_BACKEND_OK")
else:
    print("CLOUDFLARED_BACKEND_FAIL")
print(f"{'='*80}")
