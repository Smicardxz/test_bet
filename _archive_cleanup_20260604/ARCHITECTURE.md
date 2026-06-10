# 🏗️ Architecture Technique

## Vue d'Ensemble

Le système est conçu comme un **scanner d'inefficiences statistiques** modulaire et scalable.

## 🎯 Principes de Design

### 1. **Separation of Concerns**

Chaque module a une responsabilité unique :
- `ingestion/` : Collecte de données
- `stats_engine/` : Calculs statistiques
- `anomaly_engine/` : Détection anomalies
- `confidence_engine/` : Scoring confiance
- `explanation_engine/` : Génération explications

### 2. **Dependency Injection**

Tous les services reçoivent la session DB via injection :

```python
class StatsCalculator:
    def __init__(self, db: Session):
        self.db = db
```

### 3. **Stateless Services**

Services sans état interne - facilite scaling horizontal.

### 4. **Database-Centric**

PostgreSQL comme source de vérité unique.

## 📊 Schéma de Base de Données

### **Tables Principales**

```sql
teams
├── id (PK)
├── name
├── league
├── country
├── division_tier
└── is_obscure

matches
├── id (PK)
├── home_team_id (FK → teams)
├── away_team_id (FK → teams)
├── league
├── match_date
├── status
├── home_score / away_score
└── total_goals

odds
├── id (PK)
├── match_id (FK → matches)
├── bookmaker
├── market_type (ENUM)
├── line
├── over_odds / under_odds
└── timestamp

odds_markets (agrégation)
├── id (PK)
├── match_id (FK → matches)
├── market_type
├── avg_over_odds / avg_under_odds
└── implied_probability_over/under

team_stats
├── id (PK)
├── team_id (FK → teams)
├── matches_analyzed
├── avg_goals_scored/conceded
├── variance_goals_scored/conceded
├── btts_percentage
├── stability_score
└── home_away_split

anomalies
├── id (PK)
├── match_id (FK → matches)
├── market_type
├── anomaly_score
├── confidence_level (ENUM: HIGH/MEDIUM/LOW)
├── confidence_score
├── probability_gap
├── explanation
└── factors (JSON)
```

### **Relations**

```
Team 1---* Match (home_team)
Team 1---* Match (away_team)
Match 1---* Odds
Match 1---* OddsMarket
Match 1---* Anomaly
Team 1---* TeamStats
```

## 🔄 Flux de Données

### **1. Ingestion Pipeline**

```
External API
    ↓
MatchIngestionService.fetch_upcoming_matches()
    ↓
Save to DB (matches, teams)
    ↓
OddsIngestionService.save_odds()
    ↓
OddsIngestionService.calculate_market_averages()
    ↓
Data ready for analysis
```

### **2. Analysis Pipeline**

```
Match ID
    ↓
StatsCalculator.calculate_team_stats()
    ↓ (pour home & away)
StatsCalculator.calculate_match_expectation()
    ↓
AnomalyDetector.detect_match_anomalies()
    ↓ (pour chaque market)
ConfidenceScorer.calculate_confidence()
    ↓
ExplanationGenerator.generate_explanation()
    ↓
Anomaly saved with explanation
```

## 🧩 Modules Détaillés

### **1. Ingestion Module**

**Responsabilités** :
- Fetch data from external APIs
- Normalize & validate data
- Store in database
- Handle duplicates

**Services** :
- `MatchIngestionService` : Matches & teams
- `OddsIngestionService` : Odds & market averages
- `HistoricalDataService` : Historical data queries

**API Utilisée** :
- The Odds API (https://the-odds-api.com)
- Filtrage sur ligues obscures uniquement

### **2. Stats Engine**

**Responsabilités** :
- Calculer statistiques équipes
- Calculer expectations matchs
- Distribution Poisson pour probabilités

**Métriques Calculées** :

```python
{
    "avg_goals_scored": float,
    "avg_goals_conceded": float,
    "avg_total_goals": float,
    "avg_goals_scored_ht": float,
    "avg_goals_conceded_ht": float,
    "btts_percentage": float,
    "over_25_percentage": float,
    "variance_goals_scored": float,
    "stability_score": float  # 0-1
}
```

**Formules** :

```python
# Expected goals
expected_home = (home_avg_scored + away_avg_conceded) / 2
expected_away = (away_avg_scored + home_avg_conceded) / 2
expected_total = expected_home + expected_away

# Stability score
stability = max(0, 1 - (combined_variance / 10))

# Poisson probability
prob_over = 1 - poisson.cdf(line, lambda_param)
```

### **3. Anomaly Engine**

**Responsabilités** :
- Comparer bookmaker vs modèle
- Calculer anomaly score
- Filtrer anomalies significatives

**Algorithme** :

```python
def _calculate_anomaly_score(prob_gap, line_diff, variance, stability):
    base_score = prob_gap * 10
    line_weight = min(abs(line_diff) * 0.5, 2.0)
    variance_penalty = max(0, 1 - (variance / 5))
    stability_bonus = stability * 0.5
    
    return base_score + line_weight + stability_bonus - (1 - variance_penalty)
```

**Seuils** :
- `anomaly_score >= 2.0` : Anomalie détectée
- `anomaly_score >= 3.0` : Anomalie forte
- `anomaly_score >= 5.0` : Anomalie très forte

### **4. Confidence Engine**

**Responsabilités** :
- Évaluer qualité des données
- Scorer confiance multi-facteurs
- Classifier HIGH/MEDIUM/LOW

**Facteurs** :

| Facteur | Poids | Description |
|---------|-------|-------------|
| Sample Size | 25% | Nombre de matchs analysés |
| Stability | 20% | Stabilité performances |
| Anomaly Magnitude | 25% | Magnitude anomalie |
| Probability Gap | 20% | Écart probabilité |
| Variance | 10% | Variance goals |

**Scoring** :

```python
confidence_score = Σ (factor_score * weight)

if confidence_score >= 0.75: HIGH
elif confidence_score >= 0.50: MEDIUM
else: LOW
```

### **5. Explanation Engine**

**Responsabilités** :
- Générer explications lisibles
- Contextualiser avec stats
- Identifier facteurs clés

**Format** :

```
📊 ANOMALY DETECTED: Over 2.5 goals appears UNDERVALUED

🎯 Statistical Expectation: 3.2 goals
📉 Bookmaker Line: 2.5 goals
⚠️ Probability Gap: 15.3%

📈 Team A (Home):
  • Avg Goals Scored: 2.1
  • Avg Goals Conceded: 1.5
  • Over 2.5: 65.0%

📉 Team B (Away):
  • Avg Goals Scored: 1.8
  • Avg Goals Conceded: 1.9
  • Over 2.5: 58.0%

✅ HIGH STABILITY: Both teams show consistent patterns

🔍 Confidence: HIGH (78%)
🎲 Anomaly Score: 4.2
```

## 🚀 API Layer

### **Architecture FastAPI**

```python
app/
├── main.py              # FastAPI app
├── api/
│   ├── routes/
│   │   ├── anomalies.py  # GET anomalies
│   │   ├── matches.py    # GET matches
│   │   ├── analysis.py   # POST analyze
│   │   └── stats.py      # GET/POST stats
│   └── schemas.py        # Pydantic models
```

### **Endpoints Design**

**RESTful** :
- `GET /anomalies/` : Liste anomalies
- `GET /anomalies/{id}` : Détail anomalie
- `POST /analysis/analyze-match` : Analyser match
- `POST /analysis/scan-upcoming` : Scan batch

**Query Parameters** :
- Filtrage : `?min_score=3.0&confidence_level=HIGH`
- Pagination : `?limit=50&offset=0`
- Tri : `?sort_by=anomaly_score&order=desc`

## 🔧 Configuration & Environment

### **Settings Management**

```python
# app/core/config.py
class Settings(BaseSettings):
    DATABASE_URL: str
    API_ODDS_KEY: str
    MIN_MATCHES_FOR_STATS: int = 5
    ANOMALY_THRESHOLD: float = 2.0
    
    class Config:
        env_file = ".env"
```

### **Database Connection**

```python
# app/core/database.py
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
```

## 📈 Scalabilité

### **Horizontal Scaling**

Services stateless → facile à scaler :

```
Load Balancer
    ↓
[API Instance 1] [API Instance 2] [API Instance 3]
    ↓
PostgreSQL (single source of truth)
```

### **Async Processing**

Pour analyses batch :

```python
# Celery tasks
@celery.task
def analyze_match_async(match_id):
    # Long-running analysis
    pass

# FastAPI background tasks
@app.post("/analysis/scan")
def scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(analyze_all_matches)
```

### **Caching Strategy**

```python
# Redis cache
@cache(ttl=3600)  # 1 hour
def get_team_stats(team_id):
    # Expensive calculation
    pass
```

## 🔍 Monitoring & Observability

### **Metrics (Prometheus)**

```python
from prometheus_client import Counter, Histogram

anomalies_detected = Counter('anomalies_detected_total', 'Total anomalies')
analysis_duration = Histogram('analysis_duration_seconds', 'Analysis time')
```

### **Logging**

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

## 🔐 Sécurité

### **Input Validation**

```python
# Pydantic schemas
class AnalysisRequest(BaseModel):
    match_id: int = Field(..., gt=0)
```

### **Rate Limiting**

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/anomalies/")
@limiter.limit("100/minute")
def get_anomalies():
    pass
```

## 🧪 Testing Strategy

### **Unit Tests**

```python
def test_anomaly_score_calculation():
    score = calculate_anomaly_score(
        prob_gap=0.15,
        line_diff=0.5,
        variance=2.0,
        stability=0.8
    )
    assert score > 2.0
```

### **Integration Tests**

```python
def test_full_analysis_pipeline(db_session):
    match = create_test_match(db_session)
    anomalies = analyze_match(match.id, db_session)
    assert len(anomalies) > 0
```

## 📦 Déploiement

### **Docker**

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Docker Compose**

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: betting_anomaly
  
  redis:
    image: redis:7
```

---

**Architecture évolutive, modulaire, et prête pour la production.**
