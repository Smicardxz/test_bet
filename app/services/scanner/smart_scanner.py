"""
Smart Scanner - Phase 2 & 3
Combines targeting V2 with intelligent analysis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.targeting.league_targeting_service import LeagueTargetingService
from app.services.signals.signal_engine import SignalEngine
from app.services.anomaly.line_breach_analyzer import LineBreachAnalyzer
from app.services.value.value_detector import ValueDetector
from app.services.value.fair_odds_calculator import FairOddsCalculator
from app.services.analysis.edge_detector import EdgeDetector
from app.services.analysis.match_profiler import MatchProfiler
from app.services.analysis.league_profile_engine import LeagueProfileEngine
from app.services.analysis.volatility_engine import VolatilityEngine
from app.services.analysis.false_signal_detector import FalseSignalDetector
from app.services.analysis.home_away_engine import HomeAwayEngine
from app.services.analysis.league_specialization_engine import (
    LeagueSpecializationEngine, SmartRecommendation, get_engine as _get_lse_engine,
)
from app.services.universe.bettable_classifier import classify as _classify_bettable
from app.services.analysis.error_analysis_engine import (
    ErrorAnalysisEngine, PickExplanation, get_eae as _get_eae,
)
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
        odds_provider=None
    ):
        """
        Initialize smart scanner - Phase 1: Massive scan without limits

        Args:
            provider: Data provider (API-Football)
            is_real_data: Whether using real data
            include_extreme_obscure: Include extreme obscure leagues
            odds_provider: Phase 6 TheOddsAPIProvider (optional, non-blocking if None)
        """
        self.provider = provider
        self.is_real_data = is_real_data
        self.odds_provider = odds_provider  # Phase 6: real bookmaker odds (non-blocking)

        # Services - GLOBAL SCAN: Use GLOBAL_SCAN mode for all leagues
        from app.services.targeting.league_targeting_service import TargetMode
        self.targeting = LeagueTargetingService(target_mode=TargetMode.GLOBAL_SCAN)
        self.signal_engine = SignalEngine()
        self.edge_detector = EdgeDetector()
        self.match_profiler = MatchProfiler()  # Profile ALL matches
        self.line_analyzer = LineBreachAnalyzer()
        self.value_detector = ValueDetector()
        self.fair_odds_calc = FairOddsCalculator()
        # Intelligence engines (STEP 1-5)
        self.league_profile_engine = LeagueProfileEngine()
        self.volatility_engine = VolatilityEngine()
        self.false_signal_detector = FalseSignalDetector()
        self.home_away_engine = HomeAwayEngine()
        # STEP 4: League Specialization Engine (optional — ready only when CSVs loaded)
        self.league_spec_engine: LeagueSpecializationEngine = _get_lse_engine()
        # STEP 4b: Error Analysis Engine (optional — non-blocking)
        self.error_analysis_engine: ErrorAnalysisEngine = _get_eae()

        logger.info(f"SmartScanner initialized (mode=GLOBAL_SCAN, no limits)")

    # ── Phase 7 — Single fixture_id resolver ─────────────────────────────────
    @staticmethod
    def get_fixture_id(match) -> str:
        """
        Canonical fixture_id extractor.
        Checks fixture_id → match_id → id in that priority order.
        Always returns a str (never None or int).
        """
        return str(
            getattr(match, "fixture_id", None)
            or getattr(match, "match_id", None)
            or getattr(match, "id", None)
            or ""
        )

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
        
        # Step 2: PHASE 1 - Filtrer par status (UPCOMING et LIVE seulement)
        logger.info("Filtering matches by status...")
        upcoming_matches = []
        live_matches = []
        finished_matches = []
        cancelled_matches = []
        other_matches = []
        
        for match in all_matches:
            status = getattr(match, 'status', 'UNKNOWN').upper()
            
            if status in ['UPCOMING', 'NS', 'SCHEDULED', 'TBD']:
                upcoming_matches.append(match)
            elif status in ['LIVE', 'IN_PLAY', 'PAUSED', '1H', '2H', 'HT', 'ET', 'P']:
                live_matches.append(match)
            elif status in ['FINISHED', 'FT', 'AET', 'PEN', 'AWARDED', 'WALKOVER']:
                finished_matches.append(match)
            elif status in ['CANCELLED', 'POSTPONED', 'ABANDONED', 'SUSPENDED']:
                cancelled_matches.append(match)
            else:
                other_matches.append(match)
        
        logger.info(f"Status breakdown - Upcoming: {len(upcoming_matches)}, Live: {len(live_matches)}, Finished: {len(finished_matches)}, Cancelled: {len(cancelled_matches)}, Other: {len(other_matches)}")
        
        # Step 3: PHASE 1 - Target matches avec priorité UPCOMING FIRST
        logger.info("Targeting matches with V2 (PRE-MATCH FIRST)...")
        target_matches = []
        
        # PHASE 1: Priorité absolue aux UPCOMING (PRE-MATCH FIRST)
        logger.info(f"PHASE 1: Processing {len(upcoming_matches)} UPCOMING matches (PRE-MATCH PRIORITY)")
        for match in upcoming_matches:
            # Analyze league (V2 API)
            profile = self.targeting.analyze_competition(
                competition_name=match.competition.name if hasattr(match, 'competition') else "",
                country=match.competition.country if hasattr(match, 'competition') else ""
            )
            
            # Check if should include
            if self.targeting.should_include(profile):
                target_matches.append({
                    "match": match,
                    "profile": profile,
                    "priority": "HIGH_PREMATCH"  # PHASE 1: Priorité haute pour UPCOMING
                })
        
        # PHASE 2: LIVE matches (priorité secondaire)
        logger.info(f"PHASE 2: Processing {len(live_matches)} LIVE matches (SECONDARY PRIORITY)")
        for match in live_matches:
            # Analyze league (V2 API)
            profile = self.targeting.analyze_competition(
                competition_name=match.competition.name if hasattr(match, 'competition') else "",
                country=match.competition.country if hasattr(match, 'competition') else ""
            )
            
            # Check if should include
            if self.targeting.should_include(profile):
                target_matches.append({
                    "match": match,
                    "profile": profile,
                    "priority": "SECONDARY_LIVE"  # PHASE 2: Priorité secondaire pour LIVE
                })
        
        # Cap: sort by league quality score then limit (GLOBAL_SCAN covers 800+ matches)
        MAX_UPCOMING = 25
        MAX_LIVE     = 10

        def _league_score(item):
            p = item.get("profile")
            if p is None:
                return 0.0
            try:
                return float(getattr(p, "tier_score", None) or getattr(p, "score", None) or 0.0)
            except Exception:
                return 0.0

        upcoming_targeted = [m for m in target_matches if m.get("priority") == "HIGH_PREMATCH"]
        live_targeted     = [m for m in target_matches if m.get("priority") == "SECONDARY_LIVE"]

        upcoming_targeted.sort(key=_league_score, reverse=True)
        live_targeted.sort(key=_league_score, reverse=True)

        target_matches = upcoming_targeted[:MAX_UPCOMING] + live_targeted[:MAX_LIVE]
        matches_to_analyze = target_matches
        logger.info(
            f"Targeted {len(target_matches)} matches "
            f"({len(upcoming_targeted[:MAX_UPCOMING])} upcoming + {len(live_targeted[:MAX_LIVE])} live, "
            f"capped from {len(upcoming_targeted)} + {len(live_targeted)})"
        )

        # Step 3b: Phase 6 — Targeted odds prefetch (BEFORE analysis loop)
        # Only fetches sport_keys for the actual leagues we target — no wasted API calls
        if self.odds_provider and getattr(self.odds_provider, 'api_key', None):
            try:
                match_list_for_odds = [
                    {
                        "competition": item["match"].competition.name if hasattr(item["match"], "competition") else "",
                        "country":     item["match"].competition.country if hasattr(item["match"], "competition") else "",
                    }
                    for item in target_matches
                ]
                if hasattr(self.odds_provider, 'prefetch_for_matches'):
                    self.odds_provider.prefetch_for_matches(match_list_for_odds)
                    _cached_n = getattr(self.odds_provider, 'events_fetched', 0)
                    logger.info(f"[ODDS] Targeted prefetch complete — {_cached_n} events cached")
                    import os as _os2
                    if _os2.getenv('DEBUG_ODDS_WIRING', '').lower() == 'true':
                        _apifb_cache_after = getattr(getattr(self.odds_provider, '_apifb', None), '_fixture_cache', {})
                        logger.info(
                            f"[WIRE_PROVIDER] provider_id={id(self.odds_provider)}"
                            f" | cache_size={len(_apifb_cache_after)}"
                            f" | cache_keys_sample={list(_apifb_cache_after.keys())[:5]}"
                        )
            except Exception as e:
                logger.debug(f"[ODDS] Non-blocking prefetch error: {e}")

        # Step 4: Phase 1 - No limit, analyze ALL targeted upcoming matches with full history
        logger.info(f"Phase 1: Analyzing ALL {len(target_matches)} targeted matches (no limit)...")
        analyzed_matches = []
        
        # PIPELINE COUNTERS - Add detailed tracking
        pipeline_counters = {
            "fixtures_fetched": len(all_matches),
            "fixtures_after_targeting": len(target_matches),
            "fixtures_sent_to_scanner": len(target_matches),
            "fixtures_analyzed_by_scanner": 0,
            "fixtures_with_signals": 0,
            "fixtures_with_odds": 0,
            "fixtures_ev_candidates": 0,
            "predictions_to_save": 0,
            "predictions_saved": 0,
            "research_only_saved": 0,
            "live_safe_saved": 0,
            "duplicates_skipped": 0
        }
        logger.info(f"[PIPELINE] Starting with counters: {pipeline_counters}")

        # Phase 2 — ODDS_FIRST_MODE diagnostics
        _diag_apifb_cache = getattr(getattr(self.odds_provider, '_apifb', None), '_fixture_cache', {}) if self.odds_provider else {}
        _diag_analyzed_with_odds    = 0
        _diag_analyzed_without_odds = 0

        for i, item in enumerate(target_matches):
            match = item["match"]
            profile = item["profile"]

            try:
                # Analyze match with full historical data
                analysis = self._analyze_match(match, profile)
                
                # Update pipeline counters
                pipeline_counters["fixtures_analyzed_by_scanner"] += 1

                if analysis:
                    _match_data = self._extract_match_data(match)
                    analyzed_matches.append({
                        "match_data": _match_data,
                        "profile": profile.to_dict(),
                        "analysis": analysis
                    })
                    # Phase 2 diagnostics
                    if _diag_apifb_cache.get(str(_match_data.get("match_id", ""))):
                        _diag_analyzed_with_odds += 1
                        pipeline_counters["fixtures_with_odds"] += 1
                    else:
                        _diag_analyzed_without_odds += 1
                    
                    # Check for signals and EV candidates
                    if analysis.get("signals"):
                        pipeline_counters["fixtures_with_signals"] += 1
                    if analysis.get("ev_candidates"):
                        pipeline_counters["fixtures_ev_candidates"] += 1

                logger.info(f"Analyzed match {i+1}/{len(target_matches)}: {match.home_team.name} vs {match.away_team.name}")

            except Exception as e:
                logger.warning(f"Failed to analyze match {i+1}/{len(target_matches)}: {e}")
                # Continuer avec les autres matches même si celui-ci échoue
                continue

        logger.info(f"Analyzed {len(analyzed_matches)} matches (with_odds={_diag_analyzed_with_odds}, without_odds={_diag_analyzed_without_odds})")

        # Step 4: No remaining matches - all targeted matches are analyzed
        remaining_matches = []
        
        # Step 6: Ajouter les matches FINISHED/CANCELLED (non analysés mais visibles)
        skipped_matches = []
        
        # Ajouter les matches finis
        for match in finished_matches:
            skipped_matches.append({
                "match_data": self._extract_match_data(match),
                "profile": {"target_level": "SKIPPED", "target_score": 0, "bookmaker_coverage": {"coverage_score": 0, "coverage_level": "NONE"}},
                "analysis": None  # Never analyzed
            })
        
        # Ajouter les matches annulés
        for match in cancelled_matches:
            skipped_matches.append({
                "match_data": self._extract_match_data(match),
                "profile": {"target_level": "SKIPPED", "target_score": 0, "bookmaker_coverage": {"coverage_score": 0, "coverage_level": "NONE"}},
                "analysis": None  # Never analyzed
            })
        
        # Combiner remaining + skipped
        all_remaining = remaining_matches + skipped_matches
        
        # Calculate duration
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        _analyzed_fids     = {str(m["match_data"].get("match_id", "")) for m in analyzed_matches}
        _odds_not_analyzed = len(set(_diag_apifb_cache.keys()) - _analyzed_fids)

        # Log final pipeline counters
        logger.info(f"[PIPELINE] Final counters: {pipeline_counters}")
        
        return {
            "success": True,
            "total_matches": len(all_matches),
            "target_count": len(target_matches),
            "analyzed_count": len(analyzed_matches),
            "analyzed_matches": analyzed_matches,
            "remaining_matches": all_remaining,
            "scan_duration_seconds": duration,
            "is_real_data": self.is_real_data,
            # Phase 2 — ODDS_FIRST_MODE diagnostics
            "odds_first_mode_diagnostics": {
                "analyzed_with_odds":      _diag_analyzed_with_odds,
                "analyzed_without_odds":   _diag_analyzed_without_odds,
                "odds_not_analyzed":       _odds_not_analyzed,
                "apifb_fixtures_in_cache": len(_diag_apifb_cache),
            },
            # PIPELINE COUNTERS - Detailed tracking
            "pipeline_counters": pipeline_counters,
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
        PHASE 1: PRE-MATCH FIRST Prioritization
        
        Priority order:
        1. ALL UPCOMING matches (PRE-MATCH FIRST)
        2. Top scoring UPCOMING (by target_score)
        3. Remaining UPCOMING (by target_score)
        4. LIVE matches (secondary priority only if slots available)
        
        Args:
            target_matches: All targeted matches
            
        Returns:
            Prioritized list for analysis
        """
        priority_list = []
        seen_ids = set()
        
        # PHASE 1: Séparer UPCOMING vs LIVE
        upcoming_matches = [m for m in target_matches if m.get("priority") == "HIGH_PREMATCH"]
        live_matches = [m for m in target_matches if m.get("priority") == "SECONDARY_LIVE"]
        
        logger.info(f"PHASE 1: {len(upcoming_matches)} UPCOMING (HIGH PRIORITY), {len(live_matches)} LIVE (SECONDARY)")
        
        # PHASE 2: Prioriser tous les UPCOMING par target_score
        upcoming_sorted = sorted(upcoming_matches, key=lambda x: x["profile"].target_score, reverse=True)
        
        # Ajouter tous les UPCOMING en priorité
        for match in upcoming_sorted:
            match_id = self._extract_match_data(match["match"]).get("match_id")
            if match_id not in seen_ids:
                priority_list.append(match)
                seen_ids.add(match_id)
        
        logger.info(f"PHASE 2: Added {len(upcoming_sorted)} UPCOMING matches to priority list")
        
        # PHASE 3: Ajouter les LIVE (priorité secondaire, sans limite)
        live_sorted = sorted(live_matches, key=lambda x: x["profile"].target_score, reverse=True)
        for match in live_sorted:
            match_id = self._extract_match_data(match["match"]).get("match_id")
            if match_id not in seen_ids:
                priority_list.append(match)
                seen_ids.add(match_id)
        logger.info(f"PHASE 3: Added {len(live_sorted)} LIVE matches (secondary priority)")
        
        # Logs de priorisation
        upcoming_count = len([m for m in priority_list if m.get("priority") == "HIGH_PREMATCH"])
        live_count = len([m for m in priority_list if m.get("priority") == "SECONDARY_LIVE"])
        
        logger.info(f"PHASE FINAL: Prioritized {upcoming_count} UPCOMING (PRE-MATCH) + {live_count} LIVE (SECONDARY)")
        
        return priority_list
    
    def _analyze_match(
        self,
        match: Any,
        profile: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a match with REAL historical data - Phase 3: Full history for all targeted matches

        Args:
            match: Match object
            profile: League profile

        Returns:
            Analysis dict or None
        """
        try:
            # Import MatchDataLoader and EventDetector
            from app.services.data.match_data_loader import MatchDataLoader
            from app.services.events.event_detector import get_detector
            
            # Get team IDs
            home_team_id = getattr(match.home_team, 'id', None) if hasattr(match, 'home_team') else None
            away_team_id = getattr(match.away_team, 'id', None) if hasattr(match, 'away_team') else None
            
            # PHASE 5: Detect event context for conservative rules
            event_detector = get_detector()
            event_context = event_detector.detect_event(match)
            is_event_match = event_context.get("is_event_match", False)
            event_type = event_context.get("event_context", "DOMESTIC_LEAGUE")
            
            logger.info(f"[EVENT] Event context: {event_type}, is_event_match: {is_event_match}")
            
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

            # ── ODDS_FIRST_MODE — relax threshold when fixture has bookmaker odds ──
            _MIN_MATCHES_ODDS = 4
            _fid_str  = SmartScanner.get_fixture_id(match)
            _apifb_fc = getattr(getattr(self.odds_provider, '_apifb', None), '_fixture_cache', {}) if self.odds_provider else {}
            _odds_first = bool(_apifb_fc.get(_fid_str))

            # Check data quality
            if bundle.history_status == "MISSING":
                logger.warning(f"No historical data available")
                return {
                    "status": "DATA_INSUFFICIENT",
                    "reason": "NO_HISTORY_AVAILABLE",
                    "signals": [],
                    "data_origin": "REAL",
                    "home_history_count": 0,
                    "away_history_count": 0,
                    "event_context": event_context
                }
            
            if bundle.history_status == "INSUFFICIENT":
                _total_h = bundle.home_history_count + bundle.away_history_count
                
                # PHASE 5: Conservative event rules
                if is_event_match:
                    logger.warning(f"[EVENT] Insufficient data for event match: {_total_h} matches")
                    return {
                        "status": "EVENT_RESEARCH_ONLY",
                        "reason": "INSUFFICIENT_EVENT_DATA",
                        "sample_size": _total_h,
                        "signals": [],
                        "data_origin": "REAL",
                        "home_history_count": bundle.home_history_count,
                        "away_history_count": bundle.away_history_count,
                        "event_context": event_context,
                        "event_rules_applied": True
                    }
                
                if not _odds_first or _total_h < _MIN_MATCHES_ODDS:
                    logger.warning(f"Insufficient historical data: {_total_h} matches")
                    return {
                        "status": "DATA_INSUFFICIENT",
                        "reason": "INSUFFICIENT_SAMPLE_SIZE",
                        "sample_size": _total_h,
                        "signals": [],
                        "data_origin": "REAL",
                        "home_history_count": bundle.home_history_count,
                        "away_history_count": bundle.away_history_count,
                        "event_context": event_context
                    }
                logger.info(f"[ODDS_FIRST] fixture={_fid_str} total_h={_total_h} → proceeding (min={_MIN_MATCHES_ODDS})")
            
            # Extract REAL goal histories
            goal_history = bundle.get_ft_goal_history()
            ht_goal_history = bundle.get_ht_goal_history()
            
            _ft_min = _MIN_MATCHES_ODDS if _odds_first else 5
            if len(goal_history) < _ft_min:
                logger.warning(f"Insufficient FT data: {len(goal_history)} matches (min={_ft_min}, odds_first={_odds_first})")
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
            
            # PHASE 3: VRAIES PROJECTIONS PRÉ-MATCH STATISTIQUES
            logger.info(f"PHASE 3: Generating PRE-MATCH statistical projections...")
            
            # Extraire les données séparées home/away/H2H
            home_history = bundle.home_history
            away_history = bundle.away_history
            h2h_history = bundle.h2h
            
            # Calculer les profils statistiques
            home_profile = self._calculate_home_profile(home_history, ht_goal_history)
            away_profile = self._calculate_away_profile(away_history, ht_goal_history)
            h2h_profile = self._calculate_h2h_profile(h2h_history) if h2h_history else None
            
            # Calculer le profil de tempo et volatilité
            tempo_profile = self._calculate_tempo_profile(goal_history, home_profile, away_profile)
            volatility_profile = self._calculate_volatility_profile(goal_history, home_profile, away_profile)
            
            # Générer les projections pré-match
            projections = self._generate_pre_match_projections(home_profile, away_profile, h2h_profile, tempo_profile, volatility_profile)
            
            # Calculer les scores de confiance
            confidence_scores = self._calculate_confidence_scores(home_profile, away_profile, h2h_profile, goal_history)
            
            # Déterminer le tier (S/A/B/Weak)
            tier = self._calculate_tier(confidence_scores, projections, volatility_profile)
            
            logger.info(f"PHASE 3: Generated {len(projections)} projections, tier={tier}, confidence={confidence_scores.get('overall', 0)}")
            
            # Build BTTS/home-away history early (needed for signal detection)
            _all_hist = bundle.home_history + bundle.away_history
            match_history_btts = [
                {
                    "home_goals": getattr(_m, 'home_score', 0),
                    "away_goals": getattr(_m, 'away_score', 0),
                    "total_goals": (getattr(_m, 'home_score', 0) or 0) + (getattr(_m, 'away_score', 0) or 0),
                }
                for _m in _all_hist
            ]

            # Generate signals (multi-regime: UNDER + OVER + BTTS + SH)
            home_name = match.home_team.name if hasattr(match, 'home_team') else ''
            away_name = match.away_team.name if hasattr(match, 'away_team') else ''
            match_dict = {
                "match_id": _fid_str,
                "home_team": home_name,
                "away_team": away_name,
                "competition": profile.competition_name,
                "country": profile.country
            }

            signals = self.signal_engine.detect_signals(
                match=match_dict,
                goal_history=goal_history,
                ht_goal_history=ht_goal_history,
                match_history=match_history_btts,
            )

            # Phase 6: Fetch normalized bookmaker odds (non-blocking)
            normalized_odds = []
            match_mapping = None
            odds_status = "NO_KEY" if not self.odds_provider or not getattr(self.odds_provider, 'api_key', None) else "NO_EVENTS"
            market_mapping_confidence = 0.0

            if self.odds_provider and getattr(self.odds_provider, 'api_key', None):
                try:
                    normalized_odds, match_mapping = self.odds_provider.get_match_odds_normalized(
                        match_id=str(match_dict["match_id"]),
                        home_team=home_name,
                        away_team=away_name,
                    )
                    if normalized_odds:
                        odds_status = "MATCHED" if match_mapping and match_mapping.confidence_label in ("EXACT", "HIGH") else "MATCHING_UNCERTAIN"
                        market_mapping_confidence = match_mapping.match_confidence_score if match_mapping else 0.0
                        logger.info(f"[ODDS] {len(normalized_odds)} odds for {home_name} vs {away_name} (conf={market_mapping_confidence:.2f})")
                    elif match_mapping and match_mapping.confidence_label == "FAILED":
                        odds_status = "MATCHING_UNCERTAIN"
                    else:
                        odds_status = "NO_EVENTS"
                except Exception as e:
                    logger.debug(f"[ODDS] Non-blocking fetch failed: {e}")
                    odds_status = "PROVIDER_ERROR"

            # Phase 4 — DEBUG_ODDS_WIRING diagnostics (env var gated)
            import os as _os
            if _os.getenv('DEBUG_ODDS_WIRING', '').lower() == 'true':
                _has_prefetched = bool(_apifb_fc.get(_fid_str))
                _first5_markets = [nd.market for nd in normalized_odds[:5]]
                logger.info(
                    f"[WIRE_PROVIDER] provider_id={id(self.odds_provider)}"
                    f" | fixture_id={_fid_str}"
                    f" | cache_hit={_has_prefetched}"
                    f" | odds_count={len(normalized_odds)}"
                    f" | first_5_markets={_first5_markets}"
                    f" | odds_status={odds_status}"
                )

            # Build odds lookup: market_str → best_odd (highest = most favourable)
            odds_by_market: Dict[str, float] = {}
            odds_bookmaker_by_market: Dict[str, str] = {}
            for nd in normalized_odds:
                existing = odds_by_market.get(nd.market, 0)
                if nd.odd > existing:
                    odds_by_market[nd.market] = nd.odd
                    odds_bookmaker_by_market[nd.market] = nd.bookmaker

            # Phase 6: EV computation per signal using EVCalculator
            from app.services.analysis.ev_calculator import EVCalculator
            ev_calc = EVCalculator()
            ev_opportunities = []
            
            # PHASE 5: Conservative event rules for EV
            if is_event_match:
                # Require real odds for event matches
                if not odds_by_market:
                    logger.warning(f"[EVENT] No odds available for event match - skipping EV")
                    # Continue with analysis but mark as event_research_only
                    event_research_only = True
                else:
                    logger.info(f"[EVENT] Real odds available for event match: {len(odds_by_market)} markets")
                    event_research_only = False
            else:
                event_research_only = False

            # Signal-type to market string candidates
            _SIGNAL_MARKET_CANDIDATES = {
                "HT_UNDER":            ["HT_UNDER_0_5", "HT_UNDER_1_5"],
                "HT_OVER":             ["HT_OVER_0_5", "HT_OVER_1_0", "HT_OVER_1_5"],
                "FT_UNDER":            ["FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5"],
                "FT_OVER":             ["FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5"],
                "BTTS_YES":            ["BTTS_YES"],
                "BTTS_NO":             ["BTTS_NO"],
                "BTTS_PROFILE":        ["BTTS_YES"],
                "HOME_DOMINANT":       ["HOME_OVER_0_5"],
                "ASYMMETRIC_SCORING":  ["AWAY_OVER_0_5"],
                "SECOND_HALF_EXPLOSION": ["SECOND_HALF_OVER_1_5", "SECOND_HALF_OVER_0_5"],
                "EXTREME_UNDER":       ["FT_UNDER_1_5", "FT_UNDER_2_5"],
                "LOW_VARIANCE":        ["FT_UNDER_2_5", "FT_UNDER_1_5"],
            }
            # Phase 3 — markets that cannot be supplied by any current odds provider
            # Kept as statistical signals; EV calculation skipped (no bookmaker odd ever available)
            _EV_DISABLED_MARKETS = {
                "HOME_OVER_0_5", "AWAY_OVER_0_5",
                "HT_OVER_1_0",
                "SECOND_HALF_OVER_0_5", "SECOND_HALF_OVER_1_5",
            }

            # Market-specific probability from actual goal history — EV calibration.
            # signal.confidence is a discrete tier (0.7/0.8/0.9) used for ranking;
            # here we compute the real historical hit-rate per market line so that
            # EVCalculator receives an accurate model_probability.
            _market_hit_rate: Dict[str, float] = {}
            if goal_history:
                _mhr_n = len(goal_history)
                for _mhr_line, _mhr_u, _mhr_o in [
                    (1.5, "FT_UNDER_1_5", "FT_OVER_1_5"),
                    (2.5, "FT_UNDER_2_5", "FT_OVER_2_5"),
                    (3.5, "FT_UNDER_3_5", "FT_OVER_3_5"),
                ]:
                    _market_hit_rate[_mhr_u] = sum(1 for g in goal_history if g < _mhr_line) / _mhr_n
                    _market_hit_rate[_mhr_o] = sum(1 for g in goal_history if g > _mhr_line) / _mhr_n
            if ht_goal_history:
                _mhr_ht_n = len(ht_goal_history)
                for _mhr_line, _mhr_u, _mhr_o in [
                    (0.5, "HT_UNDER_0_5", "HT_OVER_0_5"),
                    (1.5, "HT_UNDER_1_5", "HT_OVER_1_5"),
                ]:
                    _market_hit_rate[_mhr_u] = sum(1 for g in ht_goal_history if g < _mhr_line) / _mhr_ht_n
                    _market_hit_rate[_mhr_o] = sum(1 for g in ht_goal_history if g > _mhr_line) / _mhr_ht_n

            for signal in signals:
                candidates = _SIGNAL_MARKET_CANDIDATES.get(signal.signal_type, [])
                for mkt_str in candidates:
                    if mkt_str in _EV_DISABLED_MARKETS:
                        continue
                    bk_odd = odds_by_market.get(mkt_str)
                    if _os.getenv('DEBUG_ODDS_WIRING', '').lower() == 'true':
                        logger.info(
                            f"[WIRE_SIG] fixture_id={_fid_str}"
                            f" | signal={signal.signal_type}"
                            f" | selected_market={mkt_str}"
                            f" | selected_market_has_odd={bk_odd is not None}"
                            f" | odd={bk_odd}"
                        )
                    # PHASE 5: Conservative event rules - require odds for event matches
                    if not bk_odd:
                        if is_event_match:
                            logger.debug(f"[EVENT] Skipping {mkt_str} - no odds for event match")
                        continue
                    ev_result = ev_calc.calculate(
                        model_probability=_market_hit_rate.get(mkt_str, signal.confidence),
                        bookmaker_odd=bk_odd,
                        market_type=mkt_str,
                        line=float(mkt_str.split("_")[-1].replace("_", ".")) if mkt_str.split("_")[-1].replace("_", "").isdigit() else None,
                        sample_size=signal.sample_size,
                        bookmaker=odds_bookmaker_by_market.get(mkt_str, "unknown"),
                        signal_type=signal.signal_type,
                    )
                    if ev_result and ev_result.expected_value > 0:
                        ev_opportunities.append(ev_result)

            # Deduplicate: keep highest EV result per market (multiple signals can
            # target the same market; only one entry per market is needed)
            _ev_best_by_market: Dict[str, object] = {}
            for _ev_r in ev_opportunities:
                _mkt_key = _ev_r.market_type
                if _mkt_key not in _ev_best_by_market or _ev_r.expected_value > _ev_best_by_market[_mkt_key].expected_value:
                    _ev_best_by_market[_mkt_key] = _ev_r
            ev_opportunities = list(_ev_best_by_market.values())

            # Sort by EV descending
            ev_opportunities.sort(key=lambda r: r.expected_value, reverse=True)
            best_ev = ev_opportunities[0] if ev_opportunities else None

            # EV safety gates — classify each unique market pick
            # Gates (ordered by severity): real odds, odds source, odd floor,
            # sample size, probability bounds, minimum EV threshold.
            _has_real_odds_gate = bool(normalized_odds)
            _odds_src_gate      = normalized_odds[0].source if normalized_odds else "NONE"
            _sig_conf_map       = {s.signal_type: s.confidence for s in signals}

            ev_qualified: list = []
            ev_rejected:  list = []

            for _ev_r in ev_opportunities:
                _mprob  = _ev_r.model_probability
                _ev_pct = _ev_r.expected_value_percent
                _bk_odd = _ev_r.bookmaker_odd
                _ssize  = _ev_r.sample_size
                _sconf  = _sig_conf_map.get(_ev_r.signal_type)
                _vlevel = _ev_r.value_level

                _reject = None
                if not _has_real_odds_gate:
                    _reject = "NO_REAL_ODDS"
                elif _odds_src_gate not in ("API_FOOTBALL", "ODDS_API"):
                    _reject = "INVALID_ODDS_SOURCE"
                elif _bk_odd < 1.20:
                    _reject = "ODD_TOO_LOW"
                elif _ssize < 10:
                    _reject = "SAMPLE_TOO_SMALL"
                elif _mprob < 0.15 or _mprob > 0.95:
                    _reject = "PROBABILITY_OUT_OF_BOUNDS"
                elif _ev_pct < 5.0:
                    _reject = "EV_TOO_LOW"

                if _reject is None:
                    _class = ("S_TIER_EV" if _vlevel in ("EXTREME", "HIGH")
                              else "A_TIER_EV" if _vlevel == "MEDIUM"
                              else "B_TIER_EV")
                else:
                    _class = ("WATCHLIST_STATISTICAL"
                              if _reject in ("EV_TOO_LOW", "PROBABILITY_OUT_OF_BOUNDS")
                              else "REJECTED_EV")

                # Normalize scales - guard against percent/fraction confusion
                _mprob_normalized = _mprob
                if _mprob_normalized and _mprob_normalized > 1.0:
                    _mprob_normalized = round(_mprob_normalized / 100.0, 4)
                
                # Calculate fair_odd from normalized market_probability
                _fair_odd = round(1.0 / _mprob_normalized, 3) if _mprob_normalized and _mprob_normalized > 0 else None
                
                # Normalize implied_probability as well
                _implied_normalized = _ev_r.implied_probability
                if _implied_normalized and _implied_normalized > 1.0:
                    _implied_normalized = round(_implied_normalized / 100.0, 4)
                
                _pick = {
                    "market":              _ev_r.market_type,
                    "market_probability":  round(_mprob_normalized, 4),
                    "probability_source":  "MARKET_HIT_RATE",
                    "signal_confidence":   round(_sconf, 4) if _sconf is not None else None,
                    "signal_type":         _ev_r.signal_type,
                    "bookmaker_odd":       round(_bk_odd, 3),
                    "fair_odd":            _fair_odd,
                    "implied_probability": round(_implied_normalized, 4),
                    "ev_percentage":       round(_ev_pct, 2),
                    "edge_percentage":     round(_ev_r.edge_percent, 2),
                    "sample_size":         _ssize,
                    "has_real_odds":       _has_real_odds_gate,
                    "odds_source":         _odds_src_gate,
                    "bookmaker":           _ev_r.bookmaker,
                    "value_level":         _vlevel,
                    "classification":      _class,
                }
                if _reject:
                    _pick["rejection_reason"] = _reject
                    ev_rejected.append(_pick)
                else:
                    ev_qualified.append(_pick)

            # ── Market generation tracking (Phase multi-regime) ───────────────
            _all_generated: dict = {}  # market -> signal_type
            for _sig in signals:
                for _mkt in _SIGNAL_MARKET_CANDIDATES.get(_sig.signal_type, []):
                    if _mkt not in _all_generated:
                        _all_generated[_mkt] = _sig.signal_type
            _top3_types = {s.signal_type for s in signals[:3]}
            _selected_markets: set = set()
            for _sig in signals[:3]:
                for _mkt in _SIGNAL_MARKET_CANDIDATES.get(_sig.signal_type, []):
                    _selected_markets.add(_mkt)
            _rejection_reasons: dict = {}
            for _mkt, _stype in _all_generated.items():
                if _stype not in _top3_types:
                    _rejection_reasons[_mkt] = "ranking_lower_than_top3"
                elif _mkt not in odds_by_market:
                    _rejection_reasons[_mkt] = "no_bookmaker_odds"
            market_generation_stats = {
                "generated_count":   len(_all_generated),
                "selected_count":    len(_selected_markets),
                "rejected_count":    len(_all_generated) - len(_selected_markets),
                "generated_markets": list(_all_generated.keys()),
                "selected_markets":  list(_selected_markets),
            }

            # Line breach analysis
            line_analyses = self.line_analyzer.analyze_all_lines(goal_history)

            # Build analysis result with value assessment AND fair odds
            signals_with_value = []
            for signal in signals[:3]:  # Top 3 signals (extended for multi-regime)
                # Phase 6: use real bookmaker odd if available
                candidates = _SIGNAL_MARKET_CANDIDATES.get(signal.signal_type, [])
                bk_odd = next((odds_by_market[m] for m in candidates if m in odds_by_market), None)
                bk_name = next((odds_bookmaker_by_market[m] for m in candidates if m in odds_bookmaker_by_market), "unknown")

                # Calculate fair odds
                fair_odds_assessment = self.fair_odds_calc.calculate_fair_odds(
                    historical_probability=signal.confidence,
                    bookmaker_odd=bk_odd
                )

                # PHASE 5: Conservative event rules - LIVE_SAFE only if odds exist for events
                selection_mode = "LIVE_SAFE" if bk_odd and (not is_event_match or (is_event_match and bk_odd)) else "RESEARCH_ONLY"
                
                # Assess value
                value_assessment = self.value_detector.assess_value(
                    statistical_probability=signal.confidence,
                    variance_score=signal.variance_score,
                    sample_size=signal.sample_size,
                    data_quality=signal.data_quality,
                    bookmaker_odd=bk_odd,
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
                    "value_assessment": value_assessment.to_dict(),
                    "selection_mode": selection_mode,
                    "event_research_only": event_research_only if is_event_match else False
                })
            
            # Build HT Analysis Table
            ht_analysis_table = []
            if ht_goal_history:
                _ht_n   = len(ht_goal_history)
                _ht_avg = sum(ht_goal_history) / _ht_n
                _ht_max = max(ht_goal_history)
                for line in [0.5, 1.5, 2.5, 3.5]:
                    under_count = sum(1 for g in ht_goal_history if g < line)
                    hit_rate = under_count / _ht_n
                    fair_odd = self.fair_odds_calc.calculate_fair_odds(hit_rate) if hit_rate > 0 else None
                    ht_analysis_table.append({
                        "line": f"U{line}",
                        "hit_rate": hit_rate * 100,
                        "under_count": under_count,
                        "over_count": _ht_n - under_count,
                        "sample_size": _ht_n,
                        "fair_odd": fair_odd.fair_odd if fair_odd else None,
                        "max_ht_goals": _ht_max,
                        "avg_ht_goals": _ht_avg,
                    })
                # OVER rows (Phase 1 — multi-regime)
                for line in [0.5, 1.0, 1.5]:
                    over_count = sum(1 for g in ht_goal_history if g > line)
                    hr_over = over_count / _ht_n
                    fo_over = self.fair_odds_calc.calculate_fair_odds(hr_over) if hr_over > 0 else None
                    ht_analysis_table.append({
                        "line": f"O{line}",
                        "hit_rate": hr_over * 100,
                        "under_count": _ht_n - over_count,
                        "over_count": over_count,
                        "sample_size": _ht_n,
                        "fair_odd": fo_over.fair_odd if fo_over else None,
                        "max_ht_goals": _ht_max,
                        "avg_ht_goals": _ht_avg,
                    })
            
            # Build FT Analysis Table
            ft_analysis_table = []
            _ft_n   = len(goal_history)
            _ft_avg = sum(goal_history) / _ft_n
            _ft_max = max(goal_history)
            for line in [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 10.5, 12.5]:
                under_count = sum(1 for g in goal_history if g < line)
                hit_rate = under_count / _ft_n
                fair_odd = self.fair_odds_calc.calculate_fair_odds(hit_rate) if hit_rate > 0 else None
                ft_analysis_table.append({
                    "line": f"U{line}",
                    "hit_rate": hit_rate * 100,
                    "under_count": under_count,
                    "over_count": _ft_n - under_count,
                    "sample_size": _ft_n,
                    "fair_odd": fair_odd.fair_odd if fair_odd else None,
                    "max_goals": _ft_max,
                    "avg_goals": _ft_avg,
                })
            # OVER rows (Phase 1 — multi-regime)
            for line in [1.5, 2.5, 3.5, 4.5]:
                over_count = sum(1 for g in goal_history if g > line)
                hr_over = over_count / _ft_n
                fo_over = self.fair_odds_calc.calculate_fair_odds(hr_over) if hr_over > 0 else None
                ft_analysis_table.append({
                    "line": f"O{line}",
                    "hit_rate": hr_over * 100,
                    "under_count": _ft_n - over_count,
                    "over_count": over_count,
                    "sample_size": _ft_n,
                    "fair_odd": fo_over.fair_odd if fo_over else None,
                    "max_goals": _ft_max,
                    "avg_goals": _ft_avg,
                })
            
            # Build match history display (last 10 for UI)
            match_history = []
            for i, goals in enumerate(goal_history[:10]):
                ht_goals_i = ht_goal_history[i] if i < len(ht_goal_history) else None
                match_history.append({
                    "match_number": i + 1,
                    "total_goals": goals,
                    "ht_goals": ht_goals_i
                })
            
            # EDGE DETECTION: Detect bookmaker mispricing (PHASE 6: Non bloquant)
            best_edges = []
            edge_results = {}
            try:
                edge_results = self.edge_detector.detect_all_edges(
                    ht_goals=ht_goal_history,
                    ft_goals=goal_history,
                    ht_analysis={"table": ht_analysis_table},
                    ft_analysis={"table": ft_analysis_table},
                    bookmaker_odds=None,  # PHASE 6: Pas de dépendance odds
                    match_history=match_history_btts  # For BTTS detection
                )
                best_edges = edge_results.get("best_edges", [])
            except Exception as e:
                logger.warning(f"[EDGE] Edge detection failed (non-blocking): {e}")
                best_edges = []
            
            # MATCH PROFILING: Generate comprehensive profile for discovery
            match_profile = self.match_profiler.profile_match(
                ft_goals=goal_history,
                ht_goals=ht_goal_history,
                match_history=match_history_btts
            )
            
            # PHASE 6: Intégrer les projections pré-match dans le profil
            logger.info(f"[PROJECTIONS] Integrating {len(projections)} pre-match projections")
            logger.info(f"[PROJECTIONS] Tier: {tier}, Overall confidence: {confidence_scores.get('overall', 0):.1f}")

            # Ajouter les projections au profil de match
            match_profile.pre_match_projections = projections
            match_profile.tier = tier
            match_profile.projection_confidence = confidence_scores
            match_profile.tempo_profile = tempo_profile
            match_profile.volatility_profile = volatility_profile

            # Ajouter les profils détaillés
            match_profile.home_profile = home_profile
            match_profile.away_profile = away_profile
            match_profile.h2h_profile = h2h_profile

            # ==========================================
            # STEP 1: LEAGUE INTELLIGENCE
            # ==========================================
            league_name = getattr(profile, 'competition_name', None) or "CONTEXT"
            league_context = self.league_profile_engine.compute_from_match_context(
                ft_goals=goal_history,
                ht_goals=ht_goal_history,
                match_history=match_history_btts,
                league_name=league_name,
            )
            adj_conf, league_reasons = self.league_profile_engine.adjust_confidence_for_profile(
                match_profile.confidence_score, league_context
            )
            match_profile.confidence_score = adj_conf
            if league_reasons:
                logger.info(f"[LEAGUE_INTEL] Confidence adjusted: {league_reasons}")

            # ==========================================
            # STEP 2: VOLATILITY ENGINE
            # ==========================================
            volatility_result = self.volatility_engine.analyze(
                ft_goals=goal_history,
                ht_goals=ht_goal_history,
                match_history=match_history_btts,
            )
            match_profile.confidence_score = max(
                0.0, match_profile.confidence_score * volatility_result.confidence_multiplier
            )
            match_profile.volatility_score = max(
                match_profile.volatility_score, volatility_result.volatility_score
            )
            if volatility_result.refuse_pick:
                logger.warning(f"[VOLATILITY] Pick REFUSED: {volatility_result.refuse_reason}")
            elif volatility_result.tags:
                logger.info(f"[VOLATILITY] Tags: {volatility_result.tags}, multiplier={volatility_result.confidence_multiplier}")

            # ==========================================
            # STEP 3: FALSE SIGNAL DETECTOR
            # ==========================================
            false_signal_result = self.false_signal_detector.analyze(
                ft_goals=goal_history,
                ht_goals=ht_goal_history,
                match_history=match_history_btts,
                h2h_count=bundle.h2h_count,
                sample_size=len(goal_history),
                home_sample=bundle.home_history_count,
                away_sample=bundle.away_history_count,
            )
            match_profile.confidence_score = max(
                0.0, match_profile.confidence_score * false_signal_result.confidence_penalty
            )
            if false_signal_result.warnings:
                logger.info(f"[FALSE_SIGNAL] score={false_signal_result.false_signal_score:.0f}, warnings={false_signal_result.warnings[:2]}")

            # ==========================================
            # STEP 4: LEAGUE SPECIALIZATION ENGINE
            # ==========================================
            _lse_rec = SmartRecommendation()
            _lse_conf_adj = 1.0
            _lse_adj_reason = ""
            if self.league_spec_engine.is_ready:
                try:
                    _lse_country = getattr(profile, 'country', '')
                    # Best market from strongest signal
                    _lse_market = ""
                    if signals:
                        _best_sig = max(signals, key=lambda s: s.confidence)
                        _candidates = _SIGNAL_MARKET_CANDIDATES.get(_best_sig.signal_type, [])
                        _lse_market = _candidates[0] if _candidates else _best_sig.signal_type
                    _lse_conf_adj, _lse_adj_reason = self.league_spec_engine.adjust_confidence(
                        confidence=match_profile.confidence_score,
                        league=league_name,
                        country=_lse_country,
                        market=_lse_market,
                    )
                    if _lse_conf_adj != 1.0:
                        match_profile.confidence_score = max(
                            0.0, match_profile.confidence_score * _lse_conf_adj
                        )
                        logger.info(f"[LSE] Confidence ×{_lse_conf_adj:.2f}: {_lse_adj_reason}")
                    _lse_rec = self.league_spec_engine.get_smart_recommendations(
                        league=league_name, country=_lse_country, market=_lse_market,
                    )
                except Exception as _lse_err:
                    logger.debug(f"[LSE] Non-blocking error: {_lse_err}")

            # ── STEP 4b: ERROR ANALYSIS ENGINE ──────────────────────────────
            _eae_explanation = PickExplanation()
            _eae_penalty = 1.0
            _eae_reason  = ""
            try:
                _eae_explanation = self.error_analysis_engine.generate_pick_explanation(
                    league=league_name,
                    country=getattr(profile, 'country', ''),
                    market=_lse_market,
                    confidence=match_profile.confidence_score,
                    volatility=volatility_result.volatility_score,
                    chaos=volatility_result.chaos_score,
                    false_signal_score=false_signal_result.false_signal_score,
                    league_tags=league_context.tags,
                    volatility_tags=volatility_result.tags,
                    tier_downgrade=false_signal_result.tier_downgrade,
                    refuse_pick=volatility_result.refuse_pick,
                    refuse_reason=volatility_result.refuse_reason,
                    league_reliability=league_context.reliability_score,
                    lse_edge_rating=_lse_rec.league_edge_rating,
                    lse_market_prof=_lse_rec.market_historical_profitability,
                )
                if self.error_analysis_engine.is_ready:
                    _eae_penalty, _eae_reason = self.error_analysis_engine.get_historical_failure_penalty(
                        league_name, getattr(profile, 'country', ''), _lse_market,
                    )
                    if _eae_penalty < 1.0:
                        match_profile.confidence_score = max(
                            0.0, match_profile.confidence_score * _eae_penalty
                        )
                        logger.info(f"[EAE] FP penalty ×{_eae_penalty:.2f}: {_eae_reason}")
            except Exception as _eae_err:
                logger.debug(f"[EAE] Non-blocking error: {_eae_err}")

            # ==========================================
            # STEP 5: HOME/AWAY CONTEXT ENGINE
            # ==========================================
            home_away_result = self.home_away_engine.analyze(
                home_profile=home_profile,
                away_profile=away_profile,
                match_history=match_history_btts,
            )

            # PHASE 6: Logging
            logger.info(f"[ANALYSIS] History counts: home={bundle.home_history_count}, away={bundle.away_history_count}")
            logger.info(f"[ANALYSIS] HT rows calculated: {len(ht_analysis_table)}")
            logger.info(f"[ANALYSIS] FT rows calculated: {len(ft_analysis_table)}")
            logger.info(f"[ANALYSIS] Signals generated: {len(signals_with_value)}")
            logger.info(f"[EDGE] Best edges detected: {len(best_edges)}")
            logger.info(f"[PROFILE] Interest score: {match_profile.interest_score:.0f}, Confidence: {match_profile.confidence_score:.0f}")
            logger.info(f"[PROJECTIONS] Tier: {tier}, Projections: {len(projections)}")
            logger.info(f"[PROJECTIONS] Tempo: {tempo_profile}, Consistency: {volatility_profile.get('consistency_score', 0):.1f}")

            # Phase 7: EV Tier classification (requires odds)
            tier_level, ranking_score = self._compute_tier_level(
                ev_opportunities=ev_opportunities,
                best_ev=best_ev,
                signals=signals,
                sample_size=len(goal_history),
                variance_score=match_profile.volatility_score if hasattr(match_profile, 'volatility_score') else 0.5,
                has_odds=bool(normalized_odds),
                refuse_pick=volatility_result.refuse_pick,
                tier_downgrade=false_signal_result.tier_downgrade,
                ranking_penalty=false_signal_result.ranking_penalty,
            )

            # Phase 7b: Statistical Tier (independent of odds)
            _vol_for_stat = volatility_result.volatility_score if volatility_result.volatility_score > 0 else (match_profile.volatility_score * 100 if hasattr(match_profile, 'volatility_score') else 50)
            statistical_tier, statistical_ranking_score = self._compute_statistical_tier(
                confidence_score=match_profile.confidence_score,
                volatility_score=_vol_for_stat,
                false_signal_score=false_signal_result.false_signal_score,
                league_reliability=league_context.reliability_score,
                sample_size=len(goal_history),
                refuse_pick=volatility_result.refuse_pick,
                tier_downgrade=false_signal_result.tier_downgrade,
                ranking_penalty=false_signal_result.ranking_penalty,
            )

            # ── UNIVERSE DETERMINATION ──────────────────────────────────────
            _has_good_odds = bool(normalized_odds) and odds_status in ("MATCHED", "MATCHING_UNCERTAIN")
            if _has_good_odds:
                match_universe   = "MARKET_EV"
                coverage_quality = "FULL" if market_mapping_confidence >= 0.80 else "PARTIAL"
            else:
                match_universe   = "STATISTICAL_ONLY"
                coverage_quality = "NONE"

            # ── PHASE 2: Market regime detection ────────────────────────────
            _avg_g  = sum(goal_history) / len(goal_history)
            _ht_avg = (sum(ht_goal_history) / len(ht_goal_history)) if ht_goal_history else 0.0
            _n      = len(goal_history)
            _o25    = sum(1 for g in goal_history if g > 2.5) / _n
            _u15    = sum(1 for g in goal_history if g < 1.5) / _n
            _btts_r = (
                sum(1 for m in match_history_btts
                    if (m.get("home_goals") or 0) > 0 and (m.get("away_goals") or 0) > 0)
                / max(len(match_history_btts), 1)
            )
            _chaos_dir = volatility_result.recommended_market_direction
            _chaos_type = volatility_result.chaos_type
            _late_r = volatility_result.late_goal_rate
            _expan  = volatility_result.ht_to_ft_expansion

            if _chaos_type == "OFFENSIVE" or (_avg_g >= 3.0 and _o25 >= 0.65):
                market_regime = "HIGH_TEMPO_OVER"
            elif _u15 >= 0.60 and _avg_g < 1.5 and _ht_avg < 0.6:
                market_regime = "LOW_TEMPO_UNDER"
            elif _btts_r >= 0.65 and _avg_g >= 2.2:
                market_regime = "BTTS_PROFILE"
            elif _late_r >= 60 and _expan >= 2.0:
                market_regime = "SECOND_HALF_CHAOS"
            elif _ht_avg >= 1.2 and _avg_g >= 2.5:
                market_regime = "EARLY_GOAL_PROFILE"
            elif home_profile and home_profile.get("avg_home_goals_scored", 0) >= 1.8:
                market_regime = "HOME_DOMINANT"
            elif _chaos_type == "DEFENSIVE":
                market_regime = "ASYMMETRIC_MATCHUP"
            elif _late_r >= 55:
                market_regime = "LATE_GOAL_LEAGUE"
            else:
                market_regime = "BALANCED"

            # ── PHASE 4: Over Intelligence metrics ──────────────────────────
            _sh_goals_list = (
                [goal_history[i] - ht_goal_history[i]
                 for i in range(min(_n, len(ht_goal_history)))]
                if ht_goal_history else []
            )
            early_goal_rate = (
                sum(1 for g in ht_goal_history if g > 0) / len(ht_goal_history)
                if ht_goal_history else 0.0
            )
            second_half_goal_rate = (
                sum(_sh_goals_list) / (len(_sh_goals_list) * max(_avg_g, 0.01))
                if _sh_goals_list and _avg_g > 0 else 0.0
            )
            explosive_pairing_score = min(100.0, volatility_result.explosive_match_rate * 2.5)
            _h_scored = (home_profile.get("avg_home_goals_scored", 0) if home_profile else 0)
            _a_scored = (away_profile.get("avg_away_goals_scored", 0) if away_profile else 0)
            offensive_overlap_score = min(100.0, (_h_scored + _a_scored) / max(_avg_g, 0.01) * 40)
            comeback_freq = volatility_result.comeback_rate

            over_intelligence = {
                "early_goal_rate":         round(early_goal_rate * 100, 1),
                "second_half_goal_rate":   round(second_half_goal_rate * 100, 1),
                "explosive_pairing_score": round(explosive_pairing_score, 1),
                "offensive_overlap_score": round(offensive_overlap_score, 1),
                "comeback_frequency":      round(comeback_freq, 1),
                "btts_rate":               round(_btts_r * 100, 1),
                "over_2_5_rate":           round(_o25 * 100, 1),
            }

            # ── PHASE 5: Smart market ranking ────────────────────────────────
            _OVER_TYPES  = {"FT_OVER", "HT_OVER", "BTTS_PROFILE", "BTTS_YES",
                            "HOME_DOMINANT", "ASYMMETRIC_SCORING", "SECOND_HALF_EXPLOSION"}
            _UNDER_TYPES = {"HT_UNDER", "FT_UNDER", "EXTREME_UNDER", "LOW_VARIANCE"}

            def _market_score(sig) -> float:
                base = sig.confidence * 100
                base += {"EXTREME": 15, "STRONG": 10, "MODERATE": 5}.get(sig.signal_strength, 0)
                if sig.variance_score >= 0.7:
                    base += 5
                if market_regime in ("HIGH_TEMPO_OVER", "EARLY_GOAL_PROFILE"):
                    if sig.signal_type in _OVER_TYPES:
                        base += 12
                    elif sig.signal_type in _UNDER_TYPES:
                        base -= 10
                elif market_regime in ("LOW_TEMPO_UNDER",):
                    if sig.signal_type in _UNDER_TYPES:
                        base += 12
                    elif sig.signal_type in _OVER_TYPES:
                        base -= 8
                if _chaos_dir in ("OVER",):
                    if sig.signal_type in _OVER_TYPES:
                        base += 8
                elif _chaos_dir in ("AVOID_UNDER",):
                    if sig.signal_type in _UNDER_TYPES:
                        base -= 15
                return base

            ranked_signals = sorted(signals, key=_market_score, reverse=True)
            best_signal    = ranked_signals[0] if ranked_signals else None
            second_signal  = ranked_signals[1] if len(ranked_signals) > 1 else None

            best_market       = best_signal.suggested_markets[0]   if best_signal  and best_signal.suggested_markets  else None
            secondary_market  = second_signal.suggested_markets[0] if second_signal and second_signal.suggested_markets else None

            # Avoid markets: UNDER picks when regime says OVER, and vice-versa
            avoid_markets = []
            if _chaos_dir == "AVOID_UNDER" or market_regime == "HIGH_TEMPO_OVER":
                avoid_markets = [m for s in signals if s.signal_type in _UNDER_TYPES
                                 for m in s.suggested_markets]
            elif market_regime == "LOW_TEMPO_UNDER":
                avoid_markets = [m for s in signals if s.signal_type in _OVER_TYPES
                                 for m in s.suggested_markets]

            best_over_market  = next(
                (s.suggested_markets[0] for s in ranked_signals
                 if s.signal_type in _OVER_TYPES and s.suggested_markets), None
            )
            best_under_market = next(
                (s.suggested_markets[0] for s in ranked_signals
                 if s.signal_type in _UNDER_TYPES and s.suggested_markets), None
            )

            recommended_playstyle = (
                "OVER_HUNTER"   if market_regime in ("HIGH_TEMPO_OVER", "EARLY_GOAL_PROFILE")
                else "UNDER_SPECIALIST" if market_regime == "LOW_TEMPO_UNDER"
                else "BTTS_TRADER"      if market_regime == "BTTS_PROFILE"
                else "SH_SPECIALIST"    if market_regime == "SECOND_HALF_CHAOS"
                else "NEUTRAL"
            )

            # ── Bettable Universe Classification (read-only, no logic change) ─
            try:
                _cov_score = float(
                    getattr(getattr(profile, 'bookmaker_coverage', None), 'coverage_score', None)
                    or 0.0
                )
            except Exception:
                _cov_score = 0.0
            _universe = _classify_bettable(
                country=profile.country,
                league=profile.competition_name,
                has_bookmaker_odds=bool(odds_by_market),
                odds_status=odds_status,
                coverage_score=_cov_score,
                statistical_tier=statistical_tier,
            )

            analysis = {
                "status": "ANALYZED_WITH_ODDS" if normalized_odds else "ANALYZED_NO_ODDS",
                # Phase 7: EV Tier (odds-dependent)
                "tier_level": tier_level,
                "ranking_score": round(ranking_score, 3),
                # Phase 7b: Statistical Tier (odds-independent)
                "statistical_tier": statistical_tier,
                "statistical_ranking_score": round(statistical_ranking_score, 3),
                # Universe (STATISTICAL_ONLY | MARKET_EV) + coverage (FULL | PARTIAL | NONE)
                "match_universe": match_universe,
                "coverage_quality": coverage_quality,
                # Intelligence engines (STEP 1-5)
                "league_intelligence": {
                    "league_name":          league_context.league_name,
                    "avg_goals":            round(league_context.avg_goals_per_match, 2),
                    "avg_ht_goals":         round(league_context.avg_ht_goals, 2),
                    "second_half_goals_rate": round(league_context.second_half_goals_rate, 1),
                    "btts_rate":            round(league_context.btts_rate, 1),
                    "under_2_5_rate":       round(league_context.under_2_5_rate, 1),
                    "over_2_5_rate":        round(league_context.over_2_5_rate, 1),
                    "goals_variance":       round(league_context.goals_variance, 3),
                    "comeback_frequency":   round(league_context.comeback_frequency, 1),
                    "late_goal_frequency":  round(league_context.late_goal_frequency, 1),
                    "volatility_score":     round(league_context.volatility_score, 1),
                    "stability_score":      round(league_context.stability_score, 1),
                    "reliability_score":    round(league_context.reliability_score, 1),
                    "tags":                 league_context.tags,
                    "confidence_adjustments": league_reasons,
                },
                "volatility_analysis":  volatility_result.to_dict(),
                "false_signal_analysis": false_signal_result.to_dict(),
                "home_away_analysis":   home_away_result.to_dict(),
                # STEP 4: League Specialization Engine recommendations
                "league_specialization": _lse_rec.to_dict(),
                # STEP 4b: Error Analysis Engine — pick explainability
                "pick_explanation": _eae_explanation.to_dict(),
                # Phase 6: EV
                "ev_opportunities": [r.to_dict() for r in ev_opportunities[:5]],
                "best_ev_opportunity": best_ev.to_dict() if best_ev else None,
                "ev_qualified": ev_qualified,
                "ev_rejected":  ev_rejected,
                # Phase 11: Odds metadata
                "odds_status": odds_status,
                "matched_odds": [nd.to_dict() for nd in normalized_odds[:20]],
                "odds_by_market": {nd.market: nd.to_dict() for nd in normalized_odds},
                "odds_count": len(normalized_odds),
                "has_real_odds": bool(normalized_odds),
                "odds_source": normalized_odds[0].source if normalized_odds else None,
                "fixture_id": _fid_str,
                "market_mapping_confidence": round(market_mapping_confidence, 3),
                "waiting_for_odds": not bool(normalized_odds),
                # PHASE 5: Event context fields
                "event_context": event_context,
                "is_event_match": is_event_match,
                "event_rules_applied": is_event_match,
                "matchup_profile": {
                    "home_avg_scored": home_profile.get("avg_home_goals_scored", 0) if home_profile else 0,
                    "home_avg_conceded": home_profile.get("avg_home_goals_conceded", 0) if home_profile else 0,
                    "away_avg_scored": away_profile.get("avg_away_goals_scored", 0) if away_profile else 0,
                    "away_avg_conceded": away_profile.get("avg_away_goals_conceded", 0) if away_profile else 0,
                    "expected_total_goals": (
                        home_profile.get("avg_home_goals_scored", 0) + away_profile.get("avg_away_goals_scored", 0)
                        if home_profile and away_profile else
                        sum(goal_history) / len(goal_history) if goal_history else 0
                    ),
                    "tempo": tempo_profile,
                    "h2h_available": bundle.h2h_count > 0,
                },
                # Phase 2: Market regime
                "market_regime":                  market_regime,
                "recommended_market_direction":   _chaos_dir,
                # Phase 4: Over Intelligence Engine
                "offensive_profile": over_intelligence,
                "defensive_profile": {
                    "under_1_5_rate":        round(_u15 * 100, 1),
                    "avg_goals":             round(_avg_g, 2),
                    "chaos_type":            _chaos_type,
                    "recommended_direction": _chaos_dir,
                },
                # Phase 5: Smart market ranking
                "best_market":           best_market,
                "secondary_market":      secondary_market,
                "best_over_market":      best_over_market,
                "best_under_market":     best_under_market,
                "avoid_markets":         list(set(avoid_markets)),
                "recommended_playstyle": recommended_playstyle,
                # Phase 5b: Market generation stats
                "market_generation_stats":     market_generation_stats,
                "rejection_reasons_by_market": _rejection_reasons,
                # Bettable Universe
                "market_access":           _universe["market_access"],
                "bettable_priority_score": _universe["bettable_priority_score"],
                "odds_coverage_score":     _universe["odds_coverage_score"],
                "market_liquidity_score":  _universe["market_liquidity_score"],
                "bettable_tier":           _universe["bettable_tier"],
                # Legacy fields
                "signals": signals_with_value,
                "best_edges": best_edges,
                "edge_detection": edge_results,
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
            logger.error(f"[ANALYSIS] Error analyzing match: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ==========================================
    # PHASE 7: TIER ENGINE
    # ==========================================

    def _compute_tier_level(
        self,
        ev_opportunities: list,
        best_ev,
        signals: list,
        sample_size: int,
        variance_score: float,
        has_odds: bool,
        refuse_pick: bool = False,
        tier_downgrade: bool = False,
        ranking_penalty: float = 0.0,
    ):
        """
        Phase 7: Classify match into S-TIER / A-TIER / WATCHLIST / NO_VALUE / LIVE_ONLY

        S-TIER:    EV >= 15% + edge >= 10% + confidence HIGH + variance low + sample >= 10
        A-TIER:    EV >= 5%  + edge >= 4%  + confidence >= MEDIUM
        WATCHLIST: Stat interest but no odds OR confidence LOW
        NO_VALUE:  Stats OK but bookmaker already adjusted
        LIVE_ONLY: Only viable in live context
        """
        ranking_score = 0.0

        # STEP 2/3: Refuse pick si volatilité ou false signal critique
        if refuse_pick:
            return "NO_VALUE", 0.0

        if not signals:
            return "NO_VALUE", 0.0

        best_signal = max(signals, key=lambda s: s.confidence)
        best_confidence = best_signal.confidence
        best_sample = best_signal.sample_size if hasattr(best_signal, 'sample_size') else sample_size

        # Compute signal quality score (0-1)
        signal_score = min(1.0, best_confidence)
        sample_ok = best_sample >= 10
        sample_good = best_sample >= 20
        low_variance = variance_score < 0.4

        # No odds available → WATCHLIST or NO_VALUE based on signal strength
        if not has_odds:
            if signal_score >= 0.75 and sample_ok:
                ranking_score = signal_score * 0.6 + (0.1 if sample_good else 0.0)
                return "WATCHLIST", round(ranking_score, 3)
            elif signal_score >= 0.60:
                ranking_score = signal_score * 0.4
                return "WATCHLIST", round(ranking_score, 3)
            else:
                return "NO_VALUE", 0.0

        # Odds available → use EV
        if not best_ev:
            if signal_score >= 0.70 and sample_ok:
                return "WATCHLIST", round(signal_score * 0.5, 3)
            return "NO_VALUE", 0.0

        ev_pct = best_ev.expected_value_percent
        edge_pct = best_ev.edge_percent
        ev_confidence = best_ev.confidence
        value_level = best_ev.value_level

        def _apply_penalties(tier: str, score: float) -> tuple:
            """Apply tier_downgrade and ranking_penalty."""
            final_score = max(0.0, score - ranking_penalty)
            if tier_downgrade:
                downgrade_map = {
                    "S_TIER": "A_TIER",
                    "A_TIER": "WATCHLIST",
                    "WATCHLIST": "NO_VALUE",
                    "NO_VALUE": "NO_VALUE",
                }
                tier = downgrade_map.get(tier, tier)
            return tier, round(final_score, 3)

        # S-TIER: exceptional value
        if (ev_pct >= 15.0 and
                edge_pct >= 10.0 and
                ev_confidence == "HIGH" and
                low_variance and
                sample_ok and
                value_level in ("HIGH", "EXTREME")):
            ranking_score = (
                min(ev_pct / 30.0, 1.0) * 0.40 +
                min(edge_pct / 20.0, 1.0) * 0.30 +
                signal_score * 0.20 +
                (0.10 if sample_good else 0.05)
            )
            return _apply_penalties("S_TIER", ranking_score)

        # A-TIER: good value
        if (ev_pct >= 5.0 and
                edge_pct >= 4.0 and
                ev_confidence in ("MEDIUM", "HIGH") and
                sample_ok):
            ranking_score = (
                min(ev_pct / 20.0, 1.0) * 0.35 +
                min(edge_pct / 15.0, 1.0) * 0.30 +
                signal_score * 0.25 +
                (0.10 if sample_good else 0.05)
            )
            return _apply_penalties("A_TIER", ranking_score)

        # WATCHLIST: EV present but not compelling enough
        if ev_pct > 0 and edge_pct > 0:
            ranking_score = min(ev_pct / 15.0, 0.6) * 0.5 + signal_score * 0.3
            return _apply_penalties("WATCHLIST", ranking_score)

        # NO_VALUE: bookmaker has priced it correctly
        return "NO_VALUE", round(signal_score * 0.2, 3)

    # ==========================================
    # PHASE 7b: STATISTICAL TIER (no odds needed)
    # ==========================================

    def _compute_statistical_tier(
        self,
        confidence_score: float,
        volatility_score: float,
        false_signal_score: float,
        league_reliability: float,
        sample_size: int,
        refuse_pick: bool = False,
        tier_downgrade: bool = False,
        ranking_penalty: float = 0.0,
    ) -> tuple:
        """
        Statistical tier based purely on model quality — NO odds required.

        Hierarchy: S_TIER > A_TIER > B_TIER > WATCHLIST > NO_VALUE

        S_TIER:    conf >= 72 + vol < 35 + fss < 30 + reliability >= 50 + sample >= 10
        A_TIER:    conf >= 55 + vol < 60 + fss < 50 + sample >= 6
        B_TIER:    conf >= 40 + fss < 65 + sample >= 4
        WATCHLIST: conf >= 22 + sample >= 2
        NO_VALUE:  below threshold or refuse_pick
        """
        if refuse_pick:
            return "NO_VALUE", 0.0

        if sample_size < 2 or confidence_score < 15:
            return "NO_VALUE", 0.0

        # Normalize inputs to 0-1
        conf_n   = min(confidence_score / 100.0, 1.0)
        vol_n    = min(volatility_score / 100.0, 1.0)
        fss_n    = min(false_signal_score / 100.0, 1.0)
        rel_n    = min(league_reliability / 100.0, 1.0)
        samp_n   = min(sample_size / 20.0, 1.0)

        # Composite statistical ranking score
        stat_score = (
            conf_n    * 0.45 +
            rel_n     * 0.20 +
            samp_n    * 0.20 +
            (1 - vol_n) * 0.075 +
            (1 - fss_n) * 0.075
        ) - ranking_penalty

        stat_score = max(0.0, min(1.0, stat_score))

        def _downgrade(tier: str) -> str:
            if not tier_downgrade:
                return tier
            return {"S_TIER": "A_TIER", "A_TIER": "B_TIER",
                    "B_TIER": "WATCHLIST", "WATCHLIST": "NO_VALUE"}.get(tier, tier)

        # S_TIER
        if (confidence_score >= 72 and
                volatility_score < 35 and
                false_signal_score < 30 and
                league_reliability >= 50 and
                sample_size >= 10):
            return _downgrade("S_TIER"), round(stat_score, 3)

        # A_TIER
        if (confidence_score >= 55 and
                volatility_score < 60 and
                false_signal_score < 50 and
                sample_size >= 6):
            return _downgrade("A_TIER"), round(stat_score, 3)

        # B_TIER
        if (confidence_score >= 40 and
                false_signal_score < 65 and
                sample_size >= 4):
            return _downgrade("B_TIER"), round(stat_score, 3)

        # WATCHLIST
        if confidence_score >= 22 and sample_size >= 2:
            return "WATCHLIST", round(stat_score, 3)

        return "NO_VALUE", 0.0

    # ==========================================
    # PHASE 3: MÉTHODES DE PROJECTIONS PRÉ-MATCH
    # ==========================================
    
    def _calculate_home_profile(self, home_history, ht_history):
        """Calcule le profil statistique HOME"""
        if not home_history:
            return {}
        
        # Buts marqués/concédés
        home_goals_scored = []
        home_goals_conceded = []
        ht_goals_scored = []
        ht_goals_conceded = []
        
        for match in home_history:
            if hasattr(match, 'home_goals') and hasattr(match, 'away_goals'):
                home_goals_scored.append(match.home_goals)
                home_goals_conceded.append(match.away_goals)
                
                # HT goals si disponibles
                if hasattr(match, 'home_ht_goals') and hasattr(match, 'away_ht_goals'):
                    ht_goals_scored.append(match.home_ht_goals)
                    ht_goals_conceded.append(match.away_ht_goals)
        
        profile = {
            'avg_home_goals_scored': sum(home_goals_scored) / len(home_goals_scored) if home_goals_scored else 0,
            'avg_home_goals_conceded': sum(home_goals_conceded) / len(home_goals_conceded) if home_goals_conceded else 0,
            'avg_home_ht_goals': sum(ht_goals_scored) / len(ht_goals_scored) if ht_goals_scored else 0,
            'avg_home_ht_conceded': sum(ht_goals_conceded) / len(ht_goals_conceded) if ht_goals_conceded else 0,
            'sample_size': len(home_history)
        }
        
        # Calculer les taux
        total_matches = len(home_goals_scored)
        if total_matches > 0:
            profile['clean_sheet_rate'] = len([g for g in home_goals_conceded if g == 0]) / total_matches
            profile['btts_rate'] = len([i for i in range(total_matches) if home_goals_scored[i] > 0 and home_goals_conceded[i] > 0]) / total_matches
            profile['over_1_5_rate'] = len([i for i in range(total_matches) if home_goals_scored[i] + home_goals_conceded[i] > 1.5]) / total_matches
            profile['over_2_5_rate'] = len([i for i in range(total_matches) if home_goals_scored[i] + home_goals_conceded[i] > 2.5]) / total_matches
            profile['under_2_5_rate'] = len([i for i in range(total_matches) if home_goals_scored[i] + home_goals_conceded[i] < 2.5]) / total_matches
            profile['first_goal_frequency'] = len([i for i in range(total_matches) if ht_goals_scored[i] > 0]) / total_matches if ht_goals_scored else 0
            profile['second_half_goals_rate'] = len([i for i in range(total_matches) if (home_goals_scored[i] + home_goals_conceded[i]) - (ht_goals_scored[i] + ht_goals_conceded[i]) > 0]) / total_matches if ht_goals_scored else 0
        
        return profile
    
    def _calculate_away_profile(self, away_history, ht_history):
        """Calcule le profil statistique AWAY"""
        if not away_history:
            return {}
        
        # Buts marqués/concédés
        away_goals_scored = []
        away_goals_conceded = []
        ht_goals_scored = []
        ht_goals_conceded = []
        
        for match in away_history:
            if hasattr(match, 'away_goals') and hasattr(match, 'home_goals'):
                away_goals_scored.append(match.away_goals)
                away_goals_conceded.append(match.home_goals)
                
                # HT goals si disponibles
                if hasattr(match, 'away_ht_goals') and hasattr(match, 'home_ht_goals'):
                    ht_goals_scored.append(match.away_ht_goals)
                    ht_goals_conceded.append(match.home_ht_goals)
        
        profile = {
            'avg_away_goals_scored': sum(away_goals_scored) / len(away_goals_scored) if away_goals_scored else 0,
            'avg_away_goals_conceded': sum(away_goals_conceded) / len(away_goals_conceded) if away_goals_conceded else 0,
            'avg_away_ht_goals': sum(ht_goals_scored) / len(ht_goals_scored) if ht_goals_scored else 0,
            'avg_away_ht_conceded': sum(ht_goals_conceded) / len(ht_goals_conceded) if ht_goals_conceded else 0,
            'sample_size': len(away_history)
        }
        
        # Calculer les taux
        total_matches = len(away_goals_scored)
        if total_matches > 0:
            profile['away_clean_sheet_rate'] = len([g for g in away_goals_conceded if g == 0]) / total_matches
            profile['away_btts_rate'] = len([i for i in range(total_matches) if away_goals_scored[i] > 0 and away_goals_conceded[i] > 0]) / total_matches
            profile['away_over_rate'] = len([i for i in range(total_matches) if away_goals_scored[i] + away_goals_conceded[i] > 2.5]) / total_matches
            profile['away_under_rate'] = len([i for i in range(total_matches) if away_goals_scored[i] + away_goals_conceded[i] < 2.5]) / total_matches
        
        return profile
    
    def _calculate_h2h_profile(self, h2h_history):
        """Calcule le profil H2H"""
        if not h2h_history:
            return {}
        
        total_goals = []
        ht_goals = []
        
        for match in h2h_history:
            if hasattr(match, 'home_goals') and hasattr(match, 'away_goals'):
                total_goals.append(match.home_goals + match.away_goals)
                
                if hasattr(match, 'home_ht_goals') and hasattr(match, 'away_ht_goals'):
                    ht_goals.append(match.home_ht_goals + match.away_ht_goals)
        
        profile = {
            'avg_h2h_goals': sum(total_goals) / len(total_goals) if total_goals else 0,
            'avg_h2h_ht_goals': sum(ht_goals) / len(ht_goals) if ht_goals else 0,
            'sample_size': len(h2h_history)
        }
        
        # Calculer les taux H2H
        total_matches = len(total_goals)
        if total_matches > 0:
            profile['h2h_btts_rate'] = len([g for g in total_goals if g > 0]) / total_matches  # Simplifié
            profile['h2h_under_rate'] = len([g for g in total_goals if g < 2.5]) / total_matches
            profile['h2h_over_rate'] = len([g for g in total_goals if g > 2.5]) / total_matches
        
        return profile
    
    def _calculate_tempo_profile(self, goal_history, home_profile, away_profile):
        """Détermine le profil de tempo"""
        if not goal_history or not home_profile or not away_profile:
            return "UNKNOWN"
        
        # Calculer la moyenne de buts par match
        avg_goals = sum(goal_history) / len(goal_history)
        
        # Calculer les buts HT en moyenne
        home_ht_avg = home_profile.get('avg_home_ht_goals', 0)
        away_ht_avg = away_profile.get('avg_away_ht_goals', 0)
        ht_avg = (home_ht_avg + away_ht_avg) / 2
        
        # Déterminer le tempo
        if avg_goals < 1.8 and ht_avg < 0.8:
            return "LOW_TEMPO"
        elif avg_goals > 3.2 and ht_avg > 1.5:
            return "HIGH_TEMPO"
        elif avg_goals > 2.8:
            return "OPEN_GAME"
        elif home_profile.get('clean_sheet_rate', 0) > 0.4 and away_profile.get('away_clean_sheet_rate', 0) > 0.4:
            return "DEFENSIVE"
        elif abs(home_profile.get('avg_home_goals_scored', 0) - away_profile.get('avg_away_goals_conceded', 0)) > 1.5:
            return "ASYMMETRIC"
        else:
            return "BALANCED_TEMPO"
    
    def _calculate_volatility_profile(self, goal_history, home_profile, away_profile):
        """Calcule le profil de volatilité"""
        if not goal_history or len(goal_history) < 3:
            return {"variance": 0, "stability": 0, "consistency": 0}
        
        # Calculer la variance des buts
        avg_goals = sum(goal_history) / len(goal_history)
        variance = sum((g - avg_goals) ** 2 for g in goal_history) / len(goal_history)
        
        # Calculer l'indice de stabilité (inverse de la variance normalisée)
        max_possible_variance = 4.0  # Variance maximale raisonnable
        stability = max(0, 100 * (1 - variance / max_possible_variance))
        
        # Calculer le score de consistance (basé sur la régularité des buts)
        consistency = 100 - (variance * 25)  # Plus la variance est faible, plus c'est consistant
        consistency = max(0, min(100, consistency))
        
        return {
            "variance": variance,
            "stability_index": stability,
            "consistency_score": consistency
        }
    
    def _generate_pre_match_projections(self, home_profile, away_profile, h2h_profile, tempo_profile, volatility_profile):
        """Génère les projections pré-match"""
        projections = []
        
        # Données de base
        home_avg_scored = home_profile.get('avg_home_goals_scored', 0)
        home_avg_conceded = home_profile.get('avg_home_goals_conceded', 0)
        away_avg_scored = away_profile.get('avg_away_goals_scored', 0)
        away_avg_conceded = away_profile.get('avg_away_goals_conceded', 0)
        
        # Projections HT
        home_ht_avg = home_profile.get('avg_home_ht_goals', 0)
        away_ht_avg = away_profile.get('avg_away_ht_goals', 0)
        home_ht_conceded = home_profile.get('avg_home_ht_conceded', 0)
        away_ht_conceded = away_profile.get('avg_away_ht_conceded', 0)
        
        # HT UNDER 0.5
        ht_under_05_prob = self._calculate_probability((home_ht_avg + away_ht_conceded) < 0.5, volatility_profile)
        if ht_under_05_prob > 0.7:
            projections.append({
                "market": "HT_UNDER_0_5",
                "probability": ht_under_05_prob,
                "confidence": min(95, ht_under_05_prob * 100 + (volatility_profile.get("consistency_score", 0) * 0.2)),
                "reasoning": f"HT avg: {(home_ht_avg + away_ht_conceded):.2f}, tempo: {tempo_profile}"
            })
        
        # HT UNDER 1.5
        ht_under_15_prob = self._calculate_probability((home_ht_avg + away_ht_conceded) < 1.5, volatility_profile)
        if ht_under_15_prob > 0.65:
            projections.append({
                "market": "HT_UNDER_1_5",
                "probability": ht_under_15_prob,
                "confidence": min(95, ht_under_15_prob * 100 + (volatility_profile.get("consistency_score", 0) * 0.2)),
                "reasoning": f"HT avg: {(home_ht_avg + away_ht_conceded):.2f}, consistency: {volatility_profile.get('consistency_score', 0):.1f}"
            })
        
        # FT UNDER 2.5
        expected_home_goals = (home_avg_scored + away_avg_conceded) / 2
        expected_away_goals = (away_avg_scored + home_avg_conceded) / 2
        expected_total = expected_home_goals + expected_away_goals
        
        if expected_total < 2.8:
            under_25_prob = self._calculate_probability(expected_total < 2.5, volatility_profile)
            if under_25_prob > 0.65:
                projections.append({
                    "market": "FT_UNDER_2_5",
                    "probability": under_25_prob,
                    "confidence": min(95, under_25_prob * 100 + (volatility_profile.get("consistency_score", 0) * 0.2)),
                    "reasoning": f"Expected total: {expected_total:.2f}, home: {expected_home_goals:.2f}, away: {expected_away_goals:.2f}"
                })
        
        # BTTS YES
        btts_yes_prob = (home_profile.get('btts_rate', 0) + away_profile.get('away_btts_rate', 0)) / 2
        if btts_yes_prob > 0.6:
            projections.append({
                "market": "BTTS_YES",
                "probability": btts_yes_prob,
                "confidence": min(95, btts_yes_prob * 100 + (volatility_profile.get("consistency_score", 0) * 0.2)),
                "reasoning": f"Home BTTS: {home_profile.get('btts_rate', 0):.2f}, Away BTTS: {away_profile.get('away_btts_rate', 0):.2f}"
            })
        
        return projections
    
    def _calculate_probability(self, condition_met, volatility_profile):
        """Calcule une probabilité basée sur les données historiques et la volatilité"""
        base_prob = 0.5  # Base 50%
        
        # Ajuster selon la condition (simplifié)
        if condition_met:
            base_prob = 0.75
        else:
            base_prob = 0.25
        
        # Ajuster selon la consistance
        consistency = volatility_profile.get("consistency_score", 50) / 100
        adjusted_prob = base_prob * (0.5 + consistency * 0.5)
        
        return max(0.1, min(0.95, adjusted_prob))
    
    def _calculate_confidence_scores(self, home_profile, away_profile, h2h_profile, goal_history):
        """Calcule les scores de confiance"""
        scores = {}
        
        # Taille d'échantillon
        home_sample = home_profile.get('sample_size', 0)
        away_sample = away_profile.get('sample_size', 0)
        total_sample = len(goal_history)
        
        # Score basé sur la taille d'échantillon
        sample_score = min(100, (total_sample / 20) * 100)  # 20 matches = 100%
        
        # Score basé sur la consistance des données
        if len(goal_history) >= 3:
            variance = sum((g - sum(goal_history)/len(goal_history)) ** 2 for g in goal_history) / len(goal_history)
            consistency_score = max(0, 100 - variance * 20)
        else:
            consistency_score = 30
        
        # Score basé sur la qualité des profils
        profile_quality = 0
        if home_sample >= 5 and away_sample >= 5:
            profile_quality += 40
        if h2h_profile and h2h_profile.get('sample_size', 0) >= 3:
            profile_quality += 30
        if home_profile.get('clean_sheet_rate', 0) > 0.3:
            profile_quality += 15
        if away_profile.get('away_clean_sheet_rate', 0) > 0.3:
            profile_quality += 15
        
        # Score global
        overall_confidence = (sample_score * 0.4 + consistency_score * 0.3 + profile_quality * 0.3)
        
        scores = {
            'sample_score': sample_score,
            'consistency_score': consistency_score,
            'profile_quality_score': profile_quality,
            'overall': overall_confidence
        }
        
        return scores
    
    def _calculate_tier(self, confidence_scores, projections, volatility_profile):
        """Détermine le tier (S/A/B/Weak)"""
        overall_confidence = confidence_scores.get('overall', 0)
        consistency = volatility_profile.get('consistency_score', 0)
        projection_count = len(projections)
        
        # S-TIER: Très haute confiance + consistance + projections multiples
        if (overall_confidence >= 90 and 
            consistency >= 80 and 
            projection_count >= 3 and
            any(p.get('confidence', 0) >= 85 for p in projections)):
            return "S-TIER"
        
        # A-TIER: Bonne confiance + consistance
        elif (overall_confidence >= 75 and 
              consistency >= 60 and 
              projection_count >= 2):
            return "A-TIER"
        
        # B-TIER: Confiance modérée
        elif (overall_confidence >= 50 and 
              consistency >= 40 and 
              projection_count >= 1):
            return "B-TIER"
        
        # WEAK: Faible confiance
        else:
            return "WEAK"
    
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
        
        # Add live score fields if available
        if hasattr(match, 'score_fulltime') and match.score_fulltime:
            match_data["home_score"] = match.score_fulltime.home
            match_data["away_score"] = match.score_fulltime.away
        else:
            match_data["home_score"] = None
            match_data["away_score"] = None
            
        if hasattr(match, 'score_halftime') and match.score_halftime:
            match_data["ht_home_score"] = match.score_halftime.home
            match_data["ht_away_score"] = match.score_halftime.away
        else:
            match_data["ht_home_score"] = None
            match_data["ht_away_score"] = None
        
        # Add minute/elapsed info
        match_data["minute"] = getattr(match, 'elapsed', None) or getattr(match, 'elapsed_minutes', None)
        match_data["elapsed"] = match_data["minute"]
        
        # Add status details
        if hasattr(match, 'status'):
            match_data["status_short"] = match.status.value if hasattr(match.status, 'value') else str(match.status)
            match_data["status_long"] = match_data["status_short"]
        else:
            match_data["status_short"] = None
            match_data["status_long"] = None
        
        # Add status classification
        status_info = MatchStatusHelper.get_display_info(match_data)
        match_data.update(status_info)
        
        return match_data
