"""
Daily Scanner Service V2 - With DataProvider Integration
Automatic anomaly detection for daily matches using external data providers
"""

from __future__ import annotations
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
        
        # Configuration - RELAXED FOR MASSIVE SCANNING
        self.min_sample_size = 3  # Très bas pour LAYER 1
        self.min_anomaly_score = 30.0  # Baissé pour plus de matches
        self.min_confidence = ConfidenceCategory.LOW  # Inclure LOW confidence
        self.min_data_quality = 0.4  # Baissé pour inclusivité
        self.max_results = 100  # Augmenté pour plus de visibilité
        
        # Market priorities
        self.market_config = self._get_market_config()
        
        # Statistics tracking
        self.scan_stats = ScanStatistics()
        
        source_tag = "REAL" if is_real_data else "MOCK"
        logger.info(f"DailyScannerServiceV2 initialized: {source_tag} data, provider: {provider.config.name}")
    
    def _get_market_config(self) -> Dict[str, Dict]:
        """Get market configuration with priorities - DIVERSIFIED"""
        return {
            # CRITICAL Priority - Expanded
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
            "btts": {
                "priority": MarketPriority.CRITICAL,
                "weight": 1.3,
                "line": None
            },
            
            # HIGH Priority - Diversified
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
            "ft_over_25": {
                "priority": MarketPriority.HIGH,
                "weight": 1.1,
                "line": 2.5
            },
            "ft_over_35": {
                "priority": MarketPriority.HIGH,
                "weight": 1.1,
                "line": 3.5
            },
            
            # MEDIUM Priority - New patterns
            "ht_over_15": {
                "priority": MarketPriority.MEDIUM,
                "weight": 1.0,
                "line": 1.5
            },
            "ft_over_45": {
                "priority": MarketPriority.MEDIUM,
                "weight": 1.0,
                "line": 4.5
            },
            "both_teams_to_score": {
                "priority": MarketPriority.MEDIUM,
                "weight": 1.0,
                "line": None
            },
            "first_half_goals": {
                "priority": MarketPriority.MEDIUM,
                "weight": 0.9,
                "line": 0.5
            },
            
            # LOW Priority - Experimental
            "correct_score": {
                "priority": MarketPriority.LOW,
                "weight": 0.8,
                "line": None
            },
            "asian_handicap": {
                "priority": MarketPriority.LOW,
                "weight": 0.7,
                "line": None
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
        
        # 2. Filtrer par status (PHASE 1)
        upcoming_matches = []
        live_matches = []
        finished_matches = []
        cancelled_matches = []
        other_matches = []
        
        for match in matches:
            status = getattr(match, 'status', 'UNKNOWN').upper()
            
            if status in ['UPCOMING', 'NS']:  # NS = Not Started
                upcoming_matches.append(match)
            elif status in ['LIVE', 'IN_PLAY', 'PAUSED']:
                live_matches.append(match)
            elif status in ['FINISHED', 'FT', 'AWARDED', 'WALKOVER']:
                finished_matches.append(match)
            elif status in ['CANCELLED', 'POSTPONED', 'ABANDONED', 'SUSPENDED']:
                cancelled_matches.append(match)
            else:
                other_matches.append(match)
        
        logger.info(f"[{source_tag}] Status breakdown - Upcoming: {len(upcoming_matches)}, Live: {len(live_matches)}, Finished: {len(finished_matches)}, Cancelled: {len(cancelled_matches)}, Other: {len(other_matches)}")
        
        # 3. Scanner uniquement UPCOMING et LIVE
        target_matches = upcoming_matches + live_matches
        all_results = []
        
        for match in target_matches:
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
        
        # 9. Status breakdown (PHASE 1)
        status_breakdown = {
            "upcoming_count": len(upcoming_matches),
            "live_count": len(live_matches),
            "finished_count": len(finished_matches),
            "cancelled_count": len(cancelled_matches),
            "other_count": len(other_matches),
            "target_matches_count": len(target_matches),
            "analyzed_upcoming": len([r for r in final_results if any(m.status in ['UPCOMING', 'NS'] for m in upcoming_matches if m.id == r.fixture_id)]),
            "analyzed_live": len([r for r in final_results if any(m.status in ['LIVE', 'IN_PLAY', 'PAUSED'] for m in live_matches if m.id == r.fixture_id)]),
            "skipped_finished": len(finished_matches),
            "skipped_cancelled": len(cancelled_matches)
        }
        
        # Log statistics
        logger.info(f"Scan Statistics: {self.scan_stats.to_dict()}")
        logger.info(f"Status breakdown: {status_breakdown}")
        logger.info(f"Returning top {len(final_results)} results")
        
        return {
            "source_status": source_status.to_dict(),
            "single_bets": [bet.to_dict() for bet in single_bets],
            "combinations": [combo.to_dict() for combo in combinations],
            "raw_anomalies": [r.to_dict() for r in final_results],
            "status_breakdown": status_breakdown
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
        
        # 4. Get odds (OPTIONNEL - ne pas bloquer l'analyse)
        odds_response = self.provider.get_odds(match.id)
        
        if not odds_response.success:
            # Ne pas skipper l'analyse si pas d'odds
            logger.info(f"[{source_tag}] No odds for {match.id} - continuing with statistical analysis")
            odds_list = []  # Pas d'odds = analyse statistique uniquement
        else:
            odds_list = odds_response.data
            logger.debug(f"[{source_tag}] Found {len(odds_list)} odds for match {match.id}")
        
        # 5. Analyze each market (si odds disponibles)
        if odds_list:
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
        
        # 6. Analyse statistique même sans odds
        if not odds_list:
            try:
                statistical_result = self._analyze_statistical_patterns(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    data_quality=data_quality,
                    h2h_available=h2h_available
                )
                
                if statistical_result:
                    results.append(statistical_result)
                    logger.debug(f"[{source_tag}] Statistical pattern found: {statistical_result.market_type} (score: {statistical_result.final_score:.1f})")
            
            except Exception as e:
                logger.warning(f"[{source_tag}] Error analyzing statistical patterns: {e}")
        
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
        """Rank and sort results by final score - PHASE 5: Useful bet tracks"""
        
        # PHASE 5: Définir les marchés utiles vs extrêmes
        USEFUL_MARKETS = {
            'HT_UNDER_0_5', 'HT_UNDER_1_5', 'HT_OVER_0_5', 'HT_OVER_1_5',
            'UNDER_1_5', 'UNDER_2_5', 'UNDER_3_5',
            'OVER_1_5', 'OVER_2_5',
            'BTTS_YES', 'BTTS_NO'
        }
        
        EXTREME_MARKETS = {
            'UNDER_4_5', 'UNDER_5_5', 'UNDER_6_5', 'UNDER_7_5', 'UNDER_8_5',
            'UNDER_9_5', 'UNDER_10_5', 'UNDER_11_5', 'UNDER_12_5'
        }
        
        for result in results:
            # Base score from anomaly
            base_score = result.anomaly_result.anomaly_score if result.anomaly_result else 0
            
            # Market priority weight
            market_info = self.market_config.get(result.market_type, {})
            priority_weight = market_info.get("weight", 1.0)
            
            # PHASE 5: Bonus pour marchés utiles
            market_bonus = 0
            if result.market_type in USEFUL_MARKETS:
                market_bonus = 15  # Bonus pour marchés utiles
            elif result.market_type in EXTREME_MARKETS:
                market_bonus = -20  # Pénalité pour marchés extrêmes
            
            # Data quality bonus
            quality_bonus = result.data_quality_score * 10
            
            # H2H bonus
            h2h_bonus = 5 if result.h2h_available else 0
            
            # PHASE 5: Hit rate bonus (plus le hit rate est élevé, meilleur)
            hit_rate = result.anomaly_result.hit_rate if result.anomaly_result else 0.5
            hit_rate_bonus = hit_rate * 10
            
            # PHASE 5: Sample size bonus (plus d'échantillons = plus fiable)
            sample_size = result.anomaly_result.sample_size if result.anomaly_result else 0
            sample_bonus = min(sample_size / 10, 10)  # Max 10 points bonus
            
            # Calculate final score
            result.final_score = (base_score * priority_weight) + quality_bonus + h2h_bonus + market_bonus + hit_rate_bonus + sample_bonus
        
        # Sort by final score
        sorted_results = sorted(results, key=lambda x: x.final_score, reverse=True)
        
        # PHASE 5: Définir le best pick pour chaque résultat
        for result in sorted_results:
            if result.anomaly_result:
                # Créer le best_pick selon les spécifications
                result.best_pick = {
                    "market": result.market_type,
                    "label": self._get_market_label(result.market_type),
                    "hit_rate": round(result.anomaly_result.hit_rate * 100, 1),
                    "fair_odd": round(1 / result.anomaly_result.hit_rate, 2) if result.anomaly_result.hit_rate > 0 else 0.0,
                    "sample_size": result.anomaly_result.sample_size,
                    "confidence": self._get_confidence_level(result.anomaly_result.confidence_category),
                    "why": [result.anomaly_result.pattern_description] if result.anomaly_result.pattern_description else [],
                    "is_useful": result.market_type in USEFUL_MARKETS,
                    "is_extreme": result.market_type in EXTREME_MARKETS
                }
        
        # Assign ranks
        for i, result in enumerate(sorted_results, 1):
            result.rank = i
        
        return sorted_results
    
    def _get_market_label(self, market_type: str) -> str:
        """Get human readable market label"""
        labels = {
            'HT_UNDER_0_5': 'HT Under 0.5',
            'HT_UNDER_1_5': 'HT Under 1.5',
            'HT_OVER_0_5': 'HT Over 0.5',
            'HT_OVER_1_5': 'HT Over 1.5',
            'UNDER_1_5': 'Under 1.5',
            'UNDER_2_5': 'Under 2.5',
            'UNDER_3_5': 'Under 3.5',
            'OVER_1_5': 'Over 1.5',
            'OVER_2_5': 'Over 2.5',
            'BTTS_YES': 'BTTS Yes',
            'BTTS_NO': 'BTTS No',
            'LOW_TEMPO': 'Low Tempo',
            'HIGH_TEMPO': 'High Tempo',
            'SECOND_HALF_GOALS': 'Second Half Goals',
            'LATE_GOAL_PROFILE': 'Late Goals',
            'VOLATILE_MATCH': 'Volatile Match',
            'CHAOTIC_MATCH': 'Chaotic Match',
            'HOME_DOMINANT': 'Home Dominant',
            'AWAY_WEAKNESS': 'Away Weakness',
            'ASYMMETRIC_SCORING': 'Asymmetric Scoring'
        }
        return labels.get(market_type, market_type)
    
    def _get_confidence_level(self, confidence_category) -> str:
        """Get confidence level string"""
        try:
            return confidence_category.value.upper()
        except:
            return "MEDIUM"
    
    def _analyze_statistical_patterns(
        self,
        match: MatchDetails,
        home_stats: Any,
        away_stats: Any,
        data_quality: float,
        h2h_available: Any
    ) -> Optional[ScanResult]:
        """Analyze statistical patterns without odds"""
        
        source_tag = "REAL" if self.is_real_data else "MOCK"
        
        try:
            # Calculer les patterns statistiques
            patterns = self._calculate_statistical_patterns(home_stats, away_stats, h2h_available)
            
            if not patterns:
                return None
            
            # Choisir le meilleur pattern
            best_pattern = max(patterns, key=lambda p: p['score'])
            
            # Créer un ScanResult sans odds
            result = ScanResult(
                fixture_id=match.id,
                home_team=match.home_team.name,
                away_team=match.away_team.name,
                competition=match.competition.name,
                kickoff_time=match.kickoff_time,
                market_type=best_pattern['market'],
                market_priority=MarketPriority.MEDIUM,
                anomaly_result=AnomalyResult(
                    anomaly_score=best_pattern['score'],
                    confidence_category=ConfidenceCategory.MEDIUM,
                    statistical_significance=best_pattern.get('significance', 0.5),
                    pattern_description=best_pattern.get('description', ''),
                    hit_rate=best_pattern.get('hit_rate', 0.5),
                    sample_size=best_pattern.get('sample_size', 0),
                    variance=best_pattern.get('variance', 0.1)
                ),
                data_quality_score=data_quality,
                analysis_timestamp=datetime.now(),
                waiting_for_odds=True  # Indiquer qu'on attend les odds
            )
            
            # PHASE 6: Ajouter les scores de qualité et intérêt
            result.interest_score = self._calculate_interest_score(best_pattern, data_quality)
            result.confidence_score = self._calculate_confidence_score(best_pattern, data_quality)
            result.volatility_score = self._calculate_volatility_score(best_pattern)
            result.data_quality_score = data_quality
            
            logger.debug(f"[{source_tag}] Statistical pattern: {best_pattern['market']} (score: {best_pattern['score']:.1f})")
            return result
            
        except Exception as e:
            logger.error(f"[{source_tag}] Error in statistical pattern analysis: {e}")
            return None
    
    def _calculate_statistical_patterns(self, home_stats: Any, away_stats: Any, h2h_available: Any) -> List[Dict]:
        """Calculate various statistical patterns - PHASE 4: Diversified profiles"""
        
        patterns = []
        
        try:
            # Get basic stats
            home_matches = getattr(home_stats, 'matches_count', 10)
            away_matches = getattr(away_stats, 'matches_count', 10)
            total_matches = home_matches + away_matches
            
            # HT_UNDER_PROFILE
            if hasattr(home_stats, 'ht_goals_avg') and hasattr(away_stats, 'ht_goals_avg'):
                ht_avg = (home_stats.ht_goals_avg + away_stats.ht_goals_avg) / 2
                if ht_avg < 0.8:  # Moins de 0.8 buts en moyenne en 1ère mi-temps
                    patterns.append({
                        'market': 'HT_UNDER_1_5',
                        'score': 85 - (ht_avg * 20),
                        'description': f'Low HT goals average: {ht_avg:.2f}',
                        'hit_rate': 0.75,
                        'sample_size': total_matches,
                        'significance': 0.7
                    })
                elif ht_avg < 1.2:  # Moins de 1.2 buts = HT Under 0.5 possible
                    patterns.append({
                        'market': 'HT_UNDER_0_5',
                        'score': 80 - (ht_avg * 15),
                        'description': f'Very low HT goals: {ht_avg:.2f}',
                        'hit_rate': 0.65,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
            
            # HT_OVER_PROFILE
            if hasattr(home_stats, 'ht_goals_avg') and hasattr(away_stats, 'ht_goals_avg'):
                ht_avg = (home_stats.ht_goals_avg + away_stats.ht_goals_avg) / 2
                if ht_avg > 1.8:  # Plus de 1.8 buts en moyenne en 1ère mi-temps
                    patterns.append({
                        'market': 'HT_OVER_1_5',
                        'score': 70 + (ht_avg * 10),
                        'description': f'High HT goals average: {ht_avg:.2f}',
                        'hit_rate': 0.60,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
                elif ht_avg > 1.3:  # Plus de 1.3 buts = HT Over 0.5 probable
                    patterns.append({
                        'market': 'HT_OVER_0_5',
                        'score': 65 + (ht_avg * 8),
                        'description': f'Good HT scoring: {ht_avg:.2f}',
                        'hit_rate': 0.70,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
            
            # FT_UNDER_PROFILE
            if hasattr(home_stats, 'total_goals_avg') and hasattr(away_stats, 'total_goals_avg'):
                ft_avg = (home_stats.total_goals_avg + away_stats.total_goals_avg) / 2
                if ft_avg < 1.8:  # Moins de 1.8 buts = Under 1.5 fort
                    patterns.append({
                        'market': 'UNDER_1_5',
                        'score': 80 + ((2.0 - ft_avg) * 15),
                        'description': f'Very low scoring: {ft_avg:.2f} goals avg',
                        'hit_rate': 0.70,
                        'sample_size': total_matches,
                        'significance': 0.7
                    })
                elif ft_avg < 2.3:  # Moins de 2.3 buts = Under 2.5 probable
                    patterns.append({
                        'market': 'UNDER_2_5',
                        'score': 75 + ((2.5 - ft_avg) * 10),
                        'description': f'Low scoring games: {ft_avg:.2f} goals avg',
                        'hit_rate': 0.65,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
                elif ft_avg < 3.0:  # Moins de 3.0 buts = Under 3.5 possible
                    patterns.append({
                        'market': 'UNDER_3_5',
                        'score': 60 + ((3.5 - ft_avg) * 8),
                        'description': f'Moderate scoring: {ft_avg:.2f} goals avg',
                        'hit_rate': 0.60,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
            
            # FT_OVER_PROFILE
            if hasattr(home_stats, 'total_goals_avg') and hasattr(away_stats, 'total_goals_avg'):
                ft_avg = (home_stats.total_goals_avg + away_stats.total_goals_avg) / 2
                if ft_avg > 3.2:  # Plus de 3.2 buts = Over 2.5 fort
                    patterns.append({
                        'market': 'OVER_2_5',
                        'score': 70 + ((ft_avg - 3.2) * 12),
                        'description': f'High scoring games: {ft_avg:.2f} goals avg',
                        'hit_rate': 0.55,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
                elif ft_avg > 2.8:  # Plus de 2.8 buts = Over 2.5 probable
                    patterns.append({
                        'market': 'OVER_1_5',
                        'score': 75 + ((ft_avg - 2.8) * 10),
                        'description': f'Good scoring: {ft_avg:.2f} goals avg',
                        'hit_rate': 0.65,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
            
            # BTTS_PROFILE
            if hasattr(home_stats, 'btts_rate') and hasattr(away_stats, 'btts_rate'):
                btts_avg = (home_stats.btts_rate + away_stats.btts_rate) / 2
                if btts_avg > 0.75:  # Plus de 75% BTTS
                    patterns.append({
                        'market': 'BTTS_YES',
                        'score': 75 + (btts_avg * 10),
                        'description': f'Very high BTTS rate: {btts_avg:.2f}',
                        'hit_rate': btts_avg,
                        'sample_size': total_matches,
                        'significance': 0.7
                    })
                elif btts_avg > 0.6:  # Plus de 60% BTTS
                    patterns.append({
                        'market': 'BTTS_YES',
                        'score': 65 + (btts_avg * 8),
                        'description': f'High BTTS rate: {btts_avg:.2f}',
                        'hit_rate': btts_avg,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
                elif btts_avg < 0.25:  # Moins de 25% BTTS
                    patterns.append({
                        'market': 'BTTS_NO',
                        'score': 75 + ((1 - btts_avg) * 10),
                        'description': f'Very low BTTS rate: {btts_avg:.2f}',
                        'hit_rate': 1 - btts_avg,
                        'sample_size': total_matches,
                        'significance': 0.7
                    })
                elif btts_avg < 0.4:  # Moins de 40% BTTS
                    patterns.append({
                        'market': 'BTTS_NO',
                        'score': 65 + ((1 - btts_avg) * 8),
                        'description': f'Low BTTS rate: {btts_avg:.2f}',
                        'hit_rate': 1 - btts_avg,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
            
            # LOW_TEMPO / HIGH_TEMPO
            if hasattr(home_stats, 'total_goals_avg') and hasattr(away_stats, 'total_goals_avg'):
                goals_avg = (home_stats.total_goals_avg + away_stats.total_goals_avg) / 2
                if goals_avg < 2.0:  # Moins de 2 buts = LOW_TEMPO
                    patterns.append({
                        'market': 'LOW_TEMPO',
                        'score': 70 + ((2.5 - goals_avg) * 12),
                        'description': f'Low tempo matches: {goals_avg:.2f} goals avg',
                        'hit_rate': 0.65,
                        'sample_size': total_matches,
                        'significance': 0.6
                    })
                elif goals_avg > 3.0:  # Plus de 3 buts = HIGH_TEMPO
                    patterns.append({
                        'market': 'HIGH_TEMPO',
                        'score': 70 + ((goals_avg - 3.0) * 12),
                        'description': f'High tempo matches: {goals_avg:.2f} goals avg',
                        'hit_rate': 0.55,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
            
            # SECOND_HALF_GOALS
            if hasattr(home_stats, 'second_half_goals_avg') and hasattr(away_stats, 'second_half_goals_avg'):
                sh_avg = (home_stats.second_half_goals_avg + away_stats.second_half_goals_avg) / 2
                if sh_avg > 1.8:  # Plus de buts en 2ème mi-temps
                    patterns.append({
                        'market': 'SECOND_HALF_GOALS',
                        'score': 65 + (sh_avg * 8),
                        'description': f'Second half strong: {sh_avg:.2f} goals avg',
                        'hit_rate': 0.60,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
            
            # LATE_GOAL_PROFILE (basé sur buts après 75')
            if hasattr(home_stats, 'late_goals_rate') and hasattr(away_stats, 'late_goals_rate'):
                late_avg = (home_stats.late_goals_rate + away_stats.late_goals_rate) / 2
                if late_avg > 0.3:  # Plus de 30% buts tardifs
                    patterns.append({
                        'market': 'LATE_GOAL_PROFILE',
                        'score': 60 + (late_avg * 15),
                        'description': f'Late goals frequent: {late_avg:.2f} rate',
                        'hit_rate': 0.45,
                        'sample_size': total_matches,
                        'significance': 0.4
                    })
            
            # VOLATILE_MATCH
            if hasattr(home_stats, 'variance') and hasattr(away_stats, 'variance'):
                variance_avg = (home_stats.variance + away_stats.variance) / 2
                if variance_avg > 1.5:  # Variance élevée
                    patterns.append({
                        'market': 'VOLATILE_MATCH',
                        'score': 60 + (variance_avg * 10),
                        'description': f'High variance: {variance_avg:.2f}',
                        'hit_rate': 0.40,
                        'sample_size': total_matches,
                        'significance': 0.4
                    })
                elif variance_avg > 0.8:  # Variance modérée
                    patterns.append({
                        'market': 'CHAOTIC_MATCH',
                        'score': 55 + (variance_avg * 8),
                        'description': f'Moderate variance: {variance_avg:.2f}',
                        'hit_rate': 0.35,
                        'sample_size': total_matches,
                        'significance': 0.3
                    })
            
            # HOME_DOMINANT
            if hasattr(home_stats, 'home_win_rate') and hasattr(away_stats, 'away_loss_rate'):
                home_dominance = home_stats.home_win_rate * away_stats.away_loss_rate
                if home_dominance > 0.6:  # Forte dominance à domicile
                    patterns.append({
                        'market': 'HOME_DOMINANT',
                        'score': 65 + (home_dominance * 15),
                        'description': f'Home dominance: {home_dominance:.2f}',
                        'hit_rate': 0.65,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
            
            # AWAY_WEAKNESS
            if hasattr(away_stats, 'away_loss_rate') and hasattr(away_stats, 'away_goals_conceded_avg'):
                away_weakness = away_stats.away_loss_rate * away_stats.away_goals_conceded_avg
                if away_weakness > 1.5:  # Faiblesse extérieure forte
                    patterns.append({
                        'market': 'AWAY_WEAKNESS',
                        'score': 60 + (away_weakness * 10),
                        'description': f'Away weakness: {away_weakness:.2f}',
                        'hit_rate': 0.60,
                        'sample_size': total_matches,
                        'significance': 0.5
                    })
            
            # ASYMMETRIC_SCORING
            if hasattr(home_stats, 'goals_for_avg') and hasattr(home_stats, 'goals_against_avg') and \
               hasattr(away_stats, 'goals_for_avg') and hasattr(away_stats, 'goals_against_avg'):
                
                home_balance = abs(home_stats.goals_for_avg - home_stats.goals_against_avg)
                away_balance = abs(away_stats.goals_for_avg - away_stats.goals_against_avg)
                
                if home_balance > 1.5 or away_balance > 1.5:  # Asymétrie forte
                    patterns.append({
                        'market': 'ASYMMETRIC_SCORING',
                        'score': 55 + max(home_balance, away_balance) * 8,
                        'description': f'Asymmetric scoring: H:{home_balance:.1f} A:{away_balance:.1f}',
                        'hit_rate': 0.40,
                        'sample_size': total_matches,
                        'significance': 0.4
                    })
            
        except Exception as e:
            logger.error(f"Error calculating patterns: {e}")
        
        return patterns
    
    def _calculate_interest_score(self, pattern: Dict, data_quality: float) -> float:
        """PHASE 6: Calculate interest score (0-100) based on statistical interest"""
        
        score = 50.0  # Base score
        
        # Hit rate influence
        hit_rate = pattern.get('hit_rate', 0.5)
        if hit_rate > 0.7:
            score += 20
        elif hit_rate > 0.6:
            score += 10
        elif hit_rate < 0.3:
            score += 5  # Low hit rate can be interesting for contrarian bets
        
        # Sample size influence
        sample_size = pattern.get('sample_size', 0)
        if sample_size > 50:
            score += 15
        elif sample_size > 20:
            score += 10
        elif sample_size > 10:
            score += 5
        
        # Significance influence
        significance = pattern.get('significance', 0.5)
        score += significance * 20
        
        # Market type influence (certain markets more interesting)
        market = pattern.get('market', '')
        if 'BTTS' in market:
            score += 10
        elif 'HT_' in market:
            score += 8
        elif 'VOLATILE' in market or 'CHAOTIC' in market:
            score += 5
        
        # Data quality influence
        score += data_quality * 10
        
        return min(max(score, 0), 100)
    
    def _calculate_confidence_score(self, pattern: Dict, data_quality: float) -> float:
        """PHASE 6: Calculate confidence score (0-100) based on data reliability"""
        
        score = 0.0
        
        # Sample size is most important for confidence
        sample_size = pattern.get('sample_size', 0)
        if sample_size > 100:
            score += 40
        elif sample_size > 50:
            score += 30
        elif sample_size > 20:
            score += 20
        elif sample_size > 10:
            score += 10
        elif sample_size > 5:
            score += 5
        
        # Hit rate stability
        hit_rate = pattern.get('hit_rate', 0.5)
        if 0.4 <= hit_rate <= 0.8:  # Reasonable hit rates
            score += 20
        elif 0.3 <= hit_rate <= 0.9:
            score += 15
        else:
            score += 5  # Extreme hit rates are less reliable
        
        # Statistical significance
        significance = pattern.get('significance', 0.5)
        score += significance * 25
        
        # Data quality
        score += data_quality * 15
        
        return min(max(score, 0), 100)
    
    def _calculate_volatility_score(self, pattern: Dict) -> float:
        """PHASE 6: Calculate volatility score (0-100) based on pattern variance"""
        
        score = 50.0  # Base volatility
        
        # Market type volatility
        market = pattern.get('market', '')
        if 'VOLATILE' in market or 'CHAOTIC' in market:
            score += 30
        elif 'LATE_GOAL' in market:
            score += 25
        elif 'BTTS' in market:
            score += 20
        elif 'OVER' in market:
            score += 15
        elif 'UNDER' in market:
            score += 10
        elif 'HT_' in market:
            score += 5
        
        # Hit rate volatility (extreme rates = more volatile)
        hit_rate = pattern.get('hit_rate', 0.5)
        if hit_rate > 0.8 or hit_rate < 0.2:
            score += 20
        elif hit_rate > 0.7 or hit_rate < 0.3:
            score += 10
        
        # Sample size (smaller samples = more volatile)
        sample_size = pattern.get('sample_size', 0)
        if sample_size < 10:
            score += 15
        elif sample_size < 20:
            score += 10
        elif sample_size < 50:
            score += 5
        
        return min(max(score, 0), 100)
    
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
