"""
AnomalyEngine Usage Examples
Demonstrates how to detect bookmaker anomalies
"""

import json
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine


def example_basic_anomaly_detection():
    """Basic anomaly detection example"""
    
    print("=" * 60)
    print("EXAMPLE 1: Basic Anomaly Detection")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # Get team stats
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        # Analyze market
        anomaly_engine = AnomalyEngine()
        result = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ft_under_25",
            bookmaker_odds=2.50,  # 40% implied probability
            home_stats=home_stats,
            away_stats=away_stats,
            line=2.5
        )
        
        print(f"\n📊 Market Analysis: FT Under 2.5")
        print(f"Bookmaker odds: {result.bookmaker_odds}")
        print(f"Bookmaker probability: {result.bookmaker_probability:.1%}")
        print(f"Model probability: {result.model_probability:.1%}")
        print(f"\n🎯 Scores:")
        print(f"  Anomaly score: {result.anomaly_score:.1f}/100")
        print(f"  Discrepancy: {result.discrepancy_score:.1f}/100")
        print(f"  Variance safety: {result.variance_safety_score:.1f}/100")
        print(f"  Stability: {result.stability_score:.1f}/100")
        print(f"\n✅ Confidence: {result.confidence_category.value} ({result.confidence_score:.0%})")
        
        if result.positive_signals:
            print(f"\n📈 Positive Signals ({len(result.positive_signals)}):")
            for signal in result.positive_signals:
                print(f"  • [{signal.strength.value}] {signal.description}")
        
        if result.risk_factors:
            print(f"\n⚠️ Risk Factors ({len(result.risk_factors)}):")
            for risk in result.risk_factors:
                print(f"  • {risk}")
    
    finally:
        db.close()


def example_ht_market_analysis():
    """HT market analysis example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: HT Market Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        
        # Analyze HT Under 0.5 (0-0 HT)
        result = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ht_under_05",
            bookmaker_odds=2.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=0.5
        )
        
        print(f"\n📊 Market: HT Under 0.5 (0-0 HT)")
        print(f"Bookmaker: {result.bookmaker_probability:.1%}")
        print(f"Model: {result.model_probability:.1%}")
        print(f"Gap: {abs(result.bookmaker_probability - result.model_probability):.1%}")
        print(f"\nAnomaly score: {result.anomaly_score:.1f}/100")
        print(f"Confidence: {result.confidence_category.value}")
    
    finally:
        db.close()


def example_btts_analysis():
    """BTTS market analysis example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: BTTS Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        result = anomaly_engine.analyze_market(
            match_id=1,
            market_type="btts",
            bookmaker_odds=1.80,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        print(f"\n📊 Market: BTTS")
        print(f"Bookmaker: {result.bookmaker_probability:.1%}")
        print(f"Model: {result.model_probability:.1%}")
        print(f"\nAnomaly score: {result.anomaly_score:.1f}/100")
        print(f"Historical BTTS rate: {result.historical_hit_rate:.1f}%")
    
    finally:
        db.close()


def example_extreme_line():
    """Extreme line analysis example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Extreme Line Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        
        # Analyze extreme line (Under 10.5)
        result = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ft_under_105",
            bookmaker_odds=1.50,  # 67% implied
            home_stats=home_stats,
            away_stats=away_stats,
            line=10.5
        )
        
        print(f"\n📊 Market: FT Under 10.5 (Extreme Line)")
        print(f"Bookmaker: {result.bookmaker_probability:.1%}")
        print(f"Model: {result.model_probability:.1%}")
        print(f"\nAnomaly score: {result.anomaly_score:.1f}/100")
        
        if result.anomaly_score > 60:
            print("\n✅ Potential value bet detected!")
    
    finally:
        db.close()


def example_json_export():
    """JSON export example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: JSON Export")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        result = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ft_under_25",
            bookmaker_odds=2.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=2.5
        )
        
        # Convert to JSON
        result_json = result.to_json()
        
        # Pretty print
        print("\n📄 Anomaly Result as JSON:")
        print(json.dumps(result_json, indent=2))
        
        # Save to file
        with open("anomaly_result.json", "w") as f:
            json.dump(result_json, f, indent=2)
        
        print("\n✅ Result saved to anomaly_result.json")
    
    finally:
        db.close()


def example_multiple_markets():
    """Analyze multiple markets example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Multiple Markets Analysis")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        
        markets = [
            ("ft_under_25", 2.50, 2.5),
            ("ft_over_25", 1.60, 2.5),
            ("ht_under_05", 2.20, 0.5),
            ("btts", 1.80, None)
        ]
        
        print(f"\n📊 Analyzing {len(markets)} markets:")
        print(f"\n{'Market':<15} {'Anomaly':<10} {'Confidence':<12} {'Signals':<10}")
        print("-" * 60)
        
        for market_type, odds, line in markets:
            result = anomaly_engine.analyze_market(
                match_id=1,
                market_type=market_type,
                bookmaker_odds=odds,
                home_stats=home_stats,
                away_stats=away_stats,
                line=line
            )
            
            print(f"{market_type:<15} "
                  f"{result.anomaly_score:<10.1f} "
                  f"{result.confidence_category.value:<12} "
                  f"{len(result.positive_signals):<10}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔍 AnomalyEngine Usage Examples\n")
    
    # Run all examples
    example_basic_anomaly_detection()
    example_ht_market_analysis()
    example_btts_analysis()
    example_extreme_line()
    example_json_export()
    example_multiple_markets()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed")
    print("=" * 60)
