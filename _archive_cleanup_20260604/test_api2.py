"""Test API /api/data response - Check inefficiencies"""
import requests
import json

try:
    print("[TEST] Calling /api/data...")
    response = requests.get('http://localhost:5000/api/data', timeout=120)
    
    if response.status_code == 200:
        data = response.json()
        
        # Check inefficiencies
        inefficiencies = data.get('categories', {}).get('upcoming_inefficiencies', [])
        print(f"[TEST] Inefficiencies matches: {len(inefficiencies)}")
        
        if len(inefficiencies) > 0:
            match = inefficiencies[0]
            print(f"\n[TEST] First inefficiency match:")
            print(f"  - Home: {match.get('home_team')}")
            print(f"  - Away: {match.get('away_team')}")
            print(f"  - Has match_profile: {'match_profile' in match}")
            print(f"  - Has best_edges: {'best_edges' in match}")
            print(f"  - Has edge_detection: {'edge_detection' in match}")
            
            if 'match_profile' in match:
                profile = match['match_profile']
                print(f"\n  [PROFILE]")
                print(f"    - Type: {type(profile)}")
                print(f"    - Keys: {list(profile.keys()) if isinstance(profile, dict) else 'NOT A DICT'}")
                if isinstance(profile, dict):
                    print(f"    - Tempo: {profile.get('tempo_profile')}")
                    print(f"    - Scoring: {profile.get('scoring_profile')}")
                    print(f"    - Specific: {profile.get('specific_profiles')}")
                    print(f"    - Statistical: {profile.get('statistical_angles')}")
                    print(f"    - Interest: {profile.get('interest_score')}")
            
            if 'best_edges' in match:
                edges = match['best_edges']
                print(f"\n  [EDGES]")
                print(f"    - Count: {len(edges) if isinstance(edges, list) else 'NOT A LIST'}")
                if isinstance(edges, list) and len(edges) > 0:
                    edge = edges[0]
                    print(f"    - Market: {edge.get('market')}")
                    print(f"    - Edge %: {edge.get('edge_percent')}")
        
except Exception as e:
    print(f"[TEST] Exception: {e}")
    import traceback
    traceback.print_exc()
