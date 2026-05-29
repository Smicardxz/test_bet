"""
Premium Explanation Generator - Analytical, data-driven explanations
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ExplanationContext:
    """Context for generating explanations"""
    # Match info
    home_team: str
    away_team: str
    league: str
    
    # Market
    market_type: str
    bookmaker_line: Optional[float] = None
    bookmaker_odds: Optional[float] = None
    
    # Probabilities
    bookmaker_prob: float = 0.0
    model_prob: float = 0.0
    probability_gap: float = 0.0
    
    # Statistics
    home_avg_goals: float = 0.0
    away_avg_goals: float = 0.0
    combined_avg: float = 0.0
    expected_goals: float = 0.0
    
    # HT specific
    home_avg_ht: Optional[float] = None
    away_avg_ht: Optional[float] = None
    home_zero_zero_pct: Optional[float] = None
    away_zero_zero_pct: Optional[float] = None
    
    # Variance
    home_variance: float = 0.0
    away_variance: float = 0.0
    avg_variance: float = 0.0
    home_cv: float = 0.0
    away_cv: float = 0.0
    
    # Stability
    home_stability: float = 0.0
    away_stability: float = 0.0
    avg_stability: float = 0.0
    
    # Historical
    sample_size_home: int = 0
    sample_size_away: int = 0
    min_sample_size: int = 0
    breach_count: int = 0
    total_matches: int = 0
    breach_rate: float = 0.0
    
    # Scores
    anomaly_score: float = 0.0
    confidence_score: float = 0.0
    confidence_level: str = "MEDIUM"
    
    # Signals
    signals: List[str] = None
    
    # Pace (for HT)
    home_pace: Optional[str] = None
    away_pace: Optional[str] = None
    is_slow_starter_home: bool = False
    is_slow_starter_away: bool = False
    
    # BTTS
    home_btts_pct: Optional[float] = None
    away_btts_pct: Optional[float] = None


class PremiumExplanationGenerator:
    """
    Generate premium analytical explanations for anomalies
    
    Style:
    - Analytical
    - Clear
    - Professional
    - Prudent
    - Data-driven
    """
    
    def generate_explanation(self, context: ExplanationContext) -> str:
        """Generate complete explanation based on market type and confidence"""
        
        market_type = context.market_type
        confidence_level = context.confidence_level
        
        # Route to appropriate generator
        if "ht_under" in market_type or "ht_zero_zero" in market_type:
            return self._generate_ht_under_explanation(context, confidence_level)
        elif "ht_over" in market_type:
            return self._generate_ht_over_explanation(context, confidence_level)
        elif "ft_under" in market_type or "under_25" in market_type:
            return self._generate_ft_under_explanation(context, confidence_level)
        elif "ft_over" in market_type or "over_25" in market_type:
            return self._generate_ft_over_explanation(context, confidence_level)
        elif "extreme_under" in market_type:
            return self._generate_extreme_under_explanation(context, confidence_level)
        elif "btts" in market_type:
            return self._generate_btts_explanation(context, confidence_level)
        else:
            return self._generate_generic_explanation(context, confidence_level)
    
    # ==================== HT UNDER EXPLANATIONS ====================
    
    def _generate_ht_under_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate HT Under/0-0 HT explanation"""
        
        if level == "HIGH":
            return self._ht_under_high_confidence(ctx)
        elif level == "MEDIUM":
            return self._ht_under_medium_confidence(ctx)
        else:
            return self._ht_under_low_confidence(ctx)
    
    def _ht_under_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence HT Under explanation"""
        
        parts = []
        
        # Opening statement
        parts.append(
            f"**Analyse statistique : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        # Core statistics
        parts.append(
            f"Les deux équipes affichent une moyenne combinée de **{ctx.combined_avg:.2f} buts** "
            f"en première mi-temps sur leurs {ctx.min_sample_size} derniers matchs. "
        )
        
        # Zero-zero frequency
        if ctx.home_zero_zero_pct and ctx.away_zero_zero_pct:
            avg_zero_zero = (ctx.home_zero_zero_pct + ctx.away_zero_zero_pct) / 2
            parts.append(
                f"{ctx.home_team} termine à 0-0 à la mi-temps dans **{ctx.home_zero_zero_pct:.0f}%** "
                f"de ses matchs à domicile, tandis que {ctx.away_team} enregistre **{ctx.away_zero_zero_pct:.0f}%** "
                f"de 0-0 HT à l'extérieur. "
            )
        
        # Breach analysis
        if ctx.breach_count == 0:
            parts.append(
                f"Sur l'ensemble des {ctx.total_matches} rencontres analysées, "
                f"**aucun match n'a dépassé** la ligne proposée par le bookmaker. "
            )
        else:
            parts.append(
                f"Sur {ctx.total_matches} matchs analysés, seulement **{ctx.breach_count} rencontre(s)** "
                f"({ctx.breach_rate:.1%}) ont dépassé cette ligne. "
            )
        
        # Variance analysis
        if ctx.avg_variance < 0.5:
            parts.append(
                f"La variance combinée de **{ctx.avg_variance:.2f}** indique des scores "
                f"très prévisibles en première mi-temps. "
            )
        
        # Pace analysis
        if ctx.is_slow_starter_home and ctx.is_slow_starter_away:
            parts.append(
                f"Les deux formations sont identifiées comme **démarreurs lents** "
                f"({ctx.home_pace} et {ctx.away_pace}), renforçant la probabilité d'un début de match prudent. "
            )
        
        # Market discrepancy
        parts.append(
            f"\n**Écart de marché** : Le bookmaker évalue la probabilité à **{ctx.bookmaker_prob:.1%}**, "
            f"tandis que notre modèle statistique calcule **{ctx.model_prob:.1%}**, "
            f"soit un écart de **{ctx.probability_gap:.1%}**. "
        )
        
        # Confidence statement
        parts.append(
            f"\n**Niveau de confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%}) - "
            f"La cohérence des données historiques ({ctx.min_sample_size} matchs) "
            f"et la stabilité des performances (CV moyen : {(ctx.home_cv + ctx.away_cv)/2:.2f}) "
            f"supportent cette analyse."
        )
        
        return "".join(parts)
    
    def _ht_under_medium_confidence(self, ctx: ExplanationContext) -> str:
        """MEDIUM confidence HT Under explanation"""
        
        parts = []
        
        parts.append(
            f"**Analyse {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Les statistiques de première mi-temps montrent une moyenne combinée de "
            f"**{ctx.combined_avg:.2f} buts** sur les derniers matchs. "
        )
        
        if ctx.home_zero_zero_pct and ctx.away_zero_zero_pct:
            parts.append(
                f"{ctx.home_team} enregistre **{ctx.home_zero_zero_pct:.0f}%** de 0-0 HT à domicile, "
                f"{ctx.away_team} **{ctx.away_zero_zero_pct:.0f}%** à l'extérieur. "
            )
        
        parts.append(
            f"Le modèle identifie un écart de **{ctx.probability_gap:.1%}** entre "
            f"l'évaluation du marché ({ctx.bookmaker_prob:.1%}) et les probabilités calculées ({ctx.model_prob:.1%}). "
        )
        
        # Caution note for medium confidence
        if ctx.min_sample_size < 10:
            parts.append(
                f"\n**Note** : L'échantillon de {ctx.min_sample_size} matchs est modéré. "
                f"Une validation supplémentaire est recommandée. "
            )
        elif ctx.avg_variance > 0.7:
            parts.append(
                f"\n**Note** : La variance élevée ({ctx.avg_variance:.2f}) suggère une certaine imprévisibilité. "
                f"Approche prudente conseillée. "
            )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    def _ht_under_low_confidence(self, ctx: ExplanationContext) -> str:
        """LOW confidence HT Under explanation"""
        
        parts = []
        
        parts.append(
            f"**Analyse préliminaire : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Les données disponibles ({ctx.min_sample_size} matchs) suggèrent une moyenne "
            f"de {ctx.combined_avg:.2f} buts en première mi-temps. "
        )
        
        parts.append(
            f"Un écart de {ctx.probability_gap:.1%} est observé entre le marché et le modèle. "
        )
        
        # Warning for low confidence
        parts.append(
            f"\n**Avertissement** : "
        )
        
        if ctx.min_sample_size < 8:
            parts.append(
                f"L'échantillon de {ctx.min_sample_size} matchs est limité. "
            )
        
        if ctx.avg_stability < 0.5:
            parts.append(
                f"La stabilité des performances est faible ({ctx.avg_stability:.2f}). "
            )
        
        if ctx.avg_variance > 0.8:
            parts.append(
                f"La variance élevée ({ctx.avg_variance:.2f}) indique une forte imprévisibilité. "
            )
        
        parts.append(
            f"Cette analyse doit être considérée comme **indicative** uniquement. "
            f"\n\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    # ==================== HT OVER EXPLANATIONS ====================
    
    def _generate_ht_over_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate HT Over explanation"""
        
        if level == "HIGH":
            return self._ht_over_high_confidence(ctx)
        elif level == "MEDIUM":
            return self._ht_over_medium_confidence(ctx)
        else:
            return self._ht_over_low_confidence(ctx)
    
    def _ht_over_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence HT Over explanation"""
        
        parts = []
        
        parts.append(
            f"**Analyse offensive première mi-temps : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Les deux équipes démontrent un rythme offensif élevé en début de match, "
            f"avec une moyenne combinée de **{ctx.combined_avg:.2f} buts** en première mi-temps. "
        )
        
        # Over frequency
        if ctx.home_zero_zero_pct and ctx.away_zero_zero_pct:
            over_freq_home = 100 - ctx.home_zero_zero_pct
            over_freq_away = 100 - ctx.away_zero_zero_pct
            parts.append(
                f"{ctx.home_team} marque au moins un but avant la pause dans **{over_freq_home:.0f}%** "
                f"de ses matchs à domicile, {ctx.away_team} dans **{over_freq_away:.0f}%** de ses déplacements. "
            )
        
        # Fast starters
        if ctx.home_pace == "FAST" or ctx.home_pace == "VERY_FAST":
            parts.append(
                f"{ctx.home_team} est classé comme **démarreur rapide** ({ctx.home_pace}). "
            )
        
        if ctx.away_pace == "FAST" or ctx.away_pace == "VERY_FAST":
            parts.append(
                f"{ctx.away_team} affiche également un profil **offensif en début de match** ({ctx.away_pace}). "
            )
        
        # Market analysis
        parts.append(
            f"\n**Évaluation du marché** : L'écart de **{ctx.probability_gap:.1%}** entre "
            f"le bookmaker ({ctx.bookmaker_prob:.1%}) et notre modèle ({ctx.model_prob:.1%}) "
            f"suggère une sous-évaluation du potentiel offensif. "
        )
        
        # Stability
        parts.append(
            f"\n**Fiabilité** : Stabilité moyenne de **{ctx.avg_stability:.2f}** sur {ctx.min_sample_size} matchs. "
            f"Confiance : {ctx.confidence_level} ({ctx.confidence_score:.0%})."
        )
        
        return "".join(parts)
    
    def _ht_over_medium_confidence(self, ctx: ExplanationContext) -> str:
        """MEDIUM confidence HT Over"""
        
        parts = []
        
        parts.append(
            f"**Analyse {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Moyenne combinée de **{ctx.combined_avg:.2f} buts** en première mi-temps. "
        )
        
        parts.append(
            f"Écart marché-modèle : **{ctx.probability_gap:.1%}**. "
        )
        
        if ctx.avg_variance > 0.6:
            parts.append(
                f"\n**Note** : Variance modérée ({ctx.avg_variance:.2f}), prudence recommandée. "
            )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    def _ht_over_low_confidence(self, ctx: ExplanationContext) -> str:
        """LOW confidence HT Over"""
        return self._ht_under_low_confidence(ctx)  # Similar structure
    
    # ==================== FT UNDER EXPLANATIONS ====================
    
    def _generate_ft_under_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate FT Under explanation"""
        
        if level == "HIGH":
            return self._ft_under_high_confidence(ctx)
        elif level == "MEDIUM":
            return self._ft_under_medium_confidence(ctx)
        else:
            return self._ft_under_low_confidence(ctx)
    
    def _ft_under_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence FT Under"""
        
        parts = []
        
        parts.append(
            f"**Analyse match complet : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Sur leurs {ctx.min_sample_size} derniers matchs, les deux équipes affichent "
            f"une moyenne combinée de **{ctx.combined_avg:.2f} buts** par rencontre. "
        )
        
        parts.append(
            f"{ctx.home_team} marque en moyenne **{ctx.home_avg_goals:.2f} buts** à domicile, "
            f"{ctx.away_team} **{ctx.away_avg_goals:.2f} buts** à l'extérieur. "
        )
        
        # Breach analysis
        if ctx.breach_count == 0:
            parts.append(
                f"**Aucune des {ctx.total_matches} rencontres** analysées n'a dépassé la ligne {ctx.bookmaker_line}. "
            )
        else:
            parts.append(
                f"Seulement **{ctx.breach_count}/{ctx.total_matches} matchs** ({ctx.breach_rate:.1%}) "
                f"ont dépassé cette ligne historiquement. "
            )
        
        # Variance
        if ctx.avg_variance < 1.0:
            parts.append(
                f"La variance faible (**{ctx.avg_variance:.2f}**) indique des scores très cohérents. "
            )
        
        # Market discrepancy
        parts.append(
            f"\n**Écart de marché** : {ctx.probability_gap:.1%} entre bookmaker ({ctx.bookmaker_prob:.1%}) "
            f"et modèle ({ctx.model_prob:.1%}). "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%}) - "
            f"Échantillon robuste de {ctx.min_sample_size} matchs, stabilité {ctx.avg_stability:.2f}."
        )
        
        return "".join(parts)
    
    def _ft_under_medium_confidence(self, ctx: ExplanationContext) -> str:
        """MEDIUM confidence FT Under"""
        
        parts = []
        
        parts.append(
            f"**Analyse {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Moyenne combinée : **{ctx.combined_avg:.2f} buts**. "
            f"Écart marché : **{ctx.probability_gap:.1%}**. "
        )
        
        if ctx.min_sample_size < 10:
            parts.append(
                f"\n**Note** : Échantillon de {ctx.min_sample_size} matchs, validation recommandée. "
            )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    def _ft_under_low_confidence(self, ctx: ExplanationContext) -> str:
        """LOW confidence FT Under"""
        return self._ht_under_low_confidence(ctx)  # Similar structure
    
    # ==================== FT OVER EXPLANATIONS ====================
    
    def _generate_ft_over_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate FT Over explanation"""
        
        if level == "HIGH":
            return self._ft_over_high_confidence(ctx)
        else:
            return self._ft_under_medium_confidence(ctx)  # Similar structure
    
    def _ft_over_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence FT Over"""
        
        parts = []
        
        parts.append(
            f"**Analyse offensive : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Les deux formations démontrent un profil offensif marqué, "
            f"avec une moyenne combinée de **{ctx.combined_avg:.2f} buts** par match. "
        )
        
        parts.append(
            f"{ctx.home_team} : **{ctx.home_avg_goals:.2f} buts/match** à domicile. "
            f"{ctx.away_team} : **{ctx.away_avg_goals:.2f} buts/match** à l'extérieur. "
        )
        
        # Over frequency
        if ctx.breach_count > 0:
            parts.append(
                f"**{ctx.breach_count}/{ctx.total_matches} matchs** ({ctx.breach_rate:.1%}) "
                f"ont dépassé cette ligne historiquement. "
            )
        
        parts.append(
            f"\n**Écart de marché** : {ctx.probability_gap:.1%}. "
            f"Le bookmaker sous-estime potentiellement le potentiel offensif. "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    # ==================== EXTREME UNDER EXPLANATIONS ====================
    
    def _generate_extreme_under_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate Extreme Under explanation"""
        
        if level == "HIGH":
            return self._extreme_under_high_confidence(ctx)
        else:
            return self._extreme_under_medium_confidence(ctx)
    
    def _extreme_under_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence Extreme Under"""
        
        parts = []
        
        parts.append(
            f"**Analyse ligne extrême : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Les données historiques révèlent une moyenne combinée de **{ctx.combined_avg:.2f} buts** "
            f"sur {ctx.min_sample_size} matchs analysés. "
        )
        
        # Extreme line emphasis
        parts.append(
            f"La ligne proposée (**{ctx.bookmaker_line}**) est **statistiquement très éloignée** "
            f"des performances observées. "
        )
        
        # Breach analysis
        if ctx.breach_count == 0:
            parts.append(
                f"**Aucune des {ctx.total_matches} rencontres** n'a approché ce total. "
                f"Le maximum observé reste significativement inférieur. "
            )
        else:
            parts.append(
                f"Seulement **{ctx.breach_count} match(s)** sur {ctx.total_matches} "
                f"({ctx.breach_rate:.1%}) ont dépassé cette ligne. "
            )
        
        # Variance emphasis
        parts.append(
            f"\nLa variance combinée de **{ctx.avg_variance:.2f}** et le coefficient de variation "
            f"moyen de **{(ctx.home_cv + ctx.away_cv)/2:.2f}** indiquent des scores très prévisibles "
            f"et cohérents. "
        )
        
        # Market discrepancy
        parts.append(
            f"\n**Écart de marché** : Le bookmaker évalue cette probabilité à **{ctx.bookmaker_prob:.1%}**, "
            f"notre modèle à **{ctx.model_prob:.1%}**, soit un écart de **{ctx.probability_gap:.1%}**. "
            f"Cette ligne semble **statistiquement surévaluée** par le marché. "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%}) - "
            f"Échantillon robuste, variance faible, cohérence historique élevée."
        )
        
        return "".join(parts)
    
    def _extreme_under_medium_confidence(self, ctx: ExplanationContext) -> str:
        """MEDIUM confidence Extreme Under"""
        
        parts = []
        
        parts.append(
            f"**Analyse {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Moyenne historique : **{ctx.combined_avg:.2f} buts**. "
            f"Ligne bookmaker : **{ctx.bookmaker_line}**. "
        )
        
        parts.append(
            f"Breach rate : **{ctx.breach_rate:.1%}** ({ctx.breach_count}/{ctx.total_matches} matchs). "
        )
        
        parts.append(
            f"\n**Écart marché** : {ctx.probability_gap:.1%}. "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    # ==================== BTTS EXPLANATIONS ====================
    
    def _generate_btts_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generate BTTS explanation"""
        
        if level == "HIGH":
            return self._btts_high_confidence(ctx)
        elif level == "MEDIUM":
            return self._btts_medium_confidence(ctx)
        else:
            return self._btts_low_confidence(ctx)
    
    def _btts_high_confidence(self, ctx: ExplanationContext) -> str:
        """HIGH confidence BTTS"""
        
        parts = []
        
        parts.append(
            f"**Analyse Both Teams To Score : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        if ctx.home_btts_pct and ctx.away_btts_pct:
            parts.append(
                f"{ctx.home_team} enregistre **{ctx.home_btts_pct:.0f}%** de matchs avec BTTS à domicile, "
                f"{ctx.away_team} **{ctx.away_btts_pct:.0f}%** à l'extérieur. "
            )
            
            avg_btts = (ctx.home_btts_pct + ctx.away_btts_pct) / 2
            parts.append(
                f"La fréquence combinée de **{avg_btts:.0f}%** suggère une forte probabilité "
                f"que les deux équipes marquent. "
            )
        
        # Offensive stats
        parts.append(
            f"\n**Capacités offensives** : {ctx.home_team} marque en moyenne **{ctx.home_avg_goals:.2f} buts** "
            f"à domicile, {ctx.away_team} **{ctx.away_avg_goals:.2f} buts** à l'extérieur. "
        )
        
        # Market discrepancy
        parts.append(
            f"\n**Écart de marché** : {ctx.probability_gap:.1%} entre l'évaluation du bookmaker "
            f"({ctx.bookmaker_prob:.1%}) et notre modèle ({ctx.model_prob:.1%}). "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%}) - "
            f"Basé sur {ctx.min_sample_size} matchs, stabilité {ctx.avg_stability:.2f}."
        )
        
        return "".join(parts)
    
    def _btts_medium_confidence(self, ctx: ExplanationContext) -> str:
        """MEDIUM confidence BTTS"""
        
        parts = []
        
        parts.append(
            f"**Analyse BTTS : {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        if ctx.home_btts_pct and ctx.away_btts_pct:
            parts.append(
                f"Fréquence BTTS : {ctx.home_team} **{ctx.home_btts_pct:.0f}%**, "
                f"{ctx.away_team} **{ctx.away_btts_pct:.0f}%**. "
            )
        
        parts.append(
            f"Écart marché : **{ctx.probability_gap:.1%}**. "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
    
    def _btts_low_confidence(self, ctx: ExplanationContext) -> str:
        """LOW confidence BTTS"""
        return self._ht_under_low_confidence(ctx)  # Similar structure
    
    # ==================== GENERIC EXPLANATION ====================
    
    def _generate_generic_explanation(self, ctx: ExplanationContext, level: str) -> str:
        """Generic explanation for other markets"""
        
        parts = []
        
        parts.append(
            f"**Analyse {ctx.home_team} vs {ctx.away_team}**\n"
        )
        
        parts.append(
            f"Moyenne combinée : **{ctx.combined_avg:.2f} buts**. "
        )
        
        parts.append(
            f"Écart marché-modèle : **{ctx.probability_gap:.1%}**. "
        )
        
        parts.append(
            f"\n**Confiance** : {ctx.confidence_level} ({ctx.confidence_score:.0%})"
        )
        
        return "".join(parts)
