# ✅ Backend FastAPI - Scanner d'Anomalies - COMPLET

## 🎯 Vue d'Ensemble

**Backend FastAPI complet** pour scanner les anomalies bookmakers sur ligues obscures de football.

---

## 📁 Structure du Projet

```
app/
├── api/
│   ├── __init__.py
│   └── endpoints.py              # 3 endpoints API
├── core/
│   ├── __init__.py
│   ├── config.py                 # Configuration
│   └── database.py               # Database setup
├── db/
│   ├── __init__.py
│   ├── base.py                   # SQLAlchemy Base
│   └── session.py                # Session & get_db
├── models/
│   ├── __init__.py
│   └── database_models.py        # 6 modèles SQLAlchemy
├── schemas/
│   ├── __init__.py
│   └── schemas.py                # Pydantic schemas
├── engines/
│   ├── __init__.py
│   ├── stats_engine.py           # Calcul statistiques
│   ├── anomaly_engine.py         # Détection anomalies
│   ├── confidence_engine.py      # Scoring confiance
│   └── explanation_engine.py     # Génération explications
├── utils/
│   ├── __init__.py
│   └── mock_data.py              # Données de test
└── main_api.py                   # Application FastAPI

run_api.py                        # Script de démarrage
API_GUIDE.md                      # Documentation API
```

---

## 🗄️ 6 Modèles de Données

### **1. Team**
```python
- id, name, country, league, league_tier
- Relationships: home_matches, away_matches, stats
```

### **2. Competition**
```python
- id, name, country, tier, is_obscure
- Relationships: matches
```

### **3. Match**
```python
- id, home_team_id, away_team_id, competition_id
- match_date, status (scheduled/live/finished)
- home_score, away_score, home_score_ht, away_score_ht
- total_goals, total_goals_ht, btts
- Relationships: home_team, away_team, competition, odds, analyses
```

### **4. Odds**
```python
- id, match_id, bookmaker
- over_25_odds, under_25_odds, over_15_odds, under_15_odds
- ht_over_05_odds, ht_under_05_odds, ht_over_15_odds, ht_under_15_odds
- btts_yes_odds, btts_no_odds, ht_btts_yes_odds, ht_btts_no_odds
- Relationship: match
```

### **5. MatchStats**
```python
- id, team_id, home_away, last_n_matches
- avg_goals_ft, avg_goals_ht, avg_goals_scored, avg_goals_conceded
- over_25_pct, under_25_pct, under_05_ht_pct, zero_zero_ht_pct
- btts_pct, btts_ht_pct
- variance_goals, stability_score
- pace_score, is_slow_starter, is_fast_starter
- Relationship: team
```

### **6. Analysis**
```python
- id, match_id, market_type
- anomaly_score (0-100), anomaly_level (LOW/MEDIUM/HIGH/VERY_HIGH/EXTREME)
- probability_gap_score, historical_pattern_score, variance_safety_score, stability_score
- bookmaker_prob, model_prob, probability_gap
- confidence_score (0-1), confidence_level (LOW/MEDIUM/HIGH)
- signals (JSON), explanation (text), recommendation (text)
- key_indicators (JSON)
- Relationship: match
```

---

## 🔌 3 Endpoints API

### **1. GET /api/v1/matches/today**

Récupère tous les matchs du jour.

**Response:**
```json
[
  {
    "id": 100,
    "home_team": {"id": 1, "name": "Wrexham AFC"},
    "away_team": {"id": 2, "name": "Notts County"},
    "competition": {"id": 1, "name": "England National League"},
    "match_date": "2026-05-27T15:00:00",
    "status": "scheduled"
  }
]
```

---

### **2. GET /api/v1/analysis/{match_id}**

Analyse un match et retourne anomalies détectées.

**Response:**
```json
[
  {
    "id": 1,
    "match_id": 100,
    "market_type": "ht_under_05",
    "anomaly_score": 85.3,
    "anomaly_level": "EXTREME",
    "confidence_score": 0.82,
    "confidence_level": "HIGH",
    "probability_gap": 0.32,
    "signals": [...],
    "explanation": "...",
    "recommendation": "✅ FORTE ANOMALIE"
  }
]
```

---

### **3. GET /api/v1/scanner/top-anomalies**

Top anomalies sur tous les matchs récents.

**Parameters:**
- `limit` (default=10): Nombre max
- `min_score` (default=45.0): Score minimum

**Response:**
```json
{
  "total_matches_analyzed": 15,
  "total_anomalies_found": 8,
  "extreme_anomalies": 2,
  "very_high_anomalies": 3,
  "high_anomalies": 3,
  "top_anomalies": [
    {
      "match_id": 100,
      "match_info": {
        "home_team": "Wrexham AFC",
        "away_team": "Notts County",
        "league": "England National League"
      },
      "market_type": "ht_under_05",
      "anomaly_score": 85.3,
      "anomaly_level": "EXTREME",
      "confidence_score": 0.82,
      "signals": [...],
      "explanation": "...",
      "recommendation": "..."
    }
  ]
}
```

---

## 🔧 4 Engines

### **1. StatsEngine**

**Fonction** : Calculer statistiques d'équipe

**Méthodes** :
- `calculate_team_stats(team_id, home_away, last_n)`
- `calculate_match_expectation(home_team_id, away_team_id)`

**Calcule** :
- Moyennes (FT, HT, scored, conceded)
- Fréquences (Over/Under, BTTS)
- Variance, stabilité, CV
- Pace score
- Slow/Fast starters

---

### **2. AnomalyEngine**

**Fonction** : Détecter anomalies bookmaker

**Méthodes** :
- `detect_match_anomalies(match_id)`
- `_check_over_under_25(odds, expectations)`
- `_check_ht_under_05(odds, expectations)`
- `_check_btts(odds, expectations)`

**Détecte** :
- Over/Under 2.5
- HT Under 0.5 (0-0 HT)
- BTTS

**Scoring** :
- Probability gap score (max 35)
- Historical pattern score (max 30)
- Stability score (max 15)
- **Total : 0-100**

---

### **3. ConfidenceEngine**

**Fonction** : Calculer confiance

**Méthode** :
- `calculate_confidence(anomaly, home_stats, away_stats)`

**Facteurs** :
- Sample size (30%)
- Stability (25%)
- Anomaly magnitude (25%)
- Probability gap (20%)

**Output** :
- confidence_score (0-1)
- confidence_level (LOW/MEDIUM/HIGH)

---

### **4. ExplanationEngine**

**Fonction** : Générer explications

**Méthodes** :
- `generate_explanation(anomaly, match_info)`
- `generate_recommendation(anomaly)`

**Output** :
- Explication détaillée
- Recommandation
- Format human-readable

---

## 🧪 Données Mockées

### **Créées Automatiquement**

- **3 compétitions** (England, France, Germany)
- **10 équipes**
- **20 matchs historiques** (pour stats)
- **3 matchs à venir** (pour test)
- **3 enregistrements odds**

### **Matchs de Test**

**Match 100** : Wrexham vs Notts County
- **Anomalie** : HT Under 0.5 (0-0 HT)
- Slow starters
- Bookmaker @ 2.50 (40%) vs Modèle 72%
- **Score attendu** : 85/100 (EXTREME)

**Match 101** : Chesterfield vs Solihull Moors
- **Anomalie** : Over 2.5
- High scoring
- Bookmaker @ 2.50 vs Modèle élevé
- **Score attendu** : 70/100 (VERY_HIGH)

**Match 102** : FC Bastia-Borgo vs Stade Briochin
- Pas d'anomalie majeure
- Odds normales

---

## 🚀 Démarrage

### **Installation**

```bash
pip install -r requirements.txt
```

### **Lancer l'API**

```bash
# Méthode 1: Script
python run_api.py

# Méthode 2: Directement
uvicorn app.main_api:app --reload
```

### **Accès**

- **API** : http://localhost:8000
- **Docs** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

---

## 📊 Exemple d'Utilisation

### **1. Récupérer matchs du jour**

```bash
curl http://localhost:8000/api/v1/matches/today
```

### **2. Analyser un match**

```bash
curl http://localhost:8000/api/v1/analysis/100
```

### **3. Top anomalies**

```bash
curl "http://localhost:8000/api/v1/scanner/top-anomalies?limit=5&min_score=60"
```

### **Réponse Exemple**

```json
{
  "total_matches_analyzed": 3,
  "total_anomalies_found": 2,
  "extreme_anomalies": 1,
  "top_anomalies": [
    {
      "match_id": 100,
      "match_info": {
        "home_team": "Wrexham AFC",
        "away_team": "Notts County",
        "league": "England National League"
      },
      "market_type": "ht_under_05",
      "anomaly_score": 85.3,
      "anomaly_level": "EXTREME",
      "confidence_score": 0.82,
      "confidence_level": "HIGH",
      "probability_gap": 0.32,
      "bookmaker_prob": 0.40,
      "model_prob": 0.72,
      "signals": [
        {
          "signal_type": "EXTREME_PROBABILITY_GAP",
          "strength": "STRONG",
          "description": "Écart de probabilité extrême: 32.0%",
          "value": 0.32
        },
        {
          "signal_type": "BOTH_SLOW_STARTERS",
          "strength": "STRONG",
          "description": "Les deux équipes démarrent lentement",
          "value": 57.5
        }
      ],
      "explanation": "🎯 MARCHÉ: HT Under 0.5 (0-0 HT)\n📊 NIVEAU D'ANOMALIE: EXTREME (85.3/100)\n\n📊 PROBABILITÉS:\n  • Bookmaker: 40.00%\n  • Modèle:    72.00%\n  • Gap:       32.00%\n\n📈 INDICATEURS CLÉS:\n  • Expected Ht: 0.75\n  • Home Zero Zero Pct: 55.00\n  • Away Zero Zero Pct: 60.00\n\n🔔 SIGNAUX DÉTECTÉS:\n  • [STRONG] Écart de probabilité extrême: 32.0%\n  • [STRONG] Les deux équipes démarrent lentement",
      "recommendation": "✅ FORTE ANOMALIE - Opportunité potentielle sur HT Under 0.5 (0-0 HT)",
      "key_indicators": {
        "expected_ht": 0.75,
        "home_zero_zero_pct": 55.0,
        "away_zero_zero_pct": 60.0,
        "home_pace": 0.25,
        "away_pace": 0.28
      }
    }
  ]
}
```

---

## ✅ Fonctionnalités Complètes

### **Backend**

✅ FastAPI avec documentation auto  
✅ SQLAlchemy ORM  
✅ Pydantic validation  
✅ SQLite (démarrage rapide)  
✅ CORS configuré  

### **Modèles**

✅ 6 modèles de données  
✅ Relationships SQLAlchemy  
✅ JSON fields pour flexibilité  

### **Endpoints**

✅ 3 endpoints API  
✅ Pagination & filtres  
✅ Validation Pydantic  
✅ Error handling  

### **Engines**

✅ StatsEngine (calcul stats)  
✅ AnomalyEngine (détection)  
✅ ConfidenceEngine (scoring)  
✅ ExplanationEngine (explications)  

### **Données**

✅ Mock data generator  
✅ 3 matchs de test  
✅ Anomalies intentionnelles  
✅ Prêt à tester  

### **Documentation**

✅ API_GUIDE.md complet  
✅ Swagger UI  
✅ ReDoc  
✅ Exemples curl  

---

## 🎯 Stack Technique

| Composant | Technologie |
|-----------|-------------|
| **Framework** | FastAPI |
| **ORM** | SQLAlchemy |
| **Validation** | Pydantic |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Server** | Uvicorn |
| **Language** | Python 3.10+ |

---

## 📈 Prochaines Étapes

Pour passer en production :

1. **PostgreSQL** : Remplacer SQLite
2. **Alembic** : Migrations de base de données
3. **Redis** : Cache pour performances
4. **Celery** : Tasks asynchrones
5. **Authentication** : JWT tokens
6. **Rate limiting** : Protection API
7. **Logging** : Structured logging
8. **Monitoring** : Prometheus/Grafana
9. **Docker** : Containerisation
10. **CI/CD** : GitHub Actions

---

**Backend FastAPI complet et fonctionnel pour scanner les anomalies bookmaker !** 🚀⚽
