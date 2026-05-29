"""
Smart Scanner - Phase 2 & 3
Combines targeting V2 with intelligent analysis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.targeting.league_targeting_v2 import LeagueTargetingServiceV2
from app.services.signals.signal_engine import SignalEngine
from app.services.anomaly.line_breach_analyzer import LineBreachAnalyzer
from app.services.value.value_detector import ValueDetector
from app.services.value.fair_odds_calculator import FairOddsCalculator
from app.services.analysis.edge_detector import EdgeDetector
from app.services.analysis.match_profiler import MatchProfiler
from app.utils.match_status import MatchStatusHelper, MatchStatus

logger = logging.getLogger(__name__)


class SmartScanner:
    """
    Smart scanner with:
    - Targeting V2 (bettable leagues)
    - Lazy analysis (top matches only)
    - Signal detection
    """
    
    def __init__(
        self,
        provider,
        is_real_data: bool = False,
        include_extreme_obscure: bool = False,
        max_analysis: int = 10
    ):
        """
        Initialize smart scanner
        
        Args:
            provider: Data provider
            is_real_data: Whether using real data
            include_extreme_obscure: Include extreme obscure leagues
            max_analysis: Maximum matches to analyze deeply (lazy analysis)
        """
        self.provider = provider
        self.is_real_data = is_real_data
        self.max_analysis = max_analysis
        
        # Services
        self.targeting = LeagueTargetingServiceV2(include_extreme_obscure=include_extreme_obscure)
        self.signal_engine = SignalEngine()
        self.edge_detector = EdgeDetector()
        self.match_profiler = MatchProfiler()  # NEW: Profile ALL matches
        self.line_analyzer = LineBreachAnalyzer()
        self.value_detector = ValueDetector()
        self.fair_odds_calc = FairOddsCalculator()
        
        logger.info(f"SmartScanner initialized (max_analysis={max_analysis}, extreme_obscure={include_extreme_obscure})")
    
    def scan_today(self) -> Dict[str, Any]:
        """
        Scan today's matches with smart targeting and lazy analysis
        
        Returns:
            Scan result with analyzed matches
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Fetch today's matches
        logger.info("Fetching today's matches...")
        response = self.provider.get_today_matches()
        
        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "total_matches": 0,
                "target_count": 0,
                "analyzed_count": 0
            }
        
        all_matches = response.data
        logger.info(f"Fetched {len(all_matches)} matches")
        
        # Step 2: Target matches with V2
        logger.info("Targeting matches with V2...")
        target_matches = []
        
        for match in all_matches:
            # Analyze league
            profile = self.targeting.analyze_league(
                competition=match.competition.name if hasattr(match, 'competition') else "",
                country=match.competition.country if hasattr(match, 'competition') else ""
            )
            
            # Check if should include
            if self.targeting.should_include(profile):
                target_matches.append({
                    "match": match,
                    "profile": profile
                })
        
        logger.info(f"Targeted {len(target_matches)} matches")
        
        # Step 3: Intelligent prioritization for analysis
        prioritized_matches = self._prioritize_for_analysis(target_matches)
        
        # Step 4: Lazy analysis (top N only)
        logger.info(f"Analyzing top {self.max_analysis} matches...")
        analyzed_matches = []
        
        for item in prioritized_matches[:self.max_analysis]:
            match = item["match"]
            profile = item["profile"]
            
            # Analyze match
            analysis = self._analyze_match(match, profile)
            
            if analysis:
                analyzed_matches.append({
                    "match_data": self._extract_match_data(match),
                    "profile": profile.to_dict(),
                    "analysis": analysis
                })
        
        logger.info(f"Analyzed {len(analyzed_matches)} matches")
        
        # Step 5: Prepare remaining matches (no deep analysis)
        remaining_matches = []
        for item in target_matches[self.max_analysis:]:
            match = item["match"]
            profile = item["profile"]
            
            remaining_matches.append({
                "match_data": self._extract_match_data(match),
                "profile": profile.to_dict(),
                "analysis": None  # Not analyzed yet
            })
        
        # Calculate duration
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "success": True,
            "total_matches": len(all_matches),
            "target_count": len(target_matches),
            "analyzed_count": len(analyzed_matches),
            "analyzed_matches": analyzed_matches,
            "remaining_matches": remaining_matches,
            "scan_duration_seconds": duration,
            "is_real_data": self.is_real_data
        }
    
    def analyze_single_match(
        self,
        match_id: str,
        competition: str,
        country: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single match on-demand
        
        Args:
            match_id: Match ID
            competition: Competition name
            country: Country name
            
        Returns:
            Analysis result or None
        """
        # Get match details
        response = self.provider.get_match_details(match_id)
        
        if not response.success:
            return None
        
        match = response.data
        
        # Analyze league
        profile = self.targeting.analyze_league(competition, country)
        
        # Analyze match
        analysis = self._analyze_match(match, profile)
        
        return {
            "match_data": self._extract_match_data(match),
            "profile": profile.to_dict(),
            "analysis": analysis
        }
    
    def _prioritize_for_analysis(
        self,
        target_matches: List[Dict]
    ) -> List[Dict]:
        """
        Intelligent prioritization for deep analysis
        
        Priority order:
        1. Top BETTABLE_MINOR leagues (5 matches)
        2. Top women leagues (2 matches)
        3. Top youth leagues (2 matches)
        4. Remaining by priority score (1 match)
        
        Args:
            target_matches: All targeted matches
            
        Returns:
            Prioritized list for analysis
        """
        priority_list = []
        seen_ids = set()
        
        # 1. Top BETTABLE_MINOR
        bettable = [
            m for m in target_matches
            if m["profile"].target_level == "BETTABLE_MINOR"
        ]
        bettable.sort(key=lambda x: x["profile"].priority_score, reverse=True)
        
        for match in bettable[:5]:
            match_id = self._extract_match_data(match["match"]).get("match_id")
            if match_id not in seen_ids:
                priority_list.append(match)
                seen_ids.add(match_id)
        
        # 2. Top women
        women = [
            m for m in target_matches
            if m["profile"].is_women
        ]
        women.sort(key=lambda x: x["profile"].priority_score, reverse=True)
        
        for match in women[:2]:
            match_id = self._extract_match_data(match["match"]).get("match_id")
            if match_id not in seen_ids:
                priority_list.append(match)
                seen_ids.add(match_id)
        
        # 3. Top youth
        youth = [
            m for m in target_matches
            if m["profile"].is_youth
        ]
        youth.sort(key=lambda x: x["profile"].priority_score, reverse=True)
        
        for match in youth[:2]:
            match_id = self._extract_match_data(match["match"]).get("match_id")
            if match_id not in seen_ids:
                priority_list.append(match)
                seen_ids.add(match_id)
        
        # 4. Fill remaining with highest priority
        remaining = [
            m for m in target_matches
            if self._extract_match_data(m["match"]).get("match_id") not in seen_ids
        ]
        remaining.sort(key=lambda x: x["profile"].priority_score, reverse=True)
        
        for match in remaining:
            if len(priority_list) >= self.max_analysis:
                break
            priority_list.append(match)
        
        logger.info(f"Prioritized: {len([m for m in priority_list if m['profile'].target_level == 'BETTABLE_MINOR'])} bettable, "
                   f"{len([m for m in priority_list if m['profile'].is_women])} women, "
                   f"{len([m for m in priority_list if m['profile'].is_youth])} youth")
        
        return priority_list
    
    def _analyze_match(
        self,
        match: Any,
        profile: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a match with REAL historical data
        
        Args:
            match: Match object
            profile: League profile
            
        Returns:
            Analysis dict or None
        """
        try:
            # Import MatchDataLoader
            from app.services.data.match_data_loader import MatchDataLoader
            
            # Get team IDs
            home_team_id = getattr(match.home_team, 'id', None) if hasattr(match, 'home_team') else None
            away_team_id = getattr(match.away_team, 'id', None) if hasattr(match, 'away_team') else None
            
            if not home_team_id or not away_team_id:
                logger.warning(f"Missing team IDs for match")
                return {
                    "status": "DATA_INSUFFICIENT",
                    "reason": "MISSING_TEAM_IDS",
                    "signals": [],
                    "data_origin": "NONE"
                }
            
            # Load REAL historical data
            loader = MatchDataLoader(self.provider)
            
            bundle = loader.load_match_data(
                fixture_id=getattr(match, 'match_id', ''),
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_team_name=match.home_team.name if hasattr(match, 'home_team') else '',
                away_team_name=match.away_team.name if hasattr(match, 'away_team') else '',
                match_date=getattr(match, 'match_date', None),
                history_limit=10
            )
            
            # Check data quality
            if bundle.history_status == "MISSING":
                logger.warning(f"No historical data available")
                return {
                    "status": "DATA_INSUFFICIENT",
                    "reason": "NO_HISTORY_AVAILABLE",
                    "signals": [],
                    "data_origin": "REAL",
                    "home_history_count": 0,
                    "away_history_count": 0
                }
            
            if bundle.history_status == "INSUFFICIENT":
                logger.warning(f"Insufficient historical data: {bundle.home_history_count + bundle.away_history_count} matches")
                return {
                    "status": "DATA_INSUFFICIENT",
                    "reason": "INSUFFICIENT_SAMPLE_SIZE",
                    "sample_size": bundle.home_history_count + bundle.away_history_count,
                    "signals": [],
                    "data_origin": "REAL",
                    "home_history_count": bundle.home_history_count,
                    "away_history_count": bundle.away_history_count
                }
            
            # Extract REAL goal histories
            goal_history = bundle.get_ft_goal_history()
            ht_goal_history = bundle.get_ht_goal_history()
            
            if len(goal_history) < 5:
                logger.warning(f"Insufficient FT data: {len(goal_history)} matches")
                return {
                    "status": "DATA_INSUFFICIENT",
                    "reason": "INSUFFICIENT_FT_DATA",
                    "sample_size": len(goal_history),
                    "signals": [],
                    "data_origin": "REAL",
                    "ft_sample_size": len(goal_history),
                    "ht_sample_size": len(ht_goal_history)
                }
            
            logger.info(f"Loaded REAL data: FT={len(goal_history)}, HT={len(ht_goal_history)}")
            logger.info(f"FT goals sample: {goal_history[:5]}")
            if ht_goal_history:
                logger.info(f"HT goals sample: {ht_goal_history[:5]}")
            
            # Generate signals
            match_dict = {
                "match_id": getattr(match, 'match_id', ''),
                "home_team": match.home_team.name if hasattr(match, 'home_team') else '',
                "away_team": match.away_team.name if hasattr(match, 'away_team') else '',
                "competition": profile.competition,
                "country": profile.country
            }
            
            signals = self.signal_engine.detect_signals(
                match=match_dict,
                goal_history=goal_history,
                ht_goal_history=ht_goal_history
            )
            
            # Line breach analysis
            line_analyses = self.line_analyzer.analyze_all_lines(goal_history)
            
            # Build analysis result with value assessment AND fair odds
            signals_with_value = []
            for signal in signals[:2]:  # Top 2 signals
                # Calculate fair odds
                fair_odds_assessment = self.fair_odds_calc.calculate_fair_odds(
                    historical_probability=signal.confidence,
                    bookmaker_odd=None  # TODO: Add odds when available
                )
                
                # Assess value (no odds for now, will be added later)
                value_assessment = self.value_detector.assess_value(
                    statistical_probability=signal.confidence,
                    variance_score=signal.variance_score,
                    sample_size=signal.sample_size,
                    data_quality=signal.data_quality,
                    bookmaker_odd=None,  # TODO: Add odds when available
                    market_type=signal.signal_type
                )
                
                signals_with_value.append({
                    "type": signal.signal_type,
                    "strength": signal.signal_strength,
                    "confidence": signal.confidence,
                    "suggested_markets": signal.suggested_markets[:3],
                    "compatible_lines": signal.compatible_lines[:3],
                    "max_observed_goals": signal.max_observed_goals,
                    "avg_goals": signal.avg_goals,
                    "variance_score": signal.variance_score,
                    "stability_score": signal.stability_score,
                    "sample_size": signal.sample_size,
                    "data_quality": signal.data_quality,
                    "reasons": signal.reasons[:3],
                    "fair_odds": fair_odds_assessment.to_dict(),
                    "value_assessment": value_assessment.to_dict()
                })
            
            # Build HT Analysis Table
            ht_analysis_table = []
            if ht_goal_history:
                for line in [0.5, 1.5, 2.5, 3.5]:
                    under_count = sum(1 for g in ht_goal_history if g < line)
                    hit_rate = (under_count / len(ht_goal_history)) if ht_goal_history else 0
                    fair_odd = self.fair_odds_calc.calculate_fair_odds(hit_rate) if hit_rate > 0 else None
                    
                    ht_analysis_table.append({
                        "line": f"U{line}",
                        "hit_rate": hit_rate * 100,
                        "under_count": under_count,
                        "over_count": len(ht_goal_history) - under_count,
                        "sample_size": len(ht_goal_history),
                        "fair_odd": fair_odd.fair_odd if fair_odd else None,
                        "max_ht_goals": max(ht_goal_history),
                        "avg_ht_goals": sum(ht_goal_history) / len(ht_goal_history)
                    })
            
            # Build FT Analysis Table
            ft_analysis_table = []
            for line in [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 10.5, 12.5]:
                under_count = sum(1 for g in goal_history if g < line)
                hit_rate = (under_count / len(goal_history)) if goal_history else 0
                fair_odd = self.fair_odds_calc.calculate_fair_odds(hit_rate) if hit_rate > 0 else None
                
                ft_analysis_table.append({
                    "line": f"U{line}",
                    "hit_rate": hit_rate * 100,
                    "under_count": under_count,
                    "over_count": len(goal_history) - under_count,
                    "sample_size": len(goal_history),
                    "fair_odd": fair_odd.fair_odd if fair_odd else None,
                    "max_goals": max(goal_history),
                    "avg_goals": sum(goal_history) / len(goal_history)
                })
            
            # Build match history display with home/away goals for BTTS
            match_history = []
            match_history_btts = []
            
            # Get all historical matches for BTTS
            all_historical_matches = bundle.home_history + bundle.away_history
            
            for i, goals in enumerate(goal_history[:10]):  # Last 10 matches for display
                ht_goals = ht_goal_history[i] if i < len(ht_goal_history) else None
                match_history.append({
                    "match_number": i + 1,
                    "total_goals": goals,
                    "ht_goals": ht_goals
                })
            
            # Prepare BTTS history (need home_goals and away_goals)
            for match in all_historical_matches:
                home_goals = getattr(match, 'home_score', 0)
                away_goals = getattr(match, 'away_score', 0)
                match_history_btts.append({
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "total_goals": home_goals + away_goals
                })
            
            # EDGE DETECTION: Detect bookmaker mispricing
            edge_results = self.edge_detector.detect_all_edges(
                ht_goals=ht_goal_history,
                ft_goals=goal_history,
                ht_analysis={"table": ht_analysis_table},
                ft_analysis={"table": ft_analysis_table},
                bookmaker_odds=None,  # TODO: Add bookmaker odds when available
                match_history=match_history_btts  # For BTTS detection
            )
            
            best_edges = edge_results.get("best_edges", [])
            
            # MATCH PROFILING: Generate comprehensive profile for discovery
            match_profile = self.match_profiler.profile_match(
                ft_goals=goal_history,
                ht_goals=ht_goal_history,
                match_history=match_history_btts
            )
            
            # PHASE 6: Logging
            logger.info(f"[ANALYSIS] History counts: home={bundle.home_history_count}, away={bundle.away_history_count}")
            logger.info(f"[ANALYSIS] HT rows calculated: {len(ht_analysis_table)}")
            logger.info(f"[ANALYSIS] FT rows calculated: {len(ft_analysis_table)}")
            logger.info(f"[ANALYSIS] Signals generated: {len(signals_with_value)}")
            logger.info(f"[EDGE] Best edges detected: {len(best_edges)}")
            logger.info(f"[PROFILE] Interest score: {match_profile.interest_score:.0f}, Confidence: {match_profile.confidence_score:.0f}")
            
            analysis = {
                "status": "ANALYZABLE_NO_ODDS",  # PHASE 3: Status for matches without odds
                "signals": signals_with_value,
                "best_edges": best_edges,  # EDGE DETECTION: Top 1-3 edges with real value
                "edge_detection": edge_results,  # Full edge detection results
                "match_profile": match_profile.to_dict(),  # DISCOVERY: Complete match profile
                "ht_analysis": {
                    "table": ht_analysis_table,
                    "max_ht_goals": max(ht_goal_history) if ht_goal_history else None,
                    "avg_ht_goals": sum(ht_goal_history) / len(ht_goal_history) if ht_goal_history else None,
                    "sample_size": len(ht_goal_history) if ht_goal_history else 0
                },
                "ft_analysis": {
                    "table": ft_analysis_table,
                    "max_goals": max(goal_history),
                    "avg_goals": sum(goal_history) / len(goal_history),
                    "sample_size": len(goal_history)
                },
                "match_history": match_history,
                "line_breach": {
                    "lines_analyzed": len(line_analyses),
                    "top_lines": [
                        {
                            "line": line,
                            "hit_rate": analysis.hit_rate,
                            "over_count": analysis.matches_over,
                            "under_count": analysis.matches_under
                        }
                        for line, analysis in sorted(
                            line_analyses.items(),
                            key=lambda x: x[1].hit_rate,
                            reverse=True
                        )[:5]  # Top 5 lines
                    ]
                },
                "historical_summary": {
                    "max_goals": max(goal_history),
                    "avg_goals": sum(goal_history) / len(goal_history),
                    "sample_size": len(goal_history),
                    "ht_max_goals": max(ht_goal_history) if ht_goal_history else None,
                    "ht_avg_goals": sum(ht_goal_history) / len(ht_goal_history) if ht_goal_history else None
                },
                # Debug metadata
                "debug": {
                    "data_origin": "REAL",
                    "home_history_count": bundle.home_history_count,
                    "away_history_count": bundle.away_history_count,
                    "h2h_count": bundle.h2h_count,
                    "h2h_missing": bundle.h2h_count == 0,  # PHASE 4: Track H2H status
                    "ht_data_available": bundle.ht_data_available,
                    "ft_data_available": bundle.ft_data_available,
                    "history_status": bundle.history_status,
                    "errors": bundle.errors,
                    "warnings": bundle.warnings,
                    "mock_usage": False
                }
            }
            
            logger.info(f"[ANALYSIS] Status: {analysis['status']}")
            logger.info(f"[ANALYSIS] Data origin: {analysis['debug']['data_origin']}")
            logger.info(f"[ANALYSIS] Mock usage: {analysis['debug']['mock_usage']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing match: {e}")
            return None
    
    def _extract_match_data(self, match: Any) -> Dict[str, Any]:
        """Extract match data to dict with status info"""
        match_data = {
            "match_id": getattr(match, 'match_id', '') or getattr(match, 'id', ''),
            "home_team": match.home_team.name if hasattr(match, 'home_team') else '',
            "away_team": match.away_team.name if hasattr(match, 'away_team') else '',
            "home_team_id": match.home_team.id if hasattr(match, 'home_team') and hasattr(match.home_team, 'id') else '',
            "away_team_id": match.away_team.id if hasattr(match, 'away_team') and hasattr(match.away_team, 'id') else '',
            "competition": match.competition.name if hasattr(match, 'competition') else '',
            "country": match.competition.country if hasattr(match, 'competition') else '',
            "kickoff_time": str(match.match_date) if hasattr(match, 'match_date') else '',
            "status": getattr(match, 'status', 'NS'),
            "elapsed_minutes": getattr(match, 'elapsed', None)
        }
        
        # Add status classification
        status_info = MatchStatusHelper.get_display_info(match_data)
        match_data.update(status_info)
        
        return match_data
