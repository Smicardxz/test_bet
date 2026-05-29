"""
False Positive Analysis Script
Identify and analyze incorrect HIGH confidence predictions

Usage:
    python scripts/analyze_false_positives.py
"""

import sys
import logging
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.anomaly import AnomalyEngine
from app.services.anomaly.false_positive_analyzer import FalsePositiveAnalyzer
from app.services.anomaly.scoring_calibration import ScoringCalibrator, ScoreBreakdown, ScoringWeights
from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory
from app.services.stats import StatsEngine
from app.services.stats import TeamStats
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_mock_stats_for_false_positive() -> TeamStats:
    """Create stats that lead to false positive"""
    return TeamStats(
        team_id=1,
        team_name="Test Team",
        sample_size=8,  # Small sample
        home_away="all",
        last_updated=datetime.utcnow().isoformat(),
        avg_total_goals=2.8,  # Slightly over
        avg_goals_scored=1.5,
        avg_goals_conceded=1.3,
        under_1_5_rate=30.0,
        under_2_5_rate=50.0,  # Not great under rate
        under_3_5_rate=70.0,
        under_4_5_rate=90.0,
        under_5_5_rate=100.0,
        under_extreme_line_rate=100.0,
        over_1_5_rate=70.0,
        over_2_5_rate=50.0,
        over_3_5_rate=30.0,
        over_4_5_rate=10.0,
        over_5_5_rate=0.0,
        btts_rate=65.0,  # High BTTS
        clean_sheets_rate=20.0,
        avg_ht_total_goals=1.2,
        avg_ht_goals_scored=0.6,
        avg_ht_goals_conceded=0.6,
        ht_00_rate=30.0,
        variance_goals_scored=2.5,  # High variance
        variance_goals_conceded=2.0,  # High variance
        stability_score=0.85,  # High stability (misleading)
        form=["W", "L", "W", "L", "W"],  # Inconsistent form
        data_quality_score=1.0
    )


def create_mock_stats_for_true_positive() -> TeamStats:
    """Create stats that lead to true positive"""
    return TeamStats(
        team_id=2,
        team_name="Defensive Team",
        sample_size=15,
        home_away="all",
        last_updated=datetime.utcnow().isoformat(),
        avg_total_goals=1.2,
        avg_goals_scored=0.6,
        avg_goals_conceded=0.6,
        under_1_5_rate=80.0,
        under_2_5_rate=93.3,
        under_3_5_rate=100.0,
        under_4_5_rate=100.0,
        under_5_5_rate=100.0,
        under_extreme_line_rate=100.0,
        over_1_5_rate=20.0,
        over_2_5_rate=6.7,
        over_3_5_rate=0.0,
        over_4_5_rate=0.0,
        over_5_5_rate=0.0,
        btts_rate=20.0,
        clean_sheets_rate=53.3,
        avg_ht_total_goals=0.3,
        avg_ht_goals_scored=0.2,
        avg_ht_goals_conceded=0.1,
        ht_00_rate=66.7,
        variance_goals_scored=0.3,  # Low variance
        variance_goals_conceded=0.3,  # Low variance
        stability_score=0.90,
        form=["W", "W", "D", "W", "D"],
        data_quality_score=1.0
    )


def create_high_confidence_win() -> tuple:
    """Create a mock HIGH confidence winning bet"""
    weights = ScoringWeights()
    
    result = AnomalyResult(
        match_id=1,
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=1.85,
        bookmaker_probability=0.54,
        normalized_bookmaker_probability=0.58,
        model_probability=0.75,
        discrepancy_score=82.0,
        variance_safety_score=85.0,
        historical_hit_rate=78.0,
        stability_score=88.0,
        anomaly_score=82.5,
        confidence_category=ConfidenceCategory.HIGH,
        confidence_score=0.85,
        positive_signals=[],
        negative_signals=[],
        risk_factors=[],
        explanation_summary="Strong under anomaly detected",
        sample_size=15,
        data_quality=1.0
    )
    
    breakdown = ScoreBreakdown(
        discrepancy_score=82.0,
        variance_safety_score=85.0,
        historical_hit_rate=78.0,
        stability_score=88.0,
        weights=weights
    )
    
    return result, breakdown


def create_high_confidence_loss(failure_type: str = "variance") -> tuple:
    """Create a mock HIGH confidence losing bet (false positive)"""
    weights = ScoringWeights()
    
    if failure_type == "variance":
        # High discrepancy but high variance - variance blindness
        result = AnomalyResult(
            match_id=2,
            market_type="ft_under_25",
            line=2.5,
            bookmaker_odds=1.75,
            bookmaker_probability=0.57,
            normalized_bookmaker_probability=0.61,
            model_probability=0.72,
            discrepancy_score=85.0,  # High
            variance_safety_score=35.0,  # Low but ignored
            historical_hit_rate=45.0,
            stability_score=82.0,
            anomaly_score=70.2,
            confidence_category=ConfidenceCategory.HIGH,
            confidence_score=0.70,
            positive_signals=[],
            negative_signals=[],
            risk_factors=["High variance (4.5)", "Low sample (8)"],
            explanation_summary="Anomaly detected but variance too high",
            sample_size=8,
            data_quality=1.0
        )
    elif failure_type == "sample":
        # Small sample size
        result = AnomalyResult(
            match_id=3,
            market_type="ht_under_05",
            line=0.5,
            bookmaker_odds=1.30,
            bookmaker_probability=0.77,
            normalized_bookmaker_probability=0.81,
            model_probability=0.65,
            discrepancy_score=75.0,
            variance_safety_score=60.0,
            historical_hit_rate=40.0,
            stability_score=70.0,
            anomaly_score=68.5,
            confidence_category=ConfidenceCategory.HIGH,
            confidence_score=0.68,
            positive_signals=[],
            negative_signals=[],
            risk_factors=["Small sample (6)"],
            explanation_summary="HT under recommended but small sample",
            sample_size=6,
            data_quality=0.8
        )
    elif failure_type == "stability":
        # Misleading stability
        result = AnomalyResult(
            match_id=4,
            market_type="ft_under_25",
            line=2.5,
            bookmaker_odds=1.90,
            bookmaker_probability=0.53,
            normalized_bookmaker_probability=0.57,
            model_probability=0.70,
            discrepancy_score=70.0,
            variance_safety_score=75.0,
            historical_hit_rate=35.0,  # Low
            stability_score=92.0,  # Very high but misleading
            anomaly_score=71.8,
            confidence_category=ConfidenceCategory.HIGH,
            confidence_score=0.72,
            positive_signals=[],
            negative_signals=[],
            risk_factors=["Stability contradicts history"],
            explanation_summary="High stability but poor historical",
            sample_size=12,
            data_quality=1.0
        )
    else:
        # Bookmaker was right
        result = AnomalyResult(
            match_id=5,
            market_type="ft_under_25",
            line=2.5,
            bookmaker_odds=1.60,
            bookmaker_probability=0.625,
            normalized_bookmaker_probability=0.66,
            model_probability=0.58,
            discrepancy_score=55.0,  # Moderate
            variance_safety_score=70.0,
            historical_hit_rate=65.0,
            stability_score=75.0,
            anomaly_score=65.2,
            confidence_category=ConfidenceCategory.HIGH,
            confidence_score=0.65,
            positive_signals=[],
            negative_signals=[],
            risk_factors=["Moderate discrepancy"],
            explanation_summary="Borderline anomaly - bookmaker may be right",
            sample_size=15,
            data_quality=1.0
        )
    
    breakdown = ScoreBreakdown(
        discrepancy_score=result.discrepancy_score,
        variance_safety_score=result.variance_safety_score,
        historical_hit_rate=result.historical_hit_rate,
        stability_score=result.stability_score,
        weights=weights
    )
    
    return result, breakdown


def run_analysis():
    """Run false positive analysis"""
    
    print("\n" + "=" * 80)
    print("FALSE POSITIVE ANALYSIS")
    print("=" * 80)
    
    # Generate mock backtest data
    print("\n📊 Generating mock backtest data...")
    
    # Create winning HIGH confidence bets (true positives)
    wins = []
    for _ in range(25):
        wins.append(create_high_confidence_win())
    
    # Create losing HIGH confidence bets (false positives) with different failure types
    losses = []
    for _ in range(8):
        losses.append(create_high_confidence_loss("variance"))
    for _ in range(4):
        losses.append(create_high_confidence_loss("sample"))
    for _ in range(3):
        losses.append(create_high_confidence_loss("stability"))
    for _ in range(2):
        losses.append(create_high_confidence_loss("bookmaker"))
    
    print(f"   Generated: {len(wins)} wins, {len(losses)} losses")
    
    # Run analysis
    print("\n🔍 Analyzing false positives...")
    analyzer = FalsePositiveAnalyzer()
    analysis = analyzer.analyze(wins, losses)
    
    # Print report
    analyzer.print_report(analysis)
    
    # Get adjusted thresholds
    print("\n📊 ADJUSTED THRESHOLDS")
    print("-" * 80)
    thresholds = analyzer.get_adjusted_thresholds(analysis)
    for key, value in thresholds.items():
        print(f"  {key:<25}: {value}")
    
    # Export JSON
    import json
    with open("false_positive_analysis.json", 'w') as f:
        json.dump(analysis.to_dict(), f, indent=2)
    print("\n💾 Exported to: false_positive_analysis.json")
    
    return analysis


def main():
    """Main entry point"""
    
    print("\n" + "=" * 80)
    print("🔍 FALSE POSITIVE ANALYSIS SYSTEM")
    print("=" * 80)
    print("\nAnalyzing incorrect HIGH confidence predictions")
    print("Goal: Reduce false positives while maintaining true positives")
    print("=" * 80)
    
    input("\nPress ENTER to start...")
    
    try:
        analysis = run_analysis()
        return 0
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        sys.exit(1)
