# ⚽ Système Spécialisé First Half (Mi-Temps)

## 🎯 Vue d'Ensemble

Système complet d'analyse des marchés **First Half** pour détecter anomalies bookmaker sur ligues obscures.

### **Marchés Analysés**

| Marché | Description | Exploitabilité |
|--------|-------------|----------------|
| **HT Under 0.5** | 0-0 à la mi-temps | ⭐⭐⭐⭐⭐ |
| **HT Under 1.5** | 0 ou 1 but HT | ⭐⭐⭐⭐ |
| **HT Over 0.5** | Au moins 1 but HT | ⭐⭐⭐⭐ |
| **HT Over 1.5** | Au moins 2 buts HT | ⭐⭐⭐ |
| **HT BTTS** | Both Teams Score HT | ⭐⭐⭐ |
| **HT 0-0** | Score exact 0-0 | ⭐⭐⭐⭐⭐ |

---

## 📊 INDICATEURS FIRST HALF (25 indicateurs)

### **Catégorie 1 : Moyennes** (3 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 1 | avg_goals_ht | Σ(goals_ht) / n | ⭐⭐⭐⭐⭐ |
| 2 | avg_goals_scored_ht | Σ(goals_scored_ht) / n | ⭐⭐⭐⭐ |
| 3 | avg_goals_conceded_ht | Σ(goals_conceded_ht) / n | ⭐⭐⭐⭐ |

---

### **Catégorie 2 : Fréquences Under/Over** (6 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 4 | under_05_ht_pct | count(ht==0) / n × 100 | ⭐⭐⭐⭐⭐ |
| 5 | under_15_ht_pct | count(ht<1.5) / n × 100 | ⭐⭐⭐⭐⭐ |
| 6 | under_25_ht_pct | count(ht<2.5) / n × 100 | ⭐⭐⭐ |
| 7 | over_05_ht_pct | 100 - under_05 | ⭐⭐⭐⭐⭐ |
| 8 | over_15_ht_pct | 100 - under_15 | ⭐⭐⭐⭐ |
| 9 | over_25_ht_pct | 100 - under_25 | ⭐⭐⭐ |

---

### **Catégorie 3 : Scores Exacts HT** (4 indicateurs)

| # | Indicateur | Description | Importance |
|---|------------|-------------|------------|
| 10 | zero_zero_ht_pct | Fréquence 0-0 HT | ⭐⭐⭐⭐⭐ |
| 11 | one_zero_ht_pct | Fréquence 1-0 ou 0-1 HT | ⭐⭐⭐ |
| 12 | one_one_ht_pct | Fréquence 1-1 HT | ⭐⭐⭐ |
| 13 | two_zero_ht_pct | Fréquence 2-0 ou 0-2 HT | ⭐⭐ |

---

### **Catégorie 4 : BTTS HT** (2 indicateurs)

| # | Indicateur | Description | Importance |
|---|------------|-------------|------------|
| 14 | btts_ht_pct | % BTTS en HT | ⭐⭐⭐⭐ |
| 15 | no_btts_ht_pct | % pas de BTTS en HT | ⭐⭐⭐ |

---

### **Catégorie 5 : Early Goals** (4 indicateurs)

| # | Indicateur | Description | Importance |
|---|------------|-------------|------------|
| 16 | goals_before_15_avg | Moyenne buts avant 15min | ⭐⭐ |
| 17 | goals_before_30_avg | Moyenne buts avant 30min | ⭐⭐⭐ |
| 18 | early_goal_15_pct | % matchs avec but avant 15min | ⭐⭐ |
| 19 | early_goal_30_pct | % matchs avec but avant 30min | ⭐⭐⭐ |

**Note** : Données minute-by-minute rarement disponibles en ligues obscures

---

### **Catégorie 6 : Rythme Offensif** (2 indicateurs)

| # | Indicateur | Description | Importance |
|---|------------|-------------|------------|
| 20 | offensive_pace | VERY_FAST / FAST / MODERATE / SLOW / VERY_SLOW | ⭐⭐⭐⭐ |
| 21 | pace_score | Score 0-1 (0=lent, 1=rapide) | ⭐⭐⭐⭐ |

**Formule Pace Score** :
```python
pace_score = (avg_goals_ht / 2.0) × 0.6 + (over_05_ht_pct / 100) × 0.4
```

**Classification** :
- **VERY_FAST** : pace_score ≥ 0.70
- **FAST** : pace_score ≥ 0.55
- **MODERATE** : pace_score ≥ 0.40
- **SLOW** : pace_score ≥ 0.25
- **VERY_SLOW** : pace_score < 0.25

---

### **Catégorie 7 : Variance & Stabilité** (4 indicateurs)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 22 | variance_ht | Σ(x - μ)² / n | ⭐⭐⭐⭐ |
| 23 | std_dev_ht | √variance | ⭐⭐⭐ |
| 24 | cv_ht | σ / μ | ⭐⭐⭐⭐ |
| 25 | stability_ht | 1 / (1 + CV) | ⭐⭐⭐⭐ |

---

### **Catégorie 8 : Tendances** (2 indicateurs)

| # | Indicateur | Condition | Importance |
|---|------------|-----------|------------|
| 26 | is_slow_starter | avg_ht < 0.8 ET zero_zero > 40% | ⭐⭐⭐⭐⭐ |
| 27 | is_fast_starter | avg_ht > 1.2 ET over_05 > 70% | ⭐⭐⭐⭐⭐ |

---

### **Catégorie 9 : Ratios** (1 indicateur)

| # | Indicateur | Formule | Importance |
|---|------------|---------|------------|
| 28 | ht_ft_ratio | avg_goals_ht / avg_goals_ft | ⭐⭐⭐⭐ |

**Valeurs typiques** :
- Ligues obscures : 0.35-0.45
- Grandes ligues : 0.38-0.42

---

## 🎯 TOP 10 INDICATEURS FIRST HALF

### **Rang 1-5 : CRITIQUES** ⭐⭐⭐⭐⭐

1. **avg_goals_ht** - Base pour tous les marchés HT
2. **under_05_ht_pct** - Marché 0-0 HT (très exploitable)
3. **under_15_ht_pct** - Marché Under 1.5 HT
4. **over_05_ht_pct** - Marché Over 0.5 HT
5. **zero_zero_ht_pct** - Score exact 0-0 (très exploitable)

### **Rang 6-10 : TRÈS IMPORTANTS** ⭐⭐⭐⭐

6. **is_slow_starter** - Détection équipes lentes
7. **is_fast_starter** - Détection équipes rapides
8. **offensive_pace** - Classification rythme
9. **pace_score** - Score rythme quantifié
10. **variance_ht** - Prévisibilité HT

---

## 🔔 SIGNAUX D'ANOMALIE FIRST HALF

### **Signal 1 : EXTREME_PROBABILITY_GAP**

**Condition** : `|P_bookmaker - P_model| > 25%`

**Exemple** :
```
Bookmaker: 0-0 HT @ 2.00 (50%)
Modèle: 0-0 HT → 75%
Gap: 25% → SIGNAL FORT
```

---

### **Signal 2 : BOTH_SLOW_STARTERS**

**Condition** : Les deux équipes sont slow starters

**Critères** :
- avg_goals_ht < 0.8
- zero_zero_ht_pct > 40%

**Implication** : **Forte probabilité 0-0 HT**

---

### **Signal 3 : FAST_STARTER_PRESENT**

**Condition** : Au moins une équipe est fast starter

**Critères** :
- avg_goals_ht > 1.2
- over_05_ht_pct > 70%

**Implication** : **Forte probabilité Over 0.5 HT**

---

### **Signal 4 : HIGH_ZERO_ZERO_FREQUENCY**

**Condition** : Fréquence 0-0 HT > 50%

**Exemple** :
```
Home: 55% de 0-0 HT
Away: 60% de 0-0 HT
Moyenne: 57.5% → SIGNAL FORT
```

---

### **Signal 5 : LOW_VARIANCE_HT**

**Condition** : Variance HT < 0.5

**Implication** : Scores HT très prévisibles

---

### **Signal 6 : CONSISTENT_PACE**

**Condition** : `|pace_home - pace_away| < 0.15`

**Implication** : Rythme similaire → prédiction fiable

---

## 📊 SCORING FIRST HALF (0-100)

### **Composition**

| Sous-Score | Points | Description |
|------------|--------|-------------|
| **Probability Gap** | 35 | Écart probabilités |
| **Historical Pattern** | 30 | Patterns historiques |
| **Pace Consistency** | 20 | Consistance rythme |
| **Stability** | 15 | Stabilité équipes |
| **TOTAL** | **100** | Score anomalie HT |

---

### **Formule 1 : Probability Gap Score** (Max: 35)

```python
score = (prob_gap × 100) × multiplier

multiplier = {
    1.0  si gap > 30%
    0.85 si gap > 20%
    0.7  si gap > 15%
    0.5  si gap > 10%
    0.3  sinon
}
```

---

### **Formule 2 : Historical Pattern Score** (Max: 30)

```python
# Fréquence historique du marché
avg_freq = (home_freq × 0.6) + (away_freq × 0.4)

# Consistance
consistency = 1 - (|home_freq - away_freq| / 100)

# Score
base_score = (avg_freq / 100) × 20
consistency_bonus = consistency × 10

score = base_score + consistency_bonus
```

**Exemple** :
```
Marché: 0-0 HT
Home: 60% de 0-0 HT
Away: 55% de 0-0 HT

avg_freq = (60 × 0.6) + (55 × 0.4) = 58%
consistency = 1 - (|60-55| / 100) = 0.95

base_score = (58 / 100) × 20 = 11.6
consistency_bonus = 0.95 × 10 = 9.5

score = 11.6 + 9.5 = 21.1 points
```

---

### **Formule 3 : Pace Consistency Score** (Max: 20)

```python
pace_score = combined_pace_score
pace_diff = |home_pace - away_pace|
pace_consistency = 1 - pace_diff

# Selon marché
if marché in [UNDER_05, ZERO_ZERO]:
    # Marchés "lents"
    if pace_score < 0.4:
        base_score = (1 - pace_score) × 15
    else:
        base_score = 5
        
elif marché in [OVER_05, OVER_15]:
    # Marchés "rapides"
    if pace_score > 0.6:
        base_score = pace_score × 15
    else:
        base_score = 5

consistency_bonus = pace_consistency × 5

score = base_score + consistency_bonus
```

---

### **Formule 4 : Stability Score** (Max: 15)

```python
avg_stability = (stability_home + stability_away) / 2

sample_quality = {
    1.0  si n ≥ 15
    0.8  si n ≥ 10
    0.6  si n ≥ 5
    0.3  si n < 5
}

score = avg_stability × sample_quality × 15
```

---

## 🎯 MARCHÉS LES PLUS EXPLOITABLES

### **1. HT Under 0.5 (0-0 HT)** ⭐⭐⭐⭐⭐

**Pourquoi exploitable** :
- Ligues obscures : 0-0 HT fréquent (35-50%)
- Bookmakers sous-estiment souvent
- Équipes slow starters = opportunité

**Indicateurs clés** :
- zero_zero_ht_pct > 50%
- is_slow_starter (both teams)
- avg_goals_ht < 0.8
- pace_score < 0.3

**Exemple** :
```
Home: 55% de 0-0 HT, pace 0.25 (VERY_SLOW)
Away: 60% de 0-0 HT, pace 0.28 (VERY_SLOW)

Bookmaker: 0-0 HT @ 2.50 (40%)
Modèle: 0-0 HT → 70%

Anomaly Score: 85/100 (EXTREME)
```

---

### **2. HT Under 1.5** ⭐⭐⭐⭐

**Pourquoi exploitable** :
- Marché populaire
- Typiquement 60-75% en ligues obscures
- Bon ratio risque/rendement

**Indicateurs clés** :
- under_15_ht_pct > 70%
- avg_goals_ht < 1.0
- variance_ht < 0.6

---

### **3. HT Over 0.5** ⭐⭐⭐⭐

**Pourquoi exploitable** :
- Inverse du 0-0 HT
- Fast starters = opportunité
- Bookmakers surestiment parfois

**Indicateurs clés** :
- over_05_ht_pct > 70%
- is_fast_starter (au moins 1 équipe)
- avg_goals_ht > 1.2

---

### **4. HT BTTS** ⭐⭐⭐

**Pourquoi exploitable** :
- Moins fréquent que FT BTTS
- Typiquement 20-35% en HT
- Défenses faibles en ligues obscures

**Indicateurs clés** :
- btts_ht_pct > 35%
- avg_goals_scored_ht > 0.6 (both teams)

---

## 📋 STRUCTURE JSON DE SORTIE

```json
{
  "total_score": 85.3,
  "level": "EXTREME",
  "market_type": "HT_UNDER_05",
  "scores": {
    "probability_gap": 32.5,
    "historical_pattern": 28.0,
    "pace_consistency": 18.0,
    "stability": 6.8
  },
  "probabilities": {
    "bookmaker": 0.4000,
    "model": 0.7200,
    "gap": 0.3200
  },
  "signals": [
    {
      "type": "EXTREME_PROBABILITY_GAP",
      "strength": "STRONG",
      "description": "Écart de probabilité extrême: 32.0%",
      "value": 0.320
    },
    {
      "type": "BOTH_SLOW_STARTERS",
      "strength": "STRONG",
      "description": "Les deux équipes démarrent lentement",
      "value": 57.5
    },
    {
      "type": "HIGH_ZERO_ZERO_FREQUENCY",
      "strength": "STRONG",
      "description": "Fréquence 0-0 HT élevée: 57.5%",
      "value": 57.5
    },
    {
      "type": "CONSISTENT_PACE",
      "strength": "MEDIUM",
      "description": "Rythme similaire entre équipes",
      "value": 0.92
    }
  ],
  "key_indicators": {
    "expected_goals_ht": 0.75,
    "home_avg_ht": 0.72,
    "away_avg_ht": 0.68,
    "home_zero_zero_pct": 55.0,
    "away_zero_zero_pct": 60.0,
    "home_over_05_pct": 45.0,
    "away_over_05_pct": 40.0,
    "home_pace_score": 0.25,
    "away_pace_score": 0.28,
    "combined_pace": 0.265,
    "home_stability": 0.78,
    "away_stability": 0.82,
    "home_variance": 0.45,
    "away_variance": 0.38
  },
  "explanation": "🎯 MARCHÉ: HT_UNDER_05\n📊 Probabilité Bookmaker: 40.00%\n🎲 Probabilité Modèle: 72.00%\n⚠️ Gap: 32.00%\n\n⚽ Expected Goals HT: 0.75\n🏠 Home avg HT: 0.72\n✈️ Away avg HT: 0.68\n\n📊 0-0 HT: Home 55.0% | Away 60.0%\n📈 Over 0.5 HT: Home 45.0% | Away 40.0%\n\n⚡ Rythme: Home VERY_SLOW | Away VERY_SLOW\n📊 Pace Score: 0.27\n\n🔔 SIGNAUX:\n  • [STRONG] Écart de probabilité extrême: 32.0%\n  • [STRONG] Les deux équipes démarrent lentement\n  • [STRONG] Fréquence 0-0 HT élevée: 57.5%\n  • [MEDIUM] Rythme similaire entre équipes",
  "recommendation": "✅ FORTE ANOMALIE - Opportunité potentielle sur HT_UNDER_05"
}
```

---

## 💻 UTILISATION

```python
from app.services.stats_engine import FirstHalfStatsCalculator
from app.services.anomaly_engine import FirstHalfAnomalyDetector, HTMarketType

# Calculer stats HT
ht_calculator = FirstHalfStatsCalculator(db)

home_stats = ht_calculator.calculate_first_half_stats(
    team_id=1,
    home_away_split="home"
)

# Détecter anomalie
detector = FirstHalfAnomalyDetector(db)

anomaly = detector.detect_ht_anomaly(
    home_team_id=1,
    away_team_id=2,
    market_type=HTMarketType.HT_UNDER_05,
    bookmaker_odds=2.50
)

# Afficher résultats
print(f"Score: {anomaly.total_score}/100")
print(f"Niveau: {anomaly.level}")
print(anomaly.explanation)

# Export JSON
json_output = anomaly.to_json()
print(json_output)
```

---

## 🎯 EXEMPLES CONCRETS

### **Exemple 1 : 0-0 HT (Anomalie EXTREME)**

**Contexte** :
```
Match: Team A vs Team B
Marché: 0-0 HT @ 2.50 (40% implied)

Team A (home):
- avg_goals_ht: 0.72
- zero_zero_ht_pct: 55%
- pace: VERY_SLOW (0.25)
- is_slow_starter: True

Team B (away):
- avg_goals_ht: 0.68
- zero_zero_ht_pct: 60%
- pace: VERY_SLOW (0.28)
- is_slow_starter: True
```

**Analyse** :
```
Expected goals HT: 0.75
Model prob 0-0: 72%
Bookmaker prob: 40%
Gap: 32%

Score: 85/100 → EXTREME
```

**Signaux** :
- ✅ EXTREME_PROBABILITY_GAP (32%)
- ✅ BOTH_SLOW_STARTERS
- ✅ HIGH_ZERO_ZERO_FREQUENCY (57.5%)
- ✅ CONSISTENT_PACE

**Recommandation** : **FORTE OPPORTUNITÉ sur 0-0 HT**

---

### **Exemple 2 : Over 0.5 HT (Anomalie HIGH)**

**Contexte** :
```
Match: Team C vs Team D
Marché: Over 0.5 HT @ 1.80 (55% implied)

Team C (home):
- avg_goals_ht: 1.35
- over_05_ht_pct: 75%
- pace: FAST (0.62)
- is_fast_starter: True

Team D (away):
- avg_goals_ht: 0.95
- over_05_ht_pct: 60%
- pace: MODERATE (0.48)
```

**Analyse** :
```
Expected goals HT: 1.25
Model prob Over 0.5: 78%
Bookmaker prob: 55%
Gap: 23%

Score: 68/100 → VERY_HIGH
```

**Recommandation** : **Opportunité sur Over 0.5 HT**

---

**Système complet First Half avec 28 indicateurs, 6 signaux, scoring 0-100 et export JSON.**
