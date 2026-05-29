"""
Base Odds Provider
Abstract base class for odds providers
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
import logging

from app.providers.odds.models import OddsData, OddsResponse, MarketType


logger = logging.getLogger(__name__)


@dataclass
class OddsProviderConfig:
    """Configuration for odds provider"""
    name: str
    enabled: bool = True
    timeout_seconds: int = 10
    rate_limit_per_minute: int = 60
    retry_attempts: int = 3
    
    # Markets to fetch
    fetch_ft_under_over: bool = True
    fetch_ht_under_over: bool = True
    fetch_btts: bool = True
    fetch_extreme_under: bool = True


class BaseOddsProvider(ABC):
    """
    Abstract base class for odds providers
    
    All odds providers must implement these methods
    """
    
    def __init__(self, config: OddsProviderConfig):
        """
        Initialize odds provider
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
        
        self.logger.info(f"OddsProvider initialized: {config.name}")
    
    @abstractmethod
    def get_match_odds(
        self,
        match_id: str,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """
        Get odds for a specific match
        
        Args:
            match_id: Match identifier
            markets: Optional list of markets to fetch (None = all priority markets)
            
        Returns:
            OddsResponse with list of OddsData
        """
        pass
    
    @abstractmethod
    def get_today_odds(
        self,
        competition_ids: Optional[List[str]] = None,
        markets: Optional[List[MarketType]] = None
    ) -> OddsResponse:
        """
        Get odds for today's matches
        
        Args:
            competition_ids: Optional list of competition IDs to filter
            markets: Optional list of markets to fetch
            
        Returns:
            OddsResponse with list of OddsData for all matches
        """
        pass
    
    def get_priority_markets(self) -> List[MarketType]:
        """
        Get list of priority markets based on config
        
        Returns:
            List of MarketType to fetch
        """
        markets = []
        
        if self.config.fetch_ft_under_over:
            markets.extend([
                MarketType.FT_UNDER_15,
                MarketType.FT_UNDER_25,
                MarketType.FT_UNDER_35,
                MarketType.FT_OVER_25,
                MarketType.FT_OVER_35
            ])
        
        if self.config.fetch_ht_under_over:
            markets.extend([
                MarketType.HT_UNDER_05,
                MarketType.HT_OVER_05,
                MarketType.HT_UNDER_15
            ])
        
        if self.config.fetch_btts:
            markets.extend([
                MarketType.BTTS_YES,
                MarketType.BTTS_NO
            ])
        
        if self.config.fetch_extreme_under:
            markets.extend([
                MarketType.FT_UNDER_85,
                MarketType.FT_UNDER_105
            ])
        
        return markets
    
    def _create_success_response(
        self,
        data: List[OddsData],
        cached: bool = False,
        cache_age: Optional[int] = None
    ) -> OddsResponse:
        """Create success response"""
        return OddsResponse(
            success=True,
            data=data,
            provider=self.config.name,
            cached=cached,
            cache_age_seconds=cache_age
        )
    
    def _create_error_response(self, error: str) -> OddsResponse:
        """Create error response"""
        return OddsResponse(
            success=False,
            error=error,
            provider=self.config.name
        )
