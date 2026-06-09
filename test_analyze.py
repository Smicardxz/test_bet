import urllib.request
import json

BASE = "http://127.0.0.1:5000"

# Warm cache + get match ID in one call
with urllib.request.urlopen(BASE + "/api/matches?limit=1", timeout=120) as r:
    d = json.loads(r.read().decode())

m = d["matches"][0]
print(f"Match: {m['home_team']} vs {m['away_team']} (ID: {m['fixture_id']})")

# POST analyze immediately (cache still warm)
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

print(f"Status: {d['analysis_status']}")
print(f"Origin: {d['data_origin']}")
print(f"Profile tags: {d['match_profile']['profile_tags']}")
print(f"Summary: {d['match_profile']['summary']}")
print(f"Top angles: {len(d['top_angles'])}")
print(f"HT rows: {len(d['ht_analysis'])}")
print(f"FT rows: {len(d['ft_analysis'])}")
print(f"Recent history: {len(d['recent_history'])}")
print(f"Warnings: {d['warnings']}")
print(f"Errors: {d['errors']}")
print("\nPOST /api/analyze_match OK")
