# ✅ Moteur de Détection d'Anomalies Bookmaker - COMPLET

## 🎯 Vue d'Ensemble

**Système complet de détection d'anomalies** qui compare les lignes bookmakers avec la réalité statistique des équipes.

---

## 📊 Score d'Anomalie (0-100)

### **Composition**

| Sous-Score | Points | Formule |
|------------|--------|---------|
| **Bookmaker Gap** | 30 | `(prob_gap × 100) × multiplier` |
| **Variance Safety** | 25 | `line_safety × variance_factor × consistency_bonus × 25` |
| **Historical Breach** | 25 | `(1 - breach_rate) × extremity_multiplier × 25` |
| **Stability** | 20 | `avg_stability × sample_quality × trend_penalty × 20` |
| **TOTAL** | **100** | Somme des 4 sous-scores |

### **Niveaux**

```
EXTREME    : ≥ 80  🔴
VERY_HIGH  : ≥ 60  🟠
HIGH       : ≥ 40  🟡
MEDIUM     : ≥ 20  🟢
LOW        : < 20  ⚪
```

---

## 🔢 LES 4 FORMULES DÉTAILLÉES

### **1. Bookmaker Gap Score** (Max: 30)

**Objectif** : Mesurer l'écart entre probabilités bookmaker et modèle

```python
bookmaker_gap_score = (prob_gap × 100) × multiplier

prob_gap = max(
    |P_bk_over - P_model_over|,
    |P_bk_under - P_model_under|
)

multiplier = {
    1.0  si prob_gap > 30%
    0.8  si prob_gap > 20%
    0.6  si prob_gap > 15%
    0.4  si prob_gap > 10%
    0.2  si prob_gap ≤ 10%
}
```

**Exemple** :
- Bookmaker: 50% | Modèle: 5% → Gap 45%
- Score: (0.45 × 100) × 1.0 = 45 → **30 points** (max)

---

### **2. Variance Safety Score** (Max: 25)

**Objectif** : Évaluer sécurité de la ligne vs variance

```python
variance_safety_score = line_safety × variance_factor × consistency_bonus × 25

line_safety = f(σ_distance)
σ_distance = |line - expected| / σ

variance_factor = f(CV_avg)
consistency_bonus = f(stability_avg)
```

**Exemple** :
- Ligne 12.5, Expected 2.5, σ = 1.28
- σ_distance = 7.8 → line_safety = 1.0
- CV = 0.4 → variance_factor = 0.8
- Stability = 0.75 → bonus = 1.2
- Score: 1.0 × 0.8 × 1.2 × 25 = **24 points**

---

### **3. Historical Breach Score** (Max: 25)

**Objectif** : Mesurer fréquence dépassement historique

```python
historical_breach_score = (1 - breach_rate) × extremity_multiplier × 25

breach_rate = weighted_average(
    h2h_breach × 0.50,
    home_breach × 0.25,
    away_breach × 0.25
)

extremity_multiplier = {
    1.5  si line > 8.5
    1.3  si line > 6.5
    1.1  si line > 4.5
    1.0  sinon
}
```

**Exemple** :
- Ligne 12.5, breach_rate = 0%
- extremity = 1.5
- Score: (1 - 0) × 1.5 × 25 = 37.5 → **25 points** (max)

---

### **4. Stability Score** (Max: 20)

**Objectif** : Évaluer fiabilité basée sur stabilité

```python
stability_score = avg_stability × sample_quality × trend_penalty × 20

sample_quality = {
    1.0  si n ≥ 15
    0.8  si n ≥ 10
    0.6  si n ≥ 5
    0.3  si n < 5
}

trend_penalty = {
    0.7   si |trend| > 0.3
    0.85  si |trend| > 0.2
    1.0   sinon
}
```

**Exemple** :
- avg_stability = 0.70
- n_min = 12 → sample_quality = 0.8
- trend = 0.05 → penalty = 1.0
- Score: 0.70 × 0.8 × 1.0 × 20 = **11.2 points**

---

## 🎯 EXEMPLE COMPLET : Under 12.5 @ 2.00

### **Contexte**

```
Match: Team A vs Team B
Bookmaker: Under 12.5 @ 2.00 (50% implied)

Stats:
- Expected goals: 2.5
- Variance: 1.65
- Home avg: 2.3, Away avg: 2.1
- Breach rate: 0% (jamais dépassé)
- Stability: 0.70
```

### **Calcul**

```
1. Bookmaker Gap:     30/30  ✅
2. Variance Safety:   15/25  ✅
3. Historical Breach: 25/25  ✅
4. Stability:         11/20  ✅

TOTAL: 81/100 → EXTREME 🔴
```

### **Triggers**

```
✅ EXTREME_PROBABILITY_GAP
✅ VERY_SAFE_LINE
✅ LINE_RARELY_BREACHED
✅ EXTREME_LINE_VALUE
✅ EXTREME_LINE_DIFFERENCE
```

### **Explication**

```
🚨 ANOMALIE DÉTECTÉE: UNDER 12.5 appears MISPRICED

📊 Bookmaker Line: 12.5 goals
📈 Expected Line: 2.0 goals
⚠️ Line Difference: +10.5 goals

🎲 Bookmaker Probability: 50.00%
🎯 Model Probability: 99.90%
📉 Probability Gap: 49.90%

⚽ Expected Total Goals: 2.50
```

---

## 💻 UTILISATION

### **Code Python**

```python
from app.services.anomaly_engine import AdvancedAnomalyDetector

detector = AdvancedAnomalyDetector(db)

anomaly = detector.detect_line_anomaly(
    match_id=1,
    home_team_id=1,
    away_team_id=2,
    market_type="over_under",
    bookmaker_line=12.5,
    bookmaker_over_odds=2.00,
    bookmaker_under_odds=2.00
)

print(f"Score: {anomaly.total_score}/100")
print(f"Niveau: {anomaly.level.value}")
print(f"Triggers: {anomaly.triggers}")
print(f"\n{anomaly.explanation}")
```

### **Résultat**

```python
AnomalyScore(
    total_score=81.2,
    level=AnomalyLevel.EXTREME,
    
    bookmaker_gap_score=30.0,
    variance_safety_score=15.0,
    historical_breach_score=25.0,
    stability_score=11.2,
    
    bookmaker_prob=0.50,
    model_prob=0.999,
    probability_gap=0.499,
    
    bookmaker_line=12.5,
    expected_line=2.0,
    line_difference=10.5,
    
    triggers=[
        "EXTREME_PROBABILITY_GAP",
        "VERY_SAFE_LINE",
        "LINE_RARELY_BREACHED",
        "EXTREME_LINE_VALUE",
        "EXTREME_LINE_DIFFERENCE"
    ],
    
    explanation="...",
    confidence_reason="..."
)
```

---

## 📈 CAS D'USAGE

### **Cas 1 : Scanner Plusieurs Lignes**

```python
lines = [2.5, 3.5, 4.5, 5.5, 8.5, 12.5]
results = []

for line in lines:
    anomaly = detector.detect_line_anomaly(...)
    results.append((line, anomaly.total_score))

# Trier par score
results.sort(key=lambda x: x[1], reverse=True)

# Meilleure anomalie
best_line, best_score = results[0]
```

### **Cas 2 : Filtrer par Confiance**

```python
anomalies = []

for match in matches:
    anomaly = detector.detect_line_anomaly(...)
    
    # Garder seulement HIGH+
    if anomaly.level in [AnomalyLevel.HIGH, AnomalyLevel.VERY_HIGH, AnomalyLevel.EXTREME]:
        anomalies.append(anomaly)
```

### **Cas 3 : Analyser Triggers**

```python
anomaly = detector.detect_line_anomaly(...)

if "EXTREME_PROBABILITY_GAP" in anomaly.triggers:
    print("⚠️ Écart de probabilité extrême détecté")

if "LINE_RARELY_BREACHED" in anomaly.triggers:
    print("⚠️ Ligne rarement atteinte historiquement")
```

---

## 🔔 TRIGGERS DISPONIBLES

| Trigger | Condition | Signification |
|---------|-----------|---------------|
| `EXTREME_PROBABILITY_GAP` | gap > 20 | Écart probabilité extrême |
| `HIGH_PROBABILITY_GAP` | gap > 15 | Écart probabilité élevé |
| `VERY_SAFE_LINE` | safety > 18 | Ligne très sûre |
| `SAFE_LINE` | safety > 12 | Ligne sûre |
| `LINE_RARELY_BREACHED` | breach > 18 | Rarement dépassée |
| `LINE_SELDOM_BREACHED` | breach > 12 | Peu souvent dépassée |
| `HIGH_STABILITY` | stability > 15 | Équipes stables |
| `EXTREME_LINE_DIFFERENCE` | diff > 3 | Différence extrême |
| `HIGH_LINE_DIFFERENCE` | diff > 2 | Différence élevée |
| `EXTREME_LINE_VALUE` | line > 8.5 | Ligne extrême |

---

## 📊 COMPARAISON AVEC ANCIEN SYSTÈME

| Aspect | Ancien | Nouveau |
|--------|--------|---------|
| **Score** | 0-10 | **0-100** ✅ |
| **Sous-scores** | 1 | **4** ✅ |
| **Formules** | Basique | **Avancées** ✅ |
| **Triggers** | Non | **10 triggers** ✅ |
| **Explications** | Basique | **Détaillées** ✅ |
| **Confiance** | Oui/Non | **Raisons** ✅ |
| **Historique** | Non | **H2H + équipes** ✅ |
| **Variance** | Non | **Safety score** ✅ |

---

## 🎯 AVANTAGES

### **1. Scoring Granulaire (0-100)**

- Permet de **comparer** précisément les anomalies
- **5 niveaux** de confiance
- **4 sous-scores** détaillés

### **2. Méthode Probabiliste**

- Utilise **Poisson** et **Negative Binomial**
- Adapté à la **variance** des équipes
- Calcul **xG** intégré

### **3. Analyse Historique**

- **H2H** (50% poids)
- **Home** (25% poids)
- **Away** (25% poids)
- **Extremity multiplier** pour lignes extrêmes

### **4. Explications Détaillées**

- **Triggers** identifiés
- **Raisons** de confiance
- **Statistiques** clés
- **Comparaison** bookmaker vs modèle

---

## 📁 FICHIERS CRÉÉS

### **Code**

```
app/services/anomaly_engine/
└── advanced_anomaly_detector.py  (600+ lignes)
    ├── AdvancedAnomalyDetector
    ├── AnomalyScore (dataclass)
    ├── AnomalyLevel (enum)
    └── 4 formules de scoring
```

### **Documentation**

```
docs/
└── ANOMALY_DETECTION_SYSTEM.md  (800+ lignes)
    ├── Vue d'ensemble
    ├── 4 formules détaillées
    ├── Exemples complets
    └── Cas d'usage
```

### **Exemples**

```
examples/
└── anomaly_detection_example.py  (300+ lignes)
    ├── 5 exemples d'utilisation
    ├── Ligne extrême
    ├── Ligne modérée
    ├── Comparaison multiple
    └── Filtrage par confiance
```

---

## ✅ CHECKLIST IMPLÉMENTATION

- [x] Score 0-100 avec 4 sous-scores
- [x] Formule Bookmaker Gap (max 30)
- [x] Formule Variance Safety (max 25)
- [x] Formule Historical Breach (max 25)
- [x] Formule Stability (max 20)
- [x] 5 niveaux d'anomalie
- [x] 10 triggers identifiables
- [x] Explications détaillées
- [x] Raisons de confiance
- [x] Analyse H2H
- [x] Distributions Poisson/NBinom
- [x] Expected goals (xG)
- [x] Extremity multiplier
- [x] Dataclass AnomalyScore
- [x] Enum AnomalyLevel
- [x] Documentation complète
- [x] 5 exemples d'utilisation

---

## 🎯 RÉSUMÉ

**Système complet de détection d'anomalies bookmaker** avec :

✅ **Score 0-100** granulaire  
✅ **4 formules** mathématiques avancées  
✅ **10 triggers** d'alerte  
✅ **Explications** détaillées automatiques  
✅ **Analyse historique** (H2H + équipes)  
✅ **Méthode probabiliste** (Poisson/NBinom)  
✅ **5 niveaux** de confiance  
✅ **Documentation** complète  
✅ **Exemples** d'utilisation  

**Prêt à détecter les incohérences bookmaker dans les ligues obscures.** 🎯
