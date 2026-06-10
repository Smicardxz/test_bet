# 📋 Récapitulatif des Indicateurs Statistiques

## 🎯 LISTE COMPLÈTE DES INDICATEURS

### ✅ **IMPLÉMENTÉS DANS LE CODE**

| # | Indicateur | Formule | Importance | Fichier |
|---|------------|---------|------------|---------|
| 1 | avg_goals_ft | Σ(total_goals) / n | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 2 | avg_goals_ht | Σ(goals_ht) / n | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 3 | avg_goals_sh | avg_ft - avg_ht | ⭐⭐⭐ | advanced_stats_calculator.py |
| 4 | avg_goals_scored | Σ(goals_scored) / n | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 5 | avg_goals_conceded | Σ(goals_conceded) / n | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 6 | variance_goals | Σ(x - μ)² / n | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 7 | std_dev_goals | √variance | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 8 | cv_total | σ / μ | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 9 | stability_score | 1/(1+CV) ou e^(-CV) | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 10 | under_15_pct | count(<1.5) / n × 100 | ⭐⭐ | advanced_stats_calculator.py |
| 11 | under_25_pct | count(<2.5) / n × 100 | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 12 | under_35_pct | count(<3.5) / n × 100 | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 13 | under_45_pct | count(<4.5) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 14 | under_55_pct | count(<5.5) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 15 | under_65_pct | count(<6.5) / n × 100 | ⭐⭐ | advanced_stats_calculator.py |
| 16 | under_85_pct | count(<8.5) / n × 100 | ⭐⭐ | advanced_stats_calculator.py |
| 17 | under_105_pct | count(<10.5) / n × 100 | ⭐⭐ | advanced_stats_calculator.py |
| 18 | over_15_pct | 100 - under_15 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 19 | over_25_pct | 100 - under_25 | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 20 | over_35_pct | 100 - under_35 | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 21 | under_05_ht_pct | count(ht==0) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 22 | under_15_ht_pct | count(ht<1.5) / n × 100 | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 23 | over_05_ht_pct | 100 - under_05_ht | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 24 | over_15_ht_pct | 100 - under_15_ht | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 25 | btts_pct | count(BTTS) / n × 100 | ⭐⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 26 | btts_over25_pct | count(BTTS & O2.5) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 27 | clean_sheet_pct | count(conceded==0) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 28 | zero_zero_ht_pct | count(0-0 HT) / n × 100 | ⭐⭐⭐ | advanced_stats_calculator.py |
| 29 | ht_ft_ratio | avg_ht / avg_ft | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 30 | sh_ft_ratio | avg_sh / avg_ft | ⭐⭐⭐ | advanced_stats_calculator.py |
| 31 | poisson_probabilities | Distribution Poisson | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 32 | nbinom_probabilities | Negative Binomial | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 33 | weighted_moving_avg | WMA avec decay | ⭐⭐⭐ | advanced_stats_calculator.py |
| 34 | trend_coefficient | Régression linéaire | ⭐⭐⭐ | advanced_stats_calculator.py |
| 35 | is_overdispersed | variance > mean | ⭐⭐⭐ | advanced_stats_calculator.py |
| 36 | attack_strength | avg_scored / league_avg | ⭐⭐⭐⭐ | advanced_stats_calculator.py |
| 37 | defense_strength | avg_conceded / league_avg | ⭐⭐⭐⭐ | advanced_stats_calculator.py |

---

## 🔧 INDICATEURS AVANCÉS

### **Expected Goals (xG)**

```python
xg_home = (attack_home + defense_away) / 2 * home_factor
xg_away = (attack_away + defense_home) / 2
xg_total = xg_home + xg_away
```

**Implémenté** : `advanced_stats_calculator.py` → `calculate_expected_goals()`

---

### **Bayesian Smoothing**

```python
smoothed = (n * team_stat + k * league_stat) / (n + k)
```

**Implémenté** : `advanced_stats_calculator.py` → `bayesian_smooth()`

**Valeurs k recommandées** :
- avg_goals : k=5
- btts_pct : k=8
- over_25_pct : k=6
- variance : k=10

---

### **Z-Score Anomaly Detection**

```python
z_score = (team_stat - league_mean) / league_std
is_anomaly = abs(z_score) > 2.0
```

**Implémenté** : `advanced_stats_calculator.py` → `detect_statistical_anomaly()`

---

### **Confidence Level**

```python
if n >= 15: "HIGH"
elif n >= 10: "MEDIUM"
elif n >= 5: "LOW"
else: "VERY_LOW"
```

**Implémenté** : `advanced_stats_calculator.py` → `_calculate_confidence_level()`

---

## 📊 INDICATEURS PAR MARCHÉ

### **OVER/UNDER 2.5**

**Indicateurs Clés** :
1. avg_goals_ft (30%)
2. avg_goals_scored + avg_goals_conceded (25%)
3. over_25_pct historique (20%)
4. variance_goals (15%)
5. stability_score (10%)

**Fonction** : `calculate_over_25_probability()`

---

### **BTTS**

**Indicateurs Clés** :
1. btts_pct historique (35%)
2. avg_goals_scored both teams (25%)
3. clean_sheet_pct inverse (20%)
4. avg_goals_conceded both teams (15%)
5. stability_score (5%)

**Fonction** : `calculate_btts_probability()`

---

### **OVER/UNDER HT**

**Indicateurs Clés** :
1. avg_goals_ht (35%)
2. over_x_ht_pct historique (30%)
3. ht_ft_ratio (20%)
4. zero_zero_ht_pct (10%)
5. early_goal_pct (5%)

**Fonction** : `calculate_over_ht_probability()`

---

### **UNDER EXTRÊMES (5.5+, 8.5+)**

**Indicateurs Clés** :
1. negative_binomial_prob (40%)
2. avg_goals_ft (25%)
3. variance_goals (20%)
4. max_goals_observed (10%)
5. league_tier (5%)

**Fonction** : `calculate_extreme_over_probability()`

---

## 🎯 TOP 10 INDICATEURS PRIORITAIRES

### **1. avg_goals_ft** ⭐⭐⭐⭐⭐
- **Formule** : Σ(total_goals) / n
- **Usage** : Base pour tous les marchés Over/Under
- **Min matches** : 5
- **Bayesian k** : 5

### **2. avg_goals_scored (home/away)** ⭐⭐⭐⭐⭐
- **Formule** : Σ(goals_scored) / n
- **Usage** : Attack strength, xG calculation
- **Min matches** : 3 (par split)
- **Bayesian k** : 5

### **3. avg_goals_conceded (home/away)** ⭐⭐⭐⭐⭐
- **Formule** : Σ(goals_conceded) / n
- **Usage** : Defense strength, xG calculation
- **Min matches** : 3 (par split)
- **Bayesian k** : 5

### **4. over_25_pct / under_25_pct** ⭐⭐⭐⭐⭐
- **Formule** : count(goals > 2.5) / n × 100
- **Usage** : Marché principal O/U
- **Min matches** : 8
- **Bayesian k** : 6

### **5. btts_pct** ⭐⭐⭐⭐⭐
- **Formule** : count(both_scored) / n × 100
- **Usage** : Marché BTTS
- **Min matches** : 8
- **Bayesian k** : 8

### **6. variance_total_goals** ⭐⭐⭐⭐
- **Formule** : Σ(x - μ)² / n
- **Usage** : Prévisibilité, choix distribution
- **Min matches** : 8
- **Bayesian k** : 10

### **7. stability_score** ⭐⭐⭐⭐
- **Formule** : e^(-CV) × (1 - |trend|)
- **Usage** : Confiance dans prédictions
- **Min matches** : 10
- **Bayesian k** : N/A

### **8. avg_goals_ht** ⭐⭐⭐⭐
- **Formule** : Σ(goals_ht) / n
- **Usage** : Marchés Half Time
- **Min matches** : 5
- **Bayesian k** : 5

### **9. over_35_pct** ⭐⭐⭐⭐
- **Formule** : count(goals > 3.5) / n × 100
- **Usage** : Marché O/U 3.5
- **Min matches** : 8
- **Bayesian k** : 6

### **10. over_15_ht_pct** ⭐⭐⭐⭐
- **Formule** : count(goals_ht > 1.5) / n × 100
- **Usage** : Marché HT O/U 1.5
- **Min matches** : 8
- **Bayesian k** : 6

---

## 🔢 MINIMUM DE MATCHS REQUIS

| Indicateur | Min Absolu | Min Recommandé | Action si n < min |
|------------|-----------|----------------|-------------------|
| Moyennes (avg_*) | 3 | 5 | Bayesian smoothing |
| Pourcentages (*_pct) | 5 | 10 | Bayesian smoothing |
| Variance | 5 | 8 | Marquer "low confidence" |
| Stabilité | 8 | 12 | Utiliser CV uniquement |
| Trend | 10 | 15 | Ignorer trend |
| xG | 5 | 10 | Utiliser league avg |

---

## 🎲 GESTION FAIBLE VOLUME

### **Stratégie 1 : Bayesian Smoothing**

```python
if n_matches < 10:
    stat = bayesian_smooth(team_stat, league_stat, n_matches, k=5)
```

### **Stratégie 2 : Régression vers Moyenne**

```python
if n_matches < threshold:
    weight = n_matches / threshold
    stat = weight * team_stat + (1 - weight) * league_stat
```

### **Stratégie 3 : Confidence Weighting**

```python
confidence = min(n_matches / 10, 1.0)
adjusted_prob = prob * confidence + 0.5 * (1 - confidence)
```

---

## 📈 DISTRIBUTIONS UTILISÉES

### **Poisson** (variance ≤ moyenne)

```python
from scipy.stats import poisson
prob_under_x = poisson.cdf(x, lambda_param)
```

**Usage** : Grandes ligues, équipes stables

### **Negative Binomial** (variance > moyenne)

```python
from scipy.stats import nbinom
r = mu**2 / (variance - mu)
p = mu / variance
prob_under_x = nbinom.cdf(x, r, 1-p)
```

**Usage** : Ligues obscures, équipes instables

---

## 🏠 HOME ADVANTAGE FACTORS

| Type de Ligue | Facteur | Application |
|---------------|---------|-------------|
| Grandes ligues | 1.15 | xG_home × 1.15 |
| Ligues obscures | 1.30 | xG_home × 1.30 |
| Ligues amateurs | 1.40 | xG_home × 1.40 |
| Ligues régionales | 1.50 | xG_home × 1.50 |

---

## 📊 EXEMPLE COMPLET : CALCUL STATS ÉQUIPE

```python
from app.services.stats_engine.advanced_stats_calculator import AdvancedStatsCalculator

calc = AdvancedStatsCalculator(db)

# Calculer stats complètes
stats = calc.calculate_comprehensive_stats(
    team_id=123,
    last_n=10,
    home_away_split="home"
)

# Résultat :
{
    "basic": {
        "avg_goals_ft": 2.8,
        "avg_goals_ht": 1.2,
        "avg_goals_scored": 1.6,
        "avg_goals_conceded": 1.2,
        "ht_ft_ratio": 0.43,
        ...
    },
    "variance": {
        "variance_total_goals": 2.1,
        "cv_total": 0.52,
        "stability_score": 0.68,
        ...
    },
    "frequencies": {
        "under_25_pct": 40.0,
        "over_25_pct": 60.0,
        "over_35_pct": 30.0,
        ...
    },
    "btts": {
        "btts_pct": 65.0,
        "btts_over25_pct": 45.0,
        ...
    },
    "advanced": {
        "poisson_probabilities": {...},
        "nbinom_probabilities": {...},
        "weighted_moving_avg": 2.9,
        "trend_coefficient": 0.08,
        ...
    },
    "meta": {
        "matches_analyzed": 10,
        "confidence_level": "MEDIUM"
    }
}
```

---

## ✅ CHECKLIST IMPLÉMENTATION

- [x] Moyennes de base (FT, HT, SH)
- [x] Buts marqués/encaissés (home/away split)
- [x] Variance et écart-type
- [x] Coefficient de variation
- [x] Stabilité (simple et avancée)
- [x] Fréquences Under/Over (1.5 à 10.5)
- [x] Fréquences Half Time
- [x] BTTS percentage
- [x] Clean sheets
- [x] 0-0 HT percentage
- [x] Ratios HT/FT et SH/FT
- [x] Distribution Poisson
- [x] Distribution Negative Binomial
- [x] Weighted Moving Average
- [x] Trend coefficient
- [x] Expected Goals (xG)
- [x] Bayesian smoothing
- [x] Z-score anomaly detection
- [x] Confidence levels
- [x] League averages
- [x] Attack/Defense strength

---

**Système complet d'indicateurs statistiques pour ligues obscures implémenté.**
