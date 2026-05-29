"""
DailyScannerService Usage Examples
Demonstrates how to scan daily matches for anomalies
"""

import json
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.scanner import DailyScannerService


def example_basic_scan():
    """Basic daily scan example"""
    
    print("=" * 60)
    print("EXAMPLE 1: Basic Daily Scan")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # Create scanner
        scanner = DailyScannerService(db)
        
        # Scan today's matches
        results = scanner.scan_today()
        
        print(f"\n✅ Scan complete")
        print(f"Total anomalies found: {len(results)}")
        
        # Display top 5
        if results:
            print(f"\n🏆 Top 5 Anomalies:")
            for i, result in enumerate(results[:5], 1):
                print(f"\n{i}. {result.home_team} vs {result.away_team}")
                print(f"   League: {result.league}")
                print(f"   Market: {result.market_type} ({result.market_priority.value})")
                print(f"   Final Score: {result.final_score:.1f}")
                
                if result.anomaly_result:
                    print(f"   Anomaly: {result.anomaly_result.anomaly_score:.1f}/100")
                    print(f"   Confidence: {result.anomaly_result.confidence_category.value}")
    
    finally:
        db.close()


def example_custom_filters():
    """Example with custom filters"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Custom Filters")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        scanner = DailyScannerService(db)
        
        # Scan with custom parameters
        results = scanner.scan_today(
            max_results=10,
            min_anomaly_score=60.0
        )
        
        print(f"\n✅ Found {len(results)} high-quality anomalies")
        
        # Filter by market priority
        critical_anomalies = [r for r in results if r.market_priority.value == "CRITICAL"]
        print(f"   CRITICAL priority: {len(critical_anomalies)}")
        
        high_anomalies = [r for r in results if r.market_priority.value == "HIGH"]
        print(f"   HIGH priority: {len(high_anomalies)}")
    
    finally:
        db.close()


def example_summary_statistics():
    """Example with summary statistics"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Summary Statistics")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        scanner = DailyScannerService(db)
        results = scanner.scan_today()
        
        # Generate summary
        summary = scanner.generate_summary(results)
        
        print(f"\n📊 Scan Summary:")
        print(f"   Total anomalies: {summary['total_anomalies']}")
        print(f"   Total matches: {summary['total_matches']}")
        print(f"   Avg anomaly score: {summary['avg_anomaly_score']:.1f}")
        print(f"   Avg confidence: {summary['avg_confidence_score']:.2%}")
        
        print(f"\n📈 By Priority:")
        for priority, count in summary['by_priority'].items():
            print(f"   {priority}: {count}")
        
        print(f"\n✅ By Confidence:")
        for confidence, count in summary['by_confidence'].items():
            print(f"   {confidence}: {count}")
    
    finally:
        db.close()


def example_filter_by_market():
    """Example filtering by market type"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Filter by Market Type")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        scanner = DailyScannerService(db)
        results = scanner.scan_today()
        
        # Filter HT markets
        ht_markets = [r for r in results if r.market_type.startswith("ht_")]
        print(f"\n📊 HT Markets: {len(ht_markets)}")
        
        # Filter extreme under
        extreme_under = [r for r in results if "65" in r.market_type or "85" in r.market_type or "105" in r.market_type]
        print(f"   Extreme Under: {len(extreme_under)}")
        
        # Filter BTTS
        btts = [r for r in results if r.market_type == "btts"]
        print(f"   BTTS: {len(btts)}")
        
        # Display best HT anomaly
        if ht_markets:
            best_ht = ht_markets[0]
            print(f"\n🏆 Best HT Anomaly:")
            print(f"   {best_ht.home_team} vs {best_ht.away_team}")
            print(f"   Market: {best_ht.market_type}")
            print(f"   Score: {best_ht.final_score:.1f}")
    
    finally:
        db.close()


def example_json_export():
    """Example exporting results to JSON"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: JSON Export")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        scanner = DailyScannerService(db)
        results = scanner.scan_today(max_results=5)
        
        # Convert to JSON
        results_json = [r.to_json() for r in results]
        
        # Save to file
        with open("daily_scan_results.json", "w") as f:
            json.dump(results_json, f, indent=2)
        
        print(f"\n✅ Exported {len(results)} results to daily_scan_results.json")
        
        # Also save summary
        summary = scanner.generate_summary(results)
        with open("daily_scan_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ Exported summary to daily_scan_summary.json")
    
    finally:
        db.close()


def example_detailed_analysis():
    """Example with detailed analysis of top anomaly"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Detailed Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        scanner = DailyScannerService(db)
        results = scanner.scan_today()
        
        if not results:
            print("\n❌ No anomalies found")
            return
        
        # Get top anomaly
        top = results[0]
        
        print(f"\n🏆 TOP ANOMALY ANALYSIS")
        print(f"=" * 60)
        print(f"\n📍 Match:")
        print(f"   {top.home_team} vs {top.away_team}")
        print(f"   League: {top.league}")
        print(f"   Date: {top.match_date}")
        
        print(f"\n📊 Market:")
        print(f"   Type: {top.market_type}")
        print(f"   Priority: {top.market_priority.value}")
        print(f"   Line: {top.line}")
        
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
            
            print(f"\n📝 Summary:")
            print(f"{anomaly.explanation_summary}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔍 DailyScannerService Usage Examples\n")
    
    # Run all examples
    example_basic_scan()
    example_custom_filters()
    example_summary_statistics()
    example_filter_by_market()
    example_json_export()
    example_detailed_analysis()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed")
    print("=" * 60)
