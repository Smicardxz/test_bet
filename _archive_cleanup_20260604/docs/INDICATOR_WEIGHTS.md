# ⚖️ Pondération des Indicateurs par Marché

## 🎯 Système de Pondération Optimisé

### **Méthodologie**

Pondération basée sur :
1. **Corrélation historique** avec résultats réels
2. **Fiabilité** en faible volume de données
3. **Spécificité** aux ligues obscures
4. **Stabilité** de l'indicateur

---

## 📊 OVER/UNDER 2.5 GOALS

### **Pondération Recommandée**

| Indicateur | Poids | Justification |
|------------|-------|---------------|
| `avg_goals_ft` | 30% | Base fondamentale, très corrélé |
| `avg_goals_scored + avg_goals_conceded` | 25% | Capacité offensive/défensive combinée |
| `over_25_pct` (historique) | 20% | Pattern historique direct |
| `variance_goals` | 15% | Prévisibilité des scores |
| `stability_score` | 10% | Confiance dans la prédiction |

### **Formule de Calcul**

```python
def calculate_over_25_probability(team_stats, opponent_stats):
    # Extraction des stats
    avg_goals = (team_stats['avg_goals_ft'] + opponent_stats['avg_goals_ft']) / 2
    combined_attack = team_stats['avg_goals_scored'] + opponent_stats['avg_goals_scored']
    combined_defense = team_stats['avg_goals_conceded'] + opponent_stats['avg_goals_conceded']
    historical_over = (team_stats['over_25_pct'] + opponent_stats['over_25_pct']) / 2
    variance = (team_stats['variance_total_goals'] + opponent_stats['variance_total_goals']) / 2
    stability = (team_stats['stability_score'] + opponent_stats['stability_score']) / 2
    
    # Normalisation (0-1)
    norm_avg_goals = min(avg_goals / 4.0, 1.0)  # 4 buts = max
    norm_attack_defense = min((combined_attack + combined_defense) / 8.0, 1.0)
    norm_historical = historical_over / 100
    norm_variance = 1 - min(variance / 5.0, 1.0)  # variance élevée = moins fiable
    norm_stability = stability
    
    # Pondération
    weighted_prob = (
        norm_avg_goals * 0.30 +
        norm_attack_defense * 0.25 +
        norm_historical * 0.20 +
        norm_variance * 0.15 +
        norm_stability * 0.10
    )
    
    return weighted_prob
```

### **Ajustements Ligues Obscures**

```python
# Bonus variance élevée (ligues obscures = plus de buts)
if variance > 3.0:
    weighted_prob *= 1.1

# Bonus défenses faibles
if combined_defense > 3.5:
    weighted_prob *= 1.15

# Malus stabilité faible
if stability < 0.4:
    weighted_prob *= 0.9
```

---

## 🎲 BOTH TEAMS TO SCORE (BTTS)

### **Pondération Recommandée**

| Indicateur | Poids | Justification |
|------------|-------|---------------|
| `btts_pct` (historique) | 35% | Pattern direct le plus fiable |
| `avg_goals_scored` (both teams) | 25% | Capacité offensive |
| `clean_sheet_pct` (inverse) | 20% | Solidité défensive inverse |
| `avg_goals_conceded` (both teams) | 15% | Faiblesse défensive |
| `stability_score` | 5% | Confiance |

### **Formule de Calcul**

```python
def calculate_btts_probability(home_stats, away_stats):
    # Stats BTTS historiques
    btts_historical = (home_stats['btts_pct'] + away_stats['btts_pct']) / 2
    
    # Capacité offensive
    attack_home = home_stats['avg_goals_scored']
    attack_away = away_stats['avg_goals_scored']
    both_can_score = min((attack_home + attack_away) / 3.0, 1.0)  # 3 = seuil
    
    # Faiblesse défensive
    defense_home = home_stats['avg_goals_conceded']
    defense_away = away_stats['avg_goals_conceded']
    both_concede = min((defense_home + defense_away) / 3.0, 1.0)
    
    # Clean sheets (inverse)
    cs_home = home_stats['clean_sheet_pct']
    cs_away = away_stats['clean_sheet_pct']
    no_clean_sheets = 1 - ((cs_home + cs_away) / 200)
    
    # Stabilité
    stability = (home_stats['stability_score'] + away_stats['stability_score']) / 2
    
    # Pondération
    weighted_prob = (
        (btts_historical / 100) * 0.35 +
        both_can_score * 0.25 +
        no_clean_sheets * 0.20 +
        both_concede * 0.15 +
        stability * 0.05
    )
    
    return weighted_prob
```

### **Ajustements Ligues Obscures**

```python
# Bonus défenses faibles (typique ligues obscures)
if (defense_home + defense_away) > 3.5:
    weighted_prob *= 1.2

# Bonus si les deux équipes marquent régulièrement
if attack_home > 1.2 and attack_away > 1.0:
    weighted_prob *= 1.1

# Malus clean sheets fréquents
if (cs_home + cs_away) > 60:
    weighted_prob *= 0.85
```

---

## 🕐 OVER/UNDER HALF TIME

### **Pondération Recommandée**

| Indicateur | Poids | Justification |
|------------|-------|---------------|
| `avg_goals_ht` | 35% | Moyenne HT directe |
| `over_x_ht_pct` (historique) | 30% | Pattern HT historique |
| `ht_ft_ratio` | 20% | Ratio HT/FT |
| `zero_zero_ht_pct` | 10% | Fréquence 0-0 HT |
| `early_goal_pct` | 5% | Démarrage rapide |

### **Formule de Calcul**

```python
def calculate_over_ht_probability(home_stats, away_stats, line=1.5):
    # Moyenne HT
    avg_ht = (home_stats['avg_goals_ht'] + away_stats['avg_goals_ht']) / 2
    norm_avg_ht = min(avg_ht / 2.0, 1.0)  # 2 buts HT = max
    
    # Historique Over HT
    if line == 0.5:
        historical = (home_stats['over_05_ht_pct'] + away_stats['over_05_ht_pct']) / 2
    elif line == 1.5:
        historical = (home_stats['over_15_ht_pct'] + away_stats['over_15_ht_pct']) / 2
    else:
        historical = 50  # default
    
    norm_historical = historical / 100
    
    # Ratio HT/FT
    ht_ft = (home_stats['ht_ft_ratio'] + away_stats['ht_ft_ratio']) / 2
    norm_ratio = min(ht_ft / 0.5, 1.0)  # 0.5 = ratio élevé
    
    # 0-0 HT (inverse)
    zero_zero = (home_stats['zero_zero_ht_pct'] + away_stats['zero_zero_ht_pct']) / 2
    norm_zero_zero = 1 - (zero_zero / 100)
    
    # Early goals (si disponible)
    early_goals = 0.5  # default si pas de données
    
    # Pondération
    weighted_prob = (
        norm_avg_ht * 0.35 +
        norm_historical * 0.30 +
        norm_ratio * 0.20 +
        norm_zero_zero * 0.10 +
        early_goals * 0.05
    )
    
    return weighted_prob
```

---

## 🔢 OVER/UNDER 3.5 GOALS

### **Pondération Recommandée**

| Indicateur | Poids | Justification |
|------------|-------|---------------|
| `avg_goals_ft` | 35% | Base fondamentale |
| `over_35_pct` (historique) | 25% | Pattern direct |
| `variance_goals` | 20% | Variance élevée favorise Over |
| `attack_strength` (combined) | 15% | Capacité offensive |
| `defense_weakness` (combined) | 5% | Faiblesse défensive |

### **Formule de Calcul**

```python
def calculate_over_35_probability(home_stats, away_stats):
    # Moyenne buts
    avg_goals = (home_stats['avg_goals_ft'] + away_stats['avg_goals_ft']) / 2
    norm_avg = min(avg_goals / 4.5, 1.0)
    
    # Historique
    historical = (home_stats['over_35_pct'] + away_stats['over_35_pct']) / 2
    norm_historical = historical / 100
    
    # Variance (élevée = plus de buts potentiels)
    variance = (home_stats['variance_total_goals'] + away_stats['variance_total_goals']) / 2
    norm_variance = min(variance / 4.0, 1.0)
    
    # Attack strength
    attack = home_stats['avg_goals_scored'] + away_stats['avg_goals_scored']
    norm_attack = min(attack / 4.0, 1.0)
    
    # Defense weakness
    defense = home_stats['avg_goals_conceded'] + away_stats['avg_goals_conceded']
    norm_defense = min(defense / 4.0, 1.0)
    
    weighted_prob = (
        norm_avg * 0.35 +
        norm_historical * 0.25 +
        norm_variance * 0.20 +
        norm_attack * 0.15 +
        norm_defense * 0.05
    )
    
    return weighted_prob
```

---

## 🎯 UNDER EXTRÊMES (5.5+, 8.5+, 10.5+)

### **Pondération Recommandée**

| Indicateur | Poids | Justification |
|------------|-------|---------------|
| `negative_binomial_prob` | 40% | Distribution adaptée variance |
| `avg_goals_ft` | 25% | Moyenne élevée nécessaire |
| `variance_goals` | 20% | Variance critique |
| `max_goals_observed` | 10% | Historique extrêmes |
| `league_tier` | 5% | Ligues amateurs = plus de buts |

### **Formule de Calcul**

```python
def calculate_extreme_over_probability(home_stats, away_stats, line=5.5):
    # Expected goals
    xg = (home_stats['avg_goals_ft'] + away_stats['avg_goals_ft']) / 2
    
    # Variance
    variance = (home_stats['variance_total_goals'] + away_stats['variance_total_goals']) / 2
    
    # Negative Binomial (si overdispersion)
    if variance > xg:
        r = xg**2 / (variance - xg)
        p = xg / variance
        prob_under = nbinom.cdf(int(line), r, 1-p)
        prob_over = 1 - prob_under
    else:
        # Poisson
        prob_over = 1 - poisson.cdf(int(line), xg)
    
    # Ajustement historique
    max_goals = max(
        home_stats.get('max_goals_observed', 0),
        away_stats.get('max_goals_observed', 0)
    )
    
    if max_goals > line:
        historical_bonus = 0.1
    else:
        historical_bonus = 0
    
    # Bonus ligues amateurs
    league_bonus = 0.05 if is_amateur_league else 0
    
    final_prob = prob_over + historical_bonus + league_bonus
    
    return min(final_prob, 0.95)  # cap à 95%
```

---

## 🏠 HOME/AWAY ADJUSTMENTS

### **Home Advantage Factors**

```python
HOME_ADVANTAGE_FACTORS = {
    "major_leagues": 1.15,      # Premier League, etc.
    "obscure_leagues": 1.30,    # Ligues obscures
    "amateur_leagues": 1.40,    # Ligues amateurs
    "regional_leagues": 1.50    # Ligues régionales
}

def apply_home_advantage(xg_home, xg_away, league_type="obscure_leagues"):
    factor = HOME_ADVANTAGE_FACTORS.get(league_type, 1.30)
    
    xg_home_adjusted = xg_home * factor
    xg_away_adjusted = xg_away / (factor ** 0.5)
    
    return xg_home_adjusted, xg_away_adjusted
```

---

## 📉 CONFIDENCE WEIGHTING

### **Ajustement selon Volume de Données**

```python
def apply_confidence_weighting(probability, n_matches, min_matches=10):
    if n_matches >= min_matches:
        confidence = 1.0
    else:
        confidence = n_matches / min_matches
    
    # Régression vers 50% si faible confiance
    adjusted_prob = probability * confidence + 0.5 * (1 - confidence)
    
    return adjusted_prob, confidence
```

---

## 🔄 BAYESIAN SMOOTHING

### **Application par Indicateur**

```python
BAYESIAN_K_VALUES = {
    "avg_goals": 5,
    "btts_pct": 8,
    "over_25_pct": 6,
    "variance": 10,
    "clean_sheet_pct": 7
}

def bayesian_smooth(team_stat, league_stat, n_matches, stat_type):
    k = BAYESIAN_K_VALUES.get(stat_type, 5)
    
    smoothed = (n_matches * team_stat + k * league_stat) / (n_matches + k)
    
    return smoothed
```

---

## 📊 EXEMPLE COMPLET : CALCUL OVER 2.5

```python
def full_over_25_calculation(home_team_id, away_team_id, league):
    # 1. Récupérer stats équipes
    home_stats = get_team_stats(home_team_id, split="home")
    away_stats = get_team_stats(away_team_id, split="away")
    league_stats = get_league_stats(league)
    
    # 2. Bayesian smoothing si faible volume
    if home_stats['n_matches'] < 10:
        home_stats['avg_goals_ft'] = bayesian_smooth(
            home_stats['avg_goals_ft'],
            league_stats['avg_goals_ft'],
            home_stats['n_matches'],
            "avg_goals"
        )
    
    if away_stats['n_matches'] < 10:
        away_stats['avg_goals_ft'] = bayesian_smooth(
            away_stats['avg_goals_ft'],
            league_stats['avg_goals_ft'],
            away_stats['n_matches'],
            "avg_goals"
        )
    
    # 3. Calculer probabilité pondérée
    prob = calculate_over_25_probability(home_stats, away_stats)
    
    # 4. Appliquer home advantage
    xg_home = home_stats['avg_goals_scored']
    xg_away = away_stats['avg_goals_scored']
    xg_home_adj, xg_away_adj = apply_home_advantage(xg_home, xg_away, "obscure_leagues")
    
    # 5. Ajuster selon confiance
    min_matches = min(home_stats['n_matches'], away_stats['n_matches'])
    prob_adjusted, confidence = apply_confidence_weighting(prob, min_matches)
    
    # 6. Retourner résultat
    return {
        "probability_over_25": prob_adjusted,
        "confidence": confidence,
        "xg_total": xg_home_adj + xg_away_adj,
        "home_stats": home_stats,
        "away_stats": away_stats
    }
```

---

## 🎯 RÉSUMÉ : TOP INDICATEURS PAR IMPORTANCE

### **Rang S-Tier** (Indispensables)
1. `avg_goals_ft`
2. `avg_goals_scored` (home/away)
3. `avg_goals_conceded` (home/away)
4. `over_25_pct` / `under_25_pct`
5. `btts_pct`

### **Rang A-Tier** (Très Importants)
6. `variance_total_goals`
7. `stability_score`
8. `avg_goals_ht`
9. `over_35_pct`
10. `clean_sheet_pct`

### **Rang B-Tier** (Importants)
11. `ht_ft_ratio`
12. `zero_zero_ht_pct`
13. `over_15_ht_pct`
14. `cv_total`
15. `attack_strength` / `defense_strength`

### **Rang C-Tier** (Secondaires)
16. Under/Over extrêmes (5.5+)
17. Early/Late goals (si disponible)
18. Trend coefficient
19. Weighted moving average
20. Z-score anomalies

---

**Système de pondération optimisé pour ligues obscures avec faible volume de données.**
