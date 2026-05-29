"""
League Targeting Service V2 - Recalibrated
Focus: Bettable minor leagues with bookmaker coverage
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TargetLevel(str, Enum):
    """Target levels based on bettability"""
    BETTABLE_MINOR = "BETTABLE_MINOR"  # Minor but bookmaker coverage likely
    EXTREME_OBSCURE = "EXTREME_OBSCURE"  # Ultra obscure, low bookmaker coverage
    MAJOR_EXCLUDED = "MAJOR_EXCLUDED"  # Major leagues to exclude


class BookmakerCoverageLevel(str, Enum):
    """Estimated bookmaker coverage"""
    HIGH = "HIGH"  # 80-100% - Most bookmakers cover
    MEDIUM = "MEDIUM"  # 50-80% - Some bookmakers cover
    LOW = "LOW"  # 0-50% - Few bookmakers cover


@dataclass
class BookmakerCoverageEstimate:
    """Estimated bookmaker coverage for a league"""
    coverage_score: float  # 0-100
    coverage_level: str
    likely_markets: List[str]
    reasoning: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_score": self.coverage_score,
            "coverage_level": self.coverage_level,
            "likely_markets": self.likely_markets,
            "reasoning": self.reasoning
        }


@dataclass
class LeagueProfile:
    """Enhanced league profile with bookmaker coverage"""
    competition: str
    country: str
    target_level: str
    target_score: float  # 0-100
    
    # Bookmaker coverage
    bookmaker_coverage: BookmakerCoverageEstimate
    
    # Targeting factors
    is_women: bool
    is_youth: bool
    is_reserve: bool
    is_lower_league: bool
    is_obscure_country: bool
    
    # Priority
    priority_score: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "competition": self.competition,
            "country": self.country,
            "target_level": self.target_level,
            "target_score": self.target_score,
            "bookmaker_coverage": self.bookmaker_coverage.to_dict(),
            "is_women": self.is_women,
            "is_youth": self.is_youth,
            "is_reserve": self.is_reserve,
            "is_lower_league": self.is_lower_league,
            "is_obscure_country": self.is_obscure_country,
            "priority_score": self.priority_score
        }


class BookmakerCoverageEstimator:
    """Estimates bookmaker coverage for leagues"""
    
    # High coverage leagues (80-100%)
    HIGH_COVERAGE_LEAGUES = {
        # South America
        "Copa Libertadores", "Copa Sudamericana",
        "Brasileiro Serie B", "Brasileiro Serie C",
        "Primera Division", "Primera B Nacional",  # Argentina
        "Primera A", "Primera B",  # Colombia
        
        # Asia
        "K League 2",  # Korea D2
        "J2 League", "J3 League",  # Japan
        "V.League 1", "V.League 2",  # Vietnam
        
        # Europe Secondary
        "First League",  # Bulgaria
        "Premier League",  # Kazakhstan
        
        # Women Major
        "Women's Super League", "Women's Championship",  # England
        "D1 Féminine",  # France
        "Frauen-Bundesliga",  # Germany
        "Primera División Femenina",  # Spain
        
        # Youth Major
        "U20 Brasileiro", "U20 Paulista",
        "Premier League 2",  # England U23
    }
    
    # Medium coverage leagues (50-80%)
    MEDIUM_COVERAGE_LEAGUES = {
        # Africa
        "Premier League",  # Egypt, Ethiopia, etc.
        "Professional League",
        
        # Asia
        "Division 1", "Division 2",
        
        # Women Secondary
        "Women's League", "Women's Division 1",
        
        # Youth Secondary
        "U19 League", "U20 League",
        
        # Reserves Known
        "Reserve League", "Premier League 2",
    }
    
    # Low coverage leagues (0-50%)
    LOW_COVERAGE_LEAGUES = {
        "Liga 3", "Esiliiga B", "Esiliiga A",
        "Regional", "Amateur", "District",
    }
    
    # Priority countries (better bookmaker coverage)
    PRIORITY_COUNTRIES = {
        # South America
        "Brazil", "Argentina", "Colombia", "Chile", "Uruguay", "Paraguay",
        "Ecuador", "Peru", "Bolivia", "Venezuela",
        
        # Asia
        "Kazakhstan", "Vietnam", "South Korea", "Japan", "China",
        "Thailand", "Malaysia", "Indonesia",
        
        # Africa
        "Egypt", "South Africa", "Morocco", "Tunisia", "Algeria",
        "Nigeria", "Ghana", "Ethiopia",
        
        # Europe East
        "Bulgaria", "Romania", "Serbia", "Croatia", "Slovenia",
        "Czech Republic", "Slovakia", "Hungary", "Poland",
    }
    
    def estimate_coverage(
        self,
        competition: str,
        country: str,
        is_women: bool = False,
        is_youth: bool = False,
        is_reserve: bool = False
    ) -> BookmakerCoverageEstimate:
        """Estimate bookmaker coverage for a league"""
        
        coverage_score = 0.0
        likely_markets = []
        reasoning = []
        
        # Check league name
        comp_lower = competition.lower()
        
        # High coverage leagues
        if any(league.lower() in comp_lower for league in self.HIGH_COVERAGE_LEAGUES):
            coverage_score += 60
            likely_markets.extend(["HT Under/Over", "FT Under/Over", "BTTS", "High Lines"])
            reasoning.append("Known high-coverage league")
        
        # Medium coverage leagues
        elif any(league.lower() in comp_lower for league in self.MEDIUM_COVERAGE_LEAGUES):
            coverage_score += 40
            likely_markets.extend(["FT Under/Over", "BTTS"])
            reasoning.append("Medium-coverage league")
        
        # Low coverage leagues
        elif any(league.lower() in comp_lower for league in self.LOW_COVERAGE_LEAGUES):
            coverage_score += 10
            reasoning.append("Low-coverage league")
        
        # Country priority
        if country in self.PRIORITY_COUNTRIES:
            coverage_score += 20
            reasoning.append(f"{country} has good bookmaker coverage")
        
        # Women leagues
        if is_women:
            if "super league" in comp_lower or "bundesliga" in comp_lower:
                coverage_score += 15
                likely_markets.append("Women Major Markets")
                reasoning.append("Major women's league")
            else:
                coverage_score += 5
                reasoning.append("Women's league (limited markets)")
        
        # Youth leagues
        if is_youth:
            if "brasileiro" in comp_lower or "premier league" in comp_lower:
                coverage_score += 10
                reasoning.append("Major youth league")
            else:
                coverage_score += 3
                reasoning.append("Youth league (very limited markets)")
        
        # Reserve leagues
        if is_reserve:
            coverage_score += 5
            reasoning.append("Reserve league (limited markets)")
        
        # Copa competitions (major international)
        if "libertadores" in comp_lower or "sudamericana" in comp_lower:
            coverage_score += 25
            likely_markets.append("Major Cup Markets")
            reasoning.append("Major international cup")
        elif "copa" in comp_lower or "cup" in comp_lower:
            coverage_score += 15
            likely_markets.append("Cup Markets")
            reasoning.append("Cup competition")
        
        # Cap at 100
        coverage_score = min(100, coverage_score)
        
        # Determine level
        if coverage_score >= 80:
            coverage_level = BookmakerCoverageLevel.HIGH
        elif coverage_score >= 50:
            coverage_level = BookmakerCoverageLevel.MEDIUM
        else:
            coverage_level = BookmakerCoverageLevel.LOW
        
        return BookmakerCoverageEstimate(
            coverage_score=coverage_score,
            coverage_level=coverage_level.value,
            likely_markets=likely_markets,
            reasoning=reasoning
        )


class LeagueTargetingServiceV2:
    """
    Recalibrated league targeting
    Focus: Bettable minor leagues with statistical edge potential
    """
    
    def __init__(self, include_extreme_obscure: bool = False):
        """
        Initialize targeting service
        
        Args:
            include_extreme_obscure: Whether to include extreme obscure leagues
        """
        self.include_extreme_obscure = include_extreme_obscure
        self.coverage_estimator = BookmakerCoverageEstimator()
        logger.info(f"LeagueTargetingServiceV2 initialized (extreme_obscure={include_extreme_obscure})")
    
    def analyze_league(
        self,
        competition: str,
        country: str
    ) -> LeagueProfile:
        """
        Analyze a league and determine targeting
        
        Args:
            competition: Competition name
            country: Country name
            
        Returns:
            LeagueProfile with targeting info
        """
        
        comp_lower = competition.lower()
        country_lower = country.lower()
        
        # Detect league type
        is_women = self._is_women(comp_lower)
        is_youth = self._is_youth(comp_lower)
        is_reserve = self._is_reserve(comp_lower)
        is_lower_league = self._is_lower_league(comp_lower)
        is_obscure_country = self._is_obscure_country(country)
        
        # Estimate bookmaker coverage
        bookmaker_coverage = self.coverage_estimator.estimate_coverage(
            competition=competition,
            country=country,
            is_women=is_women,
            is_youth=is_youth,
            is_reserve=is_reserve
        )
        
        # Determine target level
        target_level = self._determine_target_level(
            competition=competition,
            country=country,
            comp_lower=comp_lower,
            bookmaker_coverage=bookmaker_coverage
        )
        
        # Calculate priority score
        priority_score = self._calculate_priority_score(
            target_level=target_level,
            bookmaker_coverage=bookmaker_coverage,
            is_women=is_women,
            is_youth=is_youth,
            country=country
        )
        
        # Calculate target score (0-100)
        target_score = self._calculate_target_score(
            priority_score=priority_score,
            bookmaker_coverage=bookmaker_coverage,
            target_level=target_level
        )
        
        return LeagueProfile(
            competition=competition,
            country=country,
            target_level=target_level.value,
            target_score=target_score,
            bookmaker_coverage=bookmaker_coverage,
            is_women=is_women,
            is_youth=is_youth,
            is_reserve=is_reserve,
            is_lower_league=is_lower_league,
            is_obscure_country=is_obscure_country,
            priority_score=priority_score
        )
    
    def should_include(self, profile: LeagueProfile) -> bool:
        """Determine if league should be included"""
        
        # Exclude major leagues
        if profile.target_level == TargetLevel.MAJOR_EXCLUDED.value:
            return False
        
        # Exclude extreme obscure if not enabled
        if profile.target_level == TargetLevel.EXTREME_OBSCURE.value:
            if not self.include_extreme_obscure:
                return False
        
        # Include if target score >= 50
        return profile.target_score >= 50
    
    def _determine_target_level(
        self,
        competition: str,
        country: str,
        comp_lower: str,
        bookmaker_coverage: BookmakerCoverageEstimate
    ) -> TargetLevel:
        """Determine target level"""
        
        # Major leagues to exclude
        major_keywords = [
            "premier league", "la liga", "serie a", "bundesliga",
            "ligue 1", "eredivisie", "primeira liga",
            "championship"  # England only
        ]
        
        # Check if major league
        if country in ["England", "Spain", "Italy", "Germany", "France", "Netherlands", "Portugal"]:
            if any(keyword in comp_lower for keyword in major_keywords):
                return TargetLevel.MAJOR_EXCLUDED
        
        # Extreme obscure leagues
        extreme_obscure_keywords = [
            "liga 3", "esiliiga b", "esiliiga a",
            "regional", "amateur", "district"
        ]
        
        if any(keyword in comp_lower for keyword in extreme_obscure_keywords):
            return TargetLevel.EXTREME_OBSCURE
        
        # Low bookmaker coverage = extreme obscure
        if bookmaker_coverage.coverage_score < 30:
            return TargetLevel.EXTREME_OBSCURE
        
        # Default: bettable minor
        return TargetLevel.BETTABLE_MINOR
    
    def _calculate_priority_score(
        self,
        target_level: TargetLevel,
        bookmaker_coverage: BookmakerCoverageEstimate,
        is_women: bool,
        is_youth: bool,
        country: str
    ) -> float:
        """Calculate priority score"""
        
        score = 0.0
        
        # Target level base score
        if target_level == TargetLevel.BETTABLE_MINOR:
            score += 60
        elif target_level == TargetLevel.EXTREME_OBSCURE:
            score += 20
        
        # Bookmaker coverage
        score += bookmaker_coverage.coverage_score * 0.3
        
        # Women/Youth bonus
        if is_women:
            score += 10
        if is_youth:
            score += 5
        
        # Priority countries
        if country in self.coverage_estimator.PRIORITY_COUNTRIES:
            score += 15
        
        return min(100, score)
    
    def _calculate_target_score(
        self,
        priority_score: float,
        bookmaker_coverage: BookmakerCoverageEstimate,
        target_level: TargetLevel
    ) -> float:
        """Calculate final target score"""
        
        # Weighted combination
        score = (priority_score * 0.6) + (bookmaker_coverage.coverage_score * 0.4)
        
        # Penalty for extreme obscure
        if target_level == TargetLevel.EXTREME_OBSCURE:
            score *= 0.7
        
        return min(100, score)
    
    def _is_women(self, comp_lower: str) -> bool:
        """Check if women's league"""
        keywords = ["women", "femenina", "féminine", "frauen", "feminino"]
        return any(k in comp_lower for k in keywords)
    
    def _is_youth(self, comp_lower: str) -> bool:
        """Check if youth league"""
        keywords = ["u19", "u20", "u21", "u23", "youth", "junior", "sub-"]
        return any(k in comp_lower for k in keywords)
    
    def _is_reserve(self, comp_lower: str) -> bool:
        """Check if reserve league"""
        keywords = ["reserve", "ii", "b team", "promesas"]
        return any(k in comp_lower for k in keywords)
    
    def _is_lower_league(self, comp_lower: str) -> bool:
        """Check if lower league"""
        keywords = [
            "serie b", "serie c", "division 2", "segunda",
            "league 2", "league one", "championship"
        ]
        return any(k in comp_lower for k in keywords)
    
    def _is_obscure_country(self, country: str) -> bool:
        """Check if obscure country"""
        # Countries NOT in major or priority lists
        major_countries = {
            "England", "Spain", "Italy", "Germany", "France",
            "Netherlands", "Portugal", "Belgium", "Turkey"
        }
        
        return country not in major_countries and country not in self.coverage_estimator.PRIORITY_COUNTRIES
