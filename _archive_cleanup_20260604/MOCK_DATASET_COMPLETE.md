# 🎲 Mock Dataset Réaliste - Documentation

**Version** : 1.0.0  
**Date** : 27 Mai 2026  
**Objectif** : Dataset de test réaliste avec anomalies intentionnelles

---

## 🎯 Vue d'Ensemble

Dataset mock complet pour tester le moteur d'anomalies localement avec :
- **Ligues obscures** réalistes
- **Anomalies intentionnelles** (fortes, faibles)
- **Variance variée** (faible, forte)
- **Profils d'équipes** diversifiés

---

## 🏆 LIGUES INCLUSES

### **4 Ligues Obscures**

| Ligue | Type | Pays | Teams | Profil |
|-------|------|------|-------|--------|
| **England Women's Championship** | Women | England | 6 | Défensif, HT Under |
| **England U21 Premier League Division 1** | Youth | England | 4 | Haute variance |
| **England National League North** | Lower Div | England | 6 | Très défensif, Extreme Under |
| **France National 3 - Group A** | Regional | France | 4 | Mixte |

**Total** : 20 équipes, 4 ligues

---

## 👥 PROFILS D'ÉQUIPES

### **Profile 1: Très Défensif (HT Under)**

**Équipes** : London City Lionesses, Bristol City, Charlton Athletic, Durham

**Caractéristiques** :
- Avg HT goals: **0.2-0.3**
- HT 0-0 rate: **70-80%**
- Variance: **0.25-0.35** (faible)
- Stability: **0.82-0.88** (élevée)

**Anomalies attendues** : HT Under 0.5 (STRONG)

---

### **Profile 2: Modéré**

**Équipes** : Lewes Women, Southampton Women

**Caractéristiques** :
- Avg HT goals: **0.5-0.6**
- HT 0-0 rate: **45-50%**
- Variance: **0.8-0.85** (modérée)
- Stability: **0.62-0.65**

**Anomalies attendues** : Weak anomalies

---

### **Profile 3: Haute Variance (Youth)**

**Équipes** : Manchester United U21, Chelsea U21, Arsenal U21, Liverpool U21

**Caractéristiques** :
- Avg FT goals: **2.1-2.5**
- Variance: **2.3-2.8** (très élevée)
- Stability: **0.40-0.48** (faible)
- BTTS rate: **65-72%**

**Anomalies attendues** : False positives, High risk

---

### **Profile 4: Très Bas Scoring (Extreme Under)**

**Équipes** : Curzon Ashton, Farsley Celtic, Brackley Town, etc.

**Caractéristiques** :
- Avg FT goals: **0.7-1.0**
- Variance: **0.45-0.6** (faible)
- Stability: **0.70-0.82** (élevée)
- HT 0-0 rate: **58-70%**

**Anomalies attendues** : Extreme Under (6.5, 8.5, 10.5) STRONG

---

### **Profile 5: Mixte**

**Équipes** : US Avranches, Stade Briochin, Granville, Vitré

**Caractéristiques** :
- Avg FT goals: **1.1-1.5**
- Variance: **0.9-1.3** (modérée)
- Stability: **0.65-0.72**

**Anomalies attendues** : Mixed scenarios

---

## 🎯 ANOMALIES INTENTIONNELLES

### **7 Types d'Anomalies**

| Type | Description | Fréquence | Marchés |
|------|-------------|-----------|---------|
| **ht_under_strong** | HT Under 0.5 forte | 25% | HT Under 0.5 |
| **extreme_under_strong** | Extreme Under forte | 20% | Under 6.5, 8.5, 10.5 |
| **btts_strong** | BTTS forte | 15% | BTTS |
| **stable_under** | Under stable (faible variance) | 15% | Under 2.5 |
| **high_variance** | Haute variance (risqué) | 10% | Tous |
| **weak_anomaly** | Anomalie faible | 10% | Tous |
| **coherent** | Lignes cohérentes | 5% | Tous |

---

### **Anomalie 1: HT Under Strong**

**Conditions** :
- Avg HT goals < 0.4
- HT 0-0 rate > 65%

**Odds générées** :
- HT Under 0.5: **2.50** (40% implicite)
- Probabilité réelle: **~70%**
- **Écart: 30%** (STRONG)

**Exemple** :
```
London City Lionesses vs Bristol City
HT 0-0 rate combinée: 72.5%
Bookmaker: 2.50 (40%)
Modèle: 1.43 (70%)
→ STRONG ANOMALY
```

---

### **Anomalie 2: Extreme Under Strong**

**Conditions** :
- Avg FT goals < 1.8
- Variance < 0.6

**Odds générées** :
- Under 10.5: **1.50** (67% implicite)
- Probabilité réelle: **~95%**
- **Écart: 28%** (STRONG)

**Exemple** :
```
Curzon Ashton vs Brackley Town
Avg combined: 1.5 goals
Bookmaker Under 10.5: 1.50 (67%)
Modèle: 1.10 (95%)
→ EXTREME UNDER ANOMALY
```

---

### **Anomalie 3: BTTS Strong**

**Conditions** :
- BTTS rate > 60%

**Odds générées** :
- BTTS Yes: **2.20** (45% implicite)
- Probabilité réelle: **~67%**
- **Écart: 22%** (STRONG)

**Exemple** :
```
Manchester United U21 vs Liverpool U21
BTTS rate combinée: 71%
Bookmaker: 2.20 (45%)
Modèle: 1.50 (67%)
→ BTTS ANOMALY
```

---

### **Anomalie 4: Stable Under**

**Conditions** :
- Variance < 0.6
- Avg goals < 2.5

**Odds générées** :
- Under 2.5: **2.00** (50% implicite)
- Probabilité réelle: **~63%**
- **Écart: 13%** (MODERATE)

---

### **Anomalie 5: High Variance (False Positive)**

**Conditions** :
- Variance > 2.0

**Odds générées** :
- Cohérentes mais risquées
- Variance élevée réduit confiance

**Exemple** :
```
Arsenal U21 vs Chelsea U21
Variance: 2.45
Odds cohérentes mais:
→ LOW CONFIDENCE (high variance)
```

---

### **Anomalie 6: Weak Anomaly**

**Odds générées** :
- Petit écart (~10%)
- Devrait être filtré par min_anomaly_score

---

### **Anomalie 7: Coherent**

**Odds générées** :
- Cohérentes avec statistiques
- Pas d'anomalie détectée

---

## 📊 DONNÉES GÉNÉRÉES

### **Structure Dataset**

```json
{
  "teams": [...],              // 20 équipes
  "historical_matches": [...], // ~300 matchs (15 par équipe)
  "upcoming_matches": [...],   // ~10 matchs du jour
  "odds": [...],               // Odds pour matchs du jour
  "metadata": {...}
}
```

---

### **Team Data**

```json
{
  "id": 1,
  "name": "London City Lionesses Women",
  "league": "England Women's Championship",
  "country": "England",
  "avg_goals_scored": 0.6,
  "avg_goals_conceded": 0.4,
  "avg_ht_goals": 0.2,
  "ht_0_0_rate": 75.0,
  "btts_rate": 25.0,
  "variance": 0.3,
  "stability": 0.85
}
```

---

### **Match Data**

```json
{
  "id": 1,
  "home_team_id": 1,
  "away_team_id": 2,
  "league": "England Women's Championship",
  "match_date": "2026-05-20T15:00:00",
  "status": "finished",
  "home_score": 1,
  "away_score": 0,
  "home_score_ht": 0,
  "away_score_ht": 0
}
```

---

### **Odds Data**

```json
{
  "match_id": 1,
  "under_15_odds": 3.20,
  "under_25_odds": 2.00,
  "over_25_odds": 1.95,
  "under_35_odds": 1.60,
  "over_35_odds": 2.40,
  "under_65_odds": 1.35,
  "under_85_odds": 1.25,
  "under_105_odds": 1.15,
  "ht_under_05_odds": 2.50,
  "ht_over_05_odds": 1.60,
  "ht_under_15_odds": 1.40,
  "btts_yes_odds": 3.00,
  "btts_no_odds": 1.40
}
```

---

## 💻 UTILISATION

### **Générer Dataset**

```bash
python app/utils/mock_dataset_generator.py
```

**Output** :
- `mock_dataset_complete.json` - Dataset complet
- `mock_teams.json` - Équipes uniquement
- `mock_matches.json` - Matchs historiques
- `mock_upcoming.json` - Matchs à venir
- `mock_odds.json` - Odds uniquement

---

### **Charger dans Database**

```bash
python app/utils/load_mock_dataset.py
```

**Actions** :
1. Crée tables SQLite
2. Charge équipes
3. Charge matchs historiques
4. Charge matchs à venir
5. Charge odds

---

### **Tester Scanner**

```bash
python examples/daily_scanner_usage.py
```

**Résultats attendus** :
- ~10 matchs du jour
- ~5-8 anomalies détectées
- Mix de CRITICAL, HIGH, MEDIUM
- Variance de confiance (LOW, MEDIUM, HIGH)

---

## 🧪 SCÉNARIOS DE TEST

### **Test 1: HT Under Detection**

**Match** : London City Lionesses vs Bristol City

**Attendu** :
- Anomaly score: **75-85**
- Confidence: **HIGH**
- Market: `ht_under_05`
- Signals: LOW_VARIANCE, HIGH_STABILITY

---

### **Test 2: Extreme Under Detection**

**Match** : Curzon Ashton vs Brackley Town

**Attendu** :
- Anomaly score: **80-90**
- Confidence: **HIGH**
- Market: `ft_under_105`
- Signals: EXTREME_DISCREPANCY

---

### **Test 3: BTTS Detection**

**Match** : Manchester United U21 vs Liverpool U21

**Attendu** :
- Anomaly score: **65-75**
- Confidence: **MEDIUM** (high variance)
- Market: `btts`
- Risk factors: HIGH_VARIANCE

---

### **Test 4: False Positive Filtering**

**Match** : Arsenal U21 vs Chelsea U21

**Attendu** :
- Détection anomalie
- **Filtré** par variance élevée
- Confidence: **LOW**
- Risk factors: HIGH_VARIANCE, LOW_STABILITY

---

### **Test 5: Weak Anomaly Filtering**

**Match** : US Avranches vs Granville

**Attendu** :
- Anomaly score: **45-55**
- **Filtré** par min_anomaly_score (50)
- Pas dans top résultats

---

## 📈 STATISTIQUES ATTENDUES

### **Distribution Anomalies**

| Catégorie | Nombre | % |
|-----------|--------|---|
| CRITICAL priority | 3-4 | 30-40% |
| HIGH priority | 4-5 | 40-50% |
| MEDIUM priority | 1-2 | 10-20% |

### **Distribution Confiance**

| Confiance | Nombre | % |
|-----------|--------|---|
| HIGH | 3-4 | 30-40% |
| MEDIUM | 3-4 | 30-40% |
| LOW (filtered) | 2-3 | 20-30% |

---

## ✅ VALIDATION

### **Checklist Dataset**

- [x] 20 équipes créées
- [x] 4 ligues obscures
- [x] ~300 matchs historiques (15 par équipe)
- [x] ~10 matchs du jour
- [x] Odds avec anomalies intentionnelles
- [x] Profils variés (défensif, offensif, variance)
- [x] HT scores cohérents (≤ FT)
- [x] Anomalies fortes (30%+ écart)
- [x] Anomalies faibles (10-15% écart)
- [x] Lignes cohérentes
- [x] Faux positifs (haute variance)

---

## 🎯 OBJECTIFS ATTEINTS

✅ **Ligues obscures** - Women, Youth, Lower divisions  
✅ **Équipes réalistes** - Noms et profils crédibles  
✅ **Anomalies fortes** - HT Under, Extreme Under, BTTS  
✅ **Anomalies faibles** - Pour tester filtrage  
✅ **Variance variée** - Faible (stable) et forte (risqué)  
✅ **Faux positifs** - Haute variance détectée  
✅ **Données complètes** - HT, FT, odds, stats  

---

**Dataset mock réaliste prêt pour tester le moteur localement !** 🎲✨
