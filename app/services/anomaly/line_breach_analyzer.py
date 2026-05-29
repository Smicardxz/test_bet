"""
Line Breach Analyzer
Critical component for detecting bookmaker inefficiencies

Analyzes historical hit rates for every possible line
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LineBreachAnalysis:
    """Analysis for a specific line"""
    line: float
    
    # Hit rates
    hit_rate: float  # % matches under this line
    breach_rate: float  # % matches over this line
    
    # Distance metrics
    avg_distance_to_line: float  # Average goals distance from line
    max_distance: int  # Max goals over/under line
    
    # Stability
    variance: float
    consistency: float  # How consistent is the under rate
    
    # Sample
    sample_size: int
    matches_under: int
    matches_over: int
    
    # Trend
    recent_trend: str  # "STABLE", "INCREASING", "DECREASING"
    
    def is_inefficient_line(self, threshold: float = 0.90) -> bool:
        """Check if this line appears inefficient"""
        # Line is inefficient if:
        # 1. Very high hit rate (>90%)
        # 2. Large distance from line
        # 3. Good sample size
        return (
            self.hit_rate >= threshold and
            abs(self.avg_distance_to_line) > 2.0 and
            self.sample_size >= 5
        )


class LineBreachAnalyzer:
    """
    Analyzes historical data to calculate hit rates for all possible lines
    
    This is the core component for detecting bookmaker inefficiencies
    """
    
    # Standard lines to analyze
    STANDARD_LINES = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5]
    
    def __init__(self):
        """Initialize analyzer"""
        logger.info("LineBreachAnalyzer initialized")
    
    def analyze_all_lines(self, goal_history: List[int]) -> Dict[float, LineBreachAnalysis]:
        """
        Analyze all standard lines against goal history
        
        Args:
            goal_history: List of total goals from historical matches
            
        Returns:
            Dict mapping line to analysis
        """
        if not goal_history:
            return {}
        
        analyses = {}
        
        for line in self.STANDARD_LINES:
            analysis = self.analyze_line(line, goal_history)
            analyses[line] = analysis
        
        return analyses
    
    def analyze_line(self, line: float, goal_history: List[int]) -> LineBreachAnalysis:
        """
        Analyze a specific line
        
        Args:
            line: The line to analyze (e.g., 2.5)
            goal_history: List of total goals
            
        Returns:
            LineBreachAnalysis
        """
        if not goal_history:
            return self._empty_analysis(line)
        
        sample_size = len(goal_history)
        
        # Count under/over
        matches_under = sum(1 for goals in goal_history if goals < line)
        matches_over = sum(1 for goals in goal_history if goals >= line)
        
        # Hit rates
        hit_rate = matches_under / sample_size if sample_size > 0 else 0
        breach_rate = matches_over / sample_size if sample_size > 0 else 0
        
        # Distance metrics
        distances = [goals - line for goals in goal_history]
        avg_distance = sum(distances) / len(distances) if distances else 0
        max_distance = max(abs(d) for d in distances) if distances else 0
        
        # Variance
        if len(goal_history) > 1:
            mean_goals = sum(goal_history) / len(goal_history)
            variance = sum((g - mean_goals) ** 2 for g in goal_history) / len(goal_history)
        else:
            variance = 0
        
        # Consistency (how stable is the under rate)
        consistency = self._calculate_consistency(goal_history, line)
        
        # Trend (recent matches)
        recent_trend = self._calculate_trend(goal_history, line)
        
        return LineBreachAnalysis(
            line=line,
            hit_rate=hit_rate,
            breach_rate=breach_rate,
            avg_distance_to_line=avg_distance,
            max_distance=int(max_distance),
            variance=variance,
            consistency=consistency,
            sample_size=sample_size,
            matches_under=matches_under,
            matches_over=matches_over,
            recent_trend=recent_trend
        )
    
    def find_inefficient_lines(
        self,
        goal_history: List[int],
        min_hit_rate: float = 0.85
    ) -> List[LineBreachAnalysis]:
        """
        Find lines that appear inefficient (very high hit rate)
        
        Args:
            goal_history: Historical goals
            min_hit_rate: Minimum hit rate to consider inefficient
            
        Returns:
            List of inefficient line analyses
        """
        all_analyses = self.analyze_all_lines(goal_history)
        
        inefficient = [
            analysis for analysis in all_analyses.values()
            if analysis.is_inefficient_line(min_hit_rate)
        ]
        
        # Sort by hit rate descending
        inefficient.sort(key=lambda x: x.hit_rate, reverse=True)
        
        return inefficient
    
    def suggest_lines_for_market(
        self,
        goal_history: List[int],
        market_type: str = "under"
    ) -> List[float]:
        """
        Suggest which lines to target based on history
        
        Args:
            goal_history: Historical goals
            market_type: "under" or "over"
            
        Returns:
            List of suggested lines
        """
        if not goal_history:
            return []
        
        max_goals = max(goal_history)
        avg_goals = sum(goal_history) / len(goal_history)
        
        if market_type == "under":
            # Suggest lines above historical max
            suggested = [
                line for line in self.STANDARD_LINES
                if line > max_goals and line <= max_goals + 5
            ]
        else:
            # Suggest lines near average
            suggested = [
                line for line in self.STANDARD_LINES
                if abs(line - avg_goals) <= 2.0
            ]
        
        return suggested[:5]  # Top 5 suggestions
    
    def _calculate_consistency(self, goal_history: List[int], line: float) -> float:
        """Calculate how consistent the under rate is"""
        if len(goal_history) < 5:
            return 0.0
        
        # Split into windows and check variance of hit rates
        window_size = 5
        hit_rates = []
        
        for i in range(len(goal_history) - window_size + 1):
            window = goal_history[i:i + window_size]
            under_count = sum(1 for g in window if g < line)
            hit_rates.append(under_count / window_size)
        
        if not hit_rates:
            return 0.0
        
        # Low variance in hit rates = high consistency
        mean_hit_rate = sum(hit_rates) / len(hit_rates)
        variance = sum((hr - mean_hit_rate) ** 2 for hr in hit_rates) / len(hit_rates)
        
        # Convert to 0-1 scale (lower variance = higher consistency)
        consistency = max(0, 1 - (variance * 4))  # Scale factor
        
        return consistency
    
    def _calculate_trend(self, goal_history: List[int], line: float) -> str:
        """Calculate recent trend"""
        if len(goal_history) < 6:
            return "STABLE"
        
        # Compare recent vs older
        recent = goal_history[-5:]
        older = goal_history[-10:-5] if len(goal_history) >= 10 else goal_history[:-5]
        
        recent_under_rate = sum(1 for g in recent if g < line) / len(recent)
        older_under_rate = sum(1 for g in older if g < line) / len(older) if older else recent_under_rate
        
        diff = recent_under_rate - older_under_rate
        
        if diff > 0.2:
            return "INCREASING"  # More unders recently
        elif diff < -0.2:
            return "DECREASING"  # Fewer unders recently
        else:
            return "STABLE"
    
    def _empty_analysis(self, line: float) -> LineBreachAnalysis:
        """Return empty analysis"""
        return LineBreachAnalysis(
            line=line,
            hit_rate=0.0,
            breach_rate=0.0,
            avg_distance_to_line=0.0,
            max_distance=0,
            variance=0.0,
            consistency=0.0,
            sample_size=0,
            matches_under=0,
            matches_over=0,
            recent_trend="UNKNOWN"
        )
