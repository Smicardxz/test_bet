"""
League Targeting Service
Identifies and scores competitions based on targeting strategy for minor leagues
"""

import logging
from typing import List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TargetMode(str, Enum):
    """Target mode for league filtering"""
    MINOR_ONLY = "minor_only"  # Only minor leagues
    WOMEN_ONLY = "women_only"  # Only women's football
    YOUTH_ONLY = "youth_only"  # Only youth leagues
    RESERVE_ONLY = "reserve_only"  # Only reserve teams
    ALL_MINOR = "all_minor"  # All types of minor leagues
    ALL = "all"  # No filtering


class ReasonTag(str, Enum):
    """Reason tags for targeting"""
    LOWER_DIVISION = "LOWER_DIVISION"
    WOMEN = "WOMEN"
    YOUTH = "YOUTH"
    RESERVE = "RESERVE"
    OBSCURE_COUNTRY = "OBSCURE_COUNTRY"
    LOW_COVERAGE = "LOW_COVERAGE"
    MINOR_MARKET = "MINOR_MARKET"
    EXCLUDED_MAJOR_LEAGUE = "EXCLUDED_MAJOR_LEAGUE"


@dataclass
class LeagueProfile:
    """Profile for a competition"""
    country: str
    competition_name: str
    competition_level_estimate: int  # 1=top division, 2=second, etc.
    
    # Flags
    is_major_league: bool = False
    is_lower_league: bool = False
    is_women: bool = False
    is_youth: bool = False
    is_reserve: bool = False
    is_obscure: bool = False
    
    # Scoring
    target_score: float = 0.0  # 0-100
    reason_tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "country": self.country,
            "competition_name": self.competition_name,
            "competition_level_estimate": self.competition_level_estimate,
            "is_major_league": self.is_major_league,
            "is_lower_league": self.is_lower_league,
            "is_women": self.is_women,
            "is_youth": self.is_youth,
            "is_reserve": self.is_reserve,
            "is_obscure": self.is_obscure,
            "target_score": self.target_score,
            "reason_tags": self.reason_tags
        }


class LeagueTargetingService:
    """
    Service for identifying and scoring leagues based on targeting strategy
    
    Strategy: Focus on minor leagues, obscure competitions, lower divisions,
    women's football, youth leagues, and markets with less coverage.
    """
    
    # Major leagues to exclude or deprioritize
    MAJOR_LEAGUES = {
        "Premier League", "English Premier League", "EPL",
        "La Liga", "Primera División", "Spanish La Liga",
        "Serie A", "Italian Serie A",
        "Bundesliga", "German Bundesliga",
        "Ligue 1", "French Ligue 1",
        "Eredivisie",
        "Primeira Liga", "Portuguese Liga",
        "Champions League", "UEFA Champions League",
        "Europa League", "UEFA Europa League",
        "World Cup", "FIFA World Cup",
        "European Championship", "Euro"
    }
    
    # Major countries (first divisions are excluded)
    MAJOR_COUNTRIES = {
        "England", "Spain", "Italy", "Germany", "France",
        "Portugal", "Netherlands", "Belgium", "Scotland"
    }
    
    # Obscure/minor countries (prioritized)
    OBSCURE_COUNTRIES = {
        "Kazakhstan", "Uzbekistan", "Georgia", "Armenia",
        "Azerbaijan", "Belarus", "Moldova", "Albania",
        "Kosovo", "North Macedonia", "Montenegro",
        "Estonia", "Latvia", "Lithuania",
        "Vietnam", "Thailand", "Indonesia", "Malaysia",
        "Philippines", "Myanmar", "Cambodia",
        "Bolivia", "Paraguay", "Ecuador", "Peru",
        "Venezuela", "Uruguay", "Honduras", "El Salvador",
        "Guatemala", "Nicaragua", "Panama", "Costa Rica"
    }
    
    # Keywords for women's football
    WOMEN_KEYWORDS = {"women", "féminin", "feminine", "frauen", "donne", "vrouwen"}
    
    # Keywords for youth
    YOUTH_KEYWORDS = {"u21", "u19", "u18", "u23", "u20", "u17", "youth", "junior"}
    
    # Keywords for reserve
    RESERVE_KEYWORDS = {"reserve", "reserves", "b team", "ii", "2"}
    
    # Keywords for lower divisions
    LOWER_DIVISION_KEYWORDS = {
        "division 2", "division 3", "division 4", "division 5",
        "national 2", "national 3", "national league",
        "regional", "championship", "league one", "league two",
        "segunda", "tercera", "serie b", "serie c", "serie d",
        "2. bundesliga", "3. liga", "regionalliga"
    }
    
    def __init__(self, target_mode: TargetMode = TargetMode.ALL_MINOR):
        """Initialize targeting service"""
        self.target_mode = target_mode
        logger.info(f"LeagueTargetingService initialized with mode: {target_mode}")
    
    def analyze_competition(
        self,
        competition_name: str,
        country: str
    ) -> LeagueProfile:
        """
        Analyze a competition and create profile
        
        Args:
            competition_name: Name of the competition
            country: Country of the competition
            
        Returns:
            LeagueProfile with scoring and tags
        """
        
        comp_lower = competition_name.lower()
        country_lower = country.lower()
        
        # Initialize profile
        profile = LeagueProfile(
            country=country,
            competition_name=competition_name,
            competition_level_estimate=self._estimate_level(comp_lower)
        )
        
        # Check if major league
        profile.is_major_league = any(
            major.lower() in comp_lower
            for major in self.MAJOR_LEAGUES
        )
        
        # Check if women's
        profile.is_women = any(
            keyword in comp_lower
            for keyword in self.WOMEN_KEYWORDS
        )
        
        # Check if youth
        profile.is_youth = any(
            keyword in comp_lower
            for keyword in self.YOUTH_KEYWORDS
        )
        
        # Check if reserve
        profile.is_reserve = any(
            keyword in comp_lower
            for keyword in self.RESERVE_KEYWORDS
        )
        
        # Check if lower division
        profile.is_lower_league = any(
            keyword in comp_lower
            for keyword in self.LOWER_DIVISION_KEYWORDS
        ) or profile.competition_level_estimate >= 2
        
        # Check if obscure country
        profile.is_obscure = country in self.OBSCURE_COUNTRIES
        
        # Calculate target score and add tags
        profile.target_score = self._calculate_target_score(profile)
        profile.reason_tags = self._get_reason_tags(profile)
        
        return profile
    
    def _estimate_level(self, comp_name: str) -> int:
        """Estimate competition level (1=top, 2=second, etc.)"""
        
        if any(kw in comp_name for kw in ["division 1", "premier", "primera", "serie a", "bundesliga", "ligue 1"]):
            return 1
        elif any(kw in comp_name for kw in ["division 2", "championship", "segunda", "serie b", "2. bundesliga"]):
            return 2
        elif any(kw in comp_name for kw in ["division 3", "league one", "tercera", "serie c", "3. liga"]):
            return 3
        elif any(kw in comp_name for kw in ["division 4", "league two", "serie d"]):
            return 4
        elif any(kw in comp_name for kw in ["division 5", "regional", "national 3"]):
            return 5
        else:
            return 2  # Default to second level
    
    def _calculate_target_score(self, profile: LeagueProfile) -> float:
        """
        Calculate target score (0-100)
        
        Higher score = more aligned with targeting strategy
        """
        
        score = 0.0
        
        # Penalty for major leagues
        if profile.is_major_league:
            score -= 50
        
        # Bonus for lower divisions
        if profile.is_lower_league:
            score += 30
        
        # Bonus for women's football
        if profile.is_women:
            score += 40
        
        # Bonus for youth
        if profile.is_youth:
            score += 35
        
        # Bonus for reserve
        if profile.is_reserve:
            score += 25
        
        # Bonus for obscure country
        if profile.is_obscure:
            score += 45
        
        # Bonus based on division level (higher level = higher score)
        if profile.competition_level_estimate >= 3:
            score += 20
        elif profile.competition_level_estimate >= 2:
            score += 10
        
        # Penalty for major country first division
        if profile.country in self.MAJOR_COUNTRIES and profile.competition_level_estimate == 1:
            score -= 40
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
    
    def _get_reason_tags(self, profile: LeagueProfile) -> List[str]:
        """Get reason tags for targeting"""
        
        tags = []
        
        if profile.is_major_league:
            tags.append(ReasonTag.EXCLUDED_MAJOR_LEAGUE.value)
        
        if profile.is_lower_league:
            tags.append(ReasonTag.LOWER_DIVISION.value)
        
        if profile.is_women:
            tags.append(ReasonTag.WOMEN.value)
        
        if profile.is_youth:
            tags.append(ReasonTag.YOUTH.value)
        
        if profile.is_reserve:
            tags.append(ReasonTag.RESERVE.value)
        
        if profile.is_obscure:
            tags.append(ReasonTag.OBSCURE_COUNTRY.value)
        
        if profile.competition_level_estimate >= 3:
            tags.append(ReasonTag.LOW_COVERAGE.value)
        
        if not profile.is_major_league and (profile.is_obscure or profile.competition_level_estimate >= 2):
            tags.append(ReasonTag.MINOR_MARKET.value)
        
        return tags
    
    def should_include(self, profile: LeagueProfile) -> bool:
        """
        Check if competition should be included based on target mode
        
        Args:
            profile: LeagueProfile to check
            
        Returns:
            True if should be included
        """
        
        if self.target_mode == TargetMode.ALL:
            return True
        
        if self.target_mode == TargetMode.MINOR_ONLY:
            return profile.target_score >= 20 and not profile.is_major_league
        
        if self.target_mode == TargetMode.WOMEN_ONLY:
            return profile.is_women
        
        if self.target_mode == TargetMode.YOUTH_ONLY:
            return profile.is_youth
        
        if self.target_mode == TargetMode.RESERVE_ONLY:
            return profile.is_reserve
        
        if self.target_mode == TargetMode.ALL_MINOR:
            return (
                profile.is_women or
                profile.is_youth or
                profile.is_reserve or
                profile.is_lower_league or
                profile.is_obscure
            ) and not profile.is_major_league
        
        return True
    
    def filter_competitions(
        self,
        competitions: List[Dict[str, str]],
        min_target_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Filter and score competitions
        
        Args:
            competitions: List of dicts with 'name' and 'country'
            min_target_score: Minimum target score to include
            
        Returns:
            List of competitions with profiles
        """
        
        results = []
        
        for comp in competitions:
            name = comp.get("name", "Unknown")
            country = comp.get("country", "Unknown")
            
            profile = self.analyze_competition(name, country)
            
            if self.should_include(profile) and profile.target_score >= min_target_score:
                results.append({
                    **comp,
                    "profile": profile.to_dict()
                })
        
        # Sort by target score (highest first)
        results.sort(key=lambda x: x["profile"]["target_score"], reverse=True)
        
        return results
    
    def get_coverage_summary(
        self,
        competitions: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Get summary of competition coverage
        
        Args:
            competitions: List of competitions
            
        Returns:
            Summary dict
        """
        
        profiles = [
            self.analyze_competition(c.get("name", ""), c.get("country", ""))
            for c in competitions
        ]
        
        return {
            "total_competitions": len(profiles),
            "major_leagues": sum(1 for p in profiles if p.is_major_league),
            "lower_leagues": sum(1 for p in profiles if p.is_lower_league),
            "women": sum(1 for p in profiles if p.is_women),
            "youth": sum(1 for p in profiles if p.is_youth),
            "reserve": sum(1 for p in profiles if p.is_reserve),
            "obscure_countries": sum(1 for p in profiles if p.is_obscure),
            "avg_target_score": sum(p.target_score for p in profiles) / len(profiles) if profiles else 0,
            "high_target": sum(1 for p in profiles if p.target_score >= 50),
            "medium_target": sum(1 for p in profiles if 20 <= p.target_score < 50),
            "low_target": sum(1 for p in profiles if p.target_score < 20)
        }
