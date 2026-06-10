#!/usr/bin/env python3
"""
Vérification des matchs obscures dans l'API Flask
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def check_obscure_api():
    """Vérifie les matchs obscures dans l'API"""
    
    print("🔍 VÉRIFICATION MATCHS OBSCURES DANS L'API")
    print("=" * 50)
    
    try:
        # Récupérer les matches depuis l'API
        response = requests.get("http://127.0.0.1:5000/api/matches?limit=50", timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            
            print(f"✅ {len(matches)} matches récupérés depuis l'API")
            
            # Chercher les matchs obscures
            obscure_countries = ["Latvia", "Estonia", "Lithuania", "Belarus", "Georgia", "Kyrgyzstan", "Bhutan"]
            obscure_matches = []
            visible_obscure = []
            
            for match in matches:
                country = match.get("country", "").lower()
                competition = match.get("competition", "").lower()
                home_team = match.get("home_team", "").lower()
                away_team = match.get("away_team", "").lower()
                
                # Vérifier si c'est un match obscur
                is_obscure = any(
                    obs_country.lower() in country or 
                    obs_country.lower() in competition
                    for obs_country in obscure_countries
                )
                
                if is_obscure:
                    obscure_matches.append(match)
                    
                    # Vérifier si visible (analysé ou en attente)
                    if match.get("analyzed", False) or match.get("status", "").upper() in ["UPCOMING", "NS", "LIVE", "IN_PLAY", "PAUSED"]:
                        visible_obscure.append(match)
            
            print(f"\n🇱🇻 MATCHS OBSCURES DANS L'API: {len(obscure_matches)}")
            print(f"👁️ MATCHS OBSCURES VISIBLES: {len(visible_obscure)}")
            
            if visible_obscure:
                print(f"\n📋 MATCHS OBSCURES VISIBLES SUR FRONT:")
                for i, match in enumerate(visible_obscure, 1):
                    home = match.get("home_team", "Unknown")
                    away = match.get("away_team", "Unknown")
                    comp = match.get("competition", "Unknown")
                    country = match.get("country", "Unknown")
                    status = match.get("status", "Unknown")
                    analyzed = match.get("analyzed", False)
                    
                    print(f"   {i}. {home} vs {away}")
                    print(f"      🏆 {comp} ({country})")
                    print(f"      📊 {status} {'✅ Analysé' if analyzed else '⏳ En attente'}")
                    
                    # Afficher les profils si disponibles
                    profile_tags = match.get("profile_tags", [])
                    if profile_tags:
                        print(f"      🎯 Profils: {', '.join(profile_tags)}")
                    
                    print()
            else:
                print(f"\n❌ AUCUN MATCH OBSCURE VISIBLE SUR LE FRONT")
                
                # Afficher les matchs obscures trouvés mais cachés
                if obscure_matches:
                    print(f"\n🚫 MATCHS OBSCURES CACHÉS (FINISHED):")
                    for match in obscure_matches[:5]:  # Limiter à 5
                        home = match.get("home_team", "Unknown")
                        away = match.get("away_team", "Unknown")
                        comp = match.get("competition", "Unknown")
                        status = match.get("status", "Unknown")
                        
                        print(f"   - {home} vs {away} ({comp}) - {status}")
            
            # Vérifier le status breakdown
            status_breakdown = data.get("status_breakdown", {})
            if status_breakdown:
                print(f"\n📊 STATUS BREAKDOWN:")
                for status, count in status_breakdown.items():
                    print(f"   - {status}: {count}")
            
            # Vérifier les catégories
            categories = data.get("categories", {})
            if categories:
                print(f"\n📂 CATÉGORIES DISPONIBLES:")
                for category, matches in categories.items():
                    print(f"   - {category}: {len(matches)} matchs")
            
            return len(visible_obscure) > 0
            
        else:
            print(f"❌ Erreur API: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    has_visible_obscure = check_obscure_api()
    if has_visible_obscure:
        print("\n🎉 DES MATCHS OBSCURES SONT VISIBLES SUR LE FRONT!")
    else:
        print("\n❌ PAS DE MATCHS OBSCURES VISIBLES SUR LE FRONT")
    
    sys.exit(0 if has_visible_obscure else 1)
