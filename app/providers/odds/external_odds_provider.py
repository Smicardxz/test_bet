"""
External Odds Provider
Fetches odds from external APIs (The Odds API, etc.)
"""

from typing import List, Optional
import requests
from datetime import datetime
import time

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.models import OddsData, OddsResponse, MarketType


class ExternalOddsProvider(BaseOddsProvider):
    """
    External odds provider
    
    Fetches odds from external APIs like The Odds API
    
    Note: Requires API key and subscription
    """
    
    def __init__(
        self,
        config: Optional[OddsProviderConfig] = None,
        api_key: Optional[str] = None,
        api_url: str = "https://api.the-odds-api.com/v4"
    ):
        """
        Initialize external odds provider
        
        Args:
            config: Provider configuration
            api_key: API key for external service
            api_url: Base URL for API
        """
        if config is None:
            config = OddsProviderConfig(
                name="external_odds",
                enabled=True,
                timeout_seconds=15,
                rate_limit_per_minute=30
            )
        
        super().__init__(config)
        
        self.api_key = api_key
        self.api_url = api_url
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BettingAnalyzer/1.0"
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60.0 / config.rate_limit_per_minute
        
        if not api_key:
            self.logger.warning("No API key provided - provider will not work")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make HTTP request to API"""
        self._rate_limit()
        
        if not self.api_key:
            raise ValueError("API key required")
        
        url = f"{self.api_url}{endpoint}"
        
        # Add API key to params
        if params is None:
            params = {}
        params["apiKey"] = self.api_key
        
        self.logger.debug(f"GET {url}")
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise
    
    def get_match_odds(
        self,
        match_id: str,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """
        Get odds for a specific match
        
        Note: Implementation depends on specific API structure
        """
        
        self.logger.info(f"Fetching odds for match {match_id}")
        
        if not self.api_key:
            return self._create_error_response("API key not configured")
        
        try:
            # Example endpoint - adjust based on actual API
            endpoint = f"/sports/soccer/events/{match_id}/odds"
            
            data = self._make_request(endpoint)
            
            # Parse response and convert to OddsData
            odds_list = self._parse_odds_response(data, match_id, markets)
            
            return self._create_success_response(odds_list)
        
        except Exception as e:
            self.logger.error(f"Error fetching odds: {e}")
            return self._create_error_response(str(e))
    
    def get_today_odds(
        self,
        competition_ids: Optional[List[str]] = None,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """
        Get odds for today's matches
        
        Note: Implementation depends on specific API structure
        """
        
        self.logger.info("Fetching today's odds")
        
        if not self.api_key:
            return self._create_error_response("API key not configured")
        
        try:
            # Example endpoint - adjust based on actual API
            endpoint = "/sports/soccer/odds"
            
            params = {
                "regions": "eu",
                "markets": "h2h,totals,btts",
                "dateFormat": "iso"
            }
            
            data = self._make_request(endpoint, params)
            
            # Parse response
            all_odds = []
            
            for event in data:
                match_id = event.get("id")
                odds_list = self._parse_odds_response(event, match_id, markets)
                all_odds.extend(odds_list)
            
            return self._create_success_response(all_odds)
        
        except Exception as e:
            self.logger.error(f"Error fetching today's odds: {e}")
            return self._create_error_response(str(e))
    
    def _parse_odds_response(
        self,
        data: dict,
        match_id: str,
        markets: Optional[List[MarketType]] = None
    ) -> List[OddsData]:
        """
        Parse API response to OddsData list
        
        Note: This is a template - adjust based on actual API structure
        """
        
        odds_list = []
        
        # Use priority markets if not specified
        if markets is None:
            markets = self.get_priority_markets()
        
        # Example parsing - adjust based on actual API
        bookmakers = data.get("bookmakers", [])
        
        for bookmaker_data in bookmakers:
            bookmaker_name = bookmaker_data.get("title", "Unknown")
            
            for market_data in bookmaker_data.get("markets", []):
                market_key = market_data.get("key")
                
                # Map API market key to our MarketType
                market_type = self._map_market_key(market_key)
                
                if not market_type or market_type not in markets:
                    continue
                
                # Extract odds
                for outcome in market_data.get("outcomes", []):
                    odd_value = outcome.get("price")
                    line = outcome.get("point")
                    
                    if odd_value:
                        odds_data = OddsData(
                            match_id=match_id,
                            market_type=market_type,
                            line=line,
                            odd=float(odd_value),
                            bookmaker=bookmaker_name,
                            timestamp=datetime.utcnow()
                        )
                        
                        odds_list.append(odds_data)
        
        return odds_list
    
    def _map_market_key(self, api_market_key: str) -> Optional[MarketType]:
        """
        Map API market key to our MarketType
        
        Note: Adjust based on actual API market keys
        """
        
        mapping = {
            "totals_under_1.5": MarketType.FT_UNDER_15,
            "totals_over_1.5": MarketType.FT_OVER_15,
            "totals_under_2.5": MarketType.FT_UNDER_25,
            "totals_over_2.5": MarketType.FT_OVER_25,
            "totals_under_3.5": MarketType.FT_UNDER_35,
            "totals_over_3.5": MarketType.FT_OVER_35,
            "btts_yes": MarketType.BTTS_YES,
            "btts_no": MarketType.BTTS_NO,
            # Add more mappings as needed
        }
        
        return mapping.get(api_market_key)


class TheOddsAPIProvider(ExternalOddsProvider):
    """
    Specialized provider for The Odds API
    
    https://the-odds-api.com/
    """
    
    def __init__(self, api_key: str, config: Optional[OddsProviderConfig] = None):
        """Initialize The Odds API provider"""
        
        if config is None:
            config = OddsProviderConfig(
                name="the_odds_api",
                enabled=True,
                timeout_seconds=15,
                rate_limit_per_minute=30
            )
        
        super().__init__(
            config=config,
            api_key=api_key,
            api_url="https://api.the-odds-api.com/v4"
        )
