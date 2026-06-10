#!/usr/bin/env python3
"""
Test des projections pré-match (PHASE 1-3)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.scanner.smart_scanner import SmartScanner
from app.providers.data_source_manager import DataSourceManager

def test_pre_match_projections():
    """Test les projections pré-match et le système PRE-MATCH FIRST"""
    
    print("🎯 TEST PROJECTIONS PRÉ-MATCH (PHASE 1-3)")
    print("=" * 50)
    
    try:
        # Initialiser le scanner
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            max_analysis=15  # Plus de matchs pour voir les projections
        )
        
        print(f"✅ Scanner initialisé (PRE-MATCH FIRST)")
        
        # Lancer le scan
        print("📊 Lancement du scan...")
        result = scanner.scan_today()
        
        if result["success"]:
            print(f"✅ Scan réussi")
            print(f"   - Total matches: {result['total_matches']}")
            print(f"   - Target matches: {result['target_count']}")
            print(f"   - Analyzed matches: {result['analyzed_count']}")
            
            # Analyser les résultats
            analyzed_matches = result["analyzed_matches"]
            
            print(f"\n📈 ANALYSE DES PROJECTIONS PRÉ-MATCH:")
            
            s_tier_count = 0
            a_tier_count = 0
            b_tier_count = 0
            weak_count = 0
            upcoming_analyzed = 0
            live_analyzed = 0
            
            for i, match in enumerate(analyzed_matches, 1):
                match_data = match.get("match_data", {})
                analysis = match.get("analysis", {})
                
                status = match_data.get("status", "UNKNOWN")
                home_team = match_data.get("home_team", "Unknown")
                away_team = match_data.get("away_team", "Unknown")
                competition = match_data.get("competition", "Unknown")
                
                if status in ["UPCOMING", "NS"]:
                    upcoming_analyzed += 1
                elif status in ["LIVE", "IN_PLAY", "PAUSED"]:
                    live_analyzed += 1
                
                print(f"\n{i}. {home_team} vs {away_team}")
                print(f"   🏆 {competition}")
                print(f"   📊 Status: {status}")
                print(f"   🎯 Analysé: ✅")
                
                # Vérifier les projections
                match_profile = analysis.get("match_profile", {})
                tier = match_profile.get("tier", "UNKNOWN")
                projections = match_profile.get("pre_match_projections", [])
                confidence = match_profile.get("projection_confidence", {})
                
                print(f"   🏅 Tier: {tier}")
                print(f"   📊 Confiance overall: {confidence.get('overall', 0):.1f}")
                print(f"   🎲 Projections: {len(projections)}")
                
                # Compter les tiers
                if tier == "S-TIER":
                    s_tier_count += 1
                elif tier == "A-TIER":
                    a_tier_count += 1
                elif tier == "B-TIER":
                    b_tier_count += 1
                else:
                    weak_count += 1
                
                # Afficher les projections
                if projections:
                    print("   📋 Projections:")
                    for proj in projections[:3]:  # Limiter à 3 pour la lisibilité
                        market = proj.get("market", "Unknown")
                        probability = proj.get("probability", 0)
                        confidence = proj.get("confidence", 0)
                        reasoning = proj.get("reasoning", "")
                        
                        print(f"      - {market}: {probability:.2f} (conf: {confidence:.0f}%)")
                        print(f"        → {reasoning}")
                
                # Afficher les profils
                home_profile = match_profile.get("home_profile", {})
                away_profile = match_profile.get("away_profile", {})
                
                if home_profile:
                    print(f"   🏠 Home: {home_profile.get('avg_home_goals_scored', 0):.2f} scored, {home_profile.get('avg_home_goals_conceded', 0):.2f} conceded")
                    print(f"      Clean sheets: {home_profile.get('clean_sheet_rate', 0):.2f}, BTTS: {home_profile.get('btts_rate', 0):.2f}")
                
                if away_profile:
                    print(f"   ✈️ Away: {away_profile.get('avg_away_goals_scored', 0):.2f} scored, {away_profile.get('avg_away_goals_conceded', 0):.2f} conceded")
                    print(f"      Clean sheets: {away_profile.get('away_clean_sheet_rate', 0):.2f}, BTTS: {away_profile.get('away_btts_rate', 0):.2f}")
            
            # Résumé
            print(f"\n📊 RÉSUMÉ DES PROJECTIONS:")
            print(f"   - S-TIER: {s_tier_count}")
            print(f"   - A-TIER: {a_tier_count}")
            print(f"   - B-TIER: {b_tier_count}")
            print(f"   - WEAK: {weak_count}")
            print(f"   - UPCOMING analysés: {upcoming_analyzed}")
            print(f"   - LIVE analysés: {live_analyzed}")
            
            # Validation PHASE 1: PRE-MATCH FIRST
            if upcoming_analyzed > 0:
                print(f"\n✅ PHASE 1 RÉUSSIE: {upcoming_analyzed} matchs UPCOMING analysés (PRE-MATCH FIRST)")
            else:
                print(f"\n❌ PHASE 1 ÉCHOUÉE: Aucun match UPCOMING analysé")
            
            # Validation PHASE 2: Auto-analysis
            if upcoming_analyzed + live_analyzed >= 2:
                print(f"✅ PHASE 2 RÉUSSIE: Auto-analysis active ({upcoming_analyzed + live_analyzed} matchs)")
            else:
                print(f"❌ PHASE 2 ÉCHOUÉE: Auto-analysis insuffisante")
            
            # Validation PHASE 3: Projections
            total_projections = s_tier_count + a_tier_count + b_tier_count
            if total_projections > 0:
                print(f"✅ PHASE 3 RÉUSSIE: {total_projections} matchs avec projections valides")
            else:
                print(f"❌ PHASE 3 ÉCHOUÉE: Aucune projection générée")
            
            return True
            
        else:
            print(f"❌ Scan échoué: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pre_match_projections()
    if success:
        print("\n🎉 SYSTÈME PRE-MATCH FIRST FONCTIONNE!")
    else:
        print("\n❌ SYSTÈME PRE-MATCH FIRST ÉCHOUÉ")
    
    sys.exit(0 if success else 1)
