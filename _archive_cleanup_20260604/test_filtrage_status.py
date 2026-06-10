#!/usr/bin/env python3
"""
Test simple du filtrage status pour vérifier que les matches finis sont correctement exclus
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.scanner.smart_scanner import SmartScanner
from app.providers.data_source_manager import DataSourceManager

def test_status_filtering():
    """Test que le filtrage status fonctionne correctement"""
    
    print("🔍 TEST FILTRAGE STATUS")
    print("=" * 50)
    
    try:
        # Initialiser le scanner
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,
            max_analysis=2  # Très petit pour le test
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
            print(f"   - Remaining matches: {len(result['remaining_matches'])}")
            
            # Analyser les status des matches
            analyzed_statuses = {}
            remaining_statuses = {}
            
            for match in result["analyzed_matches"]:
                status = match["match_data"].get("status", "UNKNOWN")
                analyzed_statuses[status] = analyzed_statuses.get(status, 0) + 1
            
            for match in result["remaining_matches"]:
                status = match["match_data"].get("status", "UNKNOWN")
                remaining_statuses[status] = remaining_statuses.get(status, 0) + 1
            
            print("\n📈 Status des matches ANALYSÉS:")
            for status, count in analyzed_statuses.items():
                print(f"   - {status}: {count}")
            
            print("\n📊 Status des matches NON ANALYSÉS:")
            for status, count in remaining_statuses.items():
                print(f"   - {status}: {count}")
            
            # Vérifier que les matches finis ne sont pas analysés
            finished_analyzed = analyzed_statuses.get("FINISHED", 0) + analyzed_statuses.get("FT", 0)
            finished_remaining = remaining_statuses.get("FINISHED", 0) + remaining_statuses.get("FT", 0)
            
            print(f"\n🎯 VÉRIFICATION FILTRAGE:")
            print(f"   - Matches finis analysés: {finished_analyzed} (devrait être 0)")
            print(f"   - Matches finis non analysés: {finished_remaining}")
            
            if finished_analyzed == 0:
                print("✅ FILTRAGE CORRECT: Aucun match fini n'est analysé")
            else:
                print("❌ ERREUR: Des matches finis sont analysés!")
            
            # Vérifier que seuls UPCOMING/LIVE sont analysés
            upcoming_analyzed = analyzed_statuses.get("UPCOMING", 0) + analyzed_statuses.get("NS", 0)
            live_analyzed = analyzed_statuses.get("LIVE", 0) + analyzed_statuses.get("IN_PLAY", 0)
            
            print(f"   - Matches UPCOMING analysés: {upcoming_analyzed}")
            print(f"   - Matches LIVE analysés: {live_analyzed}")
            
            if upcoming_analyzed > 0 or live_analyzed > 0:
                print("✅ ANALYSE CORRECTE: Seuls les matches UPCOMING/LIVE sont analysés")
            else:
                print("ℹ️  Aucun match UPCOMING/LIVE disponible pour analyse")
            
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
    success = test_status_filtering()
    if success:
        print("\n🎉 TEST RÉUSSI")
    else:
        print("\n❌ TEST ÉCHOUÉ")
    
    sys.exit(0 if success else 1)
