"""
Scan Result to Bet Candidate Converter
Converts scanner results to bet candidates for portfolio generation
"""

from typing import List
from app.services.scanner.daily_scanner_v2 import ScanResult
from app.services.betting.bet_candidate import BetCandidate, RiskLevel, Signal


def scan_result_to_bet_candidate(
    scan_result: ScanResult,
    is_real_data: bool = False
) -> BetCandidate:
    """
    Convert a ScanResult to a BetCandidate
    
    Args:
        scan_result: The scan result from the scanner
        is_real_data: Whether the data is real or mock
        
    Returns:
        BetCandidate instance
    """
    if not scan_result.anomaly_result:
        return None
    
    # Extract signals
    positive_signals = []
    if scan_result.anomaly_result.positive_signals:
        for sig in scan_result.anomaly_result.positive_signals:
            positive_signals.append(
                Signal(
                    type=sig.type,
                    description=sig.description,
                    strength=sig.strength.value if hasattr(sig.strength, 'value') else str(sig.strength)
                )
            )
    
    # Determine risk level
    risk_score = scan_result.anomaly_result.risk_score if hasattr(scan_result.anomaly_result, 'risk_score') else 0.5
    if risk_score <= 0.3:
        risk_level = RiskLevel.VERY_LOW
    elif risk_score <= 0.5:
        risk_level = RiskLevel.LOW
    elif risk_score <= 0.7:
        risk_level = RiskLevel.MODERATE
    elif risk_score <= 0.85:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.VERY_HIGH
    
    # Get anomaly result data
    anomaly = scan_result.anomaly_result
    
    # Create bet candidate with all required fields
    candidate = BetCandidate(
        match_id=scan_result.match_id,
        home_team=scan_result.home_team,
        away_team=scan_result.away_team,
        competition=scan_result.league,
        country=scan_result.country,
        kickoff_time=scan_result.kickoff_time,
        match_date=scan_result.match_date,
        market_type=scan_result.market_type,
        line=scan_result.line,
        bookmaker=scan_result.bookmaker,
        odd=scan_result.bookmaker_odds,
        anomaly_score=anomaly.anomaly_score,
        confidence_score=anomaly.confidence_score if hasattr(anomaly, 'confidence_score') else scan_result.data_quality_score,
        data_quality_score=scan_result.data_quality_score,
        risk_score=risk_score,
        priority_score=anomaly.priority_score if hasattr(anomaly, 'priority_score') else scan_result.final_score,
        model_probability=anomaly.model_probability if hasattr(anomaly, 'model_probability') else 0.0,
        bookmaker_probability=anomaly.bookmaker_probability if hasattr(anomaly, 'bookmaker_probability') else 0.0,
        edge_percentage=anomaly.edge_percentage if hasattr(anomaly, 'edge_percentage') else 0.0,
        confidence_category=anomaly.confidence_category.value if hasattr(anomaly.confidence_category, 'value') else str(anomaly.confidence_category),
        risk_level=risk_level,
        explanation_short=anomaly.explanation_short if hasattr(anomaly, 'explanation_short') else "",
        explanation_full=anomaly.explanation_full if hasattr(anomaly, 'explanation_full') else "",
        positive_signals=positive_signals,
        risk_factors=anomaly.risk_factors if hasattr(anomaly, 'risk_factors') else [],
        data_source="REAL" if is_real_data else "MOCK",
        sample_size=scan_result.home_sample_size + scan_result.away_sample_size
    )
    
    return candidate


def scan_results_to_bet_candidates(
    scan_results: List[ScanResult],
    is_real_data: bool = False
) -> List[BetCandidate]:
    """
    Convert multiple ScanResults to BetCandidates
    
    Args:
        scan_results: List of scan results
        is_real_data: Whether the data is real or mock
        
    Returns:
        List of BetCandidate instances
    """
    candidates = []
    
    for scan_result in scan_results:
        candidate = scan_result_to_bet_candidate(scan_result, is_real_data)
        if candidate:
            candidates.append(candidate)
    
    return candidates
