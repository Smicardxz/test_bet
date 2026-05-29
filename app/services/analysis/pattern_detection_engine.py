"""
Pattern Detection Engine
Automatically identifies recurring statistical patterns in teams and leagues
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging

from app.services.stats import TeamStats


logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of statistical patterns"""
    # Team patterns
    EXTREME_UNDER = "EXTREME_UNDER"
    EXTREME_OVER = "EXTREME_OVER"
    LOW_TEMPO_FIRST_HALF = "LOW_TEMPO_FIRST_HALF"
    HIGH_TEMPO_FIRST_HALF = "HIGH_TEMPO_FIRST_HALF"
    ASYMMETRIC_HOME = "ASYMMETRIC_HOME"
    ASYMMETRIC_AWAY = "ASYMMETRIC_AWAY"
    BTTS_RARE = "BTTS_RARE"
    BTTS_FREQUENT = "BTTS_FREQUENT"
    CLEAN_SHEET_SPECIALIST = "CLEAN_SHEET_SPECIALIST"
    LOW_VARIANCE = "LOW_VARIANCE"
    HIGH_VARIANCE = "HIGH_VARIANCE"
    STABLE_PERFORMANCE = "STABLE_PERFORMANCE"
    UNSTABLE_PERFORMANCE = "UNSTABLE_PERFORMANCE"
    
    # League patterns
    LOW_SCORING_LEAGUE = "LOW_SCORING_LEAGUE"
    HIGH_SCORING_LEAGUE = "HIGH_SCORING_LEAGUE"
    DEFENSIVE_LEAGUE = "DEFENSIVE_LEAGUE"
    OPEN_LEAGUE = "OPEN_LEAGUE"
    
    # H2H patterns
    DOMINANT_H2H = "DOMINANT_H2H"
    BALANCED_H2H = "BALANCED_H2H"
    H2H_LOW_SCORING = "H2H_LOW_SCORING"
    
    # Temporal patterns
    IMPROVING_FORM = "IMPROVING_FORM"
    DECLINING_FORM = "DECLINING_FORM"
    CONSISTENT_FORM = "CONSISTENT_FORM"
    HOME_STRONG = "HOME_STRONG"
    AWAY_STRONG = "AWAY_STRONG"


class PatternStrength(str, Enum):
    """Strength of detected pattern"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    EXTREME = "EXTREME"


@dataclass
class Pattern:
    """Single detected pattern"""
    pattern_type: PatternType
    strength: PatternStrength
    score: float  # 0-100
    description: str
    evidence: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.pattern_type.value,
            "strength": self.strength.value,
            "score": self.score,
            "description": self.description,
            "evidence": self.evidence
        }


@dataclass
class PatternDetectionResult:
    """Complete pattern detection result"""
    team_id: str
    team_name: str
    
    # Detected patterns
    patterns: List[Pattern] = field(default_factory=list)
    
    # Summary
    pattern_tags: List[str] = field(default_factory=list)
    pattern_score: float = 0.0  # Overall pattern score 0-100
    
    # Explanations
    pattern_explanation: str = ""
    dominant_patterns: List[str] = field(default_factory=list)
    
    # Metadata
    sample_size: int = 0
    confidence: float = 0.0  # 0-1
    
    def to_dict(self) -> Dict:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "patterns": [p.to_dict() for p in self.patterns],
            "pattern_tags": self.pattern_tags,
            "pattern_score": self.pattern_score,
            "pattern_explanation": self.pattern_explanation,
            "dominant_patterns": self.dominant_patterns,
            "sample_size": self.sample_size,
            "confidence": self.confidence
        }


class PatternDetectionEngine:
    """
    Pattern Detection Engine
    
    Automatically identifies recurring statistical patterns in:
    - Teams (playing style, tendencies)
    - Leagues (scoring trends)
    - H2H (historical matchups)
    - Temporal (form trends)
    
    Enriches AnomalyEngine with pattern context
    """
    
    def __init__(self):
        """Initialize pattern detection engine"""
        self.min_sample_size = 8
        self.logger = logging.getLogger(__name__)
    
    def analyze_team(
        self,
        team_id: str,
        team_name: str,
        home_stats: Optional[TeamStats] = None,
        away_stats: Optional[TeamStats] = None,
        overall_stats: Optional[TeamStats] = None
    ) -> PatternDetectionResult:
        """
        Analyze team for statistical patterns
        
        Args:
            team_id: Team ID
            team_name: Team name
            home_stats: Home-specific stats
            away_stats: Away-specific stats
            overall_stats: Overall team stats
            
        Returns:
            PatternDetectionResult with all detected patterns
        """
        
        patterns = []
        
        # Use overall stats if available, else combine home/away
        if overall_stats:
            stats = overall_stats
        elif home_stats and away_stats:
            stats = self._combine_stats(home_stats, away_stats)
        elif home_stats:
            stats = home_stats
        elif away_stats:
            stats = away_stats
        else:
            return self._create_empty_result(team_id, team_name)
        
        # Check sample size
        if stats.sample_size < self.min_sample_size:
            return self._create_empty_result(team_id, team_name)
        
        # Detect team patterns
        patterns.extend(self._detect_scoring_patterns(stats))
        patterns.extend(self._detect_half_time_patterns(stats))
        patterns.extend(self._detect_btts_patterns(stats))
        patterns.extend(self._detect_variance_patterns(stats))
        patterns.extend(self._detect_stability_patterns(stats))
        patterns.extend(self._detect_clean_sheet_patterns(stats))
        
        # Detect home/away asymmetry if both available
        if home_stats and away_stats:
            patterns.extend(self._detect_asymmetry_patterns(home_stats, away_stats))
        
        # Detect temporal/form patterns
        if stats.form and len(stats.form) >= 5:
            patterns.extend(self._detect_form_patterns(stats))
        
        # Generate result
        return self._build_result(team_id, team_name, stats, patterns)
    
    def analyze_league(
        self,
        league_stats: List[TeamStats],
        league_name: str = "Unknown"
    ) -> List[Pattern]:
        """
        Analyze league for statistical patterns
        
        Args:
            league_stats: List of team stats in league
            league_name: League name
            
        Returns:
            List of detected league patterns
        """
        
        patterns = []
        
        if not league_stats:
            return patterns
        
        # Calculate league averages
        avg_goals = statistics.mean([s.avg_total_goals for s in league_stats])
        avg_ht_goals = statistics.mean([s.avg_ht_total_goals for s in league_stats])
        avg_btts = statistics.mean([s.btts_rate for s in league_stats])
        
        # Low scoring league
        if avg_goals < 2.0:
            patterns.append(Pattern(
                pattern_type=PatternType.LOW_SCORING_LEAGUE,
                strength=PatternStrength.STRONG if avg_goals < 1.5 else PatternStrength.MODERATE,
                score=min(100, max(0, (2.5 - avg_goals) * 50)),
                description=f"Low scoring league ({avg_goals:.1f} avg goals)",
                evidence={"avg_goals": avg_goals, "threshold": 2.0}
            ))
        
        # High scoring league
        if avg_goals > 3.0:
            patterns.append(Pattern(
                pattern_type=PatternType.HIGH_SCORING_LEAGUE,
                strength=PatternStrength.STRONG if avg_goals > 3.5 else PatternStrength.MODERATE,
                score=min(100, max(0, (avg_goals - 2.5) * 50)),
                description=f"High scoring league ({avg_goals:.1f} avg goals)",
                evidence={"avg_goals": avg_goals, "threshold": 3.0}
            ))
        
        # Defensive league (low BTTS, low scoring)
        if avg_goals < 2.2 and avg_btts < 45:
            patterns.append(Pattern(
                pattern_type=PatternType.DEFENSIVE_LEAGUE,
                strength=PatternStrength.STRONG,
                score=75.0,
                description=f"Defensive league ({avg_goals:.1f} goals, {avg_btts:.0f}% BTTS)",
                evidence={"avg_goals": avg_goals, "btts_rate": avg_btts}
            ))
        
        # Open league (high BTTS, high scoring)
        if avg_goals > 2.5 and avg_btts > 55:
            patterns.append(Pattern(
                pattern_type=PatternType.OPEN_LEAGUE,
                strength=PatternStrength.STRONG,
                score=75.0,
                description=f"Open league ({avg_goals:.1f} goals, {avg_btts:.0f}% BTTS)",
                evidence={"avg_goals": avg_goals, "btts_rate": avg_btts}
            ))
        
        return patterns
    
    def analyze_h2h(
        self,
        team_a_stats: TeamStats,
        team_b_stats: TeamStats,
        h2h_matches_count: int = 0
    ) -> List[Pattern]:
        """
        Analyze H2H patterns
        
        Args:
            team_a_stats: Team A stats
            team_b_stats: Team B stats
            h2h_matches_count: Number of H2H matches
            
        Returns:
            List of detected H2H patterns
        """
        
        patterns = []
        
        if h2h_matches_count < 3:
            return patterns
        
        # Dominant H2H (one team much stronger)
        avg_goals_a = team_a_stats.avg_total_goals
        avg_goals_b = team_b_stats.avg_total_goals
        
        # H2H low scoring (both teams defensive)
        if (team_a_stats.under_2_5_rate > 65 and 
            team_b_stats.under_2_5_rate > 65):
            patterns.append(Pattern(
                pattern_type=PatternType.H2H_LOW_SCORING,
                strength=PatternStrength.STRONG,
                score=80.0,
                description=f"Both teams under-prone (H2H likely low scoring)",
                evidence={
                    "team_a_under": team_a_stats.under_2_5_rate,
                    "team_b_under": team_b_stats.under_2_5_rate
                }
            ))
        
        return patterns
    
    def _detect_scoring_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect scoring-related patterns"""
        patterns = []
        
        # Extreme Under team
        if stats.under_2_5_rate >= 70:
            strength = PatternStrength.EXTREME if stats.under_2_5_rate >= 80 else PatternStrength.STRONG
            score = min(100, stats.under_2_5_rate * 1.1)
            patterns.append(Pattern(
                pattern_type=PatternType.EXTREME_UNDER,
                strength=strength,
                score=score,
                description=f"Very under-prone team ({stats.under_2_5_rate:.0f}% under 2.5)",
                evidence={"under_25_rate": stats.under_2_5_rate, "avg_goals": stats.avg_total_goals}
            ))
        
        # Extreme Over team
        elif stats.over_2_5_rate >= 65:
            strength = PatternStrength.STRONG if stats.over_2_5_rate >= 75 else PatternStrength.MODERATE
            score = min(100, stats.over_2_5_rate * 1.1)
            patterns.append(Pattern(
                pattern_type=PatternType.EXTREME_OVER,
                strength=strength,
                score=score,
                description=f"Over-prone team ({stats.over_2_5_rate:.0f}% over 2.5)",
                evidence={"over_25_rate": stats.over_2_5_rate, "avg_goals": stats.avg_total_goals}
            ))
        
        return patterns
    
    def _detect_half_time_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect half-time related patterns"""
        patterns = []
        
        # Low tempo first half (many 0-0 at HT)
        if stats.ht_00_rate >= 50:
            strength = PatternStrength.EXTREME if stats.ht_00_rate >= 65 else PatternStrength.STRONG
            score = min(100, stats.ht_00_rate * 1.2)
            patterns.append(Pattern(
                pattern_type=PatternType.LOW_TEMPO_FIRST_HALF,
                strength=strength,
                score=score,
                description=f"Very slow starters ({stats.ht_00_rate:.0f}% 0-0 at HT)",
                evidence={"ht_00_rate": stats.ht_00_rate, "avg_ht_goals": stats.avg_ht_total_goals}
            ))
        
        # High tempo first half
        elif stats.avg_ht_total_goals > 1.5:
            patterns.append(Pattern(
                pattern_type=PatternType.HIGH_TEMPO_FIRST_HALF,
                strength=PatternStrength.STRONG,
                score=min(100, stats.avg_ht_total_goals * 40),
                description=f"Fast starters ({stats.avg_ht_total_goals:.1f} avg HT goals)",
                evidence={"avg_ht_goals": stats.avg_ht_total_goals, "ht_00_rate": stats.ht_00_rate}
            ))
        
        return patterns
    
    def _detect_btts_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect BTTS patterns"""
        patterns = []
        
        # BTTS Rare
        if stats.btts_rate < 30:
            patterns.append(Pattern(
                pattern_type=PatternType.BTTS_RARE,
                strength=PatternStrength.EXTREME if stats.btts_rate < 20 else PatternStrength.STRONG,
                score=min(100, (50 - stats.btts_rate) * 2),
                description=f"BTTS rarely occurs ({stats.btts_rate:.0f}%)",
                evidence={"btts_rate": stats.btts_rate, "clean_sheets": stats.clean_sheets_rate}
            ))
        
        # BTTS Frequent
        elif stats.btts_rate > 60:
            patterns.append(Pattern(
                pattern_type=PatternType.BTTS_FREQUENT,
                strength=PatternStrength.STRONG if stats.btts_rate > 70 else PatternStrength.MODERATE,
                score=min(100, (stats.btts_rate - 50) * 2),
                description=f"BTTS frequently occurs ({stats.btts_rate:.0f}%)",
                evidence={"btts_rate": stats.btts_rate}
            ))
        
        return patterns
    
    def _detect_variance_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect variance-related patterns"""
        patterns = []
        
        # Low variance (consistent results)
        combined_variance = stats.variance_goals_scored + stats.variance_goals_conceded
        
        if combined_variance < 1.5:
            patterns.append(Pattern(
                pattern_type=PatternType.LOW_VARIANCE,
                strength=PatternStrength.STRONG,
                score=min(100, max(0, (3.0 - combined_variance) * 33)),
                description=f"Very consistent results (variance: {combined_variance:.2f})",
                evidence={"variance": combined_variance, "stability": stats.stability_score}
            ))
        
        # High variance (unpredictable)
        elif combined_variance > 4.0:
            patterns.append(Pattern(
                pattern_type=PatternType.HIGH_VARIANCE,
                strength=PatternStrength.STRONG,
                score=min(100, combined_variance * 20),
                description=f"Unpredictable results (variance: {combined_variance:.2f})",
                evidence={"variance": combined_variance}
            ))
        
        return patterns
    
    def _detect_stability_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect stability patterns"""
        patterns = []
        
        # Stable performance
        if stats.stability_score > 0.7:
            patterns.append(Pattern(
                pattern_type=PatternType.STABLE_PERFORMANCE,
                strength=PatternStrength.EXTREME if stats.stability_score > 0.85 else PatternStrength.STRONG,
                score=min(100, stats.stability_score * 100),
                description=f"Stable performance (score: {stats.stability_score:.2f})",
                evidence={"stability_score": stats.stability_score, "variance": stats.variance_goals_scored}
            ))
        
        # Unstable performance
        elif stats.stability_score < 0.3:
            patterns.append(Pattern(
                pattern_type=PatternType.UNSTABLE_PERFORMANCE,
                strength=PatternStrength.STRONG,
                score=min(100, (0.5 - stats.stability_score) * 100),
                description=f"Unstable performance (score: {stats.stability_score:.2f})",
                evidence={"stability_score": stats.stability_score}
            ))
        
        return patterns
    
    def _detect_clean_sheet_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect clean sheet patterns"""
        patterns = []
        
        # Clean sheet specialist
        if stats.clean_sheets_rate >= 40:
            patterns.append(Pattern(
                pattern_type=PatternType.CLEAN_SHEET_SPECIALIST,
                strength=PatternStrength.EXTREME if stats.clean_sheets_rate >= 50 else PatternStrength.STRONG,
                score=min(100, stats.clean_sheets_rate * 1.5),
                description=f"Clean sheet specialist ({stats.clean_sheets_rate:.0f}%)",
                evidence={"clean_sheets_rate": stats.clean_sheets_rate, "avg_conceded": stats.avg_goals_conceded}
            ))
        
        return patterns
    
    def _detect_asymmetry_patterns(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> List[Pattern]:
        """Detect home/away asymmetry patterns"""
        patterns = []
        
        # Home strong (much better at home)
        if (home_stats.avg_total_goals > away_stats.avg_total_goals * 1.5 or
            home_stats.under_2_5_rate < away_stats.under_2_5_rate - 15):
            patterns.append(Pattern(
                pattern_type=PatternType.HOME_STRONG,
                strength=PatternStrength.STRONG,
                score=75.0,
                description=f"Much stronger at home (H: {home_stats.avg_total_goals:.1f} vs A: {away_stats.avg_total_goals:.1f})",
                evidence={
                    "home_avg": home_stats.avg_total_goals,
                    "away_avg": away_stats.avg_total_goals
                }
            ))
        
        # Away strong
        elif (away_stats.avg_total_goals > home_stats.avg_total_goals * 1.5 or
              away_stats.under_2_5_rate < home_stats.under_2_5_rate - 15):
            patterns.append(Pattern(
                pattern_type=PatternType.AWAY_STRONG,
                strength=PatternStrength.STRONG,
                score=75.0,
                description=f"Much stronger away (A: {away_stats.avg_total_goals:.1f} vs H: {home_stats.avg_total_goals:.1f})",
                evidence={
                    "home_avg": home_stats.avg_total_goals,
                    "away_avg": away_stats.avg_total_goals
                }
            ))
        
        return patterns
    
    def _detect_form_patterns(self, stats: TeamStats) -> List[Pattern]:
        """Detect form/temporal patterns"""
        patterns = []
        
        if not stats.form or len(stats.form) < 5:
            return patterns
        
        # Convert form to numeric (W=3, D=1, L=0)
        form_map = {"W": 3, "D": 1, "L": 0}
        form_numeric = [form_map.get(f, 1) for f in stats.form[-5:]]
        
        # Improving form (last 2 better than first 3)
        if len(form_numeric) >= 5:
            early_avg = statistics.mean(form_numeric[:3])
            late_avg = statistics.mean(form_numeric[-2:])
            
            if late_avg > early_avg + 1:
                patterns.append(Pattern(
                    pattern_type=PatternType.IMPROVING_FORM,
                    strength=PatternStrength.STRONG if late_avg > early_avg + 1.5 else PatternStrength.MODERATE,
                    score=min(100, (late_avg - early_avg) * 30),
                    description=f"Improving form (recent: {late_avg:.1f} vs earlier: {early_avg:.1f})",
                    evidence={"early_form": early_avg, "late_form": late_avg, "form": stats.form}
                ))
            
            # Declining form
            elif early_avg > late_avg + 1:
                patterns.append(Pattern(
                    pattern_type=PatternType.DECLINING_FORM,
                    strength=PatternStrength.STRONG if early_avg > late_avg + 1.5 else PatternStrength.MODERATE,
                    score=min(100, (early_avg - late_avg) * 30),
                    description=f"Declining form (earlier: {early_avg:.1f} vs recent: {late_avg:.1f})",
                    evidence={"early_form": early_avg, "late_form": late_avg, "form": stats.form}
                ))
            
            # Consistent form (all results similar)
            else:
                form_variance = statistics.variance(form_numeric) if len(form_numeric) > 1 else 0
                if form_variance < 1.0:
                    patterns.append(Pattern(
                        pattern_type=PatternType.CONSISTENT_FORM,
                        strength=PatternStrength.MODERATE,
                        score=60.0,
                        description=f"Consistent form (variance: {form_variance:.2f})",
                        evidence={"form": stats.form, "variance": form_variance}
                    ))
        
        return patterns
    
    def _combine_stats(self, home_stats: TeamStats, away_stats: TeamStats) -> TeamStats:
        """Combine home and away stats"""
        # Create a combined stats object
        # This is a simplified version - real implementation would be more sophisticated
        
        total_sample = home_stats.sample_size + away_stats.sample_size
        
        return TeamStats(
            team_id=home_stats.team_id,
            team_name=home_stats.team_name,
            sample_size=total_sample,
            home_away="all",
            last_updated=home_stats.last_updated,
            avg_total_goals=(home_stats.avg_total_goals + away_stats.avg_total_goals) / 2,
            avg_goals_scored=(home_stats.avg_goals_scored + away_stats.avg_goals_scored) / 2,
            avg_goals_conceded=(home_stats.avg_goals_conceded + away_stats.avg_goals_conceded) / 2,
            under_1_5_rate=(home_stats.under_1_5_rate + away_stats.under_1_5_rate) / 2,
            under_2_5_rate=(home_stats.under_2_5_rate + away_stats.under_2_5_rate) / 2,
            under_3_5_rate=(home_stats.under_3_5_rate + away_stats.under_3_5_rate) / 2,
            under_4_5_rate=(home_stats.under_4_5_rate + away_stats.under_4_5_rate) / 2,
            under_5_5_rate=(home_stats.under_5_5_rate + away_stats.under_5_5_rate) / 2,
            under_extreme_line_rate=(home_stats.under_extreme_line_rate + away_stats.under_extreme_line_rate) / 2,
            over_1_5_rate=(home_stats.over_1_5_rate + away_stats.over_1_5_rate) / 2,
            over_2_5_rate=(home_stats.over_2_5_rate + away_stats.over_2_5_rate) / 2,
            over_3_5_rate=(home_stats.over_3_5_rate + away_stats.over_3_5_rate) / 2,
            over_4_5_rate=(home_stats.over_4_5_rate + away_stats.over_4_5_rate) / 2,
            over_5_5_rate=(home_stats.over_5_5_rate + away_stats.over_5_5_rate) / 2,
            btts_rate=(home_stats.btts_rate + away_stats.btts_rate) / 2,
            clean_sheets_rate=(home_stats.clean_sheets_rate + away_stats.clean_sheets_rate) / 2,
            avg_ht_total_goals=(home_stats.avg_ht_total_goals + away_stats.avg_ht_total_goals) / 2,
            avg_ht_goals_scored=(home_stats.avg_ht_goals_scored + away_stats.avg_ht_goals_scored) / 2,
            avg_ht_goals_conceded=(home_stats.avg_ht_goals_conceded + away_stats.avg_ht_goals_conceded) / 2,
            ht_00_rate=(home_stats.ht_00_rate + away_stats.ht_00_rate) / 2,
            variance_goals_scored=(home_stats.variance_goals_scored + away_stats.variance_goals_scored) / 2,
            variance_goals_conceded=(home_stats.variance_goals_conceded + away_stats.variance_goals_conceded) / 2,
            stability_score=(home_stats.stability_score + away_stats.stability_score) / 2,
            form=home_stats.form + away_stats.form,
            data_quality_score=min(home_stats.data_quality_score, away_stats.data_quality_score)
        )
    
    def _build_result(
        self,
        team_id: str,
        team_name: str,
        stats: TeamStats,
        patterns: List[Pattern]
    ) -> PatternDetectionResult:
        """Build final result from detected patterns"""
        
        # Sort patterns by score
        patterns.sort(key=lambda p: p.score, reverse=True)
        
        # Generate tags
        tags = [p.pattern_type.value for p in patterns if p.score >= 50]
        
        # Calculate overall pattern score
        if patterns:
            pattern_score = statistics.mean([p.score for p in patterns[:3]])
        else:
            pattern_score = 0.0
        
        # Get dominant patterns (top 3)
        dominant = [p.pattern_type.value for p in patterns[:3]]
        
        # Generate explanation
        explanation = self._generate_explanation(team_name, patterns)
        
        # Calculate confidence
        confidence = min(1.0, stats.sample_size / 15.0) * stats.data_quality_score
        
        return PatternDetectionResult(
            team_id=team_id,
            team_name=team_name,
            patterns=patterns,
            pattern_tags=tags,
            pattern_score=round(pattern_score, 2),
            pattern_explanation=explanation,
            dominant_patterns=dominant,
            sample_size=stats.sample_size,
            confidence=round(confidence, 2)
        )
    
    def _generate_explanation(self, team_name: str, patterns: List[Pattern]) -> str:
        """Generate human-readable explanation"""
        
        if not patterns:
            return f"No significant patterns detected for {team_name}."
        
        lines = [f"{team_name} shows the following patterns:"]
        
        for i, pattern in enumerate(patterns[:5], 1):
            lines.append(f"  {i}. {pattern.description} (strength: {pattern.strength.value})")
        
        # Add summary
        strong_patterns = [p for p in patterns if p.strength in (PatternStrength.STRONG, PatternStrength.EXTREME)]
        if strong_patterns:
            lines.append(f"\nFound {len(strong_patterns)} strong patterns.")
        
        return "\n".join(lines)
    
    def _create_empty_result(self, team_id: str, team_name: str) -> PatternDetectionResult:
        """Create empty result when insufficient data"""
        return PatternDetectionResult(
            team_id=team_id,
            team_name=team_name,
            pattern_explanation="Insufficient data for pattern detection"
        )
