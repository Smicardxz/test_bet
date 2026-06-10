"""
Odds Models
Data models for bookmaker odds
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
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

    # BTTS
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"

    # 1X2 (H2H)
    H2H_HOME = "h2h_home"
    H2H_DRAW = "h2h_draw"
    H2H_AWAY = "h2h_away"


# Markets to IGNORE (too high, not useful for EV)
IGNORED_MARKET_LINES = {6.5, 7.5, 8.5, 9.5, 10.5, 12.5}

# Mapping from (is_over, line) to MarketType
TOTALS_MAP: Dict[tuple, MarketType] = {
    (False, 1.5): MarketType.FT_UNDER_15,
    (True,  1.5): MarketType.FT_OVER_15,
    (False, 2.5): MarketType.FT_UNDER_25,
    (True,  2.5): MarketType.FT_OVER_25,
    (False, 3.5): MarketType.FT_UNDER_35,
    (True,  3.5): MarketType.FT_OVER_35,
    (False, 4.5): MarketType.FT_UNDER_45,
    (True,  4.5): MarketType.FT_OVER_45,
}

HT_TOTALS_MAP: Dict[tuple, MarketType] = {
    (False, 0.5): MarketType.HT_UNDER_05,
    (True,  0.5): MarketType.HT_OVER_05,
    (False, 1.5): MarketType.HT_UNDER_15,
    (True,  1.5): MarketType.HT_OVER_15,
}


@dataclass
class NormalizedOdd:
    """
    Phase 4 — Normalized single odd entry.
    Canonical format returned by all odds providers.
    """
    bookmaker: str
    market: str          # e.g. "FT_OVER_2_5"
    line: Optional[float]
    side: str            # OVER | UNDER | YES | NO | HOME | DRAW | AWAY
    odd: float           # decimal
    implied_probability: float   # 1 / odd
    timestamp: str
    source: str = "the_odds_api"
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bookmaker": self.bookmaker,
            "market": self.market,
            "line": self.line,
            "side": self.side,
            "odd": round(self.odd, 3),
            "implied_probability": round(self.implied_probability * 100, 2),
            "timestamp": self.timestamp,
            "source": self.source,
        }


@dataclass
class MatchMapping:
    """
    Phase 3 — Mapping result between API-Football fixture and Odds API event.
    """
    event_id: str
    home_team_api: str
    away_team_api: str
    home_team_odds: str
    away_team_odds: str
    kickoff_diff_minutes: float
    name_score_home: float
    name_score_away: float
    match_confidence_score: float          # 0.0 - 1.0
    confidence_label: str                  # EXACT | HIGH | MEDIUM | LOW | FAILED
    odds_status: str = "MATCHED"           # MATCHED | MATCHING_UNCERTAIN | FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "match_confidence_score": round(self.match_confidence_score, 3),
            "confidence_label": self.confidence_label,
            "odds_status": self.odds_status,
            "kickoff_diff_minutes": round(self.kickoff_diff_minutes, 1),
            "home_team_api": self.home_team_api,
            "home_team_odds": self.home_team_odds,
            "away_team_api": self.away_team_api,
            "away_team_odds": self.away_team_odds,
        }


class OddsData(BaseModel):
    """Single odds entry (Pydantic, for backward compat)"""
    match_id: str
    market_type: MarketType
    line: Optional[float] = None
    odd: float
    bookmaker: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    match_date: Optional[datetime] = None

    class Config:
        use_enum_values = True


class OddsResponse(BaseModel):
    """Response from odds provider"""
    success: bool
    data: Optional[List[OddsData]] = None
    error: Optional[str] = None
    provider: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = False
    cache_age_seconds: Optional[int] = None


class MarketConfig(BaseModel):
    """Market configuration"""
    market_type: MarketType
    line: Optional[float] = None
    priority: int = 1
    enabled: bool = True


# Priority markets — only useful lines, no 6.5+
PRIORITY_MARKETS = [
    MarketConfig(market_type=MarketType.HT_UNDER_05, line=0.5, priority=1),
    MarketConfig(market_type=MarketType.HT_UNDER_15, line=1.5, priority=1),
    MarketConfig(market_type=MarketType.HT_OVER_05,  line=0.5, priority=1),
    MarketConfig(market_type=MarketType.HT_OVER_15,  line=1.5, priority=2),
    MarketConfig(market_type=MarketType.FT_UNDER_15, line=1.5, priority=1),
    MarketConfig(market_type=MarketType.FT_UNDER_25, line=2.5, priority=1),
    MarketConfig(market_type=MarketType.FT_UNDER_35, line=3.5, priority=2),
    MarketConfig(market_type=MarketType.FT_OVER_15,  line=1.5, priority=2),
    MarketConfig(market_type=MarketType.FT_OVER_25,  line=2.5, priority=1),
    MarketConfig(market_type=MarketType.FT_OVER_35,  line=3.5, priority=2),
    MarketConfig(market_type=MarketType.BTTS_YES,    priority=2),
    MarketConfig(market_type=MarketType.BTTS_NO,     priority=2),
    MarketConfig(market_type=MarketType.H2H_HOME,    priority=3),
    MarketConfig(market_type=MarketType.H2H_DRAW,    priority=3),
    MarketConfig(market_type=MarketType.H2H_AWAY,    priority=3),
]
