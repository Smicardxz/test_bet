import urllib.request
import json

BASE = "http://127.0.0.1:5000"

def get(path, timeout=30):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def post(path, body, timeout=30):
    req = urllib.request.Request(BASE + path, method="POST")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

# 1. Matches (triggers scan on first call)
print("1. GET /api/matches?limit=1")
data = get("/api/matches?limit=1", timeout=120)
print(f"   Total: {data['total']}, Match: {data['matches'][0]['home_team']} vs {data['matches'][0]['away_team']}")

# 2. Dashboard summary
print("2. GET /api/dashboard/summary")
data = get("/api/dashboard/summary", timeout=30)
print(f"   Total:{data['total_matches']} Analyzed:{data['analyzed_matches']} Opportunities:{data['opportunities_count']}")

# 3. Leagues coverage
print("3. GET /api/leagues/coverage")
data = get("/api/leagues/coverage", timeout=30)
print(f"   Countries:{len(data['countries'])} Leagues:{data['total_leagues']}")

# 4. Analyze match
m = get("/api/matches?limit=1", timeout=30)["matches"][0]
print(f"4. POST /api/analyze_match for {m['fixture_id']}")
data = post("/api/analyze_match", {
    "fixture_id": m["fixture_id"],
    "home_team_id": m["home_team_id"],
    "away_team_id": m["away_team_id"],
    "home_team_name": m["home_team"],
    "away_team_name": m["away_team"]
}, timeout=120)
print(f"   Status:{data['analysis_status']} Origin:{data['data_origin']} Angles:{len(data['top_angles'])}")

# 5. Filtered matches
print("5. GET /api/matches?status=upcoming&analyzed=true&limit=2")
data = get("/api/matches?status=upcoming&analyzed=true&limit=2", timeout=30)
print(f"   Filtered: {data['returned']}/{data['total']} upcoming analyzed matches")

print("\nAll endpoints validated!")
