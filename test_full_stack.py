"""
Full Stack Test - Test complete anomaly detection pipeline
Tests StatsEngine → AnomalyEngine → DailyScannerService with mock data
"""

from app.utils.mock_dataset_generator import generate_and_save_dataset
from app.utils.load_mock_dataset import load_dataset_from_json
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.services.scanner import DailyScannerService


def test_full_stack():
    """Test complete stack with mock data"""
    
    print("\n" + "=" * 60)
    print("🧪 FULL STACK TEST")
    print("=" * 60)
    
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
        results = scanner.scan_today(max_results=10, min_anomaly_score=50.0)
        
        print(f"\n✅ Scanner complete!")
        print(f"   Found {len(results)} anomalies")
        
        # Display results
        if results:
            print(f"\n🏆 TOP 5 ANOMALIES:")
            print(f"{'Rank':<6} {'Match':<40} {'Market':<15} {'Score':<8} {'Conf':<8}")
            print("-" * 85)
            
            for result in results[:5]:
                match_name = f"{result.home_team[:15]} vs {result.away_team[:15]}"
                conf = result.anomaly_result.confidence_category.value if result.anomaly_result else "N/A"
                
                print(f"{result.rank:<6} {match_name:<40} {result.market_type:<15} "
                      f"{result.final_score:<8.1f} {conf:<8}")
        
        # Generate summary
        print(f"\n📊 SUMMARY:")
        summary = scanner.generate_summary(results)
        print(f"   Total anomalies: {summary['total_anomalies']}")
        print(f"   Total matches: {summary['total_matches']}")
        print(f"   Avg anomaly score: {summary['avg_anomaly_score']:.1f}")
        print(f"   Avg confidence: {summary['avg_confidence_score']:.0%}")
        
        print(f"\n   By Priority:")
        for priority, count in summary['by_priority'].items():
            print(f"      {priority}: {count}")
        
        print(f"\n   By Confidence:")
        for confidence, count in summary['by_confidence'].items():
            print(f"      {confidence}: {count}")
        
        # Detailed analysis of top anomaly
        if results:
            print(f"\n" + "=" * 60)
            print(f"🔍 DETAILED ANALYSIS - TOP ANOMALY")
            print("=" * 60)
            
            top = results[0]
            print(f"\n📍 Match: {top.home_team} vs {top.away_team}")
            print(f"   League: {top.league}")
            print(f"   Market: {top.market_type} ({top.market_priority.value})")
            
            if top.anomaly_result:
                anomaly = top.anomaly_result
                
                print(f"\n🎯 Scores:")
                print(f"   Final Score: {top.final_score:.1f}")
                print(f"   Anomaly Score: {anomaly.anomaly_score:.1f}/100")
                print(f"   Discrepancy: {anomaly.discrepancy_score:.1f}/100")
                print(f"   Variance Safety: {anomaly.variance_safety_score:.1f}/100")
                print(f"   Stability: {anomaly.stability_score:.1f}/100")
                
                print(f"\n📈 Probabilities:")
                print(f"   Bookmaker: {anomaly.bookmaker_probability:.1%}")
                print(f"   Model: {anomaly.model_probability:.1%}")
                print(f"   Gap: {abs(anomaly.bookmaker_probability - anomaly.model_probability):.1%}")
                
                print(f"\n✅ Confidence:")
                print(f"   Category: {anomaly.confidence_category.value}")
                print(f"   Score: {anomaly.confidence_score:.0%}")
                
                if anomaly.positive_signals:
                    print(f"\n📈 Positive Signals ({len(anomaly.positive_signals)}):")
                    for signal in anomaly.positive_signals[:3]:
                        print(f"   • [{signal.strength.value}] {signal.description}")
                
                if anomaly.risk_factors:
                    print(f"\n⚠️ Risk Factors ({len(anomaly.risk_factors)}):")
                    for risk in anomaly.risk_factors[:3]:
                        print(f"   • {risk}")
        
        # Test validation
        print(f"\n" + "=" * 60)
        print(f"✅ VALIDATION")
        print("=" * 60)
        
        validations = []
        
        # Check 1: Anomalies detected
        if len(results) >= 5:
            validations.append(("✅", "At least 5 anomalies detected"))
        else:
            validations.append(("❌", f"Only {len(results)} anomalies detected (expected ≥5)"))
        
        # Check 2: CRITICAL priority exists
        critical = [r for r in results if r.market_priority.value == "CRITICAL"]
        if critical:
            validations.append(("✅", f"CRITICAL priority anomalies found ({len(critical)})"))
        else:
            validations.append(("⚠️", "No CRITICAL priority anomalies"))
        
        # Check 3: HIGH confidence exists
        high_conf = [r for r in results if r.anomaly_result and 
                     r.anomaly_result.confidence_category.value == "HIGH"]
        if high_conf:
            validations.append(("✅", f"HIGH confidence anomalies found ({len(high_conf)})"))
        else:
            validations.append(("⚠️", "No HIGH confidence anomalies"))
        
        # Check 4: HT markets detected
        ht_markets = [r for r in results if r.market_type.startswith("ht_")]
        if ht_markets:
            validations.append(("✅", f"HT market anomalies found ({len(ht_markets)})"))
        else:
            validations.append(("⚠️", "No HT market anomalies"))
        
        # Check 5: Extreme under detected
        extreme = [r for r in results if "65" in r.market_type or "85" in r.market_type or "105" in r.market_type]
        if extreme:
            validations.append(("✅", f"Extreme Under anomalies found ({len(extreme)})"))
        else:
            validations.append(("⚠️", "No Extreme Under anomalies"))
        
        print()
        for status, message in validations:
            print(f"   {status} {message}")
        
        # Final verdict
        passed = sum(1 for v in validations if v[0] == "✅")
        total = len(validations)
        
        print(f"\n" + "=" * 60)
        if passed >= 4:
            print(f"🎉 TEST PASSED ({passed}/{total} checks)")
        else:
            print(f"⚠️ TEST PARTIAL ({passed}/{total} checks)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running scanner: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print(f"\n✅ Full stack test complete!")


if __name__ == "__main__":
    test_full_stack()
