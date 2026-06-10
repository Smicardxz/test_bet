"""
Functional Validation Suite
20 realistic test cases to validate anomaly detection accuracy
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional
from app.services.stats import TeamStats
from app.services.anomaly import AnomalyEngine, ConfidenceCategory


@dataclass
class MatchHistorical:
    """Synthetic historical data for a team"""
    matches_played: int
    avg_goals_scored: float
    avg_goals_conceded: float
    avg_ht_goals_scored: float
    avg_ht_goals_conceded: float
    variance_goals: float
    btts_rate: float  # 0-1
    ht_00_rate: float  # 0-1


@dataclass
class TestCase:
    """Functional test case"""
    id: str
    name: str
    competition: str
    home_team: str
    away_team: str
    market_type: str
    line: Optional[float]
    bookmaker_odds: float
    
    # Historical data
    home_historical: MatchHistorical
    away_historical: MatchHistorical
    
    # Expected results
    expected_anomaly_detected: bool
    expected_anomaly_score_min: float
    expected_anomaly_score_max: float
    expected_confidence: ConfidenceCategory
    expected_reason: str


# =============================================================================
# TEST CASES DEFINITION
# =============================================================================

TEST_CASES = [
    
    # =========================================================================
    # STRONG ANOMALIES (HIGH CONFIDENCE)
    # =========================================================================
    
    TestCase(
        id="STRONG_01",
        name="HT Under 0.5 - Très défensif, variance faible",
        competition="England Women's Championship",
        home_team="London City Lionesses",
        away_team="Bristol City",
        market_type="ht_under_05",
        line=0.5,
        bookmaker_odds=2.50,  # 40% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.6,
            avg_goals_conceded=0.4,
            avg_ht_goals_scored=0.2,
            avg_ht_goals_conceded=0.15,
            variance_goals=0.3,
            btts_rate=0.25,
            ht_00_rate=0.75
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.5,
            avg_goals_conceded=0.3,
            avg_ht_goals_scored=0.18,
            avg_ht_goals_conceded=0.12,
            variance_goals=0.28,
            btts_rate=0.22,
            ht_00_rate=0.78
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=70.0,
        expected_anomaly_score_max=85.0,
        expected_confidence=ConfidenceCategory.HIGH,
        expected_reason="Bookmaker sous-estime fortement le taux de 0-0 HT (75-78% historique vs 40% implicite). Variance très faible = haute prévisibilité."
    ),
    
    TestCase(
        id="STRONG_02",
        name="Extreme Under 10.5 - Très bas scoring",
        competition="England National League North",
        home_team="Curzon Ashton",
        away_team="Brackley Town",
        market_type="ft_under_105",
        line=10.5,
        bookmaker_odds=1.50,  # 67% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.8,
            avg_goals_conceded=0.7,
            avg_ht_goals_scored=0.3,
            avg_ht_goals_conceded=0.25,
            variance_goals=0.5,
            btts_rate=0.35,
            ht_00_rate=0.65
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.7,
            avg_goals_conceded=0.6,
            avg_ht_goals_scored=0.25,
            avg_ht_goals_conceded=0.22,
            variance_goals=0.48,
            btts_rate=0.32,
            ht_00_rate=0.68
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=75.0,
        expected_anomaly_score_max=90.0,
        expected_confidence=ConfidenceCategory.HIGH,
        expected_reason="Ligne 10.5 statistiquement très éloignée (avg total ~1.5 goals). Bookmaker surévalue à 67% alors que probabilité réelle ~95%+."
    ),
    
    TestCase(
        id="STRONG_03",
        name="FT Under 2.5 - Défensif stable",
        competition="France National 3",
        home_team="Granville",
        away_team="Vitré",
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=2.30,  # 43% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.0,
            avg_goals_conceded=0.9,
            avg_ht_goals_scored=0.4,
            avg_ht_goals_conceded=0.35,
            variance_goals=0.6,
            btts_rate=0.45,
            ht_00_rate=0.55
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.9,
            avg_goals_conceded=0.8,
            avg_ht_goals_scored=0.35,
            avg_ht_goals_conceded=0.3,
            variance_goals=0.58,
            btts_rate=0.42,
            ht_00_rate=0.58
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=65.0,
        expected_anomaly_score_max=78.0,
        expected_confidence=ConfidenceCategory.HIGH,
        expected_reason="Total attendu ~1.7 goals, bien sous 2.5. Variance faible confirme stabilité. Bookmaker sous-estime Under."
    ),
    
    TestCase(
        id="STRONG_04",
        name="BTTS - Équipes offensives",
        competition="England U21 Premier League",
        home_team="Manchester United U21",
        away_team="Liverpool U21",
        market_type="btts",
        line=None,
        bookmaker_odds=2.20,  # 45% implied
        home_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.3,
            avg_goals_conceded=1.8,
            avg_ht_goals_scored=1.0,
            avg_ht_goals_conceded=0.8,
            variance_goals=2.5,
            btts_rate=0.72,
            ht_00_rate=0.28
        ),
        away_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.1,
            avg_goals_conceded=1.9,
            avg_ht_goals_scored=0.9,
            avg_ht_goals_conceded=0.85,
            variance_goals=2.3,
            btts_rate=0.70,
            ht_00_rate=0.30
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=60.0,
        expected_anomaly_score_max=75.0,
        expected_confidence=ConfidenceCategory.MEDIUM,  # Variance élevée réduit confiance
        expected_reason="BTTS historique 70-72% vs 45% implicite. Écart significatif mais variance élevée (U21) réduit confiance."
    ),
    
    # =========================================================================
    # MEDIUM ANOMALIES (MEDIUM CONFIDENCE)
    # =========================================================================
    
    TestCase(
        id="MEDIUM_01",
        name="FT Under 2.5 - Échantillon modéré",
        competition="England Women's Championship",
        home_team="Lewes Women",
        away_team="Southampton Women",
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=2.10,  # 48% implied
        home_historical=MatchHistorical(
            matches_played=10,  # Échantillon limite
            avg_goals_scored=1.2,
            avg_goals_conceded=1.0,
            avg_ht_goals_scored=0.5,
            avg_ht_goals_conceded=0.45,
            variance_goals=0.85,
            btts_rate=0.55,
            ht_00_rate=0.45
        ),
        away_historical=MatchHistorical(
            matches_played=10,
            avg_goals_scored=1.1,
            avg_goals_conceded=1.1,
            avg_ht_goals_scored=0.48,
            avg_ht_goals_conceded=0.5,
            variance_goals=0.9,
            btts_rate=0.58,
            ht_00_rate=0.42
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=55.0,
        expected_anomaly_score_max=68.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="Total attendu ~2.2 goals. Anomalie détectée mais échantillon modéré (10 matchs) et variance moyenne limitent confiance."
    ),
    
    TestCase(
        id="MEDIUM_02",
        name="HT Under 0.5 - Variance moyenne",
        competition="France National 3",
        home_team="US Avranches",
        away_team="Stade Briochin",
        market_type="ht_under_05",
        line=0.5,
        bookmaker_odds=2.30,  # 43% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.5,
            avg_goals_conceded=1.2,
            avg_ht_goals_scored=0.6,
            avg_ht_goals_conceded=0.5,
            variance_goals=1.2,
            btts_rate=0.58,
            ht_00_rate=0.48
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.3,
            avg_goals_conceded=1.4,
            avg_ht_goals_scored=0.55,
            avg_ht_goals_conceded=0.6,
            variance_goals=1.3,
            btts_rate=0.52,
            ht_00_rate=0.50
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=52.0,
        expected_anomaly_score_max=65.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="HT 0-0 rate ~49% vs 43% implicite. Écart modéré, variance moyenne réduit confiance."
    ),
    
    TestCase(
        id="MEDIUM_03",
        name="FT Over 2.5 - Écart modéré",
        competition="England U21 Premier League",
        home_team="Chelsea U21",
        away_team="Arsenal U21",
        market_type="ft_over_25",
        line=2.5,
        bookmaker_odds=2.00,  # 50% implied
        home_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.2,
            avg_goals_conceded=1.7,
            avg_ht_goals_scored=0.9,
            avg_ht_goals_conceded=0.75,
            variance_goals=2.4,
            btts_rate=0.68,
            ht_00_rate=0.32
        ),
        away_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.0,
            avg_goals_conceded=1.8,
            avg_ht_goals_scored=0.85,
            avg_ht_goals_conceded=0.8,
            variance_goals=2.6,
            btts_rate=0.65,
            ht_00_rate=0.35
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=50.0,
        expected_anomaly_score_max=63.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="Total attendu ~3.8 goals suggère Over 2.5. Mais variance très élevée (U21) = imprévisibilité."
    ),
    
    # =========================================================================
    # FALSE POSITIVES (LOW CONFIDENCE - High Variance)
    # =========================================================================
    
    TestCase(
        id="FALSE_01",
        name="FT Under 2.5 - Variance très élevée",
        competition="England U21 Premier League",
        home_team="Manchester City U21",
        away_team="Tottenham U21",
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=2.20,  # 45% implied
        home_historical=MatchHistorical(
            matches_played=10,
            avg_goals_scored=2.0,
            avg_goals_conceded=2.2,
            avg_ht_goals_scored=0.9,
            avg_ht_goals_conceded=1.0,
            variance_goals=3.2,  # Très élevée
            btts_rate=0.70,
            ht_00_rate=0.30
        ),
        away_historical=MatchHistorical(
            matches_played=10,
            avg_goals_scored=1.9,
            avg_goals_conceded=2.3,
            avg_ht_goals_scored=0.85,
            avg_ht_goals_conceded=1.1,
            variance_goals=3.5,  # Très élevée
            btts_rate=0.72,
            ht_00_rate=0.28
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=45.0,
        expected_anomaly_score_max=58.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="Variance extrême (3.2-3.5) = scores imprévisibles. Risque élevé de faux positif malgré écart statistique."
    ),
    
    TestCase(
        id="FALSE_02",
        name="BTTS - Petit échantillon + variance",
        competition="England Women's Championship",
        home_team="Durham Women",
        away_team="Charlton Athletic Women",
        market_type="btts",
        line=None,
        bookmaker_odds=2.40,  # 42% implied
        home_historical=MatchHistorical(
            matches_played=6,  # Très petit
            avg_goals_scored=1.5,
            avg_goals_conceded=1.3,
            avg_ht_goals_scored=0.6,
            avg_ht_goals_conceded=0.5,
            variance_goals=1.8,
            btts_rate=0.67,
            ht_00_rate=0.33
        ),
        away_historical=MatchHistorical(
            matches_played=7,  # Très petit
            avg_goals_scored=1.4,
            avg_goals_conceded=1.2,
            avg_ht_goals_scored=0.55,
            avg_ht_goals_conceded=0.48,
            variance_goals=1.9,
            btts_rate=0.71,
            ht_00_rate=0.29
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=40.0,
        expected_anomaly_score_max=55.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="Échantillon trop petit (6-7 matchs) + variance élevée = fiabilité limitée. Faux positif probable."
    ),
    
    # =========================================================================
    # COHERENT LINES (No Anomaly or Very Weak)
    # =========================================================================
    
    TestCase(
        id="COHERENT_01",
        name="FT Under 2.5 - Ligne cohérente",
        competition="France National 3",
        home_team="Granville",
        away_team="US Avranches",
        market_type="ft_under_25",
        line=2.5,
        bookmaker_odds=2.00,  # 50% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.3,
            avg_goals_conceded=1.2,
            avg_ht_goals_scored=0.5,
            avg_ht_goals_conceded=0.48,
            variance_goals=0.9,
            btts_rate=0.50,
            ht_00_rate=0.50
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.2,
            avg_goals_conceded=1.3,
            avg_ht_goals_scored=0.48,
            avg_ht_goals_conceded=0.52,
            variance_goals=0.95,
            btts_rate=0.48,
            ht_00_rate=0.52
        ),
        expected_anomaly_detected=False,
        expected_anomaly_score_min=0.0,
        expected_anomaly_score_max=45.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="Total attendu ~2.5 goals = ligne bookmaker cohérente. Pas d'anomalie significative."
    ),
    
    TestCase(
        id="COHERENT_02",
        name="HT Under 0.5 - Ligne correcte",
        competition="England Women's Championship",
        home_team="Lewes Women",
        away_team="Southampton Women",
        market_type="ht_under_05",
        line=0.5,
        bookmaker_odds=2.00,  # 50% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.2,
            avg_goals_conceded=1.0,
            avg_ht_goals_scored=0.5,
            avg_ht_goals_conceded=0.45,
            variance_goals=0.85,
            btts_rate=0.55,
            ht_00_rate=0.50
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.1,
            avg_goals_conceded=1.1,
            avg_ht_goals_scored=0.48,
            avg_ht_goals_conceded=0.5,
            variance_goals=0.9,
            btts_rate=0.52,
            ht_00_rate=0.48
        ),
        expected_anomaly_detected=False,
        expected_anomaly_score_min=0.0,
        expected_anomaly_score_max=42.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="HT 0-0 rate ~49% = odds 2.00 cohérents. Bookmaker évalue correctement."
    ),
    
    TestCase(
        id="COHERENT_03",
        name="BTTS - Ligne équilibrée",
        competition="France National 3",
        home_team="Stade Briochin",
        away_team="Vitré",
        market_type="btts",
        line=None,
        bookmaker_odds=2.00,  # 50% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.4,
            avg_goals_conceded=1.3,
            avg_ht_goals_scored=0.55,
            avg_ht_goals_conceded=0.52,
            variance_goals=1.1,
            btts_rate=0.53,
            ht_00_rate=0.47
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.3,
            avg_goals_conceded=1.4,
            avg_ht_goals_scored=0.52,
            avg_ht_goals_conceded=0.55,
            variance_goals=1.15,
            btts_rate=0.50,
            ht_00_rate=0.50
        ),
        expected_anomaly_detected=False,
        expected_anomaly_score_min=0.0,
        expected_anomaly_score_max=40.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="BTTS rate ~51-52% = odds 2.00 appropriés. Ligne équilibrée."
    ),
    
    # =========================================================================
    # EDGE CASES
    # =========================================================================
    
    TestCase(
        id="EDGE_01",
        name="Extreme Under 6.5 - Borderline",
        competition="England National League North",
        home_team="Farsley Celtic",
        away_team="Spennymoor Town",
        market_type="ft_under_65",
        line=6.5,
        bookmaker_odds=1.40,  # 71% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.9,
            avg_goals_conceded=0.8,
            avg_ht_goals_scored=0.35,
            avg_ht_goals_conceded=0.3,
            variance_goals=0.55,
            btts_rate=0.40,
            ht_00_rate=0.60
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.8,
            avg_goals_conceded=0.9,
            avg_ht_goals_scored=0.3,
            avg_ht_goals_conceded=0.35,
            variance_goals=0.58,
            btts_rate=0.38,
            ht_00_rate=0.62
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=58.0,
        expected_anomaly_score_max=72.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="Total attendu ~1.7 goals, ligne 6.5 très éloignée. Bookmaker à 71% vs réalité ~90%+. Anomalie modérée."
    ),
    
    TestCase(
        id="EDGE_02",
        name="HT Under 1.5 - Limite haute",
        competition="England U21 Premier League",
        home_team="Liverpool U21",
        away_team="Manchester United U21",
        market_type="ht_under_15",
        line=1.5,
        bookmaker_odds=1.80,  # 56% implied
        home_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.4,
            avg_goals_conceded=2.0,
            avg_ht_goals_scored=1.1,
            avg_ht_goals_conceded=0.9,
            variance_goals=2.8,
            btts_rate=0.72,
            ht_00_rate=0.28
        ),
        away_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.3,
            avg_goals_conceded=1.8,
            avg_ht_goals_scored=1.0,
            avg_ht_goals_conceded=0.8,
            variance_goals=2.5,
            btts_rate=0.70,
            ht_00_rate=0.30
        ),
        expected_anomaly_detected=False,
        expected_anomaly_score_min=35.0,
        expected_anomaly_score_max=50.0,
        expected_confidence=ConfidenceCategory.LOW,
        expected_reason="HT total attendu ~2.0 goals. Ligne 1.5 cohérente avec variance élevée U21. Pas d'anomalie claire."
    ),
    
    TestCase(
        id="EDGE_03",
        name="FT Under 3.5 - Variance modérée",
        competition="England Women's Championship",
        home_team="Bristol City Women",
        away_team="London City Lionesses",
        market_type="ft_under_35",
        line=3.5,
        bookmaker_odds=1.70,  # 59% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.5,
            avg_goals_conceded=1.3,
            avg_ht_goals_scored=0.6,
            avg_ht_goals_conceded=0.5,
            variance_goals=1.1,
            btts_rate=0.60,
            ht_00_rate=0.40
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.4,
            avg_goals_conceded=1.2,
            avg_ht_goals_scored=0.55,
            avg_ht_goals_conceded=0.48,
            variance_goals=1.05,
            btts_rate=0.58,
            ht_00_rate=0.42
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=52.0,
        expected_anomaly_score_max=65.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="Total attendu ~2.7 goals, bien sous 3.5. Bookmaker à 59% semble sous-estimer. Anomalie modérée."
    ),
    
    # =========================================================================
    # ADDITIONAL REALISTIC CASES
    # =========================================================================
    
    TestCase(
        id="REAL_01",
        name="FT Under 1.5 - Très défensif",
        competition="England National League North",
        home_team="Blyth Spartans",
        away_team="Kidderminster Harriers",
        market_type="ft_under_15",
        line=1.5,
        bookmaker_odds=2.80,  # 36% implied
        home_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=0.9,
            avg_goals_conceded=1.0,
            avg_ht_goals_scored=0.35,
            avg_ht_goals_conceded=0.4,
            variance_goals=0.6,
            btts_rate=0.40,
            ht_00_rate=0.60
        ),
        away_historical=MatchHistorical(
            matches_played=15,
            avg_goals_scored=1.0,
            avg_goals_conceded=0.9,
            avg_ht_goals_scored=0.4,
            avg_ht_goals_conceded=0.35,
            variance_goals=0.58,
            btts_rate=0.42,
            ht_00_rate=0.58
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=68.0,
        expected_anomaly_score_max=80.0,
        expected_confidence=ConfidenceCategory.HIGH,
        expected_reason="Total attendu ~1.9 goals proche de 1.5. Bookmaker à 36% sous-estime fortement (devrait être ~55-60%). Variance faible confirme."
    ),
    
    TestCase(
        id="REAL_02",
        name="HT Over 0.5 - Équipes offensives HT",
        competition="England U21 Premier League",
        home_team="Arsenal U21",
        away_team="Chelsea U21",
        market_type="ht_over_05",
        line=0.5,
        bookmaker_odds=1.80,  # 56% implied
        home_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.1,
            avg_goals_conceded=1.9,
            avg_ht_goals_scored=0.8,
            avg_ht_goals_conceded=0.75,
            variance_goals=2.6,
            btts_rate=0.65,
            ht_00_rate=0.35
        ),
        away_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.3,
            avg_goals_conceded=1.6,
            avg_ht_goals_scored=0.9,
            avg_ht_goals_conceded=0.7,
            variance_goals=2.3,
            btts_rate=0.68,
            ht_00_rate=0.32
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=50.0,
        expected_anomaly_score_max=63.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="HT 0-0 rate ~33% suggère Over 0.5 à ~67%. Bookmaker à 56% sous-estime. Variance élevée limite confiance."
    ),
    
    TestCase(
        id="REAL_03",
        name="FT Over 3.5 - Équipes offensives",
        competition="England U21 Premier League",
        home_team="Manchester United U21",
        away_team="Manchester City U21",
        market_type="ft_over_35",
        line=3.5,
        bookmaker_odds=2.10,  # 48% implied
        home_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.5,
            avg_goals_conceded=1.8,
            avg_ht_goals_scored=1.0,
            avg_ht_goals_conceded=0.8,
            variance_goals=2.5,
            btts_rate=0.70,
            ht_00_rate=0.30
        ),
        away_historical=MatchHistorical(
            matches_played=12,
            avg_goals_scored=2.4,
            avg_goals_conceded=2.0,
            avg_ht_goals_scored=1.1,
            avg_ht_goals_conceded=0.9,
            variance_goals=2.8,
            btts_rate=0.72,
            ht_00_rate=0.28
        ),
        expected_anomaly_detected=True,
        expected_anomaly_score_min=55.0,
        expected_anomaly_score_max=68.0,
        expected_confidence=ConfidenceCategory.MEDIUM,
        expected_reason="Total attendu ~4.3 goals suggère Over 3.5. Bookmaker à 48% sous-estime. Variance très élevée = prudence."
    ),
]


# =============================================================================
# TEST EXECUTION
# =============================================================================

class TestFunctionalValidation:
    """Functional validation test suite"""
    
    def _create_team_stats(self, historical: MatchHistorical, is_home: bool) -> TeamStats:
        """Create TeamStats from historical data"""
        
        # Calculate additional metrics
        avg_total = historical.avg_goals_scored + historical.avg_goals_conceded
        over_25_pct = 0.65 if avg_total > 2.5 else 0.35
        under_25_pct = 1.0 - over_25_pct
        
        return TeamStats(
            team_id=1 if is_home else 2,
            matches_analyzed=historical.matches_played,
            
            # Full time
            avg_goals_scored=historical.avg_goals_scored,
            avg_goals_conceded=historical.avg_goals_conceded,
            avg_total_goals=avg_total,
            variance_goals_scored=historical.variance_goals,
            variance_goals_conceded=historical.variance_goals * 0.9,
            
            # First half
            avg_goals_scored_ht=historical.avg_ht_goals_scored,
            avg_goals_conceded_ht=historical.avg_ht_goals_conceded,
            avg_total_goals_ht=historical.avg_ht_goals_scored + historical.avg_ht_goals_conceded,
            ht_00_percentage=historical.ht_00_rate,
            
            # Markets
            btts_percentage=historical.btts_rate,
            over_25_percentage=over_25_pct,
            under_25_percentage=under_25_pct,
            
            # Stability
            stability_score=max(0.3, 1.0 - (historical.variance_goals / 3.0)),
            form_last_5=[1, 1, 0, 1, 0],  # Dummy
            
            # Data quality
            data_quality_score=min(1.0, historical.matches_played / 15.0),
            sample_size=historical.matches_played
        )
    
    @pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc.id for tc in TEST_CASES])
    def test_anomaly_detection(self, test_case: TestCase):
        """Test anomaly detection for each case"""
        
        print(f"\n{'='*80}")
        print(f"TEST: {test_case.id} - {test_case.name}")
        print(f"{'='*80}")
        
        # Create team stats
        home_stats = self._create_team_stats(test_case.home_historical, is_home=True)
        away_stats = self._create_team_stats(test_case.away_historical, is_home=False)
        
        # Run anomaly detection
        engine = AnomalyEngine()
        result = engine.analyze_market(
            match_id=1,
            market_type=test_case.market_type,
            bookmaker_odds=test_case.bookmaker_odds,
            home_stats=home_stats,
            away_stats=away_stats,
            line=test_case.line
        )
        
        # Print results
        print(f"\n📊 Results:")
        print(f"   Anomaly Score: {result.anomaly_score:.1f}")
        print(f"   Confidence: {result.confidence_category.value} ({result.confidence_score:.0%})")
        print(f"   Discrepancy: {result.discrepancy_score:.1f}")
        print(f"   Variance Safety: {result.variance_safety_score:.1f}")
        print(f"   Stability: {result.stability_score:.1f}")
        
        print(f"\n✅ Expected:")
        print(f"   Anomaly Detected: {test_case.expected_anomaly_detected}")
        print(f"   Score Range: {test_case.expected_anomaly_score_min:.1f}-{test_case.expected_anomaly_score_max:.1f}")
        print(f"   Confidence: {test_case.expected_confidence.value}")
        print(f"   Reason: {test_case.expected_reason}")
        
        # Assertions
        if test_case.expected_anomaly_detected:
            assert result.anomaly_score >= test_case.expected_anomaly_score_min, \
                f"Anomaly score {result.anomaly_score:.1f} below minimum {test_case.expected_anomaly_score_min:.1f}"
            assert result.anomaly_score <= test_case.expected_anomaly_score_max, \
                f"Anomaly score {result.anomaly_score:.1f} above maximum {test_case.expected_anomaly_score_max:.1f}"
        
        assert result.confidence_category == test_case.expected_confidence, \
            f"Expected {test_case.expected_confidence.value}, got {result.confidence_category.value}"
        
        print(f"\n✅ TEST PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
