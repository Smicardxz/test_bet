"""
Score Breakdown Formatter
Format anomaly score breakdown for human-readable output

Modes:
- verbose: Full details
- compact: Summary only
- json: Machine-readable
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime

from app.services.anomaly.scoring_calibration import ScoreBreakdown
from app.services.anomaly.anomaly_engine import AnomalyResult


class ScoreBreakdownFormatter:
    """Format score breakdown for display"""
    
    def __init__(self, mode: str = "verbose"):
        """
        Initialize formatter
        
        Args:
            mode: "verbose", "compact", or "json"
        """
        self.mode = mode.lower()
    
    def format(self, result: AnomalyResult, breakdown: ScoreBreakdown) -> str:
        """Format based on mode"""
        if self.mode == "verbose":
            return self._format_verbose(result, breakdown)
        elif self.mode == "compact":
            return self._format_compact(result, breakdown)
        elif self.mode == "json":
            return self._format_json(result, breakdown)
        else:
            return self._format_verbose(result, breakdown)
    
    def _format_verbose(self, result: AnomalyResult, breakdown: ScoreBreakdown) -> str:
        """Full verbose output"""
        lines = []
        
        lines.append("=" * 80)
        lines.append("ANOMALY SCORE DEBUG - VERBOSE MODE")
        lines.append("=" * 80)
        lines.append("")
        
        # Header
        lines.append(f"Match ID: {result.match_id}")
        lines.append(f"Market: {result.market_type}")
        if result.line:
            lines.append(f"Line: {result.line}")
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Probabilities
        lines.append("-" * 80)
        lines.append("PROBABILITIES")
        lines.append("-" * 80)
        lines.append(f"  Bookmaker Odds:     {result.bookmaker_odds:.2f}")
        lines.append(f"  Bookmaker Prob:     {result.bookmaker_probability:.1%}")
        lines.append(f"  Normalized Prob:    {result.normalized_bookmaker_probability:.1%}")
        lines.append(f"  Model Prob:         {result.model_probability:.1%}")
        lines.append(f"  Gap:                {abs(result.normalized_bookmaker_probability - result.model_probability):.1%}")
        lines.append("")
        
        # Component Scores
        lines.append("-" * 80)
        lines.append("COMPONENT SCORES")
        lines.append("-" * 80)
        lines.append(f"  Discrepancy:        {result.discrepancy_score:6.1f}/100")
        lines.append(f"  Variance Safety:    {result.variance_safety_score:6.1f}/100")
        lines.append(f"  Historical Hit:     {result.historical_hit_rate:6.1f}/100")
        lines.append(f"  Stability:          {result.stability_score:6.1f}/100")
        lines.append("")
        
        # Weights
        lines.append("-" * 80)
        lines.append("WEIGHTS APPLIED")
        lines.append("-" * 80)
        w = breakdown.weights
        lines.append(f"  Discrepancy:        {w.discrepancy:.0%}")
        lines.append(f"  Variance Safety:    {w.variance_safety:.0%}")
        lines.append(f"  Historical Hit:     {w.historical_hit_rate:.0%}")
        lines.append(f"  Stability:          {w.stability:.0%}")
        lines.append(f"  Total:              {w.total():.0%}")
        lines.append("")
        
        # Weighted Contributions
        lines.append("-" * 80)
        lines.append("WEIGHTED CONTRIBUTIONS")
        lines.append("-" * 80)
        lines.append(f"  Discrepancy:        {breakdown.discrepancy_contribution:6.2f} (impact: {breakdown.get_component_impact()['discrepancy']:.1f}%)")
        lines.append(f"  Variance Safety:    {breakdown.variance_contribution:6.2f} (impact: {breakdown.get_component_impact()['variance_safety']:.1f}%)")
        lines.append(f"  Historical Hit:     {breakdown.historical_contribution:6.2f} (impact: {breakdown.get_component_impact()['historical']:.1f}%)")
        lines.append(f"  Stability:          {breakdown.stability_contribution:6.2f} (impact: {breakdown.get_component_impact()['stability']:.1f}%)")
        lines.append("")
        
        # Final Score
        lines.append("-" * 80)
        lines.append("FINAL SCORE")
        lines.append("-" * 80)
        lines.append(f"  Anomaly Score:      {result.anomaly_score:.2f}/100")
        lines.append(f"  Confidence Score:   {result.confidence_score:.2f}")
        lines.append(f"  Confidence Level:   {result.confidence_category.value}")
        lines.append("")
        
        # Data Quality
        lines.append("-" * 80)
        lines.append("DATA QUALITY")
        lines.append("-" * 80)
        lines.append(f"  Sample Size:        {result.sample_size}")
        lines.append(f"  Data Quality:       {result.data_quality:.2f}")
        lines.append("")
        
        # Signals
        if result.positive_signals:
            lines.append("-" * 80)
            lines.append("POSITIVE SIGNALS")
            lines.append("-" * 80)
            for signal in result.positive_signals:
                lines.append(f"  [{signal.strength.value}] {signal.type}: {signal.description}")
                lines.append(f"    Value: {signal.value:.2f}")
        
        if result.negative_signals:
            lines.append("")
            lines.append("-" * 80)
            lines.append("NEGATIVE SIGNALS")
            lines.append("-" * 80)
            for signal in result.negative_signals:
                lines.append(f"  [{signal.strength.value}] {signal.type}: {signal.description}")
                lines.append(f"    Value: {signal.value:.2f}")
        
        if result.risk_factors:
            lines.append("")
            lines.append("-" * 80)
            lines.append("RISK FACTORS")
            lines.append("-" * 80)
            for risk in result.risk_factors:
                lines.append(f"  ⚠️  {risk}")
        
        # Explanation
        lines.append("")
        lines.append("-" * 80)
        lines.append("EXPLANATION")
        lines.append("-" * 80)
        lines.append(f"  {result.explanation_summary}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _format_compact(self, result: AnomalyResult, breakdown: ScoreBreakdown) -> str:
        """Compact summary output"""
        lines = []
        
        lines.append("=" * 80)
        lines.append("ANOMALY DEBUG")
        lines.append("=" * 80)
        lines.append("")
        
        # Compact header
        lines.append(f"{result.market_type} | Score: {result.anomaly_score:.1f} | Conf: {result.confidence_category.value}")
        lines.append(f"Book: {result.normalized_bookmaker_probability:.1%} | Model: {result.model_probability:.1%} | Gap: {abs(result.normalized_bookmaker_probability - result.model_probability):.1%}")
        lines.append("")
        
        # Compact components
        lines.append("Components: D:{:.0f}×{:.0%}={:.1f} | V:{:.0f}×{:.0%}={:.1f} | H:{:.0f}×{:.0%}={:.1f} | S:{:.0f}×{:.0%}={:.1f}".format(
            result.discrepancy_score, breakdown.weights.discrepancy, breakdown.discrepancy_contribution,
            result.variance_safety_score, breakdown.weights.variance_safety, breakdown.variance_contribution,
            result.historical_hit_rate, breakdown.weights.historical_hit_rate, breakdown.historical_contribution,
            result.stability_score, breakdown.weights.stability, breakdown.stability_contribution
        ))
        lines.append(f"Final: {result.anomaly_score:.2f} | Quality: {result.data_quality:.2f} | Sample: {result.sample_size}")
        
        # Signals count
        pos_count = len(result.positive_signals)
        neg_count = len(result.negative_signals)
        risk_count = len(result.risk_factors)
        
        lines.append(f"Signals: +{pos_count} | -{neg_count} | Risks: {risk_count}")
        
        if risk_count > 0:
            lines.append("Risks: " + ", ".join(result.risk_factors[:3]))
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _format_json(self, result: AnomalyResult, breakdown: ScoreBreakdown) -> str:
        """JSON output for machine processing"""
        
        data = {
            "match_id": result.match_id,
            "market_type": result.market_type,
            "line": result.line,
            "timestamp": datetime.now().isoformat(),
            
            "probabilities": {
                "bookmaker_odds": result.bookmaker_odds,
                "bookmaker_probability": result.bookmaker_probability,
                "normalized_probability": result.normalized_bookmaker_probability,
                "model_probability": result.model_probability,
                "gap": abs(result.normalized_bookmaker_probability - result.model_probability)
            },
            
            "component_scores": {
                "discrepancy": {"raw": result.discrepancy_score, "weight": breakdown.weights.discrepancy, "contribution": breakdown.discrepancy_contribution},
                "variance_safety": {"raw": result.variance_safety_score, "weight": breakdown.weights.variance_safety, "contribution": breakdown.variance_contribution},
                "historical_hit": {"raw": result.historical_hit_rate, "weight": breakdown.weights.historical_hit_rate, "contribution": breakdown.historical_contribution},
                "stability": {"raw": result.stability_score, "weight": breakdown.weights.stability, "contribution": breakdown.stability_contribution}
            },
            
            "final_score": {
                "anomaly_score": result.anomaly_score,
                "confidence_score": result.confidence_score,
                "confidence_category": result.confidence_category.value
            },
            
            "data_quality": {
                "sample_size": result.sample_size,
                "quality_score": result.data_quality
            },
            
            "signals": {
                "positive": [
                    {"type": s.type, "strength": s.strength.value, "description": s.description, "value": s.value}
                    for s in result.positive_signals
                ],
                "negative": [
                    {"type": s.type, "strength": s.strength.value, "description": s.description, "value": s.value}
                    for s in result.negative_signals
                ]
            },
            
            "risk_factors": result.risk_factors,
            "explanation": result.explanation_summary
        }
        
        return json.dumps(data, indent=2)


def format_multi_anomalies(results: List[tuple], mode: str = "compact") -> str:
    """
    Format multiple anomaly results
    
    Args:
        results: List of (AnomalyResult, ScoreBreakdown) tuples
        mode: Formatting mode
        
    Returns:
        Formatted string
    """
    formatter = ScoreBreakdownFormatter(mode)
    
    outputs = []
    for result, breakdown in results:
        outputs.append(formatter.format(result, breakdown))
    
    return "\n\n".join(outputs)


def export_debug_json(result: AnomalyResult, breakdown: ScoreBreakdown, filepath: str):
    """Export debug info to JSON file"""
    formatter = ScoreBreakdownFormatter("json")
    json_str = formatter.format(result, breakdown)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json_str)
