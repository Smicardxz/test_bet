# 🔍 Debug System - COMPLET

**Version** : 1.0.0  
**Date** : 27 Mai 2026  
**Statut** : ✅ OPÉRATIONNEL

---

## 🎯 OBJECTIF ATTEINT

**Mode DEBUG COMPLET** sur tout le pipeline pour rendre chaque score totalement explicable.

---

## 📁 FICHIERS CRÉÉS

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `app/services/anomaly/score_breakdown_formatter.py` | 250 | **Formateur de debug** |
| `scripts/debug_anomaly.py` | 300 | Script debug complet |
| `DEBUG_SYSTEM.md` | 400 | Ce fichier |
| **TOTAL** | **950** | **3 fichiers** |

---

## ✅ FONCTIONNALITÉS

### **12 Points de Debug**

1. ✅ **Données récupérées** - Match, équipes, historiques
2. ✅ **Stats calculées** - Home/Away, 50+ métriques
3. ✅ **Variance** - Composantes de variance
4. ✅ **Stabilité** - Score de stabilité
5. ✅ **Line breach analysis** - HistoricalLineBreachEngine
6. ✅ **Bookmaker probability** - Odds → probabilité
7. ✅ **Model probability** - Probabilité calculée
8. ✅ **Score breakdown complet** - 4 composants détaillés
9. ✅ **Poids appliqués** - 40/25/20/15 actuels
10. ✅ **Positive signals** - Signaux favorables
11. ✅ **Negative signals** - Signaux défavorables
12. ✅ **Risk factors** - Facteurs de risque

### **3 Modes d'Affichage**

#### **Verbose Mode**

```
================================================================================
ANOMALY SCORE DEBUG - VERBOSE MODE
================================================================================

Match ID: 1
Market: ft_under_25
Line: 2.5
Timestamp: 2026-05-27 15:30:45

--------------------------------------------------------------------------------
PROBABILITIES
--------------------------------------------------------------------------------
  Bookmaker Odds:     1.85
  Bookmaker Prob:     54.1%
  Normalized Prob:    58.9%
  Model Prob:         73.3%
  Gap:                14.4%

--------------------------------------------------------------------------------
COMPONENT SCORES
--------------------------------------------------------------------------------
  Discrepancy:          76.8/100
  Variance Safety:      82.5/100
  Historical Hit:       73.3/100
  Stability:            88.0/100

--------------------------------------------------------------------------------
WEIGHTS APPLIED
--------------------------------------------------------------------------------
  Discrepancy:        40%
  Variance Safety:    25%
  Historical Hit:     20%
  Stability:          15%

--------------------------------------------------------------------------------
WEIGHTED CONTRIBUTIONS
--------------------------------------------------------------------------------
  Discrepancy:        30.72 (impact: 38.7%)
  Variance Safety:    20.63 (impact: 26.0%)
  Historical Hit:     14.66 (impact: 18.5%)
  Stability:          13.20 (impact: 16.6%)

--------------------------------------------------------------------------------
FINAL SCORE
--------------------------------------------------------------------------------
  Anomaly Score:      79.21/100
  Confidence Score:   0.85
  Confidence Level:   HIGH

--------------------------------------------------------------------------------
DATA QUALITY
--------------------------------------------------------------------------------
  Sample Size:        15
  Data Quality:       1.00

--------------------------------------------------------------------------------
POSITIVE SIGNALS
--------------------------------------------------------------------------------
  [STRONG] high_under_rate: Both teams under-prone (75.3%)
    Value: 75.30

--------------------------------------------------------------------------------
NEGATIVE SIGNALS
--------------------------------------------------------------------------------
  [MODERATE] low_sample: Small sample size (15)
    Value: 15.00

--------------------------------------------------------------------------------
RISK FACTORS
--------------------------------------------------------------------------------
  ⚠️  Low sample size (15)

--------------------------------------------------------------------------------
EXPLANATION
--------------------------------------------------------------------------------
  Bookmaker line appears significantly undervalued based on historical data.

================================================================================
```

---

#### **Compact Mode**

```
================================================================================
ANOMALY DEBUG
================================================================================

ft_under_25 | Score: 79.2 | Conf: HIGH
Book: 58.9% | Model: 73.3% | Gap: 14.4%

Components: D:77×40%=30.7 | V:83×25%=20.6 | H:73×20%=14.7 | S:88×15%=13.2
Final: 79.21 | Quality: 1.00 | Sample: 15
Signals: +1 | -1 | Risks: 1
Risks: Low sample size (15)

================================================================================
```

---

#### **JSON Mode**

```json
{
  "match_id": 1,
  "market_type": "ft_under_25",
  "line": 2.5,
  "timestamp": "2026-05-27T15:30:45",
  "probabilities": {
    "bookmaker_odds": 1.85,
    "bookmaker_probability": 0.541,
    "normalized_probability": 0.589,
    "model_probability": 0.733,
    "gap": 0.144
  },
  "component_scores": {
    "discrepancy": {"raw": 76.8, "weight": 0.4, "contribution": 30.72},
    "variance_safety": {"raw": 82.5, "weight": 0.25, "contribution": 20.63},
    "historical_hit": {"raw": 73.3, "weight": 0.2, "contribution": 14.66},
    "stability": {"raw": 88.0, "weight": 0.15, "contribution": 13.20}
  },
  "final_score": {
    "anomaly_score": 79.21,
    "confidence_score": 0.85,
    "confidence_category": "HIGH"
  },
  "signals": {
    "positive": [
      {"type": "high_under_rate", "strength": "STRONG", "description": "...", "value": 75.3}
    ],
    "negative": [
      {"type": "low_sample", "strength": "MODERATE", "description": "...", "value": 15.0}
    ]
  },
  "risk_factors": ["Low sample size (15)"],
  "explanation": "Bookmaker line appears significantly undervalued..."
}
```

---

## 🚀 UTILISATION

### **Usage Simple**

```bash
# Verbose mode (default)
python scripts/debug_anomaly.py

# Compact mode
python scripts/debug_anomaly.py --mode compact

# JSON export
python scripts/debug_anomaly.py --mode json --output report.json

# All markets
python scripts/debug_anomaly.py --all-markets

# Specific match and market
python scripts/debug_anomaly.py match_001 --market ht_under_05
```

---

### **API Python**

```python
from scripts.debug_anomaly import debug_full_pipeline

# Debug single market
result, breakdown = debug_full_pipeline(
    match_id="match_001",
    market_type="ft_under_25",
    mode="verbose",
    output_file="debug_report.json"
)

# Or use formatter directly
from app.services.anomaly.score_breakdown_formatter import ScoreBreakdownFormatter

formatter = ScoreBreakdownFormatter(mode="verbose")
output = formatter.format(result, breakdown)
print(output)
```

---

## 🧪 EXEMPLE EXÉCUTION

```bash
$ python scripts/debug_anomaly.py --mode compact

================================================================================
🔍 DEBUG MODE: COMPACT
================================================================================

📥 STEP 1: Fetching Data
--------------------------------------------------------------------------------
✅ Match: London City Lionesses vs Bristol City Women
   League: England Women's Championship
   Date: 2026-05-27 18:00

📊 STEP 2: Fetching Team Histories
--------------------------------------------------------------------------------
   London City Lionesses: 15 matches
   Bristol City Women: 15 matches

📈 STEP 3: Calculating Statistics
--------------------------------------------------------------------------------
   Home Stats:
     Sample: 15
     Avg Goals: 1.20
     Under 2.5: 93.3%
     Variance: 0.60
     Stability: 0.90
   Away Stats:
     Sample: 15
     Avg Goals: 1.50
     Under 2.5: 80.0%
     Variance: 0.80
     Stability: 0.75

🛡️  STEP 4: Line Breach Analysis
--------------------------------------------------------------------------------
   Line: 2.5
   Breach Rate: 13.3%
   Safety Score: 85.2/100
   Signal: VERY_SAFE

💰 STEP 5: Fetching Odds
--------------------------------------------------------------------------------
   Market: ft_under_25
   Odds: 1.85
   Bookmaker: Bet365

🎯 STEP 6: Anomaly Detection
--------------------------------------------------------------------------------
   Anomaly detected: Score 79.2 (HIGH confidence)

🧩 STEP 7: Pattern Detection
--------------------------------------------------------------------------------
   London City Lionesses Patterns: ['EXTREME_UNDER', 'LOW_TEMPO', 'BTTS_RARE']
   Bristol City Women Patterns: ['EXTREME_UNDER', 'STABLE']

================================================================================
SCORE BREAKDOWN
================================================================================

================================================================================
ANOMALY DEBUG
================================================================================

ft_under_25 | Score: 79.2 | Conf: HIGH
Book: 58.9% | Model: 73.3% | Gap: 14.4%

Components: D:77×40%=30.7 | V:83×25%=20.6 | H:73×20%=14.7 | S:88×15%=13.2
Final: 79.21 | Quality: 1.00 | Sample: 15
Signals: +1 | -1 | Risks: 1
Risks: Low sample size (15)

================================================================================

💾 JSON exported to: anomaly_debug_report.json
```

---

## 📊 PIPELINE DEBUG (7 Steps)

```
1. 📥 Fetching Data
   └─ Match info, league, date

2. 📊 Fetching Team Histories
   └─ Home: 15 matches, Away: 15 matches

3. 📈 Calculating Statistics
   └─ Avg goals, under rates, variance, stability

4. 🛡️  Line Breach Analysis
   └─ Historical breach rate, safety score, signal

5. 💰 Fetching Odds
   └─ Market, odds, bookmaker

6. 🎯 Anomaly Detection
   └─ Score breakdown, confidence

7. 🧩 Pattern Detection
   └─ Team patterns, profile
```

---

## 🎯 AVANTAGES

1. **Explicable** - Chaque score décomposé
2. **3 modes** - Verbose, compact, JSON
3. **Pipeline complet** - 7 étapes tracées
4. **Export JSON** - Pour analyse externe
5. **Tous marchés** - --all-markets
6. **Rapide** - Données mockées locales

---

## ✅ CHECKLIST

- ✅ 12 points de debug
- ✅ 3 modes (verbose, compact, json)
- ✅ 7 étapes pipeline tracées
- ✅ Score breakdown formatter
- ✅ Probabilities display
- ✅ Component scores
- ✅ Weights applied
- ✅ Signals (+/-)
- ✅ Risk factors
- ✅ Pattern detection
- ✅ Line breach analysis
- ✅ JSON export
- ✅ Console export
- ✅ Script debug_anomaly.py
- ✅ Documentation complète

---

**Debug System 100% opérationnel !** 🔍✨
