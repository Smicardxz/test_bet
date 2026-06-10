#!/usr/bin/env python3
"""
run_event_mode_scan.py
=======================
Lance une analyse complète avec EVENT_MODE pour générer des prédictions
avec les champs event_context, event_name, is_event_match, event_phase
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def run_event_mode_scan():
    """Lance une analyse complète avec EVENT_MODE"""
    print(f"\n{BOLD}🏆 EVENT MODE SCAN - Analyse Complète{RESET}")
    print(f"{'='*50}")
    
    try:
        # Importer les composants
        from app.services.scanner.smart_scanner import SmartScanner
        from app.providers.data_source_manager import DataSourceManager
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        
        # Vérifier la connexion à la base de données
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"{RED}❌ Supabase non connecté - impossible de sauvegarder les prédictions{RESET}")
            return False
        
        print(f"{GREEN}✅ Supabase connecté{RESET}")
        
        # Initialiser le scanner avec EVENT_MODE
        manager = DataSourceManager()
        scanner = SmartScanner(
            provider=manager.provider,
            is_real_data=manager.is_real_data,
            include_extreme_obscure=True,  # Inclure les ligues obscures
            max_analysis=20  # Plus de matchs pour les événements
        )
        
        print(f"{CYAN}✅ Scanner initialisé avec EVENT_MODE{RESET}")
        
        # Lancer le scan
        print(f"\n{YELLOW}🔍 Lancement du scan avec EVENT_MODE...{RESET}")
        result = scanner.scan_today()
        
        if result["success"]:
            print(f"{GREEN}✅ Scan réussi{RESET}")
            print(f"   - Total matches: {result['total_matches']}")
            print(f"   - Target matches: {result['target_count']}")
            print(f"   - Analyzed matches: {result['analyzed_count']}")
            
            # Analyser les résultats EVENT_MODE
            analyzed_matches = result.get("analyzed_matches", [])
            
            print(f"\n{CYAN}📊 Analyse des prédictions EVENT_MODE:{RESET}")
            
            event_matches = []
            domestic_matches = []
            
            for match in analyzed_matches:
                match_data = match.get("match_data", {})
                analysis = match.get("analysis", {})
                
                # Vérifier les champs EVENT_MODE
                event_context = analysis.get("event_context", {})
                is_event_match = event_context.get("is_event_match", False)
                event_type = event_context.get("event_context", "DOMESTIC_LEAGUE")
                
                match_info = {
                    "home_team": match_data.get("home_team", "Unknown"),
                    "away_team": match_data.get("away_team", "Unknown"),
                    "competition": match_data.get("competition", "Unknown"),
                    "status": match_data.get("status", "UNKNOWN"),
                    "event_context": event_type,
                    "is_event_match": is_event_match,
                    "event_name": event_context.get("event_name", ""),
                    "event_phase": event_context.get("event_phase", "")
                }
                
                if is_event_match:
                    event_matches.append(match_info)
                else:
                    domestic_matches.append(match_info)
            
            print(f"   - Event matches: {len(event_matches)}")
            print(f"   - Domestic matches: {len(domestic_matches)}")
            
            # Afficher les détails des événements
            if event_matches:
                print(f"\n{CYAN}🏆 Matchs événements détectés:{RESET}")
                for i, match in enumerate(event_matches[:10], 1):
                    print(f"   {i}. {match['home_team']} vs {match['away_team']}")
                    print(f"      🏆 {match['competition']}")
                    print(f"      📊 Event: {match['event_context']} - {match['event_name']}")
                    print(f"      🎯 Phase: {match['event_phase']}")
                    print()
            
            # Sauvegarder les prédictions dans la base de données
            print(f"{YELLOW}💾 Sauvegarde des prédictions dans Supabase...{RESET}")
            repo = get_repository()
            
            saved_count = 0
            for match in analyzed_matches:
                try:
                    match_data = match.get("match_data", {})
                    analysis = match.get("analysis", {})
                    
                    # Extraire les données pour la sauvegarde
                    prediction_data = {
                        "fixture_id": match_data.get("match_id", ""),
                        "home_team": match_data.get("home_team", ""),
                        "away_team": match_data.get("away_team", ""),
                        "competition": match_data.get("competition", ""),
                        "country": match_data.get("country", ""),
                        "prediction_date": match_data.get("match_date", ""),
                        "market": "EVENT_MODE_ANALYSIS",
                        "prediction": f"Event: {analysis.get('event_context', {}).get('event_context', 'DOMESTIC_LEAGUE')}",
                        "confidence": analysis.get("match_profile", {}).get("confidence_score", 0),
                        "probability": analysis.get("match_profile", {}).get("interest_score", 0),
                        "status": "PENDING",
                        # Champs EVENT_MODE
                        "event_context": analysis.get("event_context", {}).get("event_context", "DOMESTIC_LEAGUE"),
                        "event_name": analysis.get("event_context", {}).get("event_name", ""),
                        "is_event_match": analysis.get("event_context", {}).get("is_event_match", False),
                        "event_phase": analysis.get("event_context", {}).get("event_phase", "")
                    }
                    
                    # Sauvegarder la prédiction
                    repo.save_prediction(prediction_data)
                    saved_count += 1
                    
                except Exception as e:
                    print(f"   ⚠️ Erreur sauvegarde match: {e}")
                    continue
            
            print(f"{GREEN}✅ {saved_count} prédictions sauvegardées avec EVENT_MODE{RESET}")
            
            # Vérifier les données sauvegardées
            print(f"\n{CYAN}🔍 Vérification des données sauvegardées...{RESET}")
            try:
                # Compter les prédictions avec EVENT_MODE
                q = repo._client.table("predictions").select(
                    "event_context, is_event_match", count="exact"
                )
                
                result = q.execute()
                if result.data:
                    total = len(result.data)
                    events = len([p for p in result.data if p.get("is_event_match", False)])
                    domestic = total - events
                    
                    print(f"   - Total prédictions: {total}")
                    print(f"   - Événements: {events}")
                    print(f"   - Domestiques: {domestic}")
                    
                    # Breakdown par type
                    breakdown = {}
                    for p in result.data:
                        ctx = p.get("event_context", "DOMESTIC_LEAGUE")
                        if ctx not in breakdown:
                            breakdown[ctx] = 0
                        breakdown[ctx] += 1
                    
                    print(f"\n   Breakdown par type:")
                    for ctx, count in breakdown.items():
                        print(f"   - {ctx}: {count}")
                
            except Exception as e:
                print(f"   ⚠️ Erreur vérification: {e}")
            
            return True
            
        else:
            print(f"{RED}❌ Scan échoué: {result.get('error', 'Unknown error')}{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}❌ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_event_mode_scan()
    
    if success:
        print(f"\n{GREEN}🎉 EVENT MODE SCAN COMPLÉTÉ!{RESET}")
        print(f"\n{CYAN}Prochaines étapes:{RESET}")
        print(f"  1. Vérifier l'API: curl http://localhost:5000/api/event-mode")
        print(f"  2. Lancer l'audit: python audit_event_mode.py")
        print(f"  3. Vérifier le front: Event Mode section")
        print(f"  \n🏆 Système prêt pour Coupe du Monde 2026!")
    else:
        print(f"\n{RED}❌ EVENT MODE SCAN ÉCHOUÉ{RESET}")
    
    sys.exit(0 if success else 1)
