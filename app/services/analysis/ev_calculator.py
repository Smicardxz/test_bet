"""
Phase 7: EV Calculator
Calculates Expected Value for each market given model probability and bookmaker odds.

Formula:
  implied_probability = 1 / bookmaker_odd
  edge = model_probability - implied_probability
  EV = model_probability * bookmaker_odd - 1

Output per market:
  - model_probability
  - bookmaker_implied_probability
  - fair_odd
  - bookmaker_odd
  - edge_percent
  - expected_value
  - confidence_interval (±)
  - verdict (STRONG_VALUE / VALUE / NEUTRAL / AVOID)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# EV thresholds
EV_EXTREME  = 0.20   # +20% EV = EXTREME value
EV_HIGH     = 0.12   # +12% EV = HIGH value
EV_MEDIUM   = 0.06   # +6%  EV = MEDIUM value
EV_LOW      = 0.02   # +2%  EV = LOW value
EV_NEUTRAL  = 0.00   # 0%   EV = neutral
# Below 0 = negative EV = NO_VALUE

# Legacy aliases
EV_STRONG_VALUE = EV_HIGH
EV_VALUE        = EV_MEDIUM


@dataclass
class EVResult:
    """EV result for a single market"""
    market_type: str
    line: Optional[float]

    # Probabilities
    model_probability: float       # 0-1 estimated by engine
    bookmaker_odd: float           # decimal odd
    implied_probability: float     # 1 / bookmaker_odd
    fair_odd: float                # 1 / model_probability

    # EV metrics
    edge: float                    # model_prob - implied_prob
    edge_percent: float            # edge * 100
    expected_value: float          # model_prob * odd - 1
    expected_value_percent: float  # EV * 100

    # Confidence interval (95% Wilson interval approximation)
    confidence_interval_low: float
    confidence_interval_high: float

    # Verdict (legacy)
    verdict: str                   # STRONG_VALUE / VALUE / NEUTRAL / AVOID

    # Phase 6: value_level for tier engine
    value_level: str = "NO_VALUE"  # NO_VALUE | LOW | MEDIUM | HIGH | EXTREME
    confidence: str = "LOW"        # LOW | MEDIUM | HIGH

    # Context
    sample_size: int = 0
    bookmaker: str = "unknown"
    signal_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market_type,
            "line": self.line,
            "model_probability": round(self.model_probability, 4),
            "bookmaker_odd": round(self.bookmaker_odd, 3),
            "implied_probability": round(self.implied_probability * 100, 2),
            "fair_odd": round(self.fair_odd, 3),
            "edge_percentage": round(self.edge_percent, 2),
            "ev_percentage": round(self.expected_value_percent, 2),
            "confidence_interval_low": round(self.confidence_interval_low, 4),
            "confidence_interval_high": round(self.confidence_interval_high, 4),
            "value_level": self.value_level,
            "confidence": self.confidence,
            "verdict": self.verdict,
            "sample_size": self.sample_size,
            "bookmaker": self.bookmaker,
            "signal_type": self.signal_type,
        }


class EVCalculator:
    """
    Phase 7: Expected Value Calculator

    Computes EV for each market given:
    - model_probability: estimated hit rate from historical data
    - bookmaker_odd: real decimal odd from TheOddsAPI
    - sample_size: number of historical matches used

    Never blocks analysis. Returns empty list if no odds present.
    """

    def calculate(
        self,
        model_probability: float,
        bookmaker_odd: float,
        market_type: str,
        line: Optional[float] = None,
        sample_size: int = 0,
        bookmaker: str = "unknown",
        signal_type: str = ""
    ) -> Optional[EVResult]:
        """
        Calculate EV for one market.

        Args:
            model_probability: 0-1 probability from signal engine
            bookmaker_odd: decimal odd from bookmaker
            market_type: string identifier
            line: optional line (e.g., 2.5)
            sample_size: historical sample count
            bookmaker: bookmaker name
            signal_type: signal identifier

        Returns:
            EVResult or None if inputs invalid
        """
        if not bookmaker_odd or bookmaker_odd <= 1.0:
            return None
        if not (0.0 < model_probability < 1.0):
            return None

        implied_probability = 1.0 / bookmaker_odd
        fair_odd = 1.0 / model_probability
        edge = model_probability - implied_probability
        edge_percent = edge * 100.0
        expected_value = model_probability * bookmaker_odd - 1.0
        expected_value_percent = expected_value * 100.0

        # Wilson confidence interval (95%)
        ci_low, ci_high = self._wilson_ci(model_probability, sample_size)

        verdict = self._verdict(expected_value)
        value_level = self._value_level(expected_value, edge)
        confidence_label = self._confidence_label(sample_size, ci_low, ci_high, model_probability)

        logger.debug(
            f"EV [{market_type}] prob={model_probability:.2%} odd={bookmaker_odd} "
            f"EV={expected_value_percent:.1f}% edge={edge_percent:.1f}% → {value_level}"
        )

        return EVResult(
            market_type=market_type,
            line=line,
            model_probability=model_probability,
            bookmaker_odd=bookmaker_odd,
            implied_probability=implied_probability,
            fair_odd=fair_odd,
            edge=edge,
            edge_percent=edge_percent,
            expected_value=expected_value,
            expected_value_percent=expected_value_percent,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            verdict=verdict,
            value_level=value_level,
            confidence=confidence_label,
            sample_size=sample_size,
            bookmaker=bookmaker,
            signal_type=signal_type,
        )

    def calculate_from_hit_rates(
        self,
        hit_rates: Dict[float, float],
        odds_by_line: Dict[float, float],
        market_prefix: str = "FT",
        direction: str = "UNDER",
        sample_size: int = 0,
        bookmaker: str = "unknown"
    ) -> List[EVResult]:
        """
        Calculate EV for multiple lines (e.g., FT Under 1.5/2.5/3.5).

        Args:
            hit_rates: {line: hit_rate} from signal engine
            odds_by_line: {line: bookmaker_odd} from odds provider
            market_prefix: "FT" or "HT"
            direction: "UNDER" or "OVER"
            sample_size: historical sample count
            bookmaker: bookmaker name

        Returns:
            List of EVResult for lines that have both hit_rate and bookmaker_odd
        """
        results = []
        for line, model_prob in hit_rates.items():
            bk_odd = odds_by_line.get(line)
            if not bk_odd:
                continue
            market_type = f"{market_prefix}_{direction}_{str(line).replace('.', '_')}"
            result = self.calculate(
                model_probability=model_prob,
                bookmaker_odd=bk_odd,
                market_type=market_type,
                line=line,
                sample_size=sample_size,
                bookmaker=bookmaker
            )
            if result:
                results.append(result)
        return results

    def best_ev(self, results: List[EVResult]) -> Optional[EVResult]:
        """Return the best EV result from a list (highest EV, minimum VALUE threshold)"""
        value_results = [r for r in results if r.expected_value > 0]
        if not value_results:
            return None
        return max(value_results, key=lambda r: r.expected_value)

    def _wilson_ci(self, p: float, n: int, z: float = 1.96) -> tuple:
        """Wilson score confidence interval for a proportion"""
        if n < 3:
            return (max(0, p - 0.15), min(1, p + 0.15))
        denominator = 1 + z ** 2 / n
        center = (p + z ** 2 / (2 * n)) / denominator
        margin = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denominator
        return (max(0.0, center - margin), min(1.0, center + margin))

    def _verdict(self, ev: float) -> str:
        """Legacy verdict string"""
        if ev >= EV_HIGH:
            return "STRONG_VALUE"
        elif ev >= EV_MEDIUM:
            return "VALUE"
        elif ev >= EV_NEUTRAL:
            return "NEUTRAL"
        else:
            return "AVOID"

    def _value_level(self, ev: float, edge: float) -> str:
        """Phase 6: Value level for tier engine"""
        if ev >= EV_EXTREME and edge >= 0.15:
            return "EXTREME"
        elif ev >= EV_HIGH and edge >= 0.08:
            return "HIGH"
        elif ev >= EV_MEDIUM and edge >= 0.04:
            return "MEDIUM"
        elif ev >= EV_LOW and edge >= 0.01:
            return "LOW"
        else:
            return "NO_VALUE"

    def _confidence_label(self, n: int, ci_low: float, ci_high: float, prob: float) -> str:
        """Assign confidence label from sample size + CI width"""
        ci_width = ci_high - ci_low
        if n >= 20 and ci_width <= 0.15:
            return "HIGH"
        elif n >= 10 and ci_width <= 0.25:
            return "MEDIUM"
        else:
            return "LOW"
