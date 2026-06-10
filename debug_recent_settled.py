"""
debug_recent_settled.py
=======================
Debug recent_settled to check why only 1 match is showing.
"""

import requests

def main():
    print(f"\n{'='*66}")
    print(f"  DEBUGGING RECENT_SETTLED")
    print(f"{'='*66}")
    
    try:
        response = requests.get("http://localhost:5000/api/shadow-lab", timeout=10)
        if response.status_code != 200:
            print(f"ERROR: HTTP {response.status_code}")
            return
        
        data = response.json()
        recent_settled = data.get("recent_settled", [])
        
        print(f"\nRecent settled count: {len(recent_settled)}")
        
        if not recent_settled:
            print("No recent settled predictions found")
            return
        
        print(f"\n{'Home':20s} {'Away':20s} {'Market':20s} {'Result':10s} {'BetIQ':8s} {'Shadow':8s}")
        print(f"{'-'*86}")
        
        for item in recent_settled:
            home = item.get("home_team", "")[:20]
            away = item.get("away_team", "")[:20]
            market = item.get("market", "")[:20]
            result = item.get("result", "")[:10]
            betiq = "YES" if item.get("betiq_taken") else "NO"
            shadow = "YES" if item.get("shadow_taken") else "NO"
            print(f"{home:20s} {away:20s} {market:20s} {result:10s} {betiq:8s} {shadow:8s}")
        
        # Check if filtering is happening on front end
        battles = [r for r in recent_settled if r.get("betiq_taken") != r.get("shadow_taken")]
        print(f"\nBattles (BetIQ != Shadow): {len(battles)}")
        
        print(f"\n{'='*66}\n")
        
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
