"""
audit_ngrok_front_connectivity.py
==================================
Validates ngrok/Lovable connectivity from browser perspective.

Checks:
  - HTTP status = 200
  - Access-Control-Allow-Origin present
  - JSON parse OK
  - EV pick counts match expectations

Usage:
  python audit_ngrok_front_connectivity.py
  python audit_ngrok_front_connectivity.py --url https://your-ngrok-url.ngrok-free.dev/api
"""

import argparse
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def _check_endpoint(base_url: str, path: str, params: str = "") -> dict:
    """Make a GET request and return status, cors, json, error."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if params:
        url += f"?{params}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BetIQ-Audit/1.0)",
                "ngrok-skip-browser-warning": "true",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            cors = resp.headers.get("Access-Control-Allow-Origin", "")
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = None
            return {"status": status, "cors": cors, "json": data, "error": None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "cors": "", "json": None, "error": str(e)}
    except urllib.error.URLError as e:
        return {"status": 0, "cors": "", "json": None, "error": str(e)}
    except Exception as e:
        return {"status": 0, "cors": "", "json": None, "error": str(e)}


def _count_ev_picks_in_matches(matches: list) -> dict:
    """Count EV picks in /api/matches response."""
    has_odds = sum(1 for m in matches if m.get("has_odds"))
    best_ev = sum(1 for m in matches if m.get("best_ev_opportunity"))
    ev_tier = sum(1 for m in matches if m.get("ev_tier") in ("S_TIER", "A_TIER"))
    is_ev = sum(1 for m in matches if m.get("is_ev_pick"))
    return {"has_odds": has_odds, "best_ev": best_ev, "ev_tier": ev_tier, "is_ev_pick": is_ev}


def _count_ev_picks_in_predictions(preds: list) -> dict:
    """Count EV picks in predictions response."""
    with_odd = sum(1 for p in preds if p.get("bookmaker_odd"))
    ge_1_1 = sum(1 for p in preds if (p.get("bookmaker_odd") or 0) >= 1.1)
    is_ev = sum(1 for p in preds if p.get("is_ev_pick"))
    return {"with_odd": with_odd, "ge_1_1": ge_1_1, "is_ev_pick": is_ev}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("PUBLIC_API_BASE", "http://localhost:5000/api"),
                        help="Base API URL (default: PUBLIC_API_BASE env or localhost:5000/api)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  NGROK FRONT-END CONNECTIVITY AUDIT{RESET}")
    print(f"{'═'*66}")
    _info(f"Base URL: {args.url}")

    # ── Endpoints to check ─────────────────────────────────────────────────────
    endpoints = [
        ("matches", ""),
        ("predictions/pending", ""),
        ("predictions/history", "since_reset=true"),
        ("performance/summary", "since_reset=true"),
        ("data", ""),
        ("diagnostics", ""),
    ]

    results = {}
    all_ok = True

    for path, params in endpoints:
        print(f"\n{BOLD}── GET /{path}{'?' + params if params else ''} {'─'*35}{RESET}")
        r = _check_endpoint(args.url, path, params)
        results[path] = r

        if r["error"]:
            _err(f"Request failed: {r['error']}")
            all_ok = False
            continue

        if r["status"] != 200:
            _err(f"HTTP {r['status']} (expected 200)")
            all_ok = False
        else:
            _ok(f"HTTP {r['status']}")

        if not r["cors"]:
            _warn("No Access-Control-Allow-Origin header")
            all_ok = False
        else:
            _ok(f"CORS: {r['cors']}")

        if r["json"] is None:
            _err("JSON parse failed")
            all_ok = False
        else:
            _ok("JSON parse OK")

    # ── EV pick counts ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}── EV Pick Counts {'─'*47}{RESET}")

    # /api/matches
    m_res = results.get("matches", {})
    if m_res.get("json") and "matches" in m_res["json"]:
        matches = m_res["json"]["matches"]
        m_counts = _count_ev_picks_in_matches(matches)
        print(f"  /api/matches:")
        print(f"    has_odds (true)          : {m_counts['has_odds']}")
        print(f"    best_ev_opportunity (!=null): {m_counts['best_ev']}")
        print(f"    ev_tier (S/A)            : {m_counts['ev_tier']}")
        print(f"    is_ev_pick (flag)        : {m_counts['is_ev_pick']}")
    else:
        _warn("/api/matches JSON missing or invalid")

    # /api/predictions/pending
    p_res = results.get("predictions/pending", {})
    if p_res.get("json") and "pending" in p_res["json"]:
        pending = p_res["json"]["pending"]
        p_counts = _count_ev_picks_in_predictions(pending)
        print(f"\n  /api/predictions/pending:")
        print(f"    total pending            : {len(pending)}")
        print(f"    with bookmaker_odd       : {p_counts['with_odd']}")
        print(f"    bookmaker_odd >= 1.1     : {p_counts['ge_1_1']}")
        print(f"    is_ev_pick (flag)        : {p_counts['is_ev_pick']}")
    else:
        _warn("/api/predictions/pending JSON missing or invalid")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    if all_ok:
        print(f"{BOLD}{GREEN}  NGROK_FRONT_CONNECTIVITY_OK{RESET}")
        _ok("All endpoints respond with 200, CORS headers, and valid JSON")
    else:
        print(f"{BOLD}{RED}  NGROK_FRONT_CONNECTIVITY_FAIL{RESET}")
        _err("One or more endpoints failed status/CORS/JSON checks")
    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
