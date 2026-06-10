"""
Signal Engine - Refactored
Produces statistical signals compatible with InefficiencyDetector

Focus: Detect patterns and prepare for bookmaker comparison
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.anomaly.line_breach_analyzer import LineBreachAnalyzer

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of statistical signals - DIVERSIFIED PROFILING"""
    # Scoring profiles
    EXTREME_UNDER = "EXTREME_UNDER"
    LOW_SCORING = "LOW_SCORING"
    BALANCED_SCORING = "BALANCED_SCORING"
    HIGH_SCORING = "HIGH_SCORING"
    EXTREME_OVER = "EXTREME_OVER"
    
    # Tempo profiles
    HIGH_TEMPO = "HIGH_TEMPO"
    MEDIUM_TEMPO = "MEDIUM_TEMPO"
    LOW_TEMPO = "LOW_TEMPO"
    SLOW_START_PROFILE = "SLOW_START_PROFILE"
    SECOND_HALF_EXPLOSION = "SECOND_HALF_EXPLOSION"
    
    # BTTS profiles
    BTTS_PROFILE = "BTTS_PROFILE"
    NO_BTTS_PROFILE = "NO_BTTS_PROFILE"
    CLEAN_SHEET_SPECIALIST = "CLEAN_SHEET_SPECIALIST"
    
    # Match patterns
    LATE_GOAL_PROFILE = "LATE_GOAL_PROFILE"
    DEAD_FIRST_HALF = "DEAD_FIRST_HALF"
    LOW_FIRST_HALF_HIGH_SECOND = "LOW_FIRST_HALF_HIGH_SECOND"
    HOME_DOMINANT = "HOME_DOMINANT"
    AWAY_COLLAPSE = "AWAY_COLLAPSE"
    COMEBACK_PROFILE = "COMEBACK_PROFILE"
    VOLATILE_MATCH = "VOLATILE_MATCH"
    ASYMMETRIC_SCORING = "ASYMMETRIC_SCORING"
    OVER_ACCELERATION = "OVER_ACCELERATION"
    
    # Statistical patterns
    HT_UNDER = "HT_UNDER"
    HT_OVER = "HT_OVER"
    FT_UNDER = "FT_UNDER"
    FT_OVER = "FT_OVER"
    LOW_VARIANCE = "LOW_VARIANCE"
    SLOW_TEMPO = "SLOW_TEMPO"
    DEFENSIVE_PATTERN = "DEFENSIVE_PATTERN"
    LEAGUE_LOW_SCORING = "LEAGUE_LOW_SCORING"
    HIGH_STABILITY = "HIGH_STABILITY"
    CHAOTIC_MATCH = "CHAOTIC_MATCH"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    EXTREME = "EXTREME"


@dataclass
class StatisticalSignal:
    """
    Statistical signal ready for bookmaker comparison

    This is the output of SignalEngine, designed to feed into InefficiencyDetector

    Categories:
    - STATISTICAL: Pure statistical pattern (no odds comparison yet)
    - MARKET_EDGE: Bookmaker inefficiency detected (with odds comparison)
    """
    # Signal identification
    signal_type: str
    signal_strength: str
    confidence: float  # 0-1
    signal_category: str  # "STATISTICAL" or "MARKET_EDGE"

    # Match context
    match_id: str
    home_team: str
    away_team: str
    competition: str
    country: str

    # Market suggestions
    suggested_markets: List[str]  # ["UNDER_4_5", "UNDER_5_5", "HT_UNDER_1_5"]
    compatible_lines: List[float]  # [4.5, 5.5, 6.5]
    expected_goal_range: Tuple[float, float]  # (min, max)

    # Historical analysis
    historical_hit_rates_by_line: Dict[float, float]  # {2.5: 0.60, 3.5: 0.87, ...}
    max_observed_goals: int
    avg_goals: float

    # Quality metrics
    variance_score: float  # 0-1 (lower is better)
    stability_score: float  # 0-1 (higher is better)
    sample_size: int
    data_quality: float  # 0-1

    # Market edge (only for MARKET_EDGE category)
    bookmaker_odd: Optional[float] = None
    fair_odd: Optional[float] = None
    edge_percent: Optional[float] = None

    # Explanation
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "signal_type": self.signal_type,
            "signal_strength": self.signal_strength,
            "confidence": self.confidence,
            "signal_category": self.signal_category,
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "competition": self.competition,
            "country": self.country,
            "suggested_markets": self.suggested_markets,
            "compatible_lines": self.compatible_lines,
            "expected_goal_range": self.expected_goal_range,
            "historical_hit_rates_by_line": self.historical_hit_rates_by_line,
            "max_observed_goals": self.max_observed_goals,
            "avg_goals": self.avg_goals,
            "variance_score": self.variance_score,
            "stability_score": self.stability_score,
            "sample_size": self.sample_size,
            "data_quality": self.data_quality,
            "bookmaker_odd": self.bookmaker_odd,
            "fair_odd": self.fair_odd,
            "edge_percent": self.edge_percent,
            "reasons": self.reasons
        }


class SignalEngine:
    """
    Detects statistical patterns and produces signals
    
    Refactored to be compatible with InefficiencyDetector
    """
    
    def __init__(self):
        """Initialize signal engine"""
        self.line_analyzer = LineBreachAnalyzer()
        logger.info("SignalEngine initialized (refactored)")
    
    def detect_signals(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        ht_goal_history: Optional[List[int]] = None,
        league_profile: Optional[Dict[str, Any]] = None,
        match_history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[StatisticalSignal]:
        """
        Detect all signals for a match (UNDER + OVER + BTTS + SH).

        Args:
            match:         Match information
            goal_history:  Full-time goals history
            ht_goal_history: Half-time goals history (optional)
            league_profile: League profile (optional)
            match_history: List of {home_goals, away_goals} for BTTS / home-over / away-over

        Returns:
            List of StatisticalSignal
        """
        signals = []

        if not goal_history or len(goal_history) < 3:
            logger.warning(f"Insufficient data for match {match.get('match_id')}")
            return signals

        # ── Shared metrics ──────────────────────────────────────────────────
        line_analyses = self.line_analyzer.analyze_all_lines(goal_history)
        hit_rates_by_line = {line: a.hit_rate for line, a in line_analyses.items()}
        max_goals     = max(goal_history)
        avg_goals     = sum(goal_history) / len(goal_history)
        variance      = self._calculate_variance(goal_history)
        variance_score   = self._variance_to_score(variance)
        stability_score  = self._calculate_stability(goal_history)
        sample_size      = len(goal_history)
        data_quality     = self._calculate_data_quality(sample_size, variance)

        # ── UNDER signals (existing) ─────────────────────────────────────
        extreme_under = self._detect_extreme_under(
            match=match, goal_history=goal_history, line_analyses=line_analyses,
            max_goals=max_goals, avg_goals=avg_goals, hit_rates_by_line=hit_rates_by_line,
            variance_score=variance_score, stability_score=stability_score,
            sample_size=sample_size, data_quality=data_quality
        )
        if extreme_under:
            signals.append(extreme_under)

        if ht_goal_history and len(ht_goal_history) >= 5:
            ht_under = self._detect_ht_under(
                match=match, ht_goal_history=ht_goal_history,
                variance_score=variance_score, stability_score=stability_score,
                data_quality=data_quality
            )
            if ht_under:
                signals.append(ht_under)

        ft_under = self._detect_ft_under(
            match=match, goal_history=goal_history, line_analyses=line_analyses,
            avg_goals=avg_goals, hit_rates_by_line=hit_rates_by_line,
            variance_score=variance_score, stability_score=stability_score,
            sample_size=sample_size, data_quality=data_quality
        )
        if ft_under:
            signals.append(ft_under)

        if variance_score >= 0.7:
            low_var = self._detect_low_variance(
                match=match, goal_history=goal_history, variance=variance,
                variance_score=variance_score, stability_score=stability_score,
                hit_rates_by_line=hit_rates_by_line, sample_size=sample_size,
                data_quality=data_quality
            )
            if low_var:
                signals.append(low_var)

        # ── OVER signals (Phase 1 — multi-regime) ─────────────────────────
        ft_over = self._detect_ft_over(
            match=match, goal_history=goal_history, avg_goals=avg_goals,
            variance_score=variance_score, stability_score=stability_score,
            sample_size=sample_size, data_quality=data_quality
        )
        if ft_over:
            signals.append(ft_over)

        if ht_goal_history and len(ht_goal_history) >= 5:
            ht_over = self._detect_ht_over(
                match=match, ht_goal_history=ht_goal_history,
                variance_score=variance_score, stability_score=stability_score,
                data_quality=data_quality
            )
            if ht_over:
                signals.append(ht_over)

            # Second-half over (FT - HT)
            sh_len = min(len(goal_history), len(ht_goal_history))
            if sh_len >= 5:
                sh_goals = [goal_history[i] - ht_goal_history[i]
                            for i in range(sh_len)]
                sh_over = self._detect_second_half_over(
                    match=match, sh_goals=sh_goals,
                    variance_score=variance_score, stability_score=stability_score,
                    data_quality=data_quality
                )
                if sh_over:
                    signals.append(sh_over)

        # ── BTTS + Home/Away over (requires match_history) ─────────────────
        if match_history and len(match_history) >= 5:
            btts_sig = self._detect_btts(
                match=match, match_history=match_history,
                variance_score=variance_score, stability_score=stability_score,
                data_quality=data_quality
            )
            if btts_sig:
                signals.append(btts_sig)

            home_over = self._detect_home_over(
                match=match, match_history=match_history,
                variance_score=variance_score, stability_score=stability_score,
                data_quality=data_quality
            )
            if home_over:
                signals.append(home_over)

            away_over = self._detect_away_over(
                match=match, match_history=match_history,
                variance_score=variance_score, stability_score=stability_score,
                data_quality=data_quality
            )
            if away_over:
                signals.append(away_over)

        logger.debug(f"[SIGNAL] {len(signals)} signals: "
                     f"{[s.signal_type for s in signals]}")
        return signals
    
    def _detect_extreme_under(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        line_analyses: Dict[float, Any],
        max_goals: int,
        avg_goals: float,
        hit_rates_by_line: Dict[float, float],
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect extreme under profile"""
        
        # Criteria: Very low scoring with high consistency
        if avg_goals > 5.0:
            return None
        
        # Find lines with 100% hit rate
        perfect_lines = [
            line for line, analysis in line_analyses.items()
            if analysis.hit_rate >= 0.95 and line > max_goals
        ]
        
        if not perfect_lines:
            return None
        
        # Determine strength
        if avg_goals < 3.0 and variance_score >= 0.8:
            strength = SignalStrength.EXTREME
            confidence = 0.9
        elif avg_goals < 4.0 and variance_score >= 0.7:
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.7
        
        # Phase 5: Allowed best pick lines only
        ALLOWED_UNDER_LINES = [4.5]  # 5.5/6.5/7.5/10.5/12.5 banned unless bookmaker odd > 3.0
        suggested_markets = []
        compatible_lines = []

        for line in ALLOWED_UNDER_LINES:
            if line > max_goals:
                suggested_markets.append(f"UNDER_{str(line).replace('.', '_')}")
                compatible_lines.append(line)
        
        # Reasons - Human-readable context
        reasons = [
            f"Extreme under profile: {len(goal_history)} matches avg {avg_goals:.1f} goals",
            f"No match exceeded {max_goals} goals in history",
            f"Low variance pattern (score: {variance_score:.2f}) = stable defensive behavior",
            f"{len(perfect_lines)} lines with 95%+ hit rate (e.g., U{perfect_lines[0] if perfect_lines else 'N/A'})",
            f"Consistent pattern suggests strong defensive structure"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.EXTREME_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            signal_category="STATISTICAL",  # Pure statistical pattern, no odds yet
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.7, max_goals * 1.2),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max_goals,
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            bookmaker_odd=None,
            fair_odd=None,
            edge_percent=None,
            reasons=reasons
        )
    
    def _detect_ht_under(
        self,
        match: Dict[str, Any],
        ht_goal_history: List[int],
        variance_score: float,
        stability_score: float,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect HT under profile"""
        
        if len(ht_goal_history) < 5:
            return None
        
        # Analyze HT lines
        ht_line_analyses = self.line_analyzer.analyze_all_lines(ht_goal_history)
        ht_hit_rates = {
            line: analysis.hit_rate
            for line, analysis in ht_line_analyses.items()
        }
        
        max_ht_goals = max(ht_goal_history)
        avg_ht_goals = sum(ht_goal_history) / len(ht_goal_history)
        
        # Check for strong HT under pattern
        under_1_5_rate = ht_hit_rates.get(1.5, 0)
        
        if under_1_5_rate < 0.70:
            return None
        
        # Determine strength
        if under_1_5_rate >= 0.90:
            strength = SignalStrength.EXTREME
            confidence = 0.9
        elif under_1_5_rate >= 0.80:
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.7
        
        # Suggested markets
        suggested_markets = ["HT_UNDER_0_5", "HT_UNDER_1_5"]
        compatible_lines = [0.5, 1.5]
        
        if max_ht_goals <= 1:
            suggested_markets.append("HT_UNDER_2_5")
            compatible_lines.append(2.5)
        
        reasons = [
            f"Strong HT under profile: {len(ht_goal_history)} matches",
            f"HT Under 1.5 hit rate: {under_1_5_rate*100:.0f}% ({int(under_1_5_rate*len(ht_goal_history))}/{len(ht_goal_history)} matches)",
            f"HT average: {avg_ht_goals:.1f} goals (slow first half tendency)",
            f"HT max: {max_ht_goals} goals (no explosive starts)",
            f"Consistent HT pattern suggests defensive early play"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.HT_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            signal_category="STATISTICAL",
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(0, max_ht_goals * 1.2),
            historical_hit_rates_by_line=ht_hit_rates,
            max_observed_goals=max_ht_goals,
            avg_goals=avg_ht_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=len(ht_goal_history),
            data_quality=data_quality,
            bookmaker_odd=None,
            fair_odd=None,
            edge_percent=None,
            reasons=reasons
        )
    
    def _detect_ft_under(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        line_analyses: Dict[float, Any],
        avg_goals: float,
        hit_rates_by_line: Dict[float, float],
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect FT under profile"""
        
        # Check for moderate under pattern
        under_2_5_rate = hit_rates_by_line.get(2.5, 0)
        under_3_5_rate = hit_rates_by_line.get(3.5, 0)
        
        if under_2_5_rate < 0.60:
            return None
        
        # Determine strength
        if under_2_5_rate >= 0.85:
            strength = SignalStrength.STRONG
            confidence = 0.85
        elif under_2_5_rate >= 0.75:
            strength = SignalStrength.MODERATE
            confidence = 0.75
        else:
            strength = SignalStrength.WEAK
            confidence = 0.65
        
        # Suggested markets
        suggested_markets = ["UNDER_2_5"]
        compatible_lines = [2.5]
        
        if under_3_5_rate >= 0.80:
            suggested_markets.append("UNDER_3_5")
            compatible_lines.append(3.5)
        
        reasons = [
            f"FT under profile: {len(goal_history)} matches avg {avg_goals:.1f} goals",
            f"Under 2.5 hit rate: {under_2_5_rate*100:.0f}% ({int(under_2_5_rate*len(goal_history))}/{len(goal_history)} matches)",
            f"Stable scoring pattern (variance score: {variance_score:.2f})",
            f"Consistent defensive behavior in recent history"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.FT_UNDER.value,
            signal_strength=strength.value,
            confidence=confidence,
            signal_category="STATISTICAL",
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.6, avg_goals * 1.4),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max(goal_history),
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            bookmaker_odd=None,
            fair_odd=None,
            edge_percent=None,
            reasons=reasons
        )
    
    def _detect_low_variance(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        variance: float,
        variance_score: float,
        stability_score: float,
        hit_rates_by_line: Dict[float, float],
        sample_size: int,
        data_quality: float
    ) -> Optional[StatisticalSignal]:
        """Detect low variance pattern"""
        
        avg_goals = sum(goal_history) / len(goal_history)
        max_goals = max(goal_history)
        
        # Determine strength
        if variance < 0.5:
            strength = SignalStrength.EXTREME
            confidence = 0.95
        elif variance < 1.0:
            strength = SignalStrength.STRONG
            confidence = 0.85
        else:
            strength = SignalStrength.MODERATE
            confidence = 0.75
        
        # Suggested markets based on average
        suggested_markets = []
        compatible_lines = []
        
        target_line = avg_goals + 1.5
        for line in [2.5, 3.5, 4.5, 5.5]:
            if line >= target_line:
                suggested_markets.append(f"UNDER_{line}")
                compatible_lines.append(line)
                if len(compatible_lines) >= 3:
                    break
        
        reasons = [
            f"Very low variance detected ({variance:.2f})",
            f"Consistent scoring pattern",
            f"Average: {avg_goals:.1f} goals",
            f"Stability score: {stability_score:.2f}"
        ]
        
        return StatisticalSignal(
            signal_type=SignalType.LOW_VARIANCE.value,
            signal_strength=strength.value,
            confidence=confidence,
            signal_category="STATISTICAL",
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=(avg_goals * 0.8, avg_goals * 1.2),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max_goals,
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            bookmaker_odd=None,
            fair_odd=None,
            edge_percent=None,
            reasons=reasons
        )
    
    # ── Phase 1: OVER / BTTS / SH signal detectors ───────────────────────

    def _make_signal(
        self,
        match: Dict[str, Any],
        signal_type: str,
        signal_strength: str,
        confidence: float,
        suggested_markets: List[str],
        compatible_lines: List[float],
        avg_goals: float,
        max_observed_goals: int,
        hit_rates_by_line: Dict[float, float],
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float,
        reasons: List[str],
        expected_goal_range: Optional[Tuple[float, float]] = None,
    ) -> StatisticalSignal:
        return StatisticalSignal(
            signal_type=signal_type,
            signal_strength=signal_strength,
            confidence=confidence,
            signal_category="STATISTICAL",
            match_id=match.get("match_id", ""),
            home_team=match.get("home_team", ""),
            away_team=match.get("away_team", ""),
            competition=match.get("competition", ""),
            country=match.get("country", ""),
            suggested_markets=suggested_markets,
            compatible_lines=compatible_lines,
            expected_goal_range=expected_goal_range or (avg_goals * 0.8, avg_goals * 1.5),
            historical_hit_rates_by_line=hit_rates_by_line,
            max_observed_goals=max_observed_goals,
            avg_goals=avg_goals,
            variance_score=variance_score,
            stability_score=stability_score,
            sample_size=sample_size,
            data_quality=data_quality,
            bookmaker_odd=None,
            fair_odd=None,
            edge_percent=None,
            reasons=reasons,
        )

    def _detect_ft_over(
        self,
        match: Dict[str, Any],
        goal_history: List[int],
        avg_goals: float,
        variance_score: float,
        stability_score: float,
        sample_size: int,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect FT OVER profile."""
        n = len(goal_history)
        over_2_5 = sum(1 for g in goal_history if g > 2.5) / n
        over_1_5 = sum(1 for g in goal_history if g > 1.5) / n
        max_g    = max(goal_history)

        if avg_goals < 2.2 or over_1_5 < 0.55:
            return None

        if avg_goals >= 3.2 and over_2_5 >= 0.70:
            strength, conf = SignalStrength.STRONG.value, 0.82
            markets = ["FT_OVER_2_5", "FT_OVER_1_5"]
            lines   = [2.5, 1.5]
        elif avg_goals >= 2.7 and over_2_5 >= 0.60:
            strength, conf = SignalStrength.MODERATE.value, 0.72
            markets = ["FT_OVER_2_5", "FT_OVER_1_5"]
            lines   = [2.5, 1.5]
        elif over_1_5 >= 0.72:
            strength, conf = SignalStrength.MODERATE.value, 0.68
            markets = ["FT_OVER_1_5"]
            lines   = [1.5]
        else:
            return None

        over_3_5 = sum(1 for g in goal_history if g > 3.5) / n
        if over_3_5 >= 0.50:
            markets.append("FT_OVER_3_5")
            lines.append(3.5)

        hrs = {1.5: over_1_5, 2.5: over_2_5, 3.5: over_3_5}
        reasons = [
            f"FT OVER profile: {n} matches avg {avg_goals:.1f} goals",
            f"Over 1.5 rate: {over_1_5*100:.0f}% ({int(over_1_5*n)}/{n})",
            f"Over 2.5 rate: {over_2_5*100:.0f}% ({int(over_2_5*n)}/{n})",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.FT_OVER.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=markets, compatible_lines=lines,
            avg_goals=avg_goals, max_observed_goals=max_g,
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=sample_size,
            data_quality=data_quality, reasons=reasons,
            expected_goal_range=(avg_goals * 0.8, avg_goals * 1.5),
        )

    def _detect_ht_over(
        self,
        match: Dict[str, Any],
        ht_goal_history: List[int],
        variance_score: float,
        stability_score: float,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect HT OVER profile."""
        n = len(ht_goal_history)
        avg_ht  = sum(ht_goal_history) / n
        max_ht  = max(ht_goal_history)
        o05     = sum(1 for g in ht_goal_history if g > 0.5) / n
        o10     = sum(1 for g in ht_goal_history if g > 1.0) / n
        o15     = sum(1 for g in ht_goal_history if g > 1.5) / n

        if avg_ht < 0.65 or o05 < 0.50:
            return None

        if avg_ht >= 1.4 and o10 >= 0.60:
            strength, conf = SignalStrength.STRONG.value, 0.80
            markets = ["HT_OVER_1_0", "HT_OVER_0_5"]
            lines   = [1.0, 0.5]
        elif o05 >= 0.70:
            strength, conf = SignalStrength.MODERATE.value, 0.70
            markets = ["HT_OVER_0_5"]
            lines   = [0.5]
        else:
            return None

        if o15 >= 0.45:
            markets.append("HT_OVER_1_5")
            lines.append(1.5)

        hrs = {0.5: o05, 1.0: o10, 1.5: o15}
        reasons = [
            f"HT OVER profile: {n} matches avg {avg_ht:.1f} HT goals",
            f"HT Over 0.5 rate: {o05*100:.0f}% ({int(o05*n)}/{n})",
            f"HT Over 1.0 rate: {o10*100:.0f}% ({int(o10*n)}/{n})",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.HT_OVER.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=markets, compatible_lines=lines,
            avg_goals=avg_ht, max_observed_goals=max_ht,
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=n,
            data_quality=data_quality, reasons=reasons,
            expected_goal_range=(avg_ht * 0.7, avg_ht * 1.6),
        )

    def _detect_second_half_over(
        self,
        match: Dict[str, Any],
        sh_goals: List[int],
        variance_score: float,
        stability_score: float,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect second-half OVER 1.5 profile."""
        n = len(sh_goals)
        avg_sh = sum(sh_goals) / n
        o15    = sum(1 for g in sh_goals if g > 1.5) / n
        o10    = sum(1 for g in sh_goals if g > 1.0) / n
        max_sh = max(sh_goals)

        if avg_sh < 1.1 or o15 < 0.45:
            return None

        if o15 >= 0.65:
            strength, conf = SignalStrength.STRONG.value, 0.78
        elif o15 >= 0.55:
            strength, conf = SignalStrength.MODERATE.value, 0.68
        else:
            return None

        hrs = {1.0: o10, 1.5: o15}
        markets = ["SECOND_HALF_OVER_1_5"]
        lines   = [1.5]
        if o10 >= 0.70:
            markets.insert(0, "SECOND_HALF_OVER_0_5")
            lines.insert(0, 0.5)

        reasons = [
            f"Second-half OVER profile: {n} matches avg {avg_sh:.1f} SH goals",
            f"SH Over 1.5 rate: {o15*100:.0f}% ({int(o15*n)}/{n})",
            f"High second-half activity consistently detected",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.SECOND_HALF_EXPLOSION.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=markets, compatible_lines=lines,
            avg_goals=avg_sh, max_observed_goals=max_sh,
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=n,
            data_quality=data_quality, reasons=reasons,
        )

    def _detect_btts(
        self,
        match: Dict[str, Any],
        match_history: List[Dict[str, Any]],
        variance_score: float,
        stability_score: float,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect BTTS YES profile."""
        n     = len(match_history)
        btts  = sum(
            1 for m in match_history
            if (m.get("home_goals", 0) or 0) > 0 and (m.get("away_goals", 0) or 0) > 0
        )
        rate  = btts / n

        if rate < 0.60:
            return None

        if rate >= 0.80:
            strength, conf = SignalStrength.STRONG.value, 0.82
        elif rate >= 0.70:
            strength, conf = SignalStrength.MODERATE.value, 0.72
        else:
            strength, conf = SignalStrength.WEAK.value, 0.62

        avg_g = sum((m.get("home_goals", 0) or 0) + (m.get("away_goals", 0) or 0)
                    for m in match_history) / n
        hrs   = {0.0: rate}
        reasons = [
            f"BTTS rate: {rate*100:.0f}% ({btts}/{n})",
            f"Both teams scored consistently in {btts} of {n} matches",
            f"Avg total goals: {avg_g:.1f}",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.BTTS_PROFILE.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=["BTTS_YES"], compatible_lines=[0.0],
            avg_goals=avg_g, max_observed_goals=int(avg_g * 2),
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=n,
            data_quality=data_quality, reasons=reasons,
        )

    def _detect_home_over(
        self,
        match: Dict[str, Any],
        match_history: List[Dict[str, Any]],
        variance_score: float,
        stability_score: float,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect HOME OVER 0.5 profile."""
        n        = len(match_history)
        scored   = sum(1 for m in match_history if (m.get("home_goals", 0) or 0) > 0)
        rate     = scored / n
        avg_home = sum((m.get("home_goals", 0) or 0) for m in match_history) / n

        if rate < 0.70 or avg_home < 0.9:
            return None

        strength = SignalStrength.STRONG.value if rate >= 0.85 else SignalStrength.MODERATE.value
        conf     = 0.76 if rate >= 0.85 else 0.66

        hrs = {0.5: rate}
        reasons = [
            f"Home OVER 0.5 rate: {rate*100:.0f}% ({scored}/{n})",
            f"Home team scores in {rate*100:.0f}% of matches",
            f"Avg home goals: {avg_home:.1f}",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.HOME_DOMINANT.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=["HOME_OVER_0_5"], compatible_lines=[0.5],
            avg_goals=avg_home, max_observed_goals=int(avg_home * 2 + 1),
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=n,
            data_quality=data_quality, reasons=reasons,
        )

    def _detect_away_over(
        self,
        match: Dict[str, Any],
        match_history: List[Dict[str, Any]],
        variance_score: float,
        stability_score: float,
        data_quality: float,
    ) -> Optional[StatisticalSignal]:
        """Detect AWAY OVER 0.5 profile."""
        n        = len(match_history)
        scored   = sum(1 for m in match_history if (m.get("away_goals", 0) or 0) > 0)
        rate     = scored / n
        avg_away = sum((m.get("away_goals", 0) or 0) for m in match_history) / n

        if rate < 0.65 or avg_away < 0.75:
            return None

        strength = SignalStrength.STRONG.value if rate >= 0.80 else SignalStrength.MODERATE.value
        conf     = 0.74 if rate >= 0.80 else 0.64

        hrs = {0.5: rate}
        reasons = [
            f"Away OVER 0.5 rate: {rate*100:.0f}% ({scored}/{n})",
            f"Away team scores in {rate*100:.0f}% of matches",
            f"Avg away goals: {avg_away:.1f}",
        ]
        return self._make_signal(
            match=match, signal_type=SignalType.ASYMMETRIC_SCORING.value,
            signal_strength=strength, confidence=conf,
            suggested_markets=["AWAY_OVER_0_5"], compatible_lines=[0.5],
            avg_goals=avg_away, max_observed_goals=int(avg_away * 2 + 1),
            hit_rates_by_line=hrs, variance_score=variance_score,
            stability_score=stability_score, sample_size=n,
            data_quality=data_quality, reasons=reasons,
        )

    def _calculate_variance(self, values: List[int]) -> float:
        """Calculate variance"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def _variance_to_score(self, variance: float) -> float:
        """Convert variance to 0-1 score (lower variance = higher score)"""
        # Variance < 1.0 = excellent (0.9+)
        # Variance 1.0-2.0 = good (0.7-0.9)
        # Variance 2.0-3.0 = moderate (0.5-0.7)
        # Variance > 3.0 = poor (< 0.5)
        
        if variance < 1.0:
            return 0.9 + (1.0 - variance) * 0.1
        elif variance < 2.0:
            return 0.7 + (2.0 - variance) * 0.2
        elif variance < 3.0:
            return 0.5 + (3.0 - variance) * 0.2
        else:
            return max(0.0, 0.5 - (variance - 3.0) * 0.1)
    
    def _calculate_stability(self, values: List[int]) -> float:
        """Calculate stability score (0-1)"""
        if len(values) < 5:
            return 0.5
        
        # Check consistency in recent vs older matches
        recent = values[-5:]
        older = values[:-5] if len(values) > 5 else values
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg
        
        # Lower difference = higher stability
        diff = abs(recent_avg - older_avg)
        
        if diff < 0.5:
            return 0.95
        elif diff < 1.0:
            return 0.85
        elif diff < 1.5:
            return 0.75
        elif diff < 2.0:
            return 0.65
        else:
            return 0.50
    
    def _calculate_data_quality(self, sample_size: int, variance: float) -> float:
        """Calculate overall data quality (0-1)"""
        
        # Sample size component
        if sample_size >= 15:
            size_score = 1.0
        elif sample_size >= 10:
            size_score = 0.8
        elif sample_size >= 5:
            size_score = 0.6
        else:
            size_score = 0.4
        
        # Variance component
        variance_score = self._variance_to_score(variance)
        
        # Weighted average
        quality = (size_score * 0.6) + (variance_score * 0.4)
        
        return quality
