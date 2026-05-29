"""
Priority Ranking Script
Rank anomalies by exploitability and display top picks

Usage:
    python scripts/priority_ranking.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.analysis import PriorityRankingEngine, RiskLevel
from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_test_anomalies() -> list:
    """Create test anomalies for demonstration"""
    
    anomalies = []
    
    # Strong anomaly (should be top)
    anomalies.append(AnomalyResult(
        match_id=1,
        market_type="ht_under_05",
        line=0.5,
        bookmaker_odds=1.30,
        bookmaker_probability=0.77,
        normalized_bookmaker_probability=0.81,
        model_probability=0.92,
        discrepancy_score=88.0,
        variance_safety_score=82.0,
        historical_hit_rate=85.0,
        stability_score=90.0,
        anomaly_score=87.5,
        confidence_category=ConfidenceCategory.HIGH,
        confidence_score=0.88,
        positive_signals=[],
        negative_signals=[],
        risk_factors=[],
        explanation_summary="Strong HT under anomaly",
        sample_size=15,
        data_quality=1.0
    ))
    
    # Good anomaly
    anomalies.append(AnomalyResult(
        match_id=2,
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=1.85,
        bookmaker_probability=0.54,
        normalized_bookmaker_probability=0.58,
        model_probability=0.78,
        discrepancy_score=75.0,
        variance_safety_score=70.0,
        historical_hit_rate=72.0,
        stability_score=75.0,
        anomaly_score=74.2,
        confidence_category=ConfidenceCategory.HIGH,
        confidence_score=0.74,
        positive_signals=[],
        negative_signals=[],
        risk_factors=[],
        explanation_summary="Good FT under anomaly",
        sample_size=12,
        data_quality=1.0
    ))
    
    # Medium anomaly with risk
    anomalies.append(AnomalyResult(
        match_id=3,
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=1.90,
        bookmaker_probability=0.53,
        normalized_bookmaker_probability=0.57,
        model_probability=0.70,
        discrepancy_score=70.0,
        variance_safety_score=45.0,  # Low variance safety
        historical_hit_rate=60.0,
        stability_score=55.0,
        anomaly_score=62.5,
        confidence_category=ConfidenceCategory.MEDIUM,
        confidence_score=0.62,
        positive_signals=[],
        negative_signals=[],
        risk_factors=["High variance", "Low stability"],
        explanation_summary="Risky under anomaly",
        sample_size=8,  # Small sample
        data_quality=0.9
    ))
    
    # Weak anomaly (should be filtered out)
    anomalies.append(AnomalyResult(
        match_id=4,
        market_type="btts_yes",
        line=None,
        bookmaker_odds=2.00,
        bookmaker_probability=0.50,
        normalized_bookmaker_probability=0.55,
        model_probability=0.60,
        discrepancy_score=50.0,
        variance_safety_score=55.0,
        historical_hit_rate=45.0,
        stability_score=50.0,
        anomaly_score=52.0,
        confidence_category=ConfidenceCategory.MEDIUM,
        confidence_score=0.52,
        positive_signals=[],
        negative_signals=[],
        risk_factors=["Low confidence"],
        explanation_summary="Weak BTTS anomaly",
        sample_size=10,
        data_quality=0.8
    ))
    
    # Strong but contradictory
    anomalies.append(AnomalyResult(
        match_id=5,
        market_type="ht_under_05",
        line=0.5,
        bookmaker_odds=1.35,
        bookmaker_probability=0.74,
        normalized_bookmaker_probability=0.78,
        model_probability=0.85,
        discrepancy_score=80.0,
        variance_safety_score=35.0,  # Very low - contradictory
        historical_hit_rate=40.0,  # Low - contradictory
        stability_score=85.0,  # High - but contradicts variance
        anomaly_score=68.5,
        confidence_category=ConfidenceCategory.HIGH,
        confidence_score=0.68,
        positive_signals=[],
        negative_signals=[],
        risk_factors=["High stability contradicts low historical"],
        explanation_summary="Contradictory signals",
        sample_size=15,
        data_quality=1.0
    ))
    
    return anomalies


def run_priority_ranking():
    """Run priority ranking demonstration"""
    
    print("\n" + "=" * 100)
    print("PRIORITY RANKING ENGINE")
    print("=" * 100)
    
    # Create test data
    anomalies = create_test_anomalies()
    
    print(f"\n📊 Input: {len(anomalies)} anomalies")
    print("-" * 100)
    
    for a in anomalies:
        print(f"  Match {a.match_id}: {a.market_type:<15} Score: {a.anomaly_score:<6.1f} "
              f"Conf: {a.confidence_category.value:<7} Sample: {a.sample_size}")
    
    # Rank anomalies
    print("\n🔍 Running priority ranking...")
    
    engine = PriorityRankingEngine()
    ranking = engine.rank_anomalies(
        anomalies=anomalies,
        min_anomaly_score=60.0,
        max_results=10
    )
    
    # Print results
    engine.print_ranking(ranking, mode="top_picks")
    
    # Print risk-adjusted
    print("\n")
    engine.print_ranking(ranking, mode="risk_adjusted")
    
    # Safe picks only
    print("\n" + "=" * 100)
    print("SAFE PICKS ONLY (Risk ≤ LOW, Score ≥ 60)")
    print("=" * 100)
    
    safe_picks = engine.get_safe_picks(ranking, max_risk=RiskLevel.LOW, min_score=60.0)
    
    if safe_picks:
        for i, pa in enumerate(safe_picks[:10], 1):
            print(f"  {i}. Match {pa.match_id}: {pa.market_type:<15} "
                  f"Score: {pa.risk_adjusted_score:.1f} | Risk: {pa.risk_level.value}")
    else:
        print("  No safe picks found")
    
    # Export
    import json
    
    with open("priority_ranking.json", 'w') as f:
        json.dump(ranking.to_dict(), f, indent=2)
    
    print("\n💾 Exported to: priority_ranking.json")
    
    return ranking


def main():
    """Main entry point"""
    
    print("\n" + "=" * 100)
    print("🎯 PRIORITY RANKING SYSTEM")
    print("=" * 100)
    print("\nRanking anomalies by exploitability:")
    print("  • Anomaly score (30%)")
    print("  • Variance safety (20%)")
    print("  • Line breach safety (15%)")
    print("  • Data quality (10%)")
    print("  • Market reliability (10%)")
    print("  • League stability (10%)")
    print("  • Confidence (5%)")
    print("=" * 100)
    
    input("\nPress ENTER to start...")
    
    try:
        ranking = run_priority_ranking()
        return 0
    except Exception as e:
        logger.error(f"Ranking failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
