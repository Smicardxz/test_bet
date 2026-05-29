"""
Normalized Data Models
Simple dataclasses for normalized historical match data
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class NormalizedHistoricalMatch:
    """
    Normalized historical match data
    
    Contains all data needed for statistical analysis
    """
    fixture_id: str
    date: datetime
    team_id: str
    opponent_id: str
    team_name: str
    opponent_name: str
    is_home: bool
    
    # HT scores
    ht_goals_for: Optional[int] = None
    ht_goals_against: Optional[int] = None
    ht_total_goals: Optional[int] = None
    ht_score_available: bool = False
    
    # FT scores
    ft_goals_for: Optional[int] = None
    ft_goals_against: Optional[int] = None
    ft_total_goals: Optional[int] = None
    ft_score_available: bool = False
    
    # Match info
    status: str = "FT"
    competition: str = ""
    season: str = ""
    
    # Data origin
    data_origin: str = "REAL"  # REAL or MOCK
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "fixture_id": self.fixture_id,
            "date": self.date.isoformat() if self.date else None,
            "team_id": self.team_id,
            "opponent_id": self.opponent_id,
            "team_name": self.team_name,
            "opponent_name": self.opponent_name,
            "is_home": self.is_home,
            "ht_goals_for": self.ht_goals_for,
            "ht_goals_against": self.ht_goals_against,
            "ht_total_goals": self.ht_total_goals,
            "ht_score_available": self.ht_score_available,
            "ft_goals_for": self.ft_goals_for,
            "ft_goals_against": self.ft_goals_against,
            "ft_total_goals": self.ft_total_goals,
            "ft_score_available": self.ft_score_available,
            "status": self.status,
            "competition": self.competition,
            "season": self.season,
            "data_origin": self.data_origin
        }


@dataclass
class MatchDataBundle:
    """
    Complete data bundle for a match analysis
    
    Contains all historical data needed for analysis
    """
    fixture_id: str
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    
    # Historical data
    home_history: List[NormalizedHistoricalMatch] = field(default_factory=list)
    away_history: List[NormalizedHistoricalMatch] = field(default_factory=list)
    h2h: List[NormalizedHistoricalMatch] = field(default_factory=list)
    
    # Odds if available
    odds_available: bool = False
    odds_markets: Dict[str, float] = field(default_factory=dict)
    
    # Data quality
    data_origin: str = "REAL"
    history_status: str = "OK"  # OK, INSUFFICIENT, MISSING, ERROR
    
    # Counts
    home_history_count: int = 0
    away_history_count: int = 0
    h2h_count: int = 0
    
    # HT data availability
    ht_data_available: bool = False
    ht_sample_size: int = 0
    
    # FT data availability
    ft_data_available: bool = False
    ft_sample_size: int = 0
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.home_history_count = len(self.home_history)
        self.away_history_count = len(self.away_history)
        self.h2h_count = len(self.h2h)
        
        # Check HT data availability
        all_matches = self.home_history + self.away_history + self.h2h
        ht_available_count = sum(1 for m in all_matches if m.ht_score_available)
        self.ht_data_available = ht_available_count > 0
        self.ht_sample_size = ht_available_count
        
        # Check FT data availability
        ft_available_count = sum(1 for m in all_matches if m.ft_score_available)
        self.ft_data_available = ft_available_count > 0
        self.ft_sample_size = ft_available_count
        
        # Determine history status
        total_matches = self.home_history_count + self.away_history_count
        if total_matches == 0:
            self.history_status = "MISSING"
        elif total_matches < 5:
            self.history_status = "INSUFFICIENT"
            self.warnings.append(f"Only {total_matches} historical matches (minimum 5 recommended)")
        else:
            self.history_status = "OK"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "fixture_id": self.fixture_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_team_name": self.home_team_name,
            "away_team_name": self.away_team_name,
            "home_history": [m.to_dict() for m in self.home_history],
            "away_history": [m.to_dict() for m in self.away_history],
            "h2h": [m.to_dict() for m in self.h2h],
            "odds_available": self.odds_available,
            "odds_markets": self.odds_markets,
            "data_origin": self.data_origin,
            "history_status": self.history_status,
            "home_history_count": self.home_history_count,
            "away_history_count": self.away_history_count,
            "h2h_count": self.h2h_count,
            "ht_data_available": self.ht_data_available,
            "ht_sample_size": self.ht_sample_size,
            "ft_data_available": self.ft_data_available,
            "ft_sample_size": self.ft_sample_size,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def get_ft_goal_history(self) -> List[int]:
        """Get FT total goals history for analysis"""
        goals = []
        for match in self.home_history + self.away_history:
            if match.ft_score_available and match.ft_total_goals is not None:
                goals.append(match.ft_total_goals)
        return goals
    
    def get_ht_goal_history(self) -> List[int]:
        """Get HT total goals history for analysis"""
        goals = []
        for match in self.home_history + self.away_history:
            if match.ht_score_available and match.ht_total_goals is not None:
                goals.append(match.ht_total_goals)
        return goals
