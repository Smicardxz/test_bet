"""
Explanation Engine - Generate human-readable explanations
Transform scores and statistics into clear, professional explanations
"""

from typing import Dict, List
from app.services.anomaly import AnomalyResult, ConfidenceCategory, SignalStrength


class ExplanationEngine:
    """
    Generate professional explanations for anomaly detections
    
    Style:
    - Analytical
    - Clear
    - Professional
    - Prudent
    - Data-driven
    
    Features:
    - Templates by confidence level
    - Templates by market type
    - Automatic signal-based generation
    - Risk factor highlighting
    """
    
    def __init__(self):
        """Initialize explanation engine"""
        pass
    
    def generate_explanation(self, anomaly: AnomalyResult) -> Dict[str, str]:
        """
        Generate complete explanation for an anomaly
        
        Args:
            anomaly: AnomalyResult to explain
        
        Returns:
            Dictionary with explanation sections
        """
        
        explanation = {
            "title": self._generate_title(anomaly),
            "summary": self._generate_summary(anomaly),
            "statistical_analysis": self._generate_statistical_analysis(anomaly),
            "confidence_explanation": self._generate_confidence_explanation(anomaly),
            "risk_assessment": self._generate_risk_assessment(anomaly),
            "recommendation": self._generate_recommendation(anomaly),
            "full_text": ""
        }
        
        # Combine all sections
        explanation["full_text"] = self._combine_sections(explanation)
        
        return explanation
    
    def _generate_title(self, anomaly: AnomalyResult) -> str:
        """Generate title"""
        
        market_names = {
            "ht_under_05": "HT Under 0.5 (0-0 HT)",
            "ht_over_05": "HT Over 0.5",
            "ht_under_15": "HT Under 1.5",
            "ft_under_15": "FT Under 1.5",
            "ft_under_25": "FT Under 2.5",
            "ft_over_25": "FT Over 2.5",
            "ft_under_35": "FT Under 3.5",
            "ft_over_35": "FT Over 3.5",
            "ft_under_65": "FT Under 6.5",
            "ft_under_85": "FT Under 8.5",
            "ft_under_105": "FT Under 10.5",
            "btts": "Both Teams To Score"
        }
        
        market_name = market_names.get(anomaly.market_type, anomaly.market_type)
        
        return f"Analyse Anomalie : {market_name}"
    
    def _generate_summary(self, anomaly: AnomalyResult) -> str:
        """Generate executive summary"""
        
        # Calculate gap
        gap = abs(anomaly.bookmaker_probability - anomaly.model_probability)
        gap_pct = gap * 100
        
        # Determine direction
        if anomaly.model_probability > anomaly.bookmaker_probability:
            direction = "sous-évalue"
            direction_detail = "plus élevée"
        else:
            direction = "surévalue"
            direction_detail = "plus faible"
        
        # Base summary
        summary = (
            f"**Écart détecté de {gap_pct:.1f}%** entre l'évaluation du bookmaker "
            f"({anomaly.bookmaker_probability:.1%}) et notre modèle statistique "
            f"({anomaly.model_probability:.1%}). "
        )
        
        # Add confidence context
        if anomaly.confidence_category == ConfidenceCategory.HIGH:
            summary += (
                f"Le bookmaker semble **{direction}** cette probabilité. "
                f"**Confiance élevée** ({anomaly.confidence_score:.0%}) basée sur "
                f"{anomaly.sample_size} matchs analysés."
            )
        elif anomaly.confidence_category == ConfidenceCategory.MEDIUM:
            summary += (
                f"Le bookmaker semble {direction} cette probabilité. "
                f"**Confiance modérée** ({anomaly.confidence_score:.0%}). "
                f"Approche prudente recommandée."
            )
        else:
            summary += (
                f"**Attention** : Confiance faible ({anomaly.confidence_score:.0%}). "
                f"Cette analyse doit être considérée comme indicative uniquement."
            )
        
        return summary
    
    def _generate_statistical_analysis(self, anomaly: AnomalyResult) -> str:
        """Generate statistical analysis section"""
        
        sections = []
        
        # Market-specific analysis
        if anomaly.market_type.startswith("ht_"):
            sections.append(self._analyze_ht_market(anomaly))
        elif "65" in anomaly.market_type or "85" in anomaly.market_type or "105" in anomaly.market_type:
            sections.append(self._analyze_extreme_under(anomaly))
        elif anomaly.market_type == "btts":
            sections.append(self._analyze_btts(anomaly))
        else:
            sections.append(self._analyze_standard_market(anomaly))
        
        # Variance analysis
        sections.append(self._analyze_variance(anomaly))
        
        # Stability analysis
        sections.append(self._analyze_stability(anomaly))
        
        return "\n\n".join(sections)
    
    def _analyze_ht_market(self, anomaly: AnomalyResult) -> str:
        """Analyze HT market"""
        
        text = "**Analyse Première Mi-Temps**\n\n"
        
        # Historical hit rate
        text += (
            f"Le taux de réussite historique pour ce marché est de **{anomaly.historical_hit_rate:.1f}%** "
            f"sur les {anomaly.sample_size} derniers matchs analysés. "
        )
        
        # Variance safety
        if anomaly.variance_safety_score >= 75:
            text += (
                f"La variance des scores en première mi-temps est **très faible** "
                f"({anomaly.variance_safety_score:.0f}/100), indiquant des performances "
                f"**hautement prévisibles**. "
            )
        elif anomaly.variance_safety_score >= 60:
            text += (
                f"La variance des scores en première mi-temps est **modérée** "
                f"({anomaly.variance_safety_score:.0f}/100). "
            )
        else:
            text += (
                f"**Attention** : La variance en première mi-temps est élevée "
                f"({anomaly.variance_safety_score:.0f}/100), suggérant une certaine imprévisibilité. "
            )
        
        # Positive signals
        ht_signals = [s for s in anomaly.positive_signals 
                     if "0-0" in s.description.lower() or "ht" in s.description.lower()]
        if ht_signals:
            text += f"Les équipes montrent un profil de **démarreurs lents** confirmé."
        
        return text
    
    def _analyze_extreme_under(self, anomaly: AnomalyResult) -> str:
        """Analyze extreme under market"""
        
        text = "**Analyse Ligne Extrême**\n\n"
        
        # Extract line
        if "105" in anomaly.market_type:
            line = 10.5
        elif "85" in anomaly.market_type:
            line = 8.5
        elif "65" in anomaly.market_type:
            line = 6.5
        else:
            line = anomaly.line
        
        text += (
            f"La ligne proposée (**{line}**) est **statistiquement très éloignée** "
            f"des performances observées. "
        )
        
        # Historical context
        if anomaly.historical_hit_rate >= 90:
            text += (
                f"Sur les {anomaly.sample_size} matchs analysés, **{anomaly.historical_hit_rate:.0f}%** "
                f"sont restés sous cette ligne, suggérant une **surévaluation significative** "
                f"par le bookmaker. "
            )
        elif anomaly.historical_hit_rate >= 80:
            text += (
                f"Historiquement, **{anomaly.historical_hit_rate:.0f}%** des matchs "
                f"restent sous cette ligne. "
            )
        
        # Variance
        if anomaly.variance_safety_score >= 70:
            text += (
                f"La variance faible ({anomaly.variance_safety_score:.0f}/100) "
                f"renforce la **cohérence** de ces statistiques."
            )
        
        return text
    
    def _analyze_btts(self, anomaly: AnomalyResult) -> str:
        """Analyze BTTS market"""
        
        text = "**Analyse Both Teams To Score**\n\n"
        
        text += (
            f"Le taux historique de matchs avec les deux équipes marquant est de "
            f"**{anomaly.historical_hit_rate:.1f}%**. "
        )
        
        # Gap analysis
        gap = abs(anomaly.bookmaker_probability - anomaly.model_probability)
        if gap >= 0.20:
            text += (
                f"L'écart de **{gap:.1%}** entre le bookmaker et le modèle suggère "
                f"une **évaluation incorrecte** des capacités offensives. "
            )
        elif gap >= 0.15:
            text += (
                f"Un écart notable de {gap:.1%} est observé. "
            )
        
        return text
    
    def _analyze_standard_market(self, anomaly: AnomalyResult) -> str:
        """Analyze standard FT market"""
        
        text = "**Analyse Match Complet**\n\n"
        
        text += (
            f"Les statistiques historiques montrent un taux de réussite de "
            f"**{anomaly.historical_hit_rate:.1f}%** pour ce marché. "
        )
        
        # Discrepancy
        if anomaly.discrepancy_score >= 75:
            text += (
                f"L'écart entre bookmaker et modèle est **très important** "
                f"({anomaly.discrepancy_score:.0f}/100), indiquant une "
                f"**incohérence majeure**. "
            )
        elif anomaly.discrepancy_score >= 50:
            text += (
                f"Un écart significatif ({anomaly.discrepancy_score:.0f}/100) "
                f"est observé. "
            )
        
        return text
    
    def _analyze_variance(self, anomaly: AnomalyResult) -> str:
        """Analyze variance"""
        
        text = "**Analyse de la Variance**\n\n"
        
        if anomaly.variance_safety_score >= 75:
            text += (
                f"✅ **Variance très faible** ({anomaly.variance_safety_score:.0f}/100). "
                f"Les scores sont **hautement prévisibles** et cohérents, "
                f"ce qui **augmente significativement la confiance** dans cette analyse. "
                f"Les équipes montrent des performances stables et répétables."
            )
        elif anomaly.variance_safety_score >= 60:
            text += (
                f"✅ **Variance modérée** ({anomaly.variance_safety_score:.0f}/100). "
                f"Les performances sont relativement cohérentes, offrant une "
                f"**base solide** pour l'analyse."
            )
        elif anomaly.variance_safety_score >= 40:
            text += (
                f"⚠️ **Variance moyenne** ({anomaly.variance_safety_score:.0f}/100). "
                f"Les résultats montrent une certaine variabilité. "
                f"**Approche prudente recommandée**."
            )
        else:
            text += (
                f"❌ **Variance élevée** ({anomaly.variance_safety_score:.0f}/100). "
                f"Les scores sont **imprévisibles**, ce qui **réduit fortement la confiance**. "
                f"Les performances fluctuent significativement d'un match à l'autre. "
                f"**Risque élevé de faux positif**."
            )
        
        return text
    
    def _analyze_stability(self, anomaly: AnomalyResult) -> str:
        """Analyze stability"""
        
        text = "**Analyse de la Stabilité**\n\n"
        
        if anomaly.stability_score >= 75:
            text += (
                f"✅ **Stabilité élevée** ({anomaly.stability_score:.0f}/100). "
                f"Les équipes montrent des **performances constantes** dans le temps, "
                f"renforçant la **fiabilité** des statistiques."
            )
        elif anomaly.stability_score >= 60:
            text += (
                f"✅ **Stabilité correcte** ({anomaly.stability_score:.0f}/100). "
                f"Les performances sont globalement cohérentes."
            )
        elif anomaly.stability_score >= 40:
            text += (
                f"⚠️ **Stabilité moyenne** ({anomaly.stability_score:.0f}/100). "
                f"Les équipes montrent des variations de forme. "
                f"**Prudence recommandée**."
            )
        else:
            text += (
                f"❌ **Stabilité faible** ({anomaly.stability_score:.0f}/100). "
                f"Les performances sont **incohérentes**, suggérant des équipes "
                f"en transition ou imprévisibles. **Risque accru**."
            )
        
        return text
    
    def _generate_confidence_explanation(self, anomaly: AnomalyResult) -> str:
        """Generate confidence explanation"""
        
        text = f"**Niveau de Confiance : {anomaly.confidence_category.value}** ({anomaly.confidence_score:.0%})\n\n"
        
        if anomaly.confidence_category == ConfidenceCategory.HIGH:
            text += self._explain_high_confidence(anomaly)
        elif anomaly.confidence_category == ConfidenceCategory.MEDIUM:
            text += self._explain_medium_confidence(anomaly)
        else:
            text += self._explain_low_confidence(anomaly)
        
        return text
    
    def _explain_high_confidence(self, anomaly: AnomalyResult) -> str:
        """Explain HIGH confidence"""
        
        reasons = []
        
        # Discrepancy
        if anomaly.discrepancy_score >= 60:
            gap_pct = abs(anomaly.bookmaker_probability - anomaly.model_probability) * 100
            reasons.append(f"**Écart important** de {gap_pct:.1f}% entre bookmaker et modèle")
        
        # Variance
        if anomaly.variance_safety_score >= 70:
            reasons.append(f"**Variance très faible** ({anomaly.variance_safety_score:.0f}/100) - scores prévisibles")
        
        # Stability
        if anomaly.stability_score >= 70:
            reasons.append(f"**Stabilité élevée** ({anomaly.stability_score:.0f}/100) - performances cohérentes")
        
        # Sample size
        if anomaly.sample_size >= 12:
            reasons.append(f"**Échantillon robuste** de {anomaly.sample_size} matchs")
        
        # Data quality
        if anomaly.data_quality >= 0.9:
            reasons.append(f"**Qualité des données excellente** ({anomaly.data_quality:.0%})")
        
        # Positive signals
        strong_signals = [s for s in anomaly.positive_signals if s.strength == SignalStrength.STRONG]
        if strong_signals:
            reasons.append(f"**{len(strong_signals)} signal(aux) fort(s)** détecté(s)")
        
        text = "**Facteurs de confiance élevée :**\n\n"
        for i, reason in enumerate(reasons, 1):
            text += f"{i}. {reason}\n"
        
        text += (
            f"\nCette combinaison de facteurs suggère une **anomalie significative** "
            f"avec un **risque de faux positif limité**."
        )
        
        return text
    
    def _explain_medium_confidence(self, anomaly: AnomalyResult) -> str:
        """Explain MEDIUM confidence"""
        
        text = "**Facteurs limitant la confiance :**\n\n"
        
        limitations = []
        
        # Sample size
        if anomaly.sample_size < 12:
            limitations.append(
                f"Échantillon modéré ({anomaly.sample_size} matchs) - "
                f"**validation supplémentaire recommandée**"
            )
        
        # Variance
        if 40 <= anomaly.variance_safety_score < 70:
            limitations.append(
                f"Variance moyenne ({anomaly.variance_safety_score:.0f}/100) - "
                f"**certaine imprévisibilité**"
            )
        
        # Data quality
        if anomaly.data_quality < 0.9:
            limitations.append(
                f"Qualité des données modérée ({anomaly.data_quality:.0%})"
            )
        
        # Discrepancy
        gap_pct = abs(anomaly.bookmaker_probability - anomaly.model_probability) * 100
        if gap_pct < 20:
            limitations.append(
                f"Écart modéré ({gap_pct:.1f}%) - anomalie moins prononcée"
            )
        
        for i, limitation in enumerate(limitations, 1):
            text += f"{i}. {limitation}\n"
        
        text += (
            f"\n**Recommandation** : Approche prudente. L'anomalie est détectée mais "
            f"certains facteurs limitent la confiance absolue. Considérer comme "
            f"**opportunité potentielle** nécessitant validation."
        )
        
        return text
    
    def _explain_low_confidence(self, anomaly: AnomalyResult) -> str:
        """Explain LOW confidence"""
        
        text = "⚠️ **ATTENTION : Confiance faible**\n\n"
        text += "**Facteurs de risque importants :**\n\n"
        
        risks = []
        
        # Sample size
        if anomaly.sample_size < 8:
            risks.append(
                f"**Échantillon très petit** ({anomaly.sample_size} matchs) - "
                f"**fiabilité limitée**"
            )
        
        # Variance
        if anomaly.variance_safety_score < 40:
            risks.append(
                f"**Variance élevée** ({anomaly.variance_safety_score:.0f}/100) - "
                f"**scores imprévisibles**"
            )
        
        # Stability
        if anomaly.stability_score < 50:
            risks.append(
                f"**Stabilité faible** ({anomaly.stability_score:.0f}/100) - "
                f"**performances incohérentes**"
            )
        
        # Data quality
        if anomaly.data_quality < 0.7:
            risks.append(
                f"**Qualité des données faible** ({anomaly.data_quality:.0%}) - "
                f"**données manquantes importantes**"
            )
        
        for i, risk in enumerate(risks, 1):
            text += f"{i}. {risk}\n"
        
        text += (
            f"\n**⚠️ AVERTISSEMENT** : Cette analyse doit être considérée comme "
            f"**purement indicative**. Le risque de faux positif est **élevé**. "
            f"**Ne pas utiliser** comme base de décision sans validation externe approfondie."
        )
        
        return text
    
    def _generate_risk_assessment(self, anomaly: AnomalyResult) -> str:
        """Generate risk assessment"""
        
        if not anomaly.risk_factors:
            return "**Évaluation des Risques**\n\n✅ Aucun facteur de risque majeur identifié."
        
        text = "**Évaluation des Risques**\n\n"
        
        for i, risk in enumerate(anomaly.risk_factors, 1):
            text += f"{i}. ⚠️ {risk}\n"
        
        # Add context based on number of risks
        if len(anomaly.risk_factors) >= 3:
            text += (
                f"\n**Risque global : ÉLEVÉ**. Plusieurs facteurs limitent la fiabilité "
                f"de cette analyse. Approche très prudente requise."
            )
        elif len(anomaly.risk_factors) >= 2:
            text += (
                f"\n**Risque global : MODÉRÉ**. Certains facteurs nécessitent attention. "
                f"Validation recommandée."
            )
        else:
            text += (
                f"\n**Risque global : FAIBLE**. Facteur(s) à surveiller mais "
                f"impact limité sur la fiabilité globale."
            )
        
        return text
    
    def _generate_recommendation(self, anomaly: AnomalyResult) -> str:
        """Generate recommendation"""
        
        text = "**Recommandation**\n\n"
        
        if anomaly.confidence_category == ConfidenceCategory.HIGH:
            if anomaly.anomaly_score >= 75:
                text += (
                    f"✅ **Anomalie forte** (score {anomaly.anomaly_score:.0f}/100) "
                    f"avec **confiance élevée**. Cette opportunité présente un "
                    f"**profil risque/rendement favorable** basé sur l'analyse statistique. "
                    f"Les données supportent une **incohérence significative** dans "
                    f"l'évaluation du bookmaker."
                )
            else:
                text += (
                    f"✅ **Anomalie modérée** (score {anomaly.anomaly_score:.0f}/100) "
                    f"avec confiance élevée. Opportunité intéressante mais moins prononcée."
                )
        
        elif anomaly.confidence_category == ConfidenceCategory.MEDIUM:
            text += (
                f"⚠️ **Approche prudente recommandée**. L'anomalie est détectée "
                f"(score {anomaly.anomaly_score:.0f}/100) mais certains facteurs "
                f"limitent la confiance. Considérer comme **opportunité potentielle** "
                f"nécessitant validation supplémentaire ou mise en contexte."
            )
        
        else:  # LOW
            text += (
                f"❌ **Non recommandé**. Malgré un score d'anomalie de "
                f"{anomaly.anomaly_score:.0f}/100, la **confiance est trop faible** "
                f"pour justifier une action. Risque élevé de faux positif. "
                f"**Utiliser uniquement à titre informatif**."
            )
        
        return text
    
    def _combine_sections(self, sections: Dict[str, str]) -> str:
        """Combine all sections into full text"""
        
        full_text = f"{sections['title']}\n\n"
        full_text += f"{sections['summary']}\n\n"
        full_text += "=" * 60 + "\n\n"
        full_text += f"{sections['statistical_analysis']}\n\n"
        full_text += "=" * 60 + "\n\n"
        full_text += f"{sections['confidence_explanation']}\n\n"
        full_text += "=" * 60 + "\n\n"
        full_text += f"{sections['risk_assessment']}\n\n"
        full_text += "=" * 60 + "\n\n"
        full_text += f"{sections['recommendation']}\n"
        
        return full_text
