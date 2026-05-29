"""
Edge Detector - Bookmaker Mispricing Detection

Transforms the system from "statistical reporter" to "EDGE DETECTOR"
Focuses on detecting bookmaker mispricing, not just interesting statistics
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EdgeOpportunity:
    """Represents a betting edge opportunity"""
    market: str  # e.g., "HT UNDER 1.5"
    market_type: str  # "HT_UNDER", "FT_OVER", "BTTS"
    line: float  # e.g., 1.5
    
    # Probabilities
    historical_probability: float  # e.g., 0.82 (82%)
    implied_probability: float  # e.g., 0.61 (61%) from bookmaker odd
    
    # Odds
    market_odd: Optional[float]  # Bookmaker odd (if available)
    fair_odd: float  # Calculated from historical probability
    
    # Edge metrics
    edge_percent: float  # historical_prob - implied_prob (e.g., 0.21 = 21%)
    edge_value: float  # Expected value
    
    # Confidence
    sample_size: int
    hit_rate: float  # 0-100
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    variance: str  # "LOW", "MEDIUM", "HIGH"
    
    # Context
    reasons: List[str]
    avg_goals: Optional[float] = None
    max_goals: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "market": self.market,
            "market_type": self.market_type,
            "line": self.line,
            "historical_probability": self.historical_probability,
            "implied_probability": self.implied_probability,
            "market_odd": self.market_odd,
            "fair_odd": self.fair_odd,
            "edge_percent": self.edge_percent,
            "edge_value": self.edge_value,
            "sample_size": self.sample_size,
            "hit_rate": self.hit_rate,
            "confidence": self.confidence,
            "variance": self.variance,
            "reasons": self.reasons,
            "avg_goals": self.avg_goals,
            "max_goals": self.max_goals
        }


class EdgeDetector:
    """
    Detects bookmaker mispricing by comparing historical probabilities
    with implied probabilities from bookmaker odds
    """
    
    # Thresholds for filtering (RELAXED for better visibility)
    MIN_ODD = 1.10  # Ignore odds below this (was 1.15)
    MIN_EDGE_PERCENT = 0.00  # Show all edges (was 0.05 = 5%)
    MIN_SAMPLE_SIZE = 5  # Reduced from 8 to show more matches
    
    # Priority markets
    PRIORITY_HT_MARKETS = ["U0.5", "U1.5", "O0.5", "O1.5"]
    PRIORITY_FT_MARKETS = ["U1.5", "U2.5", "U3.5", "O1.5", "O2.5", "O3.5"]
    
    def __init__(self):
        """Initialize edge detector"""
        pass
    
    def calculate_implied_probability(self, odd: float) -> float:
        """
        Calculate implied probability from bookmaker odd
        
        Args:
            odd: Bookmaker odd (e.g., 1.65)
            
        Returns:
            Implied probability (e.g., 0.606 for odd 1.65)
        """
        if odd <= 1.0:
            return 1.0
        return 1.0 / odd
    
    def calculate_edge(
        self,
        historical_prob: float,
        implied_prob: float
    ) -> float:
        """
        Calculate edge percentage
        
        Args:
            historical_prob: Historical probability (0-1)
            implied_prob: Implied probability from bookmaker (0-1)
            
        Returns:
            Edge percentage (e.g., 0.16 for 16% edge)
        """
        return historical_prob - implied_prob
    
    def calculate_expected_value(
        self,
        historical_prob: float,
        market_odd: float
    ) -> float:
        """
        Calculate expected value (EV)
        
        EV = (probability × profit) - (1 - probability) × stake
        With stake = 1: EV = (prob × (odd - 1)) - (1 - prob)
        
        Args:
            historical_prob: Historical probability
            market_odd: Bookmaker odd
            
        Returns:
            Expected value per unit stake
        """
        if market_odd <= 1.0:
            return 0.0
        
        profit = market_odd - 1.0
        ev = (historical_prob * profit) - (1.0 - historical_prob)
        return ev
    
    def assess_confidence(
        self,
        sample_size: int,
        hit_rate: float,
        variance: float
    ) -> str:
        """
        Assess confidence level based on sample size, hit rate, and variance
        
        Args:
            sample_size: Number of historical matches
            hit_rate: Hit rate percentage (0-100)
            variance: Variance in goals
            
        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        # High confidence: large sample, high hit rate, low variance
        if sample_size >= 15 and hit_rate >= 75 and variance < 1.5:
            return "HIGH"
        
        # Medium confidence: decent sample, good hit rate
        if sample_size >= 10 and hit_rate >= 65:
            return "MEDIUM"
        
        # Low confidence: small sample or low hit rate
        return "LOW"
    
    def assess_variance(self, goals: List[int]) -> tuple[float, str]:
        """
        Assess variance in goals
        
        Args:
            goals: List of goal counts
            
        Returns:
            (variance_value, variance_level)
        """
        if len(goals) < 2:
            return (0.0, "UNKNOWN")
        
        mean = sum(goals) / len(goals)
        variance = sum((x - mean) ** 2 for x in goals) / len(goals)
        
        # Classify variance
        if variance < 1.0:
            return (variance, "LOW")
        elif variance < 2.5:
            return (variance, "MEDIUM")
        else:
            return (variance, "HIGH")
    
    def detect_ht_edges(
        self,
        ht_goals: List[int],
        ht_analysis: Dict[str, Any],
        bookmaker_odds: Optional[Dict[str, float]] = None
    ) -> List[EdgeOpportunity]:
        """
        Detect HT (halftime) edge opportunities
        
        Args:
            ht_goals: List of HT goal counts
            ht_analysis: HT analysis table
            bookmaker_odds: Optional bookmaker odds dict
            
        Returns:
            List of EdgeOpportunity objects
        """
        edges = []
        
        if not ht_goals or len(ht_goals) < self.MIN_SAMPLE_SIZE:
            return edges
        
        # Calculate variance
        variance_value, variance_level = self.assess_variance(ht_goals)
        avg_ht_goals = sum(ht_goals) / len(ht_goals)
        max_ht_goals = max(ht_goals)
        
        # Check each line in HT analysis
        for row in ht_analysis.get("table", []):
            line_str = row.get("line", "")
            
            # Parse line (e.g., "U1.5" -> 1.5)
            if not line_str.startswith("U") and not line_str.startswith("O"):
                continue
            
            is_under = line_str.startswith("U")
            try:
                line_value = float(line_str[1:])
            except ValueError:
                continue
            
            # Only process priority markets
            if line_str not in self.PRIORITY_HT_MARKETS:
                continue
            
            # Get historical probability
            hit_rate = row.get("hit_rate", 0)
            historical_prob = hit_rate / 100.0
            fair_odd = row.get("fair_odd", 0)
            sample_size = row.get("sample_size", len(ht_goals))
            
            # Skip if fair odd too low (no edge possible)
            if fair_odd < self.MIN_ODD:
                continue
            
            # Get bookmaker odd if available
            market_key = f"HT_{line_str}"
            market_odd = bookmaker_odds.get(market_key) if bookmaker_odds else None
            
            # If no bookmaker odd, use fair odd as reference
            if market_odd is None:
                # Can't calculate edge without bookmaker odd
                # But we can still flag as potential opportunity
                implied_prob = 1.0 / fair_odd
                edge_percent = 0.0  # Unknown edge
                edge_value = 0.0
            else:
                # Calculate edge
                implied_prob = self.calculate_implied_probability(market_odd)
                edge_percent = self.calculate_edge(historical_prob, implied_prob)
                edge_value = self.calculate_expected_value(historical_prob, market_odd)
                
                # Filter by minimum edge
                if edge_percent < self.MIN_EDGE_PERCENT:
                    continue
            
            # Assess confidence
            confidence = self.assess_confidence(sample_size, hit_rate, variance_value)
            
            # Build reasons
            reasons = []
            if hit_rate >= 80:
                reasons.append(f"{int(hit_rate)}% hit rate ({int(hit_rate * sample_size / 100)}/{sample_size})")
            else:
                reasons.append(f"{int(hit_rate)}% hit rate")
            
            reasons.append(f"Avg HT goals: {avg_ht_goals:.1f}")
            
            if variance_level == "LOW":
                reasons.append("Low variance (stable)")
            
            if is_under and avg_ht_goals < line_value - 0.5:
                reasons.append(f"Avg well below line ({avg_ht_goals:.1f} < {line_value})")
            
            if edge_percent > 0.10:
                reasons.append(f"Strong edge: +{edge_percent * 100:.0f}%")
            
            # Create edge opportunity
            market_name = f"HT {'UNDER' if is_under else 'OVER'} {line_value}"
            market_type = f"HT_{'UNDER' if is_under else 'OVER'}"
            
            edge = EdgeOpportunity(
                market=market_name,
                market_type=market_type,
                line=line_value,
                historical_probability=historical_prob,
                implied_probability=implied_prob,
                market_odd=market_odd,
                fair_odd=fair_odd,
                edge_percent=edge_percent,
                edge_value=edge_value,
                sample_size=sample_size,
                hit_rate=hit_rate,
                confidence=confidence,
                variance=variance_level,
                reasons=reasons,
                avg_goals=avg_ht_goals,
                max_goals=max_ht_goals
            )
            
            edges.append(edge)
        
        return edges
    
    def detect_ft_edges(
        self,
        ft_goals: List[int],
        ft_analysis: Dict[str, Any],
        bookmaker_odds: Optional[Dict[str, float]] = None
    ) -> List[EdgeOpportunity]:
        """
        Detect FT (fulltime) edge opportunities
        
        Args:
            ft_goals: List of FT goal counts
            ft_analysis: FT analysis table
            bookmaker_odds: Optional bookmaker odds dict
            
        Returns:
            List of EdgeOpportunity objects
        """
        edges = []
        
        if not ft_goals or len(ft_goals) < self.MIN_SAMPLE_SIZE:
            return edges
        
        # Calculate variance
        variance_value, variance_level = self.assess_variance(ft_goals)
        avg_goals = sum(ft_goals) / len(ft_goals)
        max_goals = max(ft_goals)
        
        # Check each line in FT analysis
        for row in ft_analysis.get("table", []):
            line_str = row.get("line", "")
            
            # Parse line
            if not line_str.startswith("U") and not line_str.startswith("O"):
                continue
            
            is_under = line_str.startswith("U")
            try:
                line_value = float(line_str[1:])
            except ValueError:
                continue
            
            # Only process priority markets
            if line_str not in self.PRIORITY_FT_MARKETS:
                continue
            
            # Get historical probability
            hit_rate = row.get("hit_rate", 0)
            historical_prob = hit_rate / 100.0
            fair_odd = row.get("fair_odd", 0)
            sample_size = row.get("sample_size", len(ft_goals))
            
            # Skip if fair odd too low
            if fair_odd < self.MIN_ODD:
                continue
            
            # Get bookmaker odd if available
            market_key = f"FT_{line_str}"
            market_odd = bookmaker_odds.get(market_key) if bookmaker_odds else None
            
            # Calculate edge
            if market_odd is None:
                implied_prob = 1.0 / fair_odd
                edge_percent = 0.0
                edge_value = 0.0
            else:
                implied_prob = self.calculate_implied_probability(market_odd)
                edge_percent = self.calculate_edge(historical_prob, implied_prob)
                edge_value = self.calculate_expected_value(historical_prob, market_odd)
                
                if edge_percent < self.MIN_EDGE_PERCENT:
                    continue
            
            # Assess confidence
            confidence = self.assess_confidence(sample_size, hit_rate, variance_value)
            
            # Build reasons
            reasons = []
            if hit_rate >= 80:
                reasons.append(f"{int(hit_rate)}% hit rate ({int(hit_rate * sample_size / 100)}/{sample_size})")
            else:
                reasons.append(f"{int(hit_rate)}% hit rate")
            
            reasons.append(f"Avg goals: {avg_goals:.1f}")
            
            if variance_level == "LOW":
                reasons.append("Low variance (stable)")
            
            if is_under and avg_goals < line_value - 0.5:
                reasons.append(f"Avg well below line ({avg_goals:.1f} < {line_value})")
            elif not is_under and avg_goals > line_value + 0.5:
                reasons.append(f"Avg well above line ({avg_goals:.1f} > {line_value})")
            
            if edge_percent > 0.10:
                reasons.append(f"Strong edge: +{edge_percent * 100:.0f}%")
            
            # Create edge opportunity
            market_name = f"{'UNDER' if is_under else 'OVER'} {line_value}"
            market_type = f"FT_{'UNDER' if is_under else 'OVER'}"
            
            edge = EdgeOpportunity(
                market=market_name,
                market_type=market_type,
                line=line_value,
                historical_probability=historical_prob,
                implied_probability=implied_prob,
                market_odd=market_odd,
                fair_odd=fair_odd,
                edge_percent=edge_percent,
                edge_value=edge_value,
                sample_size=sample_size,
                hit_rate=hit_rate,
                confidence=confidence,
                variance=variance_level,
                reasons=reasons,
                avg_goals=avg_goals,
                max_goals=max_goals
            )
            
            edges.append(edge)
        
        return edges
    
    def select_best_edges(
        self,
        edges: List[EdgeOpportunity],
        max_edges: int = 5
    ) -> List[EdgeOpportunity]:
        """
        Select the best edge opportunities
        
        Prioritizes by:
        1. Edge percentage (higher is better)
        2. Confidence (HIGH > MEDIUM > LOW)
        3. Sample size (larger is better)
        
        Args:
            edges: List of edge opportunities
            max_edges: Maximum number of edges to return (default: 5, was 3)
            
        Returns:
            Top edge opportunities
        """
        if not edges:
            return []
        
        # Score each edge
        def score_edge(edge: EdgeOpportunity) -> float:
            score = 0.0
            
            # Edge percentage (most important)
            score += edge.edge_percent * 100  # 0-100 points
            
            # Confidence bonus
            if edge.confidence == "HIGH":
                score += 20
            elif edge.confidence == "MEDIUM":
                score += 10
            
            # Sample size bonus (capped)
            score += min(edge.sample_size / 2, 10)
            
            # Variance penalty
            if edge.variance == "HIGH":
                score -= 10
            
            # Fair odd bonus (prefer odds in sweet spot 1.3-2.5)
            if 1.3 <= edge.fair_odd <= 2.5:
                score += 5
            
            return score
        
        # Sort by score
        sorted_edges = sorted(edges, key=score_edge, reverse=True)
        
        # Return top N
        return sorted_edges[:max_edges]
    
    def detect_over_profiles(
        self,
        ft_goals: List[int],
        ht_goals: List[int]
    ) -> List[str]:
        """
        Detect OVER scoring profiles
        
        Args:
            ft_goals: FT goal history
            ht_goals: HT goal history
            
        Returns:
            List of profile names detected
        """
        profiles = []
        
        if not ft_goals or len(ft_goals) < 5:
            return profiles
        
        avg_goals = sum(ft_goals) / len(ft_goals)
        avg_ht_goals = sum(ht_goals) / len(ht_goals) if ht_goals else 0
        
        # Calculate over rates
        over_2_5 = sum(1 for g in ft_goals if g > 2.5) / len(ft_goals)
        over_3_5 = sum(1 for g in ft_goals if g > 3.5) / len(ft_goals)
        
        # EXTREME_OVER: Very high scoring (relaxed thresholds)
        if avg_goals >= 3.5 and over_2_5 >= 0.75 and over_3_5 >= 0.60:
            profiles.append("EXTREME_OVER")
            logger.info(f"[PROFILE] EXTREME_OVER detected: avg={avg_goals:.1f}, O2.5={over_2_5*100:.0f}%, O3.5={over_3_5*100:.0f}%")
        
        # HIGH_SCORING_PROFILE: High scoring (relaxed thresholds)
        elif avg_goals >= 2.7 and over_2_5 >= 0.65:
            profiles.append("HIGH_SCORING_PROFILE")
            logger.info(f"[PROFILE] HIGH_SCORING detected: avg={avg_goals:.1f}, O2.5={over_2_5*100:.0f}%")
        
        # HT_GOAL_PROFILE: Fast starts (relaxed thresholds)
        if ht_goals and len(ht_goals) >= 5:
            ht_over_0_5 = sum(1 for g in ht_goals if g > 0.5) / len(ht_goals)
            if ht_over_0_5 >= 0.75 and avg_ht_goals >= 1.0:
                profiles.append("HT_GOAL_PROFILE")
                logger.info(f"[PROFILE] HT_GOAL detected: HT avg={avg_ht_goals:.1f}, HT O0.5={ht_over_0_5*100:.0f}%")
        
        # BTTS_PROFILE: Both teams score frequently
        # Note: This requires home/away goal split, will be added in BTTS detection
        
        return profiles
    
    def detect_btts_edge(
        self,
        match_history: List[Dict[str, Any]],
        bookmaker_odds: Optional[Dict[str, float]] = None
    ) -> Optional[EdgeOpportunity]:
        """
        Detect BTTS (Both Teams To Score) edge
        
        Args:
            match_history: List of historical matches with home_goals and away_goals
            bookmaker_odds: Optional bookmaker odds dict
            
        Returns:
            EdgeOpportunity if BTTS edge detected, None otherwise
        """
        if not match_history or len(match_history) < self.MIN_SAMPLE_SIZE:
            return None
        
        # Calculate BTTS hit rate
        btts_count = 0
        for match in match_history:
            home_goals = match.get("home_goals", 0)
            away_goals = match.get("away_goals", 0)
            
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
        
        btts_hit_rate = btts_count / len(match_history)
        
        # Minimum 60% for BTTS edge (was 70%, relaxed to show more opportunities)
        if btts_hit_rate < 0.60:
            return None
        
        # Calculate fair odd
        fair_odd = 1 / btts_hit_rate if btts_hit_rate > 0 else 999
        
        # Skip if fair odd too low
        if fair_odd < self.MIN_ODD:
            return None
        
        # Get bookmaker odd if available
        market_odd = bookmaker_odds.get("BTTS_YES") if bookmaker_odds else None
        
        # Calculate edge
        if market_odd is None:
            implied_prob = 1 / fair_odd
            edge_percent = 0.0
            edge_value = 0.0
        else:
            implied_prob = self.calculate_implied_probability(market_odd)
            edge_percent = self.calculate_edge(btts_hit_rate, implied_prob)
            edge_value = self.calculate_expected_value(btts_hit_rate, market_odd)
            
            # Filter by minimum edge
            if edge_percent < self.MIN_EDGE_PERCENT:
                return None
        
        # Assess confidence
        variance_value, variance_level = 0.0, "MEDIUM"  # BTTS has medium variance
        confidence = self.assess_confidence(len(match_history), btts_hit_rate * 100, variance_value)
        
        # Build reasons
        reasons = [
            f"BTTS hit rate: {btts_hit_rate * 100:.0f}% ({btts_count}/{len(match_history)})",
            f"Both teams scored in {btts_count} of {len(match_history)} matches"
        ]
        
        if edge_percent > 0:
            reasons.insert(0, f"Edge: +{edge_percent * 100:.1f}% vs bookmaker")
        
        if btts_hit_rate >= 0.85:
            reasons.append("Very high BTTS consistency")
        
        # Create edge opportunity
        edge = EdgeOpportunity(
            market="BTTS YES",
            market_type="BTTS",
            line=0,
            historical_probability=btts_hit_rate,
            implied_probability=implied_prob,
            market_odd=market_odd,
            fair_odd=fair_odd,
            edge_percent=edge_percent,
            edge_value=edge_value,
            sample_size=len(match_history),
            hit_rate=btts_hit_rate * 100,
            confidence=confidence,
            variance=variance_level,
            reasons=reasons
        )
        
        logger.info(f"[EDGE] BTTS edge detected: {btts_hit_rate*100:.0f}%, fair={fair_odd:.2f}, edge={edge_percent*100:.1f}%")
        
        return edge
    
    def detect_all_edges(
        self,
        ht_goals: List[int],
        ft_goals: List[int],
        ht_analysis: Dict[str, Any],
        ft_analysis: Dict[str, Any],
        bookmaker_odds: Optional[Dict[str, float]] = None,
        match_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Detect all edge opportunities for a match
        
        Args:
            ht_goals: HT goal history
            ft_goals: FT goal history
            ht_analysis: HT analysis table
            ft_analysis: FT analysis table
            bookmaker_odds: Optional bookmaker odds
            match_history: Optional match history with home/away goals for BTTS
            
        Returns:
            Dict with best edges and metadata
        """
        # Detect OVER profiles
        over_profiles = self.detect_over_profiles(ft_goals, ht_goals)
        
        # Detect HT edges
        ht_edges = self.detect_ht_edges(ht_goals, ht_analysis, bookmaker_odds)
        logger.info(f"[EDGE] Detected {len(ht_edges)} HT edges")
        
        # Detect FT edges
        ft_edges = self.detect_ft_edges(ft_goals, ft_analysis, bookmaker_odds)
        logger.info(f"[EDGE] Detected {len(ft_edges)} FT edges")
        
        # Detect BTTS edge
        btts_edge = None
        if match_history:
            btts_edge = self.detect_btts_edge(match_history, bookmaker_odds)
            if btts_edge:
                logger.info(f"[EDGE] BTTS edge detected")
        
        # Combine all edges
        all_edges = ht_edges + ft_edges
        if btts_edge:
            all_edges.append(btts_edge)
        
        # Select best edges
        best_edges = self.select_best_edges(all_edges, max_edges=3)
        
        logger.info(f"[EDGE] Selected {len(best_edges)} best edges")
        for edge in best_edges:
            logger.info(f"[EDGE]   - {edge.market}: edge={edge.edge_percent*100:.1f}%, confidence={edge.confidence}")
        
        return {
            "best_edges": [e.to_dict() for e in best_edges],
            "all_ht_edges": [e.to_dict() for e in ht_edges],
            "all_ft_edges": [e.to_dict() for e in ft_edges],
            "btts_edge": btts_edge.to_dict() if btts_edge else None,
            "over_profiles": over_profiles,
            "total_edges_found": len(all_edges),
            "has_bookmaker_odds": bookmaker_odds is not None
        }
