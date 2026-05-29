"""
Test Bet Portfolio Engine
Test the betting portfolio generation system

Usage:
    python scripts/test_bet_portfolio.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.betting import (
    BetCandidate,
    BetPortfolioEngine,
    RiskLevel,
    Signal
)


def create_test_candidates() -> list:
    """Create test bet candidates"""
    candidates = [
        BetCandidate(
            match_id="1",
            home_team="Team A",
            away_team="Team B",
            competition="Premier League",
            match_date="2026-05-27",
            market_type="ft_under_25",
            line=2.5,
            bookmaker="Bookmaker1",
            odd=2.10,
            anomaly_score=75.0,
            confidence_score=0.80,
            data_quality_score=0.85,
            risk_score=0.30,
            confidence_category="HIGH",
            risk_level=RiskLevel.LOW,
            explanation="Strong under trend",
            positive_signals=[
                Signal(type="trend", description="Consistent under results", strength="STRONG")
            ],
            risk_factors=[],
            is_real_data=False
        ),
        BetCandidate(
            match_id="2",
            home_team="Team C",
            away_team="Team D",
            competition="La Liga",
            match_date="2026-05-27",
            market_type="ht_under_05",
            line=0.5,
            bookmaker="Bookmaker1",
            odd=2.50,
            anomaly_score=70.0,
            confidence_score=0.75,
            data_quality_score=0.80,
            risk_score=0.35,
            confidence_category="HIGH",
            risk_level=RiskLevel.LOW,
            explanation="HT under pattern",
            positive_signals=[
                Signal(type="pattern", description="HT under pattern", strength="MODERATE")
            ],
            risk_factors=[],
            is_real_data=False
        ),
        BetCandidate(
            match_id="3",
            home_team="Team E",
            away_team="Team F",
            competition="Serie A",
            match_date="2026-05-27",
            market_type="ft_under_15",
            line=1.5,
            bookmaker="Bookmaker1",
            odd=1.90,
            anomaly_score=65.0,
            confidence_score=0.70,
            data_quality_score=0.75,
            risk_score=0.40,
            confidence_category="MEDIUM",
            risk_level=RiskLevel.MODERATE,
            explanation="Low scoring tendency",
            positive_signals=[
                Signal(type="stats", description="Low scoring", strength="MODERATE")
            ],
            risk_factors=["Low sample size"],
            is_real_data=False
        ),
        BetCandidate(
            match_id="4",
            home_team="Team G",
            away_team="Team H",
            competition="Bundesliga",
            match_date="2026-05-27",
            market_type="btts",
            line=None,
            bookmaker="Bookmaker1",
            odd=1.85,
            anomaly_score=60.0,
            confidence_score=0.65,
            data_quality_score=0.70,
            risk_score=0.45,
            confidence_category="MEDIUM",
            risk_level=RiskLevel.MODERATE,
            explanation="BTTS opportunity",
            positive_signals=[
                Signal(type="h2h", description="High H2H BTTS", strength="WEAK")
            ],
            risk_factors=["High variance"],
            is_real_data=False
        ),
        BetCandidate(
            match_id="5",
            home_team="Team I",
            away_team="Team J",
            competition="Ligue 1",
            match_date="2026-05-27",
            market_type="ht_over_05",
            line=0.5,
            bookmaker="Bookmaker1",
            odd=1.75,
            anomaly_score=55.0,
            confidence_score=0.60,
            data_quality_score=0.65,
            risk_score=0.50,
            confidence_category="MEDIUM",
            risk_level=RiskLevel.MODERATE,
            explanation="HT over pattern",
            positive_signals=[
                Signal(type="pattern", description="HT over pattern", strength="WEAK")
            ],
            risk_factors=["Moderate risk"],
            is_real_data=False
        )
    ]
    return candidates


def test_rank_single_bets():
    """Test ranking single bets"""
    print("\n" + "=" * 80)
    print("TEST 1: Rank Single Bets")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine(min_confidence=0.60, min_data_quality=0.65)
    
    ranked = engine.rank_single_bets(candidates, max_results=10)
    
    print(f"\n✅ Ranked {len(ranked)} single bets")
    
    for i, bet in enumerate(ranked, 1):
        print(f"\n   #{i} {bet.home_team} vs {bet.away_team}")
        print(f"       Market: {bet.market_type}")
        print(f"       Odds: {bet.odd}")
        print(f"       Combined Score: {bet.combined_score:.2f}")
        print(f"       Confidence: {bet.confidence_score:.2f}")
        print(f"       Data Quality: {bet.data_quality_score:.2f}")
        print(f"       Risk: {bet.risk_level.value}")
    
    return len(ranked) > 0


def test_generate_combinations():
    """Test generating safe combinations"""
    print("\n" + "=" * 80)
    print("TEST 2: Generate Safe Combinations")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine(min_confidence=0.60, min_data_quality=0.65)
    
    combinations = engine.generate_safe_combinations(candidates, max_combinations=10)
    
    print(f"\n✅ Generated {len(combinations)} combinations")
    
    for i, combo in enumerate(combinations, 1):
        print(f"\n   Combination #{i} ({combo.bet_count} bets)")
        print(f"       Combined Odds: {combo.combined_odds}")
        print(f"       Combined Confidence: {combo.combined_confidence:.2f}")
        print(f"       Risk Score: {combo.risk_score:.2f}")
        print(f"       Correlation Risk: {combo.correlation_risk}")
        print(f"       Valid: {combo.is_valid}")
        print(f"       Explanation: {combo.explanation}")
    
    return len(combinations) > 0


def test_correlation_detection():
    """Test correlation risk detection"""
    print("\n" + "=" * 80)
    print("TEST 3: Correlation Risk Detection")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine()
    
    # Test 1: Same match (HIGH risk)
    same_match = [candidates[0], candidates[0]]
    risk = engine.detect_correlation_risk(same_match)
    print(f"\n   Same match bets: {risk} (expected: HIGH)")
    assert risk == "HIGH", "Same match should be HIGH risk"
    
    # Test 2: Same market type (MEDIUM risk)
    same_market = [candidates[0], candidates[2]]  # Both under markets
    risk = engine.detect_correlation_risk(same_market)
    print(f"   Same market type: {risk} (expected: MEDIUM)")
    assert risk == "MEDIUM", "Same market should be MEDIUM risk"
    
    # Test 3: Different matches and markets (LOW risk)
    different = [candidates[0], candidates[1]]  # Different matches, different markets
    risk = engine.detect_correlation_risk(different)
    print(f"   Different matches/markets: {risk} (expected: LOW)")
    assert risk == "LOW", "Different should be LOW risk"
    
    print("\n✅ Correlation detection working correctly")
    return True


def test_combined_odds():
    """Test combined odds calculation"""
    print("\n" + "=" * 80)
    print("TEST 4: Combined Odds Calculation")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine()
    
    # Test 2 bets
    combo = [candidates[0], candidates[1]]
    odds = engine.calculate_combined_odds(combo)
    expected = 2.10 * 2.50
    print(f"\n   2 bets: {odds} (expected: {expected})")
    assert abs(odds - expected) < 0.01, "Odds calculation incorrect"
    
    # Test 3 bets
    combo = [candidates[0], candidates[1], candidates[2]]
    odds = engine.calculate_combined_odds(combo)
    expected = 2.10 * 2.50 * 1.90
    print(f"   3 bets: {odds} (expected: {expected})")
    assert abs(odds - expected) < 0.01, "Odds calculation incorrect"
    
    print("\n✅ Combined odds calculation working correctly")
    return True


def test_combined_confidence():
    """Test combined confidence calculation"""
    print("\n" + "=" * 80)
    print("TEST 5: Combined Confidence Calculation")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine()
    
    # Test 2 bets
    combo = [candidates[0], candidates[1]]
    conf = engine.calculate_combined_confidence(combo)
    expected = (0.80 * 0.75) ** 0.5
    print(f"\n   2 bets: {conf:.2f} (expected: {expected:.2f})")
    assert abs(conf - expected) < 0.01, "Confidence calculation incorrect"
    
    print("\n✅ Combined confidence calculation working correctly")
    return True


def test_portfolio_generation():
    """Test complete portfolio generation"""
    print("\n" + "=" * 80)
    print("TEST 6: Complete Portfolio Generation")
    print("=" * 80)
    
    candidates = create_test_candidates()
    engine = BetPortfolioEngine()
    
    portfolio = engine.generate_portfolio(candidates, max_single_bets=10, max_combinations=5)
    
    print(f"\n   Single Bets: {len(portfolio['single_bets'])}")
    print(f"   Combinations: {len(portfolio['combinations'])}")
    
    assert "single_bets" in portfolio, "Portfolio missing single_bets"
    assert "combinations" in portfolio, "Portfolio missing combinations"
    
    print("\n✅ Portfolio generation working correctly")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 BET PORTFOLIO ENGINE TESTS")
    print("=" * 80)
    
    tests = [
        ("Rank Single Bets", test_rank_single_bets),
        ("Generate Combinations", test_generate_combinations),
        ("Correlation Detection", test_correlation_detection),
        ("Combined Odds", test_combined_odds),
        ("Combined Confidence", test_combined_confidence),
        ("Portfolio Generation", test_portfolio_generation)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {name}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name}: FAILED - {e}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
