"""
ExplanationEngine Usage Examples
Demonstrates how to generate professional explanations
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine
from app.services.explanation import ExplanationEngine


def example_basic_explanation():
    """Basic explanation generation"""
    
    print("=" * 60)
    print("EXAMPLE 1: Basic Explanation Generation")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # Get stats
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=1, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=2, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        # Detect anomaly
        anomaly_engine = AnomalyEngine()
        anomaly = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ht_under_05",
            bookmaker_odds=2.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=0.5
        )
        
        # Generate explanation
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        print(f"\n{explanation['full_text']}")
    
    finally:
        db.close()


def example_high_confidence_explanation():
    """Example with HIGH confidence anomaly"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: HIGH Confidence Explanation")
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
        anomaly = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ft_under_105",
            bookmaker_odds=1.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=10.5
        )
        
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        print(f"\n📊 Title: {explanation['title']}")
        print(f"\n📝 Summary:\n{explanation['summary']}")
        print(f"\n✅ Confidence:\n{explanation['confidence_explanation']}")
        print(f"\n💡 Recommendation:\n{explanation['recommendation']}")
    
    finally:
        db.close()


def example_medium_confidence_explanation():
    """Example with MEDIUM confidence anomaly"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: MEDIUM Confidence Explanation")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=3, home_away="home", last_n=10)
        away_stats = stats_engine.calculate_team_stats(team_id=4, home_away="away", last_n=10)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        anomaly = anomaly_engine.analyze_market(
            match_id=2,
            market_type="ft_under_25",
            bookmaker_odds=2.10,
            home_stats=home_stats,
            away_stats=away_stats,
            line=2.5
        )
        
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        print(f"\n{explanation['full_text']}")
    
    finally:
        db.close()


def example_btts_explanation():
    """Example with BTTS market"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: BTTS Market Explanation")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        stats_engine = StatsEngine(db)
        home_stats = stats_engine.calculate_team_stats(team_id=5, home_away="home", last_n=15)
        away_stats = stats_engine.calculate_team_stats(team_id=6, home_away="away", last_n=15)
        
        if not home_stats or not away_stats:
            print("❌ Insufficient data")
            return
        
        anomaly_engine = AnomalyEngine()
        anomaly = anomaly_engine.analyze_market(
            match_id=3,
            market_type="btts",
            bookmaker_odds=2.20,
            home_stats=home_stats,
            away_stats=away_stats
        )
        
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        print(f"\n{explanation['full_text']}")
    
    finally:
        db.close()


def example_sections_separately():
    """Example accessing sections separately"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Accessing Sections Separately")
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
        anomaly = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ht_under_05",
            bookmaker_odds=2.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=0.5
        )
        
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        print(f"\n📊 Available Sections:")
        print(f"   - title")
        print(f"   - summary")
        print(f"   - statistical_analysis")
        print(f"   - confidence_explanation")
        print(f"   - risk_assessment")
        print(f"   - recommendation")
        print(f"   - full_text")
        
        print(f"\n📝 Summary Section:")
        print(explanation['summary'])
        
        print(f"\n⚠️ Risk Assessment Section:")
        print(explanation['risk_assessment'])
    
    finally:
        db.close()


def example_export_explanation():
    """Example exporting explanation"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Export Explanation")
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
        anomaly = anomaly_engine.analyze_market(
            match_id=1,
            market_type="ht_under_05",
            bookmaker_odds=2.50,
            home_stats=home_stats,
            away_stats=away_stats,
            line=0.5
        )
        
        explanation_engine = ExplanationEngine()
        explanation = explanation_engine.generate_explanation(anomaly)
        
        # Save to file
        with open("explanation_report.txt", "w", encoding="utf-8") as f:
            f.write(explanation['full_text'])
        
        print(f"\n✅ Explanation saved to explanation_report.txt")
        
        # Also save as JSON
        import json
        with open("explanation_report.json", "w", encoding="utf-8") as f:
            json.dump(explanation, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Explanation saved to explanation_report.json")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n📝 ExplanationEngine Usage Examples\n")
    
    # Run all examples
    example_basic_explanation()
    example_high_confidence_explanation()
    example_medium_confidence_explanation()
    example_btts_explanation()
    example_sections_separately()
    example_export_explanation()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed")
    print("=" * 60)
