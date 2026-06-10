"""
Test script for GLOBAL SCAN architecture + Odds API integration (Phase 13)
"""
import requests
import json

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("TESTING GLOBAL SCAN + ODDS API INTEGRATION")
print("=" * 60)

# Test 1: Health check
print("\n1. Testing /api/health...")
try:
    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Get matches (first scan can take 2-5 min while API-Football fetches data)
print("\n2. Testing /api/matches — first scan may take 2-5 min...")
all_matches = []
try:
    response = requests.get(f"{BASE_URL}/api/matches", timeout=360)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response keys: {list(data.keys())}")
    print(f"Stats: {data.get('stats', {})}")
    print(f"Total matches: {data.get('stats', {}).get('total_matches', 0)}")
    print(f"Targeted matches: {data.get('stats', {}).get('target_count', 0)}")
    print(f"Analyzed matches: {data.get('stats', {}).get('analyzed_count', 0)}")

    # Check categories
    categories = data.get('categories', {})
    print(f"\nCategories keys: {list(categories.keys())}")
    for cat_name, cat_matches in categories.items():
        print(f"  {cat_name}: {len(cat_matches)} matches")

    # Collect all matches from all categories
    for cat_matches in categories.values():
        all_matches.extend(cat_matches)

    if all_matches:
        print(f"\nSample leagues from first 5 matches:")
        for i, m in enumerate(all_matches[:5]):
            league = m.get('league', 'Unknown')
            country = m.get('country', 'Unknown')
            print(f"  {i+1}. {league} ({country})")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Check a specific match analysis
print("\n3. Testing /api/analyze_match (check signal categories)...")
if all_matches:
    match_id = all_matches[0].get('fixture_id')
    if match_id:
        try:
            response = requests.post(
                f"{BASE_URL}/api/analyze_match",
                json={"fixture_id": match_id},
                timeout=30
            )
            print(f"Status: {response.status_code}")
            data = response.json()

            # Check for signal_category
            top_angles = data.get('top_angles', [])
            print(f"\nTop angles count: {len(top_angles)}")
            for i, angle in enumerate(top_angles[:3]):
                print(f"  {i+1}. {angle.get('label')} - confidence: {angle.get('hit_rate')}%")

            # Check profile tags
            profile = data.get('match_profile', {})
            tags = profile.get('profile_tags', [])
            print(f"\nProfile tags: {tags}")

        except Exception as e:
            print(f"Error: {e}")

print("\n" + "=" * 60)
print("PHASE 13 — ODDS API INTEGRATION TEST")
print("=" * 60)

# Test 4: Diagnostics (Phase 12)
print("\n4. Testing /api/diagnostics (Phase 12) — reads cache, instant...")
try:
    resp = requests.get(f"{BASE_URL}/api/diagnostics", timeout=15)
    print(f"Status: {resp.status_code}")
    d = resp.json()
    print(f"  odds_api_key_present: {d.get('odds_api_key_present')}")
    print(f"  odds_api_status:      {d.get('odds_api_status')}")
    print(f"  odds_events_found:    {d.get('odds_events_found')}")
    print(f"  api_quota_remaining:  {d.get('api_quota_remaining')}")
    print(f"  total_fixtures:       {d.get('total_fixtures_scanned')}")
    print(f"  total_upcoming:       {d.get('total_upcoming')}")
    print(f"  total_live:           {d.get('total_live')}")
    print(f"  total_ev_detected:    {d.get('total_ev_detected')}")
    print(f"  s_tier:               {d.get('total_s_tier')}")
    print(f"  a_tier:               {d.get('total_a_tier')}")
    print(f"  watchlist:            {d.get('total_watchlist')}")
    print(f"  bookmakers_available: {d.get('bookmakers_available', [])[:5]}")
    print(f"  markets_available:    {d.get('markets_available', [])}")
except Exception as e:
    print(f"Error: {e}")

# Test 5: EV endpoint (Phase 7)
print("\n5. Testing /api/ev (Phase 7: EV calculation)...")
try:
    payload = {
        "model_probability": 0.78,
        "bookmaker_odd": 1.70,
        "market_type": "HT_UNDER_1_5",
        "line": 1.5,
        "sample_size": 22,
        "bookmaker": "Bet365",
    }
    resp = requests.post(f"{BASE_URL}/api/ev", json=payload, timeout=10)
    print(f"Status: {resp.status_code}")
    d = resp.json()
    ev = d.get("ev", {})
    print(f"  market:            {ev.get('market')}")
    print(f"  model_probability: {ev.get('model_probability')}")
    print(f"  bookmaker_odd:     {ev.get('bookmaker_odd')}")
    print(f"  implied_prob:      {ev.get('implied_probability')}%")
    print(f"  fair_odd:          {ev.get('fair_odd')}")
    print(f"  edge_percentage:   {ev.get('edge_percentage')}%")
    print(f"  ev_percentage:     {ev.get('ev_percentage')}%")
    print(f"  value_level:       {ev.get('value_level')}")
    print(f"  confidence:        {ev.get('confidence')}")
    print(f"  verdict:           {ev.get('verdict')}")
except Exception as e:
    print(f"Error: {e}")

# Test 6: Matches with tier_level (Phase 7+11)
print("\n6. Testing /api/matches tier_level + odds_status fields (Phase 7+11)...")
try:
    resp = requests.get(f"{BASE_URL}/api/matches?analyzed=true&limit=5", timeout=360)
    print(f"Status: {resp.status_code}")
    d = resp.json()
    matches = d.get("matches", [])
    print(f"  Matches returned: {len(matches)}")
    for i, m in enumerate(matches[:3]):
        print(f"\n  Match {i+1}: {m.get('home_team')} vs {m.get('away_team')}")
        print(f"    tier_level:               {m.get('tier_level')}")
        print(f"    ranking_score:            {m.get('ranking_score')}")
        print(f"    odds_status:              {m.get('odds_status')}")
        print(f"    waiting_for_odds:         {m.get('waiting_for_odds')}")
        print(f"    market_mapping_conf:      {m.get('market_mapping_confidence')}")
        print(f"    odds_count:               {m.get('odds_count')}")
        print(f"    statistical_interest:     {m.get('statistical_interest')}")
        ev_opps = m.get("ev_opportunities", [])
        print(f"    ev_opportunities:         {len(ev_opps)}")
        if ev_opps:
            best = ev_opps[0]
            print(f"      Best EV: {best.get('market')} EV={best.get('ev_percentage')}% value={best.get('value_level')}")
except Exception as e:
    print(f"Error: {e}")

# Test 7: Backtest (Phase 8)
print("\n7. Testing /api/backtest (Phase 8)...")
try:
    resp = requests.get(f"{BASE_URL}/api/backtest", timeout=60)
    print(f"Status: {resp.status_code}")
    d = resp.json()
    print(f"  total_records: {d.get('total_records')}")
    print(f"  total_markets: {d.get('total_markets')}")
    summaries = d.get("summaries", {})
    if summaries:
        top3 = list(summaries.items())[:3]
        for mkt, s in top3:
            print(f"  {mkt}: hit={s.get('hit_rate_pct')}% roi={s.get('simulated_roi')}%")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
