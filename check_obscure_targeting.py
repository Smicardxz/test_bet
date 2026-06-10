#!/usr/bin/env python3
"""
Vérification du targeting pour les ligues obscures
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.targeting.league_targeting_service import LeagueTargetingService

def check_obscure_targeting():
    """Vérifie le targeting pour les pays obscures"""
    
    print("🎯 VÉRIFICATION TARGETING LIGUES OBSCURES")
    print("=" * 50)
    
    try:
        targeting = LeagueTargetingService()
        
        # Pays obscures à tester
        obscure_countries = [
            "Latvia", "Estonia", "Lithuania", "Belarus", "Georgia",
            "Kyrgyzstan", "Bhutan", "Armenia", "Azerbaijan", "Moldova"
        ]
        
        print("📊 Scores de targeting pour pays obscures:")
        
        results = {}
        
        for country in obscure_countries:
            # Test avec première division
            profile_premier = targeting.analyze_competition(
                competition_name="Premier League",
                country=country
            )
            
            # Test avec deuxième division si disponible
            profile_second = targeting.analyze_competition(
                competition_name="First Division" if country != "Latvia" else "1 Lyga",
                country=country
            )
            
            should_include_premier = targeting.should_include(profile_premier)
            should_include_second = targeting.should_include(profile_second)
            
            results[country] = {
                "premier_score": profile_premier.target_score,
                "second_score": profile_second.target_score,
                "premier_included": should_include_premier,
                "second_included": should_include_second,
                "reasons_premier": profile_premier.reason_tags,
                "reasons_second": profile_second.reason_tags
            }
            
            print(f"\n🇱🇻 {country}:")
            print(f"   Premier League: {profile_premier.target_score:.1f} → {'✅ Inclus' if should_include_premier else '❌ Exclus'}")
            print(f"      Raisons: {', '.join(profile_premier.reason_tags)}")
            print(f"   First Division: {profile_second.target_score:.1f} → {'✅ Inclus' if should_include_second else '❌ Exclus'}")
            print(f"      Raisons: {', '.join(profile_second.reason_tags)}")
        
        # Résumé
        print(f"\n📈 RÉSUMÉ TARGETING OBSCUR:")
        
        included_premier = sum(1 for r in results.values() if r["premier_included"])
        included_second = sum(1 for r in results.values() if r["second_included"])
        
        print(f"   - Premières divisions incluses: {included_premier}/{len(obscure_countries)}")
        print(f"   - Deuxièmes divisions incluses: {included_second}/{len(obscure_countries)}")
        
        # Vérifier les pays avec scores élevés
        high_score_countries = [c for c, r in results.items() if r["premier_score"] >= 50.0]
        print(f"   - Pays avec score ≥ 50: {len(high_score_countries)}")
        
        if high_score_countries:
            print(f"     Pays: {', '.join(high_score_countries)}")
        
        # Vérifier les constants OBSCURE_COUNTRIES
        print(f"\n🔍 VÉRIFICATION CONSTANTS OBSCURE_COUNTRIES:")
        print(f"   OBSCURE_COUNTRIES dans targeting: {len(targeting.OBSCURE_COUNTRIES)} pays")
        
        # Afficher quelques exemples
        sample_obscure = list(targeting.OBSCURE_COUNTRIES)[:10]
        print(f"   Exemples: {', '.join(sample_obscure)}...")
        
        return len(high_score_countries) > 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    targeting_works = check_obscure_targeting()
    if targeting_works:
        print("\n🎉 TARGETING OBSCUR FONCTIONNE CORRECTEMENT")
    else:
        print("\n❌ PROBLÈME AVEC TARGETING OBSCUR")
    
    sys.exit(0 if targeting_works else 1)
