"""
Test script for Lovable API endpoints.
Run this while Flask is running on localhost:5000.
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:5000"

def call(method, path, body=None, timeout=30):
    url = BASE + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if body:
        req.data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, resp.status
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except:
            data = {"error": str(e)}
        return data, e.code
    except Exception as e:
        return {"error": str(e)}, 0

def check_keys(obj, keys, label):
    missing = [k for k in keys if k not in obj]
    if missing:
        print(f"  ❌ {label} MISSING keys: {missing}")
        return False
    print(f"  ✅ {label} keys OK")
    return True

print("=" * 60)
print(" LOVABLE API CONTRACT TEST")
print("=" * 60)

# 1. Health (instant)
print("\n1. GET /api/health")
data, status = call("GET", "/api/health", timeout=5)
if status == 200 and data.get("status") == "healthy":
    print(f"  ✅ Status: {data['status']}, Version: {data.get('version')}")
    check_keys(data, ["status", "timestamp", "version", "data_source", "cache_age_seconds", "cache_active", "endpoints"], "Health")
else:
    print(f"  ❌ Failed: {data}")
    sys.exit(1)

# 2. Matches — first call triggers scan, use long timeout
print("\n2. GET /api/matches?limit=3 (first call = scan + cache)")
print("   ⏳ This may take 30-60 seconds on first load...")
data, status = call("GET", "/api/matches?limit=3", timeout=120)
if status == 200 and data.get("success"):
    total = data.get("total", 0)
    returned = data.get("returned", 0)
    matches = data.get("matches", [])
    print(f"  ✅ Total: {total}, Returned: {returned}")
    check_keys(data, ["success", "total", "returned", "offset", "limit", "matches"], "Matches response")
    if matches:
        m = matches[0]
        check_keys(m, ["fixture_id", "home_team", "away_team", "country", "league",
                       "kickoff_time", "status", "target_type", "profile_tags",
                       "best_angle", "interest_score", "confidence_score",
                       "volatility_score", "data_quality", "analyzed", "has_profile"], "Match object")
        if "best_angle" in m:
            check_keys(m["best_angle"], ["market", "label", "confidence", "fair_odd",
                                         "market_odd", "sample_size", "status", "edge_percent"], "BestAngle")
    # Show first match summary
    if matches:
        m = matches[0]
        print(f"   📋 Sample: {m['home_team']} vs {m['away_team']} | Interest:{m['interest_score']} Conf:{m['confidence_score']} Quality:{m['data_quality']}")
else:
    print(f"  ❌ Failed: {data}")

# 3. Dashboard summary (should be instant now — cache is warm)
print("\n3. GET /api/dashboard/summary")
data, status = call("GET", "/api/dashboard/summary", timeout=15)
if status == 200 and data.get("success"):
    print(f"  ✅ Total:{data['total_matches']} Analyzed:{data['analyzed_matches']} Opportunities:{data['opportunities_count']}")
    check_keys(data, ["success", "total_matches", "target_matches", "analyzed_matches",
                     "awaiting_matches", "live_matches", "finished_matches",
                     "opportunities_count", "data_source", "last_refresh", "is_real_data"], "Summary")
else:
    print(f"  ❌ Failed: {data}")

# 4. Leagues coverage
print("\n4. GET /api/leagues/coverage")
data, status = call("GET", "/api/leagues/coverage", timeout=15)
if status == 200 and data.get("success"):
    countries = data.get("countries", [])
    print(f"  ✅ Countries: {len(countries)}, Total leagues: {data.get('total_leagues')}")
    check_keys(data, ["success", "countries", "total_leagues", "total_matches"], "Coverage")
    if countries:
        check_keys(countries[0], ["country", "leagues", "league_count", "matches_today",
                                  "analyzed_count", "coverage_level", "target_type"], "Country")
else:
    print(f"  ❌ Failed: {data}")

# 5. Analyze match — pick first match from cache if available
print("\n5. POST /api/analyze_match")
# We need a fixture_id, home_team_id, away_team_id. Use from matches if available.
fixture_id = None
home_team_id = None
away_team_id = None
home_team_name = ""
away_team_name = ""

# Try to get from the earlier matches call
matches_data, _ = call("GET", "/api/matches?limit=1", timeout=15)
if matches_data.get("success") and matches_data.get("matches"):
    m = matches_data["matches"][0]
    fixture_id = m.get("fixture_id")
    home_team_id = m.get("home_team_id")
    away_team_id = m.get("away_team_id")
    home_team_name = m.get("home_team", "")
    away_team_name = m.get("away_team", "")

if fixture_id and home_team_id and away_team_id:
    body = {
        "fixture_id": fixture_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_team_name": home_team_name,
        "away_team_name": away_team_name
    }
    data, status = call("POST", "/api/analyze_match", body=body, timeout=90)
    if status == 200:
        print(f"  ✅ Status: {data.get('analysis_status')}, Origin: {data.get('data_origin')}")
        check_keys(data, ["fixture_id", "data_origin", "analysis_status", "match_profile",
                         "top_angles", "ht_analysis", "ft_analysis", "recent_history",
                         "h2h", "warnings", "errors"], "Analyze response")
        if "match_profile" in data:
            check_keys(data["match_profile"], ["profile_tags", "interest_score", "confidence_score",
                                              "volatility_score", "sample_size", "summary"], "MatchProfile")
        if data.get("top_angles"):
            check_keys(data["top_angles"][0], ["market", "label", "hit_rate", "fair_odd",
                                                "sample_size", "confidence", "edge_percent", "why"], "TopAngle")
    else:
        print(f"  ❌ Failed: {data}")
else:
    print("  ⚠️  No match IDs available to test analyze_match")

# 6. Filters test
print("\n6. GET /api/matches?status=upcoming&analyzed=true&limit=2")
data, status = call("GET", "/api/matches?status=upcoming&analyzed=true&limit=2", timeout=15)
if status == 200 and data.get("success"):
    print(f"  ✅ Filtered: {data['returned']}/{data['total']} upcoming analyzed matches")
else:
    print(f"  ❌ Failed: {data}")

print("\n" + "=" * 60)
print(" TEST COMPLETE")
print("=" * 60)
