"""
Mock Odds Provider
Generates realistic mock odds for testing
"""

from typing import List, Optional
import random
from datetime import datetime

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.models import OddsData, OddsResponse, MarketType


class MockOddsProvider(BaseOddsProvider):
    """
    Mock odds provider for testing
    
    Generates realistic odds based on market type
    """
    
    def __init__(self, config: Optional[OddsProviderConfig] = None):
        """Initialize mock odds provider"""
        if config is None:
            config = OddsProviderConfig(
                name="mock_odds",
                enabled=True
            )
        
        super().__init__(config)
        
        # Mock bookmakers
        self.bookmakers = [
            "Bet365",
            "Pinnacle",
            "Betfair",
            "William Hill",
            "Unibet"
        ]
    
    def get_match_odds(
        self,
        match_id: str,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """Get mock odds for a match"""
        
        self.logger.debug(f"Generating mock odds for match {match_id}")
        
        # Use priority markets if not specified
        if markets is None:
            markets = self.get_priority_markets()
        
        odds_list = []
        
        for market_type in markets:
            # Generate odds for this market
            odd_value = self._generate_odd(market_type)
            line = self._get_line_for_market(market_type)
            
            # Pick random bookmaker
            bookmaker = random.choice(self.bookmakers)
            
            odds_data = OddsData(
                match_id=match_id,
                market_type=market_type,
                line=line,
                odd=odd_value,
                bookmaker=bookmaker,
                timestamp=datetime.utcnow()
            )
            
            odds_list.append(odds_data)
        
        return self._create_success_response(odds_list)
    
    def get_today_odds(
        self,
        competition_ids: Optional[List[str]] = None,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """Get mock odds for today's matches"""
        
        self.logger.debug("Generating mock odds for today's matches")
        
        # Generate odds for 10 mock matches
        all_odds = []
        
        for i in range(10):
            match_id = f"match_{i+1:03d}"
            response = self.get_match_odds(match_id, markets)
            
            if response.success and response.data:
                all_odds.extend(response.data)
        
        return self._create_success_response(all_odds)
    
    def _generate_odd(self, market_type: MarketType) -> float:
        """
        Generate realistic odd for market type
        
        Args:
            market_type: Market type
            
        Returns:
            Decimal odd value
        """
        # Base odds by market type
        odds_ranges = {
            # FT Under - typically lower odds (more likely)
            MarketType.FT_UNDER_15: (1.40, 2.20),
            MarketType.FT_UNDER_25: (1.50, 2.50),
            MarketType.FT_UNDER_35: (1.30, 2.00),
            MarketType.FT_UNDER_45: (1.20, 1.80),
            
            # FT Over - typically higher odds
            MarketType.FT_OVER_15: (1.50, 2.50),
            MarketType.FT_OVER_25: (1.60, 2.80),
            MarketType.FT_OVER_35: (2.00, 3.50),
            MarketType.FT_OVER_45: (2.50, 5.00),
            
            # HT Under - very low odds (very likely)
            MarketType.HT_UNDER_05: (1.10, 1.50),
            MarketType.HT_UNDER_15: (1.05, 1.30),
            
            # HT Over - higher odds
            MarketType.HT_OVER_05: (2.00, 4.00),
            MarketType.HT_OVER_15: (3.00, 8.00),
            
            # Extreme Under - very low odds
            MarketType.FT_UNDER_85: (1.01, 1.10),
            MarketType.FT_UNDER_105: (1.001, 1.05),
            
            # BTTS
            MarketType.BTTS_YES: (1.70, 2.50),
            MarketType.BTTS_NO: (1.50, 2.20),
        }
        
        # Get range for this market
        min_odd, max_odd = odds_ranges.get(market_type, (1.50, 3.00))
        
        # Generate random odd in range
        odd = random.uniform(min_odd, max_odd)
        
        # Round to 2 decimals
        return round(odd, 2)
    
    def _get_line_for_market(self, market_type: MarketType) -> Optional[float]:
        """Get line value for market type"""
        
        lines = {
            MarketType.FT_UNDER_15: 1.5,
            MarketType.FT_OVER_15: 1.5,
            MarketType.FT_UNDER_25: 2.5,
            MarketType.FT_OVER_25: 2.5,
            MarketType.FT_UNDER_35: 3.5,
            MarketType.FT_OVER_35: 3.5,
            MarketType.FT_UNDER_45: 4.5,
            MarketType.FT_OVER_45: 4.5,
            MarketType.HT_UNDER_05: 0.5,
            MarketType.HT_OVER_05: 0.5,
            MarketType.HT_UNDER_15: 1.5,
            MarketType.HT_OVER_15: 1.5,
            MarketType.FT_UNDER_85: 8.5,
            MarketType.FT_UNDER_105: 10.5,
            MarketType.BTTS_YES: None,
            MarketType.BTTS_NO: None,
        }
        
        return lines.get(market_type)
    
    def generate_anomaly_odds(
        self,
        match_id: str,
        market_type: MarketType,
        anomaly_type: str = "overvalued"
    ) -> OddsData:
        """
        Generate odds with intentional anomaly for testing
        
        Args:
            match_id: Match ID
            market_type: Market type
            anomaly_type: "overvalued" or "undervalued"
            
        Returns:
            OddsData with anomalous odd
        """
        normal_odd = self._generate_odd(market_type)
        
        if anomaly_type == "overvalued":
            # Bookmaker odd too high (good value)
            anomalous_odd = normal_odd * random.uniform(1.3, 1.8)
        else:
            # Bookmaker odd too low (bad value)
            anomalous_odd = normal_odd * random.uniform(0.5, 0.8)
        
        line = self._get_line_for_market(market_type)
        
        return OddsData(
            match_id=match_id,
            market_type=market_type,
            line=line,
            odd=round(anomalous_odd, 2),
            bookmaker="TestBookmaker",
            timestamp=datetime.utcnow()
        )
