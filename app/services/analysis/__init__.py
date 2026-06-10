"""
Analysis Services Package
Advanced analysis engines for betting patterns
"""

from app.services.analysis.line_breach_engine import (
    HistoricalLineBreachEngine,
    LineBreachResult,
    LineBreachSignal
)
from app.services.analysis.pattern_detection_engine import (
    PatternDetectionEngine,
    PatternDetectionResult,
    Pattern,
    PatternType,
    PatternStrength
)
from app.services.analysis.league_profile_engine import (
    LeagueProfileEngine,
    LeagueProfile,
    LeagueRanking,
    LeagueCategory
)
from app.services.analysis.priority_ranking_engine import (
    PriorityRankingEngine,
    PriorityAnomaly,
    PriorityRanking,
    RiskLevel
)
from app.services.analysis.match_analysis_loader import MatchAnalysisLoader
from app.services.analysis.volatility_engine import VolatilityEngine, VolatilityResult
from app.services.analysis.false_signal_detector import FalseSignalDetector, FalseSignalResult
from app.services.analysis.home_away_engine import HomeAwayEngine, HomeAwayResult
from app.services.analysis.league_specialization_engine import (
    LeagueSpecializationEngine,
    LeagueMarketStats,
    LeagueMarketRanking,
    SmartRecommendation,
    get_engine as get_lse_engine,
)
from app.services.analysis.error_analysis_engine import (
    ErrorAnalysisEngine,
    FailureRecord,
    FalsePositivePattern,
    PickExplanation,
    get_eae,
)

__all__ = [
    "HistoricalLineBreachEngine",
    "LineBreachResult",
    "LineBreachSignal",
    "PatternDetectionEngine",
    "PatternDetectionResult",
    "Pattern",
    "PatternType",
    "PatternStrength",
    "LeagueProfileEngine",
    "LeagueProfile",
    "LeagueRanking",
    "LeagueCategory",
    "PriorityRankingEngine",
    "PriorityAnomaly",
    "PriorityRanking",
    "RiskLevel",
    "MatchAnalysisLoader",
    "VolatilityEngine",
    "VolatilityResult",
    "FalseSignalDetector",
    "FalseSignalResult",
    "HomeAwayEngine",
    "HomeAwayResult",
    "LeagueSpecializationEngine",
    "LeagueMarketStats",
    "LeagueMarketRanking",
    "SmartRecommendation",
    "get_lse_engine",
    "ErrorAnalysisEngine",
    "FailureRecord",
    "FalsePositivePattern",
    "PickExplanation",
    "get_eae",
]
