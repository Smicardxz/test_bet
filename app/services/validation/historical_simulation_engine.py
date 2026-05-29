"""
Historical Simulation Engine
Valide la pertinence historique des signaux
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Résultat de simulation historique"""
    
    # Performance
    historical_hit_rate: float  # 0-100
    simulated_roi: Optional[float]  # 0-100 (None si pas d'odds)
    average_odds: Optional[float]  # Moyenne des cotes
    
    # Résultats
    wins: int
    losses: int
    total_bets: int
    
    # Risk metrics
    max_drawdown: float  # Pire série de pertes
    best_streak: int  # Meilleure série de gains
    worst_streak: int  # Pire série de pertes
    
    # Quality metrics
    consistency_score: float  # 0-100
    simulation_confidence: str  # LOW|MEDIUM|HIGH
    
    # Historical data
    variance: float
    historical_consistency: float  # 0-100
    long_term_stability: float  # 0-100
    
    # Validation
    historical_profitability: float  # 0-100
    validated_signal: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "historical_hit_rate": self.historical_hit_rate,
            "simulated_roi": self.simulated_roi,
            "average_odds": self.average_odds,
            "wins": self.wins,
            "losses": self.losses,
            "total_bets": self.total_bets,
            "max_drawdown": self.max_drawdown,
            "best_streak": self.best_streak,
            "worst_streak": self.worst_streak,
            "consistency_score": self.consistency_score,
            "simulation_confidence": self.simulation_confidence,
            "variance": self.variance,
            "historical_consistency": self.historical_consistency,
            "long_term_stability": self.long_term_stability,
            "historical_profitability": self.historical_profitability,
            "validated_signal": self.validated_signal
        }


class HistoricalSimulationEngine:
    """
    Simule historiquement les performances des signaux
    
    Objectif: Répondre "Si nous avions suivi ce signal historiquement, qu'aurait-il donné ?"
    """
    
    def simulate_signal(
        self,
        signal_type: str,
        market_type: str,
        line: float,
        historical_matches: List[Dict[str, Any]],
        bookmaker_odds: Optional[List[float]] = None
    ) -> SimulationResult:
        """
        Simule un signal sur données historiques
        
        Args:
            signal_type: Type de signal (EXTREME_UNDER, HT_UNDER, etc.)
            market_type: Type de marché (UNDER, OVER, BTTS, etc.)
            line: Ligne du marché (ex: 4.5 pour Under 4.5)
            historical_matches: Liste des matchs historiques
            bookmaker_odds: Cotes bookmaker (optionnel)
            
        Returns:
            SimulationResult avec toutes les métriques
        """
        
        if not historical_matches:
            return self._empty_result()
        
        # Simuler chaque match
        results = []
        for i, match in enumerate(historical_matches):
            result = self._simulate_match(match, market_type, line)
            results.append(result)
        
        # Calculer métriques
        wins = sum(1 for r in results if r)
        losses = sum(1 for r in results if not r)
        total_bets = len(results)
        hit_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        # ROI si odds disponibles
        simulated_roi = None
        average_odds = None
        if bookmaker_odds and len(bookmaker_odds) == len(results):
            roi, avg_odds = self._calculate_roi(results, bookmaker_odds)
            simulated_roi = roi
            average_odds = avg_odds
        
        # Streaks
        best_streak, worst_streak = self._calculate_streaks(results)
        
        # Drawdown
        max_drawdown = self._calculate_max_drawdown(results, bookmaker_odds)
        
        # Variance
        variance = stdev(results) if len(results) > 1 else 0
        
        # Consistency
        consistency_score = self._calculate_consistency(results)
        
        # Long-term stability
        long_term_stability = self._calculate_stability(results)
        
        # Confidence
        simulation_confidence = self._determine_confidence(total_bets, consistency_score, variance)
        
        # Profitability
        historical_profitability = self._calculate_profitability(hit_rate, simulated_roi)
        
        # Validation
        validated_signal = self._validate_signal(
            hit_rate,
            consistency_score,
            total_bets,
            simulated_roi
        )
        
        return SimulationResult(
            historical_hit_rate=hit_rate,
            simulated_roi=simulated_roi,
            average_odds=average_odds,
            wins=wins,
            losses=losses,
            total_bets=total_bets,
            max_drawdown=max_drawdown,
            best_streak=best_streak,
            worst_streak=worst_streak,
            consistency_score=consistency_score,
            simulation_confidence=simulation_confidence,
            variance=variance,
            historical_consistency=consistency_score,
            long_term_stability=long_term_stability,
            historical_profitability=historical_profitability,
            validated_signal=validated_signal
        )
    
    def _simulate_match(self, match: Dict[str, Any], market_type: str, line: float) -> bool:
        """Simule un match individuel"""
        
        total_goals = match.get("total_goals", 0)
        
        if market_type == "UNDER":
            return total_goals < line
        elif market_type == "OVER":
            return total_goals > line
        elif market_type == "BTTS_YES":
            home_goals = match.get("home_goals", 0)
            away_goals = match.get("away_goals", 0)
            return home_goals > 0 and away_goals > 0
        elif market_type == "BTTS_NO":
            home_goals = match.get("home_goals", 0)
            away_goals = match.get("away_goals", 0)
            return home_goals == 0 or away_goals == 0
        
        return False
    
    def _calculate_roi(self, results: List[bool], odds: List[float]) -> tuple:
        """Calcule ROI et moyenne des cotes"""
        
        total_stake = len(results)
        total_return = sum(odd if result else 0 for result, odd in zip(results, odds))
        roi = ((total_return - total_stake) / total_stake * 100) if total_stake > 0 else 0
        average_odds = mean(odds) if odds else None
        
        return roi, average_odds
    
    def _calculate_streaks(self, results: List[bool]) -> tuple:
        """Calcule meilleures et pires séries"""
        
        if not results:
            return 0, 0
        
        best_streak = 0
        worst_streak = 0
        current_streak = 0
        
        for result in results:
            if result:
                current_streak = current_streak + 1 if current_streak > 0 else 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = current_streak - 1 if current_streak < 0 else -1
                worst_streak = min(worst_streak, current_streak)
        
        return best_streak, abs(worst_streak)
    
    def _calculate_max_drawdown(self, results: List[bool], odds: Optional[List[float]]) -> float:
        """Calcule drawdown maximum"""
        
        if not results:
            return 0
        
        if odds and len(odds) == len(results):
            # Drawdown en unités
            balance = 0
            peak = 0
            max_dd = 0
            
            for result, odd in zip(results, odds):
                balance += (odd - 1) if result else -1
                peak = max(peak, balance)
                drawdown = peak - balance
                max_dd = max(max_dd, drawdown)
            
            return max_dd
        else:
            # Drawdown en nombre de paris perdus consécutifs
            return self._calculate_streaks(results)[1]
    
    def _calculate_consistency(self, results: List[bool]) -> float:
        """Calcule score de consistance (0-100)"""
        
        if len(results) < 5:
            return 50.0  # Pas assez de données
        
        # Diviser en segments
        segment_size = max(5, len(results) // 4)
        segments = [results[i:i+segment_size] for i in range(0, len(results), segment_size)]
        
        # Hit rate par segment
        segment_hit_rates = [
            sum(1 for r in seg if r) / len(seg) * 100
            for seg in segments if len(seg) >= 3
        ]
        
        if not segment_hit_rates:
            return 50.0
        
        # Variance entre segments (plus faible = plus consistant)
        variance = stdev(segment_hit_rates) if len(segment_hit_rates) > 1 else 0
        
        # Score: 100 - variance (plafonné à 100)
        consistency = max(0, 100 - variance * 2)
        
        return consistency
    
    def _calculate_stability(self, results: List[bool]) -> float:
        """Calcule stabilité long-terme (0-100)"""
        
        if len(results) < 10:
            return 50.0
        
        # Comparer première moitié vs deuxième moitié
        mid = len(results) // 2
        first_half = results[:mid]
        second_half = results[mid:]
        
        first_hit_rate = sum(1 for r in first_half if r) / len(first_half) * 100
        second_hit_rate = sum(1 for r in second_half if r) / len(second_half) * 100
        
        # Différence (plus faible = plus stable)
        diff = abs(first_hit_rate - second_hit_rate)
        
        # Score: 100 - diff (plafonné)
        stability = max(0, 100 - diff)
        
        return stability
    
    def _determine_confidence(self, sample_size: int, consistency: float, variance: float) -> str:
        """Détermine niveau de confiance"""
        
        if sample_size >= 20 and consistency >= 70 and variance < 0.3:
            return "HIGH"
        elif sample_size >= 10 and consistency >= 60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_profitability(self, hit_rate: float, roi: Optional[float]) -> float:
        """Calcule profitabilité historique (0-100)"""
        
        if roi is not None:
            # Si ROI disponible, l'utiliser directement
            return max(0, min(100, roi + 50))  # Normaliser autour de 50
        else:
            # Sinon, utiliser hit rate
            return hit_rate
    
    def _validate_signal(
        self,
        hit_rate: float,
        consistency: float,
        sample_size: int,
        roi: Optional[float]
    ) -> bool:
        """Valide si le signal est bon historiquement"""
        
        # Critères de validation
        min_hit_rate = 60.0
        min_consistency = 50.0
        min_sample_size = 10
        min_roi = 0.0  # ROI positif si disponible
        
        # Validation
        if sample_size < min_sample_size:
            return False
        
        if hit_rate < min_hit_rate:
            return False
        
        if consistency < min_consistency:
            return False
        
        if roi is not None and roi < min_roi:
            return False
        
        return True
    
    def _empty_result(self) -> SimulationResult:
        """Résultat vide si pas de données"""
        return SimulationResult(
            historical_hit_rate=0,
            simulated_roi=None,
            average_odds=None,
            wins=0,
            losses=0,
            total_bets=0,
            max_drawdown=0,
            best_streak=0,
            worst_streak=0,
            consistency_score=0,
            simulation_confidence="LOW",
            variance=0,
            historical_consistency=0,
            long_term_stability=0,
            historical_profitability=0,
            validated_signal=False
        )
