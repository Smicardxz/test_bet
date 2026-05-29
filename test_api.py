"""Test API /api/data response"""
import requests
import json

try:
    print("[TEST] Calling /api/data...")
    response = requests.get('http://localhost:5000/api/data', timeout=120)
    
    print(f"[TEST] Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"[TEST] Success: {data.get('success')}")
        print(f"[TEST] Categories keys: {list(data.get('categories', {}).keys())}")
        
        # Check statistical matches
        statistical = data.get('categories', {}).get('upcoming_statistical', [])
        print(f"[TEST] Statistical matches: {len(statistical)}")
        
        if len(statistical) > 0:
            match = statistical[0]
            print(f"\n[TEST] First match:")
            print(f"  - Home: {match.get('home_team')}")
            print(f"  - Away: {match.get('away_team')}")
            print(f"  - Has match_profile: {match.get('match_profile') is not None}")
            
            if match.get('match_profile'):
                profile = match['match_profile']
                print(f"  - Profile keys: {list(profile.keys())}")
                print(f"  - Tempo: {profile.get('tempo_profile')}")
                print(f"  - Scoring: {profile.get('scoring_profile')}")
                print(f"  - Specific profiles: {profile.get('specific_profiles')}")
                print(f"  - Statistical angles: {profile.get('statistical_angles')}")
        
        # Check inefficiencies
        inefficiencies = data.get('categories', {}).get('upcoming_inefficiencies', [])
        print(f"\n[TEST] Inefficiencies matches: {len(inefficiencies)}")
        
    else:
        print(f"[TEST] Error: {response.text}")
        
except Exception as e:
    print(f"[TEST] Exception: {e}")
    import traceback
    traceback.print_exc()
