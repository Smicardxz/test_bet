"""
Match Data Loader
Loads and normalizes real historical data for match analysis
"""

import logging
from typing import Optional
from datetime import datetime

from app.providers.base_provider import BaseDataProvider
from app.providers.models import MatchDetails
from app.services.data.normalized_models import (
    NormalizedHistoricalMatch,
    MatchDataBundle
)

logger = logging.getLogger(__name__)


class MatchDataLoader:
    """
    Loads complete historical data for a match
    
    Fetches:
    - Home team history
    - Away team history
    - Head-to-head
    - Odds (if available)
    
    Returns normalized MatchDataBundle
    """
    
    def __init__(self, provider: BaseDataProvider):
        """
        Initialize loader
        
        Args:
            provider: Data provider (must have get_team_recent_matches, get_head_to_head)
        """
        self.provider = provider
    
    def _safe_get_status(self, status) -> str:
        """
        Safely extract status from various formats
        
        Args:
            status: Can be MatchStatus enum, dict, object, or string
            
        Returns:
            Status string (e.g., "FT", "NS") or "UNK" if unknown
        """
        if status is None:
            return "FT"  # Default for historical matches
        
        # If it's a string (MatchStatus enum value)
        if isinstance(status, str):
            if status == "finished":
                return "FT"
            if status == "scheduled":
                return "NS"
            if status == "live":
                return "LIVE"
            return status.upper()
        
        # If it's a dict
        if isinstance(status, dict):
            return status.get("short", status.get("code", "FT"))
        
        # If it's an object with .short
        if hasattr(status, "short"):
            return str(status.short)
        
        # If it's an enum with .value
        if hasattr(status, "value"):
            return self._safe_get_status(status.value)
        
        # Fallback
        logger.warning(f"Unknown status format: {type(status)} - {status}")
        return "FT"
    
    def load_match_data(
        self,
        fixture_id: str,
        home_team_id: int,
        away_team_id: int,
        home_team_name: str,
        away_team_name: str,
        match_date: Optional[datetime] = None,
        history_limit: int = 10
    ) -> MatchDataBundle:
        """
        Load complete match data bundle
        
        Args:
            fixture_id: Fixture ID
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_team_name: Home team name
            away_team_name: Away team name
            match_date: Match date (to exclude from history)
            history_limit: Number of historical matches to fetch
            
        Returns:
            MatchDataBundle with all historical data
        """
        logger.info(f"Loading data for {home_team_name} vs {away_team_name}")
        
        bundle = MatchDataBundle(
            fixture_id=fixture_id,
            home_team_id=str(home_team_id),
            away_team_id=str(away_team_id),
            home_team_name=home_team_name,
            away_team_name=away_team_name
        )
        
        # 1. Load home team history
        try:
            if hasattr(self.provider, 'get_team_recent_matches'):
                home_matches = self.provider.get_team_recent_matches(
                    team_id=home_team_id,
                    limit=history_limit,
                    before_date=match_date
                )
                bundle.home_history = [
                    self._normalize_match(m, str(home_team_id))
                    for m in home_matches
                ]
                logger.info(f"Loaded {len(bundle.home_history)} home history matches")
            else:
                bundle.errors.append("Provider does not support get_team_recent_matches")
                logger.error("Provider missing get_team_recent_matches method")
        except Exception as e:
            bundle.errors.append(f"Error loading home history: {str(e)}")
            logger.error(f"Error loading home history: {e}")
        
        # 2. Load away team history
        try:
            if hasattr(self.provider, 'get_team_recent_matches'):
                away_matches = self.provider.get_team_recent_matches(
                    team_id=away_team_id,
                    limit=history_limit,
                    before_date=match_date
                )
                bundle.away_history = [
                    self._normalize_match(m, str(away_team_id))
                    for m in away_matches
                ]
                logger.info(f"Loaded {len(bundle.away_history)} away history matches")
            else:
                bundle.errors.append("Provider does not support get_team_recent_matches")
        except Exception as e:
            bundle.errors.append(f"Error loading away history: {str(e)}")
            logger.error(f"Error loading away history: {e}")
        
        # 3. Load H2H
        try:
            if hasattr(self.provider, 'get_head_to_head'):
                h2h_matches = self.provider.get_head_to_head(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    limit=history_limit,
                    before_date=match_date
                )
                bundle.h2h = [
                    self._normalize_match(m, str(home_team_id))
                    for m in h2h_matches
                ]
                logger.info(f"Loaded {len(bundle.h2h)} H2H matches")
            else:
                bundle.warnings.append("Provider does not support get_head_to_head")
        except Exception as e:
            bundle.warnings.append(f"H2H not available: {str(e)}")
            logger.warning(f"Error loading H2H: {e}")
        
        # 4. Load odds (optimisé pour edge calculation)
        try:
            if hasattr(self.provider, 'get_fixture_odds') and fixture_id:
                odds = self.provider.get_fixture_odds(int(fixture_id))
                if odds and odds.markets:
                    bundle.odds_available = True
                    bundle.odds_markets = odds.markets
                    logger.info(f"Loaded odds with {len(odds.markets)} markets")
                else:
                    bundle.odds_available = False
                    bundle.warnings.append("Odds not available for this fixture")
            else:
                bundle.odds_available = False
                bundle.warnings.append("Provider does not support odds")
        except Exception as e:
            bundle.odds_available = False
            bundle.warnings.append(f"Odds not available: {str(e)}")
            logger.warning(f"Error loading odds: {e}")
        
        # Recalculate derived fields
        bundle.__post_init__()
        
        logger.info(f"Data bundle complete: {bundle.history_status}, "
                   f"Home: {bundle.home_history_count}, "
                   f"Away: {bundle.away_history_count}, "
                   f"H2H: {bundle.h2h_count}")
        
        return bundle
    
    def _normalize_match(
        self,
        match: MatchDetails,
        team_id: str
    ) -> NormalizedHistoricalMatch:
        """
        Normalize a MatchDetails to NormalizedHistoricalMatch
        
        Args:
            match: MatchDetails from provider
            team_id: ID of the team we're analyzing (to determine home/away)
            
        Returns:
            NormalizedHistoricalMatch
        """
        # Determine if team is home or away
        is_home = str(match.home_team.id) == str(team_id)
        
        if is_home:
            team_name = match.home_team.name
            opponent_id = str(match.away_team.id)
            opponent_name = match.away_team.name
        else:
            team_name = match.away_team.name
            opponent_id = str(match.home_team.id)
            opponent_name = match.home_team.name
        
        # Extract HT scores
        ht_goals_for = None
        ht_goals_against = None
        ht_total_goals = None
        ht_score_available = False
        
        if match.score_halftime and match.score_halftime.home is not None:
            ht_score_available = True
            if is_home:
                ht_goals_for = match.score_halftime.home
                ht_goals_against = match.score_halftime.away
            else:
                ht_goals_for = match.score_halftime.away
                ht_goals_against = match.score_halftime.home
            ht_total_goals = match.score_halftime.home + match.score_halftime.away
        
        # Extract FT scores
        ft_goals_for = None
        ft_goals_against = None
        ft_total_goals = None
        ft_score_available = False
        
        if match.score_fulltime and match.score_fulltime.home is not None:
            ft_score_available = True
            if is_home:
                ft_goals_for = match.score_fulltime.home
                ft_goals_against = match.score_fulltime.away
            else:
                ft_goals_for = match.score_fulltime.away
                ft_goals_against = match.score_fulltime.home
            ft_total_goals = match.score_fulltime.home + match.score_fulltime.away
        
        return NormalizedHistoricalMatch(
            fixture_id=match.id,
            date=match.match_date,
            team_id=team_id,
            opponent_id=opponent_id,
            team_name=team_name,
            opponent_name=opponent_name,
            is_home=is_home,
            ht_goals_for=ht_goals_for,
            ht_goals_against=ht_goals_against,
            ht_total_goals=ht_total_goals,
            ht_score_available=ht_score_available,
            ft_goals_for=ft_goals_for,
            ft_goals_against=ft_goals_against,
            ft_total_goals=ft_total_goals,
            ft_score_available=ft_score_available,
            status=self._safe_get_status(match.status),
            competition=match.competition.name if match.competition else "",
            season="",  # Can be extracted if needed
            data_origin="REAL"
        )
