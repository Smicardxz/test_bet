#!/usr/bin/env python3
"""
Vérification des ligues obscures (Lettonie, Estonie, etc.)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.providers.data_source_manager import DataSourceManager

def check_obscure_leagues():
    """Vérifie les ligues obscures dans le système"""
    
    print("🔍 VÉRIFICATION LIGUES OBSCURES")
    print("=" * 50)
    
    # Liste des pays obscures à vérifier
    obscure_countries = [
        "Latvia", "Estonia", "Lithuania", "Belarus", "Moldova", 
        "Armenia", "Azerbaijan", "Georgia", "Kazakhstan", "Kyrgyzstan",
        "Mongolia", "Bhutan", "Nepal", "Myanmar", "Cambodia",
        "Laos", "Bangladesh", "Sri Lanka", "Maldives", "Pakistan"
    ]
    
    try:
        # Récupérer tous les matches aujourd'hui
        manager = DataSourceManager()
        response = manager.provider.get_today_matches()
        
        if response.success:
            all_matches = response.data
            print(f"✅ {len(all_matches)} matches récupérés aujourd'hui")
            
            # Analyser tous les pays présents
            all_countries = set()
            obscure_matches = {}
            
            for match in all_matches:
                country = getattr(match.competition, 'country', '') if hasattr(match, 'competition') else ''
                country = str(country).strip()
                
                if country and country != "Unknown" and country != "":
                    all_countries.add(country)
                    
                    # Vérifier si c'est un pays obscur
                    for obscure_country in obscure_countries:
                        if obscure_country.lower() in country.lower():
                            if obscure_country not in obscure_matches:
                                obscure_matches[obscure_country] = []
                            obscure_matches[obscure_country].append(match)
                            break
            
            print(f"\n🌍 TOUS LES PAYS PRÉSENTS ({len(all_countries)}):")
            for country in sorted(list(all_countries)):
                count = sum(1 for m in all_matches 
                           if getattr(m.competition, 'country', '') == country)
                print(f"   - {country}: {count} match(s)")
            
            print(f"\n🎯 PAYS OBSCURES TROUVÉS: {len(obscure_matches)}")
            
            if obscure_matches:
                print(f"\n📋 DÉTAILS DES MATCHS OBSCURES:")
                
                for country, matches in sorted(obscure_matches.items()):
                    print(f"\n🇱🇻 {country} ({len(matches)} matchs):")
                    
                    upcoming_live = 0
                    finished = 0
                    
                    for match in matches:
                        status = getattr(match, 'status', 'UNKNOWN').upper()
                        home = getattr(match.home_team, 'name', 'Unknown')
                        away = getattr(match.away_team, 'name', 'Unknown')
                        comp = getattr(match.competition, 'name', 'Unknown')
                        kickoff = getattr(match, 'kickoff_time', None)
                        time_str = kickoff.strftime("%H:%M") if kickoff else "TBD"
                        
                        if status in ['UPCOMING', 'NS', 'LIVE', 'IN_PLAY', 'PAUSED']:
                            upcoming_live += 1
                            visibility = "👁️ VISIBLE"
                        else:
                            finished += 1
                            visibility = "🚫 CACHÉ (FINISHED)"
                        
                        print(f"   {home} vs {away}")
                        print(f"      🏆 {comp}")
                        print(f"      ⏰ {time_str}")
                        print(f"      📊 {status} {visibility}")
                        print()
                    
                    print(f"   📊 Résumé {country}: {upcoming_live} visibles, {finished} cachés")
                
                # Compter totaux
                total_obscure_visible = 0
                total_obscure_hidden = 0
                
                for country, matches in obscure_matches.items():
                    for match in matches:
                        status = getattr(match, 'status', 'UNKNOWN').upper()
                        if status in ['UPCOMING', 'NS', 'LIVE', 'IN_PLAY', 'PAUSED']:
                            total_obscure_visible += 1
                        else:
                            total_obscure_hidden += 1
                
                print(f"\n📈 TOTAUX OBSCURES:")
                print(f"   - Visibles sur front: {total_obscure_visible}")
                print(f"   - Cachés (FINISHED): {total_obscure_hidden}")
                print(f"   - Total: {total_obscure_visible + total_obscure_hidden}")
                
                return total_obscure_visible > 0
                
            else:
                print(f"\n❌ AUCUN PAYS OBSCURE TROUVÉ AUJOURD'HUI")
                
                # Vérifier le targeting pour ces pays
                print(f"\n🎯 TEST TARGETING PAYS OBSCURES:")
                from app.services.targeting.league_targeting_service import LeagueTargetingService
                
                targeting = LeagueTargetingService()
                
                for country in ["Latvia", "Estonia", "Lithuania"]:
                    profile = targeting.analyze_competition(
                        competition_name="Premier League",
                        country=country
                    )
                    
                    print(f"   - {country} Premier League score: {profile.target_score}")
                    print(f"     Should include: {targeting.should_include(profile)}")
                
                return False
            
        else:
            print(f"❌ Erreur récupération matches: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    has_obscure_visible = check_obscure_leagues()
    if has_obscure_visible:
        print("\n🎉 DES MATCHS OBSCURES SONT VISIBLES SUR LE FRONT")
    else:
        print("\n❌ PAS DE MATCHS OBSCURES VISIBLES SUR LE FRONT")
    
    sys.exit(0 if has_obscure_visible else 1)
