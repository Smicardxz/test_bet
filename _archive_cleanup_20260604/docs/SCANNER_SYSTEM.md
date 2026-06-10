# 🔍 Scanner Automatique d'Anomalies - Documentation Complète

## 🎯 Vue d'Ensemble

**Scanner automatique** qui analyse tous les matchs du jour pour détecter les anomalies bookmaker fortes sur ligues obscures.

---

## 📊 Architecture du Scanner

### **Pipeline de Scanning**

```
1. RÉCUPÉRATION
   ↓
   Get all matches (scheduled, next N days)
   
2. FILTRAGE LIGUES
   ↓
   Skip Tier 1 & 2 → Focus Tier 3 & 4+
   
3. ANALYSE MULTI-MARCHÉS
   ↓
   Scan 6 markets per match
   
4. CALCUL SCORES
   ↓
   - Anomaly score
   - Bookmaker discrepancy
   - Historical consistency
   - Variance safety
   - Stability score
   - Line breach probability
   
5. FILTRAGE QUALITÉ
   ↓
   - Min anomaly score
   - Min confidence
   - Max false positive risk
   - Min sample size
   
6. RANKING
   ↓
   Sort by final_score (weighted)
   
7. OUTPUT
   ↓
   Top N anomalies
```

---

## 🎯 Marchés Prioritaires

### **CRITICAL Priority** ⭐⭐⭐⭐⭐

| Marché | Raison | Exploitabilité |
|--------|--------|----------------|
| **HT Under 0.5** | 0-0 HT fréquent en ligues obscures | 95% |
| **Extreme Under 1.5** | Lignes très sûres | 90% |

### **HIGH Priority** ⭐⭐⭐⭐

| Marché | Raison | Exploitabilité |
|--------|--------|----------------|
| **HT Over 0.5** | Fast starters détectables | 80% |
| **FT Under 2.5** | Marché populaire | 75% |
| **FT Over 2.5** | High scoring teams | 75% |

### **MEDIUM Priority** ⭐⭐⭐

| Marché | Raison | Exploitabilité |
|--------|--------|----------------|
| **BTTS** | Défenses faibles | 70% |
| **HT BTTS** | Moins fréquent | 65% |

---

## 📐 Calcul des Scores

### **1. Anomaly Score (0-100)**

**Formule** :
```python
anomaly_score = (
    discrepancy × 100 × 0.40 +           # 40%
    historical_consistency × 100 × 0.30 + # 30%
    variance_safety × 100 × 0.15 +        # 15%
    stability × 100 × 0.15                # 15%
)
```

**Composants** :
- **Discrepancy** : `|P_bookmaker - P_model|`
- **Historical Consistency** : Fréquence historique du résultat
- **Variance Safety** : `1 - (variance / 3.0)`
- **Stability** : Score de stabilité des équipes

---

### **2. Bookmaker Discrepancy (0-1)**

**Formule** :
```python
discrepancy = |P_bookmaker - P_model|

où:
P_bookmaker = 1 / odds
P_model = Poisson/NBinom probability
```

**Seuils** :
- `> 0.30` : EXTREME
- `> 0.20` : VERY_HIGH
- `> 0.15` : HIGH
- `< 0.15` : Rejeté

---

### **3. Historical Consistency (0-1)**

**Formule** :
```python
historical_consistency = (
    home_frequency + away_frequency
) / 2

où frequency = % matchs avec résultat attendu
```

**Exemple** :
```
Marché: 0-0 HT
Home: 55% de 0-0 HT
Away: 60% de 0-0 HT

historical_consistency = (0.55 + 0.60) / 2 = 0.575
```

---

### **4. Variance Safety (0-1)**

**Formule** :
```python
variance_safety = 1 - min(avg_variance / 3.0, 1.0)

où:
avg_variance = (home_variance + away_variance) / 2
```

**Interprétation** :
- Variance faible → Safety élevé → Scores prévisibles
- Variance élevée → Safety faible → Scores imprévisibles

---

### **5. Stability Score (0-1)**

**Formule** :
```python
stability = (
    home_stability + away_stability
) / 2

où:
stability = 1 / (1 + CV)
CV = σ / μ
```

---

### **6. Line Breach Probability (0-1)**

**Formule** :
```python
breach_probability = 1 - historical_consistency

où:
breach_rate = count(result > line) / n_matches
```

**Exemple** :
```
Ligne: Under 12.5
Breach rate historique: 0% (jamais dépassé)

breach_probability = 1 - 1.0 = 0.0 (très sûr)
```

---

## 🎯 Final Score (Weighted)

### **Formule Complète**

```python
final_score = anomaly_score × market_bonus × league_bonus × (1 - fp_penalty) × (1 - sample_penalty)
```

### **Market Priority Bonus**

```python
if market_priority == CRITICAL:
    market_bonus = 1.20  # +20%
elif market_priority == HIGH:
    market_bonus = 1.10  # +10%
elif market_priority == MEDIUM:
    market_bonus = 1.00  # +0%
else:
    market_bonus = 0.90  # -10%
```

### **League Tier Bonus**

```python
if league_tier == TIER_4_PLUS:
    league_bonus = 1.15  # +15%
elif league_tier == TIER_3:
    league_bonus = 1.05  # +5%
else:
    league_bonus = 1.00  # +0%
```

### **False Positive Penalty**

```python
fp_penalty = false_positive_risk × 0.5

final_score × (1 - fp_penalty)
```

### **Small Sample Penalty**

```python
if sample_size < 8:
    sample_penalty = 1 - (sample_size / 8)
else:
    sample_penalty = 0

final_score × (1 - sample_penalty × 0.3)
```

---

## 🚫 Stratégie Anti-Faux Positifs

### **1. False Positive Risk Calculation**

**Formule** :
```python
false_positive_risk = (
    sample_risk × 0.30 +
    stability_risk × 0.25 +
    consistency_risk × 0.25 +
    discrepancy_risk × 0.20
)
```

**Composants** :

```python
# Sample risk
if sample_size < 8:
    sample_risk = 0.5
elif sample_size < 12:
    sample_risk = 0.3
else:
    sample_risk = 0.1

# Stability risk
stability_risk = 1 - stability_score

# Consistency risk
consistency_risk = 1 - historical_consistency

# Discrepancy risk
if discrepancy < 0.15:
    discrepancy_risk = 0.5
elif discrepancy < 0.20:
    discrepancy_risk = 0.3
else:
    discrepancy_risk = 0.1
```

### **2. Filtrage Multi-Critères**

```python
# Filter 1: Min anomaly score
if anomaly_score < 45.0:
    REJECT

# Filter 2: Min confidence
if confidence_score < 0.50:
    REJECT

# Filter 3: Max false positive risk
if false_positive_risk > 0.30:
    REJECT

# Filter 4: Min sample size (hard limit)
if sample_size < 5:
    REJECT
```

---

## 📏 Gestion Small Samples

### **Stratégie Progressive**

| Sample Size | Penalty | Action |
|-------------|---------|--------|
| **< 5** | REJECT | Données insuffisantes |
| **5-7** | 40% | Pénalité forte |
| **8-11** | 20% | Pénalité modérée |
| **12-14** | 10% | Pénalité légère |
| **≥ 15** | 0% | Pas de pénalité |

### **Formule Penalty**

```python
if sample_size < min_sample_size:
    penalty = 1 - (sample_size / min_sample_size)
    
    final_score × (1 - penalty × 0.3)
```

### **Bayesian Smoothing (Optionnel)**

```python
# Pour très petits samples
if sample_size < 8:
    smoothed_value = (
        observed_value × sample_size +
        league_average × k
    ) / (sample_size + k)
    
    où k = 5 (prior strength)
```

---

## 🏆 Priorisation des Ligues

### **Tier Classification**

| Tier | Description | Action | Bonus |
|------|-------------|--------|-------|
| **TIER_1** | Top leagues (Premier League, La Liga, etc.) | **SKIP** | - |
| **TIER_2** | Second divisions (Championship, etc.) | **SKIP** | - |
| **TIER_3** | Third divisions | **ANALYZE** | +5% |
| **TIER_4+** | Obscure leagues (National League, etc.) | **PRIORITY** | +15% |

### **Logique de Filtrage**

```python
def classify_league_tier(competition):
    tier = competition.tier
    
    if tier == 1:
        return TIER_1  # Skip
    elif tier == 2:
        return TIER_2  # Skip
    elif tier == 3:
        return TIER_3  # Analyze
    else:
        return TIER_4_PLUS  # Priority

# Dans le scanner
if league_tier in [TIER_1, TIER_2]:
    continue  # Skip match
```

---

## 🔄 Algorithme de Ranking

### **Étapes**

1. **Calcul Final Score** pour chaque résultat
2. **Tri décroissant** par final_score
3. **Retour Top N** résultats

### **Formule de Tri**

```python
results.sort(key=lambda x: x.final_score, reverse=True)

top_results = results[:max_results]
```

### **Critères de Départage**

Si final_score égal :
1. Anomaly score le plus élevé
2. Confidence score le plus élevé
3. False positive risk le plus faible
4. Sample size le plus grand

---

## 🏗️ Architecture Scalable

### **Design Patterns**

**1. Strategy Pattern**
```python
class MarketScanner:
    def scan(self, match, odds, expectations):
        pass

class HTUnder05Scanner(MarketScanner):
    def scan(self, match, odds, expectations):
        # Specific logic
        pass
```

**2. Factory Pattern**
```python
class ScannerFactory:
    def create_scanner(self, market_type):
        if market_type == "ht_under_05":
            return HTUnder05Scanner()
        # ...
```

**3. Pipeline Pattern**
```python
pipeline = [
    FetchMatchesStage(),
    FilterLeaguesStage(),
    ScanMarketsStage(),
    CalculateScoresStage(),
    FilterResultsStage(),
    RankResultsStage()
]

results = pipeline.execute()
```

### **Scalabilité**

**Horizontal Scaling** :
```python
# Distribuer scanning sur workers
from celery import group

tasks = [
    scan_match.s(match_id)
    for match_id in match_ids
]

job = group(tasks)
results = job.apply_async()
```

**Caching** :
```python
# Cache stats pour éviter recalculs
@cache.memoize(timeout=3600)
def get_team_stats(team_id, home_away):
    return stats_engine.calculate_team_stats(team_id, home_away)
```

**Batch Processing** :
```python
# Traiter matchs par batch
batch_size = 50

for i in range(0, len(matches), batch_size):
    batch = matches[i:i+batch_size]
    process_batch(batch)
```

---

## 📊 Output Format

### **ScanResult Structure**

```python
{
    "match_id": 100,
    "match_info": {
        "home_team": "Wrexham AFC",
        "away_team": "Notts County",
        "league": "England National League",
        "match_date": "2026-05-27T15:00:00"
    },
    "market_type": "ht_under_05",
    "market_priority": "CRITICAL",
    
    # Scores
    "anomaly_score": 85.3,
    "bookmaker_discrepancy": 0.32,
    "historical_consistency": 0.575,
    "variance_safety": 0.82,
    "stability_score": 0.78,
    "line_breach_probability": 0.425,
    "final_score": 98.5,
    
    # Confidence
    "confidence_score": 0.82,
    "confidence_level": "HIGH",
    
    # Metadata
    "sample_size": 12,
    "league_tier": "TIER_4_PLUS",
    "signals": [
        {
            "type": "EXTREME_PROBABILITY_GAP",
            "strength": "STRONG",
            "value": 0.32
        },
        {
            "type": "BOTH_SLOW_STARTERS",
            "strength": "STRONG",
            "value": 0.575
        }
    ],
    
    # Risk
    "false_positive_risk": 0.15,
    "small_sample_penalty": 0.0,
    
    # Explanation
    "explanation": "...",
    "recommendation": "✅ FORTE ANOMALIE"
}
```

---

## 🚀 Utilisation

### **API Endpoint**

```bash
POST /api/v1/scanner/run

Parameters:
- days_ahead: int (1-7)
- max_results: int (1-100)
- min_anomaly_score: float (0-100)
- min_confidence: float (0-1)
```

### **Exemple**

```bash
curl -X POST "http://localhost:8000/api/v1/scanner/run?days_ahead=1&max_results=10&min_anomaly_score=60&min_confidence=0.70"
```

### **Response**

```json
{
    "total_matches_scanned": 45,
    "total_anomalies_found": 8,
    "critical_priority": 3,
    "high_priority": 4,
    "medium_priority": 1,
    "tier_4_plus_leagues": 6,
    "tier_3_leagues": 2,
    "avg_anomaly_score": 72.5,
    "avg_confidence_score": 0.78,
    "avg_false_positive_risk": 0.18,
    "top_results": [...]
}
```

---

## ✅ Checklist Qualité

### **Avant Validation**

- [ ] Anomaly score ≥ 45
- [ ] Confidence score ≥ 0.50
- [ ] False positive risk ≤ 0.30
- [ ] Sample size ≥ 5
- [ ] League tier = 3 ou 4+
- [ ] Bookmaker discrepancy ≥ 0.15
- [ ] Historical consistency vérifiée
- [ ] Variance safety calculée
- [ ] Stability score validé

---

**Scanner automatique complet avec logique avancée, ranking intelligent et stratégies anti-faux positifs.** 🔍⚽

