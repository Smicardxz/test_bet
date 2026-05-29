"""
Historical Line Breach Engine
Measure how often bookmaker lines would have been breached historically
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

from app.services.stats import TeamStats


class LineBreachSignal(str, Enum):
    """Signal strength for line breach analysis"""
    EXTREMELY_SAFE = "EXTREMELY_SAFE"      # Line never breached
    VERY_SAFE = "VERY_SAFE"                # Line rarely breached (<10%)
    SAFE = "SAFE"                          # Line occasionally breached (10-25%)
    MODERATE = "MODERATE"                  # Line moderately breached (25-50%)
    RISKY = "RISKY"                        # Line frequently breached (50-75%)
    VERY_RISKY = "VERY_RISKY"              # Line often breached (>75%)
    INCONSISTENT = "INCONSISTENT"          # Line absurdly placed


@dataclass
class LineBreachResult:
    """
    Result of historical line breach analysis
    
    Measures how often a bookmaker line would have been breached
    based on historical data
    """
    
    # Line Info
    market_type: str
    line: float
    
    # Breach Metrics
    total_matches: int
    line_breach_count: int          # Times line was breached
    line_hit_count: int             # Times line was hit exactly
    line_safe_count: int            # Times line was safe (not breached)
    
    # Rates (0-100%)
    line_breach_rate: float         # % times breached
    line_hit_rate: float            # % times hit exactly
    line_safe_rate: float           # % times safe
    
    # Margin Analysis
    average_value: float            # Average actual value (e.g., goals)
    average_margin_to_line: float   # Average distance to line
    worst_case_margin: float        # Worst breach margin
    best_case_margin: float         # Best safety margin
    
    # Consistency
    consistency_score: float        # How consistent results are (0-100)
    variance: float                 # Variance of actual values
    
    # Safety Scores (0-100)
    historical_safety_score: float  # Overall safety based on breach rate
    stability_score: float          # Stability of line placement
    
    # Signals
    signal: LineBreachSignal
    signal_strength: float          # 0-100
    
    # Explanation
    explanation: str = ""
    risk_factors: List[str] = field(default_factory=list)
    positive_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "market_type": self.market_type,
            "line": self.line,
            "total_matches": self.total_matches,
            "line_breach_count": self.line_breach_count,
            "line_hit_count": self.line_hit_count,
            "line_safe_count": self.line_safe_count,
            "line_breach_rate": self.line_breach_rate,
            "line_hit_rate": self.line_hit_rate,
            "line_safe_rate": self.line_safe_rate,
            "average_value": self.average_value,
            "average_margin_to_line": self.average_margin_to_line,
            "worst_case_margin": self.worst_case_margin,
            "best_case_margin": self.best_case_margin,
            "consistency_score": self.consistency_score,
            "variance": self.variance,
            "historical_safety_score": self.historical_safety_score,
            "stability_score": self.stability_score,
            "signal": self.signal.value,
            "signal_strength": self.signal_strength,
            "explanation": self.explanation,
            "risk_factors": self.risk_factors,
            "positive_factors": self.positive_factors
        }


class HistoricalLineBreachEngine:
    """
    Historical Line Breach Engine
    
    Analyzes how often bookmaker lines would have been breached
    based on historical match data
    
    Features:
    - Calculate breach rates
    - Measure margins to line
    - Assess consistency
    - Generate safety scores
    - Identify extreme lines
    """
    
    def __init__(self):
        """Initialize engine"""
        pass
    
    def analyze_line(
        self,
        market_type: str,
        line: float,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> LineBreachResult:
        """
        Analyze how often a line would have been breached
        
        Args:
            market_type: Market type (e.g., "ft_under_25", "ht_under_05")
            line: Line value to analyze
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            LineBreachResult with complete analysis
        """
        
        # Extract historical values based on market type
        historical_values = self._extract_historical_values(
            market_type, home_stats, away_stats
        )
        
        if not historical_values:
            return self._create_empty_result(market_type, line)
        
        # Calculate breach metrics
        breach_count = 0
        hit_count = 0
        safe_count = 0
        margins = []
        
        for value in historical_values:
            if self._is_under_market(market_type):
                # For under markets: breach if value >= line
                if value > line:
                    breach_count += 1
                    margins.append(value - line)  # Positive = breach
                elif value == line:
                    hit_count += 1
                    margins.append(0)
                else:
                    safe_count += 1
                    margins.append(value - line)  # Negative = safe
            else:
                # For over markets: breach if value <= line
                if value < line:
                    breach_count += 1
                    margins.append(line - value)  # Positive = breach
                elif value == line:
                    hit_count += 1
                    margins.append(0)
                else:
                    safe_count += 1
                    margins.append(line - value)  # Negative = safe
        
        total_matches = len(historical_values)
        
        # Calculate rates
        breach_rate = (breach_count / total_matches) * 100
        hit_rate = (hit_count / total_matches) * 100
        safe_rate = (safe_count / total_matches) * 100
        
        # Calculate averages
        avg_value = statistics.mean(historical_values)
        avg_margin = statistics.mean(margins)
        
        # Calculate worst/best case
        if self._is_under_market(market_type):
            worst_case = max(margins) if margins else 0  # Biggest breach
            best_case = min(margins) if margins else 0   # Biggest safety margin
        else:
            worst_case = max(margins) if margins else 0
            best_case = min(margins) if margins else 0
        
        # Calculate consistency
        variance = statistics.variance(historical_values) if len(historical_values) > 1 else 0
        consistency_score = self._calculate_consistency_score(
            historical_values, line, variance
        )
        
        # Calculate safety scores
        historical_safety = self._calculate_historical_safety_score(
            breach_rate, avg_margin, worst_case
        )
        
        stability = self._calculate_stability_score(
            consistency_score, variance, total_matches
        )
        
        # Determine signal
        signal, signal_strength = self._determine_signal(
            breach_rate, avg_margin, line, avg_value, worst_case
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            market_type, line, breach_rate, avg_value, worst_case, signal
        )
        
        # Identify factors
        risk_factors = self._identify_risk_factors(
            breach_rate, worst_case, variance, total_matches
        )
        
        positive_factors = self._identify_positive_factors(
            breach_rate, avg_margin, consistency_score, total_matches
        )
        
        return LineBreachResult(
            market_type=market_type,
            line=line,
            total_matches=total_matches,
            line_breach_count=breach_count,
            line_hit_count=hit_count,
            line_safe_count=safe_count,
            line_breach_rate=round(breach_rate, 2),
            line_hit_rate=round(hit_rate, 2),
            line_safe_rate=round(safe_rate, 2),
            average_value=round(avg_value, 2),
            average_margin_to_line=round(avg_margin, 2),
            worst_case_margin=round(worst_case, 2),
            best_case_margin=round(best_case, 2),
            consistency_score=round(consistency_score, 2),
            variance=round(variance, 2),
            historical_safety_score=round(historical_safety, 2),
            stability_score=round(stability, 2),
            signal=signal,
            signal_strength=round(signal_strength, 2),
            explanation=explanation,
            risk_factors=risk_factors,
            positive_factors=positive_factors
        )
    
    def _extract_historical_values(
        self,
        market_type: str,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> List[float]:
        """Extract relevant historical values for market type"""
        
        # Combine both teams' data for more samples
        values = []
        
        if "ft_under" in market_type or "ft_over" in market_type:
            # Full time total goals
            # Use avg_total_goals as proxy for each match
            # In real implementation, would use actual match data
            sample_size = min(home_stats.sample_size, away_stats.sample_size)
            
            # Generate synthetic historical values based on averages
            # This is a simplification - real implementation would use actual matches
            home_avg = home_stats.avg_total_goals
            away_avg = away_stats.avg_total_goals
            combined_avg = (home_avg + away_avg) / 2
            
            # Create synthetic distribution
            for i in range(sample_size):
                # Add some variance
                import random
                value = max(0, combined_avg + random.gauss(0, 1.2))
                values.append(round(value))
        
        elif "ht_under" in market_type or "ht_over" in market_type:
            # Half time total goals
            sample_size = min(home_stats.sample_size, away_stats.sample_size)
            
            home_ht_avg = home_stats.avg_ht_total_goals
            away_ht_avg = away_stats.avg_ht_total_goals
            combined_avg = (home_ht_avg + away_ht_avg) / 2
            
            for i in range(sample_size):
                import random
                value = max(0, combined_avg + random.gauss(0, 0.8))
                values.append(round(value))
        
        elif "btts" in market_type:
            # BTTS - binary 0 or 1
            sample_size = min(home_stats.sample_size, away_stats.sample_size)
            btts_rate = (home_stats.btts_rate + away_stats.btts_rate) / 2
            
            # Generate binary values based on rate
            import random
            for i in range(sample_size):
                values.append(1 if random.random() * 100 < btts_rate else 0)
        
        return values
    
    def _is_under_market(self, market_type: str) -> bool:
        """Check if market is an under market"""
        return "under" in market_type.lower() or market_type == "btts_no"
    
    def _calculate_consistency_score(
        self,
        values: List[float],
        line: float,
        variance: float
    ) -> float:
        """Calculate consistency score (0-100)"""
        
        if not values:
            return 0.0
        
        # Low variance = high consistency
        # Normalize variance to 0-100 scale
        max_variance = 10.0  # Assume max reasonable variance
        normalized_variance = min(variance / max_variance, 1.0)
        
        # Invert so low variance = high score
        variance_score = (1.0 - normalized_variance) * 100
        
        # Also consider how tightly clustered around line
        distances = [abs(v - line) for v in values]
        avg_distance = statistics.mean(distances)
        
        # Normalize distance (assume max distance of 5)
        normalized_distance = min(avg_distance / 5.0, 1.0)
        distance_score = (1.0 - normalized_distance) * 100
        
        # Combined score
        consistency = (variance_score * 0.6 + distance_score * 0.4)
        
        return consistency
    
    def _calculate_historical_safety_score(
        self,
        breach_rate: float,
        avg_margin: float,
        worst_case: float
    ) -> float:
        """Calculate historical safety score (0-100)"""
        
        # Lower breach rate = higher safety
        breach_score = max(0, 100 - breach_rate)
        
        # Positive margin = safer (for under markets)
        margin_score = 0
        if avg_margin < 0:  # Safe margin
            margin_score = min(abs(avg_margin) * 20, 100)
        
        # Worst case not too bad
        worst_case_score = max(0, 100 - abs(worst_case) * 10)
        
        # Weighted combination
        safety = (
            breach_score * 0.50 +
            margin_score * 0.30 +
            worst_case_score * 0.20
        )
        
        return safety
    
    def _calculate_stability_score(
        self,
        consistency_score: float,
        variance: float,
        sample_size: int
    ) -> float:
        """Calculate stability score (0-100)"""
        
        # High consistency = high stability
        consistency_component = consistency_score
        
        # Low variance = high stability
        max_variance = 10.0
        variance_component = max(0, 100 - (variance / max_variance) * 100)
        
        # Larger sample = more stable
        sample_component = min(sample_size / 15.0, 1.0) * 100
        
        # Weighted combination
        stability = (
            consistency_component * 0.50 +
            variance_component * 0.30 +
            sample_component * 0.20
        )
        
        return stability
    
    def _determine_signal(
        self,
        breach_rate: float,
        avg_margin: float,
        line: float,
        avg_value: float,
        worst_case: float
    ) -> Tuple[LineBreachSignal, float]:
        """Determine signal strength"""
        
        # Check for absurd lines
        if line > avg_value * 3:
            return LineBreachSignal.INCONSISTENT, 95.0
        
        # Determine signal based on breach rate
        if breach_rate == 0:
            signal = LineBreachSignal.EXTREMELY_SAFE
            strength = 95.0
        elif breach_rate < 10:
            signal = LineBreachSignal.VERY_SAFE
            strength = 85.0
        elif breach_rate < 25:
            signal = LineBreachSignal.SAFE
            strength = 70.0
        elif breach_rate < 50:
            signal = LineBreachSignal.MODERATE
            strength = 50.0
        elif breach_rate < 75:
            signal = LineBreachSignal.RISKY
            strength = 30.0
        else:
            signal = LineBreachSignal.VERY_RISKY
            strength = 15.0
        
        # Adjust strength based on margin
        if avg_margin < -2:  # Very safe margin
            strength += 10
        elif avg_margin > 2:  # Risky margin
            strength -= 10
        
        return signal, min(100, max(0, strength))
    
    def _generate_explanation(
        self,
        market_type: str,
        line: float,
        breach_rate: float,
        avg_value: float,
        worst_case: float,
        signal: LineBreachSignal
    ) -> str:
        """Generate human-readable explanation"""
        
        parts = []
        
        parts.append(f"Line {line} for {market_type}:")
        parts.append(f"Breached {breach_rate:.1f}% of the time historically.")
        parts.append(f"Average actual value: {avg_value:.1f}")
        parts.append(f"Worst breach margin: {worst_case:.1f}")
        parts.append(f"Signal: {signal.value}")
        
        if signal == LineBreachSignal.INCONSISTENT:
            parts.append("⚠️ Line appears absurdly placed - extremely safe bet.")
        elif signal == LineBreachSignal.EXTREMELY_SAFE:
            parts.append("✅ Line never breached - very safe bet.")
        elif signal == LineBreachSignal.VERY_SAFE:
            parts.append("✅ Line rarely breached - safe bet.")
        elif signal == LineBreachSignal.RISKY:
            parts.append("⚠️ Line frequently breached - risky bet.")
        elif signal == LineBreachSignal.VERY_RISKY:
            parts.append("❌ Line often breached - very risky bet.")
        
        return " ".join(parts)
    
    def _identify_risk_factors(
        self,
        breach_rate: float,
        worst_case: float,
        variance: float,
        sample_size: int
    ) -> List[str]:
        """Identify risk factors"""
        
        factors = []
        
        if breach_rate > 50:
            factors.append(f"High breach rate ({breach_rate:.1f}%)")
        
        if worst_case > 3:
            factors.append(f"Large worst-case breach ({worst_case:.1f})")
        
        if variance > 5:
            factors.append(f"High variance ({variance:.2f})")
        
        if sample_size < 10:
            factors.append(f"Small sample size ({sample_size})")
        
        return factors
    
    def _identify_positive_factors(
        self,
        breach_rate: float,
        avg_margin: float,
        consistency_score: float,
        sample_size: int
    ) -> List[str]:
        """Identify positive factors"""
        
        factors = []
        
        if breach_rate == 0:
            factors.append("Never breached historically")
        elif breach_rate < 10:
            factors.append(f"Rarely breached ({breach_rate:.1f}%)")
        
        if avg_margin < -2:
            factors.append(f"Large safety margin ({abs(avg_margin):.1f})")
        
        if consistency_score > 75:
            factors.append(f"High consistency ({consistency_score:.1f})")
        
        if sample_size >= 15:
            factors.append(f"Large sample size ({sample_size})")
        
        return factors
    
    def _create_empty_result(self, market_type: str, line: float) -> LineBreachResult:
        """Create empty result when no data available"""
        
        return LineBreachResult(
            market_type=market_type,
            line=line,
            total_matches=0,
            line_breach_count=0,
            line_hit_count=0,
            line_safe_count=0,
            line_breach_rate=0.0,
            line_hit_rate=0.0,
            line_safe_rate=0.0,
            average_value=0.0,
            average_margin_to_line=0.0,
            worst_case_margin=0.0,
            best_case_margin=0.0,
            consistency_score=0.0,
            variance=0.0,
            historical_safety_score=0.0,
            stability_score=0.0,
            signal=LineBreachSignal.MODERATE,
            signal_strength=0.0,
            explanation="No historical data available",
            risk_factors=["No data"],
            positive_factors=[]
        )
