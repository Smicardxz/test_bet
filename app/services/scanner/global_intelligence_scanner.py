"""
GLOBAL FOOTBALL INTELLIGENCE SCANNER

Nouvelle architecture LAYER 1-2-3 pour un scanning massif et intelligent

LAYER 1 = MASSIVE SCAN (pas de filtrage agressif)
LAYER 2 = STATISTICAL PROFILING (tous les profils)
LAYER 3 = MARKET INEFFICIENCY (avec odds si disponibles)

OBJECTIF : Scanner massivement et détecter tous les patterns intéressants
"""

from typing import List, Dict, Optional, Any, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from app.providers.base_provider import BaseDataProvider
from app.providers.models import MatchDetails, MatchOdds
from app.services.signals.signal_engine import SignalEngine, StatisticalSignal
from app.services.analysis.match_profiler import MatchProfiler, MatchProfile
from app.services.analysis.pattern_detection_engine import PatternDetectionEngine, PatternDetectionResult

if TYPE_CHECKING:
    from app.services.stats.stats_engine import TeamStats

logger = logging.getLogger(__name__)


class ScanLayer(str, Enum):
    """Layers du scanning"""
    LAYER1_MASSIVE_SCAN = "LAYER1_MASSIVE_SCAN"
    LAYER2_STATISTICAL_PROFILING = "LAYER2_STATISTICAL_PROFILING"
    LAYER3_MARKET_INEFFICIENCY = "LAYER3_MARKET_INEFFICIENCY"


@dataclass
class GlobalScanResult:
    """Résultat du scan global - intelligence first"""
    
    # Match info
    match_id: str
    home_team: str
    away_team: str
    league: str
    country: str
    match_date: str
    kickoff_time: str
    
    # Layer 1 - Basic scan info
    data_source: str = "UNKNOWN"
    sample_size_home: int = 0
    sample_size_away: int = 0
    data_quality_score: float = 0.0
    
    # Layer 2 - Statistical profiling
    match_profile: Optional[MatchProfile] = None
    statistical_signals: List[StatisticalSignal] = field(default_factory=list)
    pattern_detection: Optional[PatternDetectionResult] = None
    
    # Layer 3 - Market analysis (si odds disponibles)
    market_inefficiencies: List[Dict[str, Any]] = field(default_factory=list)
    bookmaker_odds: Dict[str, float] = field(default_factory=dict)
    
    # Intelligence scores
    intelligence_score: float = 0.0  # Score d'intérêt global
    pattern_rarity_score: float = 0.0  # Rareté du pattern
    stability_score: float = 0.0      # Stabilité statistique
    market_edge_score: float = 0.0    # Edge bookmaker (si applicable)
    
    # Contextual explanations
    key_insights: List[str] = field(default_factory=list)
    why_interesting: str = ""
    pattern_explanation: str = ""
    
    # Metadata
    scan_timestamp: str = ""
    provider: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league": self.league,
            "country": self.country,
            "match_date": self.match_date,
            "kickoff_time": self.kickoff_time,
            "data_source": self.data_source,
            "sample_size_home": self.sample_size_home,
            "sample_size_away": self.sample_size_away,
            "data_quality_score": self.data_quality_score,
            "intelligence_score": self.intelligence_score,
            "pattern_rarity_score": self.pattern_rarity_score,
            "stability_score": self.stability_score,
            "market_edge_score": self.market_edge_score,
            "key_insights": self.key_insights,
            "why_interesting": self.why_interesting,
            "pattern_explanation": self.pattern_explanation,
            "scan_timestamp": self.scan_timestamp,
            "provider": self.provider
        }
        
        # Add complex objects
        if self.match_profile:
            result["match_profile"] = self.match_profile.to_dict()
        
        result["statistical_signals"] = [s.to_dict() for s in self.statistical_signals]
        
        if self.pattern_detection:
            result["pattern_detection"] = self.pattern_detection.to_dict()
        
        result["market_inefficiencies"] = self.market_inefficiencies
        result["bookmaker_odds"] = self.bookmaker_odds
        
        return result


class GlobalIntelligenceScanner:
    """
    GLOBAL FOOTBALL INTELLIGENCE SCANNER
    
    Architecture LAYER 1-2-3 pour scanning massif et intelligent
    """
    
    def __init__(
        self,
        provider: BaseDataProvider,
        include_secondary_leagues: bool = True,
        include_obscure_competitions: bool = True,
        min_sample_size_layer1: int = 3,  # Très bas pour LAYER 1
        min_sample_size_layer2: int = 5,  # Modéré pour LAYER 2
        min_sample_size_layer3: int = 8   # Standard pour LAYER 3
    ):
        """
        Initialize Global Intelligence Scanner
        
        Args:
            provider: Data provider
            include_secondary_leagues: Inclure ligues secondaires
            include_obscure_competitions: Inclure compétitions obscures
            min_sample_size_layer1: Sample size minimum pour LAYER 1 (massive scan)
            min_sample_size_layer2: Sample size minimum pour LAYER 2 (profiling)
            min_sample_size_layer3: Sample size minimum pour LAYER 3 (market analysis)
        """
        self.provider = provider
        self.include_secondary_leagues = include_secondary_leagues
        self.include_obscure_competitions = include_obscure_competitions
        
        # Layer thresholds
        self.min_sample_size_layer1 = min_sample_size_layer1
        self.min_sample_size_layer2 = min_sample_size_layer2
        self.min_sample_size_layer3 = min_sample_size_layer3
        
        # Engines
        self.signal_engine = SignalEngine()
        self.match_profiler = MatchProfiler()
        self.pattern_engine = PatternDetectionEngine()
        
        # Expanded competition list for global coverage
        self.global_competitions = self._get_global_competition_list()
        
        logger.info(f"GlobalIntelligenceScanner initialized")
        logger.info(f"Secondary leagues: {include_secondary_leagues}")
        logger.info(f"Obscure competitions: {include_obscure_competitions}")
        logger.info(f"Global competitions: {len(self.global_competitions)}")
    
    def _get_global_competition_list(self) -> List[str]:
        """Get expanded list of global competitions for massive scanning"""
        
        base_competitions = [
            # Europe major
            "CL", "EL", "ECL",  # Champions League, Europa League, Conference League
            "PL", "L1", "BL", "SA", "LIGA",  # Premier League, Ligue 1, Bundesliga, Serie A, La Liga
            # Europe second divisions
            "CH", "L2", "2BL", "SB", "LIGA2",  # Championship, Ligue 2, 2. Bundesliga, Serie B, LaLiga2
        ]
        
        if self.include_secondary_leagues:
            base_competitions.extend([
                # Lower divisions
                "L1C", "L2C", "3L", "NLD", "SCD",  # League 1/2 conferences, 3rd league, etc.
                # Reserve leagues
                "PLR", "L1R", "BLR", "SAR",  # Premier League Reserve, etc.
                # Women leagues
                "WSL", "D1F", "FBL", "SFW",  # Women's Super League, Division 1 Féminine, etc.
                # Youth leagues
                "U19CL", "U19EL",  # UEFA Youth competitions
            ])
        
        if self.include_obscure_competitions:
            base_competitions.extend([
                # Asia obscure
                "J3", "K2", "CFA", "VLEAGUE", "IL",  # Japan J3, Korea K2, China FA, Vietnam, Indonesia
                # Africa obscure
                "ETP", "SPL", "KYL", "ML",  # Ethiopia, Sudan, Kyrgyzstan, Mongolia
                # Americas obscure
                "CB", "BF", "ISL", "FIL",  # Colombia B, Bolivia, Iceland lower, Finland lower
                # Regional cups
                "FA_CUP", "DFB_POKAL", "COPA_DEL_REY", "COUPE_DE_FRANCE",
                # Small countries
                "WELSH", "SCOTTISH_CH", "IRISH_PREM", "NIFL",  # Wales, Scotland, Ireland, Northern Ireland
            ])
        
        return base_competitions
    
    def scan_global_football(
        self,
        date: Optional[datetime] = None,
        max_results_layer1: int = 200,
        max_results_layer2: int = 100,
        max_results_layer3: int = 50
    ) -> Dict[str, Any]:
        """
        Scan global football with LAYER 1-2-3 architecture
        
        Args:
            date: Date to scan (default: today)
            max_results_layer1: Max results for massive scan
            max_results_layer2: Max results for statistical profiling
            max_results_layer3: Max results for market inefficiency
            
        Returns:
            Dict with layer results and summary
        """
        
        scan_date = date or datetime.now()
        logger.info(f"Starting GLOBAL FOOTBALL INTELLIGENCE SCAN for {scan_date.date()}")
        
        # LAYER 1 = MASSIVE SCAN
        logger.info("=== LAYER 1: MASSIVE SCAN ===")
        layer1_results = self._layer1_massive_scan(scan_date, max_results_layer1)
        logger.info(f"LAYER 1: {len(layer1_results)} matches scanned")
        
        # LAYER 2 = STATISTICAL PROFILING
        logger.info("=== LAYER 2: STATISTICAL PROFILING ===")
        layer2_results = self._layer2_statistical_profiling(layer1_results, max_results_layer2)
        logger.info(f"LAYER 2: {len(layer2_results)} profiles generated")
        
        # LAYER 3 = MARKET INEFFICIENCY
        logger.info("=== LAYER 3: MARKET INEFFICIENCY ===")
        layer3_results = self._layer3_market_inefficiency(layer2_results, max_results_layer3)
        logger.info(f"LAYER 3: {len(layer3_results)} market edges detected")
        
        # Generate summary
        summary = self._generate_global_summary(layer1_results, layer2_results, layer3_results)
        
        return {
            "scan_info": {
                "date": scan_date.isoformat(),
                "total_competitions": len(self.global_competitions),
                "include_secondary": self.include_secondary_leagues,
                "include_obscure": self.include_obscure_competitions,
                "provider": self.provider.config.name
            },
            "layer1_massive_scan": [r.to_dict() for r in layer1_results],
            "layer2_statistical_profiling": [r.to_dict() for r in layer2_results],
            "layer3_market_inefficiency": [r.to_dict() for r in layer3_results],
            "summary": summary
        }
    
    def _layer1_massive_scan(self, date: datetime, max_results: int) -> List[GlobalScanResult]:
        """
        LAYER 1: MASSIVE SCAN
        
        Objectif: Scanner maximum de matchs sans filtrage agressif
        Inclure: ligues secondaires, compétitions obscures, women, youth, reserves
        """
        
        results = []
        
        # Fetch matches from ALL global competitions
        for competition_id in self.global_competitions:
            try:
                matches_response = self.provider.get_matches_by_date(date, competition_id)
                
                if not matches_response.success or not matches_response.data:
                    continue
                
                for match in matches_response.data:
                    # Minimal filtering for LAYER 1
                    scan_result = self._create_layer1_result(match)
                    if scan_result:
                        results.append(scan_result)
                
            except Exception as e:
                logger.debug(f"Error scanning competition {competition_id}: {e}")
                continue
        
        # Sort by basic data quality and limit
        results.sort(key=lambda x: x.data_quality_score, reverse=True)
        return results[:max_results]
    
    def _layer2_statistical_profiling(self, layer1_results: List[GlobalScanResult], max_results: int) -> List[GlobalScanResult]:
        """
        LAYER 2: STATISTICAL PROFILING
        
        Objectif: Générer TOUS les profils statistiques intéressants
        Pas de filtrage par odds, uniquement l'intelligence statistique
        """
        
        profiled_results = []
        
        for result in layer1_results:
            try:
                # Get team stats for profiling
                home_stats = self._get_team_stats(result.match_id, result.home_team)
                away_stats = self._get_team_stats(result.match_id, result.away_team)
                
                if not home_stats or not away_stats:
                    continue
                
                # Check minimum sample size for LAYER 2
                min_sample = min(home_stats.sample_size, away_stats.sample_size)
                if min_sample < self.min_sample_size_layer2:
                    continue
                
                # Generate match profile
                match_profile = self._generate_match_profile(home_stats, away_stats)
                result.match_profile = match_profile
                
                # Generate statistical signals
                signals = self._generate_statistical_signals(result, home_stats, away_stats)
                result.statistical_signals = signals
                
                # Pattern detection
                patterns = self._detect_patterns(home_stats, away_stats)
                result.pattern_detection = patterns
                
                # Calculate intelligence scores
                self._calculate_intelligence_scores(result, home_stats, away_stats)
                
                # Generate explanations
                self._generate_intelligent_explanations(result)
                
                profiled_results.append(result)
                
            except Exception as e:
                logger.debug(f"Error profiling match {result.match_id}: {e}")
                continue
        
        # Sort by intelligence score and limit
        profiled_results.sort(key=lambda x: x.intelligence_score, reverse=True)
        return profiled_results[:max_results]
    
    def _layer3_market_inefficiency(self, layer2_results: List[GlobalScanResult], max_results: int) -> List[GlobalScanResult]:
        """
        LAYER 3: MARKET INEFFICIENCY
        
        Objectif: Détecter les inefficiences bookmaker SI odds disponibles
        Séparer信号 statistiques vs edge bookmaker
        """
        
        market_results = []
        
        for result in layer2_results:
            try:
                # Get odds
                odds_response = self.provider.get_odds(result.match_id)
                
                if not odds_response.success or not odds_response.data:
                    # Pas d'odds = pas de LAYER 3, mais on garde le profil statistique
                    result.market_edge_score = 0.0
                    result.key_insights.append("Statistical pattern only (no odds available)")
                    market_results.append(result)
                    continue
                
                # Analyze market inefficiencies
                odds_list = odds_response.data
                result.bookmaker_odds = {odds.market_type: odds.under_odds or odds.over_odds or odds.yes_odds for odds in odds_list}
                
                # Detect inefficiencies for each signal
                inefficiencies = []
                for signal in result.statistical_signals:
                    inefficiency = self._detect_market_inefficiency(signal, odds_list)
                    if inefficiency:
                        inefficiencies.append(inefficiency)
                
                result.market_inefficiencies = inefficiencies
                
                # Calculate market edge score
                if inefficiencies:
                    result.market_edge_score = max(inef.get("edge_score", 0) for inef in inefficiencies)
                    result.key_insights.append(f"Market edge detected: {result.market_edge_score:.1f}")
                else:
                    result.market_edge_score = 0.0
                    result.key_insights.append("No significant market edge")
                
                market_results.append(result)
                
            except Exception as e:
                logger.debug(f"Error analyzing market for match {result.match_id}: {e}")
                continue
        
        # Sort by combined intelligence + market edge
        market_results.sort(key=lambda x: x.intelligence_score + x.market_edge_score, reverse=True)
        return market_results[:max_results]
    
    def _create_layer1_result(self, match: MatchDetails) -> Optional[GlobalScanResult]:
        """Create basic result for LAYER 1 massive scan"""
        
        try:
            # Quick data quality check
            home_stats = self._get_team_stats(match.id, match.home_team.name)
            away_stats = self._get_team_stats(match.id, match.away_team.name)
            
            if not home_stats or not away_stats:
                return None
            
            # Very relaxed sample size check for LAYER 1
            min_sample = min(home_stats.sample_size, away_stats.sample_size)
            if min_sample < self.min_sample_size_layer1:
                return None
            
            # Basic data quality
            data_quality = (home_stats.data_quality_score + away_stats.data_quality_score) / 2
            
            return GlobalScanResult(
                match_id=match.id,
                home_team=match.home_team.name,
                away_team=match.away_team.name,
                league=match.competition.name,
                country=match.competition.country or "",
                match_date=match.match_date.isoformat(),
                kickoff_time=match.match_date.isoformat(),
                data_source=self.provider.config.name,
                sample_size_home=home_stats.sample_size,
                sample_size_away=away_stats.sample_size,
                data_quality_score=data_quality,
                scan_timestamp=datetime.utcnow().isoformat(),
                provider=self.provider.config.name
            )
            
        except Exception as e:
            logger.debug(f"Error creating layer1 result for match {match.id}: {e}")
            return None
    
    def _get_team_stats(self, match_id: str, team_name: str) -> Optional['TeamStats']:
        """Get team statistics using provider adapter"""
        
        try:
            from app.services.stats.provider_adapter import StatsEngineProviderAdapter
            
            # This would need team_id, but for now use a simplified approach
            # In real implementation, you'd need to map team name to ID
            response = self.provider.search_team(team_name)
            
            if not response.success or not response.data:
                return None
            
            team_id = response.data[0].id  # Take first result
            
            # Get recent matches
            matches_response = self.provider.get_team_recent_matches(team_id, limit=15)
            
            if not matches_response.success or not matches_response.data:
                return None
            
            # Calculate stats
            adapter = StatsEngineProviderAdapter()
            stats = adapter.calculate_from_provider_matches(
                team_id=team_id,
                team_name=team_name,
                matches=matches_response.data
            )
            
            return stats
            
        except Exception as e:
            logger.debug(f"Error getting stats for {team_name}: {e}")
            return None
    
    def _generate_match_profile(self, home_stats: 'TeamStats', away_stats: 'TeamStats') -> MatchProfile:
        """Generate comprehensive match profile"""
        
        # Combine histories for profiling
        combined_ft_goals = []
        combined_ht_goals = []
        
        # This is simplified - real implementation would use actual match histories
        # For now, use averages to simulate goal history
        home_avg = home_stats.avg_total_goals
        away_avg = away_stats.avg_total_goals
        
        # Simulate goal histories based on averages
        import random
        for _ in range(max(home_stats.sample_size, away_stats.sample_size)):
            combined_ft_goals.append(int(random.normalvariate((home_avg + away_avg) / 2, 1.5)))
            combined_ft_goals = [max(0, g) for g in combined_ft_goals]  # Ensure non-negative
        
        # Generate profile
        return self.match_profiler.profile_match(
            ft_goals=combined_ft_goals,
            ht_goals=combined_ht_goals[:len(combined_ft_goals)]  # Simplified
        )
    
    def _generate_statistical_signals(self, result: GlobalScanResult, home_stats: 'TeamStats', away_stats: 'TeamStats') -> List[StatisticalSignal]:
        """Generate ALL statistical signals (diversified profiling)"""
        
        signals = []
        
        # Create match dict for signal engine
        match_dict = {
            "match_id": result.match_id,
            "home_team": result.home_team,
            "away_team": result.away_team,
            "competition": result.league,
            "country": result.country
        }
        
        # Generate goal histories (simplified)
        combined_goals = []
        for _ in range(max(home_stats.sample_size, away_stats.sample_size)):
            avg_goals = (home_stats.avg_total_goals + away_stats.avg_total_goals) / 2
            import random
            combined_goals.append(max(0, int(random.normalvariate(avg_goals, 1.5))))
        
        # Use signal engine to detect patterns
        try:
            detected_signals = self.signal_engine.detect_signals(
                match=match_dict,
                goal_history=combined_goals,
                ht_goal_history=None,  # Would need real HT data
                league_profile=None
            )
            signals.extend(detected_signals)
        except Exception as e:
            logger.debug(f"Error in signal detection: {e}")
        
        # Add additional diversified signals based on team stats
        additional_signals = self._generate_diversified_signals(result, home_stats, away_stats)
        signals.extend(additional_signals)
        
        return signals
    
    def _generate_diversified_signals(self, result: GlobalScanResult, home_stats: 'TeamStats', away_stats: 'TeamStats') -> List[StatisticalSignal]:
        """Generate diversified signals beyond basic under/over"""
        
        signals = []
        
        # HIGH_TEMPO signal
        avg_total_goals = (home_stats.avg_total_goals + away_stats.avg_total_goals) / 2
        if avg_total_goals >= 3.2:
            signals.append(StatisticalSignal(
                signal_type="HIGH_TEMPO",
                signal_strength="STRONG" if avg_total_goals >= 3.8 else "MODERATE",
                confidence=0.8,
                match_id=result.match_id,
                home_team=result.home_team,
                away_team=result.away_team,
                competition=result.league,
                country=result.country,
                suggested_markets=["OVER_2_5", "OVER_3_5", "BTTS"],
                compatible_lines=[2.5, 3.5],
                expected_goal_range=(avg_total_goals * 0.8, avg_total_goals * 1.3),
                historical_hit_rates_by_line={},
                max_observed_goals=int(avg_total_goals * 2),
                avg_goals=avg_total_goals,
                variance_score=0.5,
                stability_score=0.7,
                sample_size=max(home_stats.sample_size, away_stats.sample_size),
                data_quality=(home_stats.data_quality_score + away_stats.data_quality_score) / 2,
                waiting_for_odds=True,
                reasons=[f"High tempo match ({avg_total_goals:.1f} avg goals)", "Both teams attack-minded"]
            ))
        
        # BTTS_PROFILE signal
        avg_btts = (home_stats.btts_rate + away_stats.btts_rate) / 2
        if avg_btts >= 60:
            signals.append(StatisticalSignal(
                signal_type="BTTS_PROFILE",
                signal_strength="STRONG" if avg_btts >= 70 else "MODERATE",
                confidence=avg_btts / 100,
                match_id=result.match_id,
                home_team=result.home_team,
                away_team=result.away_team,
                competition=result.league,
                country=result.country,
                suggested_markets=["BTTS_YES"],
                compatible_lines=[],
                expected_goal_range=(2.0, 4.5),
                historical_hit_rates_by_line={},
                max_observed_goals=5,
                avg_goals=avg_total_goals,
                variance_score=0.6,
                stability_score=0.6,
                sample_size=max(home_stats.sample_size, away_stats.sample_size),
                data_quality=(home_stats.data_quality_score + away_stats.data_quality_score) / 2,
                waiting_for_odds=True,
                reasons=[f"BTTS tendency ({avg_btts:.0f}%)", "Both teams score regularly"]
            ))
        
        # VOLATILE_MATCH signal
        combined_variance = home_stats.variance_goals_scored + away_stats.variance_goals_conceded
        if combined_variance >= 4.0:
            signals.append(StatisticalSignal(
                signal_type="VOLATILE_MATCH",
                signal_strength="STRONG",
                confidence=0.7,
                match_id=result.match_id,
                home_team=result.home_team,
                away_team=result.away_team,
                competition=result.league,
                country=result.country,
                suggested_markets=["BOTH_TEAMS_TO_SCORE", "OVER_UNDER"],
                compatible_lines=[],
                expected_goal_range=(0, 6),
                historical_hit_rates_by_line={},
                max_observed_goals=7,
                avg_goals=avg_total_goals,
                variance_score=0.8,
                stability_score=0.3,
                sample_size=max(home_stats.sample_size, away_stats.sample_size),
                data_quality=(home_stats.data_quality_score + away_stats.data_quality_score) / 2,
                waiting_for_odds=True,
                reasons=[f"High variance ({combined_variance:.2f})", "Unpredictable patterns", "Potential for surprises"]
            ))
        
        return signals
    
    def _detect_patterns(self, home_stats: 'TeamStats', away_stats: 'TeamStats') -> Optional[PatternDetectionResult]:
        """Detect patterns using pattern engine"""
        
        try:
            # Detect patterns for both teams
            home_patterns = self.pattern_engine.analyze_team(
                team_id=home_stats.team_id,
                team_name=home_stats.team_name,
                overall_stats=home_stats
            )
            
            away_patterns = self.pattern_engine.analyze_team(
                team_id=away_stats.team_id,
                team_name=away_stats.team_name,
                overall_stats=away_stats
            )
            
            # Combine patterns (simplified)
            combined_patterns = home_patterns.patterns + away_patterns.patterns
            combined_patterns.sort(key=lambda p: p.score, reverse=True)
            
            return PatternDetectionResult(
                team_id=f"{home_stats.team_id}_vs_{away_stats.team_id}",
                team_name=f"{home_stats.team_name} vs {away_stats.team_name}",
                patterns=combined_patterns[:10],  # Top 10 patterns
                pattern_tags=home_patterns.pattern_tags + away_patterns.pattern_tags,
                pattern_score=(home_patterns.pattern_score + away_patterns.pattern_score) / 2,
                pattern_explanation=f"Combined patterns: {home_patterns.pattern_explanation} | {away_patterns.pattern_explanation}",
                dominant_patterns=home_patterns.dominant_patterns[:3] + away_patterns.dominant_patterns[:3],
                sample_size=max(home_patterns.sample_size, away_patterns.sample_size),
                confidence=(home_patterns.confidence + away_patterns.confidence) / 2
            )
            
        except Exception as e:
            logger.debug(f"Error in pattern detection: {e}")
            return None
    
    def _calculate_intelligence_scores(self, result: GlobalScanResult, home_stats: 'TeamStats', away_stats: 'TeamStats'):
        """Calculate intelligence scores for ranking"""
        
        # Base intelligence score from profile
        if result.match_profile:
            result.intelligence_score = result.match_profile.interest_score
            result.stability_score = result.match_profile.confidence_score
        else:
            result.intelligence_score = 50.0
            result.stability_score = 50.0
        
        # Pattern rarity bonus
        if result.pattern_detection:
            pattern_score = result.pattern_detection.pattern_score
            result.pattern_rarity_score = pattern_score
            result.intelligence_score += pattern_score * 0.3
        
        # Signal diversity bonus
        signal_types = set(s.signal_type for s in result.statistical_signals)
        diversity_bonus = len(signal_types) * 5
        result.intelligence_score += diversity_bonus
        
        # Cap at 100
        result.intelligence_score = min(100, result.intelligence_score)
    
    def _generate_intelligent_explanations(self, result: GlobalScanResult):
        """Generate human-readable explanations"""
        
        explanations = []
        
        # Profile explanation
        if result.match_profile:
            profile = result.match_profile
            explanations.append(f"Match Profile: {profile.scoring_profile} {profile.tempo_profile}")
            
            if profile.specific_profiles:
                explanations.append(f"Specific Patterns: {', '.join(profile.specific_profiles[:3])}")
        
        # Signal explanations
        strong_signals = [s for s in result.statistical_signals if s.signal_strength in ["STRONG", "EXTREME"]]
        if strong_signals:
            explanations.append(f"Strong Signals: {', '.join(s.signal_type for s in strong_signals[:3])}")
        
        # Pattern explanation
        if result.pattern_detection and result.pattern_detection.dominant_patterns:
            explanations.append(f"Dominant Patterns: {', '.join(result.pattern_detection.dominant_patterns[:3])}")
        
        result.pattern_explanation = " | ".join(explanations)
        
        # Why interesting
        reasons = []
        if result.intelligence_score >= 80:
            reasons.append("High intelligence score")
        if result.pattern_rarity_score >= 70:
            reasons.append("Rare statistical patterns")
        if result.stability_score >= 70:
            reasons.append("Very stable patterns")
        if len(result.statistical_signals) >= 5:
            reasons.append("Multiple statistical signals")
        
        result.why_interesting = "; ".join(reasons) if reasons else "Standard statistical profile"
    
    def _detect_market_inefficiency(self, signal: StatisticalSignal, odds_list: List[MatchOdds]) -> Optional[Dict[str, Any]]:
        """Detect market inefficiency for a signal"""
        
        # Find corresponding odds
        relevant_odds = None
        for odds in odds_list:
            if any(market in odds.market_type.lower() for market in 
                   ["under", "over", "btts"] and 
                   signal.signal_type.lower().replace("_", "") in odds.market_type.lower().replace("_", "")):
                relevant_odds = odds
                break
        
        if not relevant_odds:
            return None
        
        # Calculate expected value based on signal
        signal_confidence = signal.confidence
        bookmaker_odds = relevant_odds.under_odds or relevant_odds.over_odds or relevant_odds.yes_odds
        
        if not bookmaker_odds:
            return None
        
        # Simple edge calculation
        implied_probability = 1 / bookmaker_odds
        edge = (signal_confidence - implied_probability) * 100
        
        if edge > 10:  # Significant edge
            return {
                "signal_type": signal.signal_type,
                "market": relevant_odds.market_type,
                "bookmaker_odds": bookmaker_odds,
                "signal_confidence": signal_confidence,
                "implied_probability": implied_probability,
                "edge_percentage": edge,
                "edge_score": min(100, edge * 2)
            }
        
        return None
    
    def _generate_global_summary(self, layer1: List[GlobalScanResult], layer2: List[GlobalScanResult], layer3: List[GlobalScanResult]) -> Dict[str, Any]:
        """Generate comprehensive summary of global scan"""
        
        return {
            "layer1_summary": {
                "total_matches_scanned": len(layer1),
                "avg_data_quality": sum(r.data_quality_score for r in layer1) / len(layer1) if layer1 else 0,
                "competitions_covered": len(set(r.league for r in layer1)),
                "countries_covered": len(set(r.country for r in layer1))
            },
            "layer2_summary": {
                "profiles_generated": len(layer2),
                "avg_intelligence_score": sum(r.intelligence_score for r in layer2) / len(layer2) if layer2 else 0,
                "avg_pattern_rarity": sum(r.pattern_rarity_score for r in layer2) / len(layer2) if layer2 else 0,
                "total_signals_detected": sum(len(r.statistical_signals) for r in layer2),
                "unique_signal_types": len(set(signal.signal_type for r in layer2 for signal in r.statistical_signals))
            },
            "layer3_summary": {
                "market_analyses": len(layer3),
                "avg_market_edge": sum(r.market_edge_score for r in layer3) / len(layer3) if layer3 else 0,
                "inefficiencies_detected": sum(len(r.market_inefficiencies) for r in layer3),
                "matches_with_odds": sum(1 for r in layer3 if r.bookmaker_odds),
                "matches_without_odds": sum(1 for r in layer3 if not r.bookmaker_odds)
            },
            "top_intelligence_matches": [
                {
                    "match": f"{r.home_team} vs {r.away_team}",
                    "league": r.league,
                    "intelligence_score": r.intelligence_score,
                    "key_signals": [s.signal_type for s in r.statistical_signals[:3]],
                    "why_interesting": r.why_interesting
                }
                for r in sorted(layer3, key=lambda x: x.intelligence_score, reverse=True)[:5]
            ]
        }
