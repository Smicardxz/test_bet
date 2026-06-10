#!/usr/bin/env python3
"""
Vérification des matchs chinois pour demain
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.providers.data_source_manager import DataSourceManager
from datetime import datetime, timedelta

def check_chinese_tomorrow():
    """Vérifie les matchs chinois pour demain"""
    
    print("🔍 VÉRIFICATION MATCHS CHINOIS DEMAIN")
    print("=" * 50)
    
    try:
        # Récupérer les matches de demain
        manager = DataSourceManager()
        tomorrow = datetime.now().date() + timedelta(days=1)
        
        # Essayer de récupérer les matches de demain
        response = manager.provider.get_matches_by_date(tomorrow)
        
        if response.success:
            matches_tomorrow = response.data
            print(f"✅ {len(matches_tomorrow)} matches prévus pour demain ({tomorrow})")
            
            # Filtrer les matchs chinois
            chinese_matches = []
            
            for match in matches_tomorrow:
                country = getattr(match.competition, 'country', '') if hasattr(match, 'competition') else ''
                competition_name = getattr(match.competition, 'name', '') if hasattr(match, 'competition') else ''
                
                if ("China" in str(country) or "Chinese" in str(competition_name)):
                    chinese_matches.append(match)
            
            print(f"\n🇨🇳 MATCHS CHINOIS DEMAIN: {len(chinese_matches)}")
            
            if chinese_matches:
                print(f"\n📅 MATCHS CHINOIS PRÉVUS DEMAIN:")
                for i, match in enumerate(chinese_matches, 1):
                    home = getattr(match.home_team, 'name', 'Unknown')
                    away = getattr(match.away_team, 'name', 'Unknown')
                    comp = getattr(match.competition, 'name', 'Unknown')
                    kickoff = getattr(match, 'kickoff_time', None)
                    time_str = kickoff.strftime("%H:%M") if kickoff else "TBD"
                    
                    print(f"   {i}. {home} vs {away}")
                    print(f"      🏆 {comp}")
                    print(f"      ⏰ {time_str}")
                    print(f"      📊 {getattr(match, 'status', 'Unknown')}")
                
                print(f"\n🎉 DEMAIN VOUS VERREZ DES MATCHS CHINOIS SUR LE FRONT!")
                return True
            else:
                print(f"\n❌ AUCUN MATCH CHINOIS PRÉVU DEMAIN")
                return False
                
        else:
            print(f"❌ Erreur récupération matches demain: {response.error}")
            
            # Alternative: vérifier les prochains jours
            print(f"\n🔍 VÉRIFICATION PROCHAINS JOURS...")
            
            for days_ahead in range(1, 4):
                future_date = datetime.now().date() + timedelta(days=days_ahead)
                response = manager.provider.get_matches_by_date(future_date)
                
                if response.success:
                    matches = response.data
                    chinese_count = 0
                    
                    for match in matches:
                        country = getattr(match.competition, 'country', '') if hasattr(match, 'competition') else ''
                        competition_name = getattr(match.competition, 'name', '') if hasattr(match, 'competition') else ''
                        
                        if ("China" in str(country) or "Chinese" in str(competition_name)):
                            chinese_count += 1
                    
                    if chinese_count > 0:
                        print(f"   - {future_date}: {chinese_count} match(s) chinois")
            
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    has_chinese_future = check_chinese_tomorrow()
    if has_chinese_future:
        print("\n🎉 DES MATCHS CHINOIS SONT PRÉVUS BIENTÔT!")
    else:
        print("\n❌ PAS DE MATCHS CHINOIS PRÉVUS PROCHAINEMENT")
    
    sys.exit(0 if has_chinese_future else 1)
