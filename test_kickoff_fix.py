"""
test_kickoff_fix.py
===================
Test if kickoff_time is now correct in today_comparison.
"""

import requests
import json

def main():
    print(f"\n{'='*66}")
    print(f"  TESTING KICKOFF TIME FIX")
    print(f"{'='*66}")
    
    try:
        response = requests.get("http://localhost:5000/api/shadow-lab", timeout=10)
        if response.status_code != 200:
            print(f"ERROR: HTTP {response.status_code}")
            return
        
        data = response.json()
        today_comparison = data.get("today_comparison", [])
        
        print(f"\nToday comparison: {len(today_comparison)} items")
        print(f"\n{'Home':20s} {'Away':20s} {'kickoff_time':30s}")
        print(f"{'-'*70}")
        
        for item in today_comparison[:10]:
            home = item.get("home_team", "")[:20]
            away = item.get("away_team", "")[:20]
            kickoff = item.get("kickoff_time", "")
            print(f"{home:20s} {away:20s} {str(kickoff):30s}")
        
        # Check if all are the same (the bug)
        kickoff_times = [item.get("kickoff_time") for item in today_comparison]
        unique_times = set(kickoff_times)
        
        print(f"\nUnique kickoff times: {len(unique_times)}")
        if len(unique_times) == 1:
            print(f"WARNING: All items have same kickoff time: {list(unique_times)[0]}")
        else:
            print(f"OK: Multiple kickoff times found")
        
        print(f"\n{'='*66}\n")
        
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
