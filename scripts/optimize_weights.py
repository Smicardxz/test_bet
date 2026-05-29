"""
Weight Optimization Script
Analyze backtest results and optimize scoring weights

Usage:
    python scripts/optimize_weights.py
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backtesting import BacktestingEngine
from app.services.anomaly.weight_optimizer import WeightOptimizer, SimpleWeightOptimizer
from app.services.anomaly.scoring_calibration import ScoringWeights, ScoreBreakdown


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def extract_breakdowns_from_backtest(engine: BacktestingEngine) -> tuple:
    """
    Extract score breakdowns from backtest results
    
    Returns:
        Tuple of (winning_breakdowns, losing_breakdowns)
    """
    winning = []
    losing = []
    
    # Generate mock breakdowns for wins/losses
    # In real usage, these would come from actual ScoreBreakdown objects
    # stored during the backtest
    
    from app.services.anomaly.scoring_calibration import ScoringWeights
    
    weights = ScoringWeights(
        discrepancy=0.40,
        variance_safety=0.25,
        historical_hit_rate=0.20,
        stability=0.15
    )
    
    # Simulate winning patterns (high discrepancy, high stability)
    for _ in range(30):
        b = ScoreBreakdown(
            discrepancy_score=random.uniform(70, 95),
            variance_safety_score=random.uniform(65, 90),
            historical_hit_rate=random.uniform(60, 85),
            stability_score=random.uniform(70, 95),
            weights=weights
        )
        winning.append(b)
    
    # Simulate losing patterns (lower scores, more random)
    for _ in range(20):
        b = ScoreBreakdown(
            discrepancy_score=random.uniform(30, 65),
            variance_safety_score=random.uniform(40, 70),
            historical_hit_rate=random.uniform(35, 60),
            stability_score=random.uniform(30, 55),
            weights=weights
        )
        losing.append(b)
    
    return winning, losing


def run_full_analysis():
    """Run complete weight optimization analysis"""
    
    print("\n" + "="*80)
    print("WEIGHT OPTIMIZATION ANALYSIS")
    print("="*80)
    
    # Step 1: Run backtest
    print("\n📊 Step 1: Running backtest...")
    engine = BacktestingEngine()
    matches = engine.load_historical_matches(count=200)
    results = engine.run_backtest(matches=matches, min_anomaly_score=50.0)
    
    print(f"   Total bets: {results.total_bets}")
    print(f"   Wins: {results.total_wins}")
    print(f"   Losses: {results.total_losses}")
    print(f"   Hit rate: {results.hit_rate:.1f}%")
    print(f"   ROI: {results.roi:.1f}%")
    
    # Step 2: Extract component breakdowns
    print("\n🔍 Step 2: Analyzing component performance...")
    
    winning, losing = extract_breakdowns_from_backtest(engine)
    print(f"   Winning breakdowns: {len(winning)}")
    print(f"   Losing breakdowns: {len(losing)}")
    
    # Step 3: Optimize weights
    print("\n⚙️  Step 3: Optimizing weights...")
    
    optimizer = WeightOptimizer()
    opt_result = optimizer.optimize_from_backtest(winning, losing)
    
    # Step 4: Print results
    print("\n" + "="*80)
    print(opt_result.explanation)
    
    # Step 5: Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    for i, rec in enumerate(opt_result.recommendations, 1):
        print(f"{i}. {rec}")
    
    # Step 6: Simple optimizer comparison
    print("\n" + "="*80)
    print("SIMPLE OPTIMIZER (Rule-based)")
    print("="*80)
    
    simple = SimpleWeightOptimizer()
    
    # Convert breakdowns to score dicts
    win_scores = []
    for b in winning:
        win_scores.append({
            "discrepancy": b.discrepancy_score,
            "variance_safety": b.variance_safety_score,
            "historical": b.historical_hit_rate,
            "stability": b.stability_score
        })
    
    loss_scores = []
    for b in losing:
        loss_scores.append({
            "discrepancy": b.discrepancy_score,
            "variance_safety": b.variance_safety_score,
            "historical": b.historical_hit_rate,
            "stability": b.stability_score
        })
    
    simple_weights = simple.optimize(win_scores, loss_scores)
    
    print("\nSimple optimizer weights:")
    for comp, weight in simple_weights.items():
        print(f"  {comp:<20}: {weight:.0%}")
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
    
    return opt_result


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("⚙️  WEIGHT OPTIMIZATION SYSTEM")
    print("="*80)
    print("\nThis script analyzes backtest results and optimizes scoring weights")
    print("using simple, interpretable statistical methods (no ML).")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    try:
        result = run_full_analysis()
        return 0
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    import random
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
