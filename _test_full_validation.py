"""
Full validation: odds_events_found, mapping, tiers, EV, upcoming priority
"""
import requests, json, time

BASE = "http://localhost:5000"

def check(label, condition, detail=""):
    icon = "OK" if condition else "FAIL"
    print(f"  [{icon}] {label}" + (f" — {detail}" if detail else ""))
    return condition

print("=" * 60)
print("VALIDATION COMPLETE — Phase 13")
print("=" * 60)

# 1. Health
print("\n[1] /api/health")
r = requests.get(f"{BASE}/api/health", timeout=10)
d = r.json()
check("status=healthy", d.get("status") == "healthy")

# 2. Trigger scan — poll until ready (async background scan)
print("\n[2] /api/data — triggering scan (async, poll until ready)...")
t0 = time.time()
d = {}
for attempt in range(40):  # up to 200s
    try:
        r = requests.get(f"{BASE}/api/data", timeout=15)
        d = r.json()
        err = d.get("error", "") or (d.get("scan_result", {}) or {}).get("error", "")
        analyzed = d.get("stats", {}).get("analyzed_count", 0) or 0
        if d.get("success") or analyzed > 0:
            break
        if "scan_in_progress" in str(err) or not d.get("success"):
            print(f"  [{attempt+1}] waiting (scan running)... {err or 'no data yet'}")
            time.sleep(5)
            continue
        break
    except Exception as e:
        print(f"  [{attempt+1}] error: {e}")
        time.sleep(5)
elapsed = time.time() - t0
stats = d.get("stats", {})
print(f"  Done in {elapsed:.0f}s")
check("success=True", d.get("success"), str(d.get("stats", {})))
total = stats.get("total_matches", 0)
analyzed = stats.get("analyzed_count", 0)
check("total_matches > 0", total > 0, f"total={total}")
check("analyzed_count > 0", analyzed > 0, f"analyzed={analyzed}")

# 3. Diagnostics
print("\n[3] /api/diagnostics")
r = requests.get(f"{BASE}/api/diagnostics", timeout=15)
d = r.json()
check("success", d.get("success"))
check("odds_api_key_present", d.get("odds_api_key_present"), d.get("odds_api_status"))
events = d.get("odds_events_found", 0)
check("odds_events_found > 0", events > 0, f"events={events}")
check("quota_remaining not None", d.get("api_quota_remaining") is not None, str(d.get("api_quota_remaining")))
sports = d.get("sports_loaded", 0) or len(d.get("bookmakers_available", []))
s_tier = d.get("total_s_tier", 0)
a_tier = d.get("total_a_tier", 0)
watchlist = d.get("total_watchlist", 0)
ev_detected = d.get("total_ev_detected", 0)
print(f"  odds_events_found:  {events}")
print(f"  quota_remaining:    {d.get('api_quota_remaining')}")
print(f"  bookmakers:         {d.get('bookmakers_available', [])[:5]}")
print(f"  markets:            {d.get('markets_available', [])}")
print(f"  S_TIER: {s_tier}  A_TIER: {a_tier}  WATCHLIST: {watchlist}  EV: {ev_detected}")

# 4. EV calculation
print("\n[4] /api/ev — EV calculation")
r = requests.post(f"{BASE}/api/ev", json={
    "model_probability": 0.75,
    "bookmaker_odd": 1.80,
    "market_type": "FT_UNDER_2_5",
    "line": 2.5,
    "sample_size": 18,
    "bookmaker": "Betsson"
}, timeout=10)
ev = r.json().get("ev", {})
check("ev_percentage present", ev.get("ev_percentage") is not None, str(ev.get("ev_percentage")))
check("value_level present", ev.get("value_level") is not None, ev.get("value_level"))
check("confidence present", ev.get("confidence") is not None, ev.get("confidence"))
check("EV > 0 (0.75*1.80-1=0.35)", ev.get("ev_percentage", 0) > 0, f"{ev.get('ev_percentage')}%")

# 5. Matches with Phase 11 fields
print("\n[5] /api/matches — Phase 11 fields")
r = requests.get(f"{BASE}/api/matches", timeout=30)
d = r.json()
matches = d.get("matches", [])
# Flatten categories if needed
if not matches:
    cats = d.get("categories", {})
    for v in cats.values():
        matches.extend(v)

check("matches returned", len(matches) > 0, f"{len(matches)} matches")

upcoming_first = None
finished_in_tier = False
ev_non_empty = False
for m in matches:
    if m.get("status") == "UPCOMING" and upcoming_first is None:
        upcoming_first = m
    tier = m.get("tier_level", "")
    if tier in ("S_TIER", "A_TIER") and m.get("status") == "FINISHED":
        finished_in_tier = True
    if m.get("ev_opportunities"):
        ev_non_empty = True

check("UPCOMING matches prioritized first", upcoming_first is not None)
check("No FINISHED in S/A-TIER", not finished_in_tier)

# Show first 3 matches with key fields
for m in matches[:3]:
    print(f"\n  {m.get('home_team')} vs {m.get('away_team')} [{m.get('status')}]")
    print(f"    tier_level:           {m.get('tier_level')}")
    print(f"    ranking_score:        {m.get('ranking_score')}")
    print(f"    odds_status:          {m.get('odds_status')}")
    print(f"    waiting_for_odds:     {m.get('waiting_for_odds')}")
    print(f"    odds_count:           {m.get('odds_count')}")
    print(f"    mapping_confidence:   {m.get('market_mapping_confidence')}")
    print(f"    statistical_interest: {m.get('statistical_interest')}")
    evs = m.get("ev_opportunities", [])
    print(f"    ev_opportunities:     {len(evs)}")
    if evs:
        best = evs[0]
        print(f"      Best: {best.get('market')} EV={best.get('ev_percentage')}% val={best.get('value_level')} bk={best.get('bookmaker')}")

# EV audit
print("\n[6] EV AUDIT — checking for inflated values")
suspicious = []
for m in matches:
    for ev in m.get("ev_opportunities", []):
        ev_pct = ev.get("ev_percentage", 0) or 0
        prob = ev.get("model_probability", 0) or 0
        odd = ev.get("bookmaker_odd", 0) or 0
        if ev_pct > 50:
            suspicious.append(f"{m.get('home_team')} vs {m.get('away_team')}: {ev.get('market')} EV={ev_pct}% prob={prob} odd={odd}")

check("No EV > 50% (inflation guard)", len(suspicious) == 0,
      f"{len(suspicious)} suspicious" if suspicious else "clean")
for s in suspicious[:3]:
    print(f"    SUSPICIOUS: {s}")

print("\n" + "=" * 60)
print("VALIDATION DONE")
print("=" * 60)
