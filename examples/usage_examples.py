"""
Exemples d'utilisation du système de statistiques avancées
"""

from app.core.database import SessionLocal
from app.services.stats_engine import AdvancedStatsCalculator, LeagueStatsCalculator
from app.services.anomaly_engine import AnomalyDetector
from app.services.confidence_engine import ConfidenceScorer


def example_1_calculate_team_stats():
    """
    Exemple 1 : Calculer les statistiques complètes d'une équipe
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    team_id = 1
    
    stats = calc.calculate_comprehensive_stats(
        team_id=team_id,
        last_n=10,
        home_away_split="home"
    )
    
    print("=== STATISTIQUES ÉQUIPE ===")
    print(f"\nMoyennes de base:")
    print(f"  Buts FT: {stats['basic']['avg_goals_ft']:.2f}")
    print(f"  Buts HT: {stats['basic']['avg_goals_ht']:.2f}")
    print(f"  Buts marqués: {stats['basic']['avg_goals_scored']:.2f}")
    print(f"  Buts encaissés: {stats['basic']['avg_goals_conceded']:.2f}")
    
    print(f"\nVariance & Stabilité:")
    print(f"  Variance: {stats['variance']['variance_total_goals']:.2f}")
    print(f"  CV: {stats['variance']['cv_total']:.2f}")
    print(f"  Stabilité: {stats['variance']['stability_score']:.2f}")
    
    print(f"\nFréquences:")
    print(f"  Over 2.5: {stats['frequencies']['over_25_pct']:.1f}%")
    print(f"  Under 2.5: {stats['frequencies']['under_25_pct']:.1f}%")
    print(f"  BTTS: {stats['btts']['btts_pct']:.1f}%")
    
    print(f"\nConfiance: {stats['meta']['confidence_level']}")
    
    db.close()


def example_2_calculate_expected_goals():
    """
    Exemple 2 : Calculer les expected goals pour un match
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    home_team_id = 1
    away_team_id = 2
    
    xg_data = calc.calculate_expected_goals(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        league_avg_goals=2.5,
        home_advantage_factor=1.3
    )
    
    print("=== EXPECTED GOALS ===")
    print(f"xG Home: {xg_data['xg_home']:.2f}")
    print(f"xG Away: {xg_data['xg_away']:.2f}")
    print(f"xG Total: {xg_data['xg_total']:.2f}")
    
    print(f"\nProbabilités (Poisson/NBinom):")
    probs = xg_data['probabilities']
    print(f"  Over 2.5: {probs['over_25']:.2%}")
    print(f"  Under 2.5: {probs['under_25']:.2%}")
    print(f"  Over 3.5: {probs['over_35']:.2%}")
    
    print(f"\nOverdispersion: {xg_data['is_overdispersed']}")
    
    db.close()


def example_3_bayesian_smoothing():
    """
    Exemple 3 : Appliquer Bayesian smoothing pour faible volume
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    team_stat = 3.2
    league_stat = 2.5
    n_matches = 4
    
    smoothed = calc.bayesian_smooth(
        team_stat=team_stat,
        league_stat=league_stat,
        n_matches=n_matches,
        k=5
    )
    
    print("=== BAYESIAN SMOOTHING ===")
    print(f"Stat équipe (n={n_matches}): {team_stat:.2f}")
    print(f"Stat ligue: {league_stat:.2f}")
    print(f"Stat lissée: {smoothed:.2f}")
    print(f"\nAjustement: {((smoothed - team_stat) / team_stat * 100):.1f}%")
    
    db.close()


def example_4_detect_anomaly():
    """
    Exemple 4 : Détecter une anomalie statistique
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    team_stat = 3.8
    league_mean = 2.5
    league_std = 0.6
    
    is_anomaly, z_score = calc.detect_statistical_anomaly(
        team_stat=team_stat,
        league_mean=league_mean,
        league_std=league_std,
        threshold=2.0
    )
    
    print("=== DÉTECTION ANOMALIE ===")
    print(f"Stat équipe: {team_stat:.2f}")
    print(f"Moyenne ligue: {league_mean:.2f}")
    print(f"Écart-type ligue: {league_std:.2f}")
    print(f"Z-Score: {z_score:.2f}")
    print(f"Anomalie détectée: {is_anomaly}")
    
    if is_anomaly:
        if z_score > 0:
            print("→ Équipe SIGNIFICATIVEMENT AU-DESSUS de la moyenne")
        else:
            print("→ Équipe SIGNIFICATIVEMENT EN-DESSOUS de la moyenne")
    
    db.close()


def example_5_league_statistics():
    """
    Exemple 5 : Calculer les statistiques de ligue
    """
    db = SessionLocal()
    league_calc = LeagueStatsCalculator(db)
    
    league = "england-national-league"
    
    league_stats = league_calc.calculate_league_averages(
        league=league,
        days_back=90
    )
    
    if league_stats:
        print("=== STATISTIQUES LIGUE ===")
        print(f"Ligue: {league_stats['league']}")
        print(f"Matchs analysés: {league_stats['matches_analyzed']}")
        
        print(f"\nMoyennes:")
        print(f"  Buts FT: {league_stats['avg_goals_ft']:.2f}")
        print(f"  Buts HT: {league_stats['avg_goals_ht']:.2f}")
        print(f"  Buts domicile: {league_stats['avg_goals_home']:.2f}")
        print(f"  Buts extérieur: {league_stats['avg_goals_away']:.2f}")
        
        print(f"\nFréquences:")
        print(f"  BTTS: {league_stats['btts_pct']:.1f}%")
        print(f"  Over 2.5: {league_stats['over_25_pct']:.1f}%")
        print(f"  Under 2.5: {league_stats['under_25_pct']:.1f}%")
        
        print(f"\nHome Advantage Factor: {league_stats['home_advantage_factor']:.2f}")
    
    db.close()


def example_6_full_match_analysis():
    """
    Exemple 6 : Analyse complète d'un match
    """
    db = SessionLocal()
    
    match_id = 1
    home_team_id = 1
    away_team_id = 2
    
    stats_calc = AdvancedStatsCalculator(db)
    anomaly_detector = AnomalyDetector(db)
    confidence_scorer = ConfidenceScorer(db)
    
    print("=== ANALYSE COMPLÈTE MATCH ===\n")
    
    print("1. Calcul statistiques équipes...")
    home_stats = stats_calc.calculate_comprehensive_stats(home_team_id, home_away_split="home")
    away_stats = stats_calc.calculate_comprehensive_stats(away_team_id, home_away_split="away")
    
    print("2. Calcul expected goals...")
    xg_data = stats_calc.calculate_expected_goals(home_team_id, away_team_id)
    
    print("3. Détection anomalies...")
    anomalies = anomaly_detector.detect_match_anomalies(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id
    )
    
    print("4. Calcul confiance...")
    for anomaly in anomalies:
        confidence_scorer.calculate_confidence(
            anomaly=anomaly,
            home_team_id=home_team_id,
            away_team_id=away_team_id
        )
    
    print(f"\n=== RÉSULTATS ===")
    print(f"xG Total: {xg_data['xg_total']:.2f}")
    print(f"Anomalies détectées: {len(anomalies)}")
    
    for i, anomaly in enumerate(anomalies, 1):
        print(f"\nAnomalie {i}:")
        print(f"  Marché: {anomaly.market_type}")
        print(f"  Score: {anomaly.anomaly_score:.2f}")
        print(f"  Confiance: {anomaly.confidence_level.value} ({anomaly.confidence_score:.2%})")
        print(f"  Gap probabilité: {anomaly.probability_gap:.2%}")
    
    db.close()


def example_7_weighted_moving_average():
    """
    Exemple 7 : Calculer weighted moving average
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    goals_last_10 = [2, 3, 1, 2, 4, 1, 2, 3, 2, 1]
    
    wma = calc._calculate_weighted_moving_average(goals_last_10)
    simple_avg = sum(goals_last_10) / len(goals_last_10)
    
    print("=== WEIGHTED MOVING AVERAGE ===")
    print(f"Buts derniers 10 matchs: {goals_last_10}")
    print(f"Moyenne simple: {simple_avg:.2f}")
    print(f"WMA (récent = plus de poids): {wma:.2f}")
    print(f"Différence: {(wma - simple_avg):.2f}")
    
    db.close()


def example_8_compare_distributions():
    """
    Exemple 8 : Comparer Poisson vs Negative Binomial
    """
    db = SessionLocal()
    calc = AdvancedStatsCalculator(db)
    
    mu = 2.8
    variance_low = 2.5
    variance_high = 4.5
    
    print("=== COMPARAISON DISTRIBUTIONS ===\n")
    
    print(f"Cas 1 : Variance faible (variance ≤ moyenne)")
    print(f"  Moyenne: {mu:.2f}")
    print(f"  Variance: {variance_low:.2f}")
    poisson_probs = calc._calculate_poisson_probabilities(mu)
    print(f"  Over 2.5 (Poisson): {poisson_probs['over_25']:.2%}")
    
    print(f"\nCas 2 : Variance élevée (variance > moyenne)")
    print(f"  Moyenne: {mu:.2f}")
    print(f"  Variance: {variance_high:.2f}")
    nbinom_probs = calc._calculate_negative_binomial_probabilities(mu, variance_high)
    print(f"  Over 2.5 (Negative Binomial): {nbinom_probs['over_25']:.2%}")
    
    print(f"\nDifférence: {(nbinom_probs['over_25'] - poisson_probs['over_25']):.2%}")
    print("→ Negative Binomial donne probabilités plus élevées (variance haute)")
    
    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("EXEMPLES D'UTILISATION - SYSTÈME STATISTIQUE AVANCÉ")
    print("=" * 60)
    
    print("\n" + "=" * 60)
    example_1_calculate_team_stats()
    
    print("\n" + "=" * 60)
    example_2_calculate_expected_goals()
    
    print("\n" + "=" * 60)
    example_3_bayesian_smoothing()
    
    print("\n" + "=" * 60)
    example_4_detect_anomaly()
    
    print("\n" + "=" * 60)
    example_5_league_statistics()
    
    print("\n" + "=" * 60)
    example_7_weighted_moving_average()
    
    print("\n" + "=" * 60)
    example_8_compare_distributions()
    
    print("\n" + "=" * 60)
    print("EXEMPLES TERMINÉS")
    print("=" * 60)
