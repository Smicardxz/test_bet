# 🚀 API Guide - Football Anomaly Scanner

## 📋 Vue d'Ensemble

Backend FastAPI pour scanner les anomalies bookmakers sur ligues obscures de football.

---

## 🏗️ Architecture

```
app/
├── api/              # Endpoints FastAPI
│   └── endpoints.py
├── core/             # Configuration
│   ├── config.py
│   └── database.py
├── db/               # Database setup
│   ├── base.py
│   └── session.py
├── models/           # SQLAlchemy models
│   └── database_models.py
├── schemas/          # Pydantic schemas
│   └── schemas.py
├── engines/          # Business logic
│   ├── stats_engine.py
│   ├── anomaly_engine.py
│   ├── confidence_engine.py
│   └── explanation_engine.py
├── utils/            # Utilities
│   └── mock_data.py
└── main_api.py       # FastAPI app
```

---

## 🗄️ Modèles de Données

### **Team**
```python
- id: int
- name: str
- country: str
- league: str
- league_tier: int  # 1=top, 5+=obscure
```

### **Competition**
```python
- id: int
- name: str
- country: str
- tier: int
- is_obscure: bool
```

### **Match**
```python
- id: int
- home_team_id: int
- away_team_id: int
- competition_id: int
- match_date: datetime
- status: str  # scheduled, live, finished
- home_score, away_score: int
- home_score_ht, away_score_ht: int
- total_goals, total_goals_ht: int
- btts: bool
```

### **Odds**
```python
- id: int
- match_id: int
- bookmaker: str
- over_25_odds, under_25_odds: float
- ht_over_05_odds, ht_under_05_odds: float
- btts_yes_odds, btts_no_odds: float
```

### **MatchStats**
```python
- id: int
- team_id: int
- home_away: str  # home, away, all
- avg_goals_ft, avg_goals_ht: float
- over_25_pct, under_05_ht_pct: float
- btts_pct, btts_ht_pct: float
- pace_score: float
- is_slow_starter, is_fast_starter: bool
- variance_goals, stability_score: float
```

### **Analysis**
```python
- id: int
- match_id: int
- market_type: str  # over_under_25, ht_under_05, btts
- anomaly_score: float  # 0-100
- anomaly_level: str  # LOW, MEDIUM, HIGH, VERY_HIGH, EXTREME
- probability_gap_score: float
- historical_pattern_score: float
- bookmaker_prob, model_prob: float
- confidence_score: float
- confidence_level: str  # LOW, MEDIUM, HIGH
- signals: JSON
- explanation: text
- recommendation: text
```

---

## 🔌 Endpoints API

### **1. GET /api/v1/matches/today**

Récupère tous les matchs du jour.

**Response:**
```json
[
  {
    "id": 100,
    "home_team_id": 1,
    "away_team_id": 2,
    "competition_id": 1,
    "match_date": "2026-05-27T15:00:00",
    "status": "scheduled",
    "home_team": {
      "id": 1,
      "name": "Wrexham AFC",
      "league": "National League"
    },
    "away_team": {
      "id": 2,
      "name": "Notts County",
      "league": "National League"
    }
  }
]
```

---

### **2. GET /api/v1/analysis/{match_id}**

Analyse un match spécifique et retourne les anomalies détectées.

**Parameters:**
- `match_id` (path): ID du match

**Response:**
```json
[
  {
    "id": 1,
    "match_id": 100,
    "market_type": "ht_under_05",
    "anomaly_score": 85.3,
    "anomaly_level": "EXTREME",
    "probability_gap_score": 32.5,
    "historical_pattern_score": 28.0,
    "bookmaker_prob": 0.40,
    "model_prob": 0.72,
    "probability_gap": 0.32,
    "confidence_score": 0.82,
    "confidence_level": "HIGH",
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
    "explanation": "🎯 MARCHÉ: HT Under 0.5 (0-0 HT)\n📊 NIVEAU D'ANOMALIE: EXTREME (85.3/100)\n...",
    "recommendation": "✅ FORTE ANOMALIE - Opportunité potentielle sur HT Under 0.5 (0-0 HT)",
    "key_indicators": {
      "expected_ht": 0.75,
      "home_zero_zero_pct": 55.0,
      "away_zero_zero_pct": 60.0
    }
  }
]
```

---

### **3. GET /api/v1/scanner/top-anomalies**

Récupère les meilleures anomalies sur tous les matchs récents.

**Parameters:**
- `limit` (query, default=10): Nombre max d'anomalies
- `min_score` (query, default=45.0): Score minimum

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
        "league": "England National League",
        "match_date": "2026-05-27T15:00:00"
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
        }
      ],
      "explanation": "...",
      "recommendation": "✅ FORTE ANOMALIE - Opportunité potentielle",
      "key_indicators": {
        "expected_ht": 0.75,
        "home_zero_zero_pct": 55.0
      }
    }
  ]
}
```

---

## 🚀 Démarrage Rapide

### **1. Installation**

```bash
# Installer dépendances
pip install -r requirements.txt
```

### **2. Lancer l'API**

```bash
# Méthode 1: Script de démarrage
python run_api.py

# Méthode 2: Directement
uvicorn app.main_api:app --reload
```

### **3. Accéder à l'API**

- **API**: http://localhost:8000
- **Documentation interactive**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Tester avec Données Mockées

Les données mockées sont créées automatiquement au démarrage :

- **3 compétitions** (England National League, France National 2, Germany Regionalliga)
- **10 équipes**
- **20 matchs historiques** (pour calcul stats)
- **3 matchs à venir** (pour tester anomalies)
- **3 enregistrements odds** (avec anomalies intentionnelles)

### **Matchs de Test**

**Match 100** : Wrexham vs Notts County
- Anomalie attendue : **HT Under 0.5** (0-0 HT)
- Les deux équipes sont slow starters
- Bookmaker sous-estime à 2.50 (40%)

**Match 101** : Chesterfield vs Solihull Moors
- Anomalie attendue : **Over 2.5**
- Équipes high scoring
- Bookmaker sous-estime à 2.50

**Match 102** : FC Bastia-Borgo vs Stade Briochin
- Pas d'anomalie majeure
- Odds normales

---

## 🔧 Engines

### **StatsEngine**

Calcule les statistiques d'équipe :
- Moyennes buts (FT, HT)
- Fréquences (Over/Under, BTTS)
- Variance & stabilité
- Pace score
- Slow/Fast starters

### **AnomalyEngine**

Détecte les anomalies :
- Compare probabilités bookmaker vs modèle
- Calcule anomaly score (0-100)
- Identifie signaux
- 3 marchés : Over/Under 2.5, HT Under 0.5, BTTS

### **ConfidenceEngine**

Calcule confiance :
- Sample size factor
- Stability factor
- Anomaly magnitude factor
- Probability gap factor
- Score final (0-1)

### **ExplanationEngine**

Génère explications :
- Explication détaillée
- Recommandation
- Format human-readable

---

## 📊 Exemple Complet

### **Requête**

```bash
curl http://localhost:8000/api/v1/scanner/top-anomalies?limit=5&min_score=60
```

### **Réponse**

```json
{
  "total_matches_analyzed": 3,
  "total_anomalies_found": 2,
  "extreme_anomalies": 1,
  "very_high_anomalies": 1,
  "high_anomalies": 0,
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
      "signals": [
        {
          "signal_type": "EXTREME_PROBABILITY_GAP",
          "strength": "STRONG",
          "description": "Écart de probabilité extrême: 32.0%"
        },
        {
          "signal_type": "BOTH_SLOW_STARTERS",
          "strength": "STRONG",
          "description": "Les deux équipes démarrent lentement"
        }
      ],
      "recommendation": "✅ FORTE ANOMALIE - Opportunité potentielle"
    }
  ]
}
```

---

## ✅ Fonctionnalités

✅ **3 endpoints** API complets  
✅ **6 modèles** de données  
✅ **4 engines** de calcul  
✅ **Données mockées** pour test rapide  
✅ **Documentation** interactive (Swagger)  
✅ **Scoring 0-100** pour anomalies  
✅ **Confidence scoring** multi-facteurs  
✅ **Explications** détaillées  
✅ **Signaux** d'alerte  
✅ **SQLite** pour démarrage rapide  

**Backend FastAPI complet prêt à scanner les anomalies bookmaker !** 🚀
