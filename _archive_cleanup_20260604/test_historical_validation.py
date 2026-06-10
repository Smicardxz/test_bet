"""
Test Historical Validation
Valide le moteur de simulation historique
"""

from app.services.validation.historical_simulation_engine import HistoricalSimulationEngine
from app.services.value.fair_odds_calculator import FairOddsCalculator

def test_simulation_engine():
    """Test du moteur de simulation"""
    
    print("\n" + "="*60)
    print(" TEST HISTORICAL SIMULATION ENGINE")
    print("="*60 + "\n")
    
    engine = HistoricalSimulationEngine()
    
    # Données historiques simulées (EXTREME_UNDER 4.5)
    historical_matches = [
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
        {"total_goals": 3, "home_goals": 2, "away_goals": 1},  # WIN
        {"total_goals": 1, "home_goals": 1, "away_goals": 0},  # WIN
        {"total_goals": 4, "home_goals": 2, "away_goals": 2},  # WIN
        {"total_goals": 5, "home_goals": 3, "away_goals": 2},  # LOSS
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
        {"total_goals": 3, "home_goals": 2, "away_goals": 1},  # WIN
        {"total_goals": 1, "home_goals": 0, "away_goals": 1},  # WIN
        {"total_goals": 6, "home_goals": 4, "away_goals": 2},  # LOSS
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
        {"total_goals": 3, "home_goals": 2, "away_goals": 1},  # WIN
        {"total_goals": 4, "home_goals": 3, "away_goals": 1},  # WIN
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
        {"total_goals": 1, "home_goals": 1, "away_goals": 0},  # WIN
        {"total_goals": 3, "home_goals": 2, "away_goals": 1},  # WIN
        {"total_goals": 5, "home_goals": 3, "away_goals": 2},  # LOSS
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
        {"total_goals": 4, "home_goals": 2, "away_goals": 2},  # WIN
        {"total_goals": 1, "home_goals": 0, "away_goals": 1},  # WIN
        {"total_goals": 2, "home_goals": 1, "away_goals": 1},  # WIN
    ]
    
    # Cotes bookmaker simulées (Under 4.5)
    bookmaker_odds = [1.15] * len(historical_matches)
    
    # Simuler
    result = engine.simulate_signal(
        signal_type="EXTREME_UNDER",
        market_type="UNDER",
        line=4.5,
        historical_matches=historical_matches,
        bookmaker_odds=bookmaker_odds
    )
    
    print("📊 RÉSULTATS DE SIMULATION")
    print("-" * 60)
    print(f"Signal: EXTREME_UNDER 4.5")
    print(f"Sample size: {result.total_bets} matches")
    print()
    
    print("🎯 PERFORMANCE")
    print(f"  Hit Rate: {result.historical_hit_rate:.1f}%")
    print(f"  Wins: {result.wins}")
    print(f"  Losses: {result.losses}")
    print(f"  ROI: {result.simulated_roi:.1f}%" if result.simulated_roi else "  ROI: N/A")
    print(f"  Average Odds: {result.average_odds:.2f}" if result.average_odds else "  Average Odds: N/A")
    print()
    
    print("📈 RISK METRICS")
    print(f"  Max Drawdown: {result.max_drawdown:.1f}")
    print(f"  Best Streak: {result.best_streak}")
    print(f"  Worst Streak: {result.worst_streak}")
    print(f"  Variance: {result.variance:.2f}")
    print()
    
    print("✅ QUALITY METRICS")
    print(f"  Consistency: {result.consistency_score:.1f}/100")
    print(f"  Long-term Stability: {result.long_term_stability:.1f}/100")
    print(f"  Historical Profitability: {result.historical_profitability:.1f}/100")
    print(f"  Confidence: {result.simulation_confidence}")
    print()
    
    print("🎯 VALIDATION")
    print(f"  Validated Signal: {'✅ YES' if result.validated_signal else '❌ NO'}")
    print()
    
    return result


def test_fair_odds_calculator():
    """Test du calculateur de cotes justes"""
    
    print("\n" + "="*60)
    print(" TEST FAIR ODDS CALCULATOR")
    print("="*60 + "\n")
    
    calculator = FairOddsCalculator()
    
    # Test 1: 83% de probabilité
    print("📊 TEST 1: 83% probability")
    print("-" * 60)
    
    assessment = calculator.calculate_fair_odds(
        historical_probability=0.83,
        bookmaker_odd=1.15
    )
    
    print(f"Historical Probability: {assessment.historical_probability*100:.1f}%")
    print(f"Fair Odd: {assessment.fair_odd:.2f}")
    print(f"Bookmaker Odd: {assessment.bookmaker_odd}")
    print(f"Bookmaker Implied Prob: {assessment.bookmaker_implied_probability*100:.1f}%")
    print(f"Value Gap: {assessment.value_gap_percentage:+.1f}%")
    print(f"Has Value: {'✅ YES' if assessment.has_value else '❌ NO'}")
    print(f"Value Level: {assessment.value_level}")
    print()
    
    # Test 2: Kelly stake
    print("💰 KELLY STAKE CALCULATION")
    print("-" * 60)
    
    kelly = calculator.calculate_kelly_stake(
        historical_probability=0.83,
        bookmaker_odd=1.15,
        bankroll=100.0,
        kelly_fraction=0.25
    )
    
    print(f"Recommended Stake: {kelly:.1f}% of bankroll")
    print()
    
    # Test 3: Expected Value
    print("📈 EXPECTED VALUE")
    print("-" * 60)
    
    ev = calculator.expected_value(
        historical_probability=0.83,
        bookmaker_odd=1.15,
        stake=1.0
    )
    
    print(f"EV per €1 bet: €{ev:.3f}")
    print()
    
    # Test 4: ROI Projection
    print("🎯 ROI PROJECTION (100 bets)")
    print("-" * 60)
    
    roi = calculator.roi_projection(
        historical_probability=0.83,
        bookmaker_odd=1.15,
        num_bets=100
    )
    
    print(f"Projected ROI: {roi:+.1f}%")
    print()
    
    return assessment


if __name__ == "__main__":
    print("\n" + "="*60)
    print(" HISTORICAL VALIDATION SYSTEM TEST")
    print("="*60)
    
    # Test simulation engine
    sim_result = test_simulation_engine()
    
    # Test fair odds calculator
    odds_assessment = test_fair_odds_calculator()
    
    print("\n" + "="*60)
    print(" ✅ ALL TESTS COMPLETED")
    print("="*60)
    print()
    print("📊 SUMMARY")
    print("-" * 60)
    print(f"Simulation Hit Rate: {sim_result.historical_hit_rate:.1f}%")
    print(f"Simulation ROI: {sim_result.simulated_roi:.1f}%")
    print(f"Signal Validated: {'✅ YES' if sim_result.validated_signal else '❌ NO'}")
    print()
    print(f"Fair Odd: {odds_assessment.fair_odd:.2f}")
    print(f"Value Gap: {odds_assessment.value_gap_percentage:+.1f}%")
    print(f"Value Level: {odds_assessment.value_level}")
    print()
    print("="*60)
    print()
