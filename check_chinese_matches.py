#!/usr/bin/env python3
"""
Vérification des matchs chinois dans le système
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.scanner.smart_scanner import SmartScanner
from app.providers.data_source_manager import DataSourceManager

def check_chinese_matches():
    """Vérifie si des matchs chinois sont présents"""
    
    print("🔍 VÉRIFICATION MATCHS CHINOIS")
    print("=" * 50)
    
    try:
        # Initialiser le scanner
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            max_analysis=20  # Augmenté pour voir plus de matches
        )
        
        print(f"✅ Scanner initialisé (real_data: {manager.is_real_data})")
        
        # Lancer le scan
        print("📊 Lancement du scan...")
        result = scanner.scan_today()
        
        if result["success"]:
            print(f"✅ Scan réussi")
            print(f"   - Total matches: {result['total_matches']}")
            print(f"   - Target matches: {result['target_count']}")
            print(f"   - Analyzed matches: {result['analyzed_count']}")
            
            # Chercher les matchs chinois
            chinese_matches = []
            all_matches = []
            
            # Analyser les matches analysés
            for match in result["analyzed_matches"]:
                match_data = match["match_data"]
                all_matches.append(match_data)
                
                # Vérifier si c'est un match chinois
                country = match_data.get("country", "").lower()
                competition = match_data.get("competition", "").lower()
                home_team = match_data.get("home_team", "").lower()
                away_team = match_data.get("away_team", "").lower()
                
                if ("china" in country or "chinese" in country or 
                    "china" in competition or "chinese" in competition or
                    "china" in home_team or "chinese" in home_team or
                    "china" in away_team or "chinese" in away_team):
                    chinese_matches.append(match_data)
            
            # Analyser les matches non analysés
            for match in result["remaining_matches"]:
                match_data = match["match_data"]
                all_matches.append(match_data)
                
                # Vérifier si c'est un match chinois
                country = match_data.get("country", "").lower()
                competition = match_data.get("competition", "").lower()
                home_team = match_data.get("home_team", "").lower()
                away_team = match_data.get("away_team", "").lower()
                
                if ("china" in country or "chinese" in country or 
                    "china" in competition or "chinese" in competition or
                    "china" in home_team or "chinese" in home_team or
                    "china" in away_team or "chinese" in away_team):
                    chinese_matches.append(match_data)
            
            print(f"\n🇨🇳 MATCHS CHINOIS TROUVÉS: {len(chinese_matches)}")
            
            if chinese_matches:
                print("\n📋 DÉTAILS DES MATCHS CHINOIS:")
                for i, match in enumerate(chinese_matches, 1):
                    print(f"\n{i}. {match.get('home_team', 'Unknown')} vs {match.get('away_team', 'Unknown')}")
                    print(f"   🏆 Compétition: {match.get('competition', 'Unknown')}")
                    print(f"   🌍 Pays: {match.get('country', 'Unknown')}")
                    print(f"   ⏰ Heure: {match.get('time_display', 'Unknown')}")
                    print(f"   📊 Status: {match.get('status', 'Unknown')}")
                    print(f"   🎯 Analysé: {'Oui' if match in [m['match_data'] for m in result['analyzed_matches']] else 'Non'}")
            else:
                print("\n❌ AUCUN MATCH CHINOIS TROUVÉ")
                
                # Afficher tous les pays disponibles pour diagnostic
                countries = set()
                for match in all_matches:
                    country = match.get("country", "Unknown")
                    if country and country != "Unknown":
                        countries.add(country)
                
                print(f"\n🌍 PAYS DISPONIBLES ({len(countries)}):")
                for country in sorted(list(countries))[:20]:  # Limiter à 20 pour la lisibilité
                    print(f"   - {country}")
                if len(countries) > 20:
                    print(f"   ... et {len(countries) - 20} autres")
            
            # Vérifier le targeting pour la Chine
            print(f"\n🎯 TEST TARGETING CHINE:")
            from app.services.targeting.league_targeting_service import LeagueTargetingService
            
            targeting = LeagueTargetingService()
            
            # Test avec une ligue chinoise
            profile_china = targeting.analyze_competition(
                competition_name="Chinese Super League",
                country="China"
            )
            
            print(f"   - Chinese Super League score: {profile_china.target_score}")
            print(f"   - Target level: {profile_china.reason_tags}")
            print(f"   - Should include: {targeting.should_include(profile_china)}")
            
            return len(chinese_matches) > 0
            
        else:
            print(f"❌ Scan échoué: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    found_chinese = check_chinese_matches()
    if found_chinese:
        print("\n🎉 MATCHS CHINOIS PRÉSENTS DANS LE SYSTÈME")
    else:
        print("\n❌ AUCUN MATCH CHINOIS DANS LE SYSTÈME")
    
    sys.exit(0 if found_chinese else 1)
