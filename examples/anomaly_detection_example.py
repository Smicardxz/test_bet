"""
Exemple d'utilisation du moteur de détection d'anomalies avancé
"""

from app.core.database import SessionLocal
from app.services.anomaly_engine.advanced_anomaly_detector import (
    AdvancedAnomalyDetector,
    AnomalyLevel
)


def example_1_extreme_line_anomaly():
    """
    Exemple 1 : Détection d'anomalie sur ligne extrême (Under 12.5)
    
    Cas typique : Bookmaker propose une ligne très élevée
    pour un match entre équipes qui marquent peu de buts
    """
    
    print("=" * 80)
    print("EXEMPLE 1 : ANOMALIE LIGNE EXTRÊME (Under 12.5)")
    print("=" * 80)
    
    db = SessionLocal()
    detector = AdvancedAnomalyDetector(db)
    
    # Paramètres du match
    match_id = 1
    home_team_id = 1  # Équipe qui marque ~2 buts/match
    away_team_id = 2  # Équipe qui marque ~2 buts/match
    
    # Ligne bookmaker
    bookmaker_line = 12.5
    bookmaker_over_odds = 2.00  # 50% implied probability
    bookmaker_under_odds = 2.00  # 50% implied probability
    
    # Détection
    anomaly = detector.detect_line_anomaly(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        market_type="over_under",
        bookmaker_line=bookmaker_line,
        bookmaker_over_odds=bookmaker_over_odds,
        bookmaker_under_odds=bookmaker_under_odds
    )
    
    # Affichage résultats
    print(f"\n{'='*80}")
    print(f"RÉSULTATS DE L'ANALYSE")
    print(f"{'='*80}\n")
    
    print(f"🎯 SCORE TOTAL: {anomaly.total_score:.1f}/100")
    print(f"📊 NIVEAU: {anomaly.level.value}\n")
    
    print(f"📈 SOUS-SCORES:")
    print(f"  • Bookmaker Gap:      {anomaly.bookmaker_gap_score:.1f}/30")
    print(f"  • Variance Safety:    {anomaly.variance_safety_score:.1f}/25")
    print(f"  • Historical Breach:  {anomaly.historical_breach_score:.1f}/25")
    print(f"  • Stability:          {anomaly.stability_score:.1f}/20\n")
    
    print(f"📊 PROBABILITÉS:")
    print(f"  • Bookmaker: {anomaly.bookmaker_prob:.2%}")
    print(f"  • Modèle:    {anomaly.model_prob:.2%}")
    print(f"  • Gap:       {anomaly.probability_gap:.2%}\n")
    
    print(f"📏 LIGNES:")
    print(f"  • Bookmaker: {anomaly.bookmaker_line}")
    print(f"  • Expected:  {anomaly.expected_line}")
    print(f"  • Diff:      {anomaly.line_difference:+.1f}\n")
    
    print(f"🔔 TRIGGERS ({len(anomaly.triggers)}):")
    for trigger in anomaly.triggers:
        print(f"  • {trigger}")
    
    print(f"\n{'='*80}")
    print(f"EXPLICATION DÉTAILLÉE")
    print(f"{'='*80}\n")
    print(anomaly.explanation)
    
    print(f"\n{'='*80}")
    print(f"RAISON DE CONFIANCE")
    print(f"{'='*80}\n")
    print(anomaly.confidence_reason)
    
    db.close()
    
    return anomaly


def example_2_moderate_line_anomaly():
    """
    Exemple 2 : Détection d'anomalie modérée (Under 2.5)
    
    Cas : Ligne proche de l'expected mais avec écart de probabilité
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 2 : ANOMALIE MODÉRÉE (Under 2.5)")
    print("=" * 80)
    
    db = SessionLocal()
    detector = AdvancedAnomalyDetector(db)
    
    match_id = 2
    home_team_id = 3
    away_team_id = 4
    
    bookmaker_line = 2.5
    bookmaker_over_odds = 2.20  # ~45% implied
    bookmaker_under_odds = 1.70  # ~59% implied
    
    anomaly = detector.detect_line_anomaly(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        market_type="over_under",
        bookmaker_line=bookmaker_line,
        bookmaker_over_odds=bookmaker_over_odds,
        bookmaker_under_odds=bookmaker_under_odds
    )
    
    print(f"\n🎯 SCORE TOTAL: {anomaly.total_score:.1f}/100")
    print(f"📊 NIVEAU: {anomaly.level.value}")
    
    if anomaly.level in [AnomalyLevel.HIGH, AnomalyLevel.VERY_HIGH, AnomalyLevel.EXTREME]:
        print("\n✅ ANOMALIE DÉTECTÉE - Opportunité potentielle")
    else:
        print("\n⚠️ Anomalie faible/modérée - Vérifier manuellement")
    
    db.close()
    
    return anomaly


def example_3_no_anomaly():
    """
    Exemple 3 : Pas d'anomalie (ligne cohérente)
    
    Cas : Ligne cohérente avec statistiques
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 3 : PAS D'ANOMALIE (Ligne cohérente)")
    print("=" * 80)
    
    db = SessionLocal()
    detector = AdvancedAnomalyDetector(db)
    
    match_id = 3
    home_team_id = 5
    away_team_id = 6
    
    bookmaker_line = 3.5
    bookmaker_over_odds = 2.10
    bookmaker_under_odds = 1.80
    
    anomaly = detector.detect_line_anomaly(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        market_type="over_under",
        bookmaker_line=bookmaker_line,
        bookmaker_over_odds=bookmaker_over_odds,
        bookmaker_under_odds=bookmaker_under_odds
    )
    
    print(f"\n🎯 SCORE TOTAL: {anomaly.total_score:.1f}/100")
    print(f"📊 NIVEAU: {anomaly.level.value}")
    
    if anomaly.level == AnomalyLevel.LOW:
        print("\n❌ Pas d'anomalie significative - Ligne cohérente")
    
    db.close()
    
    return anomaly


def example_4_compare_multiple_lines():
    """
    Exemple 4 : Comparer plusieurs lignes pour le même match
    
    Cas : Analyser Under 2.5, 3.5, 4.5, 5.5 pour trouver la meilleure anomalie
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 4 : COMPARAISON MULTIPLE LIGNES")
    print("=" * 80)
    
    db = SessionLocal()
    detector = AdvancedAnomalyDetector(db)
    
    match_id = 4
    home_team_id = 7
    away_team_id = 8
    
    lines_to_test = [
        (2.5, 1.90, 1.95),
        (3.5, 2.10, 1.75),
        (4.5, 2.50, 1.55),
        (5.5, 3.20, 1.35),
        (8.5, 8.00, 1.10),
        (12.5, 20.00, 1.01)
    ]
    
    results = []
    
    for line, over_odds, under_odds in lines_to_test:
        anomaly = detector.detect_line_anomaly(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            market_type="over_under",
            bookmaker_line=line,
            bookmaker_over_odds=over_odds,
            bookmaker_under_odds=under_odds
        )
        
        results.append((line, anomaly))
    
    # Trier par score décroissant
    results.sort(key=lambda x: x[1].total_score, reverse=True)
    
    print(f"\n{'='*80}")
    print(f"RÉSULTATS TRIÉS PAR SCORE D'ANOMALIE")
    print(f"{'='*80}\n")
    
    print(f"{'Ligne':<8} {'Score':<10} {'Niveau':<12} {'Prob Gap':<12} {'Triggers'}")
    print(f"{'-'*80}")
    
    for line, anomaly in results:
        triggers_count = len(anomaly.triggers)
        print(f"{line:<8.1f} {anomaly.total_score:<10.1f} {anomaly.level.value:<12} "
              f"{anomaly.probability_gap:<12.2%} {triggers_count}")
    
    # Meilleure anomalie
    best_line, best_anomaly = results[0]
    
    print(f"\n{'='*80}")
    print(f"MEILLEURE ANOMALIE DÉTECTÉE")
    print(f"{'='*80}\n")
    print(f"Ligne: {best_line}")
    print(f"Score: {best_anomaly.total_score:.1f}/100")
    print(f"Niveau: {best_anomaly.level.value}")
    print(f"\nTriggers:")
    for trigger in best_anomaly.triggers:
        print(f"  • {trigger}")
    
    db.close()
    
    return results


def example_5_anomaly_filtering():
    """
    Exemple 5 : Filtrer anomalies par niveau de confiance
    
    Cas : Scanner plusieurs matchs et ne garder que les anomalies HIGH+
    """
    
    print("\n\n" + "=" * 80)
    print("EXEMPLE 5 : FILTRAGE PAR NIVEAU DE CONFIANCE")
    print("=" * 80)
    
    db = SessionLocal()
    detector = AdvancedAnomalyDetector(db)
    
    # Simuler plusieurs matchs
    matches_to_scan = [
        (1, 1, 2, 12.5, 2.00, 2.00),
        (2, 3, 4, 2.5, 2.20, 1.70),
        (3, 5, 6, 3.5, 2.10, 1.80),
        (4, 7, 8, 8.5, 8.00, 1.10),
        (5, 9, 10, 5.5, 3.20, 1.35),
    ]
    
    high_confidence_anomalies = []
    
    for match_id, home_id, away_id, line, over_odds, under_odds in matches_to_scan:
        anomaly = detector.detect_line_anomaly(
            match_id=match_id,
            home_team_id=home_id,
            away_team_id=away_id,
            market_type="over_under",
            bookmaker_line=line,
            bookmaker_over_odds=over_odds,
            bookmaker_under_odds=under_odds
        )
        
        # Filtrer : garder seulement HIGH, VERY_HIGH, EXTREME
        if anomaly.level in [AnomalyLevel.HIGH, AnomalyLevel.VERY_HIGH, AnomalyLevel.EXTREME]:
            high_confidence_anomalies.append((match_id, line, anomaly))
    
    print(f"\n📊 Matchs scannés: {len(matches_to_scan)}")
    print(f"✅ Anomalies HIGH+ détectées: {len(high_confidence_anomalies)}\n")
    
    if high_confidence_anomalies:
        print(f"{'='*80}")
        print(f"ANOMALIES HAUTE CONFIANCE")
        print(f"{'='*80}\n")
        
        for match_id, line, anomaly in high_confidence_anomalies:
            print(f"Match #{match_id} - Ligne {line}")
            print(f"  Score: {anomaly.total_score:.1f}/100")
            print(f"  Niveau: {anomaly.level.value}")
            print(f"  Prob Gap: {anomaly.probability_gap:.2%}")
            print(f"  Triggers: {', '.join(anomaly.triggers[:3])}")
            print()
    else:
        print("❌ Aucune anomalie haute confiance détectée")
    
    db.close()
    
    return high_confidence_anomalies


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("EXEMPLES D'UTILISATION - MOTEUR DE DÉTECTION D'ANOMALIES")
    print("=" * 80)
    
    # Exemple 1 : Ligne extrême
    example_1_extreme_line_anomaly()
    
    # Exemple 2 : Ligne modérée
    example_2_moderate_line_anomaly()
    
    # Exemple 3 : Pas d'anomalie
    example_3_no_anomaly()
    
    # Exemple 4 : Comparaison multiple lignes
    example_4_compare_multiple_lines()
    
    # Exemple 5 : Filtrage par confiance
    example_5_anomaly_filtering()
    
    print("\n" + "=" * 80)
    print("EXEMPLES TERMINÉS")
    print("=" * 80)
