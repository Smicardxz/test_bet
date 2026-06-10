#!/usr/bin/env python3
"""
Vérification des matchs chinois UPCOMING/LIVE
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.providers.data_source_manager import DataSourceManager

def check_chinese_upcoming():
    """Vérifie les matchs chinois UPCOMING/LIVE aujourd'hui"""
    
    print("🔍 VÉRIFICATION MATCHS CHINOIS UPCOMING/LIVE")
    print("=" * 50)
    
    try:
        # Récupérer tous les matches aujourd'hui
        manager = DataSourceManager()
        response = manager.provider.get_today_matches()
        
        if response.success:
            all_matches = response.data
            print(f"✅ {len(all_matches)} matches récupérés aujourd'hui")
            
            # Filtrer les matchs chinois
            chinese_matches = []
            chinese_upcoming = []
            chinese_live = []
            chinese_finished = []
            
            for match in all_matches:
                # Vérifier si c'est un match chinois
                country = getattr(match.competition, 'country', '') if hasattr(match, 'competition') else ''
                competition_name = getattr(match.competition, 'name', '') if hasattr(match, 'competition') else ''
                
                if ("China" in str(country) or "Chinese" in str(competition_name)):
                    chinese_matches.append(match)
                    
                    status = getattr(match, 'status', 'UNKNOWN').upper()
                    
                    if status in ['UPCOMING', 'NS']:
                        chinese_upcoming.append(match)
                    elif status in ['LIVE', 'IN_PLAY', 'PAUSED']:
                        chinese_live.append(match)
                    elif status in ['FINISHED', 'FT', 'AWARDED', 'WALKOVER']:
                        chinese_finished.append(match)
            
            print(f"\n🇨🇳 MATCHS CHINOIS AUJOURD'HUI: {len(chinese_matches)}")
            print(f"   - UPCOMING: {len(chinese_upcoming)}")
            print(f"   - LIVE: {len(chinese_live)}")
            print(f"   - FINISHED: {len(chinese_finished)}")
            
            # Afficher les détails
            if chinese_upcoming:
                print(f"\n📅 MATCHS CHINOIS UPCOMING:")
                for i, match in enumerate(chinese_upcoming, 1):
                    home = getattr(match.home_team, 'name', 'Unknown')
                    away = getattr(match.away_team, 'name', 'Unknown')
                    comp = getattr(match.competition, 'name', 'Unknown')
                    kickoff = getattr(match, 'kickoff_time', None)
                    time_str = kickoff.strftime("%H:%M") if kickoff else "TBD"
                    
                    print(f"   {i}. {home} vs {away}")
                    print(f"      🏆 {comp}")
                    print(f"      ⏰ {time_str}")
                    print(f"      📊 {getattr(match, 'status', 'Unknown')}")
            
            if chinese_live:
                print(f"\n🔴 MATCHS CHINOIS LIVE:")
                for i, match in enumerate(chinese_live, 1):
                    home = getattr(match.home_team, 'name', 'Unknown')
                    away = getattr(match.away_team, 'name', 'Unknown')
                    comp = getattr(match.competition, 'name', 'Unknown')
                    
                    print(f"   {i}. {home} vs {away}")
                    print(f"      🏆 {comp}")
                    print(f"      📊 {getattr(match, 'status', 'Unknown')}")
            
            if chinese_finished:
                print(f"\n✅ MATCHS CHINOIS FINISHED:")
                for i, match in enumerate(chinese_finished[:5], 1):  # Limiter à 5
                    home = getattr(match.home_team, 'name', 'Unknown')
                    away = getattr(match.away_team, 'name', 'Unknown')
                    comp = getattr(match.competition, 'name', 'Unknown')
                    
                    print(f"   {i}. {home} vs {away}")
                    print(f"      🏆 {comp}")
                if len(chinese_finished) > 5:
                    print(f"      ... et {len(chinese_finished) - 5} autres")
            
            if not chinese_upcoming and not chinese_live:
                print(f"\n❌ AUCUN MATCH CHINOIS UPCOMING/LIVE AUJOURD'HUI")
                print(f"💡 C'est pourquoi vous ne les voyez pas sur le front !")
            
            # Vérifier d'autres pays mineurs pour comparaison
            print(f"\n🌍 AUTRES PAYS MINEURS AUJOURD'HUI:")
            minor_countries = ["Kazakhstan", "Vietnam", "Ethiopia", "Egypt", "Georgia", "Armenia"]
            
            for country in minor_countries:
                country_matches = []
                for match in all_matches:
                    match_country = getattr(match.competition, 'country', '') if hasattr(match, 'competition') else ''
                    if country in str(match_country):
                        status = getattr(match, 'status', 'UNKNOWN').upper()
                        if status in ['UPCOMING', 'NS', 'LIVE', 'IN_PLAY', 'PAUSED']:
                            country_matches.append(match)
                
                if country_matches:
                    print(f"   - {country}: {len(country_matches)} match(s) UPCOMING/LIVE")
            
            return len(chinese_upcoming) + len(chinese_live) > 0
            
        else:
            print(f"❌ Erreur récupération matches: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    has_chinese_upcoming = check_chinese_upcoming()
    if has_chinese_upcoming:
        print("\n🎉 IL Y A DES MATCHS CHINOIS À VOIR SUR LE FRONT")
    else:
        print("\n❌ PAS DE MATCHS CHINOIS VISIBLES SUR LE FRONT (tous FINISHED)")
    
    sys.exit(0 if has_chinese_upcoming else 1)
