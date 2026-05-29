# ⚽ Local Football Anomaly Scanner

**Version** : 3.0.0 - **Provider-Centric Architecture**

Scanner local automatique pour détecter les anomalies bookmakers sur des matchs de football de ligues obscures.

## 🎯 Objectif

Détecter les **incohérences statistiques** entre les lignes bookmakers et la réalité statistique des équipes dans les divisions inférieures et ligues peu suivies.

**Ce système NE prédit PAS les vainqueurs** - il identifie les marchés mal évalués.

## ⚡ Quick Start (2 minutes)

```bash
# 1. Installer dépendances
pip install -r requirements.txt

# 2. Démarrer Dashboard
streamlit run dashboard_v3.py

# 3. Accéder
# Dashboard: http://localhost:8501
```

## 🎲 Marchés Analysés

- **Over/Under** (2.5, 3.5, etc.)
- **Over/Under Mi-Temps**
- **BTTS** (Both Teams To Score)
- **Extrêmes** (5.5+, 6.5+, 8.5+, 10.5+, 12.5+)
- **First/Second Half Goals**

## 🏆 Ligues Ciblées

✅ **CIBLÉES** :
- Divisions inférieures (National League, Regionalliga, etc.)
- Ligues régionales
- Football féminin obscur
- U19, U21
- Équipes réserves
- Championnats secondaires/tertiaires

❌ **NON CIBLÉES** :
- Premier League, Ligue 1, Liga, Serie A, Bundesliga
- Grandes divisions majeures

## 🏗️ Architecture

### **Provider-Centric Stack**

```
Dashboard (Streamlit)
    ↓
DataSourceManager
    ↓
DataProviders (Mock / SofaScore)
    ↓
Cache (JSON local)
    ↓
Scanner (DailyScannerServiceV2)
    ↓
Engines (Stats, Anomaly, Analysis, Betting)
```

### **Structure Projet**

```
test bet/
├── dashboard_v3.py         # Streamlit dashboard
├── requirements.txt       # Dépendances simplifiées
├── app/
│   ├── config/
│   │   └── data_source_config.py  # Configuration providers
│   ├── providers/
│   │   ├── base_provider.py       # Interface provider
│   │   ├── mock_provider.py      # Provider mock (tests)
│   │   ├── sofascore_provider.py # Provider SofaScore (réel)
│   │   ├── cached_provider.py    # Cache provider
│   │   ├── data_source_manager.py # Manager providers
│   │   └── odds/                 # Providers odds
│   ├── services/
│   │   ├── scanner/
│   │   │   └── daily_scanner_v2.py  # Scanner provider-centric
│   │   ├── stats/
│   │   │   └── provider_adapter.py  # Stats sans DB
│   │   ├── anomaly/
│   │   │   └── anomaly_engine.py    # Détection anomalies
│   │   ├── analysis/
│   │   │   ├── line_breach_engine.py
│   │   │   ├── pattern_detection_engine.py
│   │   │   ├── league_profile_engine.py
│   │   │   └── priority_ranking_engine.py
│   │   ├── betting/
│   │   │   ├── bet_candidate.py
│   │   │   ├── bet_portfolio_engine.py
│   │   │   └── scan_result_converter.py
│   │   └── explanation/
│   │       └── explanation_engine.py
│   ├── cache/              # Cache JSON local
│   ├── core/
│   │   └── config.py       # Configuration application
│   └── utils/              # Utilitaires
```

## 📊 Pipeline Automatique

```
1. DataSourceManager
   ↓
   Sélection provider (Mock ou SofaScore)
   
2. DataProvider
   ↓
   Récupération matchs depuis source externe
   Cache JSON local (TTL configurable)
   
3. DailyScannerServiceV2
   ↓
   Scan matchs du jour
   Calcul stats via provider_adapter
   
4. StatsEngine (provider_adapter)
   ↓
   Calcul 50+ métriques statistiques
   (FT, HT, variance, stabilité, trending)
   
5. AnomalyEngine
   ↓
   Détection anomalies avec 8 scores
   (discrepancy, variance safety, stability)
   
6. Analysis Engines
   ↓
   Line breach, pattern detection, league profile, priority ranking
   
7. BetPortfolioEngine
   ↓
   Génération candidats de paris
```

## 🚀 Installation & Utilisation

### **Installation**

```bash
# Installer dépendances
pip install -r requirements.txt
```

### **Configuration**

```bash
# Optionnel: Configurer provider via variable d'environnement
export DATA_PROVIDER=mock        # Pour tests (défaut)
export DATA_PROVIDER=sofascore   # Pour données réelles
export CACHE_ENABLED=true        # Activer cache (défaut)
export CACHE_TTL=300            # TTL cache en secondes (défaut: 300)
```

### **Démarrer l'Application**

```bash
# Dashboard Streamlit
streamlit run dashboard_v3.py
```

### **Accès**

- **Dashboard** : `http://localhost:8501`

## 📡 Providers

### **MockProvider** (Tests)

- Données synthétiques réalistes
- Pour développement et tests
- Activé par défaut (`DATA_PROVIDER=mock`)

### **SofaScoreProvider** (Données réelles)

- Données réelles depuis API SofaScore
- Pour usage en production
- Activé via `DATA_PROVIDER=sofascore`
- Limite de taux configurable (30 req/min par défaut)

### **Cache JSON**

- Stockage local en JSON
- TTL configurable (300s par défaut)
- Vidage automatique après expiration
- Lisible et inspectable manuellement

## 🔍 Exemples d'Utilisation

### **1. Scanner avec MockProvider**

```python
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.mock_provider import MockDataProvider

scanner = DailyScannerServiceV2(MockDataProvider(), is_real_data=False)
results = scanner.scan_today()
```

### **2. Scanner avec SofaScoreProvider**

```python
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.providers.sofascore_provider import SofaScoreProvider
from app.providers import ProviderConfig

config = ProviderConfig(name="sofascore", enabled=True, cache_enabled=True)
provider = SofaScoreProvider(config)
scanner = DailyScannerServiceV2(provider, is_real_data=True)
results = scanner.scan_today()
```

### **3. DataSourceManager (recommandé)**

```python
from app.providers.data_source_manager import DataSourceManager

manager = DataSourceManager()  # Utilise DATA_PROVIDER env var
results = manager.provider.get_today_matches()
```

## 📈 Logique de Scoring

### **Anomaly Score**

```python
anomaly_score = (probability_gap * 10) + line_weight + stability_bonus - variance_penalty
```

**Facteurs** :
- `probability_gap` : Écart entre probabilité bookmaker et modèle
- `line_weight` : Différence entre ligne bookmaker et expectation statistique
- `stability_bonus` : Bonus si équipes stables
- `variance_penalty` : Pénalité si variance élevée

### **Confidence Score**

Pondération de 5 facteurs :
- **Sample Size** (25%) : Nombre de matchs analysés
- **Stability** (20%) : Stabilité des performances
- **Anomaly Magnitude** (25%) : Magnitude de l'anomalie
- **Probability Gap** (20%) : Écart de probabilité
- **Variance** (10%) : Variance des goals

**Classification** :
- `HIGH` : score ≥ 0.75
- `MEDIUM` : score ≥ 0.50
- `LOW` : score < 0.50

## 🧪 Tests

```bash
# Lancer les tests
pytest

# Avec coverage
pytest --cov=app tests/
```

## 📦 Modules Détaillés

### **1. Providers**

- `BaseDataProvider` : Interface abstraite pour tous les providers
- `MockDataProvider` : Données synthétiques pour tests
- `SofaScoreProvider` : Données réelles depuis API SofaScore
- `CachedProvider` : Cache JSON avec TTL configurable
- `DataSourceManager` : Manager pour sélection et switching providers

### **2. Scanner**

- `DailyScannerServiceV2` : Scanner provider-centric (sans DB)
- Scan automatique des matchs du jour
- Calcul stats via provider_adapter
- Ranking pondéré des anomalies

### **3. Stats Engine (provider_adapter)**

- Calcul moyennes goals (FT/HT)
- Variance et stabilité
- Pourcentages BTTS, Over/Under
- Distribution Poisson pour probabilités
- **Sans dépendance DB**

### **4. Anomaly Engine**

- Comparaison probabilités bookmaker vs modèle
- Détection écarts significatifs
- Scoring multi-facteurs
- Classification confiance

### **5. Analysis Engines**

- `HistoricalLineBreachEngine` : Détection dépassements lignes historiques
- `PatternDetectionEngine` : Détection patterns récurrents
- `LeagueProfileEngine` : Profilage ligues
- `PriorityRankingEngine` : Ranking priorité anomalies

### **6. Betting Engine**

- `BetCandidate` : Candidats de paris structurés
- `BetPortfolioEngine` : Gestion portefeuille paris
- `scan_result_converter` : Conversion résultats en candidats

### **7. Explanation Engine**

- Génération explications lisibles
- Contexte statistique détaillé
- Facteurs clés de l'anomalie

## 🎯 Architecture Simplifiée

### **Supprimé (ancienne architecture DB-centric)**

- ❌ SQLAlchemy ORM
- ❌ PostgreSQL/SQLite
- ❌ FastAPI
- ❌ Alembic migrations
- ❌ Ingestion services DB
- ❌ Models ORM
- ❌ API REST endpoints
- ❌ Backtesting engine
- ❌ Market performance analyzer

### **Conservé (architecture provider-centric)**

- ✅ Streamlit dashboard
- ✅ DataProviders (Mock, SofaScore)
- ✅ Cache JSON local
- ✅ StatsEngine (provider_adapter)
- ✅ AnomalyEngine
- ✅ Analysis engines
- ✅ Betting engine
- ✅ Explanation engine

## ⚡ Performance & Scalabilité

### **Optimisations**

1. **Cache JSON** :
   - TTL configurable (300s par défaut)
   - Stockage local lisible
   - Vidage automatique

2. **Rate Limiting** :
   - Limite configurable par provider
   - 30 req/min par défaut pour SofaScore

3. **Lazy Loading** :
   - Providers initialisés à la demande
   - Stats calculées uniquement si nécessaire

## 🔐 Sécurité

- Variables d'environnement pour configuration
- Validation Pydantic sur inputs
- Pas de stockage persistant de données sensibles
- Cache local uniquement

## ✅ Fonctionnalités Implémentées

### **Providers**
- ✅ **MockDataProvider** - Données synthétiques pour tests
- ✅ **SofaScoreProvider** - Données réelles depuis API
- ✅ **CachedProvider** - Cache JSON avec TTL
- ✅ **DataSourceManager** - Manager providers

### **Scanner**
- ✅ **DailyScannerServiceV2** - Scanner provider-centric
- ✅ Scan automatique matchs du jour
- ✅ Ranking pondéré anomalies

### **Engines**
- ✅ **StatsEngine** (provider_adapter) - 50+ métriques sans DB
- ✅ **AnomalyEngine** - 8 scores, signaux, confiance
- ✅ **HistoricalLineBreachEngine** - Détection dépassements lignes
- ✅ **PatternDetectionEngine** - Détection patterns
- ✅ **LeagueProfileEngine** - Profilage ligues
- ✅ **PriorityRankingEngine** - Ranking priorité
- ✅ **BetPortfolioEngine** - Gestion portefeuille
- ✅ **ExplanationEngine** - Explications professionnelles

### **Dashboard Streamlit**
- ✅ Interface simple et intuitive
- ✅ Filtres multiples
- ✅ Visualisation claire
- ✅ Explications détaillées
- ✅ Indicateur source de données (REAL/MOCK)

## 🎯 Caractéristiques

✅ **Local uniquement** - Pas de cloud, pas de SaaS  
✅ **Simple** - Installation en 2 minutes  
✅ **Sans DB** - Architecture provider-centric  
✅ **Léger** - 5 dépendances essentielles  
✅ **Flexible** - Switch facile Mock/Réal  
✅ **Cache intelligent** - JSON avec TTL  
✅ **Prêt** - Production locale immédiate  

## 📊 Métriques Projet

| Aspect | Valeur |
|--------|--------|
| **Lignes de code** | ~2000 (simplifié) |
| **Dépendances** | 5 (streamlit, httpx, requests, pandas, numpy) |
| **Providers** | 2 (Mock, SofaScore) |
| **Engines** | 8 |
| **Pages Dashboard** | 1 (multi-vues) |

## 🤝 Contribution

Contributions bienvenues ! Ouvrir une issue ou PR.

## 📄 Licence

MIT License

---

**⚠️ Disclaimer** : Ce système est à usage éducatif et de recherche uniquement. Les paris comportent des risques. Jouez responsable.
