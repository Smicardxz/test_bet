"""
Analysis Modes
Defines the two core operating modes of the system
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional


class AnalysisMode(str, Enum):
    """
    System operating modes
    
    STATISTICAL_SIGNAL: Analyze historical data only (no odds needed)
    INEFFICIENCY_DETECTION: Compare historical vs bookmaker (requires odds)
    """
    STATISTICAL_SIGNAL = "statistical_signal"
    INEFFICIENCY_DETECTION = "inefficiency_detection"


@dataclass
class ModeStatus:
    """Current system mode status"""
    mode: AnalysisMode
    odds_available: bool
    can_detect_inefficiencies: bool
    message: str
    
    @classmethod
    def from_odds_availability(cls, odds_available: bool) -> "ModeStatus":
        """Create status from odds availability"""
        if odds_available:
            return cls(
                mode=AnalysisMode.INEFFICIENCY_DETECTION,
                odds_available=True,
                can_detect_inefficiencies=True,
                message="✅ Inefficiency detection active - odds available"
            )
        else:
            return cls(
                mode=AnalysisMode.STATISTICAL_SIGNAL,
                odds_available=False,
                can_detect_inefficiencies=False,
                message="⏳ Statistical signal mode - waiting for odds"
            )
