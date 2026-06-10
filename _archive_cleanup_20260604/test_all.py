import urllib.request
import json

BASE = "http://127.0.0.1:5000"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read().decode())

# 1. Warm cache
print("1. Warming cache with /api/matches?limit=1...")
d = get("/api/matches?limit=1")
print(f"   Matches total: {d['total']}")

# 2. Dashboard (cache is warm)
print("2. GET /api/dashboard/summary")
d = get("/api/dashboard/summary")
print(f"   Total:{d['total_matches']} Analyzed:{d['analyzed_matches']} Opportunities:{d['opportunities_count']}")

# 3. Leagues
print("3. GET /api/leagues/coverage")
d = get("/api/leagues/coverage")
print(f"   Countries:{len(d['countries'])} Leagues:{d['total_leagues']}")

# 4. Filtered matches
print("4. GET /api/matches?status=upcoming&analyzed=true&limit=2")
d = get("/api/matches?status=upcoming&analyzed=true&limit=2")
print(f"   Upcoming analyzed: {d['returned']}")

# 5. Analyze
m = get("/api/matches?limit=1")["matches"][0]
print(f"5. POST /api/analyze_match for {m['fixture_id']}")
req = urllib.request.Request(
    BASE + "/api/analyze_match",
    method="POST",
    data=json.dumps({
        "fixture_id": m["fixture_id"],
        "home_team_id": m["home_team_id"],
        "away_team_id": m["away_team_id"],
        "home_team_name": m["home_team"],
        "away_team_name": m["away_team"]
    }).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=120) as r:
    d = json.loads(r.read().decode())
print(f"   Status:{d['analysis_status']} Origin:{d['data_origin']} Angles:{len(d['top_angles'])}")

print("\nALL ENDPOINTS VALIDATED SUCCESSFULLY")
