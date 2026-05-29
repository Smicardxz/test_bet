"""
Anomaly Engine - Detect bookmaker line anomalies
Compare bookmaker lines with statistical reality
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import math

from app.services.stats import TeamStats


class ConfidenceCategory(str, Enum):
    """Confidence level categories"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass
class Signal:
    """Signal detected in anomaly analysis"""
    type: str
    strength: SignalStrength
    description: str
    value: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "strength": self.strength.value,
            "description": self.description,
            "value": self.value
        }


@dataclass
class AnomalyResult:
    """
    Complete anomaly analysis result
    """
    
    # Match & Market Info
    match_id: str
    market_type: str  # "HT_UNDER", "HT_OVER", "FT_UNDER", "FT_OVER", "BTTS"
    home_team: str = ""
    away_team: str = ""
    competition: str = ""
    country: str = ""
    kickoff_time: str = ""
    line: Optional[float] = None  # For under/over markets
    bookmaker: str = "Unknown"
    
    # Probabilities
    bookmaker_odds: float = 0.0
    bookmaker_probability: float = 0.0
    normalized_bookmaker_probability: float = 0.0
    model_probability: float = 0.0
    edge_percentage: float = 0.0
    
    # Scores (0-100)
    discrepancy_score: float = 0.0
    variance_safety_score: float = 0.0
    historical_hit_rate: float = 0.0
    stability_score: float = 0.0
    anomaly_score: float = 0.0
    priority_score: float = 0.0
    risk_score: float = 0.0
    
    # Confidence
    confidence_category: ConfidenceCategory = ConfidenceCategory.LOW
    confidence_score: float = 0.0  # 0-1
    risk_level: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH"
    
    # Signals & Risk
    positive_signals: List[Signal] = field(default_factory=list)
    negative_signals: List[Signal] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Summary
    explanation_short: str = ""
    explanation_full: str = ""
    
    # Metadata
    sample_size: int = 0
    data_quality: float = 0.0
    data_source: str = "MOCK"  # "MOCK" or "REAL"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result["confidence_category"] = self.confidence_category.value
        result["positive_signals"] = [s.to_dict() for s in self.positive_signals]
        result["negative_signals"] = [s.to_dict() for s in self.negative_signals]
        return result
    
    def to_json(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return self.to_dict()


class AnomalyEngine:
    """
    Detect anomalies between bookmaker lines and statistical reality
    
    Features:
    - Compare bookmaker probabilities with model probabilities
    - Calculate discrepancy scores
    - Assess variance safety and stability
    - Generate confidence scores
    - Identify positive/negative signals
    """
    
    def __init__(self):
        """Initialize anomaly engine"""
        
        # Thresholds
        self.min_sample_size = 8
        self.min_discrepancy = 0.10  # 10% minimum gap
        self.high_discrepancy = 0.25  # 25% = strong anomaly
        
        # Bookmaker margin (typical overround)
        self.typical_margin = 0.05  # 5%
    
    def analyze_market(
        self,
        match_id: int,
        market_type: str,
        bookmaker_odds: float,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float] = None
    ) -> AnomalyResult:
        """
        Analyze a specific market for anomalies
        
        Args:
            match_id: Match ID
            market_type: Market type (e.g., "ft_under_25", "ht_under_05")
            bookmaker_odds: Bookmaker odds
            home_stats: Home team statistics
            away_stats: Away team statistics
            line: Line value for under/over markets
        
        Returns:
            AnomalyResult with complete analysis
        """
        
        # Calculate probabilities
        bk_prob = odds_to_probability(bookmaker_odds)
        normalized_bk_prob = normalize_probability(bk_prob, self.typical_margin)
        model_prob = self._calculate_model_probability(
            market_type, home_stats, away_stats, line
        )
        
        # Calculate scores
        discrepancy = abs(normalized_bk_prob - model_prob)
        discrepancy_score = self._calculate_discrepancy_score(discrepancy)
        variance_safety = self._calculate_variance_safety_score(
            market_type, home_stats, away_stats
        )
        historical_hit = self._calculate_historical_hit_rate(
            market_type, home_stats, away_stats, line
        )
        stability = self._calculate_stability_score(home_stats, away_stats)
        
        # Calculate final anomaly score
        anomaly_score = self._calculate_anomaly_score(
            discrepancy_score,
            variance_safety,
            historical_hit,
            stability
        )
        
        # Calculate confidence
        sample_size = min(home_stats.sample_size, away_stats.sample_size)
        data_quality = (home_stats.data_quality_score + away_stats.data_quality_score) / 2
        
        confidence_score = self._calculate_confidence_score(
            discrepancy,
            variance_safety,
            stability,
            sample_size,
            data_quality
        )
        confidence_category = self._categorize_confidence(confidence_score)
        
        # Detect signals
        positive_signals = self._detect_positive_signals(
            market_type, discrepancy, variance_safety, stability,
            home_stats, away_stats, historical_hit
        )
        negative_signals = self._detect_negative_signals(
            sample_size, data_quality, variance_safety, stability
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            sample_size, data_quality, variance_safety, stability, discrepancy
        )
        
        # Generate explanation
        explanation = self._generate_explanation_summary(
            market_type, discrepancy, anomaly_score, confidence_category,
            positive_signals, risk_factors
        )
        
        return AnomalyResult(
            match_id=match_id,
            market_type=market_type,
            line=line,
            bookmaker_odds=bookmaker_odds,
            bookmaker_probability=bk_prob,
            normalized_bookmaker_probability=normalized_bk_prob,
            model_probability=model_prob,
            edge_percentage=abs(model_prob - normalized_bk_prob) * 100,
            discrepancy_score=discrepancy_score,
            variance_safety_score=variance_safety,
            historical_hit_rate=historical_hit,
            stability_score=stability,
            anomaly_score=anomaly_score,
            priority_score=anomaly_score * confidence_score,  # Calculate priority from anomaly and confidence
            risk_score=1.0 - confidence_score,  # Risk is inverse of confidence
            confidence_category=confidence_category,
            confidence_score=confidence_score,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            risk_factors=risk_factors,
            explanation_short=explanation,
            explanation_full=explanation,
            sample_size=sample_size,
            data_quality=data_quality
        )
    
    def _calculate_model_probability(
        self,
        market_type: str,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """Calculate model probability based on statistics"""
        
        if market_type.startswith("ft_under"):
            return self._calculate_ft_under_probability(home_stats, away_stats, line)
        elif market_type.startswith("ft_over"):
            return self._calculate_ft_over_probability(home_stats, away_stats, line)
        elif market_type.startswith("ht_under"):
            return self._calculate_ht_under_probability(home_stats, away_stats, line)
        elif market_type.startswith("ht_over"):
            return self._calculate_ht_over_probability(home_stats, away_stats, line)
        elif market_type == "btts":
            return self._calculate_btts_probability(home_stats, away_stats)
        else:
            return 0.5  # Default
    
    def _calculate_ft_under_probability(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """Calculate FT under probability"""
        
        if line is None:
            return 0.5
        
        # Use historical rates
        if line == 1.5:
            rate = (home_stats.under_1_5_rate + away_stats.under_1_5_rate) / 2
        elif line == 2.5:
            rate = (home_stats.under_2_5_rate + away_stats.under_2_5_rate) / 2
        elif line == 3.5:
            rate = (home_stats.under_3_5_rate + away_stats.under_3_5_rate) / 2
        elif line == 4.5:
            rate = (home_stats.under_4_5_rate + away_stats.under_4_5_rate) / 2
        elif line == 5.5:
            rate = (home_stats.under_5_5_rate + away_stats.under_5_5_rate) / 2
        elif line >= 6.5:
            # Extreme lines - use extreme rate
            rate = (home_stats.under_extreme_line_rate + away_stats.under_extreme_line_rate) / 2
        else:
            # Interpolate or use average
            avg_goals = (home_stats.avg_total_goals + away_stats.avg_total_goals) / 2
            rate = poisson_under_probability(avg_goals, line)
        
        return rate / 100  # Convert percentage to probability
    
    def _calculate_ft_over_probability(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """Calculate FT over probability"""
        
        under_prob = self._calculate_ft_under_probability(home_stats, away_stats, line)
        return 1 - under_prob
    
    def _calculate_ht_under_probability(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """Calculate HT under probability"""
        
        if line is None:
            return 0.5
        
        if line == 0.5:
            rate = (home_stats.ht_under_0_5_rate + away_stats.ht_under_0_5_rate) / 2
        elif line == 1.5:
            rate = (home_stats.ht_under_1_5_rate + away_stats.ht_under_1_5_rate) / 2
        else:
            # Use average HT goals
            avg_ht_goals = (home_stats.avg_ht_goals + away_stats.avg_ht_goals) / 2
            rate = poisson_under_probability(avg_ht_goals, line)
        
        return rate / 100
    
    def _calculate_ht_over_probability(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """Calculate HT over probability"""
        
        under_prob = self._calculate_ht_under_probability(home_stats, away_stats, line)
        return 1 - under_prob
    
    def _calculate_btts_probability(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> float:
        """Calculate BTTS probability"""
        
        # Average BTTS rate
        rate = (home_stats.btts_rate + away_stats.btts_rate) / 2
        return rate / 100
    
    def _calculate_discrepancy_score(self, discrepancy: float) -> float:
        """
        Calculate discrepancy score (0-100)
        Higher = larger gap between bookmaker and model
        """
        
        # Scale: 0.10 (10%) = 25 points, 0.50 (50%) = 100 points
        score = min(discrepancy * 200, 100)
        return score
    
    def _calculate_variance_safety_score(
        self,
        market_type: str,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> float:
        """
        Calculate variance safety score (0-100)
        Higher = lower variance = safer prediction
        """
        
        if market_type.startswith("ht"):
            avg_variance = (home_stats.ht_goals_variance + away_stats.ht_goals_variance) / 2
        else:
            avg_variance = (home_stats.goals_variance + away_stats.goals_variance) / 2
        
        # Low variance = high safety
        # Normalize: variance 0-3 → safety 100-0
        safety = max(0, 100 - (avg_variance / 3.0 * 100))
        return safety
    
    def _calculate_historical_hit_rate(
        self,
        market_type: str,
        home_stats: TeamStats,
        away_stats: TeamStats,
        line: Optional[float]
    ) -> float:
        """
        Calculate historical hit rate (0-100)
        How often this outcome occurs historically
        """
        
        # This is essentially the model probability converted to percentage
        model_prob = self._calculate_model_probability(
            market_type, home_stats, away_stats, line
        )
        return model_prob * 100
    
    def _calculate_stability_score(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> float:
        """
        Calculate stability score (0-100)
        Higher = more consistent performance
        """
        
        avg_stability = (home_stats.stability_score + away_stats.stability_score) / 2
        return avg_stability * 100
    
    def _calculate_anomaly_score(
        self,
        discrepancy_score: float,
        variance_safety: float,
        historical_hit: float,
        stability: float
    ) -> float:
        """
        Calculate final anomaly score (0-100)
        
        Weights:
        - Discrepancy: 40%
        - Variance safety: 25%
        - Historical hit rate: 20%
        - Stability: 15%
        """
        
        score = (
            discrepancy_score * 0.40 +
            variance_safety * 0.25 +
            historical_hit * 0.20 +
            stability * 0.15
        )
        
        return min(score, 100)
    
    def _calculate_confidence_score(
        self,
        discrepancy: float,
        variance_safety: float,
        stability: float,
        sample_size: int,
        data_quality: float
    ) -> float:
        """
        Calculate confidence score (0-1)
        
        Factors:
        - Discrepancy size (larger = more confident)
        - Variance safety (lower variance = more confident)
        - Stability (higher = more confident)
        - Sample size (larger = more confident)
        - Data quality (higher = more confident)
        """
        
        # Discrepancy confidence (0-1)
        discrepancy_conf = min(discrepancy / 0.30, 1.0)
        
        # Variance confidence (0-1)
        variance_conf = variance_safety / 100
        
        # Stability confidence (0-1)
        stability_conf = stability / 100
        
        # Sample size confidence (0-1)
        if sample_size >= 15:
            sample_conf = 1.0
        elif sample_size >= 10:
            sample_conf = 0.8
        elif sample_size >= 8:
            sample_conf = 0.6
        else:
            sample_conf = 0.4
        
        # Weighted average
        confidence = (
            discrepancy_conf * 0.30 +
            variance_conf * 0.25 +
            stability_conf * 0.20 +
            sample_conf * 0.15 +
            data_quality * 0.10
        )
        
        return min(confidence, 1.0)
    
    def _categorize_confidence(self, confidence_score: float) -> ConfidenceCategory:
        """Categorize confidence score"""
        
        if confidence_score >= 0.75:
            return ConfidenceCategory.HIGH
        elif confidence_score >= 0.50:
            return ConfidenceCategory.MEDIUM
        else:
            return ConfidenceCategory.LOW
    
    def _detect_positive_signals(
        self,
        market_type: str,
        discrepancy: float,
        variance_safety: float,
        stability: float,
        home_stats: TeamStats,
        away_stats: TeamStats,
        historical_hit: float
    ) -> List[Signal]:
        """Detect positive signals (support the anomaly)"""
        
        signals = []
        
        # Large discrepancy
        if discrepancy >= 0.30:
            signals.append(Signal(
                type="EXTREME_DISCREPANCY",
                strength=SignalStrength.STRONG,
                description=f"Écart extrême de {discrepancy:.1%} entre bookmaker et modèle",
                value=discrepancy
            ))
        elif discrepancy >= 0.20:
            signals.append(Signal(
                type="LARGE_DISCREPANCY",
                strength=SignalStrength.MODERATE,
                description=f"Écart important de {discrepancy:.1%}",
                value=discrepancy
            ))
        
        # Low variance
        if variance_safety >= 75:
            signals.append(Signal(
                type="LOW_VARIANCE",
                strength=SignalStrength.STRONG,
                description="Variance très faible - scores prévisibles",
                value=variance_safety
            ))
        elif variance_safety >= 60:
            signals.append(Signal(
                type="MODERATE_VARIANCE",
                strength=SignalStrength.MODERATE,
                description="Variance modérée",
                value=variance_safety
            ))
        
        # High stability
        if stability >= 75:
            signals.append(Signal(
                type="HIGH_STABILITY",
                strength=SignalStrength.STRONG,
                description="Performances très stables",
                value=stability
            ))
        
        # Strong historical pattern
        if historical_hit >= 70:
            signals.append(Signal(
                type="STRONG_HISTORICAL_PATTERN",
                strength=SignalStrength.STRONG,
                description=f"Pattern historique fort ({historical_hit:.0f}%)",
                value=historical_hit
            ))
        elif historical_hit >= 60:
            signals.append(Signal(
                type="MODERATE_HISTORICAL_PATTERN",
                strength=SignalStrength.MODERATE,
                description=f"Pattern historique modéré ({historical_hit:.0f}%)",
                value=historical_hit
            ))
        
        # Trending momentum (for relevant markets)
        avg_momentum = (home_stats.momentum_score + away_stats.momentum_score) / 2
        if abs(avg_momentum) >= 0.3:
            direction = "hausse" if avg_momentum > 0 else "baisse"
            signals.append(Signal(
                type="STRONG_MOMENTUM",
                strength=SignalStrength.MODERATE,
                description=f"Momentum fort en {direction}",
                value=avg_momentum
            ))
        
        return signals
    
    def _detect_negative_signals(
        self,
        sample_size: int,
        data_quality: float,
        variance_safety: float,
        stability: float
    ) -> List[Signal]:
        """Detect negative signals (weaken the anomaly)"""
        
        signals = []
        
        # Small sample
        if sample_size < 8:
            signals.append(Signal(
                type="SMALL_SAMPLE",
                strength=SignalStrength.STRONG,
                description=f"Échantillon très petit ({sample_size} matchs)",
                value=sample_size
            ))
        elif sample_size < 12:
            signals.append(Signal(
                type="MODERATE_SAMPLE",
                strength=SignalStrength.MODERATE,
                description=f"Échantillon modéré ({sample_size} matchs)",
                value=sample_size
            ))
        
        # Poor data quality
        if data_quality < 0.7:
            signals.append(Signal(
                type="POOR_DATA_QUALITY",
                strength=SignalStrength.STRONG,
                description=f"Qualité données faible ({data_quality:.0%})",
                value=data_quality
            ))
        elif data_quality < 0.85:
            signals.append(Signal(
                type="MODERATE_DATA_QUALITY",
                strength=SignalStrength.MODERATE,
                description=f"Qualité données modérée ({data_quality:.0%})",
                value=data_quality
            ))
        
        # High variance
        if variance_safety < 40:
            signals.append(Signal(
                type="HIGH_VARIANCE",
                strength=SignalStrength.STRONG,
                description="Variance élevée - scores imprévisibles",
                value=variance_safety
            ))
        
        # Low stability
        if stability < 50:
            signals.append(Signal(
                type="LOW_STABILITY",
                strength=SignalStrength.MODERATE,
                description="Stabilité faible - performances incohérentes",
                value=stability
            ))
        
        return signals
    
    def _identify_risk_factors(
        self,
        sample_size: int,
        data_quality: float,
        variance_safety: float,
        stability: float,
        discrepancy: float
    ) -> List[str]:
        """Identify risk factors"""
        
        risks = []
        
        if sample_size < 8:
            risks.append("Échantillon très petit - fiabilité limitée")
        elif sample_size < 12:
            risks.append("Échantillon modéré - prudence recommandée")
        
        if data_quality < 0.7:
            risks.append("Données manquantes importantes")
        
        if variance_safety < 40:
            risks.append("Variance élevée - résultats imprévisibles")
        
        if stability < 50:
            risks.append("Performances instables")
        
        if discrepancy < 0.15:
            risks.append("Écart faible - anomalie peu significative")
        
        return risks
    
    def _generate_explanation_summary(
        self,
        market_type: str,
        discrepancy: float,
        anomaly_score: float,
        confidence_category: ConfidenceCategory,
        positive_signals: List[Signal],
        risk_factors: List[str]
    ) -> str:
        """Generate explanation summary"""
        
        parts = []
        
        # Market & score
        parts.append(f"Marché: {market_type}")
        parts.append(f"Score anomalie: {anomaly_score:.1f}/100")
        parts.append(f"Confiance: {confidence_category.value}")
        parts.append(f"Écart: {discrepancy:.1%}")
        
        # Positive signals
        if positive_signals:
            parts.append(f"\nSignaux positifs: {len(positive_signals)}")
            for signal in positive_signals[:3]:  # Top 3
                parts.append(f"  • {signal.description}")
        
        # Risk factors
        if risk_factors:
            parts.append(f"\nFacteurs de risque: {len(risk_factors)}")
            for risk in risk_factors[:3]:  # Top 3
                parts.append(f"  ⚠️ {risk}")
        
        return "\n".join(parts)


# ==================== UTILITY FUNCTIONS ====================

def odds_to_probability(odds: float) -> float:
    """Convert decimal odds to probability"""
    if odds <= 1.0:
        return 0.0
    return 1 / odds


def normalize_probability(prob: float, margin: float) -> float:
    """Remove bookmaker margin from probability"""
    # Simple normalization
    normalized = prob / (1 + margin)
    return min(normalized, 1.0)


def poisson_under_probability(avg_goals: float, line: float) -> float:
    """
    Calculate under probability using Poisson distribution
    Simplified approximation
    """
    
    if avg_goals <= 0:
        return 100.0
    
    # Cumulative probability for goals < line
    cumulative = 0.0
    for k in range(int(line)):
        cumulative += poisson_pmf(k, avg_goals)
    
    return min(cumulative * 100, 100.0)


def poisson_pmf(k: int, lambda_: float) -> float:
    """Poisson probability mass function"""
    if lambda_ <= 0:
        return 0.0
    
    return (lambda_ ** k) * math.exp(-lambda_) / math.factorial(k)
