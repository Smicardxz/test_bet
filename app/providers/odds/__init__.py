"""
Odds Providers Package
Dedicated providers for bookmaker odds
"""

from app.providers.odds.base_odds_provider import BaseOddsProvider, OddsProviderConfig
from app.providers.odds.mock_odds_provider import MockOddsProvider
from app.providers.odds.external_odds_provider import TheOddsAPIProvider, ExternalOddsProvider
from app.providers.odds.apifootball_odds_provider import ApiFootballOddsProvider
from app.providers.odds.odds_provider_manager import OddsProviderManager
from app.providers.odds.models import (
    OddsData,
    MarketType,
    OddsResponse,
    NormalizedOdd,
    PRIORITY_MARKETS,
)

__all__ = [
    "BaseOddsProvider",
    "OddsProviderConfig",
    "MockOddsProvider",
    "TheOddsAPIProvider",
    "ExternalOddsProvider",
    "ApiFootballOddsProvider",
    "OddsProviderManager",
    "OddsData",
    "MarketType",
    "OddsResponse",
    "NormalizedOdd",
    "PRIORITY_MARKETS",
]
