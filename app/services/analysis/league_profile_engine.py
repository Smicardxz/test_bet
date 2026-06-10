"""
League Profile Engine
Analyze and profile leagues for anomaly detection performance

Identifies the best obscure leagues to scan in priority
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging

from app.services.stats import TeamStats


logger = logging.getLogger(__name__)


class LeagueCategory(str, Enum):
    """League categories"""
    EXTREMELY_DEFENSIVE = "EXTREMELY_DEFENSIVE"
    DEFENSIVE = "DEFENSIVE"
    BALANCED = "BALANCED"
    OPEN = "OPEN"
    HIGH_SCORING = "HIGH_SCORING"
    INCONSISTENT = "INCONSISTENT"


@dataclass
class LeagueProfile:
    """Complete profile of a league"""
    
    # Identity
    league_name: str
    league_id: str = ""
    country: str = ""
    tier: int = 3  # 1=top, 5=obscure
    
    # Volume
    total_teams: int = 0
    total_matches_analyzed: int = 0
    total_anomalies_detected: int = 0
    
    # Scoring profile
    avg_goals_per_match: float = 0.0
    goals_variance: float = 0.0
    under_2_5_rate: float = 0.0
    under_1_5_rate: float = 0.0
    over_2_5_rate: float = 0.0
    btts_rate: float = 0.0
    
    # Half-time trends
    ht_00_rate: float = 0.0
    avg_ht_goals: float = 0.0
    ht_low_scoring: bool = False  # HT 0-0 > 50%
    
    # Line breach
    line_breach_frequency: float = 0.0  # How often lines breached
    extreme_under_rate: float = 0.0    # Under extreme lines
    
    # Scoring dynamics (STEP 1)
    second_half_goals_rate: float = 50.0  # % goals in 2nd half
    comeback_frequency: float = 0.0       # % matches with strong 2H comeback
    late_goal_frequency: float = 0.0      # % matches with more goals in 2H than 1H
    red_card_frequency: float = 0.0       # Red cards per match (if available)
    volatility_score: float = 0.0         # 0-100: how unpredictable is this league
    reliability_score: float = 0.0        # 0-100: inverse of volatility

    # Bookmaker
    avg_bookmaker_margin: float = 0.0
    avg_discrepancy: float = 0.0       # Average gap bookmaker/model
    high_discrepancy_matches: int = 0   # Count of strong anomalies
    
    # Anomaly performance
    high_conf_anomalies: int = 0
    high_conf_hit_rate: float = 0.0
    medium_conf_hit_rate: float = 0.0
    
    # Scores
    stability_score: float = 0.0         # 0-100, higher = more predictable
    exploitability_score: float = 0.0    # 0-100, higher = more exploitable
    obscurity_score: float = 0.0        # 0-100, higher = more obscure (good)
    
    # Category
    category: LeagueCategory = LeagueCategory.BALANCED
    
    # Recommendations
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "league_name": self.league_name,
            "country": self.country,
            "tier": self.tier,
            "total_matches": self.total_matches_analyzed,
            "avg_goals": round(self.avg_goals_per_match, 2),
            "goals_variance": round(self.goals_variance, 2),
            "under_2_5_rate": round(self.under_2_5_rate, 1),
            "under_1_5_rate": round(self.under_1_5_rate, 1),
            "ht_00_rate": round(self.ht_00_rate, 1),
            "avg_discrepancy": round(self.avg_discrepancy, 1),
            "high_conf_hit_rate": round(self.high_conf_hit_rate, 1),
            "stability_score": round(self.stability_score, 1),
            "exploitability_score": round(self.exploitability_score, 1),
            "obscurity_score": round(self.obscurity_score, 1),
            "category": self.category.value,
            "tags": self.tags
        }


@dataclass
class LeagueRanking:
    """Ranking of leagues by various criteria"""
    
    # Rankings
    by_exploitability: List[LeagueProfile] = field(default_factory=list)
    by_stability: List[LeagueProfile] = field(default_factory=list)
    by_under_rate: List[LeagueProfile] = field(default_factory=list)
    by_low_variance: List[LeagueProfile] = field(default_factory=list)
    by_ht_trends: List[LeagueProfile] = field(default_factory=list)
    
    # Best overall
    best_overall: Optional[LeagueProfile] = None
    best_for_under: Optional[LeagueProfile] = None
    best_for_ht: Optional[LeagueProfile] = None
    best_for_extreme: Optional[LeagueProfile] = None
    
    # Summary
    total_leagues: int = 0
    total_anomalies: int = 0
    avg_exploitability: float = 0.0
    
    # Recommendations
    priority_scan_list: List[str] = field(default_factory=list)
    avoid_list: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class LeagueProfileEngine:
    """
    League Profile Engine
    
    Analyzes and profiles leagues to identify the best obscure leagues
    for anomaly detection.
    
    Features:
    - League scoring profiles
    - Variance analysis
    - HT trends
    - Line breach patterns
    - Bookmaker discrepancy analysis
    - Stability scoring
    - Exploitability ranking
    """
    
    def __init__(self):
        """Initialize engine"""
        self.min_matches = 10
        self.min_anomalies = 3
    
    def analyze_leagues(
        self,
        league_stats: Dict[str, List[TeamStats]],
        league_anomalies: Optional[Dict[str, Dict]] = None
    ) -> LeagueRanking:
        """
        Analyze all leagues and create profiles
        
        Args:
            league_stats: Dict mapping league name to list of team stats
            league_anomalies: Optional dict with anomaly performance per league
            
        Returns:
            LeagueRanking with complete analysis
        """
        
        profiles = []
        
        for league_name, team_stats_list in league_stats.items():
            if len(team_stats_list) < 2:
                continue
            
            profile = self._create_profile(league_name, team_stats_list)
            
            # Add anomaly performance if available
            if league_anomalies and league_name in league_anomalies:
                self._add_anomaly_performance(profile, league_anomalies[league_name])
            
            profiles.append(profile)
        
        # Create ranking
        ranking = self._create_ranking(profiles)
        
        return ranking
    
    def _create_profile(self, league_name: str, team_stats: List[TeamStats]) -> LeagueProfile:
        """Create profile for a single league"""
        
        profile = LeagueProfile(league_name=league_name)
        profile.total_teams = len(team_stats)
        
        if not team_stats:
            return profile
        
        # Calculate league averages
        profile.avg_goals_per_match = statistics.mean(s.avg_total_goals for s in team_stats)
        profile.goals_variance = statistics.variance(s.avg_total_goals for s in team_stats) if len(team_stats) > 1 else 0
        profile.under_2_5_rate = statistics.mean(s.under_2_5_rate for s in team_stats)
        profile.under_1_5_rate = statistics.mean(s.under_1_5_rate for s in team_stats)
        profile.over_2_5_rate = statistics.mean(s.over_2_5_rate for s in team_stats)
        profile.btts_rate = statistics.mean(s.btts_rate for s in team_stats)
        profile.ht_00_rate = statistics.mean(s.ht_00_rate for s in team_stats)
        profile.avg_ht_goals = statistics.mean(s.avg_ht_total_goals for s in team_stats)
        
        # HT trends
        profile.ht_low_scoring = profile.ht_00_rate > 50
        
        # Calculate line breach frequency (simplified)
        # How often do teams exceed 2.5 goals?
        teams_over_2_5 = sum(1 for s in team_stats if s.avg_total_goals >= 2.5)
        profile.line_breach_frequency = (teams_over_2_5 / len(team_stats)) * 100
        
        # Extreme under rate
        profile.extreme_under_rate = statistics.mean(s.under_extreme_line_rate for s in team_stats)
        
        # Calculate stability
        # Lower variance in team stats = more stable league
        if len(team_stats) > 1:
            goal_variance = statistics.variance(s.avg_total_goals for s in team_stats)
            max_variance = 5.0  # Assume max reasonable variance
            profile.stability_score = max(0, 100 - (goal_variance / max_variance) * 100)
        else:
            profile.stability_score = 50
        
        # Calculate obscurity score
        # Lower tier = more obscure = better
        profile.obscurity_score = max(0, min(100, (5 - profile.tier) * 25))
        
        # Calculate exploitability
        profile.exploitability_score = self._calculate_exploitability(profile)
        
        # Categorize
        profile.category = self._categorize_league(profile)
        
        # Generate tags
        profile.tags = self._generate_tags(profile)
        
        return profile
    
    def _add_anomaly_performance(self, profile: LeagueProfile, anomaly_data: Dict):
        """Add anomaly detection performance to profile"""
        
        profile.total_anomalies_detected = anomaly_data.get("total_anomalies", 0)
        profile.high_conf_anomalies = anomaly_data.get("high_conf_count", 0)
        profile.high_conf_hit_rate = anomaly_data.get("high_conf_hit_rate", 0)
        profile.medium_conf_hit_rate = anomaly_data.get("medium_conf_hit_rate", 0)
        profile.avg_discrepancy = anomaly_data.get("avg_discrepancy", 0)
        profile.avg_bookmaker_margin = anomaly_data.get("avg_margin", 0)
    
    def _calculate_exploitability(self, profile: LeagueProfile) -> float:
        """
        Calculate league exploitability score
        
        Factors:
        - Under rate (weight: 30%)
        - HT 0-0 rate (weight: 20%)
        - Stability (weight: 20%)
        - Low variance (weight: 15%)
        - Obscurity (weight: 15%)
        """
        
        under_score = profile.under_2_5_rate
        ht_score = profile.ht_00_rate
        stability_score = profile.stability_score
        variance_score = max(0, 100 - profile.goals_variance * 10)
        obscurity_score = profile.obscurity_score
        
        exploitability = (
            under_score * 0.30 +
            ht_score * 0.20 +
            stability_score * 0.20 +
            variance_score * 0.15 +
            obscurity_score * 0.15
        )
        
        return min(100, max(0, exploitability))
    
    def _categorize_league(self, profile: LeagueProfile) -> LeagueCategory:
        """Categorize league based on profile"""
        
        if profile.avg_goals_per_match < 1.8 and profile.under_2_5_rate > 75:
            return LeagueCategory.EXTREMELY_DEFENSIVE
        elif profile.avg_goals_per_match < 2.2 and profile.under_2_5_rate > 60:
            return LeagueCategory.DEFENSIVE
        elif profile.avg_goals_per_match > 3.0 and profile.over_2_5_rate > 60:
            return LeagueCategory.HIGH_SCORING
        elif profile.goals_variance > 3.0:
            return LeagueCategory.INCONSISTENT
        elif profile.avg_goals_per_match > 2.5:
            return LeagueCategory.OPEN
        else:
            return LeagueCategory.BALANCED
    
    def _generate_tags(self, profile: LeagueProfile) -> List[str]:
        """Generate descriptive tags for league (STEP 1 enhanced)"""

        tags = []

        # --- Original tags ---
        if profile.under_2_5_rate > 70:
            tags.append("VERY_UNDER")
        if profile.under_1_5_rate > 50:
            tags.append("ULTRA_DEFENSIVE")
        if profile.ht_00_rate > 50:
            tags.append("HT_00_SPECIALIST")
        if profile.avg_goals_per_match < 2.0:
            tags.append("LOW_SCORING")
        if profile.stability_score > 70:
            tags.append("STABLE")
        if profile.goals_variance < 1.5:
            tags.append("CONSISTENT")
        if profile.exploitability_score > 70:
            tags.append("HIGHLY_EXPLOITABLE")
        if profile.obscurity_score > 60:
            tags.append("OBSCURE")
        if profile.extreme_under_rate > 90:
            tags.append("EXTREME_UNDER")

        # --- STEP 1: Intelligence tags ---
        if profile.avg_goals_per_match < 2.2 and "LOW_SCORING" not in tags:
            tags.append("LOW_SCORING_LEAGUE")
        if profile.goals_variance > 2.5:
            tags.append("HIGH_VOLATILITY_LEAGUE")
        if profile.avg_ht_goals < 0.75 and profile.ht_00_rate > 45:
            tags.append("HT_UNDER_FRIENDLY")
        if profile.btts_rate > 55:
            tags.append("BTTS_FRIENDLY")
        if profile.goals_variance > 3.0 and profile.avg_goals_per_match > 2.3:
            tags.append("CHAOTIC_LEAGUE")
        if profile.stability_score > 60 and profile.under_2_5_rate > 55:
            tags.append("STABLE_UNDER_LEAGUE")
        if profile.late_goal_frequency > 58:
            tags.append("LATE_GOAL_LEAGUE")
        if profile.volatility_score > 65:
            tags.append("YOUTH_CHAOS")   # Heuristic: high volatility leagues often = youth/amateur
        if profile.goals_variance > 3.5 and profile.btts_rate > 55:
            tags.append("WOMEN_HIGH_VARIANCE")  # Heuristic based on scoring pattern

        return tags

    def compute_from_match_context(
        self,
        ft_goals: List[int],
        ht_goals: Optional[List[int]] = None,
        match_history: Optional[List[Dict]] = None,
        league_name: str = "CONTEXT",
    ) -> LeagueProfile:
        """
        Construit un profil de ligue depuis le contexte disponible pour un match.
        Utilisé quand on n'a pas de base de données de ligue mais seulement
        l'historique des deux équipes.

        Args:
            ft_goals:      Historique buts FT combiné
            ht_goals:      Historique buts HT
            match_history: Dicts avec home_goals/away_goals
            league_name:   Nom de la ligue (optionnel)

        Returns:
            LeagueProfile (pseudo-profil de contexte)
        """
        profile = LeagueProfile(league_name=league_name)
        n = len(ft_goals)
        if n < 3:
            return profile

        profile.total_matches_analyzed = n
        mean = sum(ft_goals) / n
        profile.avg_goals_per_match = mean
        profile.under_2_5_rate = sum(1 for g in ft_goals if g < 2.5) / n * 100
        profile.under_1_5_rate = sum(1 for g in ft_goals if g < 1.5) / n * 100
        profile.over_2_5_rate = 100.0 - profile.under_2_5_rate

        if n > 1:
            profile.goals_variance = sum((g - mean) ** 2 for g in ft_goals) / n
            profile.line_breach_frequency = profile.over_2_5_rate

        if ht_goals and len(ht_goals) >= 3:
            nh = min(len(ht_goals), n)
            profile.avg_ht_goals = sum(ht_goals[:nh]) / nh
            ht_zeros = sum(1 for g in ht_goals[:nh] if g == 0)
            profile.ht_00_rate = ht_zeros / nh * 100
            profile.ht_low_scoring = profile.ht_00_rate > 50

            sh_goals = [ft_goals[i] - ht_goals[i] for i in range(nh)]
            total_1h = sum(ht_goals[:nh])
            total_2h = sum(sh_goals)
            total_all = total_1h + total_2h
            profile.second_half_goals_rate = (total_2h / total_all * 100) if total_all > 0 else 50.0
            profile.late_goal_frequency = (
                sum(1 for i in range(nh) if sh_goals[i] > ht_goals[i]) / nh * 100
            )

        if match_history and len(match_history) >= 3:
            nm = len(match_history)
            btts = sum(
                1 for m in match_history
                if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
            )
            profile.btts_rate = btts / nm * 100

            if ht_goals and len(ht_goals) >= 3:
                nh2 = min(len(match_history), len(ht_goals), n)
                comebacks = sum(
                    1 for i in range(nh2)
                    if (ft_goals[i] - ht_goals[i]) >= ht_goals[i] + 2
                )
                profile.comeback_frequency = comebacks / nh2 * 100

        # Computed composite scores
        profile.volatility_score = min(
            100.0, profile.goals_variance * 18 + max(ft_goals) * 2.5
        )
        profile.stability_score = max(0.0, 100.0 - (profile.goals_variance / 5.0) * 100)
        profile.reliability_score = max(0.0, 100.0 - profile.volatility_score * 0.70)
        profile.exploitability_score = self._calculate_exploitability(profile)
        profile.category = self._categorize_league(profile)
        profile.tags = self._generate_tags(profile)

        return profile

    def adjust_confidence_for_profile(
        self, base_confidence: float, profile: LeagueProfile
    ) -> Tuple[float, List[str]]:
        """
        Ajuste le score de confiance en fonction du profil de ligue/contexte.

        Args:
            base_confidence: Score de confiance initial (0-100)
            profile:         LeagueProfile calculé

        Returns:
            (adjusted_confidence, list_of_reasons)
        """
        adjusted = base_confidence
        reasons: List[str] = []

        # Ligue volatile → under moins fiable
        if profile.volatility_score > 70:
            adjusted *= 0.78
            reasons.append(f"HIGH_VOLATILITY ({profile.volatility_score:.0f}/100) -22%")
        elif profile.volatility_score > 50:
            adjusted *= 0.88
            reasons.append(f"MEDIUM_VOLATILITY ({profile.volatility_score:.0f}/100) -12%")

        # BTTS élevé = under 2.5 moins fiable
        if "BTTS_FRIENDLY" in profile.tags:
            adjusted *= 0.88
            reasons.append("BTTS_FRIENDLY league -12% under confidence")

        # Ligue chaotique
        if "CHAOTIC_LEAGUE" in profile.tags:
            adjusted *= 0.80
            reasons.append("CHAOTIC_LEAGUE -20%")

        # Buts tardifs = HT under moins fiable
        if "LATE_GOAL_LEAGUE" in profile.tags:
            adjusted *= 0.92
            reasons.append("LATE_GOAL_LEAGUE -8% HT confidence")

        # Ligue stable under → bonus de confiance
        if "STABLE_UNDER_LEAGUE" in profile.tags:
            adjusted = min(100.0, adjusted * 1.08)
            reasons.append("STABLE_UNDER_LEAGUE +8% under confidence")

        # HT friendly → bonus HT under
        if "HT_UNDER_FRIENDLY" in profile.tags:
            adjusted = min(100.0, adjusted * 1.05)
            reasons.append("HT_UNDER_FRIENDLY +5% HT confidence")

        return min(100.0, max(0.0, adjusted)), reasons
    
    def _create_ranking(self, profiles: List[LeagueProfile]) -> LeagueRanking:
        """Create league rankings"""
        
        ranking = LeagueRanking()
        ranking.total_leagues = len(profiles)
        
        if not profiles:
            return ranking
        
        # Sort by different criteria
        ranking.by_exploitability = sorted(
            profiles, key=lambda p: p.exploitability_score, reverse=True
        )
        ranking.by_stability = sorted(
            profiles, key=lambda p: p.stability_score, reverse=True
        )
        ranking.by_under_rate = sorted(
            profiles, key=lambda p: p.under_2_5_rate, reverse=True
        )
        ranking.by_low_variance = sorted(
            profiles, key=lambda p: p.goals_variance
        )
        ranking.by_ht_trends = sorted(
            profiles, key=lambda p: p.ht_00_rate, reverse=True
        )
        
        # Best overall
        ranking.best_overall = ranking.by_exploitability[0]
        ranking.best_for_under = ranking.by_under_rate[0]
        ranking.best_for_ht = ranking.by_ht_trends[0]
        
        # Best for extreme (extreme under rate)
        extreme_sorted = sorted(
            profiles, key=lambda p: p.extreme_under_rate, reverse=True
        )
        ranking.best_for_extreme = extreme_sorted[0] if extreme_sorted else None
        
        # Calculate averages
        ranking.avg_exploitability = statistics.mean(p.exploitability_score for p in profiles)
        
        # Priority lists
        ranking.priority_scan_list = [
            p.league_name for p in ranking.by_exploitability[:5]
            if p.exploitability_score >= 60
        ]
        
        ranking.avoid_list = [
            p.league_name for p in profiles
            if p.exploitability_score < 30
        ]
        
        # Recommendations
        ranking.recommendations = self._generate_recommendations(ranking)
        
        return ranking
    
    def _generate_recommendations(self, ranking: LeagueRanking) -> List[str]:
        """Generate strategic recommendations"""
        
        recs = []
        
        if not ranking.by_exploitability:
            return recs
        
        # Best league
        best = ranking.best_overall
        recs.append(
            f"🏆 PRIORITY LEAGUE: {best.league_name} "
            f"(Exploitability: {best.exploitability_score:.0f}/100, "
            f"Under: {best.under_2_5_rate:.0f}%)"
        )
        
        # Top under leagues
        under_leagues = [p for p in ranking.by_under_rate[:3] if p.under_2_5_rate > 60]
        if under_leagues:
            recs.append(
                f"🎯 UNDER MARKETS: Focus on {', '.join(p.league_name for p in under_leagues[:2])}"
            )
        
        # HT specialists
        ht_leagues = [p for p in ranking.by_ht_trends[:3] if p.ht_00_rate > 50]
        if ht_leagues:
            recs.append(
                f"⏱️  HT MARKETS: {', '.join(p.league_name for p in ht_leagues[:2])} "
                f"have strong HT 0-0 trends"
            )
        
        # Stable leagues
        stable = [p for p in ranking.by_stability[:3] if p.stability_score > 70]
        if stable:
            recs.append(
                f"📊 STABLE: {', '.join(p.league_name for p in stable[:2])} "
                f"are most predictable"
            )
        
        # Volume check
        high_volume = [p for p in ranking.by_exploitability if p.total_matches_analyzed >= 50]
        if len(high_volume) < 3:
            recs.append(
                "⚠️  Low volume: Need more matches for reliable league profiling"
            )
        
        # Avoid
        if ranking.avoid_list:
            recs.append(
                f"🚫 AVOID: {', '.join(ranking.avoid_list[:3])} - "
                f"low exploitability"
            )
        
        return recs
    
    def print_ranking(self, ranking: LeagueRanking):
        """Print detailed league ranking"""
        
        print("\n" + "=" * 100)
        print("LEAGUE PROFILE ANALYSIS")
        print("=" * 100)
        
        # Summary
        print("\n📊 SUMMARY")
        print(f"  Leagues Analyzed: {ranking.total_leagues}")
        print(f"  Average Exploitability: {ranking.avg_exploitability:.1f}/100")
        
        # Best overall
        if ranking.best_overall:
            print(f"\n  🏆 Best Overall: {ranking.best_overall.league_name}")
            print(f"     Exploitability: {ranking.best_overall.exploitability_score:.0f}/100")
        
        # Rankings
        print("\n📈 EXPLOITABILITY RANKING")
        print("-" * 100)
        print(f"{'Rank':<6} {'League':<35} {'Goals':<8} {'Under%':<8} "
              f"{'HT 0-0%':<8} {'Stable':<8} {'Exploit':<8}")
        print("-" * 100)
        
        for i, p in enumerate(ranking.by_exploitability[:10], 1):
            print(f"{i:<6} {p.league_name:<35} {p.avg_goals_per_match:<8.2f} "
                  f"{p.under_2_5_rate:<8.1f} {p.ht_00_rate:<8.1f} "
                  f"{p.stability_score:<8.0f} {p.exploitability_score:<8.0f}")
        
        # Under rate ranking
        print("\n🎯 MOST UNDER-PRONE LEAGUES")
        print("-" * 80)
        print(f"{'Rank':<6} {'League':<35} {'Under 2.5%':<12} {'Under 1.5%':<12}")
        print("-" * 80)
        
        for i, p in enumerate(ranking.by_under_rate[:5], 1):
            print(f"{i:<6} {p.league_name:<35} {p.under_2_5_rate:<12.1f} {p.under_1_5_rate:<12.1f}")
        
        # HT trends
        print("\n⏱️  HT TRENDS (0-0 Half Time)")
        print("-" * 80)
        print(f"{'Rank':<6} {'League':<35} {'HT 0-0%':<10} {'Avg HT Goals':<12}")
        print("-" * 80)
        
        for i, p in enumerate(ranking.by_ht_trends[:5], 1):
            print(f"{i:<6} {p.league_name:<35} {p.ht_00_rate:<10.1f} {p.avg_ht_goals:<12.2f}")
        
        # Most stable
        print("\n📊 MOST STABLE LEAGUES")
        print("-" * 80)
        print(f"{'Rank':<6} {'League':<35} {'Stability':<10} {'Variance':<10}")
        print("-" * 80)
        
        for i, p in enumerate(ranking.by_stability[:5], 1):
            print(f"{i:<6} {p.league_name:<35} {p.stability_score:<10.0f} {p.goals_variance:<10.2f}")
        
        # Categories
        print("\n🏷️  LEAGUE CATEGORIES")
        print("-" * 80)
        
        from collections import defaultdict
        categories = defaultdict(list)
        for p in ranking.by_exploitability:
            categories[p.category.value].append(p.league_name)
        
        for cat, leagues in categories.items():
            print(f"  {cat}: {', '.join(leagues[:3])}")
        
        # Priority list
        print("\n🎯 PRIORITY SCAN LIST")
        print("-" * 80)
        for i, league in enumerate(ranking.priority_scan_list[:5], 1):
            print(f"  {i}. {league}")
        
        # Recommendations
        print("\n💡 STRATEGIC RECOMMENDATIONS")
        print("-" * 80)
        for rec in ranking.recommendations:
            print(f"  {rec}")
        
        print("\n" + "=" * 100)
    
    def get_priority_leagues(
        self,
        ranking: LeagueRanking,
        min_exploitability: float = 65.0,
        max_results: int = 5
    ) -> List[LeagueProfile]:
        """Get priority leagues for scanning"""
        
        return [
            p for p in ranking.by_exploitability[:max_results]
            if p.exploitability_score >= min_exploitability
        ]
    
    def get_ht_specialist_leagues(
        self,
        ranking: LeagueRanking,
        min_ht_00_rate: float = 45.0
    ) -> List[LeagueProfile]:
        """Get leagues with strong HT 0-0 trends"""
        
        return [
            p for p in ranking.by_ht_trends
            if p.ht_00_rate >= min_ht_00_rate
        ]
    
    def get_under_specialist_leagues(
        self,
        ranking: LeagueRanking,
        min_under_rate: float = 65.0
    ) -> List[LeagueProfile]:
        """Get leagues with strong under trends"""
        
        return [
            p for p in ranking.by_under_rate
            if p.under_2_5_rate >= min_under_rate
        ]
