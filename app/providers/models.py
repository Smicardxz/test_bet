"""
Normalized Data Models
Pydantic models for provider responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MatchStatus(str, Enum):
    """Match status enum"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class TeamInfo(BaseModel):
    """Normalized team information"""
    id: str = Field(..., description="Provider-specific team ID")
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None


class CompetitionInfo(BaseModel):
    """Normalized competition information"""
    id: str = Field(..., description="Provider-specific competition ID")
    name: str
    country: Optional[str] = None
    tier: Optional[int] = None
    is_obscure: bool = False


class MatchScore(BaseModel):
    """Match score information"""
    home: int
    away: int


class MatchOdds(BaseModel):
    """Match odds information"""
    bookmaker: str
    market_type: str
    line: Optional[float] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    yes_odds: Optional[float] = None  # For BTTS
    no_odds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MatchDetails(BaseModel):
    """Complete match information"""
    id: str = Field(..., description="Provider-specific match ID")
    home_team: TeamInfo
    away_team: TeamInfo
    competition: CompetitionInfo
    match_date: datetime
    status: MatchStatus
    
    # Scores
    score_fulltime: Optional[MatchScore] = None
    score_halftime: Optional[MatchScore] = None
    
    # Live match details
    elapsed: Optional[int] = None  # Minute elapsed
    status_short: Optional[str] = None  # Status short code (1H, 2H, etc.)
    status_long: Optional[str] = None  # Status long description
    
    # Venue
    venue: Optional[str] = None
    
    # Additional data
    referee: Optional[str] = None
    attendance: Optional[int] = None
    
    # Provider metadata
    provider: str
    provider_url: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TeamStats(BaseModel):
    """Team statistics from recent matches"""
    team: TeamInfo
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_scored: int
    goals_conceded: int
    clean_sheets: int
    
    # Averages
    avg_goals_scored: float
    avg_goals_conceded: float
    
    # Form (last 5 matches: W=3, D=1, L=0)
    form: List[str] = Field(default_factory=list)
    
    # Provider metadata
    provider: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class HeadToHead(BaseModel):
    """Head-to-head statistics"""
    team_a: TeamInfo
    team_b: TeamInfo
    total_matches: int
    team_a_wins: int
    team_b_wins: int
    draws: int
    recent_matches: List[MatchDetails] = Field(default_factory=list)
    
    # Provider metadata
    provider: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ProviderResponse(BaseModel):
    """Generic provider response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    provider: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = False
    cache_age_seconds: Optional[int] = None
