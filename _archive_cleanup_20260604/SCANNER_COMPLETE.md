# ✅ Scanner Automatique d'Anomalies - COMPLET

## 🎯 Vue d'Ensemble

**Scanner automatique intelligent** qui analyse tous les matchs du jour pour détecter les meilleures anomalies bookmaker sur ligues obscures.

---

## 📊 Pipeline de Scanning (7 Étapes)

```
1. RÉCUPÉRATION → Get matches (scheduled, next N days)
2. FILTRAGE LIGUES → Skip Tier 1 & 2, Focus Tier 3 & 4+
3. ANALYSE MULTI-MARCHÉS → Scan 6 markets per match
4. CALCUL SCORES → 6 scores calculés
5. FILTRAGE QUALITÉ → 4 filtres appliqués
6. RANKING → Sort by final_score
7. OUTPUT → Top N anomalies
```

---

## 🎯 6 Marchés Analysés

| Priorité | Marché | Exploitabilité |
|----------|--------|----------------|
| **CRITICAL** | HT Under 0.5 | 95% |
| **CRITICAL** | Extreme Under 1.5 | 90% |
| **HIGH** | HT Over 0.5 | 80% |
| **HIGH** | FT Under 2.5 | 75% |
| **HIGH** | FT Over 2.5 | 75% |
| **MEDIUM** | BTTS | 70% |

---

## 📐 6 Scores Calculés

### **1. Anomaly Score (0-100)**

```python
anomaly_score = (
    discrepancy × 100 × 0.40 +
    historical_consistency × 100 × 0.30 +
    variance_safety × 100 × 0.15 +
    stability × 100 × 0.15
)
```

### **2. Bookmaker Discrepancy (0-1)**

```python
discrepancy = |P_bookmaker - P_model|
```

### **3. Historical Consistency (0-1)**

```python
historical_consistency = (home_freq + away_freq) / 2
```

### **4. Variance Safety (0-1)**

```python
variance_safety = 1 - min(avg_variance / 3.0, 1.0)
```

### **5. Stability Score (0-1)**

```python
stability = (home_stability + away_stability) / 2
```

### **6. Line Breach Probability (0-1)**

```python
breach_probability = 1 - historical_consistency
```

---

## 🎯 Final Score (Weighted)

```python
final_score = anomaly_score × market_bonus × league_bonus × (1 - fp_penalty) × (1 - sample_penalty)
```

### **Bonus & Pénalités**

| Type | Valeur | Impact |
|------|--------|--------|
| **Market CRITICAL** | ×1.20 | +20% |
| **Market HIGH** | ×1.10 | +10% |
| **League TIER_4+** | ×1.15 | +15% |
| **League TIER_3** | ×1.05 | +5% |
| **False Positive** | ×(1 - risk×0.5) | Jusqu'à -50% |
| **Small Sample** | ×(1 - penalty×0.3) | Jusqu'à -30% |

---

## 🚫 Stratégie Anti-Faux Positifs

### **False Positive Risk**

```python
false_positive_risk = (
    sample_risk × 0.30 +
    stability_risk × 0.25 +
    consistency_risk × 0.25 +
    discrepancy_risk × 0.20
)
```

### **4 Filtres de Qualité**

1. **Min anomaly score** : ≥ 45.0
2. **Min confidence** : ≥ 0.50
3. **Max false positive risk** : ≤ 0.30
4. **Min sample size** : ≥ 5

---

## 📏 Gestion Small Samples

| Sample Size | Penalty | Action |
|-------------|---------|--------|
| **< 5** | REJECT | Données insuffisantes |
| **5-7** | 40% | Pénalité forte |
| **8-11** | 20% | Pénalité modérée |
| **12-14** | 10% | Pénalité légère |
| **≥ 15** | 0% | Pas de pénalité |

---

## 🏆 Priorisation des Ligues

| Tier | Description | Action | Bonus |
|------|-------------|--------|-------|
| **TIER_1** | Top leagues | **SKIP** | - |
| **TIER_2** | Second divisions | **SKIP** | - |
| **TIER_3** | Third divisions | **ANALYZE** | +5% |
| **TIER_4+** | Obscure leagues | **PRIORITY** | +15% |

---

## 🔄 Algorithme de Ranking

```python
# 1. Calcul final_score pour chaque résultat
for result in results:
    result.final_score = calculate_final_score(result)

# 2. Tri décroissant
results.sort(key=lambda x: x.final_score, reverse=True)

# 3. Top N
top_results = results[:max_results]
```

---

## 🏗️ Architecture Scalable

### **Design Patterns**

- **Strategy Pattern** : Scanners par marché
- **Factory Pattern** : Création de scanners
- **Pipeline Pattern** : Étapes de traitement

### **Scalabilité**

- **Horizontal Scaling** : Celery workers
- **Caching** : Redis pour stats
- **Batch Processing** : Traitement par lots

---

## 📊 Output Format

```json
{
    "match_id": 100,
    "match_info": {
        "home_team": "Wrexham AFC",
        "away_team": "Notts County",
        "league": "England National League"
    },
    "market_type": "ht_under_05",
    "market_priority": "CRITICAL",
    
    "anomaly_score": 85.3,
    "bookmaker_discrepancy": 0.32,
    "historical_consistency": 0.575,
    "variance_safety": 0.82,
    "stability_score": 0.78,
    "line_breach_probability": 0.425,
    "final_score": 98.5,
    
    "confidence_score": 0.82,
    "confidence_level": "HIGH",
    
    "sample_size": 12,
    "league_tier": "TIER_4_PLUS",
    "false_positive_risk": 0.15,
    "small_sample_penalty": 0.0,
    
    "signals": [...],
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
- days_ahead: 1-7
- max_results: 1-100
- min_anomaly_score: 0-100
- min_confidence: 0-1
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

## ✅ Fonctionnalités

✅ **Pipeline 7 étapes** automatique  
✅ **6 marchés** analysés  
✅ **6 scores** calculés  
✅ **Final score** pondéré  
✅ **4 filtres** de qualité  
✅ **False positive risk** calculé  
✅ **Small sample** gestion  
✅ **League prioritization** (Tier 1-4+)  
✅ **Ranking** intelligent  
✅ **Architecture scalable**  
✅ **API endpoint** complet  

---

## 📁 Fichiers Créés

- `anomaly_scanner.py` (800+ lignes)
- `scanner_endpoints.py` (API)
- `SCANNER_SYSTEM.md` (documentation complète)
- `SCANNER_COMPLETE.md` (récapitulatif)

---

**Scanner automatique complet avec logique avancée, ranking intelligent et stratégies anti-faux positifs prêt à détecter les meilleures opportunités !** 🔍⚽
