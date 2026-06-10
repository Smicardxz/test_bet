"""
event_detector.py
==================
Event context detection for international tournaments and friendlies.

Detects:
- DOMESTIC_LEAGUE
- INTERNATIONAL_FRIENDLY
- WORLD_CUP
- CONTINENTAL_TOURNAMENT
- YOUTH_TOURNAMENT
- UNKNOWN_EVENT

Usage:
    from app.services.events.event_detector import EventDetector, EventContext
    
    detector = EventDetector()
    context = detector.detect_event(match)
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class EventContext(Enum):
    """Event context types."""
    DOMESTIC_LEAGUE = "DOMESTIC_LEAGUE"
    INTERNATIONAL_FRIENDLY = "INTERNATIONAL_FRIENDLY"
    WORLD_CUP = "WORLD_CUP"
    CONTINENTAL_TOURNAMENT = "CONTINENTAL_TOURNAMENT"
    YOUTH_TOURNAMENT = "YOUTH_TOURNAMENT"
    UNKNOWN_EVENT = "UNKNOWN_EVENT"


class EventPhase(Enum):
    """Event phases for tournaments."""
    QUALIFICATION = "qualification"
    GROUP_STAGE = "group_stage"
    KNOCKOUT_ROUND = "knockout_round"
    SEMI_FINAL = "semi_final"
    FINAL = "final"
    WARMUP = "warmup"
    UNKNOWN_PHASE = "unknown_phase"


class EventDetector:
    """
    Detects event context from match metadata.
    
    Uses league name, competition name, country, and date window to classify matches.
    """
    
    # World Cup keywords
    WORLD_CUP_KEYWORDS = [
        "world cup", "fifa world cup", "worldcup",
        "copa mundo", "copa do mundo"
    ]
    
    # Continental tournament keywords
    CONTINENTAL_TOURNAMENT_KEYWORDS = [
        "euro", "european championship", "uefa euro",
        "copa america", "africa cup of nations", "afcon",
        "asian cup", "afc asian cup",
        "concacaf gold cup", "gold cup",
        "nations league", "uefa nations league"
    ]
    
    # Youth tournament keywords
    YOUTH_TOURNAMENT_KEYWORDS = [
        "u20", "u21", "u19", "u17", "under-20", "under-21", "under-19", "under-17",
        "youth", "junior", "u-20", "u-21", "u-19", "u-17"
    ]
    
    # Friendly keywords
    FRIENDLY_KEYWORDS = [
        "friendly", "friendlies", "international friendly"
    ]
    
    # Domestic league indicators (these are NOT events)
    DOMESTIC_LEAGUE_INDICATORS = [
        "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
        "eredivisie", "primeira liga", "scottish premiership",
        "championship", "segunda", "serie b", "2. bundesliga",
        "ligue 2", "eredivisie", "jupiler pro league",
        "super lig", "superliga", "premiership"
    ]
    
    def __init__(self):
        """Initialize event detector."""
        pass
    
    def detect_event(self, match: Any) -> Dict[str, Any]:
        """
        Detect event context from match metadata.
        
        Args:
            match: Match object with league, competition, country, date fields
            
        Returns:
            Dict with event_context, event_name, is_event_match, event_phase
        """
        # Extract match metadata
        league_name = self._extract_league_name(match)
        competition_name = self._extract_competition_name(match)
        country = self._extract_country(match)
        match_date = self._extract_date(match)
        
        # Detect event context
        event_context = self._classify_event(
            league_name, competition_name, country, match_date
        )
        
        # Determine if it's an event match
        is_event_match = event_context != EventContext.DOMESTIC_LEAGUE
        
        # Extract event name
        event_name = self._extract_event_name(
            league_name, competition_name, event_context
        )
        
        # Detect event phase
        event_phase = self._detect_event_phase(
            league_name, competition_name, event_context, match_date
        )
        
        return {
            "event_context": event_context.value,
            "event_name": event_name,
            "is_event_match": is_event_match,
            "event_phase": event_phase.value
        }
    
    def _extract_league_name(self, match: Any) -> str:
        """Extract league name from match."""
        if hasattr(match, "league"):
            league = match.league
            if hasattr(league, "name"):
                return league.name.lower()
            if isinstance(league, str):
                return league.lower()
        if hasattr(match, "league_name"):
            return str(match.league_name).lower()
        if hasattr(match, "competition"):
            competition = match.competition
            if hasattr(competition, "name"):
                return competition.name.lower()
            if isinstance(competition, str):
                return competition.lower()
        return ""
    
    def _extract_competition_name(self, match: Any) -> str:
        """Extract competition name from match."""
        if hasattr(match, "competition"):
            competition = match.competition
            if hasattr(competition, "name"):
                return competition.name.lower()
            if isinstance(competition, str):
                return competition.lower()
        return ""
    
    def _extract_country(self, match: Any) -> str:
        """Extract country from match."""
        if hasattr(match, "country"):
            return str(match.country).lower()
        if hasattr(match, "league"):
            league = match.league
            if hasattr(league, "country"):
                return str(league.country).lower()
        return ""
    
    def _extract_date(self, match: Any) -> Optional[datetime]:
        """Extract date from match."""
        if hasattr(match, "date"):
            try:
                if isinstance(match.date, datetime):
                    return match.date
                if isinstance(match.date, str):
                    return datetime.fromisoformat(match.date)
            except Exception:
                pass
        if hasattr(match, "fixture_date"):
            try:
                if isinstance(match.fixture_date, datetime):
                    return match.fixture_date
                if isinstance(match.fixture_date, str):
                    return datetime.fromisoformat(match.fixture_date)
            except Exception:
                pass
        return None
    
    def _classify_event(
        self, league_name: str, competition_name: str, country: str, match_date: Optional[datetime]
    ) -> EventContext:
        """
        Classify event context from metadata.
        
        Priority:
        1. World Cup
        2. Continental Tournament
        3. Youth Tournament
        4. International Friendly
        5. Domestic League
        6. Unknown
        """
        combined_text = f"{league_name} {competition_name}".lower()
        
        # Check for World Cup
        if any(kw in combined_text for kw in self.WORLD_CUP_KEYWORDS):
            return EventContext.WORLD_CUP
        
        # Check for Continental Tournament
        if any(kw in combined_text for kw in self.CONTINENTAL_TOURNAMENT_KEYWORDS):
            return EventContext.CONTINENTAL_TOURNAMENT
        
        # Check for Youth Tournament
        if any(kw in combined_text for kw in self.YOUTH_TOURNAMENT_KEYWORDS):
            return EventContext.YOUTH_TOURNAMENT
        
        # Check for Friendly
        if any(kw in combined_text for kw in self.FRIENDLY_KEYWORDS):
            return EventContext.INTERNATIONAL_FRIENDLY
        
        # Check for Domestic League indicators
        if any(kw in combined_text for kw in self.DOMESTIC_LEAGUE_INDICATORS):
            return EventContext.DOMESTIC_LEAGUE
        
        # If it's international (world) but not classified above, treat as friendly
        if "world" in country or "international" in combined_text:
            return EventContext.INTERNATIONAL_FRIENDLY
        
        # Default to domestic league if no indicators
        return EventContext.DOMESTIC_LEAGUE
    
    def _extract_event_name(
        self, league_name: str, competition_name: str, event_context: EventContext
    ) -> str:
        """Extract human-readable event name."""
        if event_context == EventContext.DOMESTIC_LEAGUE:
            return league_name or competition_name or "Domestic League"
        
        if event_context == EventContext.INTERNATIONAL_FRIENDLY:
            return "International Friendlies"
        
        if event_context == EventContext.WORLD_CUP:
            return "FIFA World Cup 2026"
        
        if event_context == EventContext.CONTINENTAL_TOURNAMENT:
            # Try to extract specific tournament name
            if "euro" in competition_name or "european" in competition_name:
                return "UEFA European Championship"
            if "copa america" in competition_name:
                return "Copa América"
            if "afcon" in competition_name or "africa cup" in competition_name:
                return "Africa Cup of Nations"
            if "asian cup" in competition_name:
                return "AFC Asian Cup"
            if "gold cup" in competition_name:
                return "CONCACAF Gold Cup"
            if "nations league" in competition_name:
                return "UEFA Nations League"
            return competition_name or "Continental Tournament"
        
        if event_context == EventContext.YOUTH_TOURNAMENT:
            return competition_name or "Youth Tournament"
        
        return competition_name or league_name or "Unknown Event"
    
    def _detect_event_phase(
        self, league_name: str, competition_name: str, event_context: EventContext, match_date: Optional[datetime]
    ) -> EventPhase:
        """Detect event phase (group stage, knockout, etc.)."""
        combined_text = f"{league_name} {competition_name}".lower()
        
        if event_context == EventContext.DOMESTIC_LEAGUE:
            return EventPhase.UNKNOWN_PHASE
        
        if event_context == EventContext.INTERNATIONAL_FRIENDLY:
            return EventPhase.WARMUP
        
        # Check for phase keywords
        if "qualification" in combined_text or "qualifier" in combined_text or "qualifying" in combined_text:
            return EventPhase.QUALIFICATION
        
        if "group" in combined_text:
            return EventPhase.GROUP_STAGE
        
        if "final" in combined_text:
            return EventPhase.FINAL
        
        if "semi" in combined_text:
            return EventPhase.SEMI_FINAL
        
        if "knockout" in combined_text or "round of" in combined_text:
            return EventPhase.KNOCKOUT_ROUND
        
        # For World Cup, use date-based detection (June-July 2026)
        if event_context == EventContext.WORLD_CUP and match_date:
            if match_date.month in (6, 7) and match_date.year == 2026:
                return EventPhase.GROUP_STAGE  # Default to group stage for World Cup
        
        return EventPhase.UNKNOWN_PHASE


# Singleton instance
_detector_instance: Optional[EventDetector] = None


def get_detector() -> EventDetector:
    """Get singleton event detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EventDetector()
    return _detector_instance
