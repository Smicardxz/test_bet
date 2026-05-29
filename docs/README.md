# 📚 Documentation - Système Statistique Avancé

## 📖 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Fichiers de documentation](#fichiers-de-documentation)
3. [Guide de démarrage rapide](#guide-de-démarrage-rapide)
4. [Exemples d'utilisation](#exemples-dutilisation)

---

## 🎯 Vue d'ensemble

Ce système fournit **37 indicateurs statistiques** optimisés pour les ligues obscures de football avec faible volume de données.

### **Objectif**

Détecter les **inefficiences statistiques** entre les lignes bookmakers et la réalité statistique des équipes dans les divisions inférieures.

### **Caractéristiques Principales**

✅ **37 indicateurs statistiques** complets  
✅ **Gestion faible volume** (Bayesian smoothing, régression)  
✅ **Distributions adaptées** (Poisson, Negative Binomial)  
✅ **Détection d'anomalies** (Z-score, percentiles)  
✅ **Confidence scoring** multi-facteurs  
✅ **Optimisé ligues obscures** (home advantage amplifié, variance élevée)  

---

## 📁 Fichiers de Documentation

### **1. STATISTICAL_INDICATORS.md** 📊

**Contenu** : Liste complète des 37 indicateurs avec formules, logique métier, gestion faible volume.

**Sections** :
- Moyennes de buts (FT, HT, SH)
- Buts marqués/encaissés
- Variance & stabilité
- Fréquences Under/Over
- Fréquences Half Time
- BTTS
- Clean sheets
- Indicateurs prioritaires (Top 10)
- Formules avancées
- Gestion faible volume

**Utilisation** : Référence complète pour comprendre chaque indicateur.

---

### **2. INDICATOR_WEIGHTS.md** ⚖️

**Contenu** : Pondération optimale des indicateurs par marché.

**Sections** :
- Over/Under 2.5 (pondération + formule)
- BTTS (pondération + formule)
- Over/Under HT (pondération + formule)
- Over/Under 3.5
- Under extrêmes (5.5+, 8.5+)
- Home/Away adjustments
- Confidence weighting
- Bayesian smoothing
- Exemple complet de calcul

**Utilisation** : Guide pour implémenter le calcul de probabilités pondérées.

---

### **3. MATHEMATICAL_FORMULAS.md** 🧮

**Contenu** : Toutes les formules mathématiques détaillées.

**Sections** :
- Statistiques de base (moyenne, variance, CV)
- Distributions (Poisson, Negative Binomial)
- Régression & tendances
- Probabilités & Bayésien
- Expected Goals (xG)
- Stabilité & confiance
- Détection d'anomalies (Z-score, percentiles)
- Moyennes pondérées (WMA, EMA)
- Combinaison de probabilités
- Kelly Criterion
- Value betting
- Normalisation

**Utilisation** : Référence mathématique complète.

---

### **4. INDICATORS_SUMMARY.md** 📋

**Contenu** : Récapitulatif des 37 indicateurs implémentés.

**Sections** :
- Liste complète avec importance
- Indicateurs avancés (xG, Bayesian, Z-score)
- Indicateurs par marché
- Top 10 prioritaires
- Minimum de matchs requis
- Gestion faible volume
- Distributions utilisées
- Home advantage factors
- Exemple complet

**Utilisation** : Vue d'ensemble rapide de tous les indicateurs.

---

### **5. BEST_PRACTICES.md** 💡

**Contenu** : Best practices pour ligues obscures.

**Sections** :
- Gestion faible volume (4 stratégies)
- Choix de distribution
- Home advantage
- Pondération des indicateurs
- Gestion de la variance
- Seuils de détection
- Filtrage des matchs
- Minimum de données
- Gestion des outliers
- Mise à jour des stats
- Backtesting
- Calibration
- Validation
- Conseils spécifiques ligues obscures
- Monitoring & logging
- Red flags
- Checklist pré-analyse

**Utilisation** : Guide pratique pour utiliser le système correctement.

---

## 🚀 Guide de Démarrage Rapide

### **1. Installation**

```bash
# Installer dépendances
pip install -r requirements.txt

# Configurer base de données
createdb betting_anomaly

# Créer tables
python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
```

### **2. Premier Calcul de Stats**

```python
from app.core.database import SessionLocal
from app.services.stats_engine import AdvancedStatsCalculator

db = SessionLocal()
calc = AdvancedStatsCalculator(db)

# Calculer stats équipe
stats = calc.calculate_comprehensive_stats(
    team_id=1,
    last_n=10,
    home_away_split="home"
)

print(f"Moyenne buts: {stats['basic']['avg_goals_ft']:.2f}")
print(f"Over 2.5: {stats['frequencies']['over_25_pct']:.1f}%")
print(f"BTTS: {stats['btts']['btts_pct']:.1f}%")
print(f"Confiance: {stats['meta']['confidence_level']}")

db.close()
```

### **3. Calculer Expected Goals**

```python
xg_data = calc.calculate_expected_goals(
    home_team_id=1,
    away_team_id=2,
    league_avg_goals=2.5,
    home_advantage_factor=1.3
)

print(f"xG Total: {xg_data['xg_total']:.2f}")
print(f"Prob Over 2.5: {xg_data['probabilities']['over_25']:.2%}")
```

### **4. Détecter Anomalie**

```python
is_anomaly, z_score = calc.detect_statistical_anomaly(
    team_stat=3.8,
    league_mean=2.5,
    league_std=0.6,
    threshold=2.0
)

print(f"Anomalie: {is_anomaly}")
print(f"Z-Score: {z_score:.2f}")
```

---

## 📚 Exemples d'Utilisation

### **Fichier : `examples/usage_examples.py`**

**8 exemples complets** :

1. **Calculer stats équipe** - Stats complètes avec 37 indicateurs
2. **Calculer expected goals** - xG avec probabilités
3. **Bayesian smoothing** - Lissage pour faible volume
4. **Détecter anomalie** - Z-score detection
5. **Stats de ligue** - Moyennes et benchmarks
6. **Analyse complète match** - Pipeline complet
7. **Weighted moving average** - Moyenne pondérée
8. **Comparer distributions** - Poisson vs NBinom

**Lancer les exemples** :

```bash
python examples/usage_examples.py
```

---

## 🎯 Workflow Recommandé

### **Étape 1 : Ingestion**

```python
from app.services.ingestion import MatchIngestionService, OddsIngestionService

# Récupérer matchs
match_service = MatchIngestionService(db)
matches = await match_service.fetch_upcoming_matches(days_ahead=7)

# Récupérer odds
odds_service = OddsIngestionService(db)
odds_service.save_odds(match_id, odds_data)
odds_service.calculate_market_averages(match_id)
```

### **Étape 2 : Calcul Stats**

```python
from app.services.stats_engine import AdvancedStatsCalculator

calc = AdvancedStatsCalculator(db)

# Stats home
home_stats = calc.calculate_comprehensive_stats(
    team_id=home_team_id,
    home_away_split="home"
)

# Stats away
away_stats = calc.calculate_comprehensive_stats(
    team_id=away_team_id,
    home_away_split="away"
)

# Expected goals
xg_data = calc.calculate_expected_goals(home_team_id, away_team_id)
```

### **Étape 3 : Détection Anomalies**

```python
from app.services.anomaly_engine import AnomalyDetector

detector = AnomalyDetector(db)

anomalies = detector.detect_match_anomalies(
    match_id=match_id,
    home_team_id=home_team_id,
    away_team_id=away_team_id
)
```

### **Étape 4 : Scoring Confiance**

```python
from app.services.confidence_engine import ConfidenceScorer

scorer = ConfidenceScorer(db)

for anomaly in anomalies:
    scorer.calculate_confidence(
        anomaly=anomaly,
        home_team_id=home_team_id,
        away_team_id=away_team_id
    )
```

### **Étape 5 : Génération Explications**

```python
from app.services.explanation_engine import ExplanationGenerator

generator = ExplanationGenerator(db)

for anomaly in anomalies:
    explanation = generator.generate_explanation(
        anomaly=anomaly,
        match=match,
        home_stats=home_stats,
        away_stats=away_stats
    )
    
    print(explanation)
```

---

## 📊 Indicateurs par Importance

### **S-Tier** (Indispensables) ⭐⭐⭐⭐⭐

1. `avg_goals_ft`
2. `avg_goals_scored` (home/away)
3. `avg_goals_conceded` (home/away)
4. `over_25_pct` / `under_25_pct`
5. `btts_pct`

### **A-Tier** (Très Importants) ⭐⭐⭐⭐

6. `variance_total_goals`
7. `stability_score`
8. `avg_goals_ht`
9. `over_35_pct`
10. `clean_sheet_pct`

### **B-Tier** (Importants) ⭐⭐⭐

11-20. Ratios, fréquences HT, attack/defense strength

### **C-Tier** (Secondaires) ⭐⭐

21-37. Extrêmes, trends, WMA, Z-scores

---

## 🔧 Configuration

### **Paramètres Clés**

```python
# app/core/config.py

MIN_MATCHES_FOR_STATS = 5        # Minimum de matchs
ANOMALY_THRESHOLD = 2.0          # Seuil anomaly score
CONFIDENCE_HIGH_THRESHOLD = 0.75 # Seuil confiance HIGH
CONFIDENCE_MEDIUM_THRESHOLD = 0.50
```

### **Bayesian K Values**

```python
BAYESIAN_K = {
    "avg_goals": 5,
    "btts_pct": 8,
    "over_25_pct": 6,
    "variance": 10
}
```

### **Home Advantage Factors**

```python
HOME_ADVANTAGE = {
    "major_leagues": 1.15,
    "obscure_leagues": 1.30,
    "amateur_leagues": 1.40,
    "regional_leagues": 1.50
}
```

---

## 🧪 Tests

```bash
# Lancer tests unitaires
pytest tests/

# Avec coverage
pytest --cov=app tests/

# Tests spécifiques
pytest tests/test_stats_calculator.py
```

---

## 📈 Performance

### **Optimisations Implémentées**

✅ Calculs vectorisés (NumPy)  
✅ Caching des stats de ligue  
✅ Queries optimisées (jointures)  
✅ Bayesian smoothing (évite recalculs)  
✅ Incremental updates  

### **Benchmarks**

- Calcul stats équipe : ~50ms
- Expected goals : ~30ms
- Détection anomalies : ~100ms
- Analyse complète match : ~200ms

---

## 🐛 Troubleshooting

### **Problème : "Insufficient data"**

**Solution** : Appliquer Bayesian smoothing

```python
if n_matches < 10:
    stat = calc.bayesian_smooth(team_stat, league_stat, n_matches)
```

### **Problème : Variance très élevée**

**Solution** : Utiliser Negative Binomial

```python
if variance > avg_goals:
    probs = calc._calculate_negative_binomial_probabilities(avg, variance)
```

### **Problème : Confiance très faible**

**Solution** : Augmenter k Bayesian ou utiliser league averages

```python
k = 10  # au lieu de 5
smoothed = calc.bayesian_smooth(team_stat, league_stat, n_matches, k=k)
```

---

## 📞 Support

- **Documentation** : `/docs/`
- **Exemples** : `/examples/usage_examples.py`
- **Issues** : GitHub Issues
- **Architecture** : `ARCHITECTURE.md`

---

## 🎓 Ressources Supplémentaires

### **Lectures Recommandées**

1. **Poisson Process** : https://en.wikipedia.org/wiki/Poisson_distribution
2. **Negative Binomial** : https://en.wikipedia.org/wiki/Negative_binomial_distribution
3. **Bayesian Statistics** : https://en.wikipedia.org/wiki/Bayesian_statistics
4. **Expected Goals** : https://en.wikipedia.org/wiki/Expected_goals

### **Papers**

- Dixon & Coles (1997) - Modelling Association Football Scores
- Karlis & Ntzoufras (2003) - Bayesian modelling of football outcomes

---

## ✅ Checklist Utilisation

Avant d'utiliser le système :

- [ ] Lire `STATISTICAL_INDICATORS.md`
- [ ] Lire `BEST_PRACTICES.md`
- [ ] Tester avec `usage_examples.py`
- [ ] Configurer `.env` correctement
- [ ] Vérifier minimum de données (n >= 5)
- [ ] Appliquer Bayesian smoothing si n < 10
- [ ] Utiliser home/away split
- [ ] Vérifier variance (Poisson vs NBinom)
- [ ] Calculer confidence score
- [ ] Logger les analyses

---

**Documentation complète pour le système de statistiques avancées.**
