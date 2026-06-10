#!/usr/bin/env python3
"""
Test de l'endpoint /api/analyze_match corrigé
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_analyze_endpoint():
    """Test l'endpoint /api/analyze_match"""
    
    print("🔍 TEST ENDPOINT /api/analyze_match")
    print("=" * 50)
    
    try:
        # D'abord récupérer quelques matches pour avoir un fixture_id
        print("1. Récupération des matches...")
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=5", timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Erreur récupération matches: {response.status_code}")
            return False
        
        data = response.json()
        matches = data.get("matches", [])
        
        if not matches:
            print("❌ Aucun match trouvé")
            return False
        
        # Prendre le premier match
        first_match = matches[0]
        fixture_id = first_match.get("fixture_id")
        
        if not fixture_id:
            print("❌ Aucun fixture_id trouvé")
            return False
        
        print(f"✅ Match trouvé: {first_match.get('home_team')} vs {first_match.get('away_team')}")
        print(f"   Fixture ID: {fixture_id}")
        print(f"   Status actuel: {first_match.get('analysis_status', 'Unknown')}")
        
        # Tester l'endpoint d'analyse
        print(f"\n2. Test /api/analyze_match...")
        
        analyze_payload = {
            "fixture_id": fixture_id
        }
        
        response = requests.post(
            "http://127.0.0.1:5000/api/analyze_match",
            json=analyze_payload,
            timeout=20
        )
        
        print(f"   Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Endpoint répond correctement")
            print(f"   Success: {result.get('success')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Message: {result.get('message')}")
            
            # Vérifier les champs V2
            if result.get("success"):
                v2_fields = ["interest_score", "confidence_score", "volatility_score", "data_quality_score"]
                has_v2 = any(field in result for field in v2_fields)
                
                if has_v2:
                    print("✅ Champs V2 présents")
                    for field in v2_fields:
                        value = result.get(field, "N/A")
                        print(f"   - {field}: {value}")
                else:
                    print("ℹ️  Pas de champs V2 (match peut être PENDING)")
                
                # Vérifier les données du match
                match_data = result.get("match_data", {})
                if match_data:
                    print(f"✅ Données match présentes: {match_data.get('home_team')} vs {match_data.get('away_team')}")
                
                # Vérifier l'analyse
                analysis = result.get("analysis", {})
                if analysis:
                    print("✅ Analyse présente")
                    best_pick = analysis.get("best_pick", {})
                    if best_pick:
                        print(f"   Best pick: {best_pick.get('market', 'N/A')}")
            
            return True
            
        else:
            print(f"❌ Erreur endpoint: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Erreur: {error_data.get('error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_analyze_endpoint()
    if success:
        print("\n🎉 ENDPOINT /api/analyze_match FONCTIONNE!")
    else:
        print("\n❌ ENDPOINT /api/analyze_match ÉCHOUÉ")
    
    sys.exit(0 if success else 1)
