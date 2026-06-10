"""
API-Football Provider
Uses API-Football / API-Sports for real match data

Documentation: https://www.api-football.com/documentation-v3
"""

import os
import logging
import requests
import json
import time
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path

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

logger = logging.getLogger(__name__)


def safe_get_status_short(status) -> str:
    """
    Safely extract status short code from various formats
    
    Args:
        status: Can be MatchStatus enum, dict, object with .short, or string
        
    Returns:
        Status short code (e.g., "FT", "NS", "LIVE") or "UNK" if unknown
    """
    if status is None:
        return "UNK"
    
    # If it's already a string (MatchStatus enum value)
    if isinstance(status, str):
        # Map common values
        status_upper = status.upper()
        if status_upper in ["FT", "AET", "PEN", "NS", "TBD", "LIVE", "1H", "2H", "HT"]:
            return status_upper
        if status == "finished":
            return "FT"
        if status == "scheduled":
            return "NS"
        if status == "live":
            return "LIVE"
        return status_upper[:3]  # Fallback: first 3 chars
    
    # If it's a dict
    if isinstance(status, dict):
        return status.get("short", status.get("code", "UNK"))
    
    # If it's an object with .short attribute
    if hasattr(status, "short"):
        return str(status.short)
    
    # If it's an object with .value attribute (enum)
    if hasattr(status, "value"):
        return safe_get_status_short(status.value)
    
    # Last resort: convert to string
    return str(status)[:3].upper()


class ApiFootballProvider(BaseDataProvider):
    """
    API-Football / API-Sports provider
    
    Provides real match data, odds, and statistics from API-Football.
    Requires valid API key.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        """Initialize API-Football provider"""
        
        # Get API key from environment
        api_key = os.getenv("API_FOOTBALL_KEY", "")
        api_url = os.getenv("API_FOOTBALL_URL", "https://v3.football.api-sports.io")
        
        if not api_key:
            logger.error("API_FOOTBALL_KEY not found in environment variables")
            logger.error("Please set API_FOOTBALL_KEY in .env file or environment")
            logger.error("Example: API_FOOTBALL_KEY=your_key_here")
            raise ValueError(
                "API_FOOTBALL_KEY not found. "
                "Set it in .env file or use: $env:API_FOOTBALL_KEY='your_key'"
            )
        
        if config is None:
            config = ProviderConfig(
                name="api_football",
                base_url=api_url,
                rate_limit_per_minute=45,  # Raised: API-Football Basic = 300/min
                timeout_seconds=10,
                retry_attempts=2,
                cache_enabled=True,
                cache_ttl_seconds=3600  # 1-hour cache — team history stable within a day
            )
        
        super().__init__(config)
        
        self.api_key = api_key
        self.base_url = api_url
        
        # Setup session with API key
        self.session = requests.Session()
        self.session.headers.update({
            "x-apisports-key": self.api_key,
            "Accept": "application/json"
        })
        
        # Cache directory
        self.cache_dir = Path(".cache/api_football")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ApiFootballProvider initialized with URL: {self.base_url}")
    
    # =========================================================================
    # CORE API METHODS
    # =========================================================================
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to API-Football (with disk cache)"""
        # Build cache key from endpoint + params
        cache_key = self._get_cache_key(endpoint, **(params or {}))
        cached = self._get_from_cache(cache_key)
        if cached:
            self.logger.debug(f"[CACHE HIT] {endpoint} (age {cached.get('cache_age_seconds')}s)")
            return cached.get("response_data", {})

        # Miss → rate-limit then fetch
        self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        self.logger.debug(f"GET {url} with params {params}")

        def _request():
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            return response.json()

        data = self._retry_request(_request)
        self._save_to_cache(cache_key, {"response_data": data})
        return data
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and key validity
        
        Returns:
            Dict with connection status
        """
        try:
            # Test with status endpoint
            data = self._make_request("status")
            
            response_data = data.get("response", {})
            
            return {
                "success": True,
                "api_reachable": True,
                "key_valid": True,
                "account": response_data.get("account", {}),
                "requests": response_data.get("requests", {}),
                "subscription": response_data.get("subscription", {})
            }
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return {
                    "success": False,
                    "api_reachable": True,
                    "key_valid": False,
                    "error": "Invalid API key"
                }
            return {
                "success": False,
                "api_reachable": True,
                "key_valid": False,
                "error": str(e)
            }
        
        except Exception as e:
            return {
                "success": False,
                "api_reachable": False,
                "key_valid": False,
                "error": str(e)
            }
    
    def get_today_matches(self, competition_ids: Optional[List[str]] = None) -> ProviderResponse:
        """
        Get today's matches
        
        Args:
            competition_ids: Optional list of league IDs to filter
            
        Returns:
            ProviderResponse with list of MatchDetails
        """
        try:
            today = date.today().isoformat()
            
            params = {
                "date": today,
                "timezone": "UTC"
            }
            
            # Add league filter if provided
            if competition_ids:
                params["league"] = ",".join(competition_ids)
            
            data = self._make_request("fixtures", params)
            
            if not data.get("response"):
                return ProviderResponse(
                    success=True,
                    data=[],
                    error=None,
                    provider=self.config.name
                )
            
            matches = []
            for fixture in data["response"]:
                match = self._parse_fixture(fixture)
                if match:
                    matches.append(match)
            
            logger.info(f"Fetched {len(matches)} matches for {today}")
            
            return ProviderResponse(
                success=True,
                data=matches,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching today's matches: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_leagues(self) -> ProviderResponse:
        """
        Get all available leagues
        
        Returns:
            ProviderResponse with list of leagues
        """
        try:
            data = self._make_request("leagues")
            
            leagues = []
            for league_data in data.get("response", []):
                league = league_data.get("league", {})
                country = league_data.get("country", {})
                
                leagues.append({
                    "id": str(league.get("id", "")),
                    "name": league.get("name", ""),
                    "type": league.get("type", ""),
                    "country": country.get("name", ""),
                    "country_code": country.get("code", ""),
                    "logo": league.get("logo", "")
                })
            
            logger.info(f"Fetched {len(leagues)} leagues")
            
            return ProviderResponse(
                success=True,
                data=leagues,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching leagues: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_odds_for_fixture(self, fixture_id: str) -> ProviderResponse:
        """
        Get odds for a specific fixture
        
        Args:
            fixture_id: Fixture ID
            
        Returns:
            ProviderResponse with odds data
        """
        try:
            params = {"fixture": fixture_id}
            data = self._make_request("odds", params)
            
            if not data.get("response"):
                return ProviderResponse(
                    success=True,
                    data=[],
                    error="No odds available",
                    provider=self.config.name
                )
            
            odds_list = []
            for odds_data in data["response"]:
                bookmakers = odds_data.get("bookmakers", [])
                for bookmaker in bookmakers:
                    odds_list.append({
                        "bookmaker": bookmaker.get("name", ""),
                        "bets": bookmaker.get("bets", [])
                    })
            
            return ProviderResponse(
                success=True,
                data=odds_list,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching odds for fixture {fixture_id}: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_team_recent_matches(self, team_id: str, limit: int = 10) -> ProviderResponse:
        """
        Get recent matches for a team
        
        Args:
            team_id: Team ID
            limit: Number of matches to fetch
            
        Returns:
            ProviderResponse with list of MatchDetails
        """
        try:
            params = {
                "team": team_id,
                "last": limit
            }
            
            data = self._make_request("fixtures", params)
            
            matches = []
            for fixture in data.get("response", []):
                match = self._parse_fixture(fixture)
                if match:
                    matches.append(match)
            
            return ProviderResponse(
                success=True,
                data=matches,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching recent matches for team {team_id}: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_head_to_head(self, team_a_id: str, team_b_id: str, limit: int = 10) -> ProviderResponse:
        """
        Get head-to-head matches between two teams
        
        Args:
            team_a_id: Team A ID
            team_b_id: Team B ID
            limit: Maximum number of matches
            
        Returns:
            ProviderResponse with H2H data
        """
        try:
            params = {
                "h2h": f"{team_a_id}-{team_b_id}",
                "last": limit
            }
            
            data = self._make_request("fixtures/headtohead", params)
            
            matches = []
            for fixture in data.get("response", []):
                match = self._parse_fixture(fixture)
                if match:
                    matches.append(match)
            
            return ProviderResponse(
                success=True,
                data=matches,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching H2H: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_match_details(self, match_id: str) -> ProviderResponse:
        """
        Get detailed information for a specific match
        
        Args:
            match_id: Match/Fixture ID
            
        Returns:
            ProviderResponse with MatchDetails
        """
        try:
            params = {"id": match_id}
            data = self._make_request("fixtures", params)
            
            if not data.get("response"):
                return ProviderResponse(
                    success=False,
                    data=None,
                    error="Match not found",
                    provider=self.config.name
                )
            
            match = self._parse_fixture(data["response"][0])
            
            return ProviderResponse(
                success=True,
                data=match,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching match details: {e}")
            return ProviderResponse(
                success=False,
                data=None,
                error=str(e),
                provider=self.config.name
            )
    
    def get_competition_matches(
        self,
        competition_id: str,
        match_date: Optional[date] = None
    ) -> ProviderResponse:
        """
        Get matches for a specific competition
        
        Args:
            competition_id: League ID
            match_date: Optional date to filter
            
        Returns:
            ProviderResponse with list of MatchDetails
        """
        try:
            params = {"league": competition_id}
            
            if match_date:
                params["date"] = match_date.isoformat()
            else:
                params["season"] = datetime.now().year
            
            data = self._make_request("fixtures", params)
            
            matches = []
            for fixture in data.get("response", []):
                match = self._parse_fixture(fixture)
                if match:
                    matches.append(match)
            
            return ProviderResponse(
                success=True,
                data=matches,
                error=None,
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error fetching competition matches: {e}")
            return ProviderResponse(
                success=False,
                data=[],
                error=str(e),
                provider=self.config.name
            )
    
    def get_odds(self, match_id: str) -> ProviderResponse:
        """
        Get odds for a specific match
        
        Args:
            match_id: Match/Fixture ID
            
        Returns:
            ProviderResponse with odds data
        """
        return self.get_odds_for_fixture(match_id)
    
    # =========================================================================
    # PARSING METHODS
    # =========================================================================
    
    def _parse_fixture(self, fixture_data: Dict) -> Optional[MatchDetails]:
        """Parse fixture data into MatchDetails"""
        try:
            fixture = fixture_data.get("fixture", {})
            league = fixture_data.get("league", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            score = fixture_data.get("score", {})
            
            # Parse teams
            home_team = TeamInfo(
                id=str(teams.get("home", {}).get("id", "")),
                name=teams.get("home", {}).get("name", "Unknown"),
                logo=teams.get("home", {}).get("logo", "")
            )
            
            away_team = TeamInfo(
                id=str(teams.get("away", {}).get("id", "")),
                name=teams.get("away", {}).get("name", "Unknown"),
                logo=teams.get("away", {}).get("logo", "")
            )
            
            # Parse competition
            competition = CompetitionInfo(
                id=str(league.get("id", "")),
                name=league.get("name", "Unknown"),
                country=league.get("country", "Unknown"),
                logo=league.get("logo", "")
            )
            
            # Parse status first (needed for score logic)
            raw_status = fixture.get("status", {})
            status_short = raw_status.get("short", "NS") if isinstance(raw_status, dict) else str(raw_status)
            status_long = raw_status.get("long", "") if isinstance(raw_status, dict) else ""
            elapsed = raw_status.get("elapsed") if isinstance(raw_status, dict) else None
            
            # Log raw status for debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[PARSE] Raw status: {raw_status}, short: {status_short}, elapsed: {elapsed}")
            
            status_map = {
                "TBD": MatchStatus.SCHEDULED,
                "NS": MatchStatus.SCHEDULED,
                "1H": MatchStatus.LIVE,
                "HT": MatchStatus.LIVE,
                "2H": MatchStatus.LIVE,
                "ET": MatchStatus.LIVE,
                "P": MatchStatus.LIVE,
                "FT": MatchStatus.FINISHED,
                "AET": MatchStatus.FINISHED,
                "PEN": MatchStatus.FINISHED,
                "PST": MatchStatus.POSTPONED,
                "CANC": MatchStatus.CANCELLED,
                "ABD": MatchStatus.CANCELLED
            }
            status = status_map.get(status_short, MatchStatus.SCHEDULED)
            
            # Parse score (always include goals for live/finished matches)
            score_fulltime = None
            score_halftime = None
            
            # For live and finished matches, use goals (current score)
            # For upcoming matches, goals might be null
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            if (home_goals is not None and away_goals is not None) or status != MatchStatus.SCHEDULED:
                # Ensure we have valid integers (default to 0 if None for live matches)
                home_score_val = int(home_goals) if home_goals is not None else 0
                away_score_val = int(away_goals) if away_goals is not None else 0
                
                score_fulltime = MatchScore(
                    home=home_score_val,
                    away=away_score_val
                )
            
            ht_home = score.get("halftime", {}).get("home")
            ht_away = score.get("halftime", {}).get("away")
            if ht_home is not None and ht_away is not None:
                score_halftime = MatchScore(
                    home=int(ht_home),
                    away=int(ht_away)
                )
            
            # Parse date
            match_date_str = fixture.get("date", "")
            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00')) if match_date_str else datetime.now()
            
            return MatchDetails(
                id=str(fixture.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                competition=competition,
                match_date=match_date,
                status=status,
                score_fulltime=score_fulltime,
                score_halftime=score_halftime,
                elapsed=elapsed,
                status_short=status_short,
                status_long=status_long,
                venue=fixture.get("venue", {}).get("name", ""),
                referee=fixture.get("referee", ""),
                provider=self.config.name
            )
        
        except Exception as e:
            logger.error(f"Error parsing fixture: {e}")
            return None
    
    # =========================================================================
    # PROVIDER STATUS
    # =========================================================================
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get provider status and health"""
        connection_test = self.test_connection()
        
        return {
            "provider": "api_football",
            "api_reachable": connection_test.get("api_reachable", False),
            "key_valid": connection_test.get("key_valid", False),
            "account": connection_test.get("account", {}),
            "requests": connection_test.get("requests", {}),
            "subscription": connection_test.get("subscription", {}),
            "error": connection_test.get("error")
        }
    
    # =========================================================================
    # HISTORICAL DATA METHODS
    # =========================================================================
    
    def get_team_recent_matches(
        self,
        team_id: int,
        limit: int = 10,
        before_date: Optional[datetime] = None
    ) -> List[MatchDetails]:
        """
        Get team's recent finished matches
        
        Args:
            team_id: Team ID
            limit: Number of matches to fetch
            before_date: Only matches before this date (to exclude current match)
            
        Returns:
            List of MatchDetails (only finished matches)
        """
        try:
            # PHASE 1: Detailed logging
            logger.info("="*60)
            logger.info(f"[HISTORY] Fetching team history")
            logger.info(f"[HISTORY] team_id={team_id}")
            logger.info(f"[HISTORY] limit={limit}")
            logger.info(f"[HISTORY] before_date={before_date}")
            
            # PHASE 2: Try multiple strategies
            current_year = datetime.now().year
            strategies = [
                {
                    "name": "team+last+status+season",
                    "params": {"team": team_id, "last": limit, "status": "FT", "season": current_year}
                },
                {
                    "name": "team+last+season",
                    "params": {"team": team_id, "last": limit, "season": current_year}
                },
                {
                    "name": "team+last",
                    "params": {"team": team_id, "last": limit}
                },
                {
                    "name": "team+last+status",
                    "params": {"team": team_id, "last": limit, "status": "FT"}
                }
            ]
            
            response = None
            strategy_used = None
            
            for strategy in strategies:
                logger.info(f"[HISTORY] Trying strategy: {strategy['name']}")
                logger.info(f"[HISTORY] params={strategy['params']}")
                
                temp_response = self._make_request("fixtures", strategy['params'])
                
                if temp_response and "response" in temp_response:
                    raw_count = len(temp_response.get("response", []))
                    logger.info(f"[HISTORY] Strategy '{strategy['name']}' returned {raw_count} fixtures")
                    
                    if raw_count > 0:
                        response = temp_response
                        strategy_used = strategy['name']
                        logger.info(f"[HISTORY] ✓ Using strategy: {strategy_used}")
                        break
                else:
                    logger.info(f"[HISTORY] Strategy '{strategy['name']}' failed")
            
            if not strategy_used:
                logger.warning(f"[HISTORY] All strategies failed for team {team_id}")
                strategy_used = "none_successful"
            
            # Log response details
            if response:
                logger.info(f"[HISTORY] HTTP status=200")
                raw_count = len(response.get("response", []))
                logger.info(f"[HISTORY] raw_fixtures_count={raw_count}")
                
                if raw_count > 0:
                    # Log first few fixture IDs and dates
                    sample_fixtures = response["response"][:3]
                    for i, fixture in enumerate(sample_fixtures):
                        fixture_id = fixture.get("fixture", {}).get("id", "?")
                        fixture_date = fixture.get("fixture", {}).get("date", "?")
                        fixture_status = fixture.get("fixture", {}).get("status", {}).get("short", "?")
                        home_goals = fixture.get("goals", {}).get("home")
                        away_goals = fixture.get("goals", {}).get("away")
                        logger.info(f"[HISTORY] sample[{i}]: id={fixture_id}, date={fixture_date}, status={fixture_status}, score={home_goals}-{away_goals}")
            else:
                logger.warning(f"[HISTORY] No response from API")
            
            if not response or "response" not in response:
                logger.warning(f"[HISTORY] No history found for team {team_id}")
                logger.info("="*60)
                return []
            
            # Parse and filter
            matches = []
            rejected_future = 0
            rejected_not_finished = 0
            rejected_missing_score = 0
            rejected_date_filter = 0
            rejected_parsing = 0
            
            for fixture_data in response["response"]:
                # Check status
                status = fixture_data.get("fixture", {}).get("status", {}).get("short", "")
                if status != "FT":
                    rejected_not_finished += 1
                    continue
                
                # Check score
                goals = fixture_data.get("goals", {})
                if goals.get("home") is None or goals.get("away") is None:
                    rejected_missing_score += 1
                    continue
                
                match = self._parse_fixture(fixture_data)
                if not match:
                    rejected_parsing += 1
                    continue
                
                # Filter by date if specified
                if before_date and match.match_date >= before_date:
                    rejected_date_filter += 1
                    continue
                    
                matches.append(match)
            
            # Log filtering results
            logger.info(f"[HISTORY] Filtering results:")
            logger.info(f"[HISTORY]   - raw_count={raw_count}")
            logger.info(f"[HISTORY]   - rejected_not_finished={rejected_not_finished}")
            logger.info(f"[HISTORY]   - rejected_missing_score={rejected_missing_score}")
            logger.info(f"[HISTORY]   - rejected_date_filter={rejected_date_filter}")
            logger.info(f"[HISTORY]   - rejected_parsing={rejected_parsing}")
            logger.info(f"[HISTORY]   - accepted={len(matches)}")
            logger.info(f"[HISTORY] Final count: {len(matches)}")
            logger.info(f"[HISTORY] Strategy used: {strategy_used}")
            logger.info("="*60)
            
            # Store strategy for debugging (can be accessed by caller)
            self._last_history_strategy = strategy_used
            
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"[HISTORY] Error fetching team history: {e}")
            import traceback
            traceback.print_exc()
            logger.info("="*60)
            return []
    
    def get_head_to_head(
        self,
        home_team_id: int,
        away_team_id: int,
        limit: int = 10,
        before_date: Optional[datetime] = None
    ) -> List[MatchDetails]:
        """
        Get head-to-head matches between two teams
        
        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            limit: Number of matches to fetch
            before_date: Only matches before this date
            
        Returns:
            List of MatchDetails
        """
        try:
            # PHASE 5: H2H logging
            logger.info("="*60)
            logger.info(f"[H2H] Fetching head-to-head")
            logger.info(f"[H2H] home_team_id={home_team_id}")
            logger.info(f"[H2H] away_team_id={away_team_id}")
            logger.info(f"[H2H] limit={limit}")
            
            h2h_string = f"{home_team_id}-{away_team_id}"
            params = {
                "h2h": h2h_string,
                "last": limit
            }
            
            logger.info(f"[H2H] h2h_string={h2h_string}")
            logger.info(f"[H2H] endpoint=fixtures/headtohead")
            logger.info(f"[H2H] params={params}")
            
            response = self._make_request("fixtures/headtohead", params)
            
            # Log response
            if response:
                logger.info(f"[H2H] HTTP status=200")
                raw_count = len(response.get("response", []))
                logger.info(f"[H2H] raw_count={raw_count}")
            else:
                logger.warning(f"[H2H] No response from API")
            
            if not response or "response" not in response:
                logger.warning(f"[H2H] No H2H found for {home_team_id} vs {away_team_id}")
                logger.info("="*60)
                return []
            
            # Parse and filter
            matches = []
            rejected_not_finished = 0
            rejected_date_filter = 0
            rejected_parsing = 0
            
            for fixture_data in response["response"]:
                match = self._parse_fixture(fixture_data)
                if not match:
                    rejected_parsing += 1
                    continue
                
                # Filter by date if specified
                if before_date and match.match_date >= before_date:
                    rejected_date_filter += 1
                    continue
                    
                # Only finished matches
                status_short = safe_get_status_short(match.status)
                if status_short not in ["FT", "AET", "PEN"]:
                    rejected_not_finished += 1
                    continue
                    
                matches.append(match)
            
            # Log filtering results
            logger.info(f"[H2H] Filtering results:")
            logger.info(f"[H2H]   - raw_count={raw_count}")
            logger.info(f"[H2H]   - rejected_not_finished={rejected_not_finished}")
            logger.info(f"[H2H]   - rejected_date_filter={rejected_date_filter}")
            logger.info(f"[H2H]   - rejected_parsing={rejected_parsing}")
            logger.info(f"[H2H]   - accepted={len(matches)}")
            logger.info(f"[H2H] Final count: {len(matches)}")
            logger.info("="*60)
            
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"[H2H] Error fetching H2H: {e}")
            import traceback
            traceback.print_exc()
            logger.info("="*60)
            return []
    
    def get_fixture_odds(self, fixture_id: int) -> Optional[MatchOdds]:
        """
        Get odds for a specific fixture
        
        Args:
            fixture_id: Fixture ID
            
        Returns:
            MatchOdds or None if not available
        """
        try:
            params = {
                "fixture": fixture_id
            }
            
            response = self._make_request("odds", params)
            
            if not response or "response" not in response:
                logger.info(f"No odds available for fixture {fixture_id}")
                return None
            
            if len(response["response"]) == 0:
                return None
            
            # Parse odds (simplified - can be expanded)
            odds_data = response["response"][0]
            bookmakers = odds_data.get("bookmakers", [])
            
            if not bookmakers:
                return None
            
            # Get first bookmaker (usually Bet365)
            bookmaker = bookmakers[0]
            bets = bookmaker.get("bets", [])
            
            # Extract relevant markets (avec gestion d'erreurs)
            markets = {}
            for bet in bets:
                bet_name = bet.get("name", "")
                values = bet.get("values", [])
                
                if bet_name == "Match Winner":
                    for v in values:
                        odd_value = v.get("odd", "")
                        if odd_value and odd_value.strip():  # Vérifier que l'odd n'est pas vide
                            try:
                                if v["value"] == "Home":
                                    markets["home_win"] = float(odd_value)
                                elif v["value"] == "Draw":
                                    markets["draw"] = float(odd_value)
                                elif v["value"] == "Away":
                                    markets["away_win"] = float(odd_value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid odd value: {odd_value} for {v['value']}")
                                continue
                
                elif "Over/Under" in bet_name or "Goals" in bet_name:
                    for v in values:
                        value_str = v.get("value", "")
                        odd_value = v.get("odd", "")
                        if value_str and odd_value and odd_value.strip():  # Vérifier que les valeurs ne sont pas vides
                            try:
                                if "Over" in value_str:
                                    line = value_str.replace("Over ", "").strip()
                                    markets[f"over_{line}"] = float(odd_value)
                                elif "Under" in value_str:
                                    line = value_str.replace("Under ", "").strip()
                                    markets[f"under_{line}"] = float(odd_value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid odd value: {odd_value} for {value_str}")
                                continue
            
            if not markets:
                return None
            
            return MatchOdds(
                fixture_id=str(fixture_id),
                bookmaker=bookmaker.get("name", "Unknown"),
                markets=markets,
                last_update=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return None
