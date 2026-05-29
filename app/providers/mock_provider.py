"""
Mock Data Provider
For testing and development without external API calls
"""

from typing import List, Optional
from datetime import datetime, date, timedelta
from app.providers.base_provider import BaseDataProvider, ProviderConfig, ProviderResponse
from app.providers.models import (
    MatchDetails,
    TeamInfo,
    CompetitionInfo,
    MatchScore,
    MatchStatus,
    TeamStats,
    HeadToHead,
    MatchOdds
)


class MockDataProvider(BaseDataProvider):
    """
    Mock provider with realistic synthetic data
    Useful for testing without external dependencies
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        """Initialize mock provider"""
        if config is None:
            config = ProviderConfig(
                name="mock",
                enabled=True,
                cache_enabled=False  # No need to cache mock data
            )
        
        super().__init__(config)
        
        # Generate mock data
        self._generate_mock_data()
    
    def _generate_mock_data(self):
        """Generate realistic mock data"""
        
        # Mock competitions
        self.competitions = {
            "eng_women_champ": CompetitionInfo(
                id="eng_women_champ",
                name="England Women's Championship",
                country="England",
                tier=2,
                is_obscure=True
            ),
            "eng_u21": CompetitionInfo(
                id="eng_u21",
                name="England U21 Premier League",
                country="England",
                tier=3,
                is_obscure=True
            ),
            "eng_national_north": CompetitionInfo(
                id="eng_national_north",
                name="England National League North",
                country="England",
                tier=6,
                is_obscure=True
            ),
            "fra_national_3": CompetitionInfo(
                id="fra_national_3",
                name="France National 3",
                country="France",
                tier=5,
                is_obscure=True
            )
        }
        
        # Mock teams
        self.teams = {
            "london_city": TeamInfo(
                id="london_city",
                name="London City Lionesses",
                short_name="London City",
                country="England"
            ),
            "bristol_city": TeamInfo(
                id="bristol_city",
                name="Bristol City Women",
                short_name="Bristol City",
                country="England"
            ),
            "man_utd_u21": TeamInfo(
                id="man_utd_u21",
                name="Manchester United U21",
                short_name="Man Utd U21",
                country="England"
            ),
            "liverpool_u21": TeamInfo(
                id="liverpool_u21",
                name="Liverpool U21",
                short_name="Liverpool U21",
                country="England"
            ),
            "curzon_ashton": TeamInfo(
                id="curzon_ashton",
                name="Curzon Ashton",
                short_name="Curzon",
                country="England"
            ),
            "brackley_town": TeamInfo(
                id="brackley_town",
                name="Brackley Town",
                short_name="Brackley",
                country="England"
            ),
            "granville": TeamInfo(
                id="granville",
                name="Granville",
                short_name="Granville",
                country="France"
            ),
            "vitre": TeamInfo(
                id="vitre",
                name="Vitré",
                short_name="Vitré",
                country="France"
            )
        }
        
        # Mock today's matches
        today = datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)
        
        self.matches = {
            "match_001": MatchDetails(
                id="match_001",
                home_team=self.teams["london_city"],
                away_team=self.teams["bristol_city"],
                competition=self.competitions["eng_women_champ"],
                match_date=today,
                status=MatchStatus.SCHEDULED,
                provider="mock"
            ),
            "match_002": MatchDetails(
                id="match_002",
                home_team=self.teams["man_utd_u21"],
                away_team=self.teams["liverpool_u21"],
                competition=self.competitions["eng_u21"],
                match_date=today + timedelta(hours=2),
                status=MatchStatus.SCHEDULED,
                provider="mock"
            ),
            "match_003": MatchDetails(
                id="match_003",
                home_team=self.teams["curzon_ashton"],
                away_team=self.teams["brackley_town"],
                competition=self.competitions["eng_national_north"],
                match_date=today + timedelta(hours=1),
                status=MatchStatus.SCHEDULED,
                provider="mock"
            ),
            "match_004": MatchDetails(
                id="match_004",
                home_team=self.teams["granville"],
                away_team=self.teams["vitre"],
                competition=self.competitions["fra_national_3"],
                match_date=today + timedelta(hours=3),
                status=MatchStatus.SCHEDULED,
                provider="mock"
            )
        }
        
        # Mock odds
        self.odds = {
            "match_001": [
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="ht_under_05",
                    line=0.5,
                    under_odds=2.50,
                    over_odds=1.55
                ),
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="ft_under_25",
                    line=2.5,
                    under_odds=2.30,
                    over_odds=1.65
                ),
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="btts",
                    yes_odds=2.20,
                    no_odds=1.70
                )
            ],
            "match_002": [
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="ft_over_25",
                    line=2.5,
                    over_odds=2.00,
                    under_odds=1.85
                ),
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="btts",
                    yes_odds=1.80,
                    no_odds=2.05
                )
            ],
            "match_003": [
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="ft_under_105",
                    line=10.5,
                    under_odds=1.50,
                    over_odds=2.70
                ),
                MatchOdds(
                    bookmaker="Mock Bookmaker",
                    market_type="ft_under_25",
                    line=2.5,
                    under_odds=2.10,
                    over_odds=1.75
                )
            ]
        }
    
    def get_today_matches(
        self,
        competition_ids: Optional[List[str]] = None
    ) -> ProviderResponse:
        """Get today's matches"""
        
        self.logger.info("Fetching today's matches from mock provider")
        
        matches = list(self.matches.values())
        
        # Filter by competition if specified
        if competition_ids:
            matches = [
                m for m in matches
                if m.competition.id in competition_ids
            ]
        
        return self._create_success_response(matches)
    
    def get_match_details(self, match_id: str) -> ProviderResponse:
        """Get match details"""
        
        self.logger.info(f"Fetching match details for {match_id}")
        
        if match_id not in self.matches:
            return self._create_error_response(f"Match {match_id} not found")
        
        return self._create_success_response(self.matches[match_id])
    
    def get_team_recent_matches(
        self,
        team_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get team recent matches"""
        
        self.logger.info(f"Fetching recent matches for team {team_id}")
        
        if team_id not in self.teams:
            return self._create_error_response(f"Team {team_id} not found")
        
        # Generate mock recent matches
        team = self.teams[team_id]
        recent_matches = []
        
        for i in range(min(limit, 10)):
            days_ago = (i + 1) * 7  # Weekly matches
            match_date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Alternate home/away
            is_home = i % 2 == 0
            
            mock_match = MatchDetails(
                id=f"hist_{team_id}_{i}",
                home_team=team if is_home else self.teams["bristol_city"],
                away_team=self.teams["bristol_city"] if is_home else team,
                competition=self.competitions["eng_women_champ"],
                match_date=match_date,
                status=MatchStatus.FINISHED,
                score_fulltime=MatchScore(home=1, away=0) if is_home else MatchScore(home=0, away=1),
                score_halftime=MatchScore(home=0, away=0),
                provider="mock"
            )
            
            recent_matches.append(mock_match)
        
        return self._create_success_response(recent_matches)
    
    def get_head_to_head(
        self,
        team_a_id: str,
        team_b_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get head-to-head"""
        
        self.logger.info(f"Fetching H2H for {team_a_id} vs {team_b_id}")
        
        if team_a_id not in self.teams or team_b_id not in self.teams:
            return self._create_error_response("Team not found")
        
        team_a = self.teams[team_a_id]
        team_b = self.teams[team_b_id]
        
        # Generate mock H2H
        h2h = HeadToHead(
            team_a=team_a,
            team_b=team_b,
            total_matches=5,
            team_a_wins=2,
            team_b_wins=2,
            draws=1,
            recent_matches=[],
            provider="mock"
        )
        
        return self._create_success_response(h2h)
    
    def get_competition_matches(
        self,
        competition_id: str,
        match_date: Optional[date] = None
    ) -> ProviderResponse:
        """Get competition matches"""
        
        self.logger.info(f"Fetching matches for competition {competition_id}")
        
        if competition_id not in self.competitions:
            return self._create_error_response(f"Competition {competition_id} not found")
        
        # Filter matches by competition
        matches = [
            m for m in self.matches.values()
            if m.competition.id == competition_id
        ]
        
        # Filter by date if specified
        if match_date:
            matches = [
                m for m in matches
                if m.match_date.date() == match_date
            ]
        
        return self._create_success_response(matches)
    
    def get_odds(self, match_id: str) -> ProviderResponse:
        """Get match odds"""
        
        self.logger.info(f"Fetching odds for match {match_id}")
        
        if match_id not in self.odds:
            return self._create_error_response(f"No odds available for match {match_id}")
        
        return self._create_success_response(self.odds[match_id])
