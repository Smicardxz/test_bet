"""
SofaScore Data Provider
Extracts data from SofaScore public API

IMPORTANT: This provider uses SofaScore's public API.
- Respect rate limits
- Cache aggressively
- For production, consider official API access
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import requests
import time
from app.providers.base_provider import BaseDataProvider, ProviderConfig, ProviderResponse
from app.providers.models import (
    MatchDetails,
    TeamInfo,
    CompetitionInfo,
    MatchScore,
    MatchStatus,
    TeamStats,
    HeadToHead,
    MatchOdds
)


class SofaScoreProvider(BaseDataProvider):
    """
    SofaScore data provider
    
    Uses SofaScore's public API endpoints.
    Implements aggressive caching and rate limiting.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        """Initialize SofaScore provider"""
        
        if config is None:
            config = ProviderConfig(
                name="sofascore",
                base_url="https://api.sofascore.com/api/v1",
                rate_limit_per_minute=30,  # Conservative limit
                timeout_seconds=15,
                retry_attempts=3,
                cache_enabled=True,
                cache_ttl_seconds=300  # 5 minutes
            )
        
        super().__init__(config)
        
        self.base_url = config.base_url or "https://api.sofascore.com/api/v1"
        
        # Setup session with realistic headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/"
        })
        
        # Obscure league keywords for filtering
        self.obscure_keywords = [
            "women", "u21", "u19", "u18", "u23", "reserve",
            "national league", "regional", "championship",
            "division 3", "division 4", "division 5",
            "national 3", "national 2"
        ]
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make HTTP request to SofaScore API"""
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"GET {url}")
        
        def _request():
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        
        return self._retry_request(_request)
    
    def _safe_get(self, data: dict, *keys, default=None):
        """Safely get nested dict values"""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, {})
            else:
                return default
        return data if data != {} else default
    
    def _parse_timestamp(self, timestamp: Optional[int]) -> datetime:
        """Parse Unix timestamp to datetime"""
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return datetime.utcnow()
    
    def _is_obscure_competition(self, tournament_data: dict) -> bool:
        """Determine if competition is obscure"""
        name = tournament_data.get("name", "").lower()
        category = self._safe_get(tournament_data, "category", "name", default="").lower()
        
        # Check tier
        tier = tournament_data.get("tier")
        if tier and tier >= 3:
            return True
        
        # Check keywords
        full_text = f"{name} {category}"
        return any(keyword in full_text for keyword in self.obscure_keywords)
    
    def _map_match_status(self, status_data: dict) -> MatchStatus:
        """Map SofaScore status to our MatchStatus"""
        status_type = status_data.get("type", "").lower()
        
        status_map = {
            "notstarted": MatchStatus.SCHEDULED,
            "inprogress": MatchStatus.LIVE,
            "finished": MatchStatus.FINISHED,
            "postponed": MatchStatus.POSTPONED,
            "cancelled": MatchStatus.CANCELLED,
            "abandoned": MatchStatus.CANCELLED
        }
        
        return status_map.get(status_type, MatchStatus.SCHEDULED)
    
    def _map_to_match_details(self, event_data: dict) -> MatchDetails:
        """Map SofaScore event data to MatchDetails"""
        
        # Extract teams
        home_team = TeamInfo(
            id=str(self._safe_get(event_data, "homeTeam", "id", default="")),
            name=self._safe_get(event_data, "homeTeam", "name", default="Unknown"),
            short_name=self._safe_get(event_data, "homeTeam", "shortName"),
            country=self._safe_get(event_data, "homeTeam", "country", "name")
        )
        
        away_team = TeamInfo(
            id=str(self._safe_get(event_data, "awayTeam", "id", default="")),
            name=self._safe_get(event_data, "awayTeam", "name", default="Unknown"),
            short_name=self._safe_get(event_data, "awayTeam", "shortName"),
            country=self._safe_get(event_data, "awayTeam", "country", "name")
        )
        
        # Extract competition
        tournament = event_data.get("tournament", {})
        competition = CompetitionInfo(
            id=str(tournament.get("id", "")),
            name=tournament.get("name", "Unknown"),
            country=self._safe_get(tournament, "category", "name"),
            tier=tournament.get("tier"),
            is_obscure=self._is_obscure_competition(tournament)
        )
        
        # Extract scores
        score_ft = None
        score_ht = None
        
        home_score = event_data.get("homeScore", {})
        away_score = event_data.get("awayScore", {})
        
        if home_score and away_score:
            # Full time score
            if "current" in home_score:
                score_ft = MatchScore(
                    home=home_score.get("current", 0),
                    away=away_score.get("current", 0)
                )
            
            # Half time score
            if "period1" in home_score:
                score_ht = MatchScore(
                    home=home_score.get("period1", 0),
                    away=away_score.get("period1", 0)
                )
        
        # Map status
        status = self._map_match_status(event_data.get("status", {}))
        
        return MatchDetails(
            id=str(event_data.get("id", "")),
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=self._parse_timestamp(event_data.get("startTimestamp")),
            status=status,
            score_fulltime=score_ft,
            score_halftime=score_ht,
            venue=self._safe_get(event_data, "venue", "stadium", "name"),
            provider="sofascore",
            provider_url=f"https://www.sofascore.com/match/{event_data.get('id', '')}"
        )
    
    # =========================================================================
    # IMPLEMENT ABSTRACT METHODS
    # =========================================================================
    
    def get_today_matches(
        self,
        competition_ids: Optional[List[str]] = None
    ) -> ProviderResponse:
        """Get today's matches from SofaScore"""
        
        self.logger.info("Fetching today's matches from SofaScore")
        
        # Check cache
        cache_key = self._get_cache_key("today_matches", competition_ids=competition_ids)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            # Get today's date
            today = date.today().strftime("%Y-%m-%d")
            
            # SofaScore endpoint for scheduled events
            endpoint = f"/sport/football/scheduled-events/{today}"
            data = self._make_request(endpoint)
            
            # Map to our models
            matches = []
            for event in data.get("events", []):
                try:
                    match = self._map_to_match_details(event)
                    
                    # Filter by competition if specified
                    if competition_ids and match.competition.id not in competition_ids:
                        continue
                    
                    # Only include obscure competitions
                    if not match.competition.is_obscure:
                        continue
                    
                    matches.append(match)
                
                except Exception as e:
                    self.logger.warning(f"Error mapping match {event.get('id')}: {e}")
                    continue
            
            self.logger.info(f"Found {len(matches)} obscure matches")
            
            response = self._create_success_response(matches)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error fetching today's matches: {e}")
            return self._create_error_response(str(e))
    
    def get_match_details(self, match_id: str) -> ProviderResponse:
        """Get match details from SofaScore"""
        
        self.logger.info(f"Fetching match details for {match_id}")
        
        # Check cache
        cache_key = self._get_cache_key("match_details", match_id=match_id)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            endpoint = f"/event/{match_id}"
            data = self._make_request(endpoint)
            
            match = self._map_to_match_details(data.get("event", {}))
            
            response = self._create_success_response(match)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error fetching match details: {e}")
            return self._create_error_response(str(e))
    
    def get_team_recent_matches(
        self,
        team_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get team recent matches from SofaScore"""
        
        self.logger.info(f"Fetching recent matches for team {team_id}")
        
        # Check cache
        cache_key = self._get_cache_key("team_recent", team_id=team_id, limit=limit)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            endpoint = f"/team/{team_id}/events/last/{limit}"
            data = self._make_request(endpoint)
            
            matches = []
            for event in data.get("events", []):
                try:
                    match = self._map_to_match_details(event)
                    matches.append(match)
                except Exception as e:
                    self.logger.warning(f"Error mapping match: {e}")
                    continue
            
            response = self._create_success_response(matches)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error fetching team recent matches: {e}")
            return self._create_error_response(str(e))
    
    def get_head_to_head(
        self,
        team_a_id: str,
        team_b_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get head-to-head from SofaScore"""
        
        self.logger.info(f"Fetching H2H for {team_a_id} vs {team_b_id}")
        
        # Check cache
        cache_key = self._get_cache_key("h2h", team_a_id=team_a_id, team_b_id=team_b_id)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            endpoint = f"/team/{team_a_id}/team/{team_b_id}/h2h/events"
            data = self._make_request(endpoint)
            
            # Extract H2H stats
            events = data.get("events", [])
            
            team_a_wins = 0
            team_b_wins = 0
            draws = 0
            recent_matches = []
            
            for event in events[:limit]:
                try:
                    match = self._map_to_match_details(event)
                    recent_matches.append(match)
                    
                    # Count results
                    if match.score_fulltime:
                        if match.score_fulltime.home > match.score_fulltime.away:
                            if match.home_team.id == team_a_id:
                                team_a_wins += 1
                            else:
                                team_b_wins += 1
                        elif match.score_fulltime.home < match.score_fulltime.away:
                            if match.away_team.id == team_a_id:
                                team_a_wins += 1
                            else:
                                team_b_wins += 1
                        else:
                            draws += 1
                
                except Exception as e:
                    self.logger.warning(f"Error mapping H2H match: {e}")
                    continue
            
            h2h = HeadToHead(
                team_a=TeamInfo(id=team_a_id, name="Team A"),
                team_b=TeamInfo(id=team_b_id, name="Team B"),
                total_matches=len(recent_matches),
                team_a_wins=team_a_wins,
                team_b_wins=team_b_wins,
                draws=draws,
                recent_matches=recent_matches,
                provider="sofascore"
            )
            
            response = self._create_success_response(h2h)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error fetching H2H: {e}")
            return self._create_error_response(str(e))
    
    def get_competition_matches(
        self,
        competition_id: str,
        match_date: Optional[date] = None
    ) -> ProviderResponse:
        """Get competition matches from SofaScore"""
        
        self.logger.info(f"Fetching matches for competition {competition_id}")
        
        # Check cache
        cache_key = self._get_cache_key(
            "competition_matches",
            competition_id=competition_id,
            match_date=match_date
        )
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            # Build endpoint
            if match_date:
                date_str = match_date.strftime("%Y-%m-%d")
                endpoint = f"/unique-tournament/{competition_id}/events/{date_str}"
            else:
                endpoint = f"/unique-tournament/{competition_id}/events/next/0"
            
            data = self._make_request(endpoint)
            
            matches = []
            for event in data.get("events", []):
                try:
                    match = self._map_to_match_details(event)
                    matches.append(match)
                except Exception as e:
                    self.logger.warning(f"Error mapping match: {e}")
                    continue
            
            response = self._create_success_response(matches)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error fetching competition matches: {e}")
            return self._create_error_response(str(e))
    
    def get_odds(self, match_id: str) -> ProviderResponse:
        """
        Get odds from SofaScore
        
        NOTE: SofaScore may not provide comprehensive odds.
        This is a best-effort implementation.
        """
        
        self.logger.info(f"Fetching odds for match {match_id}")
        
        # Check cache
        cache_key = self._get_cache_key("odds", match_id=match_id)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return ProviderResponse(**cached)
        
        try:
            endpoint = f"/event/{match_id}/odds/1/all"
            data = self._make_request(endpoint)
            
            odds_list = []
            
            # Parse odds data (structure may vary)
            # This is a simplified implementation
            for market in data.get("markets", []):
                try:
                    market_name = market.get("marketName", "")
                    
                    # Extract odds based on market type
                    # This would need to be expanded based on actual API structure
                    
                    odds = MatchOdds(
                        bookmaker="SofaScore",
                        market_type=market_name.lower().replace(" ", "_"),
                        timestamp=datetime.utcnow()
                    )
                    
                    odds_list.append(odds)
                
                except Exception as e:
                    self.logger.warning(f"Error parsing odds market: {e}")
                    continue
            
            if not odds_list:
                return self._create_error_response("No odds available for this match")
            
            response = self._create_success_response(odds_list)
            self._save_to_cache(cache_key, response.dict())
            
            return response
        
        except Exception as e:
            self.logger.warning(f"Odds not available: {e}")
            return self._create_error_response(f"Odds not available: {str(e)}")
