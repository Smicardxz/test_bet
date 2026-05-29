"""
Priority Ranking Engine
Rank anomalies by exploitability and strength

Considers multiple factors to surface only the best anomalies
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging

from app.services.anomaly.anomaly_engine import AnomalyResult, ConfidenceCategory
from app.services.analysis import LineBreachResult


logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level for anomaly"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class PriorityAnomaly:
    """An anomaly with priority scoring"""
    
    # Original anomaly
    match_id: str
    home_team: str
    away_team: str
    league: str
    market_type: str
    
    # Original scores
    anomaly_score: float
    confidence_category: str
    variance_safety: float
    stability_score: float
    data_quality: float
    sample_size: int
    
    # Line breach analysis
    line_breach_safety: float = 0.0
    line_breach_rate: float = 0.0
    
    # Market reliability (from backtesting)
    market_hit_rate: float = 50.0
    market_roi: float = 0.0
    
    # League stability (from league profile)
    league_stability: float = 50.0
    league_exploitability: float = 50.0
    
    # Contradictory signals
    contradictory_signals: int = 0
    
    # Calculated scores
    raw_priority_score: float = 0.0
    risk_adjusted_score: float = 0.0
    final_priority_score: float = 0.0
    
    # Risk
    risk_level: RiskLevel = RiskLevel.MODERATE
    risk_factors: List[str] = field(default_factory=list)
    
    # Explanation
    explanation: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "match": f"{self.home_team} vs {self.away_team}",
            "league": self.league,
            "market": self.market_type,
            "anomaly_score": round(self.anomaly_score, 1),
            "confidence": self.confidence_category,
            "variance_safety": round(self.variance_safety, 1),
            "line_breach_safety": round(self.line_breach_safety, 1),
            "league_stability": round(self.league_stability, 1),
            "contradictory_signals": self.contradictory_signals,
            "sample_size": self.sample_size,
            "raw_priority": round(self.raw_priority_score, 1),
            "risk_adjusted": round(self.risk_adjusted_score, 1),
            "final_score": round(self.final_priority_score, 1),
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors
        }


@dataclass
class PriorityRanking:
    """Complete priority ranking"""
    
    # Rankings
    top_picks: List[PriorityAnomaly] = field(default_factory=list)
    risk_adjusted_ranking: List[PriorityAnomaly] = field(default_factory=list)
    
    # Filters applied
    min_anomaly_score: float = 0.0
    max_results: int = 0
    
    # Summary
    total_anomalies: int = 0
    filtered_out: int = 0
    avg_risk_score: float = 0.0
    
    # By risk level
    very_low_risk: int = 0
    low_risk: int = 0
    moderate_risk: int = 0
    high_risk: int = 0
    very_high_risk: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_anomalies": self.total_anomalies,
                "filtered_out": self.filtered_out,
                "top_picks_count": len(self.top_picks),
                "avg_risk": round(self.avg_risk_score, 2),
                "risk_distribution": {
                    "very_low": self.very_low_risk,
                    "low": self.low_risk,
                    "moderate": self.moderate_risk,
                    "high": self.high_risk,
                    "very_high": self.very_high_risk
                }
            },
            "top_picks": [a.to_dict() for a in self.top_picks[:20]]
        }


class PriorityRankingEngine:
    """
    Priority Ranking Engine
    
    Ranks anomalies by considering:
    - Anomaly score (core signal)
    - Variance safety (consistency)
    - Historical line breach (historical safety)
    - Data quality (reliability)
    - Market reliability (backtest performance)
    - League stability (predictability)
    - Confidence category
    
    Penalizes:
    - Contradictory signals
    - Low sample size
    - High risk factors
    - Unstable leagues
    """
    
    def __init__(self):
        """Initialize ranking engine"""
        
        # Weights for priority score
        self.weights = {
            "anomaly": 0.30,
            "variance": 0.20,
            "line_breach": 0.15,
            "data_quality": 0.10,
            "market_reliability": 0.10,
            "league_stability": 0.10,
            "confidence": 0.05
        }
        
        # Penalty factors
        self.contradictory_penalty = 15.0
        self.low_sample_penalty = 10.0
        self.risk_penalty_base = 5.0
    
    def rank_anomalies(
        self,
        anomalies: List[AnomalyResult],
        line_breach_results: Optional[Dict[str, LineBreachResult]] = None,
        market_performance: Optional[Dict[str, Dict]] = None,
        league_profiles: Optional[Dict[str, Dict]] = None,
        min_anomaly_score: float = 60.0,
        max_results: int = 20,
        min_risk_adjusted_score: float = 50.0
    ) -> PriorityRanking:
        """
        Rank anomalies by priority
        
        Args:
            anomalies: List of detected anomalies
            line_breach_results: Dict mapping match_id to line breach result
            market_performance: Dict mapping market_type to performance metrics
            league_profiles: Dict mapping league name to profile
            min_anomaly_score: Minimum anomaly score to consider
            max_results: Maximum results to return
            min_risk_adjusted_score: Minimum risk-adjusted score
            
        Returns:
            PriorityRanking with ranked anomalies
        """
        
        result = PriorityRanking()
        result.min_anomaly_score = min_anomaly_score
        result.max_results = max_results
        result.total_anomalies = len(anomalies)
        
        logger.info(f"Ranking {len(anomalies)} anomalies...")
        
        # Score each anomaly
        scored = []
        
        for anomaly in anomalies:
            # Skip if below minimum score
            if anomaly.anomaly_score < min_anomaly_score:
                result.filtered_out += 1
                continue
            
            pa = self._score_anomaly(
                anomaly,
                line_breach_results,
                market_performance,
                league_profiles
            )
            
            scored.append(pa)
        
        # Sort by raw priority score
        result.top_picks = sorted(
            scored,
            key=lambda a: a.raw_priority_score,
            reverse=True
        )[:max_results]
        
        # Sort by risk-adjusted score
        result.risk_adjusted_ranking = sorted(
            scored,
            key=lambda a: a.risk_adjusted_score,
            reverse=True
        )[:max_results]
        
        # Count risk levels
        for pa in scored:
            if pa.risk_level == RiskLevel.VERY_LOW:
                result.very_low_risk += 1
            elif pa.risk_level == RiskLevel.LOW:
                result.low_risk += 1
            elif pa.risk_level == RiskLevel.MODERATE:
                result.moderate_risk += 1
            elif pa.risk_level == RiskLevel.HIGH:
                result.high_risk += 1
            elif pa.risk_level == RiskLevel.VERY_HIGH:
                result.very_high_risk += 1
        
        # Calculate average risk
        risk_scores = self._risk_scores()
        if scored:
            result.avg_risk_score = statistics.mean(
                risk_scores.get(pa.risk_level, 50) for pa in scored
            )
        
        logger.info(f"Ranking complete: {len(result.top_picks)} top picks")
        
        return result
    
    def _score_anomaly(
        self,
        anomaly: AnomalyResult,
        line_breach_results: Optional[Dict[str, LineBreachResult]],
        market_performance: Optional[Dict[str, Dict]],
        league_profiles: Optional[Dict[str, Dict]]
    ) -> PriorityAnomaly:
        """Score a single anomaly"""
        
        pa = PriorityAnomaly(
            match_id=str(anomaly.match_id),
            home_team="Home",  # Would be populated from match data
            away_team="Away",
            league="Unknown",
            market_type=anomaly.market_type,
            anomaly_score=anomaly.anomaly_score,
            confidence_category=anomaly.confidence_category.value,
            variance_safety=anomaly.variance_safety_score,
            stability_score=anomaly.stability_score,
            data_quality=anomaly.data_quality,
            sample_size=anomaly.sample_size
        )
        
        # Get line breach result
        if line_breach_results and pa.match_id in line_breach_results:
            lb = line_breach_results[pa.match_id]
            pa.line_breach_safety = lb.historical_safety_score
            pa.line_breach_rate = lb.line_breach_rate
        
        # Get market performance
        if market_performance and anomaly.market_type in market_performance:
            mp = market_performance[anomaly.market_type]
            pa.market_hit_rate = mp.get("hit_rate", 50.0)
            pa.market_roi = mp.get("roi", 0.0)
        
        # Get league stability
        # Would be populated from actual league data
        if league_profiles:
            # Find matching league
            pass
        
        # Count contradictory signals
        pa.contradictory_signals = self._count_contradictory_signals(anomaly)
        
        # Calculate raw priority score
        pa.raw_priority_score = self._calculate_raw_priority(pa)
        
        # Calculate risk-adjusted score
        pa.risk_adjusted_score = self._calculate_risk_adjusted(pa)
        
        # Determine risk level
        pa.risk_level = self._determine_risk(pa)
        
        # Generate explanation
        pa.explanation = self._generate_explanation(pa)
        
        return pa
    
    def _count_contradictory_signals(self, anomaly: AnomalyResult) -> int:
        """Count contradictory signals in anomaly"""
        
        contradictions = 0
        
        # Check for contradictory signals
        positive_types = {s.type for s in anomaly.positive_signals}
        negative_types = {s.type for s in anomaly.negative_signals}
        
        # Example contradictions:
        # High under rate but high over signal
        if "high_under_rate" in positive_types and "over_trend" in positive_types:
            contradictions += 1
        
        # High stability but high variance
        if anomaly.stability_score > 80 and anomaly.variance_safety_score < 40:
            contradictions += 1
        
        # High confidence but low sample
        if (anomaly.confidence_category == ConfidenceCategory.HIGH and 
            anomaly.sample_size < 10):
            contradictions += 1
        
        return contradictions
    
    def _calculate_raw_priority(self, pa: PriorityAnomaly) -> float:
        """Calculate raw priority score (before risk adjustment)"""
        
        # Normalize confidence to 0-100
        confidence_map = {
            "HIGH": 100.0,
            "MEDIUM": 60.0,
            "LOW": 30.0
        }
        confidence_score = confidence_map.get(pa.confidence_category, 50.0)
        
        # Calculate weighted score
        score = (
            pa.anomaly_score * self.weights["anomaly"] +
            pa.variance_safety * self.weights["variance"] +
            pa.line_breach_safety * self.weights["line_breach"] +
            pa.data_quality * 100 * self.weights["data_quality"] +
            pa.market_hit_rate * self.weights["market_reliability"] +
            pa.league_stability * self.weights["league_stability"] +
            confidence_score * self.weights["confidence"]
        )
        
        # Apply penalties
        if pa.contradictory_signals > 0:
            score -= pa.contradictory_signals * self.contradictory_penalty
        
        if pa.sample_size < 10:
            sample_penalty = self.low_sample_penalty * (10 - pa.sample_size) / 10
            score -= sample_penalty
        
        return max(0, score)
    
    def _calculate_risk_adjusted(self, pa: PriorityAnomaly) -> float:
        """Calculate risk-adjusted score"""
        
        raw = pa.raw_priority_score
        
        # Risk factors
        risk_factors = []
        risk_penalty = 0.0
        
        # Sample size risk
        if pa.sample_size < 12:
            risk_factors.append("Small sample")
            risk_penalty += 5.0 * (12 - pa.sample_size) / 12
        
        # Variance risk
        if pa.variance_safety < 50:
            risk_factors.append("High variance")
            risk_penalty += 8.0
        
        # Line breach risk
        if pa.line_breach_rate > 30:
            risk_factors.append("High line breach rate")
            risk_penalty += 7.0
        
        # Contradiction risk
        if pa.contradictory_signals > 0:
            risk_factors.append("Contradictory signals")
            risk_penalty += pa.contradictory_signals * 5.0
        
        # Low stability risk
        if pa.stability_score < 50:
            risk_factors.append("Low stability")
            risk_penalty += 5.0
        
        # Store risk factors
        pa.risk_factors = risk_factors
        
        # Apply risk penalty
        adjusted = raw - risk_penalty
        
        return max(0, adjusted)
    
    def _determine_risk(self, pa: PriorityAnomaly) -> RiskLevel:
        """Determine risk level"""
        
        risk_score = len(pa.risk_factors)
        
        if risk_score == 0 and pa.risk_adjusted_score > 80:
            return RiskLevel.VERY_LOW
        elif risk_score <= 1 and pa.risk_adjusted_score > 70:
            return RiskLevel.LOW
        elif risk_score <= 2 and pa.risk_adjusted_score > 50:
            return RiskLevel.MODERATE
        elif risk_score <= 3:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _generate_explanation(self, pa: PriorityAnomaly) -> str:
        """Generate human-readable explanation"""
        
        parts = []
        
        parts.append(f"Score: {pa.anomaly_score:.0f} | Priority: {pa.raw_priority_score:.0f} | Risk-Adj: {pa.risk_adjusted_score:.0f}")
        
        if pa.line_breach_safety > 80:
            parts.append("Line historically very safe")
        elif pa.line_breach_safety > 50:
            parts.append("Line moderately safe")
        else:
            parts.append("Line historically risky")
        
        if pa.contradictory_signals > 0:
            parts.append(f"⚠️ {pa.contradictory_signals} contradictory signals")
        
        if pa.risk_factors:
            parts.append(f"Risks: {', '.join(pa.risk_factors)}")
        
        return " | ".join(parts)
    
    def _risk_scores(self) -> Dict[RiskLevel, float]:
        """Get numerical risk scores"""
        return {
            RiskLevel.VERY_LOW: 10,
            RiskLevel.LOW: 30,
            RiskLevel.MODERATE: 50,
            RiskLevel.HIGH: 70,
            RiskLevel.VERY_HIGH: 90
        }
    
    def print_ranking(self, ranking: PriorityRanking, mode: str = "top_picks"):
        """Print ranking to console"""
        
        anomalies = ranking.top_picks if mode == "top_picks" else ranking.risk_adjusted_ranking
        
        print("\n" + "=" * 100)
        print(f"PRIORITY RANKING - {mode.upper().replace('_', ' ')}")
        print("=" * 100)
        
        # Summary
        print("\n📊 SUMMARY")
        print(f"  Total Anomalies: {ranking.total_anomalies}")
        print(f"  Filtered Out: {ranking.filtered_out}")
        print(f"  Top Picks: {len(anomalies)}")
        print(f"  Avg Risk Score: {ranking.avg_risk_score:.0f}/100")
        
        # Risk distribution
        print("\n🎚️  RISK DISTRIBUTION")
        print(f"  Very Low: {ranking.very_low_risk}")
        print(f"  Low: {ranking.low_risk}")
        print(f"  Moderate: {ranking.moderate_risk}")
        print(f"  High: {ranking.high_risk}")
        print(f"  Very High: {ranking.very_high_risk}")
        
        # Top picks
        print(f"\n🎯 TOP {len(anomalies)} PICKS")
        print("-" * 100)
        print(f"{'Rank':<6} {'Match':<30} {'Market':<15} {'Score':<8} "
              f"{'Priority':<8} {'Risk-Adj':<8} {'Risk':<12}")
        print("-" * 100)
        
        for i, pa in enumerate(anomalies[:20], 1):
            print(f"{i:<6} {f'{pa.home_team} v {pa.away_team}':<30} "
                  f"{pa.market_type:<15} {pa.anomaly_score:<8.1f} "
                  f"{pa.raw_priority_score:<8.1f} {pa.risk_adjusted_score:<8.1f} "
                  f"{pa.risk_level.value:<12}")
        
        # Detailed view for top 5
        print("\n📋 DETAILED TOP 5")
        print("-" * 100)
        
        for i, pa in enumerate(anomalies[:5], 1):
            print(f"\n  #{i} {pa.home_team} vs {pa.away_team}")
            print(f"     Market: {pa.market_type}")
            print(f"     Anomaly: {pa.anomaly_score:.1f} | Priority: {pa.raw_priority_score:.1f} | Risk-Adj: {pa.risk_adjusted_score:.1f}")
            print(f"     Confidence: {pa.confidence_category}")
            print(f"     Variance Safety: {pa.variance_safety:.1f} | Line Breach Safety: {pa.line_breach_safety:.1f}")
            print(f"     Sample: {pa.sample_size} | Data Quality: {pa.data_quality:.2f}")
            print(f"     Risk: {pa.risk_level.value}")
            if pa.risk_factors:
                print(f"     Risks: {', '.join(pa.risk_factors)}")
        
        print("\n" + "=" * 100)
    
    def get_safe_picks(
        self,
        ranking: PriorityRanking,
        max_risk: RiskLevel = RiskLevel.LOW,
        min_score: float = 60.0
    ) -> List[PriorityAnomaly]:
        """Get only safe picks"""
        
        risk_order = {
            RiskLevel.VERY_LOW: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.VERY_HIGH: 4
        }
        
        max_risk_level = risk_order.get(max_risk, 2)
        
        return [
            pa for pa in ranking.top_picks
            if risk_order.get(pa.risk_level, 4) <= max_risk_level
            and pa.risk_adjusted_score >= min_score
        ]
