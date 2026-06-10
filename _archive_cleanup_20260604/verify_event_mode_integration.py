#!/usr/bin/env python3
"""
verify_event_mode_integration.py
================================
Vérification complète que tous les composants EVENT_MODE sont branchés
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


def verify_database_connection():
    """Vérifie la connexion à la base de données"""
    print(f"\n{BOLD}🗄️  VÉRIFICATION BASE DE DONNÉES{RESET}")
    print(f"{'='*50}")
    
    try:
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        
        cfg = get_supabase_config()
        
        print(f"  URL: {cfg.supabase_url[:50]}..." if cfg.supabase_url else f"  URL: {RED}Non configuré{RESET}")
        print(f"  Key: {'✅ Configuré' if cfg.supabase_key else '❌ Non configuré'}")
        print(f"  Status: {'✅ Connecté' if cfg.supabase_connected else '❌ Non connecté'}")
        
        if cfg.supabase_connected:
            repo = get_repository()
            
            # Test simple query
            try:
                result = repo._client.table("predictions").select("count", count="exact").execute()
                print(f"  Test query: {'✅ Succès' if result.data else '❌ Erreur'}")
                if result.data:
                    print(f"  Total predictions: {result.data[0]['count']}")
                return True
            except Exception as e:
                print(f"  Test query: ❌ Erreur - {e}")
                return False
        else:
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur de connexion: {e}")
        return False


def verify_event_columns():
    """Vérifie que les colonnes EVENT_MODE existent"""
    print(f"\n{BOLD}🏛️  VÉRIFICATION COLONNES EVENT_MODE{RESET}")
    print(f"{'='*50}")
    
    try:
        from app.database.supabase_config import get_supabase_config
        from app.database.supabase_repository import get_repository
        
        cfg = get_supabase_config()
        if not cfg.supabase_connected:
            print(f"  ❌ Base de données non connectée")
            return False
        
        repo = get_repository()
        
        # Vérifier les colonnes
        required_columns = ['event_context', 'event_name', 'is_event_match', 'event_phase']
        existing_columns = []
        missing_columns = []
        
        for column in required_columns:
            try:
                result = repo._client.table("predictions").select(column).limit(1).execute()
                if result.data is not None:
                    existing_columns.append(column)
                    print(f"  ✅ {column}: Existe")
                else:
                    missing_columns.append(column)
                    print(f"  ❌ {column}: Manquant")
            except Exception as e:
                if "does not exist" in str(e).lower():
                    missing_columns.append(column)
                    print(f"  ❌ {column}: Manquant")
                else:
                    existing_columns.append(column)
                    print(f"  ⚠️  {column}: Erreur - {e}")
        
        if len(missing_columns) == 0:
            print(f"\n  {GREEN}✅ Toutes les colonnes EVENT_MODE existent{RESET}")
            return True
        else:
            print(f"\n  {RED}❌ Colonnes manquantes: {missing_columns}{RESET}")
            print(f"\n  {YELLOW}💡 Solution: Exécuter event_mode_migration.sql{RESET}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def verify_event_detector():
    """Vérifie le détecteur d'événements"""
    print(f"\n{BOLD}🔍 VÉRIFICATION EVENT DETECTOR{RESET}")
    print(f"{'='*50}")
    
    try:
        from app.services.events.event_detector import get_detector, EventContext
        
        detector = get_detector()
        
        # Test avec différents contextes
        test_cases = [
            ("World Cup", "FIFA World Cup 2026", "World", EventContext.WORLD_CUP),
            ("Friendly", "International Friendly", "France", EventContext.INTERNATIONAL_FRIENDLY),
            ("Euro", "UEFA Euro 2024", "Germany", EventContext.CONTINENTAL_TOURNAMENT),
            ("Domestic", "Premier League", "England", EventContext.DOMESTIC_LEAGUE),
        ]
        
        all_passed = True
        for name, competition, country, expected in test_cases:
            class MockMatch:
                def __init__(self, comp, country):
                    self.competition = MockCompetition(comp)
                    self.country = country
            
            class MockCompetition:
                def __init__(self, name):
                    self.name = name
            
            mock_match = MockMatch(competition, country)
            result = detector.detect_event(mock_match)
            
            actual = result.get("event_context")
            expected_value = expected.value
            
            status = f"{GREEN}✅{RESET}" if actual == expected_value else f"{RED}❌{RESET}"
            print(f"  {status} {name}: {actual} (expected: {expected_value})")
            
            if actual != expected_value:
                all_passed = False
        
        if all_passed:
            print(f"\n  {GREEN}✅ Event Detector fonctionne correctement{RESET}")
            return True
        else:
            print(f"\n  {RED}❌ Event Detector a des problèmes{RESET}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def verify_scanner_integration():
    """Vérifie l'intégration dans le scanner"""
    print(f"\n{BOLD}🔬 VÉRIFICATION SCANNER INTEGRATION{RESET}")
    print(f"{'='*50}")
    
    try:
        # Vérifier que le scanner inclut la détection d'événements
        scanner_file = os.path.join(os.path.dirname(__file__), "app", "services", "scanner", "smart_scanner.py")
        
        if not os.path.exists(scanner_file):
            print(f"  ❌ smart_scanner.py non trouvé")
            return False
        
        with open(scanner_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_integrations = [
            ("event_detector", "from app.services.events.event_detector import get_detector"),
            ("event_context", "event_context = event_detector.detect_event(match)"),
            ("is_event_match", "is_event_match = event_context.get(\"is_event_match\", False)"),
            ("event_rules", "PHASE 5: Conservative event rules"),
            ("EVENT_RESEARCH_ONLY", "\"EVENT_RESEARCH_ONLY\""),
            ("event_context_field", "\"event_context\": event_context"),
        ]
        
        missing_integrations = []
        for integration_name, integration_code in required_integrations:
            if integration_code not in content:
                missing_integrations.append(integration_name)
                print(f"  ❌ {integration_name}: Non trouvé")
            else:
                print(f"  ✅ {integration_name}: Intégré")
        
        if not missing_integrations:
            print(f"\n  {GREEN}✅ Scanner intègre avec EVENT_MODE{RESET}")
            return True
        else:
            print(f"\n  {RED}❌ Intégrations manquantes: {missing_integrations}{RESET}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def verify_api_endpoint():
    """Vérifie l'endpoint API"""
    print(f"\n{BOLD}🌐 VÉRIFICATION API ENDPOINT{RESET}")
    print(f"{'='*50}")
    
    try:
        flask_file = os.path.join(os.path.dirname(__file__), "app_flask.py")
        
        if not os.path.exists(flask_file):
            print(f"  ❌ app_flask.py non trouvé")
            return False
        
        with open(flask_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_api_elements = [
            ("Endpoint", "/api/event-mode"),
            ("Function", "def event_mode_status()"),
            ("Event context", "event_context"),
            ("Event name", "event_name"),
            ("Event phase", "event_phase"),
            ("Is event match", "is_event_match"),
        ]
        
        missing_elements = []
        for element_name, element_code in required_api_elements:
            if element_code not in content:
                missing_elements.append(element_name)
                print(f"  ❌ {element_name}: Non trouvé")
            else:
                print(f"  ✅ {element_name}: Intégré")
        
        if not missing_elements:
            print(f"\n  {GREEN}✅ API endpoint /api/event-mode intégré{RESET}")
            return True
        else:
            print(f"\n  {RED}❌ Éléments API manquants: {missing_elements}{RESET}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def verify_audit_tool():
    """Vérifie l'outil d'audit"""
    print(f"\n{BOLD}📊 VÉRIFICATION AUDIT TOOL{RESET}")
    print(f"{'='*50}")
    
    try:
        audit_file = os.path.join(os.path.dirname(__file__), "audit_event_mode.py")
        
        if not os.path.exists(audit_file):
            print(f"  ❌ audit_event_mode.py non trouvé")
            return False
        
        with open(audit_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = [
            "get_event_predictions",
            "analyze_event_performance", 
            "breakdown_by_event_context",
            "breakdown_by_market",
            "breakdown_by_team",
            "breakdown_by_event_phase",
            "run_audit"
        ]
        
        missing_functions = []
        for function in required_functions:
            if f"def {function}" not in content:
                missing_functions.append(function)
                print(f"  ❌ {function}: Non trouvée")
            else:
                print(f"  ✅ {function}: Implémentée")
        
        if not missing_functions:
            print(f"\n  {GREEN}✅ Audit tool complet{RESET}")
            return True
        else:
            print(f"\n  {RED}❌ Fonctions manquantes: {missing_functions}{RESET}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def verify_performance_reporting():
    """Vérifie le reporting de performance"""
    print(f"\n{BOLD}📈 VÉRIFICATION PERFORMANCE REPORTING{RESET}")
    print(f"{'='*50}")
    
    try:
        report_file = os.path.join(os.path.dirname(__file__), "scripts", "performance_report.py")
        
        if not os.path.exists(report_file):
            print(f"  ❌ performance_report.py non trouvé")
            return False
        
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "PHASE 7 — Event Mode Performance" in content:
            print(f"  ✅ PHASE 7: Event Mode Performance implémentée")
            
            if "event_context" in content and "DOMESTIC_LEAGUE" in content:
                print(f"  ✅ Séparation événements/domestique")
                return True
            else:
                print(f"  ⚠️  Séparation incomplète")
                return True
        else:
            print(f"  ❌ PHASE 7 non trouvée")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def run_complete_verification():
    """Exécute la vérification complète"""
    print(f"\n{BOLD}{'='*60}")
    print(f"🔍 VÉRIFICATION COMPLÈTE EVENT MODE INTEGRATION")
    print(f"{'='*60}{RESET}")
    
    verifications = [
        ("Base de données", verify_database_connection),
        ("Colonnes EVENT_MODE", verify_event_columns),
        ("Event Detector", verify_event_detector),
        ("Scanner Integration", verify_scanner_integration),
        ("API Endpoint", verify_api_endpoint),
        ("Audit Tool", verify_audit_tool),
        ("Performance Reporting", verify_performance_reporting),
    ]
    
    results = []
    for name, verify_func in verifications:
        try:
            result = verify_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ {name} - Erreur critique: {e}")
            results.append((name, False))
    
    # Résumé final
    print(f"\n{BOLD}{'='*60}")
    print(f"📋 RÉSUMÉ DE VÉRIFICATION")
    print(f"{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"  {status} {name}")
    
    print(f"\n{BOLD}Résultat: {passed}/{total} composants vérifiés{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 EVENT_MODE COMPLÈTEMENT INTÉGRÉ!{RESET}")
        print(f"\n{CYAN}Prochaines:{RESET}")
        print(f"  1. Exécuter: event_mode_migration.sql dans Supabase")
        print(f"  2. Tester: python audit_event_mode.py")
        print(f" 3. Monitor: curl http://localhost:5000/api/event-mode")
        print(f"  4. Rapport: python scripts/performance_report.py")
        print(f"  \n🏆 Système prêt pour Coupe du Monde 2026!")
    else:
        print(f"\n{YELLOW}⚠️  EVENT_MODE PARTIELLEMENT INTÉGRÉ{RESET}")
        print(f"  {total - passed} composants nécessitent attention")
    
    return passed == total


if __name__ == "__main__":
    success = run_complete_verification()
    sys.exit(0 if success else 1)
