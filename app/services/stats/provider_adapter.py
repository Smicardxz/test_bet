"""
Provider Adapter for StatsEngine
Converts provider matches to format usable by StatsEngine
"""

from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from app.providers.models import MatchDetails, MatchStatus


# Define TeamStats here to avoid importing from stats_engine
@dataclass
class TeamStats:
    """
    Complete statistical profile for a team
    All rates are percentages (0-100)
    """
    
    # Metadata
    team_id: int
    team_name: str
    sample_size: int
    home_away: str  # "home", "away", "all"
    last_updated: str
    
    # Full Time Stats
    avg_total_goals: float
    avg_goals_scored: float
    avg_goals_conceded: float
    
    # Under Rates (%)
    under_1_5_rate: float
    under_2_5_rate: float
    under_3_5_rate: float
    under_4_5_rate: float
    under_5_5_rate: float
    under_extreme_line_rate: float  # Under 10.5 or custom extreme
    
    # Over Rates (%)
    over_1_5_rate: float
    over_2_5_rate: float
    over_3_5_rate: float
    over_4_5_rate: float
    over_5_5_rate: float
    
    # Half Time Stats
    avg_ht_total_goals: float
    avg_ht_goals_scored: float
    avg_ht_goals_conceded: float
    ht_under_0_5_rate: float
    ht_under_1_5_rate: float
    ht_over_0_5_rate: float
    ht_over_1_5_rate: float
    
    # BTTS & Clean sheets
    btts_rate: float
    ht_btts_rate: float
    clean_sheet_rate: float
    failed_to_score_rate: float
    
    # Variance & Stability
    goals_variance: float
    ht_goals_variance: float
    goals_scored_variance: float
    goals_conceded_variance: float
    stability_score: float
    
    # Trending (last 5 vs last 10)
    trending_total_goals: str  # "increasing", "decreasing", "stable"
    trending_goals_scored: str
    trending_goals_conceded: str
    
    # Momentum
    momentum_score: float
    
    # Data Quality
    data_quality_score: float
    sample_adequacy: str  # "excellent", "good", "adequate", "poor"
    
    # Form
    form: List
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return self.to_dict()


class StatsEngineProviderAdapter:
    """Adapter to use StatsEngine with provider data"""
    
    def __init__(self, stats_engine: Optional[Any] = None):
        """
        Initialize adapter
        
        Args:
            stats_engine: StatsEngine instance (optional, not used in standalone mode)
        """
        self.stats_engine = stats_engine
    
    def calculate_from_provider_matches(
        self,
        team_id: str,
        team_name: str,
        matches: List[MatchDetails],
        home_away: str = "all"
    ) -> TeamStats:
        """
        Calculate team stats from provider matches
        
        Args:
            team_id: Team ID
            team_name: Team name
            matches: List of MatchDetails from provider
            home_away: "home", "away", or "all"
            
        Returns:
            TeamStats object
        """
        
        # Filter finished matches only
        finished_matches = [
            m for m in matches
            if m.status == MatchStatus.FINISHED and m.score_fulltime
        ]
        
        if not finished_matches:
            return self._create_empty_stats(team_id, team_name, home_away)
        
        # Filter by home/away if specified
        if home_away == "home":
            filtered_matches = [m for m in finished_matches if m.home_team.id == team_id]
        elif home_away == "away":
            filtered_matches = [m for m in finished_matches if m.away_team.id == team_id]
        else:
            filtered_matches = finished_matches
        
        if not filtered_matches:
            return self._create_empty_stats(team_id, team_name, home_away)
        
        # Extract goals data
        goals_scored = []
        goals_conceded = []
        ht_goals_scored = []
        ht_goals_conceded = []
        
        for match in filtered_matches:
            is_home = match.home_team.id == team_id
            
            # Full time goals
            if is_home:
                goals_scored.append(match.score_fulltime.home)
                goals_conceded.append(match.score_fulltime.away)
            else:
                goals_scored.append(match.score_fulltime.away)
                goals_conceded.append(match.score_fulltime.home)
            
            # Half time goals (if available)
            if match.score_halftime:
                if is_home:
                    ht_goals_scored.append(match.score_halftime.home)
                    ht_goals_conceded.append(match.score_halftime.away)
                else:
                    ht_goals_scored.append(match.score_halftime.away)
                    ht_goals_conceded.append(match.score_halftime.home)
        
        # Calculate stats using StatsEngine methods
        sample_size = len(filtered_matches)
        
        # Full time averages
        avg_goals_scored = sum(goals_scored) / sample_size
        avg_goals_conceded = sum(goals_conceded) / sample_size
        avg_total_goals = avg_goals_scored + avg_goals_conceded
        
        # Half time averages
        if ht_goals_scored:
            avg_ht_goals_scored = sum(ht_goals_scored) / len(ht_goals_scored)
            avg_ht_goals_conceded = sum(ht_goals_conceded) / len(ht_goals_conceded)
            avg_ht_total_goals = avg_ht_goals_scored + avg_ht_goals_conceded
            ht_00_rate = sum(1 for g in ht_goals_scored + ht_goals_conceded if g == 0) / (len(ht_goals_scored) * 2) * 100
        else:
            avg_ht_goals_scored = 0.0
            avg_ht_goals_conceded = 0.0
            avg_ht_total_goals = 0.0
            ht_00_rate = 0.0
        
        # Under/Over rates
        total_goals_list = [gs + gc for gs, gc in zip(goals_scored, goals_conceded)]
        
        under_1_5_rate = sum(1 for g in total_goals_list if g < 1.5) / sample_size * 100
        under_2_5_rate = sum(1 for g in total_goals_list if g < 2.5) / sample_size * 100
        under_3_5_rate = sum(1 for g in total_goals_list if g < 3.5) / sample_size * 100
        under_4_5_rate = sum(1 for g in total_goals_list if g < 4.5) / sample_size * 100
        under_5_5_rate = sum(1 for g in total_goals_list if g < 5.5) / sample_size * 100
        under_extreme_rate = sum(1 for g in total_goals_list if g < 10.5) / sample_size * 100
        
        over_1_5_rate = 100 - under_1_5_rate
        over_2_5_rate = 100 - under_2_5_rate
        over_3_5_rate = 100 - under_3_5_rate
        over_4_5_rate = 100 - under_4_5_rate
        over_5_5_rate = 100 - under_5_5_rate
        
        # BTTS rate
        btts_rate = sum(1 for gs, gc in zip(goals_scored, goals_conceded) if gs > 0 and gc > 0) / sample_size * 100
        
        # Clean sheets
        clean_sheet_rate = sum(1 for gc in goals_conceded if gc == 0) / sample_size * 100
        
        # Variance
        if sample_size > 1:
            variance_goals_scored = sum((g - avg_goals_scored) ** 2 for g in goals_scored) / sample_size
            variance_goals_conceded = sum((g - avg_goals_conceded) ** 2 for g in goals_conceded) / sample_size
        else:
            variance_goals_scored = 0.0
            variance_goals_conceded = 0.0
        
        # Stability score (inverse of variance)
        combined_variance = (variance_goals_scored + variance_goals_conceded) / 2
        stability_score = max(0.0, 1.0 - (combined_variance / 3.0))
        
        # Form (last 5 matches)
        form = []
        for match in filtered_matches[-5:]:
            is_home = match.home_team.id == team_id
            home_score = match.score_fulltime.home
            away_score = match.score_fulltime.away
            
            if is_home:
                if home_score > away_score:
                    form.append("W")
                elif home_score < away_score:
                    form.append("L")
                else:
                    form.append("D")
            else:
                if away_score > home_score:
                    form.append("W")
                elif away_score < home_score:
                    form.append("L")
                else:
                    form.append("D")
        
        # Data quality score
        data_quality_score = min(1.0, sample_size / 15.0)
        
        # Calculate total variance
        goals_variance = (variance_goals_scored + variance_goals_conceded) / 2
        
        # Calculate HT variance
        if sample_size > 1 and ht_goals_scored:
            ht_goals_variance = sum((g - avg_ht_goals_scored) ** 2 for g in ht_goals_scored) / sample_size
        else:
            ht_goals_variance = 0.0
        
        # Trending (simple version)
        trending_total_goals = "stable"
        trending_goals_scored = "stable"
        trending_goals_conceded = "stable"
        
        # Momentum (simple version)
        momentum_score = 0.5
        
        # Sample adequacy
        if sample_size >= 15:
            sample_adequacy = "excellent"
        elif sample_size >= 10:
            sample_adequacy = "good"
        elif sample_size >= 5:
            sample_adequacy = "adequate"
        else:
            sample_adequacy = "poor"
        
        # Failed to score rate
        failed_to_score_rate = sum(1 for gs in goals_scored if gs == 0) / sample_size * 100
        
        # HT BTTS rate
        if ht_goals_scored and ht_goals_conceded:
            ht_btts_rate = sum(1 for gs, gc in zip(ht_goals_scored, ht_goals_conceded) if gs > 0 and gc > 0) / len(ht_goals_scored) * 100
        else:
            ht_btts_rate = 0.0
        
        # HT over/under rates
        ht_under_0_5_rate = sum(1 for g in ht_goals_scored if g == 0) / len(ht_goals_scored) * 100 if ht_goals_scored else 0.0
        ht_under_1_5_rate = sum(1 for g in ht_goals_scored if g <= 1) / len(ht_goals_scored) * 100 if ht_goals_scored else 0.0
        ht_over_0_5_rate = 100 - ht_under_0_5_rate
        ht_over_1_5_rate = 100 - ht_under_1_5_rate
        
        # Create TeamStats
        return TeamStats(
            team_id=int(team_id) if team_id.isdigit() else hash(team_id) % 1000000,
            team_name=team_name,
            sample_size=sample_size,
            home_away=home_away,
            last_updated=datetime.utcnow().isoformat(),
            
            # Full time
            avg_total_goals=round(avg_total_goals, 2),
            avg_goals_scored=round(avg_goals_scored, 2),
            avg_goals_conceded=round(avg_goals_conceded, 2),
            
            # Under rates
            under_1_5_rate=round(under_1_5_rate, 1),
            under_2_5_rate=round(under_2_5_rate, 1),
            under_3_5_rate=round(under_3_5_rate, 1),
            under_4_5_rate=round(under_4_5_rate, 1),
            under_5_5_rate=round(under_5_5_rate, 1),
            under_extreme_line_rate=round(under_extreme_rate, 1),
            
            # Over rates
            over_1_5_rate=round(over_1_5_rate, 1),
            over_2_5_rate=round(over_2_5_rate, 1),
            over_3_5_rate=round(over_3_5_rate, 1),
            over_4_5_rate=round(over_4_5_rate, 1),
            over_5_5_rate=round(over_5_5_rate, 1),
            
            # Half time
            avg_ht_total_goals=round(avg_ht_total_goals, 2),
            avg_ht_goals_scored=round(avg_ht_goals_scored, 2),
            avg_ht_goals_conceded=round(avg_ht_goals_conceded, 2),
            ht_under_0_5_rate=round(ht_under_0_5_rate, 1),
            ht_under_1_5_rate=round(ht_under_1_5_rate, 1),
            ht_over_0_5_rate=round(ht_over_0_5_rate, 1),
            ht_over_1_5_rate=round(ht_over_1_5_rate, 1),
            
            # BTTS & Clean sheets
            btts_rate=round(btts_rate, 1),
            ht_btts_rate=round(ht_btts_rate, 1),
            clean_sheet_rate=round(clean_sheet_rate, 1),
            failed_to_score_rate=round(failed_to_score_rate, 1),
            
            # Variance & Stability
            goals_variance=round(goals_variance, 2),
            ht_goals_variance=round(ht_goals_variance, 2),
            goals_scored_variance=round(variance_goals_scored, 2),
            goals_conceded_variance=round(variance_goals_conceded, 2),
            stability_score=round(stability_score, 2),
            
            # Trending
            trending_total_goals=trending_total_goals,
            trending_goals_scored=trending_goals_scored,
            trending_goals_conceded=trending_goals_conceded,
            
            # Momentum
            momentum_score=round(momentum_score, 2),
            
            # Data quality
            data_quality_score=round(data_quality_score, 2),
            sample_adequacy=sample_adequacy,
            
            # Form
            form=form
        )
    
    def _create_empty_stats(self, team_id: str, team_name: str, home_away: str) -> TeamStats:
        """Create empty stats when no data available"""
        return TeamStats(
            team_id=int(team_id) if team_id.isdigit() else hash(team_id) % 1000000,
            team_name=team_name,
            sample_size=0,
            home_away=home_away,
            last_updated=datetime.utcnow().isoformat(),
            avg_total_goals=0.0,
            avg_goals_scored=0.0,
            avg_goals_conceded=0.0,
            under_1_5_rate=0.0,
            under_2_5_rate=0.0,
            under_3_5_rate=0.0,
            under_4_5_rate=0.0,
            under_5_5_rate=0.0,
            under_extreme_line_rate=0.0,
            over_1_5_rate=0.0,
            over_2_5_rate=0.0,
            over_3_5_rate=0.0,
            over_4_5_rate=0.0,
            over_5_5_rate=0.0,
            avg_ht_total_goals=0.0,
            avg_ht_goals_scored=0.0,
            avg_ht_goals_conceded=0.0,
            ht_under_0_5_rate=0.0,
            ht_under_1_5_rate=0.0,
            ht_over_0_5_rate=0.0,
            ht_over_1_5_rate=0.0,
            btts_rate=0.0,
            ht_btts_rate=0.0,
            clean_sheet_rate=0.0,
            failed_to_score_rate=0.0,
            goals_variance=0.0,
            ht_goals_variance=0.0,
            goals_scored_variance=0.0,
            goals_conceded_variance=0.0,
            stability_score=0.0,
            trending_total_goals="stable",
            trending_goals_scored="stable",
            trending_goals_conceded="stable",
            momentum_score=0.0,
            data_quality_score=0.0,
            sample_adequacy="poor",
            form=[]
        )


# Add method to StatsEngine for convenience
def add_provider_support_to_stats_engine():
    """Add calculate_from_provider_matches method to StatsEngine"""
    try:
        from app.services.stats.stats_engine import StatsEngine
        
        def calculate_from_provider_matches(self, team_id: str, matches: List[MatchDetails]) -> TeamStats:
            """Calculate stats from provider matches"""
            adapter = StatsEngineProviderAdapter(self)
            team_name = matches[0].home_team.name if matches[0].home_team.id == team_id else matches[0].away_team.name
            return adapter.calculate_from_provider_matches(team_id, team_name, matches)
        
        StatsEngine.calculate_from_provider_matches = calculate_from_provider_matches
    except (ImportError, NameError):
        # StatsEngine not available (SQLAlchemy not installed), skip monkey-patching
        pass


# Auto-add on import (safe - will skip if StatsEngine not available)
add_provider_support_to_stats_engine()
