"""
Pipeline Debug Script
Test end-to-end pipeline with real data flow

Tests complete workflow:
1. Fetch matches via provider
2. Fetch team histories
3. Fetch H2H
4. Fetch odds
5. Calculate stats
6. Detect anomalies
7. Rank results
8. Display dashboard

Usage:
    python debug_pipeline.py
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, field

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.data_source_config import DataSourceConfig
from app.providers.data_source_manager import DataSourceManager
from app.providers.odds import MockOddsProvider
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline_debug.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Metrics for pipeline execution"""
    step_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = False
    error: str = ""
    data_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self):
        """Start timing"""
        self.start_time = time.time()
    
    def end(self, success: bool = True, error: str = "", data_count: int = 0, **metadata):
        """End timing and record results"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error
        self.data_count = data_count
        self.metadata = metadata


class PipelineDebugger:
    """
    Pipeline debugger
    
    Tests complete end-to-end workflow with detailed logging
    """
    
    def __init__(self):
        """Initialize debugger"""
        self.metrics: List[PipelineMetrics] = []
        self.total_start_time = 0.0
        self.total_end_time = 0.0
        
        logger.info("="*80)
        logger.info("PIPELINE DEBUG - START")
        logger.info("="*80)
    
    def run(self) -> bool:
        """
        Run complete pipeline test
        
        Returns:
            True if pipeline completed successfully
        """
        self.total_start_time = time.time()
        
        try:
            # Step 1: Initialize providers
            if not self._step_initialize_providers():
                return False
            
            # Step 2: Fetch today's matches
            matches = self._step_fetch_matches()
            if not matches:
                return False
            
            # Step 3: Fetch team histories
            if not self._step_fetch_team_histories(matches[0]):
                return False
            
            # Step 4: Fetch H2H
            if not self._step_fetch_h2h(matches[0]):
                return False
            
            # Step 5: Fetch odds
            if not self._step_fetch_odds(matches[0]):
                return False
            
            # Step 6: Calculate stats
            if not self._step_calculate_stats(matches[0]):
                return False
            
            # Step 7: Run anomaly detection
            if not self._step_detect_anomalies(matches[0]):
                return False
            
            # Step 8: Run full scanner
            results = self._step_run_scanner()
            if results is None:
                return False
            
            # Step 9: Display results
            self._step_display_results(results)
            
            self.total_end_time = time.time()
            
            # Final summary
            self._print_summary()
            
            return True
        
        except Exception as e:
            logger.error(f"Pipeline failed with exception: {e}", exc_info=True)
            return False
    
    def _step_initialize_providers(self) -> bool:
        """Step 1: Initialize providers"""
        metric = PipelineMetrics("Initialize Providers")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 1: Initialize Providers")
        logger.info("="*80)
        
        try:
            # Load adapter
            logger.info("Loading StatsEngine adapter...")
            add_provider_support_to_stats_engine()
            
            # Create data source manager
            logger.info("Creating DataSourceManager...")
            config = DataSourceConfig()
            self.data_manager = DataSourceManager(config)
            self.data_provider = self.data_manager.provider
            
            # Create odds provider
            logger.info("Creating odds provider...")
            self.odds_provider = self.data_manager.odds_provider
            
            # Create scanner
            logger.info("Creating DailyScannerServiceV2...")
            self.scanner = DailyScannerServiceV2(self.data_provider, is_real_data=self.data_manager.is_real_data)
            
            # Log data source
            source_tag = "REAL" if self.data_manager.is_real_data else "MOCK"
            logger.info(f"Data source: {source_tag} ({self.data_manager.source_label})")
            
            metric.end(success=True, data_count=3)
            self.metrics.append(metric)
            
            logger.info("✅ Providers initialized successfully")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to initialize providers: {e}")
            return False
    
    def _step_fetch_matches(self) -> List:
        """Step 2: Fetch today's matches"""
        metric = PipelineMetrics("Fetch Matches")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 2: Fetch Today's Matches")
        logger.info("="*80)
        
        try:
            logger.info("Fetching matches from provider...")
            response = self.data_provider.get_today_matches()
            
            if not response.success:
                raise Exception(f"Provider error: {response.error}")
            
            matches = response.data
            
            metric.end(
                success=True,
                data_count=len(matches),
                provider=response.provider,
                cached=response.cached
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Fetched {len(matches)} matches")
            
            # Display sample matches
            for i, match in enumerate(matches[:3], 1):
                logger.info(f"  {i}. {match.home_team.name} vs {match.away_team.name}")
                logger.info(f"     Competition: {match.competition.name}")
                logger.info(f"     Obscure: {match.competition.is_obscure}")
            
            if len(matches) > 3:
                logger.info(f"  ... and {len(matches) - 3} more")
            
            return matches
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to fetch matches: {e}")
            return []
    
    def _step_fetch_team_histories(self, match) -> bool:
        """Step 3: Fetch team histories"""
        metric = PipelineMetrics("Fetch Team Histories")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 3: Fetch Team Histories")
        logger.info("="*80)
        
        try:
            # Fetch home team history
            logger.info(f"Fetching history for {match.home_team.name}...")
            home_response = self.data_provider.get_team_recent_matches(
                match.home_team.id,
                limit=15
            )
            
            if not home_response.success:
                raise Exception(f"Home team error: {home_response.error}")
            
            logger.info(f"  ✅ Found {len(home_response.data)} matches")
            
            # Fetch away team history
            logger.info(f"Fetching history for {match.away_team.name}...")
            away_response = self.data_provider.get_team_recent_matches(
                match.away_team.id,
                limit=15
            )
            
            if not away_response.success:
                raise Exception(f"Away team error: {away_response.error}")
            
            logger.info(f"  ✅ Found {len(away_response.data)} matches")
            
            total_matches = len(home_response.data) + len(away_response.data)
            
            metric.end(
                success=True,
                data_count=total_matches,
                home_matches=len(home_response.data),
                away_matches=len(away_response.data)
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Fetched {total_matches} total historical matches")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to fetch team histories: {e}")
            return False
    
    def _step_fetch_h2h(self, match) -> bool:
        """Step 4: Fetch H2H"""
        metric = PipelineMetrics("Fetch H2H")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 4: Fetch Head-to-Head")
        logger.info("="*80)
        
        try:
            logger.info(f"Fetching H2H: {match.home_team.name} vs {match.away_team.name}...")
            response = self.data_provider.get_head_to_head(
                match.home_team.id,
                match.away_team.id,
                limit=10
            )
            
            if not response.success:
                logger.warning(f"⚠️  H2H not available: {response.error}")
                metric.end(success=True, data_count=0, available=False)
                self.metrics.append(metric)
                return True
            
            h2h = response.data
            
            logger.info(f"  Total matches: {h2h.total_matches}")
            logger.info(f"  {match.home_team.name} wins: {h2h.team_a_wins}")
            logger.info(f"  {match.away_team.name} wins: {h2h.team_b_wins}")
            logger.info(f"  Draws: {h2h.draws}")
            
            metric.end(
                success=True,
                data_count=h2h.total_matches,
                available=True,
                team_a_wins=h2h.team_a_wins,
                team_b_wins=h2h.team_b_wins
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ H2H data available")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to fetch H2H: {e}")
            return False
    
    def _step_fetch_odds(self, match) -> bool:
        """Step 5: Fetch odds"""
        metric = PipelineMetrics("Fetch Odds")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 5: Fetch Odds")
        logger.info("="*80)
        
        try:
            logger.info(f"Fetching odds for match {match.id}...")
            response = self.odds_provider.get_match_odds(match.id)
            
            if not response.success:
                logger.warning(f"⚠️  Odds not available: {response.error}")
                metric.end(success=True, data_count=0, available=False)
                self.metrics.append(metric)
                return True
            
            odds_list = response.data
            
            logger.info(f"  ✅ Found {len(odds_list)} odds")
            
            # Display sample odds
            for i, odd in enumerate(odds_list[:5], 1):
                logger.info(f"  {i}. {odd.market_type.value}: {odd.odd} ({odd.bookmaker})")
            
            if len(odds_list) > 5:
                logger.info(f"  ... and {len(odds_list) - 5} more")
            
            metric.end(
                success=True,
                data_count=len(odds_list),
                available=True
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Odds data available")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to fetch odds: {e}")
            return False
    
    def _step_calculate_stats(self, match) -> bool:
        """Step 6: Calculate stats"""
        metric = PipelineMetrics("Calculate Stats")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 6: Calculate Statistics")
        logger.info("="*80)
        
        try:
            # Fetch team histories
            logger.info(f"Calculating stats for {match.home_team.name}...")
            home_response = self.data_provider.get_team_recent_matches(
                match.home_team.id,
                limit=15
            )
            
            if not home_response.success:
                raise Exception("Failed to fetch home team matches")
            
            # Calculate stats using adapter
            from app.services.stats import StatsEngine
            stats_engine = StatsEngine(db=None)
            
            home_stats = stats_engine.calculate_from_provider_matches(
                match.home_team.id,
                home_response.data
            )
            
            logger.info(f"  Sample size: {home_stats.sample_size}")
            logger.info(f"  Avg total goals: {home_stats.avg_total_goals}")
            logger.info(f"  Under 2.5 rate: {home_stats.under_2_5_rate}%")
            logger.info(f"  Data quality: {home_stats.data_quality_score}")
            
            logger.info(f"Calculating stats for {match.away_team.name}...")
            away_response = self.data_provider.get_team_recent_matches(
                match.away_team.id,
                limit=15
            )
            
            if not away_response.success:
                raise Exception("Failed to fetch away team matches")
            
            away_stats = stats_engine.calculate_from_provider_matches(
                match.away_team.id,
                away_response.data
            )
            
            logger.info(f"  Sample size: {away_stats.sample_size}")
            logger.info(f"  Avg total goals: {away_stats.avg_total_goals}")
            logger.info(f"  Under 2.5 rate: {away_stats.under_2_5_rate}%")
            logger.info(f"  Data quality: {away_stats.data_quality_score}")
            
            metric.end(
                success=True,
                data_count=2,
                home_sample=home_stats.sample_size,
                away_sample=away_stats.sample_size,
                home_quality=home_stats.data_quality_score,
                away_quality=away_stats.data_quality_score
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Statistics calculated successfully")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to calculate stats: {e}")
            return False
    
    def _step_detect_anomalies(self, match) -> bool:
        """Step 7: Detect anomalies"""
        metric = PipelineMetrics("Detect Anomalies")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 7: Detect Anomalies")
        logger.info("="*80)
        
        try:
            from app.services.stats import StatsEngine
            from app.services.anomaly import AnomalyEngine
            
            # Get stats
            stats_engine = StatsEngine(db=None)
            
            home_response = self.data_provider.get_team_recent_matches(match.home_team.id, 15)
            away_response = self.data_provider.get_team_recent_matches(match.away_team.id, 15)
            
            home_stats = stats_engine.calculate_from_provider_matches(
                match.home_team.id,
                home_response.data
            )
            
            away_stats = stats_engine.calculate_from_provider_matches(
                match.away_team.id,
                away_response.data
            )
            
            # Get odds
            odds_response = self.odds_provider.get_match_odds(match.id)
            
            if not odds_response.success or not odds_response.data:
                logger.warning("⚠️  No odds available for anomaly detection")
                metric.end(success=True, data_count=0)
                self.metrics.append(metric)
                return True
            
            # Detect anomalies
            anomaly_engine = AnomalyEngine()
            anomalies_found = 0
            
            logger.info(f"Analyzing {len(odds_response.data)} markets...")
            
            for odd in odds_response.data[:3]:  # Test first 3
                try:
                    result = anomaly_engine.analyze_market(
                        match_id=match.id,
                        market_type=odd.market_type.value,
                        bookmaker_odds=odd.odd,
                        home_stats=home_stats,
                        away_stats=away_stats,
                        line=odd.line
                    )
                    
                    logger.info(f"  {odd.market_type.value}:")
                    logger.info(f"    Anomaly score: {result.anomaly_score:.1f}")
                    logger.info(f"    Confidence: {result.confidence_category.value}")
                    
                    if result.anomaly_score >= 50:
                        anomalies_found += 1
                
                except Exception as e:
                    logger.warning(f"  Error analyzing {odd.market_type.value}: {e}")
            
            metric.end(
                success=True,
                data_count=anomalies_found,
                markets_analyzed=3
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Found {anomalies_found} anomalies")
            return True
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to detect anomalies: {e}")
            return False
    
    def _step_run_scanner(self) -> List:
        """Step 8: Run full scanner"""
        metric = PipelineMetrics("Run Scanner")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 8: Run Full Scanner")
        logger.info("="*80)
        
        try:
            logger.info("Running daily scanner...")
            results = self.scanner.scan_today(max_results=10)
            
            metric.end(
                success=True,
                data_count=len(results)
            )
            self.metrics.append(metric)
            
            logger.info(f"✅ Scanner completed: {len(results)} results")
            return results
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Scanner failed: {e}")
            return None
    
    def _step_display_results(self, results: List):
        """Step 9: Display results"""
        metric = PipelineMetrics("Display Results")
        metric.start()
        
        logger.info("\n" + "="*80)
        logger.info("STEP 9: Display Results")
        logger.info("="*80)
        
        try:
            if not results:
                logger.info("No anomalies found")
                metric.end(success=True, data_count=0)
                self.metrics.append(metric)
                return
            
            logger.info(f"\n🎯 TOP {len(results)} ANOMALIES DETECTED:\n")
            
            for i, result in enumerate(results, 1):
                logger.info(f"#{i} - Rank {result.rank}")
                logger.info(f"  Match: {result.home_team} vs {result.away_team}")
                logger.info(f"  League: {result.league}")
                logger.info(f"  Market: {result.market_type} (Priority: {result.market_priority.value})")
                
                if result.line:
                    logger.info(f"  Line: {result.line}")
                
                if result.bookmaker_odds:
                    logger.info(f"  Odds: {result.bookmaker_odds}")
                
                if result.anomaly_result:
                    logger.info(f"  Anomaly Score: {result.anomaly_result.anomaly_score:.1f}")
                    logger.info(f"  Confidence: {result.anomaly_result.confidence_category.value}")
                
                logger.info(f"  Data Quality: {result.data_quality_score:.2f}")
                logger.info(f"  Sample Size: {result.home_sample_size}/{result.away_sample_size}")
                logger.info(f"  Final Score: {result.final_score:.2f}")
                logger.info("")
            
            # Summary
            summary = self.scanner.get_summary(results)
            
            logger.info("="*80)
            logger.info("SUMMARY")
            logger.info("="*80)
            logger.info(f"Total results: {summary['total_results']}")
            logger.info(f"Avg anomaly score: {summary['avg_anomaly_score']}")
            logger.info(f"Avg data quality: {summary['avg_data_quality']}")
            
            logger.info("\nBy priority:")
            for priority, count in summary['by_priority'].items():
                logger.info(f"  {priority}: {count}")
            
            logger.info("\nBy confidence:")
            for conf, count in summary['by_confidence'].items():
                logger.info(f"  {conf}: {count}")
            
            metric.end(success=True, data_count=len(results))
            self.metrics.append(metric)
            
            logger.info("\n✅ Results displayed successfully")
        
        except Exception as e:
            metric.end(success=False, error=str(e))
            self.metrics.append(metric)
            logger.error(f"❌ Failed to display results: {e}")
    
    def _print_summary(self):
        """Print final summary"""
        total_duration = (self.total_end_time - self.total_start_time) * 1000
        
        logger.info("\n" + "="*80)
        logger.info("PIPELINE SUMMARY")
        logger.info("="*80)
        
        # Step results
        logger.info("\n📊 Step Results:\n")
        
        for metric in self.metrics:
            status = "✅" if metric.success else "❌"
            logger.info(f"{status} {metric.step_name}")
            logger.info(f"   Duration: {metric.duration_ms:.0f}ms")
            logger.info(f"   Data count: {metric.data_count}")
            
            if metric.error:
                logger.info(f"   Error: {metric.error}")
            
            if metric.metadata:
                for key, value in metric.metadata.items():
                    logger.info(f"   {key}: {value}")
            
            logger.info("")
        
        # Overall metrics
        success_count = sum(1 for m in self.metrics if m.success)
        total_steps = len(self.metrics)
        
        logger.info("="*80)
        logger.info(f"Total steps: {total_steps}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {total_steps - success_count}")
        logger.info(f"Total duration: {total_duration:.0f}ms ({total_duration/1000:.2f}s)")
        logger.info("="*80)
        
        if success_count == total_steps:
            logger.info("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        else:
            logger.info(f"\n⚠️  PIPELINE COMPLETED WITH {total_steps - success_count} ERRORS")


def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("🔍 PIPELINE DEBUG - END-TO-END TEST")
    print("="*80)
    print("\nThis script tests the complete pipeline:")
    print("  1. Fetch matches")
    print("  2. Fetch team histories")
    print("  3. Fetch H2H")
    print("  4. Fetch odds")
    print("  5. Calculate stats")
    print("  6. Detect anomalies")
    print("  7. Run scanner")
    print("  8. Display results")
    print("\nLogs will be saved to: pipeline_debug.log")
    print("="*80)
    
    input("\nPress ENTER to start...")
    
    # Run pipeline
    debugger = PipelineDebugger()
    success = debugger.run()
    
    # Exit code
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
