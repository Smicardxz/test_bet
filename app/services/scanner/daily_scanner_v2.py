"""
Daily Scanner Service V2 - With DataProvider Integration
Automatic anomaly detection for daily matches using external data providers
"""

from typing import List, Dict, Optional, Union, TYPE_CHECKING, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

from app.providers.base_provider import BaseDataProvider
from app.providers.models import MatchDetails, MatchOdds
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine
from app.services.anomaly import AnomalyEngine, AnomalyResult, ConfidenceCategory

# Type hints only - not imported at runtime
if TYPE_CHECKING:
    from app.services.stats.stats_engine import StatsEngine, TeamStats


logger = logging.getLogger(__name__)


class MarketPriority(str, Enum):
    """Market priority levels"""
    CRITICAL = "CRITICAL"      # HT Under, Extreme Under
    HIGH = "HIGH"              # FT Under/Over, HT Over
    MEDIUM = "MEDIUM"          # BTTS
    LOW = "LOW"                # Other markets


@dataclass
class SourceStatus:
    """Status of data source for a scan"""
    provider: str = ""
    data_mode: str = "MOCK"  # "MOCK" or "REAL"
    matches_found: int = 0
    markets_analyzed: int = 0
    odds_available: int = 0
    missing_odds: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScanStatistics:
    """Statistics for a scan run"""
    matches_fetched: int = 0
    matches_analyzable: int = 0
    ignored_no_odds: int = 0
    ignored_no_history: int = 0
    ignored_low_quality: int = 0
    provider_errors: int = 0
    total_anomalies: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScanResult:
    """Result of a market scan with ranking information"""
    
    # Match Info (required fields first)
    match_id: str
    home_team: str
    away_team: str
    league: str
    match_date: str
    market_type: str
    market_priority: MarketPriority
    
    # Optional fields with defaults
    country: str = ""
    kickoff_time: str = ""
    line: Optional[float] = None
    bookmaker_odds: Optional[float] = None
    bookmaker: str = "Unknown"
    
    # Anomaly Analysis
    anomaly_result: Optional[AnomalyResult] = None
    
    # Data Quality
    data_quality_score: float = 0.0
    home_sample_size: int = 0
    away_sample_size: int = 0
    h2h_available: bool = False
    
    # Ranking
    final_score: float = 0.0
    rank: int = 0
    
    # Metadata
    scan_timestamp: str = ""
    provider: str = ""
    data_source: str = "MOCK"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result["market_priority"] = self.market_priority.value
        if self.anomaly_result:
            result["anomaly_result"] = self.anomaly_result.to_dict()
        return result


class DailyScannerServiceV2:
    """
    Daily Scanner Service V2 with DataProvider Integration
    
    Features:
    - Fetch matches from external providers (SofaScore, Mock, etc.)
    - Calculate statistics from historical data
    - Run anomaly detection on priority markets
    - Handle missing data gracefully
    - Rank and sort results
    """
    
    def __init__(
        self,
        provider: BaseDataProvider,
        anomaly_engine: Optional[AnomalyEngine] = None,
        is_real_data: bool = False
    ):
        """
        Initialize scanner service
        
        Args:
            provider: Data provider (MockProvider, SofaScoreProvider, etc.)
            anomaly_engine: Optional AnomalyEngine instance
            is_real_data: Whether using real data (affects odds handling)
        """
        self.provider = provider
        self.is_real_data = is_real_data
        self.anomaly_engine = anomaly_engine or AnomalyEngine()
        
        # Configuration
        self.min_sample_size = 8
        self.min_anomaly_score = 50.0
        self.min_confidence = ConfidenceCategory.MEDIUM
        self.min_data_quality = 0.6
        self.max_results = 20
        
        # Market priorities
        self.market_config = self._get_market_config()
        
        # Statistics tracking
        self.scan_stats = ScanStatistics()
        
        source_tag = "REAL" if is_real_data else "MOCK"
        logger.info(f"DailyScannerServiceV2 initialized: {source_tag} data, provider: {provider.config.name}")
    
    def _get_market_config(self) -> Dict[str, Dict]:
        """Get market configuration with priorities"""
        return {
            # CRITICAL Priority
            "ht_under_05": {
                "priority": MarketPriority.CRITICAL,
                "weight": 1.5,
                "line": 0.5
            },
            "ft_under_105": {
                "priority": MarketPriority.CRITICAL,
                "weight": 1.4,
                "line": 10.5
            },
            "ft_under_85": {
                "priority": MarketPriority.CRITICAL,
                "weight": 1.3,
                "line": 8.5
            },
            
            # HIGH Priority
            "ft_under_25": {
                "priority": MarketPriority.HIGH,
                "weight": 1.2,
                "line": 2.5
            },
            "ft_under_15": {
                "priority": MarketPriority.HIGH,
                "weight": 1.2,
                "line": 1.5
            },
            "ht_over_05": {
                "priority": MarketPriority.HIGH,
                "weight": 1.1,
                "line": 0.5
            },
            
            # MEDIUM Priority
            "btts": {
                "priority": MarketPriority.MEDIUM,
                "weight": 1.0,
                "line": None
            },
            "ft_over_25": {
                "priority": MarketPriority.MEDIUM,
                "weight": 0.9,
                "line": 2.5
            }
        }
    
    def scan_today(
        self,
        competition_ids: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scan today's matches for anomalies and return structured response
        
        Args:
            competition_ids: Optional list of competition IDs to filter
            max_results: Maximum number of results to return
            
        Returns:
            Dict with source_status, single_bets, combinations, raw_anomalies
        """
        logger.info("Starting daily scan...")
        
        # Initialize source status
        source_status = SourceStatus(
            provider=self.provider.config.name,
            data_mode="REAL" if self.is_real_data else "MOCK"
        )
        
        # Reset statistics
        self.scan_stats = ScanStatistics()
        
        # 1. Fetch today's matches
        matches_response = self.provider.get_today_matches(competition_ids)
        
        if not matches_response.success:
            logger.error(f"Failed to fetch matches: {matches_response.error}")
            source_status.errors.append(matches_response.error or "Failed to fetch matches")
            self.scan_stats.provider_errors += 1
            return {
                "source_status": source_status.to_dict(),
                "single_bets": [],
                "combinations": [],
                "raw_anomalies": []
            }
        
        matches = matches_response.data
        self.scan_stats.matches_fetched = len(matches)
        source_status.matches_found = len(matches)
        source_tag = "REAL" if self.is_real_data else "MOCK"
        logger.info(f"[{source_tag}] Fetched {len(matches)} matches")
        
        # 2. Scan each match
        all_results = []
        
        for match in matches:
            try:
                match_results = self._scan_match(match)
                all_results.extend(match_results)
            except Exception as e:
                logger.error(f"Error scanning match {match.id}: {e}")
                source_status.errors.append(f"Match {match.id}: {str(e)}")
                self.scan_stats.provider_errors += 1
                continue
        
        self.scan_stats.total_anomalies = len(all_results)
        source_status.markets_analyzed = len(all_results)
        logger.info(f"Generated {len(all_results)} scan results")
        
        # 3. Filter weak anomalies
        filtered_results = self._filter_results(all_results)
        logger.info(f"After filtering: {len(filtered_results)} results")
        
        # 4. Rank and sort
        ranked_results = self._rank_results(filtered_results)
        
        # 5. Limit results
        max_res = max_results or self.max_results
        final_results = ranked_results[:max_res]
        
        # 6. Convert to BetCandidates
        single_bets = self._convert_to_bet_candidates(final_results)
        
        # 7. Generate combinations
        combinations = self._generate_combinations(single_bets)
        
        # 8. Track odds availability
        source_status.odds_available = sum(1 for r in final_results if r.bookmaker_odds is not None)
        source_status.missing_odds = sum(1 for r in final_results if r.bookmaker_odds is None)
        
        # Log statistics
        logger.info(f"Scan Statistics: {self.scan_stats.to_dict()}")
        logger.info(f"Returning top {len(final_results)} results")
        
        return {
            "source_status": source_status.to_dict(),
            "single_bets": [bet.to_dict() for bet in single_bets],
            "combinations": [combo.to_dict() for combo in combinations],
            "raw_anomalies": [r.to_dict() for r in final_results]
        }
    
    def _convert_to_bet_candidates(self, scan_results: List[ScanResult]) -> List:
        """Convert ScanResults to BetCandidates"""
        from app.services.betting.scan_result_converter import scan_results_to_bet_candidates
        return scan_results_to_bet_candidates(scan_results, self.is_real_data)
    
    def _generate_combinations(self, bet_candidates: List) -> List:
        """Generate bet combinations from single bets"""
        from app.services.betting.bet_portfolio_engine import BetPortfolioEngine
        engine = BetPortfolioEngine()
        return engine.generate_combinations(bet_candidates)
    
    def get_scan_statistics(self) -> ScanStatistics:
        """Get statistics from the last scan"""
        return self.scan_stats
    
    def _scan_match(self, match: MatchDetails) -> List[ScanResult]:
        """Scan a single match for anomalies"""
        
        source_tag = "REAL" if self.is_real_data else "MOCK"
        logger.info(f"[{source_tag}] Scanning: {match.home_team.name} vs {match.away_team.name} ({match.competition.name})")
        
        results = []
        
        # 1. Get team statistics
        home_stats = self._get_team_stats(match.home_team.id, match.home_team.name)
        away_stats = self._get_team_stats(match.away_team.id, match.away_team.name)
        
        if not home_stats or not away_stats:
            logger.warning(f"[{source_tag}] Ignored {match.id}: No history available")
            self.scan_stats.ignored_no_history += 1
            return results
        
        # 2. Calculate data quality
        data_quality = self._calculate_data_quality(home_stats, away_stats)
        
        if data_quality < self.min_data_quality:
            logger.warning(f"[{source_tag}] Ignored {match.id}: Data quality too low ({data_quality:.2f})")
            self.scan_stats.ignored_low_quality += 1
            return results
        
        self.scan_stats.matches_analyzable += 1
        
        # 3. Get H2H (optional)
        h2h_available = self._get_h2h(match.home_team.id, match.away_team.id)
        
        # 4. Get odds
        odds_response = self.provider.get_odds(match.id)
        
        if not odds_response.success:
            if self.is_real_data:
                # In real mode, skip if no odds available
                logger.warning(f"[{source_tag}] Ignored {match.id}: Odds missing")
                self.scan_stats.ignored_no_odds += 1
                return results
            else:
                # In mock mode, generate default odds
                logger.debug(f"[{source_tag}] No odds, using defaults (mock mode)")
                odds_list = self._generate_default_odds()
        else:
            odds_list = odds_response.data
            logger.debug(f"[{source_tag}] Found {len(odds_list)} odds for match {match.id}")
        
        # 5. Analyze each market
        for odds in odds_list:
            try:
                result = self._analyze_market(
                    match=match,
                    odds=odds,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    data_quality=data_quality,
                    h2h_available=h2h_available
                )
                
                if result:
                    results.append(result)
                    logger.debug(f"[{source_tag}] Anomaly found: {result.market_type} (score: {result.final_score:.1f})")
            
            except Exception as e:
                logger.warning(f"[{source_tag}] Error analyzing market {odds.market_type}: {e}")
                continue
        
        return results
    
    def _get_team_stats(self, team_id: str, team_name: str) -> Optional[Any]:
        """Get team statistics from recent matches using provider adapter"""
        
        try:
            # Import provider adapter (no database dependency)
            from app.services.stats.provider_adapter import StatsEngineProviderAdapter
            
            # Fetch recent matches
            response = self.provider.get_team_recent_matches(team_id, limit=15)
            
            if not response.success or not response.data:
                logger.warning(f"No recent matches for team {team_name}")
                return None
            
            recent_matches = response.data
            
            # Calculate stats using provider adapter
            adapter = StatsEngineProviderAdapter()
            stats = adapter.calculate_from_provider_matches(
                team_id=team_id,
                team_name=team_name,
                matches=recent_matches
            )
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting stats for team {team_name}: {e}")
            return None
    
    def _calculate_data_quality(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> float:
        """Calculate overall data quality score"""
        
        # Sample size score
        min_sample = min(home_stats.sample_size, away_stats.sample_size)
        sample_score = min(1.0, min_sample / 15.0)
        
        # Data quality scores
        home_quality = home_stats.data_quality_score
        away_quality = away_stats.data_quality_score
        avg_quality = (home_quality + away_quality) / 2
        
        # Combined score
        return (sample_score * 0.4 + avg_quality * 0.6)
    
    def _get_h2h(self, team_a_id: str, team_b_id: str) -> bool:
        """Get head-to-head data (returns True if available)"""
        
        try:
            response = self.provider.get_head_to_head(team_a_id, team_b_id)
            return response.success and response.data.total_matches > 0
        except Exception as e:
            logger.debug(f"H2H not available: {e}")
            return False
    
    def _generate_default_odds(self) -> List[MatchOdds]:
        """Generate default odds for priority markets when odds unavailable"""
        
        return [
            MatchOdds(
                bookmaker="Default",
                market_type="ht_under_05",
                line=0.5,
                under_odds=2.50,
                over_odds=1.55
            ),
            MatchOdds(
                bookmaker="Default",
                market_type="ft_under_25",
                line=2.5,
                under_odds=2.20,
                over_odds=1.70
            ),
            MatchOdds(
                bookmaker="Default",
                market_type="btts",
                yes_odds=2.00,
                no_odds=1.90
            )
        ]
    
    def _analyze_market(
        self,
        match: MatchDetails,
        odds: MatchOdds,
        home_stats: TeamStats,
        away_stats: TeamStats,
        data_quality: float,
        h2h_available: bool
    ) -> Optional[ScanResult]:
        """Analyze a specific market for anomalies"""
        
        market_type = odds.market_type
        
        # Check if market is in our config
        if market_type not in self.market_config:
            return None
        
        market_info = self.market_config[market_type]
        
        # Determine bookmaker odds to use
        if "under" in market_type:
            bookmaker_odds = odds.under_odds
        elif "over" in market_type:
            bookmaker_odds = odds.over_odds
        elif market_type == "btts":
            bookmaker_odds = odds.yes_odds
        else:
            return None
        
        if not bookmaker_odds:
            return None
        
        # Run anomaly detection
        try:
            anomaly_result = self.anomaly_engine.analyze_market(
                match_id=match.id,
                market_type=market_type,
                bookmaker_odds=bookmaker_odds,
                home_stats=home_stats,
                away_stats=away_stats,
                line=market_info.get("line")
            )
            
            # Create scan result
            scan_result = ScanResult(
                match_id=match.id,
                home_team=match.home_team.name,
                away_team=match.away_team.name,
                league=match.competition.name,
                country=match.competition.country if match.competition.country else "",
                kickoff_time=match.match_date.isoformat(),
                match_date=match.match_date.isoformat(),
                market_type=market_type,
                market_priority=market_info["priority"],
                line=market_info.get("line"),
                bookmaker_odds=bookmaker_odds,
                bookmaker=odds.bookmaker,
                anomaly_result=anomaly_result,
                data_quality_score=data_quality,
                home_sample_size=home_stats.sample_size,
                away_sample_size=away_stats.sample_size,
                h2h_available=h2h_available,
                scan_timestamp=datetime.utcnow().isoformat(),
                provider=self.provider.config.name,
                data_source="REAL" if self.is_real_data else "MOCK"
            )
            
            return scan_result
        
        except Exception as e:
            logger.error(f"Error in anomaly detection for {market_type}: {e}")
            return None
    
    def _filter_results(self, results: List[ScanResult]) -> List[ScanResult]:
        """Filter out weak anomalies"""
        
        filtered = []
        
        for result in results:
            if not result.anomaly_result:
                continue
            
            # Check anomaly score
            if result.anomaly_result.anomaly_score < self.min_anomaly_score:
                continue
            
            # Check confidence
            if result.anomaly_result.confidence_category == ConfidenceCategory.LOW:
                if self.min_confidence != ConfidenceCategory.LOW:
                    continue
            
            # Check sample size
            min_sample = min(result.home_sample_size, result.away_sample_size)
            if min_sample < self.min_sample_size:
                continue
            
            # Check data quality
            if result.data_quality_score < self.min_data_quality:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _rank_results(self, results: List[ScanResult]) -> List[ScanResult]:
        """Rank and sort results by final score"""
        
        for result in results:
            # Base score from anomaly
            base_score = result.anomaly_result.anomaly_score if result.anomaly_result else 0
            
            # Market priority weight
            market_info = self.market_config.get(result.market_type, {})
            priority_weight = market_info.get("weight", 1.0)
            
            # Data quality bonus
            quality_bonus = result.data_quality_score * 10
            
            # H2H bonus
            h2h_bonus = 5 if result.h2h_available else 0
            
            # Calculate final score
            result.final_score = (base_score * priority_weight) + quality_bonus + h2h_bonus
        
        # Sort by final score
        sorted_results = sorted(results, key=lambda x: x.final_score, reverse=True)
        
        # Assign ranks
        for i, result in enumerate(sorted_results, 1):
            result.rank = i
        
        return sorted_results
    
    def get_summary(self, results: List[ScanResult]) -> Dict:
        """Generate summary statistics"""
        
        if not results:
            return {
                "total_results": 0,
                "by_priority": {},
                "by_confidence": {},
                "avg_anomaly_score": 0,
                "avg_data_quality": 0
            }
        
        # Count by priority
        by_priority = {}
        for result in results:
            priority = result.market_priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        # Count by confidence
        by_confidence = {}
        for result in results:
            if result.anomaly_result:
                conf = result.anomaly_result.confidence_category.value
                by_confidence[conf] = by_confidence.get(conf, 0) + 1
        
        # Averages
        avg_anomaly = sum(
            r.anomaly_result.anomaly_score for r in results if r.anomaly_result
        ) / len(results)
        
        avg_quality = sum(r.data_quality_score for r in results) / len(results)
        
        return {
            "total_results": len(results),
            "by_priority": by_priority,
            "by_confidence": by_confidence,
            "avg_anomaly_score": round(avg_anomaly, 2),
            "avg_data_quality": round(avg_quality, 2),
            "provider": self.provider.config.name
        }
