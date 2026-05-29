"""
Exemples d'utilisation du système First Half spécialisé
"""

from app.core.database import SessionLocal
from app.services.stats_engine.first_half_stats_calculator import (
    FirstHalfStatsCalculator,
    FirstHalfPace
)
from app.services.anomaly_engine.first_half_anomaly_detector import (
    FirstHalfAnomalyDetector,
    HTMarketType
)
import json


def example_1_calculate_ht_stats():
    """
    Exemple 1 : Calculer statistiques First Half complètes
    """
    
    print("=" * 80)
    print("EXEMPLE 1 : STATISTIQUES FIRST HALF COMPLÈTES")
    print("=" * 80)
    
    db = SessionLocal()
    calculator = FirstHalfStatsCalculator(db)
    
    team_id = 1
    
    # Calculer stats HT (home)
    stats = calculator.calculate_first_half_stats(
        team_id=team_id,
        last_n=15,
        home_away_split="home"
    )
    
    if stats:
        print(f"\n{'='*80}")
        print(f"STATISTIQUES FIRST HALF - ÉQUIPE #{team_id} (DOMICILE)")
        print(f"{'='*80}\n")
        
        print(f"📊 MOYENNES:")
        print(f"  • Buts HT:           {stats.avg_goals_ht:.2f}")
        print(f"  • Buts marqués HT:   {stats.avg_goals_scored_ht:.2f}")
        print(f"  • Buts encaissés HT: {stats.avg_goals_conceded_ht:.2f}\n")
        
        print(f"📈 FRÉQUENCES UNDER/OVER:")
        print(f"  • Under 0.5 HT:  {stats.under_05_ht_pct:.1f}%")
        print(f"  • Under 1.5 HT:  {stats.under_15_ht_pct:.1f}%")
        print(f"  • Over 0.5 HT:   {stats.over_05_ht_pct:.1f}%")
        print(f"  • Over 1.5 HT:   {stats.over_15_ht_pct:.1f}%\n")
        
        print(f"🎯 SCORES EXACTS HT:")
        print(f"  • 0-0 HT:  {stats.zero_zero_ht_pct:.1f}%")
        print(f"  • 1-0 HT:  {stats.one_zero_ht_pct:.1f}%")
        print(f"  • 1-1 HT:  {stats.one_one_ht_pct:.1f}%")
        print(f"  • 2-0 HT:  {stats.two_zero_ht_pct:.1f}%\n")
        
        print(f"⚡ RYTHME OFFENSIF:")
        print(f"  • Pace:       {stats.offensive_pace.value}")
        print(f"  • Pace Score: {stats.pace_score:.2f}")
        print(f"  • Slow Start: {'✅ OUI' if stats.is_slow_starter else '❌ NON'}")
        print(f"  • Fast Start: {'✅ OUI' if stats.is_fast_starter else '❌ NON'}\n")
        
        print(f"📊 VARIANCE & STABILITÉ:")
        print(f"  • Variance HT:   {stats.variance_ht:.2f}")
        print(f"  • Std Dev HT:    {stats.std_dev_ht:.2f}")
        print(f"  • CV HT:         {stats.cv_ht:.2f}")
        print(f"  • Stabilité HT:  {stats.stability_ht:.2f}\n")
        
        print(f"📏 RATIOS:")
        print(f"  • HT/FT Ratio: {stats.ht_ft_ratio:.2f}\n")
        
        print(f"ℹ️ MÉTADONNÉES:")
        print(f"  • Matchs analysés: {stats.matches_analyzed}")
        print(f"  • Confiance:       {stats.confidence_level}")
    else:
        print("\n❌ Données insuffisantes")
    
    db.close()
    return stats


def example_2_detect_zero_zero_anomaly():
    """
    Exemple 2 : Détecter anomalie sur marché 0-0 HT
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 2 : DÉTECTION ANOMALIE 0-0 HT")
    print("=" * 80)
    
    db = SessionLocal()
    detector = FirstHalfAnomalyDetector(db)
    
    # Deux équipes slow starters
    home_team_id = 1
    away_team_id = 2
    
    # Bookmaker sous-estime 0-0 HT
    bookmaker_odds = 2.50  # 40% implied
    
    anomaly = detector.detect_ht_anomaly(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        market_type=HTMarketType.HT_ZERO_ZERO,
        bookmaker_odds=bookmaker_odds
    )
    
    print(f"\n{'='*80}")
    print(f"RÉSULTATS ANALYSE 0-0 HT")
    print(f"{'='*80}\n")
    
    print(f"🎯 SCORE TOTAL: {anomaly.total_score:.1f}/100")
    print(f"📊 NIVEAU: {anomaly.level}\n")
    
    print(f"📈 SOUS-SCORES:")
    print(f"  • Probability Gap:     {anomaly.probability_gap_score:.1f}/35")
    print(f"  • Historical Pattern:  {anomaly.historical_pattern_score:.1f}/30")
    print(f"  • Pace Consistency:    {anomaly.pace_consistency_score:.1f}/20")
    print(f"  • Stability:           {anomaly.stability_score:.1f}/15\n")
    
    print(f"📊 PROBABILITÉS:")
    print(f"  • Bookmaker: {anomaly.bookmaker_prob:.2%}")
    print(f"  • Modèle:    {anomaly.model_prob:.2%}")
    print(f"  • Gap:       {anomaly.probability_gap:.2%}\n")
    
    print(f"🔔 SIGNAUX ({len(anomaly.signals)}):")
    for signal in anomaly.signals:
        print(f"  • [{signal.strength}] {signal.description}")
    
    print(f"\n{'='*80}")
    print(f"EXPLICATION")
    print(f"{'='*80}\n")
    print(anomaly.explanation)
    
    print(f"\n{'='*80}")
    print(f"RECOMMANDATION")
    print(f"{'='*80}\n")
    print(anomaly.recommendation)
    
    # Export JSON
    print(f"\n{'='*80}")
    print(f"EXPORT JSON")
    print(f"{'='*80}\n")
    print(anomaly.to_json())
    
    db.close()
    return anomaly


def example_3_compare_ht_markets():
    """
    Exemple 3 : Comparer plusieurs marchés HT pour le même match
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 3 : COMPARAISON MARCHÉS HT")
    print("=" * 80)
    
    db = SessionLocal()
    detector = FirstHalfAnomalyDetector(db)
    
    home_team_id = 3
    away_team_id = 4
    
    # Tester différents marchés HT
    markets_to_test = [
        (HTMarketType.HT_ZERO_ZERO, 2.50),
        (HTMarketType.HT_UNDER_05, 2.00),
        (HTMarketType.HT_UNDER_15, 1.60),
        (HTMarketType.HT_OVER_05, 1.80),
        (HTMarketType.HT_OVER_15, 3.50),
        (HTMarketType.HT_BTTS, 4.00)
    ]
    
    results = []
    
    for market_type, odds in markets_to_test:
        anomaly = detector.detect_ht_anomaly(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            market_type=market_type,
            bookmaker_odds=odds
        )
        results.append((market_type, anomaly))
    
    # Trier par score
    results.sort(key=lambda x: x[1].total_score, reverse=True)
    
    print(f"\n{'='*80}")
    print(f"RÉSULTATS TRIÉS PAR SCORE D'ANOMALIE")
    print(f"{'='*80}\n")
    
    print(f"{'Marché':<20} {'Odds':<8} {'Score':<10} {'Niveau':<12} {'Prob Gap':<12} {'Signaux'}")
    print(f"{'-'*80}")
    
    for market_type, anomaly in results:
        signals_count = len(anomaly.signals)
        odds = 1 / anomaly.bookmaker_prob if anomaly.bookmaker_prob > 0 else 0
        print(f"{market_type.value:<20} {odds:<8.2f} {anomaly.total_score:<10.1f} "
              f"{anomaly.level:<12} {anomaly.probability_gap:<12.2%} {signals_count}")
    
    # Meilleure opportunité
    best_market, best_anomaly = results[0]
    
    print(f"\n{'='*80}")
    print(f"MEILLEURE OPPORTUNITÉ HT")
    print(f"{'='*80}\n")
    print(f"Marché: {best_market.value}")
    print(f"Score: {best_anomaly.total_score:.1f}/100")
    print(f"Niveau: {best_anomaly.level}")
    print(f"Gap: {best_anomaly.probability_gap:.2%}")
    print(f"\nSignaux:")
    for signal in best_anomaly.signals:
        print(f"  • [{signal.strength}] {signal.description}")
    
    db.close()
    return results


def example_4_match_ht_expectation():
    """
    Exemple 4 : Calculer expectations HT pour un match
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 4 : EXPECTATIONS FIRST HALF")
    print("=" * 80)
    
    db = SessionLocal()
    calculator = FirstHalfStatsCalculator(db)
    
    home_team_id = 5
    away_team_id = 6
    
    ht_data = calculator.calculate_match_ht_expectation(
        home_team_id=home_team_id,
        away_team_id=away_team_id
    )
    
    if ht_data:
        print(f"\n{'='*80}")
        print(f"EXPECTATIONS FIRST HALF")
        print(f"{'='*80}\n")
        
        print(f"⚽ EXPECTED GOALS HT:")
        print(f"  • Total:  {ht_data['expected_goals_ht']:.2f}")
        print(f"  • Home:   {ht_data['expected_home_ht']:.2f}")
        print(f"  • Away:   {ht_data['expected_away_ht']:.2f}\n")
        
        print(f"📊 PROBABILITÉS:")
        probs = ht_data['probabilities']
        print(f"  • Under 0.5 HT: {probs['under_05']:.2%}")
        print(f"  • Under 1.5 HT: {probs['under_15']:.2%}")
        print(f"  • Over 0.5 HT:  {probs['over_05']:.2%}")
        print(f"  • Over 1.5 HT:  {probs['over_15']:.2%}\n")
        
        print(f"🎯 AUTRES PROBABILITÉS:")
        print(f"  • BTTS HT:   {ht_data['btts_ht_probability']:.2%}")
        print(f"  • 0-0 HT:    {ht_data['zero_zero_probability']:.2%}\n")
        
        print(f"⚡ RYTHME COMBINÉ:")
        print(f"  • Pace Score: {ht_data['combined_pace_score']:.2f}")
        
        home_stats = ht_data['home_stats']
        away_stats = ht_data['away_stats']
        
        print(f"  • Home Pace:  {home_stats.offensive_pace.value} ({home_stats.pace_score:.2f})")
        print(f"  • Away Pace:  {away_stats.offensive_pace.value} ({away_stats.pace_score:.2f})\n")
        
        print(f"📊 VARIANCE:")
        print(f"  • Variance HT: {ht_data['variance_ht']:.2f}")
    else:
        print("\n❌ Données insuffisantes")
    
    db.close()
    return ht_data


def example_5_slow_vs_fast_starters():
    """
    Exemple 5 : Analyser match Slow Starters vs Fast Starters
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 5 : SLOW STARTERS vs FAST STARTERS")
    print("=" * 80)
    
    db = SessionLocal()
    calculator = FirstHalfStatsCalculator(db)
    detector = FirstHalfAnomalyDetector(db)
    
    # Team A: Slow starter
    # Team B: Fast starter
    home_team_id = 7
    away_team_id = 8
    
    home_stats = calculator.calculate_first_half_stats(
        team_id=home_team_id,
        home_away_split="home"
    )
    
    away_stats = calculator.calculate_first_half_stats(
        team_id=away_team_id,
        home_away_split="away"
    )
    
    if home_stats and away_stats:
        print(f"\n{'='*80}")
        print(f"ANALYSE RYTHMES")
        print(f"{'='*80}\n")
        
        print(f"🏠 HOME (Team #{home_team_id}):")
        print(f"  • Pace:         {home_stats.offensive_pace.value}")
        print(f"  • Pace Score:   {home_stats.pace_score:.2f}")
        print(f"  • Slow Starter: {'✅' if home_stats.is_slow_starter else '❌'}")
        print(f"  • Fast Starter: {'✅' if home_stats.is_fast_starter else '❌'}")
        print(f"  • 0-0 HT:       {home_stats.zero_zero_ht_pct:.1f}%")
        print(f"  • Over 0.5 HT:  {home_stats.over_05_ht_pct:.1f}%\n")
        
        print(f"✈️ AWAY (Team #{away_team_id}):")
        print(f"  • Pace:         {away_stats.offensive_pace.value}")
        print(f"  • Pace Score:   {away_stats.pace_score:.2f}")
        print(f"  • Slow Starter: {'✅' if away_stats.is_slow_starter else '❌'}")
        print(f"  • Fast Starter: {'✅' if away_stats.is_fast_starter else '❌'}")
        print(f"  • 0-0 HT:       {away_stats.zero_zero_ht_pct:.1f}%")
        print(f"  • Over 0.5 HT:  {away_stats.over_05_ht_pct:.1f}%\n")
        
        # Recommandation marché
        if home_stats.is_slow_starter and away_stats.is_slow_starter:
            recommended_market = HTMarketType.HT_ZERO_ZERO
            print(f"💡 RECOMMANDATION: {recommended_market.value}")
            print(f"   Raison: Les deux équipes sont SLOW STARTERS\n")
        elif home_stats.is_fast_starter or away_stats.is_fast_starter:
            recommended_market = HTMarketType.HT_OVER_05
            print(f"💡 RECOMMANDATION: {recommended_market.value}")
            print(f"   Raison: Au moins une équipe est FAST STARTER\n")
        else:
            recommended_market = HTMarketType.HT_UNDER_15
            print(f"💡 RECOMMANDATION: {recommended_market.value}")
            print(f"   Raison: Rythme modéré\n")
        
        # Tester le marché recommandé
        anomaly = detector.detect_ht_anomaly(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            market_type=recommended_market,
            bookmaker_odds=2.00
        )
        
        print(f"{'='*80}")
        print(f"TEST MARCHÉ RECOMMANDÉ")
        print(f"{'='*80}\n")
        print(f"Score: {anomaly.total_score:.1f}/100")
        print(f"Niveau: {anomaly.level}")
        print(f"Gap: {anomaly.probability_gap:.2%}")
    
    db.close()


def example_6_export_all_ht_indicators():
    """
    Exemple 6 : Exporter tous les indicateurs HT en JSON
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 6 : EXPORT JSON COMPLET")
    print("=" * 80)
    
    db = SessionLocal()
    calculator = FirstHalfStatsCalculator(db)
    
    team_id = 1
    
    stats = calculator.calculate_first_half_stats(
        team_id=team_id,
        home_away_split="all"
    )
    
    if stats:
        # Créer dictionnaire complet
        ht_indicators = {
            "team_id": team_id,
            "averages": {
                "avg_goals_ht": stats.avg_goals_ht,
                "avg_goals_scored_ht": stats.avg_goals_scored_ht,
                "avg_goals_conceded_ht": stats.avg_goals_conceded_ht
            },
            "frequencies": {
                "under_05_ht_pct": stats.under_05_ht_pct,
                "under_15_ht_pct": stats.under_15_ht_pct,
                "under_25_ht_pct": stats.under_25_ht_pct,
                "over_05_ht_pct": stats.over_05_ht_pct,
                "over_15_ht_pct": stats.over_15_ht_pct,
                "over_25_ht_pct": stats.over_25_ht_pct
            },
            "exact_scores": {
                "zero_zero_ht_pct": stats.zero_zero_ht_pct,
                "one_zero_ht_pct": stats.one_zero_ht_pct,
                "one_one_ht_pct": stats.one_one_ht_pct,
                "two_zero_ht_pct": stats.two_zero_ht_pct
            },
            "btts": {
                "btts_ht_pct": stats.btts_ht_pct,
                "no_btts_ht_pct": stats.no_btts_ht_pct
            },
            "pace": {
                "offensive_pace": stats.offensive_pace.value,
                "pace_score": stats.pace_score,
                "is_slow_starter": stats.is_slow_starter,
                "is_fast_starter": stats.is_fast_starter
            },
            "variance": {
                "variance_ht": stats.variance_ht,
                "std_dev_ht": stats.std_dev_ht,
                "cv_ht": stats.cv_ht,
                "stability_ht": stats.stability_ht
            },
            "ratios": {
                "ht_ft_ratio": stats.ht_ft_ratio
            },
            "metadata": {
                "matches_analyzed": stats.matches_analyzed,
                "confidence_level": stats.confidence_level
            }
        }
        
        json_output = json.dumps(ht_indicators, indent=2)
        
        print(f"\n{'='*80}")
        print(f"JSON EXPORT - TOUS LES INDICATEURS HT")
        print(f"{'='*80}\n")
        print(json_output)
    
    db.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("EXEMPLES D'UTILISATION - SYSTÈME FIRST HALF SPÉCIALISÉ")
    print("=" * 80)
    
    # Exemple 1: Stats HT complètes
    example_1_calculate_ht_stats()
    
    # Exemple 2: Anomalie 0-0 HT
    example_2_detect_zero_zero_anomaly()
    
    # Exemple 3: Comparer marchés HT
    example_3_compare_ht_markets()
    
    # Exemple 4: Expectations HT
    example_4_match_ht_expectation()
    
    # Exemple 5: Slow vs Fast starters
    example_5_slow_vs_fast_starters()
    
    # Exemple 6: Export JSON
    example_6_export_all_ht_indicators()
    
    print("\n" + "=" * 80)
    print("EXEMPLES TERMINÉS")
    print("=" * 80)
