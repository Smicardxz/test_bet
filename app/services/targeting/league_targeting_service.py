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
    GLOBAL_SCAN = "global_scan"  # MASSIVE SCAN: Include ALL leagues for Layer 1 (no filtering)
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
    """Profile for a competition - Phase 2: League Intelligence Layer"""
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

    # Phase 2: League Intelligence Scores
    league_reliability_score: float = 0.0  # 0-100
    bookmaker_coverage_estimate: float = 0.0  # 0-100
    volatility_profile: str = "UNKNOWN"  # LOW, MEDIUM, HIGH, EXTREME
    scoring_profile: str = "UNKNOWN"  # LOW_SCORING, BALANCED, HIGH_SCORING
    average_goals: float = 0.0
    ht_average_goals: float = 0.0
    btts_rate: float = 0.0
    over_rate: float = 0.0
    under_rate: float = 0.0
    sample_size: int = 0

    # Phase 2: League Category
    league_category: str = "UNCATEGORIZED"  # major_excluded, minor_bettable, obscure_watchlist, volatile_danger, low_data_quality

    # Coverage priority (Bettable Universe)
    coverage_priority: str = "C"          # "A", "B", "C"
    coverage_priority_score: float = 0.0  # 0-100

    # Legacy scoring
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
            # Phase 2: League Intelligence
            "league_reliability_score": self.league_reliability_score,
            "bookmaker_coverage_estimate": self.bookmaker_coverage_estimate,
            "volatility_profile": self.volatility_profile,
            "scoring_profile": self.scoring_profile,
            "average_goals": self.average_goals,
            "ht_average_goals": self.ht_average_goals,
            "btts_rate": self.btts_rate,
            "over_rate": self.over_rate,
            "under_rate": self.under_rate,
            "sample_size": self.sample_size,
            "league_category": self.league_category,
            # Coverage priority
            "coverage_priority":       self.coverage_priority,
            "coverage_priority_score": self.coverage_priority_score,
            # Legacy
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
    
    # MINOR_TOP_TIER countries + PRIORITY_A bettable additions
    MINOR_TOP_TIER_COUNTRIES = {
        # PRIORITY_A: strong bookmaker coverage (added for re-prioritisation)
        "Japan", "South Korea",
        "Finland", "Sweden", "Norway", "Denmark", "Iceland", "Ireland",
        "Poland", "Czech Republic", "Slovakia", "Romania",
        "Croatia", "Serbia", "Slovenia",
        "Brazil", "Argentina", "Chile", "Uruguay",
        "United States", "Canada",
        # existing entries (unchanged)
        "Kazakhstan", "China", "Vietnam", "Ethiopia", "Egypt",
        "Sudan", "Bhutan", "Kyrgyzstan", "Mongolia", "Uzbekistan",
        "Georgia", "Armenia", "Azerbaijan", "Bolivia", "Paraguay",
        "Peru", "Ecuador", "Colombia", "Venezuela",
    }
    
    # Obscure/minor countries (prioritaires)
    OBSCURE_COUNTRIES = {
        "Belarus", "Moldova", "Albania", "Kosovo", "North Macedonia", "Montenegro",
        "Estonia", "Latvia", "Lithuania", "Thailand", "Indonesia", "Malaysia",
        "Philippines", "Myanmar", "Cambodia", "Uruguay", "Honduras", "El Salvador",
        "Guatemala", "Nicaragua", "Panama", "Costa Rica"
    }
    
    # ── Coverage priority sets (Bettable Universe) ──────────────────────────
    PRIORITY_A_COUNTRIES: frozenset = frozenset({
        "Japan", "South Korea", "China",
        "Finland", "Sweden", "Norway", "Denmark", "Iceland", "Ireland",
        "Poland", "Czech Republic", "Slovakia", "Romania",
        "Croatia", "Serbia", "Slovenia",
        "Brazil", "Argentina", "Colombia", "Chile", "Peru",
        "Uruguay", "Paraguay", "Ecuador",
        "United States", "Canada",
        "Israel",
    })

    PRIORITY_B_COUNTRIES: frozenset = frozenset({
        "Ukraine", "Kazakhstan", "Iran", "Iraq",
        "Belarus", "Georgia", "Armenia", "Azerbaijan",
        "Turkey", "Greece", "Cyprus",
        "Australia", "Egypt", "Morocco", "Vietnam",
    })

    PRIORITY_A_LEAGUE_KEYWORDS: frozenset = frozenset({
        "j1", "j2", "j3", "j league",
        "k league",
        "veikkausliiga", "allsvenskan", "eliteserien", "superligaen",
        "urvalsdeild", "league of ireland",
        "ekstraklasa", "fortuna liga", "liga i",
        "hnl", "prva liga",
        "liga betplay", "liga profesional",
        "mls next pro", "usl championship", "canadian premier",
        "serie b", "serie c",
        "primera nacional",
    })

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
        
        # Check if major league - use exact matching to avoid false positives
        comp_normalized = comp_lower.strip()
        profile.is_major_league = any(
            major.lower() == comp_normalized or
            (major.lower() + " " in comp_normalized and not any(suffix in comp_normalized for suffix in [" 2", " 3", " u19", " u20", " u21", " u23", " women", " youth", " reserve", " regional"])) or
            ("world cup" in comp_normalized and "women" in comp_normalized)  # Allow Women's World Cup as major
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

        # Phase 2: Calculate league intelligence scores
        profile.league_reliability_score = self._calculate_reliability_score(profile)
        profile.bookmaker_coverage_estimate = self._calculate_coverage_estimate(profile)
        profile.volatility_profile = self._determine_volatility_profile(profile)
        profile.scoring_profile = self._determine_scoring_profile(profile)
        profile.league_category = self._categorize_league(profile)

        # ── Coverage priority blend (final = 70% statistical + 30% coverage) ─
        _cov_prio, _cov_score = self._calculate_coverage_priority_score(profile)
        profile.coverage_priority       = _cov_prio
        profile.coverage_priority_score = round(_cov_score, 1)
        profile.target_score = round(
            min(100.0, 0.7 * profile.target_score + 0.3 * _cov_score), 2
        )

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
        
        # PHASE 3: MINOR_TOP_TIER countries (prioritaires)
        if profile.country in self.MINOR_TOP_TIER_COUNTRIES:
            if profile.competition_level_estimate == 1:  # Première division
                score += 60
            elif profile.competition_level_estimate <= 2:  # Jusqu'à deuxième division
                score += 50
            else:
                score += 40
        
        # Bonus for obscure countries
        if profile.country in self.OBSCURE_COUNTRIES:
            score += 30
        
        # Penalty for major leagues (sauf si pays mineurs OU obscurs)
        if profile.is_major_league:
            if profile.country in self.MINOR_TOP_TIER_COUNTRIES:
                # Exception: Premier League mais pays mineur = garder
                if "Premier League" in profile.competition_name and profile.country in ["Kazakhstan", "China", "Vietnam", "Ethiopia", "Egypt"]:
                    score += 20  # Garder les premières divisions de pays mineurs
                else:
                    score -= 30  # Réduire pénalité pour pays mineurs
            elif profile.country in self.OBSCURE_COUNTRIES:
                # Exception: Premier League mais pays obscur = garder
                if "Premier League" in profile.competition_name or "Meistriliiga" in profile.competition_name or "Virsliga" in profile.competition_name or "A Lyga" in profile.competition_name:
                    score += 40  # Garder les premières divisions de pays obscures
                else:
                    score -= 20  # Pénalité réduite pour pays obscures
            else:
                score -= 50  # Forte pénalité pour pays majeurs
        
        # Bonus for lower divisions
        if profile.is_lower_league:
            if profile.country in self.MINOR_TOP_TIER_COUNTRIES:
                score += 40  # Bonus augmenté pour pays mineurs
            else:
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

        # GLOBAL_SCAN: Include ALL leagues for Layer 1 massive scan
        if self.target_mode == TargetMode.GLOBAL_SCAN:
            return True

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
            # Pour les pays obscures, permettre les premières divisions
            if profile.is_obscure and profile.target_score >= 80.0:
                return True

            return (
                profile.is_women or
                profile.is_youth or
                profile.is_reserve or
                profile.is_lower_league or
                profile.is_obscure
            ) and not profile.is_major_league

        return True

    def _calculate_coverage_priority_score(self, profile: LeagueProfile):
        """
        Classify a league into PRIORITY_A/B/C and return a coverage score (0-100).

        PRIORITY_A (65-100): bookmaker odds consistently available
        PRIORITY_B (28-55):  partial coverage
        PRIORITY_C (5-12):   minimal / no coverage

        Returns (priority_letter: str, score: float)
        """
        league_n = profile.competition_name.lower()

        is_prio_a = (
            profile.country in self.PRIORITY_A_COUNTRIES
            or any(kw in league_n for kw in self.PRIORITY_A_LEAGUE_KEYWORDS)
        )
        is_prio_b = profile.country in self.PRIORITY_B_COUNTRIES

        if is_prio_a:
            priority = "A"
            if profile.competition_level_estimate == 1:
                base = 92.0
            elif profile.competition_level_estimate == 2:
                base = 80.0
            else:
                base = 66.0
            if profile.is_youth or profile.is_reserve:
                base -= 28.0
        elif is_prio_b:
            priority = "B"
            if profile.competition_level_estimate == 1:
                base = 54.0
            elif profile.competition_level_estimate == 2:
                base = 40.0
            else:
                base = 28.0
            if profile.is_youth or profile.is_reserve:
                base -= 12.0
        else:
            priority = "C"
            base = 10.0
            if profile.is_youth or profile.is_reserve:
                base = 5.0

        return priority, max(0.0, min(100.0, base))

    def _calculate_reliability_score(self, profile: LeagueProfile) -> float:
        """Calculate league reliability score (0-100) based on data quality and consistency"""
        score = 50.0  # Base

        # Major leagues are more reliable
        if profile.is_major_league:
            score += 30
        elif profile.is_lower_league:
            score += 10

        # Obscure countries have lower reliability
        if profile.is_obscure:
            score -= 15

        # Youth/reserve/women leagues have lower reliability
        if profile.is_youth or profile.is_reserve:
            score -= 20
        elif profile.is_women:
            score -= 10

        # Lower divisions have lower reliability
        if profile.competition_level_estimate >= 3:
            score -= 15
        elif profile.competition_level_estimate >= 2:
            score -= 5

        return max(0, min(100, score))

    def _calculate_coverage_estimate(self, profile: LeagueProfile) -> float:
        """Estimate bookmaker coverage (0-100)"""
        score = 50.0  # Base

        # Major leagues have high coverage
        if profile.is_major_league:
            score += 40
        elif profile.is_lower_league:
            score += 15

        # Obscure countries have low coverage
        if profile.is_obscure:
            score -= 30

        # Youth/reserve/women have low coverage
        if profile.is_youth or profile.is_reserve:
            score -= 35
        elif profile.is_women:
            score -= 20

        # Lower divisions have lower coverage
        if profile.competition_level_estimate >= 3:
            score -= 25
        elif profile.competition_level_estimate >= 2:
            score -= 10

        return max(0, min(100, score))

    def _determine_volatility_profile(self, profile: LeagueProfile) -> str:
        """Determine volatility profile based on league characteristics"""
        if profile.is_youth or profile.is_reserve:
            return "HIGH"
        elif profile.is_obscure and profile.competition_level_estimate >= 2:
            return "EXTREME"
        elif profile.is_lower_league:
            return "MEDIUM"
        elif profile.is_major_league:
            return "LOW"
        else:
            return "MEDIUM"

    def _determine_scoring_profile(self, profile: LeagueProfile) -> str:
        """Determine scoring profile based on league characteristics"""
        # This is a heuristic - will be refined with actual data
        if profile.is_youth or profile.is_reserve:
            return "HIGH_SCORING"  # Youth/reserve often high scoring
        elif profile.is_lower_league:
            return "BALANCED"
        elif profile.is_major_league:
            return "BALANCED"
        elif profile.is_obscure:
            return "LOW_SCORING"  # Obscure leagues often defensive
        else:
            return "BALANCED"

    def _categorize_league(self, profile: LeagueProfile) -> str:
        """Categorize league based on intelligence scores"""
        if profile.is_major_league:
            return "major_excluded"
        elif profile.is_obscure and profile.competition_level_estimate >= 2:
            return "obscure_watchlist"
        elif profile.is_youth or profile.is_reserve:
            return "volatile_danger"
        elif profile.competition_level_estimate >= 4:
            return "low_data_quality"
        elif profile.is_lower_league or profile.is_obscure:
            return "minor_bettable"
        else:
            return "minor_bettable"

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
