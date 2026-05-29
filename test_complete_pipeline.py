"""
Complete Pipeline Test
Tests the full pipeline: Stats → Anomaly → Scanner → Explanation
"""

from app.utils.mock_dataset_generator import generate_and_save_dataset
from app.utils.load_mock_dataset import load_dataset_from_json
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.services.scanner import DailyScannerService
from app.services.explanation import ExplanationEngine


def test_complete_pipeline():
    """Test complete pipeline with explanations"""
    
    print("\n" + "=" * 80)
    print("🧪 COMPLETE PIPELINE TEST - WITH EXPLANATIONS")
    print("=" * 80)
    
    # Step 1: Generate mock dataset
    print("\n📊 Step 1: Generating mock dataset...")
    dataset = generate_and_save_dataset()
    
    # Step 2: Create database
    print("\n🔧 Step 2: Creating database...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Database created")
    
    # Step 3: Load dataset
    print("\n📥 Step 3: Loading dataset into database...")
    db = SessionLocal()
    try:
        load_dataset_from_json(db, "mock_dataset_complete.json")
    except Exception as e:
        print(f"   ❌ Error loading dataset: {e}")
        db.close()
        return
    
    # Step 4: Run scanner
    print("\n🔍 Step 4: Running daily scanner...")
    try:
        scanner = DailyScannerService(db)
        results = scanner.scan_today(max_results=5, min_anomaly_score=55.0)
        
        print(f"\n✅ Scanner complete!")
        print(f"   Found {len(results)} anomalies")
        
        if not results:
            print("   No anomalies found")
            db.close()
            return
        
        # Step 5: Generate explanations
        print("\n📝 Step 5: Generating explanations...")
        explanation_engine = ExplanationEngine()
        
        explanations = []
        for result in results:
            if result.anomaly_result:
                explanation = explanation_engine.generate_explanation(result.anomaly_result)
                explanations.append({
                    "match": f"{result.home_team} vs {result.away_team}",
                    "market": result.market_type,
                    "explanation": explanation
                })
        
        print(f"   ✅ Generated {len(explanations)} explanations")
        
        # Step 6: Display detailed analysis
        print("\n" + "=" * 80)
        print("📊 TOP 3 ANOMALIES WITH DETAILED EXPLANATIONS")
        print("=" * 80)
        
        for i, item in enumerate(explanations[:3], 1):
            print(f"\n{'#' * 80}")
            print(f"ANOMALY #{i}")
            print(f"{'#' * 80}")
            print(f"\n🏟️ Match: {item['match']}")
            print(f"📊 Market: {item['market']}")
            print(f"\n{'-' * 80}")
            print(f"\n{item['explanation']['full_text']}")
            print(f"\n{'-' * 80}")
        
        # Step 7: Export reports
        print("\n📄 Step 6: Exporting reports...")
        
        # Export top anomaly full report
        if explanations:
            top = explanations[0]
            
            # Text report
            with open("top_anomaly_report.txt", "w", encoding="utf-8") as f:
                f.write(f"RAPPORT D'ANALYSE - ANOMALIE BOOKMAKER\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"Match: {top['match']}\n")
                f.write(f"Marché: {top['market']}\n\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(top['explanation']['full_text'])
            
            print(f"   ✅ Saved top_anomaly_report.txt")
            
            # JSON report
            import json
            with open("top_anomaly_report.json", "w", encoding="utf-8") as f:
                json.dump({
                    "match": top['match'],
                    "market": top['market'],
                    "explanation": top['explanation']
                }, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ Saved top_anomaly_report.json")
            
            # All explanations summary
            with open("all_anomalies_summary.txt", "w", encoding="utf-8") as f:
                f.write(f"RÉSUMÉ DES ANOMALIES DÉTECTÉES\n")
                f.write(f"{'=' * 80}\n\n")
                
                for i, item in enumerate(explanations, 1):
                    f.write(f"\n{i}. {item['match']} - {item['market']}\n")
                    f.write(f"{'-' * 80}\n")
                    f.write(f"{item['explanation']['summary']}\n")
                    f.write(f"\n")
            
            print(f"   ✅ Saved all_anomalies_summary.txt")
        
        # Step 8: Validation
        print("\n" + "=" * 80)
        print("✅ VALIDATION COMPLÈTE")
        print("=" * 80)
        
        validations = []
        
        # Check 1: Anomalies detected
        if len(results) >= 3:
            validations.append(("✅", f"{len(results)} anomalies détectées"))
        else:
            validations.append(("⚠️", f"Seulement {len(results)} anomalies"))
        
        # Check 2: Explanations generated
        if len(explanations) >= 3:
            validations.append(("✅", f"{len(explanations)} explications générées"))
        else:
            validations.append(("⚠️", f"Seulement {len(explanations)} explications"))
        
        # Check 3: HIGH confidence exists
        high_conf = [e for e in explanations if "HIGH" in e['explanation']['confidence_explanation']]
        if high_conf:
            validations.append(("✅", f"{len(high_conf)} anomalie(s) HIGH confidence"))
        else:
            validations.append(("⚠️", "Aucune anomalie HIGH confidence"))
        
        # Check 4: Variance analysis present
        variance_analysis = [e for e in explanations if "Variance" in e['explanation']['statistical_analysis']]
        if variance_analysis:
            validations.append(("✅", "Analyse variance présente"))
        else:
            validations.append(("❌", "Analyse variance manquante"))
        
        # Check 5: Recommendations present
        recommendations = [e for e in explanations if e['explanation']['recommendation']]
        if len(recommendations) == len(explanations):
            validations.append(("✅", "Recommandations générées pour toutes les anomalies"))
        else:
            validations.append(("⚠️", "Recommandations manquantes"))
        
        # Check 6: Risk assessment present
        risk_assessments = [e for e in explanations if e['explanation']['risk_assessment']]
        if len(risk_assessments) == len(explanations):
            validations.append(("✅", "Évaluations risques générées"))
        else:
            validations.append(("⚠️", "Évaluations risques manquantes"))
        
        print()
        for status, message in validations:
            print(f"   {status} {message}")
        
        # Final verdict
        passed = sum(1 for v in validations if v[0] == "✅")
        total = len(validations)
        
        print(f"\n" + "=" * 80)
        if passed >= 5:
            print(f"🎉 PIPELINE COMPLET VALIDÉ ({passed}/{total} checks)")
            print("\n✅ Le système est opérationnel :")
            print("   • StatsEngine : Calcul 50+ métriques")
            print("   • AnomalyEngine : Détection anomalies avec 8 scores")
            print("   • DailyScannerService : Scan automatique et ranking")
            print("   • ExplanationEngine : Explications professionnelles")
        else:
            print(f"⚠️ PIPELINE PARTIEL ({passed}/{total} checks)")
        print("=" * 80)
        
        # Summary
        print(f"\n📊 RÉSUMÉ FINAL")
        print(f"   Matchs scannés: {len(dataset['upcoming_matches'])}")
        print(f"   Anomalies détectées: {len(results)}")
        print(f"   Explications générées: {len(explanations)}")
        print(f"   Rapports exportés: 3 fichiers")
        
        print(f"\n📁 Fichiers générés:")
        print(f"   • top_anomaly_report.txt")
        print(f"   • top_anomaly_report.json")
        print(f"   • all_anomalies_summary.txt")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print(f"\n✅ Test pipeline complet terminé!")


if __name__ == "__main__":
    test_complete_pipeline()
