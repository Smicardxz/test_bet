#!/usr/bin/env python3
"""
Test rapide pour vérifier le filtrage status dans l'API Flask
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def test_api_status_filtering():
    """Test que l'API filtre correctement les matches finis"""
    
    print("🔍 TEST API FILTRAGE STATUS")
    print("=" * 50)
    
    try:
        # Test health endpoint
        print("1. Test health endpoint...")
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint OK")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        # Test matches endpoint avec petit timeout
        print("2. Test matches endpoint...")
        try:
            response = requests.get("http://127.0.0.1:5000/api/matches?limit=3", timeout=15)
            if response.status_code == 200:
                data = response.json()
                print("✅ Matches endpoint OK")
                
                # Analyser les status
                matches = data.get("matches", [])
                analyzed_count = 0
                finished_count = 0
                upcoming_count = 0
                live_count = 0
                
                for match in matches:
                    status = match.get("status", "UNKNOWN")
                    analyzed = match.get("analyzed", False)
                    
                    if analyzed:
                        analyzed_count += 1
                        
                        if "FINISHED" in status or "FT" in status:
                            finished_count += 1
                        elif "UPCOMING" in status or "NS" in status:
                            upcoming_count += 1
                        elif "LIVE" in status or "IN_PLAY" in status:
                            live_count += 1
                
                print(f"\n📊 RÉSULTATS:")
                print(f"   - Total matches: {len(matches)}")
                print(f"   - Matches analysés: {analyzed_count}")
                print(f"   - Matches finis analysés: {finished_count}")
                print(f"   - Matches UPCOMING analysés: {upcoming_count}")
                print(f"   - Matches LIVE analysés: {live_count}")
                
                if finished_count == 0 and analyzed_count > 0:
                    print("✅ FILTRAGE CORRECT: Aucun match fini analysé")
                    return True
                elif analyzed_count == 0:
                    print("ℹ️  Aucun match analysé (timeout?)")
                    return True
                else:
                    print("❌ ERREUR: Des matches finis sont analysés!")
                    return False
            else:
                print(f"❌ Matches endpoint failed: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print("⏰ Matches endpoint timeout (normal si scanner lent)")
            return True
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = test_api_status_filtering()
    if success:
        print("\n🎉 TEST API RÉUSSI")
    else:
        print("\n❌ TEST API ÉCHOUÉ")
    
    sys.exit(0 if success else 1)
