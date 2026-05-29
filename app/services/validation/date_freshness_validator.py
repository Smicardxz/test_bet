"""
Date Freshness Validator
Ensures data freshness and date consistency
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FreshnessStatus(str, Enum):
    """Data freshness status"""
    FRESH = "FRESH"
    STALE = "STALE"
    OUTDATED = "OUTDATED"
    UNKNOWN = "UNKNOWN"


@dataclass
class MatchFreshnessInfo:
    """Freshness information for a match"""
    fixture_date_utc: str
    fixture_date_local: str
    is_today: bool
    is_from_real_api: bool
    cache_age_minutes: int
    freshness_status: str
    freshness_warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "fixture_date_utc": self.fixture_date_utc,
            "fixture_date_local": self.fixture_date_local,
            "is_today": self.is_today,
            "is_from_real_api": self.is_from_real_api,
            "cache_age_minutes": self.cache_age_minutes,
            "freshness_status": self.freshness_status,
            "freshness_warnings": self.freshness_warnings
        }


@dataclass
class HistoryFreshnessInfo:
    """Freshness information for match history"""
    history_matches_count: int
    latest_history_match_date: Optional[str]
    oldest_history_match_date: Optional[str]
    history_only_past_matches: bool
    history_excludes_current_fixture: bool
    history_warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "history_matches_count": self.history_matches_count,
            "latest_history_match_date": self.latest_history_match_date,
            "oldest_history_match_date": self.oldest_history_match_date,
            "history_only_past_matches": self.history_only_past_matches,
            "history_excludes_current_fixture": self.history_excludes_current_fixture,
            "history_warnings": self.history_warnings
        }


@dataclass
class GlobalFreshnessReport:
    """Global freshness report"""
    today_local_date: str
    today_utc_date: str
    provider_active: str
    total_fixtures: int
    fixtures_today: int
    fixtures_targeted: int
    fixtures_rejected_not_today: int
    cache_age_minutes: int
    freshness_status: str
    warnings: List[str]
    sample_matches: List[Dict[str, Any]]
    
    def is_ok(self) -> bool:
        """Check if data freshness is OK"""
        return self.freshness_status == FreshnessStatus.FRESH.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "today_local_date": self.today_local_date,
            "today_utc_date": self.today_utc_date,
            "provider_active": self.provider_active,
            "total_fixtures": self.total_fixtures,
            "fixtures_today": self.fixtures_today,
            "fixtures_targeted": self.fixtures_targeted,
            "fixtures_rejected_not_today": self.fixtures_rejected_not_today,
            "cache_age_minutes": self.cache_age_minutes,
            "freshness_status": self.freshness_status,
            "warnings": self.warnings,
            "sample_matches": self.sample_matches
        }


class DateFreshnessValidator:
    """
    Validates data freshness and date consistency
    
    Ensures:
    - Matches are from today
    - Dates are from real API
    - Timezones are correct
    - History only contains past matches
    - Cache is not stale
    """
    
    # Thresholds
    CACHE_WARNING_MINUTES = 60
    CACHE_STALE_MINUTES = 120
    HISTORY_MAX_AGE_DAYS = 365
    
    def __init__(self):
        """Initialize validator"""
        logger.info("DateFreshnessValidator initialized")
    
    def validate_match_freshness(
        self,
        match: Dict[str, Any],
        is_from_real_api: bool = False,
        cache_timestamp: Optional[datetime] = None
    ) -> MatchFreshnessInfo:
        """
        Validate match freshness
        
        Args:
            match: Match data
            is_from_real_api: Whether data is from real API
            cache_timestamp: When data was cached
            
        Returns:
            MatchFreshnessInfo
        """
        warnings = []
        
        # Get match date (handle both dict and Pydantic objects)
        if hasattr(match, 'match_date'):
            kickoff_time = match.match_date
        elif hasattr(match, 'get'):
            kickoff_time = match.get("kickoff_time", "")
        else:
            kickoff_time = getattr(match, 'kickoff_time', None)
        
        if not kickoff_time:
            return self._unknown_freshness("No kickoff time available")
        
        try:
            # Parse kickoff time
            if isinstance(kickoff_time, str):
                match_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
            else:
                match_date = kickoff_time
            
            # Get today's date
            now_utc = datetime.now(timezone.utc)
            today_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_utc = today_utc + timedelta(days=1)
            
            # Check if match is today
            is_today = today_utc <= match_date < tomorrow_utc
            
            # Format dates
            fixture_date_utc = match_date.strftime("%Y-%m-%d %H:%M UTC")
            
            # Convert to local time (assuming UTC+1 for user)
            local_offset = timedelta(hours=1)
            match_date_local = match_date + local_offset
            fixture_date_local = match_date_local.strftime("%Y-%m-%d %H:%M Local")
            
            # Calculate cache age
            if cache_timestamp:
                cache_age = (now_utc - cache_timestamp).total_seconds() / 60
                cache_age_minutes = int(cache_age)
            else:
                cache_age_minutes = 0
            
            # Determine freshness status
            if not is_today:
                freshness_status = FreshnessStatus.OUTDATED
                warnings.append(f"Match is not today (date: {fixture_date_local})")
            elif cache_age_minutes > self.CACHE_STALE_MINUTES:
                freshness_status = FreshnessStatus.STALE
                warnings.append(f"Cache is stale ({cache_age_minutes} minutes old)")
            elif cache_age_minutes > self.CACHE_WARNING_MINUTES:
                freshness_status = FreshnessStatus.FRESH
                warnings.append(f"Cache is aging ({cache_age_minutes} minutes old)")
            else:
                freshness_status = FreshnessStatus.FRESH
            
            # Check if from real API
            if not is_from_real_api:
                warnings.append("Data is from MOCK provider, not real API")
            
            # Check timezone
            if match_date.tzinfo is None:
                warnings.append("Timezone information missing - assuming UTC")
            
            return MatchFreshnessInfo(
                fixture_date_utc=fixture_date_utc,
                fixture_date_local=fixture_date_local,
                is_today=is_today,
                is_from_real_api=is_from_real_api,
                cache_age_minutes=cache_age_minutes,
                freshness_status=freshness_status.value,
                freshness_warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating match freshness: {e}")
            return self._unknown_freshness(f"Error parsing date: {e}")
    
    def validate_history_freshness(
        self,
        history_matches: List[Dict[str, Any]],
        current_fixture_date: Optional[datetime] = None
    ) -> HistoryFreshnessInfo:
        """
        Validate history freshness
        
        Args:
            history_matches: Historical matches
            current_fixture_date: Date of current fixture being analyzed
            
        Returns:
            HistoryFreshnessInfo
        """
        warnings = []
        
        if not history_matches:
            return HistoryFreshnessInfo(
                history_matches_count=0,
                latest_history_match_date=None,
                oldest_history_match_date=None,
                history_only_past_matches=True,
                history_excludes_current_fixture=True,
                history_warnings=["No history matches available"]
            )
        
        # Extract dates
        history_dates = []
        now_utc = datetime.now(timezone.utc)
        
        for match in history_matches:
            match_date_str = match.get("match_date") or match.get("kickoff_time")
            if match_date_str:
                try:
                    if isinstance(match_date_str, str):
                        match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    else:
                        match_date = match_date_str
                    history_dates.append(match_date)
                except:
                    pass
        
        if not history_dates:
            warnings.append("Could not parse any history match dates")
            return HistoryFreshnessInfo(
                history_matches_count=len(history_matches),
                latest_history_match_date=None,
                oldest_history_match_date=None,
                history_only_past_matches=False,
                history_excludes_current_fixture=False,
                history_warnings=warnings
            )
        
        # Sort dates
        history_dates.sort()
        latest_date = history_dates[-1]
        oldest_date = history_dates[0]
        
        # Check if all matches are in the past
        history_only_past = all(d < now_utc for d in history_dates)
        
        if not history_only_past:
            future_count = sum(1 for d in history_dates if d >= now_utc)
            warnings.append(f"History contains {future_count} future matches")
        
        # Check if current fixture is excluded
        history_excludes_current = True
        if current_fixture_date:
            for hist_date in history_dates:
                # Check if any history match is within 1 hour of current fixture
                time_diff = abs((hist_date - current_fixture_date).total_seconds())
                if time_diff < 3600:  # 1 hour
                    history_excludes_current = False
                    warnings.append("History may contain the current fixture being analyzed")
                    break
        
        # Check if history is too old
        oldest_age_days = (now_utc - oldest_date).days
        if oldest_age_days > self.HISTORY_MAX_AGE_DAYS:
            warnings.append(f"Oldest history match is {oldest_age_days} days old")
        
        return HistoryFreshnessInfo(
            history_matches_count=len(history_matches),
            latest_history_match_date=latest_date.strftime("%Y-%m-%d"),
            oldest_history_match_date=oldest_date.strftime("%Y-%m-%d"),
            history_only_past_matches=history_only_past,
            history_excludes_current_fixture=history_excludes_current,
            history_warnings=warnings
        )
    
    def validate_global_freshness(
        self,
        all_matches: List[Dict[str, Any]],
        provider_name: str,
        is_real_data: bool,
        cache_timestamp: Optional[datetime] = None
    ) -> GlobalFreshnessReport:
        """
        Validate global data freshness
        
        Args:
            all_matches: All matches from provider
            provider_name: Provider name
            is_real_data: Whether using real data
            cache_timestamp: When data was cached
            
        Returns:
            GlobalFreshnessReport
        """
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc + timedelta(hours=1)  # UTC+1
        
        today_local_date = now_local.strftime("%Y-%m-%d")
        today_utc_date = now_utc.strftime("%Y-%m-%d")
        
        # Calculate cache age
        if cache_timestamp:
            cache_age = (now_utc - cache_timestamp).total_seconds() / 60
            cache_age_minutes = int(cache_age)
        else:
            cache_age_minutes = 0
        
        # Validate each match
        fixtures_today = 0
        fixtures_rejected = 0
        sample_matches = []
        warnings = []
        
        for match in all_matches[:100]:  # Limit to first 100 for performance
            freshness = self.validate_match_freshness(
                match=match,
                is_from_real_api=is_real_data,
                cache_timestamp=cache_timestamp
            )
            
            if freshness.is_today:
                fixtures_today += 1
                
                # Add to sample (first 10)
                if len(sample_matches) < 10:
                    # Handle both dict and Pydantic objects
                    if hasattr(match, 'home_team'):
                        home_team = match.home_team.name if hasattr(match.home_team, 'name') else str(match.home_team)
                        away_team = match.away_team.name if hasattr(match.away_team, 'name') else str(match.away_team)
                    else:
                        home_team = match.get("home_team", "Unknown")
                        away_team = match.get("away_team", "Unknown")
                    
                    sample_matches.append({
                        "home_team": home_team,
                        "away_team": away_team,
                        "kickoff_local": freshness.fixture_date_local,
                        "freshness": freshness.freshness_status
                    })
            else:
                fixtures_rejected += 1
        
        # Determine global freshness status
        if not is_real_data:
            freshness_status = FreshnessStatus.UNKNOWN
            warnings.append("Using MOCK data - freshness cannot be guaranteed")
        elif cache_age_minutes > self.CACHE_STALE_MINUTES:
            freshness_status = FreshnessStatus.STALE
            warnings.append(f"Cache is stale ({cache_age_minutes} minutes old)")
        elif fixtures_today == 0:
            freshness_status = FreshnessStatus.OUTDATED
            warnings.append("No fixtures found for today")
        else:
            freshness_status = FreshnessStatus.FRESH
        
        if cache_age_minutes > self.CACHE_WARNING_MINUTES:
            warnings.append(f"Cache age: {cache_age_minutes} minutes (consider refresh)")
        
        return GlobalFreshnessReport(
            today_local_date=today_local_date,
            today_utc_date=today_utc_date,
            provider_active=provider_name,
            total_fixtures=len(all_matches),
            fixtures_today=fixtures_today,
            fixtures_targeted=0,  # To be filled by caller
            fixtures_rejected_not_today=fixtures_rejected,
            cache_age_minutes=cache_age_minutes,
            freshness_status=freshness_status.value,
            warnings=warnings,
            sample_matches=sample_matches
        )
    
    def _unknown_freshness(self, reason: str) -> MatchFreshnessInfo:
        """Return unknown freshness info"""
        return MatchFreshnessInfo(
            fixture_date_utc="Unknown",
            fixture_date_local="Unknown",
            is_today=False,
            is_from_real_api=False,
            cache_age_minutes=0,
            freshness_status=FreshnessStatus.UNKNOWN.value,
            freshness_warnings=[reason]
        )
