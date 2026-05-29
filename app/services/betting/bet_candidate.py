"""
Bet Candidate
Represents a single betting opportunity
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level for a bet"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class Signal:
    """A positive or negative signal for a bet"""
    type: str
    description: str
    strength: str  # "WEAK", "MODERATE", "STRONG"


@dataclass
class BetCandidate:
    """
    Represents a single betting opportunity
    
    Each bet is evaluated individually, not based on market history.
    """
    
    # Match Information (required fields first)
    match_id: str
    home_team: str
    away_team: str
    competition: str
    market_type: str  # e.g., "HT_UNDER", "HT_OVER", "FT_UNDER", "FT_OVER", "BTTS"
    
    # Optional fields with defaults
    country: str = "Unknown"
    kickoff_time: str = ""
    match_date: str = ""
    line: Optional[float] = None
    bookmaker: str = "Unknown"
    
    # Odds
    odd: Optional[float] = None
    
    # Analysis Scores
    anomaly_score: float = 0.0
    confidence_score: float = 0.0
    data_quality_score: float = 0.0
    risk_score: float = 0.0
    priority_score: float = 0.0
    
    # Probabilities
    model_probability: float = 0.0
    bookmaker_probability: float = 0.0
    edge_percentage: float = 0.0
    
    # Categorization
    confidence_category: str = "MEDIUM"  # "HIGH", "MEDIUM", "LOW"
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Explanation
    explanation_short: str = ""
    explanation_full: str = ""
    
    # Signals
    positive_signals: List[Signal] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: str = ""
    data_source: str = "MOCK"  # "MOCK" or "REAL"
    sample_size: int = 0
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        
        # Handle missing data
        if self.home_team == "Unknown" or self.away_team == "Unknown":
            self.risk_factors.append("Team names missing")
            self.data_quality_score = max(0.0, self.data_quality_score - 20.0)
        
        if self.competition == "Unknown":
            self.risk_factors.append("Competition missing")
            self.data_quality_score = max(0.0, self.data_quality_score - 10.0)
        
        if self.bookmaker == "Unknown":
            self.risk_factors.append("Bookmaker missing")
            self.data_quality_score = max(0.0, self.data_quality_score - 15.0)
        
        if self.odd is None:
            self.risk_factors.append("Odds missing")
            self.data_quality_score = max(0.0, self.data_quality_score - 30.0)
    
    @property
    def combined_score(self) -> float:
        """Calculate a combined score for ranking"""
        # Weight: anomaly (40%), confidence (30%), data quality (20%), risk (10%)
        risk_weight = 1.0 - (self.risk_score / 100.0)
        return (
            self.anomaly_score * 0.40 +
            self.confidence_score * 0.30 +
            self.data_quality_score * 0.20 +
            risk_weight * 100.0 * 0.10
        )
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if bet has high confidence"""
        return self.confidence_category == "HIGH" and self.confidence_score >= 0.70
    
    @property
    def is_safe(self) -> bool:
        """Check if bet is considered safe"""
        return (
            self.risk_level in (RiskLevel.VERY_LOW, RiskLevel.LOW) and
            self.data_quality_score >= 0.60 and
            self.confidence_score >= 0.60
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "data_source": self.data_source,
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "competition": self.competition,
            "country": self.country,
            "kickoff_time": self.kickoff_time,
            "match_date": self.match_date,
            "market_type": self.market_type,
            "line": self.line,
            "odd": self.odd,
            "bookmaker": self.bookmaker,
            "anomaly_score": round(self.anomaly_score, 2),
            "confidence_score": round(self.confidence_score, 2),
            "confidence_category": self.confidence_category,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level.value,
            "data_quality_score": round(self.data_quality_score, 2),
            "sample_size": self.sample_size,
            "model_probability": round(self.model_probability, 2),
            "bookmaker_probability": round(self.bookmaker_probability, 2),
            "edge_percentage": round(self.edge_percentage, 2),
            "priority_score": round(self.priority_score, 2),
            "positive_signals": [
                {"type": s.type, "description": s.description, "strength": s.strength}
                for s in self.positive_signals
            ],
            "risk_factors": self.risk_factors,
            "explanation_short": self.explanation_short,
            "explanation_full": self.explanation_full,
            "combined_score": round(self.combined_score, 2),
            "timestamp": self.timestamp
        }
