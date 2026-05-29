"""
Tests for InefficiencyDetector
Validates all detection scenarios
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.anomaly.inefficiency_detector import InefficiencyDetector, InefficiencyLevel, Confidence
from app.services.anomaly.line_breach_analyzer import LineBreachAnalysis


def test_case_1_extreme_inefficiency():
    """
    Test Case 1: Under 12.5 with historical max 5 goals
    Expected: EXTREME inefficiency
    """
    print("\n" + "="*60)
    print("TEST CASE 1: Extreme Inefficiency")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    # Mock line breach analysis
    line_breach = LineBreachAnalysis(
        line=12.5,
        hit_rate=1.00,  # 100% hit rate
        breach_rate=0.00,
        avg_distance_to_line=-7.5,  # Very far from line
        max_distance=7,
        variance=0.8,  # Low variance
        consistency=0.95,
        sample_size=15,
        matches_under=15,
        matches_over=0,
        recent_trend="STABLE"
    )
    
    result = detector.detect(
        match={"home": "Kazakhstan U21", "away": "Uzbekistan U21"},
        market_type="FT Under",
        bookmaker_line=12.5,
        odd=1.85,
        bookmaker="Bet365",
        historical_stats={
            "max_goals": 5,
            "avg_goals": 3.1,
            "variance": 0.8,
            "sample_size": 15
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.9
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Inefficiency Level: {result.inefficiency_level}")
    print(f"Confidence: {result.confidence}")
    print(f"Divergence Score: {result.divergence_score:.1f}/100")
    print(f"Edge Score: {result.edge_score:.1f}/100")
    print(f"Risk Score: {result.risk_score:.1f}/100")
    print(f"Recommended Action: {result.recommended_action}")
    
    print(f"\nWhy:")
    for reason in result.why:
        print(f"  - {reason}")
    
    print(f"\nRisk Factors:")
    for risk in result.risk_factors:
        print(f"  - {risk}")
    
    # Assertions
    assert result.inefficiency_level == InefficiencyLevel.EXTREME.value
    assert result.confidence == Confidence.HIGH.value
    assert result.divergence_score >= 80
    assert result.edge_score >= 40
    
    print("\n✅ TEST PASSED")


def test_case_2_ht_under_high_hit_rate():
    """
    Test Case 2: HT Under 1.5 with 90% hit rate
    Expected: STRONG inefficiency
    """
    print("\n" + "="*60)
    print("TEST CASE 2: HT Under with High Hit Rate")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    line_breach = LineBreachAnalysis(
        line=1.5,
        hit_rate=0.90,
        breach_rate=0.10,
        avg_distance_to_line=-0.7,
        max_distance=2,
        variance=0.5,
        consistency=0.88,
        sample_size=20,
        matches_under=18,
        matches_over=2,
        recent_trend="STABLE"
    )
    
    result = detector.detect(
        match={"home": "Team A", "away": "Team B"},
        market_type="HT Under",
        bookmaker_line=1.5,
        odd=2.10,  # Implies ~47.6% probability
        bookmaker="Bookmaker X",
        historical_stats={
            "max_goals": 2,
            "avg_goals": 0.8,
            "variance": 0.5,
            "sample_size": 20
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.85
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Inefficiency Level: {result.inefficiency_level}")
    print(f"Confidence: {result.confidence}")
    print(f"Bookmaker Probability: {result.bookmaker_probability:.1f}%")
    print(f"Historical Probability: {result.historical_probability:.1f}%")
    print(f"Divergence Score: {result.divergence_score:.1f}/100")
    print(f"Edge Score: {result.edge_score:.1f}/100")
    
    print(f"\nWhy:")
    for reason in result.why:
        print(f"  - {reason}")
    
    # Assertions
    assert result.inefficiency_level in [InefficiencyLevel.STRONG.value, InefficiencyLevel.MEDIUM.value]
    assert result.edge_score > 20
    
    print("\n✅ TEST PASSED")


def test_case_3_coherent_line():
    """
    Test Case 3: Coherent line without inefficiency
    Expected: NONE or WEAK inefficiency
    """
    print("\n" + "="*60)
    print("TEST CASE 3: Coherent Line (No Inefficiency)")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    line_breach = LineBreachAnalysis(
        line=2.5,
        hit_rate=0.55,  # Close to 50/50
        breach_rate=0.45,
        avg_distance_to_line=-0.2,
        max_distance=3,
        variance=1.5,
        consistency=0.60,
        sample_size=15,
        matches_under=8,
        matches_over=7,
        recent_trend="STABLE"
    )
    
    result = detector.detect(
        match={"home": "Team C", "away": "Team D"},
        market_type="FT Under",
        bookmaker_line=2.5,
        odd=1.90,  # Implies ~52.6% probability
        bookmaker="Bookmaker Y",
        historical_stats={
            "max_goals": 4,
            "avg_goals": 2.3,
            "variance": 1.5,
            "sample_size": 15
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.75
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Inefficiency Level: {result.inefficiency_level}")
    print(f"Divergence Score: {result.divergence_score:.1f}/100")
    print(f"Edge Score: {result.edge_score:.1f}/100")
    print(f"Recommended Action: {result.recommended_action}")
    
    print(f"\nWhy:")
    for reason in result.why:
        print(f"  - {reason}")
    
    # Assertions
    assert result.inefficiency_level in [InefficiencyLevel.NONE.value, InefficiencyLevel.WEAK.value]
    assert result.divergence_score < 40
    
    print("\n✅ TEST PASSED")


def test_case_4_small_sample_size():
    """
    Test Case 4: Small sample size (high risk)
    Expected: Lower confidence, higher risk score
    """
    print("\n" + "="*60)
    print("TEST CASE 4: Small Sample Size")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    line_breach = LineBreachAnalysis(
        line=10.5,
        hit_rate=1.00,  # 100% but small sample
        breach_rate=0.00,
        avg_distance_to_line=-6.5,
        max_distance=6,
        variance=1.2,
        consistency=0.70,
        sample_size=4,  # Very small
        matches_under=4,
        matches_over=0,
        recent_trend="UNKNOWN"
    )
    
    result = detector.detect(
        match={"home": "Team E", "away": "Team F"},
        market_type="FT Under",
        bookmaker_line=10.5,
        odd=1.75,
        bookmaker="Bookmaker Z",
        historical_stats={
            "max_goals": 4,
            "avg_goals": 2.5,
            "variance": 1.2,
            "sample_size": 4
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.4
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Confidence: {result.confidence}")
    print(f"Risk Score: {result.risk_score:.1f}/100")
    print(f"Sample Size: {result.historical_context['sample_size']}")
    
    print(f"\nRisk Factors:")
    for risk in result.risk_factors:
        print(f"  - {risk}")
    
    # Assertions
    assert result.confidence == Confidence.LOW.value
    assert result.risk_score >= 40
    assert "sample size" in " ".join(result.risk_factors).lower()
    
    print("\n✅ TEST PASSED")


def test_case_5_high_variance():
    """
    Test Case 5: High variance (inconsistent scoring)
    Expected: Higher risk, lower confidence
    """
    print("\n" + "="*60)
    print("TEST CASE 5: High Variance")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    line_breach = LineBreachAnalysis(
        line=5.5,
        hit_rate=0.75,
        breach_rate=0.25,
        avg_distance_to_line=-1.5,
        max_distance=8,  # Large max
        variance=4.5,  # Very high variance
        consistency=0.40,
        sample_size=12,
        matches_under=9,
        matches_over=3,
        recent_trend="INCREASING"
    )
    
    result = detector.detect(
        match={"home": "Team G", "away": "Team H"},
        market_type="FT Under",
        bookmaker_line=5.5,
        odd=1.95,
        bookmaker="Bookmaker W",
        historical_stats={
            "max_goals": 10,
            "avg_goals": 4.0,
            "variance": 4.5,
            "sample_size": 12
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.65
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Confidence: {result.confidence}")
    print(f"Risk Score: {result.risk_score:.1f}/100")
    print(f"Variance: {result.historical_context['variance']}")
    
    print(f"\nRisk Factors:")
    for risk in result.risk_factors:
        print(f"  - {risk}")
    
    # Assertions
    assert result.confidence in [Confidence.LOW.value, Confidence.MEDIUM.value]
    assert result.risk_score >= 30
    assert "variance" in " ".join(result.risk_factors).lower()
    
    print("\n✅ TEST PASSED")


def test_case_6_no_odds():
    """
    Test Case 6: No odds available
    Expected: STATISTICAL_SIGNAL mode
    """
    print("\n" + "="*60)
    print("TEST CASE 6: No Odds (Statistical Signal Mode)")
    print("="*60)
    
    detector = InefficiencyDetector()
    
    line_breach = LineBreachAnalysis(
        line=4.5,
        hit_rate=0.95,
        breach_rate=0.05,
        avg_distance_to_line=-1.5,
        max_distance=4,
        variance=0.9,
        consistency=0.92,
        sample_size=20,
        matches_under=19,
        matches_over=1,
        recent_trend="STABLE"
    )
    
    result = detector.detect(
        match={"home": "Team I", "away": "Team J"},
        market_type="FT Under",
        bookmaker_line=None,  # No line
        odd=None,  # No odd
        bookmaker=None,
        historical_stats={
            "max_goals": 4,
            "avg_goals": 2.5,
            "variance": 0.9,
            "sample_size": 20
        },
        line_breach_analysis=line_breach,
        data_quality_score=0.85
    )
    
    print(f"\nMode: {result.mode}")
    print(f"Inefficiency Level: {result.inefficiency_level}")
    print(f"Historical Probability: {result.historical_probability:.1f}%")
    print(f"Recommended Action: {result.recommended_action}")
    
    print(f"\nWhy:")
    for reason in result.why:
        print(f"  - {reason}")
    
    # Assertions
    assert result.mode == "statistical_signal"
    assert result.inefficiency_level == InefficiencyLevel.NONE.value
    assert result.bookmaker is None
    assert "not available" in " ".join(result.why).lower()
    
    print("\n✅ TEST PASSED")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*60)
    print(" INEFFICIENCY DETECTOR - TEST SUITE")
    print("="*60)
    
    try:
        test_case_1_extreme_inefficiency()
        test_case_2_ht_under_high_hit_rate()
        test_case_3_coherent_line()
        test_case_4_small_sample_size()
        test_case_5_high_variance()
        test_case_6_no_odds()
        
        print("\n" + "="*60)
        print(" ✅ ALL TESTS PASSED")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
