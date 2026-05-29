"""
Test Real Data Pipeline
Verify the complete pipeline works with real data

Usage:
    DATA_PROVIDER=sofascore python scripts/test_real_data_pipeline.py
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine
from app.services.analysis import HistoricalLineBreachEngine


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_pipeline_step(name: str, step_func):
    """Run a pipeline step with timing"""
    print(f"\n{'='*80}")
    print(f"STEP: {name}")
    print(f"{'='*80}")
    
    start = time.time()
    try:
        result = step_func()
        elapsed = time.time() - start
        print(f"✅ SUCCESS ({elapsed:.2f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ FAILED ({elapsed:.2f}s): {e}")
        logger.error(f"Step '{name}' failed", exc_info=True)
        return None


def step_1_fetch_matches(manager: DataSourceManager):
    """Step 1: Fetch today's matches"""
    print("📥 Fetching today's matches...")
    
    response = manager.get_today_matches()
    
    if not response.success:
        raise Exception(f"Failed to fetch matches: {response.error}")
    
    matches = response.data
    print(f"   Found {len(matches)} matches")
    
    # Show first match
    if matches:
        m = matches[0]
        source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
        print(f"\n   {source_tag} Example:")
        print(f"   {m.home_team.name} vs {m.away_team.name}")
        print(f"   League: {m.competition.name}")
        print(f"   Date: {m.match_date}")
    
    return matches


def step_2_fetch_team_history(manager: DataSourceManager, team_id: str, team_name: str):
    """Step 2: Fetch team history"""
    print(f"📥 Fetching history for {team_name}...")
    
    response = manager.get_team_recent_matches(team_id, limit=10)
    
    if not response.success:
        raise Exception(f"Failed to fetch history: {response.error}")
    
    matches = response.data
    print(f"   Found {len(matches)} recent matches")
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"   {source_tag} Last match: {matches[0].match_date if matches else 'N/A'}")
    
    return matches


def step_3_fetch_h2h(manager: DataSourceManager, team_a_id: str, team_b_id: str):
    """Step 3: Fetch H2H"""
    print(f"📥 Fetching H2H...")
    
    response = manager.get_head_to_head(team_a_id, team_b_id)
    
    if not response.success:
        print(f"   ⚠️ H2H not available: {response.error}")
        return None
    
    h2h = response.data
    print(f"   Found {h2h.total_matches} H2H matches")
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"   {source_tag} Home wins: {h2h.home_wins}, Away wins: {h2h.away_wins}")
    
    return h2h


def step_4_calculate_stats(manager: DataSourceManager, team_id: str, team_name: str):
    """Step 4: Calculate stats from real data"""
    print(f"📊 Calculating stats for {team_name}...")
    
    add_provider_support_to_stats_engine()
    
    response = manager.get_team_recent_matches(team_id, limit=15)
    if not response.success or not response.data:
        raise Exception("No history available for stats calculation")
    
    stats_engine = StatsEngine(db=None)
    stats = stats_engine.calculate_from_provider_matches(team_id, response.data)
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"\n   {source_tag} Calculated Stats:")
    print(f"   Sample size: {stats.sample_size}")
    print(f"   Avg goals: {stats.avg_total_goals:.2f}")
    print(f"   Under 2.5%: {stats.under_2_5_rate:.1f}%")
    print(f"   HT 0-0%: {stats.ht_00_rate:.1f}%")
    print(f"   Variance: {stats.variance_goals_scored + stats.variance_goals_conceded:.2f}")
    
    return stats


def step_5_detect_anomaly(stats_home, stats_away, manager: DataSourceManager):
    """Step 5: Detect anomalies"""
    print("🎯 Running anomaly detection...")
    
    # Get odds
    odds_response = manager.get_match_odds("test_match")
    bookmaker_odds = 1.85
    if odds_response.success and odds_response.data:
        bookmaker_odds = odds_response.data[0].odd
    
    anomaly_engine = AnomalyEngine()
    result = anomaly_engine.analyze_market(
        match_id=1,
        market_type="ft_under_25",
        bookmaker_odds=bookmaker_odds,
        home_stats=stats_home,
        away_stats=stats_away,
        line=2.5
    )
    
    source_tag = "[REAL]" if manager.is_real_data else "[MOCK]"
    print(f"\n   {source_tag} Anomaly Result:")
    print(f"   Score: {result.anomaly_score:.1f}")
    print(f"   Confidence: {result.confidence_category.value}")
    print(f"   Discrepancy: {result.discrepancy_score:.1f}")
    print(f"   Explanation: {result.explanation_summary}")
    
    return result


def step_6_source_status(manager: DataSourceManager):
    """Step 6: Verify source status"""
    print("📊 Checking source status...")
    
    status = manager.get_source_status()
    
    print(f"\n   Source Type: {status['source_type']}")
    print(f"   Is Real: {'YES ✅' if status['is_real_data'] else 'NO ❌'}")
    print(f"   Provider: {status['provider_name']}")
    
    print(f"\n   Provenance Log:")
    for entry in status['provenance_log']:
        marker = "✅" if entry['source_type'] == "REAL" else "❌"
        print(f"   {marker} [{entry['source_type']}] {entry['endpoint']}")
    
    return status


def main():
    """Main entry point"""
    
    print("\n" + "=" * 80)
    print("🧪 REAL DATA PIPELINE TEST")
    print("=" * 80)
    
    # Check config
    config = DataSourceConfig()
    print(f"\n📊 Configuration:")
    print(f"   Source: {config.source_label}")
    print(f"   Real Data: {'YES ✅' if config.is_real_data else 'NO ❌'}")
    
    if config.is_mock_data:
        print(f"\n⚠️  WARNING: Using MOCK data")
        print(f"   To test with real data:")
        print(f"   DATA_PROVIDER=sofascore python scripts/test_real_data_pipeline.py")
    
    input("\nPress ENTER to start pipeline test...")
    
    manager = DataSourceManager()
    results = {}
    
    try:
        # Step 1: Fetch matches
        matches = test_pipeline_step(
            "1. Fetch Today's Matches",
            lambda: step_1_fetch_matches(manager)
        )
        results['matches'] = matches
        
        if not matches:
            print("\n❌ Pipeline halted: No matches available")
            return 1
        
        # Step 2: Fetch team history
        home_matches = test_pipeline_step(
            f"2. Fetch Team History ({matches[0].home_team.name})",
            lambda: step_2_fetch_team_history(manager, matches[0].home_team.id, matches[0].home_team.name)
        )
        results['home_history'] = home_matches
        
        away_matches = test_pipeline_step(
            f"2b. Fetch Team History ({matches[0].away_team.name})",
            lambda: step_2_fetch_team_history(manager, matches[0].away_team.id, matches[0].away_team.name)
        )
        results['away_history'] = away_matches
        
        # Step 3: Fetch H2H
        h2h = test_pipeline_step(
            "3. Fetch H2H",
            lambda: step_3_fetch_h2h(manager, matches[0].home_team.id, matches[0].away_team.id)
        )
        results['h2h'] = h2h
        
        # Step 4: Calculate stats
        home_stats = test_pipeline_step(
            f"4. Calculate Stats ({matches[0].home_team.name})",
            lambda: step_4_calculate_stats(manager, matches[0].home_team.id, matches[0].home_team.name)
        )
        
        away_stats = test_pipeline_step(
            f"4b. Calculate Stats ({matches[0].away_team.name})",
            lambda: step_4_calculate_stats(manager, matches[0].away_team.id, matches[0].away_team.name)
        )
        results['stats'] = (home_stats, away_stats)
        
        # Step 5: Detect anomaly
        if home_stats and away_stats:
            anomaly = test_pipeline_step(
                "5. Detect Anomaly",
                lambda: step_5_detect_anomaly(home_stats, away_stats, manager)
            )
            results['anomaly'] = anomaly
        
        # Step 6: Source status
        status = test_pipeline_step(
            "6. Source Status",
            lambda: step_6_source_status(manager)
        )
        results['status'] = status
        
        # Summary
        print("\n" + "=" * 80)
        print("📋 PIPELINE SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for v in results.values() if v is not None)
        total = len(results)
        
        print(f"\n   Steps passed: {passed}/{total}")
        print(f"   Data source: {manager.source_label}")
        print(f"   Real data: {'YES ✅' if manager.is_real_data else 'NO ❌'}")
        
        if manager.is_real_data and passed == total:
            print(f"\n   ✅ FULL REAL DATA PIPELINE WORKING")
        elif manager.is_real_data:
            print(f"\n   ⚠️  PARTIAL REAL DATA (some steps failed)")
        else:
            print(f"\n   ℹ️  MOCK DATA PIPELINE (use DATA_PROVIDER=sofascore for real)")
        
        print("\n" + "=" * 80)
        return 0
    
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted")
        return 1
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
