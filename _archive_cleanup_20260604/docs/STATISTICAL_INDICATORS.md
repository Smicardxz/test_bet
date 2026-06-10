# 📊 Indicateurs Statistiques - Ligues Obscures

## 🎯 Objectif

Calculer des indicateurs fiables pour détecter des anomalies bookmakers dans les ligues obscures avec **faible volume de données**.

---

## 📈 Catégories d'Indicateurs

### **1. MOYENNES DE BUTS**

#### **1.1 Moyenne Buts Full Time (FT)**

**Formule** :
```
avg_goals_ft = Σ(total_goals) / n_matches
```

**Logique Métier** :
- Indicateur de base pour Over/Under
- Calculer séparément : domicile / extérieur / total
- Minimum 5 matchs recommandé

**Gestion Faible Volume** :
- Si n < 5 : utiliser moyenne ligue
- Si n < 10 : pondérer avec moyenne ligue (70% team / 30% league)

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

#### **1.2 Moyenne Buts Half Time (HT)**

**Formule** :
```
avg_goals_ht = Σ(goals_ht) / n_matches
```

**Logique Métier** :
- Essentiel pour marchés HT Over/Under
- Généralement 30-40% des buts FT
- Ratio HT/FT important

**Ratio HT/FT** :
```
ht_ft_ratio = avg_goals_ht / avg_goals_ft
```

**Gestion Faible Volume** :
- Ratio typique ligues obscures : 0.35-0.45
- Si n < 5 : utiliser ratio ligue moyen

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

#### **1.3 Moyenne Buts Second Half (SH)**

**Formule** :
```
avg_goals_sh = avg_goals_ft - avg_goals_ht
```

**Logique Métier** :
- Généralement 55-65% des buts
- Fatigue défensive en fin de match
- Important pour ligues amateurs (fatigue++)

**Ratio SH/FT** :
```
sh_ft_ratio = avg_goals_sh / avg_goals_ft
```

**Gestion Faible Volume** :
- Ratio typique : 0.55-0.65
- Ligues amateurs : ratio plus élevé (fatigue)

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

### **2. BUTS MARQUÉS / ENCAISSÉS**

#### **2.1 Buts Marqués (Attack Strength)**

**Formule** :
```
avg_goals_scored = Σ(goals_scored) / n_matches
avg_goals_scored_home = Σ(goals_scored_home) / n_home_matches
avg_goals_scored_away = Σ(goals_scored_away) / n_away_matches
```

**Attack Strength** :
```
attack_strength = avg_goals_scored / league_avg_goals_scored
```

**Logique Métier** :
- Mesure force offensive
- Split home/away ESSENTIEL
- Ligues obscures : écart home/away plus marqué

**Gestion Faible Volume** :
- Minimum 3 matchs home/away
- Sinon : utiliser moyenne totale

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

#### **2.2 Buts Encaissés (Defense Strength)**

**Formule** :
```
avg_goals_conceded = Σ(goals_conceded) / n_matches
avg_goals_conceded_home = Σ(goals_conceded_home) / n_home_matches
avg_goals_conceded_away = Σ(goals_conceded_away) / n_away_matches
```

**Defense Strength** :
```
defense_strength = avg_goals_conceded / league_avg_goals_conceded
```

**Logique Métier** :
- Mesure solidité défensive
- Ligues obscures : défenses souvent faibles
- Home advantage défensif important

**Gestion Faible Volume** :
- Minimum 3 matchs home/away
- Pondérer avec moyenne ligue si n < 5

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

### **3. VARIANCE & STABILITÉ**

#### **3.1 Variance des Scores**

**Formule** :
```
variance_goals = Σ((goals - avg_goals)²) / n_matches
std_dev_goals = √variance_goals
```

**Coefficient de Variation** :
```
cv = std_dev_goals / avg_goals
```

**Logique Métier** :
- Mesure prévisibilité
- CV faible (<0.5) = équipe stable
- CV élevé (>0.8) = équipe imprévisible

**Gestion Faible Volume** :
- Minimum 8 matchs pour variance fiable
- Si n < 8 : marquer comme "low confidence"

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

#### **3.2 Stabilité des Scores (Stability Score)**

**Formule** :
```
stability_score = 1 / (1 + cv)
```

**Ou version avancée** :
```
stability_score = exp(-cv) * (1 - abs(trend_coefficient))
```

**Trend Coefficient** :
```
# Régression linéaire sur derniers N matchs
trend = coefficient de la droite de régression
```

**Logique Métier** :
- Score 0-1 (1 = très stable)
- Intègre variance + tendance
- Ligues obscures : souvent instables

**Gestion Faible Volume** :
- Minimum 10 matchs pour trend fiable
- Sinon : utiliser uniquement CV

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

### **4. FRÉQUENCES UNDER**

#### **4.1 Under 1.5 FT**

**Formule** :
```
under_15_pct = count(total_goals < 1.5) / n_matches * 100
```

**Logique Métier** :
- Matchs très fermés (0-0, 1-0, 0-1)
- Rare en général (<20%)
- Plus fréquent en ligues défensives

**Gestion Faible Volume** :
- Minimum 10 matchs
- Comparer avec moyenne ligue

**Pondération** : ⭐⭐ (2/5) - **SECONDAIRE**

---

#### **4.2 Under 2.5 FT**

**Formule** :
```
under_25_pct = count(total_goals < 2.5) / n_matches * 100
```

**Logique Métier** :
- Marché le plus populaire
- Typiquement 40-60% des matchs
- Ligues obscures : souvent >50%

**Gestion Faible Volume** :
- Minimum 8 matchs
- Bayesian smoothing avec prior ligue

**Bayesian Smoothing** :
```
smoothed_pct = (n * team_pct + k * league_pct) / (n + k)
# k = 5 (strength of prior)
```

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

#### **4.3 Under 3.5 FT**

**Formule** :
```
under_35_pct = count(total_goals < 3.5) / n_matches * 100
```

**Logique Métier** :
- Typiquement 65-80% des matchs
- Bon indicateur pour matchs "normaux"

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

#### **4.4 Under 4.5 / 5.5 FT**

**Formule** :
```
under_45_pct = count(total_goals < 4.5) / n_matches * 100
under_55_pct = count(total_goals < 5.5) / n_matches * 100
```

**Logique Métier** :
- Typiquement >85% pour 4.5
- Typiquement >92% pour 5.5

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

#### **4.5 Under Extrêmes (6.5, 8.5, 10.5)**

**Formule** :
```
under_extreme_pct = count(total_goals < line) / n_matches * 100
```

**Logique Métier** :
- Ligues obscures : défenses faibles → plus de buts
- Ligues amateurs : matchs parfois fous (8-5, etc.)
- Bookmakers sous-estiment parfois

**Distribution Poisson** :
```
prob_under_x = Σ(k=0 to x) [λ^k * e^(-λ) / k!]
# λ = avg_goals_ft
```

**Gestion Faible Volume** :
- Utiliser Poisson si n < 15
- Ajuster λ avec variance observée

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT** (pour ligues amateurs)

---

### **5. FRÉQUENCES OVER**

#### **5.1 Over 1.5 / 2.5 / 3.5**

**Formule** :
```
over_x_pct = 100 - under_x_pct
```

**Logique Métier** :
- Complémentaire des Under
- Over 2.5 = marché principal

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

### **6. FRÉQUENCES HALF TIME**

#### **6.1 Under 0.5 HT**

**Formule** :
```
under_05_ht_pct = count(goals_ht == 0) / n_matches * 100
```

**Logique Métier** :
- 0-0 à la mi-temps
- Typiquement 25-40%
- Ligues obscures : souvent >35%

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

#### **6.2 Under 1.5 HT**

**Formule** :
```
under_15_ht_pct = count(goals_ht < 1.5) / n_matches * 100
```

**Logique Métier** :
- Marché HT populaire
- Typiquement 60-75%

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

#### **6.3 Over 0.5 / 1.5 HT**

**Formule** :
```
over_05_ht_pct = 100 - under_05_ht_pct
over_15_ht_pct = 100 - under_15_ht_pct
```

**Pondération** : ⭐⭐⭐⭐ (4/5) - **TRÈS IMPORTANT**

---

### **7. BOTH TEAMS TO SCORE (BTTS)**

#### **7.1 BTTS Percentage**

**Formule** :
```
btts_pct = count(home_goals > 0 AND away_goals > 0) / n_matches * 100
```

**Logique Métier** :
- Typiquement 45-60%
- Ligues obscures : défenses faibles → BTTS élevé
- Split home/away important

**BTTS Home vs Away** :
```
btts_home_pct = count(BTTS in home matches) / n_home_matches * 100
btts_away_pct = count(BTTS in away matches) / n_away_matches * 100
```

**Gestion Faible Volume** :
- Minimum 8 matchs
- Bayesian smoothing avec prior ligue

**Pondération** : ⭐⭐⭐⭐⭐ (5/5) - **CRITIQUE**

---

#### **7.2 BTTS & Over 2.5**

**Formule** :
```
btts_over25_pct = count(BTTS AND total_goals > 2.5) / n_matches * 100
```

**Logique Métier** :
- Marché combo populaire
- Typiquement 30-45%

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

### **8. CLEAN SHEETS**

#### **8.1 Clean Sheets Percentage**

**Formule** :
```
clean_sheet_pct = count(goals_conceded == 0) / n_matches * 100
clean_sheet_home_pct = count(goals_conceded_home == 0) / n_home_matches * 100
clean_sheet_away_pct = count(goals_conceded_away == 0) / n_away_matches * 100
```

**Logique Métier** :
- Indicateur solidité défensive
- Ligues obscures : clean sheets rares (<20%)
- Home clean sheets plus fréquents

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

### **9. 0-0 HALF TIME**

#### **9.1 0-0 HT Percentage**

**Formule** :
```
zero_zero_ht_pct = count(home_goals_ht == 0 AND away_goals_ht == 0) / n_matches * 100
```

**Logique Métier** :
- Typiquement 25-40%
- Ligues obscures : souvent >30%
- Indicateur rythme lent

**Pondération** : ⭐⭐⭐ (3/5) - **IMPORTANT**

---

### **10. RYTHME DÉBUT DE MATCH**

#### **10.1 Buts Avant Minute 15**

**Formule** :
```
goals_before_15 = Σ(goals scored before min 15) / n_matches
early_goal_pct = count(at least 1 goal before min 15) / n_matches * 100
```

**Logique Métier** :
- Indicateur démarrage rapide
- Typiquement 15-25% des matchs
- Ligues obscures : souvent démarrage lent

**Gestion Faible Volume** :
- Données minute-by-minute rares en ligues obscures
- Utiliser si disponible, sinon ignorer

**Pondération** : ⭐⭐ (2/5) - **SECONDAIRE** (données souvent indisponibles)

---

#### **10.2 Buts Après Minute 75**

**Formule** :
```
goals_after_75 = Σ(goals scored after min 75) / n_matches
late_goal_pct = count(at least 1 goal after min 75) / n_matches * 100
```

**Logique Métier** :
- Fatigue défensive
- Typiquement 25-35% des matchs
- Ligues amateurs : fatigue ++ → plus de buts tardifs

**Pondération** : ⭐⭐ (2/5) - **SECONDAIRE** (données souvent indisponibles)

---

## 🎯 INDICATEURS PRIORITAIRES (Top 10)

### **Rang 1-5 : CRITIQUES** ⭐⭐⭐⭐⭐

1. **Moyenne Buts FT** (avg_goals_ft)
2. **Buts Marqués Home/Away** (avg_goals_scored_home/away)
3. **Buts Encaissés Home/Away** (avg_goals_conceded_home/away)
4. **Under/Over 2.5 %** (under_25_pct / over_25_pct)
5. **BTTS %** (btts_pct)

### **Rang 6-10 : TRÈS IMPORTANTS** ⭐⭐⭐⭐

6. **Variance des Scores** (variance_goals, cv)
7. **Stabilité** (stability_score)
8. **Moyenne Buts HT** (avg_goals_ht)
9. **Under/Over 3.5 %** (under_35_pct)
10. **Under/Over 1.5 HT %** (under_15_ht_pct)

---

## 🧮 FORMULES AVANCÉES

### **Poisson Ajusté pour Faible Volume**

**Problème** : Poisson classique sous-estime variance en ligues obscures.

**Solution : Negative Binomial Distribution**

```python
from scipy.stats import nbinom

# Paramètres
mu = avg_goals_ft  # moyenne
var = variance_goals  # variance observée

# Si variance > moyenne (overdispersion)
if var > mu:
    # Negative Binomial
    r = mu**2 / (var - mu)  # dispersion parameter
    p = mu / var
    prob_under_x = nbinom.cdf(x, r, 1-p)
else:
    # Poisson standard
    prob_under_x = poisson.cdf(x, mu)
```

---

### **Expected Goals (xG) Simplifié**

**Formule** :
```
xG_home = (attack_strength_home * defense_strength_away) * league_avg_goals
xG_away = (attack_strength_away * defense_strength_home) * league_avg_goals
xG_total = xG_home + xG_away
```

**Ajustement Home Advantage** :
```
home_advantage_factor = league_avg_goals_home / league_avg_goals_away
xG_home *= home_advantage_factor
```

---

### **Bayesian Smoothing pour Faible Volume**

**Formule** :
```
smoothed_stat = (n * team_stat + k * league_stat) / (n + k)

# k = strength of prior
# Recommandé : k = 5 pour ligues obscures
```

**Exemple** :
```python
# Équipe : 3 matchs, 60% BTTS
# Ligue : moyenne 50% BTTS
# k = 5

smoothed_btts = (3 * 0.60 + 5 * 0.50) / (3 + 5)
             = (1.8 + 2.5) / 8
             = 0.5375 = 53.75%
```

---

### **Weighted Moving Average (WMA)**

**Formule** :
```
WMA = Σ(weight_i * value_i) / Σ(weight_i)

# Poids décroissants (matchs récents plus importants)
weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
```

**Exemple** :
```python
# 10 derniers matchs : buts = [2, 3, 1, 2, 4, 1, 2, 3, 2, 1]
weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

WMA = (2*1.0 + 3*0.9 + 1*0.8 + ... + 1*0.1) / sum(weights)
```

---

## 🎲 GESTION FAIBLE VOLUME - BEST PRACTICES

### **1. Minimum de Matchs Requis**

| Indicateur | Minimum Absolu | Minimum Recommandé | Action si n < min |
|------------|----------------|-------------------|-------------------|
| Moyenne buts | 3 | 5 | Utiliser moyenne ligue |
| Variance | 5 | 8 | Marquer "low confidence" |
| Pourcentages | 5 | 10 | Bayesian smoothing |
| Stabilité | 8 | 12 | Utiliser CV uniquement |
| Trend | 10 | 15 | Ignorer trend |

### **2. Stratégies de Compensation**

**A. Bayesian Smoothing**
```python
def bayesian_smooth(team_stat, league_stat, n_matches, k=5):
    return (n_matches * team_stat + k * league_stat) / (n_matches + k)
```

**B. Pooling avec Équipes Similaires**
```python
# Trouver équipes similaires (même ligue, tier, performance)
similar_teams = find_similar_teams(team, league, n=5)
pooled_stat = weighted_average([team_stat] + [t.stat for t in similar_teams])
```

**C. Régression vers la Moyenne**
```python
def regress_to_mean(team_stat, league_stat, n_matches, threshold=10):
    if n_matches < threshold:
        weight = n_matches / threshold
        return weight * team_stat + (1 - weight) * league_stat
    return team_stat
```

### **3. Confidence Intervals**

**Formule** :
```python
import scipy.stats as stats

# Intervalle de confiance 95%
ci_95 = stats.norm.interval(0.95, loc=mean, scale=std_error)

# Standard error
std_error = std_dev / sqrt(n_matches)
```

---

## 📊 PONDÉRATION RECOMMANDÉE PAR MARCHÉ

### **Over/Under 2.5**

| Indicateur | Poids |
|------------|-------|
| avg_goals_ft | 30% |
| avg_goals_scored + avg_goals_conceded | 25% |
| over_25_pct (historique) | 20% |
| variance_goals | 15% |
| stability_score | 10% |

### **BTTS**

| Indicateur | Poids |
|------------|-------|
| btts_pct (historique) | 35% |
| avg_goals_scored (both teams) | 25% |
| clean_sheet_pct (inverse) | 20% |
| avg_goals_conceded (both teams) | 15% |
| stability_score | 5% |

### **Over/Under HT**

| Indicateur | Poids |
|------------|-------|
| avg_goals_ht | 35% |
| over_x_ht_pct (historique) | 30% |
| ht_ft_ratio | 20% |
| zero_zero_ht_pct | 10% |
| early_goal_pct | 5% |

---

## 🔍 DÉTECTION D'ANOMALIES

### **Z-Score Method**

**Formule** :
```
z_score = (team_stat - league_mean) / league_std_dev

# Anomalie si |z_score| > 2
```

### **Percentile Method**

**Formule** :
```
percentile = percentileofscore(league_stats, team_stat)

# Anomalie si percentile < 10 ou > 90
```

### **Bookmaker vs Model Gap**

**Formule** :
```
prob_gap = |bookmaker_implied_prob - model_prob|

# Anomalie si prob_gap > 0.15 (15%)
```

---

## 💡 CONSEILS SPÉCIFIQUES LIGUES OBSCURES

### **1. Home Advantage Amplifié**

Ligues obscures → home advantage plus fort :
```python
home_advantage_multiplier = 1.3  # vs 1.15 en grandes ligues
```

### **2. Variance Élevée**

Ligues obscures → plus de variance :
```python
# Utiliser Negative Binomial au lieu de Poisson
# Ajuster intervals de confiance (+20%)
```

### **3. Données Manquantes**

```python
# Priorité des données :
# 1. Score final (toujours disponible)
# 2. Score HT (souvent disponible)
# 3. Minute-by-minute (rarement disponible)

# Stratégie : se concentrer sur 1 et 2
```

### **4. Qualité Variable**

```python
# Filtrer matchs suspects :
# - Scores aberrants (>8 buts)
# - Matchs avec incidents (expulsions multiples)
# - Matchs truqués potentiels
```

---

**Ce système d'indicateurs est optimisé pour les ligues obscures avec faible volume de données.**
