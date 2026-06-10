# 🎯 Système de Détection d'Anomalies Bookmaker

## 📊 Vue d'Ensemble

Le système compare les **lignes bookmakers** avec la **réalité statistique** des équipes pour détecter des incohérences et opportunités.

### **Objectif**

Identifier quand une ligne bookmaker est **statistiquement incohérente** avec les données historiques et les probabilités calculées.

---

## 🔢 Anomaly Score (0-100)

### **Composition du Score**

Le score total est composé de **4 sous-scores** :

| Sous-Score | Points Max | Description |
|------------|-----------|-------------|
| **Bookmaker Gap Score** | 30 | Écart probabilités bookmaker vs modèle |
| **Variance Safety Score** | 25 | Sécurité de la ligne vs variance |
| **Historical Breach Score** | 25 | Fréquence dépassement historique |
| **Stability Score** | 20 | Stabilité des équipes |
| **TOTAL** | **100** | Score d'anomalie total |

### **Niveaux d'Anomalie**

```python
EXTREME    : score >= 80  # Anomalie extrême
VERY_HIGH  : score >= 60  # Anomalie très forte
HIGH       : score >= 40  # Anomalie forte
MEDIUM     : score >= 20  # Anomalie modérée
LOW        : score < 20   # Anomalie faible
```

---

## 📐 FORMULE 1 : Bookmaker Gap Score

### **Objectif**

Mesurer l'écart entre les probabilités implicites du bookmaker et les probabilités calculées par le modèle.

### **Formule Mathématique**

```
bookmaker_gap_score = (prob_gap × 100) × multiplier

où :
prob_gap = max(|P_bk_over - P_model_over|, |P_bk_under - P_model_under|)

multiplier = {
    1.0  si prob_gap > 0.30 (30%)
    0.8  si prob_gap > 0.20 (20%)
    0.6  si prob_gap > 0.15 (15%)
    0.4  si prob_gap > 0.10 (10%)
    0.2  si prob_gap ≤ 0.10
}

Max: 30 points
```

### **Logique Métier**

1. **Conversion cotes → probabilités**
   ```python
   P_bookmaker = 1 / cote
   ```

2. **Calcul probabilité modèle**
   - Si variance > moyenne : **Negative Binomial**
   - Sinon : **Poisson**

3. **Calcul gap**
   - Prendre le maximum entre gap Over et gap Under
   - Plus le gap est élevé, plus l'anomalie est forte

### **Exemple**

```
Bookmaker: Over 12.5 @ 2.00 → P = 50%
Modèle:    Over 12.5 → P = 5%

prob_gap = |0.50 - 0.05| = 0.45 (45%)
multiplier = 1.0 (gap > 30%)

bookmaker_gap_score = (0.45 × 100) × 1.0 = 45 points
→ Mais max = 30, donc score = 30 points
```

### **Code**

```python
def _calculate_bookmaker_gap_score(
    bookmaker_prob_over, bookmaker_prob_under,
    model_prob_over, model_prob_under
):
    prob_gap = max(
        abs(bookmaker_prob_over - model_prob_over),
        abs(bookmaker_prob_under - model_prob_under)
    )
    
    if prob_gap > 0.30:
        multiplier = 1.0
    elif prob_gap > 0.20:
        multiplier = 0.8
    elif prob_gap > 0.15:
        multiplier = 0.6
    elif prob_gap > 0.10:
        multiplier = 0.4
    else:
        multiplier = 0.2
    
    score = (prob_gap * 100) * multiplier
    return min(score, 30.0)
```

---

## 📐 FORMULE 2 : Variance Safety Score

### **Objectif**

Évaluer si la ligne est "sûre" compte tenu de la variance des scores.

### **Formule Mathématique**

```
variance_safety_score = line_safety × variance_factor × consistency_bonus × 25

où :

line_safety = f(σ_distance)
σ_distance = |line - expected_goals| / σ

σ_distance > 3.0 → line_safety = 1.0
σ_distance > 2.5 → line_safety = 0.85
σ_distance > 2.0 → line_safety = 0.7
σ_distance > 1.5 → line_safety = 0.5
σ_distance > 1.0 → line_safety = 0.3
σ_distance ≤ 1.0 → line_safety = 0.1

variance_factor = f(CV_avg)
CV_avg < 0.3 → variance_factor = 1.0  (très stable)
CV_avg < 0.5 → variance_factor = 0.8
CV_avg < 0.7 → variance_factor = 0.6
CV_avg ≥ 0.7 → variance_factor = 0.4  (instable)

consistency_bonus = f(stability_avg)
stability_avg > 0.7 → consistency_bonus = 1.2
stability_avg > 0.5 → consistency_bonus = 1.0
stability_avg ≤ 0.5 → consistency_bonus = 0.8

Max: 25 points
```

### **Logique Métier**

1. **Line Safety** : Plus la ligne est éloignée de l'expected (en nombre de σ), plus elle est "sûre"
   - Ligne à 3σ de l'expected = très peu probable d'être atteinte
   - Si bookmaker propose cette ligne → anomalie potentielle

2. **Variance Factor** : Variance faible = scores prévisibles
   - Si variance faible ET ligne extrême → anomalie forte

3. **Consistency Bonus** : Équipes stables = prédictions fiables
   - Bonus si les deux équipes sont stables

### **Exemple**

```
Expected goals: 2.5
Variance: 1.5
Std dev (σ): 1.22
Bookmaker line: 12.5

σ_distance = |12.5 - 2.5| / 1.22 = 8.2
→ line_safety = 1.0 (très éloigné)

CV_avg = 0.4
→ variance_factor = 0.8

stability_avg = 0.75
→ consistency_bonus = 1.2

variance_safety_score = 1.0 × 0.8 × 1.2 × 25 = 24 points
```

### **Code**

```python
def _calculate_variance_safety_score(
    bookmaker_line, expected_goals, variance,
    home_stats, away_stats
):
    std_dev = np.sqrt(variance)
    line_distance = abs(bookmaker_line - expected_goals)
    sigma_distance = line_distance / (std_dev + 0.1)
    
    # Line safety
    if sigma_distance > 3.0:
        line_safety = 1.0
    elif sigma_distance > 2.5:
        line_safety = 0.85
    elif sigma_distance > 2.0:
        line_safety = 0.7
    elif sigma_distance > 1.5:
        line_safety = 0.5
    elif sigma_distance > 1.0:
        line_safety = 0.3
    else:
        line_safety = 0.1
    
    # Variance factor
    cv_avg = (home_stats['variance']['cv_total'] + 
              away_stats['variance']['cv_total']) / 2
    
    if cv_avg < 0.3:
        variance_factor = 1.0
    elif cv_avg < 0.5:
        variance_factor = 0.8
    elif cv_avg < 0.7:
        variance_factor = 0.6
    else:
        variance_factor = 0.4
    
    # Consistency bonus
    stability_avg = (home_stats['variance']['stability_score'] + 
                     away_stats['variance']['stability_score']) / 2
    
    if stability_avg > 0.7:
        consistency_bonus = 1.2
    elif stability_avg > 0.5:
        consistency_bonus = 1.0
    else:
        consistency_bonus = 0.8
    
    score = line_safety * variance_factor * consistency_bonus * 25
    return min(score, 25.0)
```

---

## 📐 FORMULE 3 : Historical Breach Score

### **Objectif**

Mesurer à quelle fréquence la ligne a été dépassée historiquement.

### **Formule Mathématique**

```
historical_breach_score = (1 - breach_rate_weighted) × extremity_multiplier × 25

où :

breach_rate_weighted = {
    h2h_breach_rate × 0.50 + home_breach_rate × 0.25 + away_breach_rate × 0.25
    (si H2H >= 3 matchs)
    
    home_breach_rate × 0.50 + away_breach_rate × 0.50
    (si H2H < 3 matchs)
}

breach_rate = count(total_goals > line) / n_matches

extremity_multiplier = {
    1.5  si line > 8.5
    1.3  si line > 6.5
    1.1  si line > 4.5
    1.0  si line ≤ 4.5
}

Max: 25 points
```

### **Logique Métier**

1. **Breach Rate** : % de matchs qui ont dépassé la ligne
   - 0% breach = ligne jamais atteinte → score max
   - 50% breach = ligne atteinte 1 fois sur 2 → score moyen
   - 100% breach = ligne toujours atteinte → score min

2. **Pondération** :
   - **H2H** (50%) : confrontations directes = plus pertinent
   - **Home** (25%) : historique équipe domicile
   - **Away** (25%) : historique équipe extérieur

3. **Extremity Multiplier** : Lignes extrêmes = plus d'importance
   - Ligne > 8.5 : très rare → multiplier élevé

### **Exemple**

```
Bookmaker line: 12.5

H2H (5 matchs):
- Scores: 2-1, 1-0, 3-2, 2-2, 1-1
- Breach count: 0/5 (aucun match > 12.5)
- h2h_breach_rate = 0%

Home (20 matchs):
- Breach count: 0/20
- home_breach_rate = 0%

Away (20 matchs):
- Breach count: 1/20
- away_breach_rate = 5%

breach_rate_weighted = 0.00 × 0.50 + 0.00 × 0.25 + 0.05 × 0.25 = 0.0125 (1.25%)

extremity_multiplier = 1.5 (line > 8.5)

historical_breach_score = (1 - 0.0125) × 1.5 × 25 = 37 points
→ Mais max = 25, donc score = 25 points
```

### **Code**

```python
def _calculate_historical_breach_score(
    bookmaker_line, home_matches, away_matches, h2h_matches
):
    # Calculer breach rates
    home_breach_rate = sum(1 for m in home_matches if m.total_goals > bookmaker_line) / len(home_matches)
    away_breach_rate = sum(1 for m in away_matches if m.total_goals > bookmaker_line) / len(away_matches)
    h2h_breach_rate = sum(1 for m in h2h_matches if m.total_goals > bookmaker_line) / len(h2h_matches) if h2h_matches else 0.5
    
    # Pondération
    if len(h2h_matches) >= 3:
        weighted_breach_rate = (
            h2h_breach_rate * 0.50 +
            home_breach_rate * 0.25 +
            away_breach_rate * 0.25
        )
    else:
        weighted_breach_rate = (
            home_breach_rate * 0.50 +
            away_breach_rate * 0.50
        )
    
    # Score inversé
    base_score = 1 - weighted_breach_rate
    
    # Extremity multiplier
    if bookmaker_line > 8.5:
        extremity_multiplier = 1.5
    elif bookmaker_line > 6.5:
        extremity_multiplier = 1.3
    elif bookmaker_line > 4.5:
        extremity_multiplier = 1.1
    else:
        extremity_multiplier = 1.0
    
    score = base_score * extremity_multiplier * 25
    return min(score, 25.0)
```

---

## 📐 FORMULE 4 : Stability Score

### **Objectif**

Évaluer la fiabilité des prédictions basée sur la stabilité des équipes.

### **Formule Mathématique**

```
stability_score = avg_stability × sample_quality × trend_penalty × 20

où :

avg_stability = (stability_home + stability_away) / 2

sample_quality = {
    1.0  si n_min >= 15
    0.8  si n_min >= 10
    0.6  si n_min >= 5
    0.3  si n_min < 5
}

trend_penalty = {
    0.7   si |trend_avg| > 0.3
    0.85  si |trend_avg| > 0.2
    1.0   si |trend_avg| ≤ 0.2
}

Max: 20 points
```

### **Logique Métier**

1. **Average Stability** : Moyenne des stability_score des deux équipes
   - Équipes stables = prédictions fiables

2. **Sample Quality** : Qualité de l'échantillon
   - Plus de matchs = plus fiable

3. **Trend Penalty** : Pénalité si équipe en progression/régression
   - Trend fort = situation changeante = moins fiable

### **Exemple**

```
Home stability: 0.75
Away stability: 0.70
avg_stability = 0.725

n_home = 12
n_away = 15
n_min = 12
→ sample_quality = 0.8

trend_home = 0.15
trend_away = -0.10
avg_trend = |0.025| = 0.025
→ trend_penalty = 1.0

stability_score = 0.725 × 0.8 × 1.0 × 20 = 11.6 points
```

### **Code**

```python
def _calculate_stability_score(home_stats, away_stats):
    # Stability moyenne
    avg_stability = (
        home_stats['variance']['stability_score'] +
        away_stats['variance']['stability_score']
    ) / 2
    
    # Sample quality
    n_min = min(
        home_stats['meta']['matches_analyzed'],
        away_stats['meta']['matches_analyzed']
    )
    
    if n_min >= 15:
        sample_quality = 1.0
    elif n_min >= 10:
        sample_quality = 0.8
    elif n_min >= 5:
        sample_quality = 0.6
    else:
        sample_quality = 0.3
    
    # Trend penalty
    avg_trend = abs((
        home_stats['advanced'].get('trend_coefficient', 0) +
        away_stats['advanced'].get('trend_coefficient', 0)
    ) / 2)
    
    if avg_trend > 0.3:
        trend_penalty = 0.7
    elif avg_trend > 0.2:
        trend_penalty = 0.85
    else:
        trend_penalty = 1.0
    
    score = avg_stability * sample_quality * trend_penalty * 20
    return min(score, 20.0)
```

---

## 🎯 EXEMPLE COMPLET : Under 12.5 @ 2.00

### **Contexte**

```
Match: Team A (home) vs Team B (away)
Bookmaker: Under 12.5 @ 2.00 (50% implied probability)
```

### **Données Statistiques**

```
Team A (home):
- avg_goals_ft: 2.3
- variance: 1.8
- cv: 0.58
- stability: 0.68
- n_matches: 12

Team B (away):
- avg_goals_ft: 2.1
- variance: 1.5
- cv: 0.58
- stability: 0.72
- n_matches: 15

Expected goals: 2.5
Variance combined: 1.65
Std dev: 1.28

Historique:
- Home (20 matchs): 0 matchs > 12.5 (0%)
- Away (20 matchs): 0 matchs > 12.5 (0%)
- H2H (5 matchs): 0 matchs > 12.5 (0%)
```

### **Calcul des Sous-Scores**

#### **1. Bookmaker Gap Score**

```
P_bookmaker_under = 1 / 2.00 = 50%
P_model_under = 99.9% (Poisson avec λ=2.5)

prob_gap = |0.50 - 0.999| = 0.499 (49.9%)
multiplier = 1.0 (gap > 30%)

bookmaker_gap_score = (0.499 × 100) × 1.0 = 49.9
→ Max 30, donc = 30 points ✅
```

#### **2. Variance Safety Score**

```
σ_distance = |12.5 - 2.5| / 1.28 = 7.8
→ line_safety = 1.0

CV_avg = 0.58
→ variance_factor = 0.6

stability_avg = 0.70
→ consistency_bonus = 1.0

variance_safety_score = 1.0 × 0.6 × 1.0 × 25 = 15 points ✅
```

#### **3. Historical Breach Score**

```
breach_rate_weighted = 0.00 × 0.50 + 0.00 × 0.25 + 0.00 × 0.25 = 0%

extremity_multiplier = 1.5 (line > 8.5)

historical_breach_score = (1 - 0) × 1.5 × 25 = 37.5
→ Max 25, donc = 25 points ✅
```

#### **4. Stability Score**

```
avg_stability = 0.70
sample_quality = 0.8 (n_min = 12)
trend_penalty = 1.0

stability_score = 0.70 × 0.8 × 1.0 × 20 = 11.2 points ✅
```

### **Score Total**

```
total_score = 30 + 15 + 25 + 11.2 = 81.2 points

Niveau: EXTREME (≥ 80)
```

### **Triggers Identifiés**

```
✅ EXTREME_PROBABILITY_GAP (gap 49.9%)
✅ VERY_SAFE_LINE (σ_distance = 7.8)
✅ LINE_RARELY_BREACHED (0% breach rate)
✅ EXTREME_LINE_VALUE (line > 8.5)
✅ EXTREME_LINE_DIFFERENCE (line - expected = 10)
```

### **Explication Générée**

```
🚨 ANOMALIE DÉTECTÉE: UNDER 12.5 appears MISPRICED

📊 Bookmaker Line: 12.5 goals
📈 Expected Line: 2.0 goals
⚠️ Line Difference: +10.5 goals

🎲 Bookmaker Probability: 50.00%
🎯 Model Probability: 99.90%
📉 Probability Gap: 49.90%

⚽ Expected Total Goals: 2.50
🏠 Home avg: 2.30 goals/match
✈️ Away avg: 2.10 goals/match

📊 Home CV: 0.58 (stability: 0.68)
📊 Away CV: 0.58 (stability: 0.72)

🔔 TRIGGERS:
  • EXTREME PROBABILITY GAP
  • VERY SAFE LINE
  • LINE RARELY BREACHED
  • EXTREME LINE VALUE
  • EXTREME LINE DIFFERENCE
```

### **Raison de Confiance**

```
Score d'anomalie EXTRÊME (≥80) | 
Échantillon de données MOYEN (≥10 matchs) | 
Équipes STABLES | 
Écart de probabilité EXTRÊME | 
Ligne RAREMENT dépassée historiquement
```

---

## 🎯 Cas d'Usage

### **Cas 1 : Ligne Extrême (Under 12.5)**

**Situation** : Bookmaker propose Under 12.5 @ 2.00

**Analyse** :
- Expected goals: 2.5
- Ligne jamais atteinte historiquement
- **Score : 80+ (EXTREME)**
- **Action : FORTE ANOMALIE**

---

### **Cas 2 : Ligne Modérée (Under 2.5)**

**Situation** : Bookmaker propose Under 2.5 @ 1.80

**Analyse** :
- Expected goals: 2.8
- Ligne proche de l'expected
- **Score : 20-40 (MEDIUM/HIGH)**
- **Action : Anomalie modérée**

---

### **Cas 3 : Ligne Cohérente (Under 3.5)**

**Situation** : Bookmaker propose Under 3.5 @ 1.70

**Analyse** :
- Expected goals: 2.5
- Ligne cohérente avec statistiques
- **Score : <20 (LOW)**
- **Action : Pas d'anomalie**

---

## 📊 Résumé des Formules

| Formule | Max Points | Facteurs Clés |
|---------|-----------|---------------|
| **Bookmaker Gap** | 30 | Écart probabilités |
| **Variance Safety** | 25 | Distance σ, CV, stabilité |
| **Historical Breach** | 25 | Breach rate, extremity |
| **Stability** | 20 | Stabilité, sample, trend |
| **TOTAL** | **100** | - |

---

**Système complet de détection d'anomalies avec scoring 0-100 et explications détaillées.**
