# ✅ SYSTÈME COMPLET D'INDICATEURS STATISTIQUES

## 🎯 Vue d'Ensemble

**37 indicateurs statistiques** implémentés et optimisés pour les **ligues obscures** avec **faible volume de données**.

---

## 📊 LISTE COMPLÈTE DES 37 INDICATEURS

### **CATÉGORIE 1 : MOYENNES DE BUTS** (10 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 1 | avg_goals_ft | Σ(total_goals) / n | ⭐⭐⭐⭐⭐ |
| 2 | avg_goals_ht | Σ(goals_ht) / n | ⭐⭐⭐⭐ |
| 3 | avg_goals_sh | avg_ft - avg_ht | ⭐⭐⭐ |
| 4 | avg_goals_scored | Σ(goals_scored) / n | ⭐⭐⭐⭐⭐ |
| 5 | avg_goals_conceded | Σ(goals_conceded) / n | ⭐⭐⭐⭐⭐ |
| 6 | avg_goals_scored_ht | Σ(goals_scored_ht) / n | ⭐⭐⭐ |
| 7 | avg_goals_conceded_ht | Σ(goals_conceded_ht) / n | ⭐⭐⭐ |
| 8 | avg_goals_scored_sh | avg_scored - avg_scored_ht | ⭐⭐⭐ |
| 9 | ht_ft_ratio | avg_ht / avg_ft | ⭐⭐⭐⭐ |
| 10 | sh_ft_ratio | avg_sh / avg_ft | ⭐⭐⭐ |

---

### **CATÉGORIE 2 : VARIANCE & STABILITÉ** (8 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 11 | variance_goals_scored | Σ(x - μ)² / n | ⭐⭐⭐⭐ |
| 12 | variance_goals_conceded | Σ(x - μ)² / n | ⭐⭐⭐⭐ |
| 13 | variance_total_goals | Σ(x - μ)² / n | ⭐⭐⭐⭐ |
| 14 | std_dev_scored | √variance | ⭐⭐⭐ |
| 15 | std_dev_conceded | √variance | ⭐⭐⭐ |
| 16 | std_dev_total | √variance | ⭐⭐⭐ |
| 17 | cv_total | σ / μ | ⭐⭐⭐⭐ |
| 18 | stability_score | e^(-CV) × (1 - \|trend\|) | ⭐⭐⭐⭐ |

---

### **CATÉGORIE 3 : FRÉQUENCES UNDER/OVER** (13 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 19 | under_15_pct | count(<1.5) / n × 100 | ⭐⭐ |
| 20 | under_25_pct | count(<2.5) / n × 100 | ⭐⭐⭐⭐⭐ |
| 21 | under_35_pct | count(<3.5) / n × 100 | ⭐⭐⭐⭐ |
| 22 | under_45_pct | count(<4.5) / n × 100 | ⭐⭐⭐ |
| 23 | under_55_pct | count(<5.5) / n × 100 | ⭐⭐⭐ |
| 24 | under_65_pct | count(<6.5) / n × 100 | ⭐⭐ |
| 25 | under_85_pct | count(<8.5) / n × 100 | ⭐⭐ |
| 26 | under_105_pct | count(<10.5) / n × 100 | ⭐⭐ |
| 27 | over_15_pct | 100 - under_15 | ⭐⭐⭐ |
| 28 | over_25_pct | 100 - under_25 | ⭐⭐⭐⭐⭐ |
| 29 | over_35_pct | 100 - under_35 | ⭐⭐⭐⭐ |
| 30 | over_45_pct | 100 - under_45 | ⭐⭐⭐ |
| 31 | over_55_pct | 100 - under_55 | ⭐⭐⭐ |

---

### **CATÉGORIE 4 : HALF TIME** (6 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 32 | under_05_ht_pct | count(ht==0) / n × 100 | ⭐⭐⭐ |
| 33 | under_15_ht_pct | count(ht<1.5) / n × 100 | ⭐⭐⭐⭐ |
| 34 | under_25_ht_pct | count(ht<2.5) / n × 100 | ⭐⭐⭐ |
| 35 | over_05_ht_pct | 100 - under_05_ht | ⭐⭐⭐⭐ |
| 36 | over_15_ht_pct | 100 - under_15_ht | ⭐⭐⭐⭐ |
| 37 | zero_zero_ht_pct | count(0-0 HT) / n × 100 | ⭐⭐⭐ |

---

### **CATÉGORIE 5 : BTTS & CLEAN SHEETS** (4 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 38 | btts_pct | count(BTTS) / n × 100 | ⭐⭐⭐⭐⭐ |
| 39 | btts_over25_pct | count(BTTS & O2.5) / n × 100 | ⭐⭐⭐ |
| 40 | no_btts_pct | 100 - btts_pct | ⭐⭐⭐ |
| 41 | clean_sheet_pct | count(conceded==0) / n × 100 | ⭐⭐⭐ |

---

### **CATÉGORIE 6 : INDICATEURS AVANCÉS** (10 indicateurs)

| # | Indicateur | Description | Importance |
|---|------------|-------------|------------|
| 42 | attack_strength | avg_scored / league_avg | ⭐⭐⭐⭐ |
| 43 | defense_strength | avg_conceded / league_avg | ⭐⭐⭐⭐ |
| 44 | is_overdispersed | variance > mean | ⭐⭐⭐ |
| 45 | poisson_probabilities | Distribution Poisson | ⭐⭐⭐⭐ |
| 46 | nbinom_probabilities | Negative Binomial | ⭐⭐⭐⭐ |
| 47 | weighted_moving_avg | WMA avec decay | ⭐⭐⭐ |
| 48 | trend_coefficient | Régression linéaire | ⭐⭐⭐ |
| 49 | is_trending_up | trend > 0.1 | ⭐⭐ |
| 50 | is_trending_down | trend < -0.1 | ⭐⭐ |
| 51 | confidence_level | HIGH/MEDIUM/LOW | ⭐⭐⭐⭐⭐ |

---

## 🎯 TOP 10 INDICATEURS PRIORITAIRES

### **1. avg_goals_ft** ⭐⭐⭐⭐⭐
- Base pour tous les marchés Over/Under
- Min 5 matchs, Bayesian k=5

### **2. avg_goals_scored (home/away)** ⭐⭐⭐⭐⭐
- Attack strength, xG calculation
- Min 3 matchs par split, Bayesian k=5

### **3. avg_goals_conceded (home/away)** ⭐⭐⭐⭐⭐
- Defense strength, xG calculation
- Min 3 matchs par split, Bayesian k=5

### **4. over_25_pct / under_25_pct** ⭐⭐⭐⭐⭐
- Marché principal O/U
- Min 8 matchs, Bayesian k=6

### **5. btts_pct** ⭐⭐⭐⭐⭐
- Marché BTTS
- Min 8 matchs, Bayesian k=8

### **6. variance_total_goals** ⭐⭐⭐⭐
- Prévisibilité, choix distribution
- Min 8 matchs, Bayesian k=10

### **7. stability_score** ⭐⭐⭐⭐
- Confiance dans prédictions
- Min 10 matchs

### **8. avg_goals_ht** ⭐⭐⭐⭐
- Marchés Half Time
- Min 5 matchs, Bayesian k=5

### **9. over_35_pct** ⭐⭐⭐⭐
- Marché O/U 3.5
- Min 8 matchs, Bayesian k=6

### **10. over_15_ht_pct** ⭐⭐⭐⭐
- Marché HT O/U 1.5
- Min 8 matchs, Bayesian k=6

---

## 📁 FICHIERS IMPLÉMENTÉS

### **Code Python**

```
app/services/stats_engine/
├── stats_calculator.py              # Calculateur de base
├── advanced_stats_calculator.py     # 51 indicateurs complets
└── league_stats_calculator.py       # Stats de ligue
```

### **Documentation**

```
docs/
├── STATISTICAL_INDICATORS.md        # Liste complète + formules
├── INDICATOR_WEIGHTS.md             # Pondération par marché
├── MATHEMATICAL_FORMULAS.md         # Formules mathématiques
├── INDICATORS_SUMMARY.md            # Récapitulatif
├── BEST_PRACTICES.md                # Best practices
└── README.md                        # Guide complet
```

### **Exemples**

```
examples/
└── usage_examples.py                # 8 exemples d'utilisation
```

---

## 🔧 UTILISATION

### **Calcul Stats Complètes**

```python
from app.services.stats_engine import AdvancedStatsCalculator

calc = AdvancedStatsCalculator(db)

stats = calc.calculate_comprehensive_stats(
    team_id=1,
    last_n=10,
    home_away_split="home"
)

# Résultat : dictionnaire avec 51 indicateurs
{
    "basic": {...},           # 10 moyennes
    "variance": {...},        # 8 variance/stabilité
    "frequencies": {...},     # 13 under/over
    "half_time": {...},       # 6 HT
    "btts": {...},            # 4 BTTS/clean sheets
    "clean_sheets": {...},
    "advanced": {...},        # 10 avancés
    "meta": {...}             # confiance
}
```

### **Expected Goals**

```python
xg_data = calc.calculate_expected_goals(
    home_team_id=1,
    away_team_id=2,
    league_avg_goals=2.5,
    home_advantage_factor=1.3
)

# xG + probabilités Poisson/NBinom
```

### **Bayesian Smoothing**

```python
smoothed = calc.bayesian_smooth(
    team_stat=3.2,
    league_stat=2.5,
    n_matches=4,
    k=5
)
```

### **Détection Anomalie**

```python
is_anomaly, z_score = calc.detect_statistical_anomaly(
    team_stat=3.8,
    league_mean=2.5,
    league_std=0.6,
    threshold=2.0
)
```

---

## 🎲 GESTION FAIBLE VOLUME

### **4 Stratégies Implémentées**

#### **1. Bayesian Smoothing** ✅

```python
if n_matches < 10:
    stat = bayesian_smooth(team_stat, league_stat, n_matches, k=5)
```

#### **2. Régression vers Moyenne** ✅

```python
if n_matches < 8:
    weight = n_matches / 8
    stat = weight * team_stat + (1 - weight) * league_stat
```

#### **3. Confidence Weighting** ✅

```python
confidence = min(n_matches / 10, 1.0)
adjusted_prob = prob * confidence + 0.5 * (1 - confidence)
```

#### **4. Distribution Adaptée** ✅

```python
if variance > avg_goals:
    # Negative Binomial (ligues obscures)
    probs = calculate_nbinom_probabilities(avg, variance)
else:
    # Poisson (ligues stables)
    probs = calculate_poisson_probabilities(avg)
```

---

## 📊 PONDÉRATION PAR MARCHÉ

### **Over/Under 2.5**

```python
weights = {
    "avg_goals_ft": 0.30,
    "attack_defense": 0.25,
    "historical_over_25": 0.20,
    "variance": 0.15,
    "stability": 0.10
}
```

### **BTTS**

```python
weights = {
    "btts_pct": 0.35,
    "avg_goals_scored": 0.25,
    "clean_sheet_inverse": 0.20,
    "avg_goals_conceded": 0.15,
    "stability": 0.05
}
```

### **Over/Under HT**

```python
weights = {
    "avg_goals_ht": 0.35,
    "over_ht_pct": 0.30,
    "ht_ft_ratio": 0.20,
    "zero_zero_ht": 0.10,
    "early_goals": 0.05
}
```

---

## 🏠 HOME ADVANTAGE FACTORS

```python
HOME_ADVANTAGE = {
    "major_leagues": 1.15,
    "obscure_leagues": 1.30,      # ← Défaut
    "amateur_leagues": 1.40,
    "regional_leagues": 1.50
}
```

---

## 📈 MINIMUM DE MATCHS

| Analyse | Min Absolu | Min Recommandé | Action si < min |
|---------|-----------|----------------|-----------------|
| Moyennes | 3 | 5 | Bayesian smoothing |
| Variance | 5 | 8 | Marquer "low confidence" |
| Pourcentages | 5 | 10 | Bayesian smoothing |
| Stabilité | 8 | 12 | Utiliser CV uniquement |
| Trend | 10 | 15 | Ignorer trend |

---

## ✅ CHECKLIST IMPLÉMENTATION

- [x] 10 moyennes de buts (FT, HT, SH, scored, conceded)
- [x] 8 indicateurs variance/stabilité
- [x] 13 fréquences Under/Over (1.5 à 10.5)
- [x] 6 indicateurs Half Time
- [x] 4 indicateurs BTTS/Clean Sheets
- [x] 10 indicateurs avancés (xG, Poisson, NBinom, WMA, trend)
- [x] Bayesian smoothing
- [x] Régression vers moyenne
- [x] Confidence weighting
- [x] Z-score anomaly detection
- [x] League averages calculator
- [x] Home advantage factors
- [x] Distribution adaptative (Poisson/NBinom)
- [x] Weighted moving average
- [x] Trend coefficient
- [x] Attack/Defense strength

---

## 🎯 RÉSUMÉ

✅ **51 indicateurs** implémentés  
✅ **4 stratégies** gestion faible volume  
✅ **2 distributions** (Poisson, Negative Binomial)  
✅ **3 niveaux** de confiance (HIGH/MEDIUM/LOW)  
✅ **Optimisé** pour ligues obscures  
✅ **Documentation** complète (6 fichiers)  
✅ **Exemples** d'utilisation (8 exemples)  

**Système complet et prêt à l'emploi pour détecter les inefficiences statistiques dans les ligues obscures de football.**
