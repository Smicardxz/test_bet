"""
Odds Models
Data models for bookmaker odds
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MarketType(str, Enum):
    """Supported market types"""
    # Full Time Under/Over
    FT_UNDER_15 = "ft_under_15"
    FT_OVER_15 = "ft_over_15"
    FT_UNDER_25 = "ft_under_25"
    FT_OVER_25 = "ft_over_25"
    FT_UNDER_35 = "ft_under_35"
    FT_OVER_35 = "ft_over_35"
    FT_UNDER_45 = "ft_under_45"
    FT_OVER_45 = "ft_over_45"
    
    # Half Time Under/Over
    HT_UNDER_05 = "ht_under_05"
    HT_OVER_05 = "ht_over_05"
    HT_UNDER_15 = "ht_under_15"
    HT_OVER_15 = "ht_over_15"
    
    # Extreme Under
    FT_UNDER_85 = "ft_under_85"
    FT_UNDER_105 = "ft_under_105"
    
    # BTTS
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class OddsData(BaseModel):
    """
    Single odds entry
    
    Represents one bookmaker odd for a specific market
    """
    match_id: str
    market_type: MarketType
    line: Optional[float] = None  # e.g., 2.5 for Over/Under 2.5
    odd: float  # Decimal odds (e.g., 1.85)
    bookmaker: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional metadata
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    match_date: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class OddsResponse(BaseModel):
    """
    Response from odds provider
    
    Contains list of odds for a match or multiple matches
    """
    success: bool
    data: Optional[List[OddsData]] = None
    error: Optional[str] = None
    provider: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Cache metadata
    cached: bool = False
    cache_age_seconds: Optional[int] = None


class MarketConfig(BaseModel):
    """
    Market configuration
    
    Defines which markets to fetch and their priority
    """
    market_type: MarketType
    line: Optional[float] = None
    priority: int = 1  # 1=highest, 5=lowest
    enabled: bool = True


# Priority markets configuration
PRIORITY_MARKETS = [
    # CRITICAL - HT Under
    MarketConfig(market_type=MarketType.HT_UNDER_05, line=0.5, priority=1),
    
    # CRITICAL - Extreme Under
    MarketConfig(market_type=MarketType.FT_UNDER_85, line=8.5, priority=1),
    MarketConfig(market_type=MarketType.FT_UNDER_105, line=10.5, priority=1),
    
    # HIGH - FT Under/Over
    MarketConfig(market_type=MarketType.FT_UNDER_15, line=1.5, priority=2),
    MarketConfig(market_type=MarketType.FT_UNDER_25, line=2.5, priority=2),
    MarketConfig(market_type=MarketType.FT_OVER_25, line=2.5, priority=2),
    
    # HIGH - HT Over
    MarketConfig(market_type=MarketType.HT_OVER_05, line=0.5, priority=2),
    
    # MEDIUM - BTTS
    MarketConfig(market_type=MarketType.BTTS_YES, priority=3),
    MarketConfig(market_type=MarketType.BTTS_NO, priority=3),
    
    # MEDIUM - Additional FT
    MarketConfig(market_type=MarketType.FT_UNDER_35, line=3.5, priority=3),
    MarketConfig(market_type=MarketType.FT_OVER_35, line=3.5, priority=3),
]
