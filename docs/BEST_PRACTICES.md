# 🎯 Best Practices - Ligues Obscures

## 📊 GESTION DU FAIBLE VOLUME DE DONNÉES

### **Problème Principal**

Ligues obscures = peu de matchs disponibles → statistiques moins fiables.

### **Solutions Recommandées**

#### **1. Bayesian Smoothing** ⭐⭐⭐⭐⭐

**Quand l'utiliser** : n < 10 matchs

```python
def apply_bayesian_smoothing(team_stat, league_stat, n_matches):
    k = 5  # strength of prior
    
    if n_matches < 10:
        smoothed = (n_matches * team_stat + k * league_stat) / (n_matches + k)
        return smoothed
    
    return team_stat
```

**Valeurs k recommandées** :
- Moyennes (avg_goals) : k=5
- Pourcentages (btts_pct, over_25_pct) : k=6-8
- Variance : k=10

---

#### **2. Régression vers la Moyenne** ⭐⭐⭐⭐

**Quand l'utiliser** : n < 8 matchs

```python
def regress_to_mean(team_stat, league_stat, n_matches, threshold=8):
    if n_matches < threshold:
        weight = n_matches / threshold
        return weight * team_stat + (1 - weight) * league_stat
    
    return team_stat
```

---

#### **3. Confidence Weighting** ⭐⭐⭐⭐

**Quand l'utiliser** : Toujours pour ajuster probabilités

```python
def apply_confidence_weighting(probability, n_matches, min_matches=10):
    confidence = min(n_matches / min_matches, 1.0)
    
    # Régression vers 50% si faible confiance
    adjusted = probability * confidence + 0.5 * (1 - confidence)
    
    return adjusted, confidence
```

---

#### **4. Pooling avec Équipes Similaires** ⭐⭐⭐

**Quand l'utiliser** : n < 5 matchs

```python
def pool_with_similar_teams(team_id, league, n_similar=5):
    # Trouver équipes similaires (même ligue, performance proche)
    similar_teams = find_similar_teams(team_id, league, n=n_similar)
    
    # Pooler les statistiques
    pooled_stats = weighted_average([team] + similar_teams)
    
    return pooled_stats
```

---

## 🎲 CHOIX DE LA DISTRIBUTION

### **Décision : Poisson vs Negative Binomial**

```python
def choose_distribution(avg_goals, variance):
    if variance > avg_goals:
        # Overdispersion → Negative Binomial
        return "negative_binomial"
    else:
        # Variance normale → Poisson
        return "poisson"
```

**Règle générale** :
- **Grandes ligues** : Poisson (variance ≈ moyenne)
- **Ligues obscures** : Negative Binomial (variance > moyenne)

---

## 🏠 HOME ADVANTAGE

### **Facteurs par Type de Ligue**

```python
HOME_ADVANTAGE = {
    "premier_league": 1.15,
    "ligue_1": 1.18,
    "bundesliga": 1.12,
    
    "national_league": 1.30,
    "regionalliga": 1.35,
    "segunda_b": 1.32,
    
    "amateur_leagues": 1.40,
    "regional_leagues": 1.50,
    "womens_obscure": 1.45
}
```

**Application** :

```python
def apply_home_advantage(xg_home, league_type):
    factor = HOME_ADVANTAGE.get(league_type, 1.30)
    return xg_home * factor
```

---

## ⚖️ PONDÉRATION DES INDICATEURS

### **Principe de Base**

Plus un indicateur est :
- **Corrélé** avec le résultat → poids élevé
- **Stable** en faible volume → poids élevé
- **Spécifique** au marché → poids élevé

### **Exemple : Over/Under 2.5**

```python
WEIGHTS_OVER_25 = {
    "avg_goals_ft": 0.30,           # Très corrélé
    "attack_defense_combined": 0.25, # Très corrélé
    "historical_over_25": 0.20,      # Pattern direct
    "variance": 0.15,                # Prévisibilité
    "stability": 0.10                # Confiance
}

def calculate_weighted_probability(indicators, weights):
    return sum(indicators[k] * weights[k] for k in weights)
```

---

## 📉 GESTION DE LA VARIANCE

### **Variance Élevée = Opportunité**

Ligues obscures ont souvent variance élevée → plus de buts extrêmes.

**Stratégie** :

```python
def adjust_for_high_variance(probability, variance, threshold=3.0):
    if variance > threshold:
        # Bonus pour Over extrêmes
        bonus = min((variance - threshold) * 0.05, 0.15)
        return probability + bonus
    
    return probability
```

---

## 🎯 SEUILS DE DÉTECTION D'ANOMALIES

### **Anomaly Score Thresholds**

```python
ANOMALY_THRESHOLDS = {
    "low": 2.0,      # Anomalie détectée
    "medium": 3.0,   # Anomalie forte
    "high": 4.5,     # Anomalie très forte
    "extreme": 6.0   # Anomalie extrême
}
```

### **Probability Gap Thresholds**

```python
PROBABILITY_GAP_THRESHOLDS = {
    "low": 0.10,     # 10% gap
    "medium": 0.15,  # 15% gap
    "high": 0.20,    # 20% gap
    "extreme": 0.30  # 30% gap
}
```

---

## 🔍 FILTRAGE DES MATCHS

### **Matchs à Exclure**

```python
def should_exclude_match(match):
    # Scores aberrants
    if match.total_goals > 10:
        return True
    
    # Expulsions multiples (si données disponibles)
    if match.red_cards > 2:
        return True
    
    # Matchs truqués potentiels (patterns suspects)
    if is_suspicious_pattern(match):
        return True
    
    return False
```

---

## 📊 MINIMUM DE DONNÉES REQUIS

### **Seuils Stricts**

| Analyse | Min Absolu | Min Recommandé | Action si < min |
|---------|-----------|----------------|-----------------|
| Calcul moyennes | 3 | 5 | Bayesian smoothing |
| Calcul variance | 5 | 8 | Marquer "low confidence" |
| Calcul pourcentages | 5 | 10 | Bayesian smoothing |
| Calcul stabilité | 8 | 12 | Utiliser CV uniquement |
| Calcul trend | 10 | 15 | Ignorer trend |
| Analyse complète | 8 | 15 | Confiance réduite |

### **Code de Validation**

```python
def validate_sample_size(n_matches, analysis_type):
    thresholds = {
        "basic": 5,
        "variance": 8,
        "percentages": 10,
        "stability": 12,
        "trend": 15
    }
    
    min_required = thresholds.get(analysis_type, 5)
    
    if n_matches < min_required:
        return False, f"Insufficient data: {n_matches} < {min_required}"
    
    return True, "OK"
```

---

## 🎲 GESTION DES OUTLIERS

### **Détection**

```python
def detect_outliers(values):
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    outliers = [v for v in values if v < lower_bound or v > upper_bound]
    
    return outliers
```

### **Traitement**

**Option 1 : Exclusion** (recommandé si n > 15)

```python
def remove_outliers(values):
    outliers = detect_outliers(values)
    return [v for v in values if v not in outliers]
```

**Option 2 : Winsorization** (recommandé si n < 15)

```python
def winsorize(values, limits=(0.05, 0.05)):
    from scipy.stats.mstats import winsorize
    return winsorize(values, limits=limits)
```

---

## 🔄 MISE À JOUR DES STATISTIQUES

### **Fréquence Recommandée**

```python
UPDATE_FREQUENCY = {
    "after_each_match": ["avg_goals", "frequencies"],
    "daily": ["variance", "stability"],
    "weekly": ["league_averages", "percentiles"],
    "monthly": ["historical_patterns", "trends"]
}
```

### **Stratégie Incremental**

```python
def incremental_update(old_avg, old_n, new_value):
    """
    Mise à jour incrémentale de la moyenne
    Évite de recalculer sur tous les matchs
    """
    new_n = old_n + 1
    new_avg = (old_avg * old_n + new_value) / new_n
    
    return new_avg, new_n
```

---

## 📈 BACKTESTING

### **Validation des Indicateurs**

```python
def backtest_indicator(indicator_func, historical_matches):
    predictions = []
    actuals = []
    
    for match in historical_matches:
        # Prédiction
        pred = indicator_func(match)
        predictions.append(pred)
        
        # Résultat réel
        actual = match.actual_result
        actuals.append(actual)
    
    # Métriques
    accuracy = calculate_accuracy(predictions, actuals)
    brier_score = calculate_brier_score(predictions, actuals)
    
    return {
        "accuracy": accuracy,
        "brier_score": brier_score,
        "n_matches": len(historical_matches)
    }
```

---

## 🎯 CALIBRATION DES PROBABILITÉS

### **Vérification Calibration**

```python
def check_calibration(predicted_probs, actual_outcomes, n_bins=10):
    """
    Vérifier si probabilités prédites sont bien calibrées
    """
    bins = np.linspace(0, 1, n_bins + 1)
    
    for i in range(n_bins):
        bin_mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i+1])
        
        if bin_mask.sum() > 0:
            avg_predicted = predicted_probs[bin_mask].mean()
            avg_actual = actual_outcomes[bin_mask].mean()
            
            print(f"Bin {i}: Predicted {avg_predicted:.2%}, Actual {avg_actual:.2%}")
```

---

## 🔐 SÉCURITÉ & VALIDATION

### **Validation des Inputs**

```python
def validate_stats_input(avg_goals, variance, n_matches):
    # Vérifier valeurs positives
    if avg_goals < 0 or variance < 0 or n_matches < 0:
        raise ValueError("Values must be positive")
    
    # Vérifier cohérence
    if avg_goals > 15:
        raise ValueError("avg_goals too high (>15)")
    
    if variance > 50:
        raise ValueError("variance too high (>50)")
    
    # Vérifier minimum de données
    if n_matches < 3:
        raise ValueError("Insufficient matches (<3)")
    
    return True
```

---

## 💡 CONSEILS SPÉCIFIQUES LIGUES OBSCURES

### **1. Privilégier Home/Away Split**

```python
# TOUJOURS calculer séparément
home_stats = calculate_stats(team_id, split="home")
away_stats = calculate_stats(team_id, split="away")

# NE PAS utiliser stats "all" pour prédictions
```

### **2. Utiliser Negative Binomial par Défaut**

```python
# Ligues obscures → variance élevée
# Utiliser NBinom même si variance ≈ moyenne
distribution = "negative_binomial"
```

### **3. Augmenter Home Advantage Factor**

```python
# Ligues obscures → home advantage plus fort
home_factor = 1.30  # vs 1.15 en grandes ligues
```

### **4. Réduire Confiance en Trend**

```python
# Ligues obscures → trends moins fiables
if league_tier > 3:
    trend_weight = 0.05  # vs 0.15 en grandes ligues
```

### **5. Prioriser Données Récentes**

```python
# Ligues obscures → changements rapides
# Utiliser WMA avec decay élevé
wma = calculate_wma(values, decay_rate=0.15)  # vs 0.10
```

---

## 📊 MONITORING & LOGGING

### **Métriques à Tracker**

```python
METRICS_TO_TRACK = {
    "accuracy": "Précision des prédictions",
    "brier_score": "Qualité probabilités",
    "roi": "Retour sur investissement",
    "coverage": "% matchs analysés",
    "confidence_distribution": "Distribution confiance",
    "anomaly_hit_rate": "% anomalies correctes"
}
```

### **Logging Structure**

```python
import logging

logger.info({
    "event": "stats_calculated",
    "team_id": team_id,
    "n_matches": n_matches,
    "avg_goals": avg_goals,
    "confidence": confidence_level,
    "timestamp": datetime.utcnow()
})
```

---

## 🚨 RED FLAGS

### **Signaux d'Alerte**

```python
def check_red_flags(stats):
    red_flags = []
    
    # Variance extrême
    if stats['variance'] > 10:
        red_flags.append("EXTREME_VARIANCE")
    
    # CV très élevé
    if stats['cv'] > 1.5:
        red_flags.append("VERY_HIGH_CV")
    
    # Stabilité très faible
    if stats['stability'] < 0.2:
        red_flags.append("VERY_LOW_STABILITY")
    
    # Trend fort
    if abs(stats['trend']) > 0.3:
        red_flags.append("STRONG_TREND")
    
    # Données insuffisantes
    if stats['n_matches'] < 5:
        red_flags.append("INSUFFICIENT_DATA")
    
    return red_flags
```

---

## ✅ CHECKLIST PRÉ-ANALYSE

Avant d'analyser un match :

- [ ] Vérifier n_matches >= 5 pour chaque équipe
- [ ] Calculer stats home/away séparément
- [ ] Appliquer Bayesian smoothing si n < 10
- [ ] Vérifier variance (utiliser NBinom si élevée)
- [ ] Calculer league averages
- [ ] Appliquer home advantage factor
- [ ] Vérifier red flags
- [ ] Calculer confidence score
- [ ] Valider inputs
- [ ] Logger l'analyse

---

**Best practices optimisées pour ligues obscures avec faible volume de données.**
