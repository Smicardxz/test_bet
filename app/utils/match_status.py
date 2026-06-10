"""
Match Status Utilities
Handles match status classification (Upcoming, Live, Finished)
"""

from enum import Enum
from typing import Dict, Any
from datetime import datetime, timezone


class MatchStatus(str, Enum):
    """Match status categories"""
    UPCOMING = "UPCOMING"  # Not started yet
    LIVE = "LIVE"  # Currently playing
    FINISHED = "FINISHED"  # Completed
    UNKNOWN = "UNKNOWN"  # Status unclear


class MatchStatusHelper:
    """Helper for match status classification"""
    
    # API-Football status codes
    UPCOMING_STATUSES = {
        "TBD",        # Time to be defined
        "NS",         # Not started
        "SCHEDULED",  # API-Football scheduled (= NS equivalent)
        "SUSP",       # Suspended (upcoming)
        "PST",        # Postponed
        "CANC",       # Cancelled
        "ABD",        # Abandoned (before start)
    }
    
    LIVE_STATUSES = {
        "1H",      # First half
        "HT",      # Halftime
        "2H",      # Second half
        "ET",      # Extra time
        "BT",      # Break time (extra time)
        "P",       # Penalty shootout
        "LIVE",    # Generic live
        "IN_PLAY", # API-Football live
        "PAUSED",  # Paused
        "INT",     # Interrupted
    }
    
    FINISHED_STATUSES = {
        "FT",   # Full time
        "AET",  # After extra time
        "PEN",  # Penalties finished
        "AWD",  # Awarded (walkover)
        "WO",   # Walkover
    }
    
    @classmethod
    def classify_status(cls, api_status: str) -> MatchStatus:
        """
        Classify match status
        
        Args:
            api_status: Status from API (e.g., "NS", "1H", "FT")
            
        Returns:
            MatchStatus enum
        """
        if not api_status:
            return MatchStatus.UNKNOWN
        
        status_upper = api_status.upper()
        
        if status_upper in cls.UPCOMING_STATUSES:
            return MatchStatus.UPCOMING
        elif status_upper in cls.LIVE_STATUSES:
            return MatchStatus.LIVE
        elif status_upper in cls.FINISHED_STATUSES:
            return MatchStatus.FINISHED
        else:
            return MatchStatus.UNKNOWN
    
    @classmethod
    def get_status_badge(cls, status: MatchStatus) -> Dict[str, str]:
        """
        Get badge info for status
        
        Args:
            status: MatchStatus enum
            
        Returns:
            Dict with badge text and color
        """
        if status == MatchStatus.UPCOMING:
            return {
                "text": "⏰ UPCOMING",
                "color": "#3498db",  # Blue
                "bg_color": "#e3f2fd"
            }
        elif status == MatchStatus.LIVE:
            return {
                "text": "🔴 LIVE",
                "color": "#e74c3c",  # Red
                "bg_color": "#ffebee"
            }
        elif status == MatchStatus.FINISHED:
            return {
                "text": "✅ FINISHED",
                "color": "#95a5a6",  # Gray
                "bg_color": "#f5f5f5"
            }
        else:
            return {
                "text": "❓ UNKNOWN",
                "color": "#95a5a6",
                "bg_color": "#f5f5f5"
            }
    
    @classmethod
    def get_display_info(cls, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete display info for a match
        
        Args:
            match_data: Match data dict
            
        Returns:
            Dict with status, badge, time info
        """
        api_status = match_data.get("status", "NS")
        kickoff_time = match_data.get("kickoff_time", "")
        elapsed_minutes = match_data.get("elapsed_minutes")
        
        # Classify status
        status = cls.classify_status(api_status)
        badge = cls.get_status_badge(status)
        
        # Format time display
        time_display = cls._format_time_display(
            status=status,
            api_status=api_status,
            kickoff_time=kickoff_time,
            elapsed_minutes=elapsed_minutes
        )
        
        return {
            "status": status.value,
            "api_status": api_status,
            "badge_text": badge["text"],
            "badge_color": badge["color"],
            "badge_bg_color": badge["bg_color"],
            "time_display": time_display,
            "is_upcoming": status == MatchStatus.UPCOMING,
            "is_live": status == MatchStatus.LIVE,
            "is_finished": status == MatchStatus.FINISHED
        }
    
    @classmethod
    def _format_time_display(
        cls,
        status: MatchStatus,
        api_status: str,
        kickoff_time: str,
        elapsed_minutes: Any
    ) -> str:
        """Format time display based on status"""
        
        if status == MatchStatus.LIVE:
            if elapsed_minutes is not None:
                return f"{elapsed_minutes}'"
            else:
                return api_status
        
        elif status == MatchStatus.UPCOMING:
            if kickoff_time:
                try:
                    from datetime import datetime, timedelta
                    if isinstance(kickoff_time, str):
                        dt = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                    else:
                        dt = kickoff_time
                    
                    # Convert to local (UTC+1)
                    local_dt = dt + timedelta(hours=1)
                    return local_dt.strftime("%H:%M")
                except:
                    return "TBD"
            else:
                return "TBD"
        
        elif status == MatchStatus.FINISHED:
            return "FT"
        
        else:
            return api_status
    
    @classmethod
    def should_display_by_default(cls, status: MatchStatus) -> bool:
        """
        Determine if match should be displayed by default
        
        Args:
            status: MatchStatus enum
            
        Returns:
            True if should display by default
        """
        # Display upcoming and live by default
        # Hide finished by default
        return status in [MatchStatus.UPCOMING, MatchStatus.LIVE]
    
    @classmethod
    def get_sort_priority(cls, status: MatchStatus) -> int:
        """
        Get sort priority (lower = higher priority)
        
        Args:
            status: MatchStatus enum
            
        Returns:
            Sort priority integer
        """
        if status == MatchStatus.UPCOMING:
            return 1  # Highest priority
        elif status == MatchStatus.LIVE:
            return 2  # Second priority
        elif status == MatchStatus.FINISHED:
            return 3  # Lowest priority
        else:
            return 4  # Unknown last
