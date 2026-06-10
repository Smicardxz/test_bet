# 🔌 Data Providers - Architecture Complète

**Version** : 1.0.0  
**Date** : 27 Mai 2026  
**Statut** : ✅ OPÉRATIONNEL

---

## 🎯 Objectif

Créer une **couche d'abstraction propre** pour l'extraction de données depuis des sources externes (SofaScore, Flashscore, etc.) sans mélanger extraction et logique métier.

---

## 🏗️ Architecture

### **Principe de Design**

```
Scanner/Engines (Logique Métier)
        ↓
    Interface BaseDataProvider
        ↓
    ┌───────┬───────┬───────┐
    │       │       │       │
MockProvider SofaScore FlashScore ...
```

**Avantages** :
- ✅ Séparation extraction/logique métier
- ✅ Interface générique
- ✅ Providers interchangeables
- ✅ Tests faciles (MockProvider)
- ✅ Extension simple (nouveaux providers)

---

## 📁 Structure

```
app/providers/
├── __init__.py              # Exports
├── models.py                # Modèles Pydantic normalisés
├── base_provider.py         # Interface abstraite
├── mock_provider.py         # Provider mock pour tests
├── sofascore_provider.py    # Provider SofaScore (template)
└── flashscore_provider.py   # Provider Flashscore (futur)
```

---

## 📊 Modèles Normalisés

### **MatchDetails**

```python
class MatchDetails(BaseModel):
    id: str                      # Provider-specific ID
    home_team: TeamInfo
    away_team: TeamInfo
    competition: CompetitionInfo
    match_date: datetime
    status: MatchStatus
    score_fulltime: Optional[MatchScore]
    score_halftime: Optional[MatchScore]
    venue: Optional[str]
    provider: str
    provider_url: Optional[str]
    last_updated: datetime
```

### **TeamInfo**

```python
class TeamInfo(BaseModel):
    id: str
    name: str
    short_name: Optional[str]
    country: Optional[str]
    logo_url: Optional[str]
```

### **MatchOdds**

```python
class MatchOdds(BaseModel):
    bookmaker: str
    market_type: str
    line: Optional[float]
    over_odds: Optional[float]
    under_odds: Optional[float]
    yes_odds: Optional[float]
    no_odds: Optional[float]
    timestamp: datetime
```

---

## 🔧 Interface BaseDataProvider

### **Méthodes Abstraites**

Tous les providers doivent implémenter :

```python
@abstractmethod
def get_today_matches(
    competition_ids: Optional[List[str]] = None
) -> ProviderResponse:
    """Get all matches scheduled for today"""
    pass

@abstractmethod
def get_match_details(match_id: str) -> ProviderResponse:
    """Get detailed information for a specific match"""
    pass

@abstractmethod
def get_team_recent_matches(
    team_id: str,
    limit: int = 10
) -> ProviderResponse:
    """Get recent matches for a team"""
    pass

@abstractmethod
def get_head_to_head(
    team_a_id: str,
    team_b_id: str,
    limit: int = 10
) -> ProviderResponse:
    """Get head-to-head statistics"""
    pass

@abstractmethod
def get_competition_matches(
    competition_id: str,
    match_date: Optional[date] = None
) -> ProviderResponse:
    """Get matches for a specific competition"""
    pass

@abstractmethod
def get_odds(match_id: str) -> ProviderResponse:
    """Get odds for a specific match (if available)"""
    pass
```

---

## 🛠️ Fonctionnalités Intégrées

### **1. Rate Limiting**

```python
config = ProviderConfig(
    name="provider",
    rate_limit_per_minute=60
)
```

- Limite automatique de requêtes
- Attente automatique si limite atteinte
- Logs clairs

---

### **2. Cache Local**

```python
config = ProviderConfig(
    name="provider",
    cache_enabled=True,
    cache_ttl_seconds=300  # 5 minutes
)
```

- Cache automatique des réponses
- TTL configurable
- Évite requêtes répétées
- Stockage local `.cache/providers/{name}/`

---

### **3. Retry avec Backoff**

```python
config = ProviderConfig(
    name="provider",
    retry_attempts=3,
    retry_delay_seconds=2
)
```

- Retry automatique en cas d'échec
- Backoff exponentiel (2s, 4s, 8s)
- Logs des tentatives

---

### **4. Gestion Erreurs**

```python
response = provider.get_match_details("123")

if response.success:
    match = response.data
else:
    print(f"Error: {response.error}")
```

- Réponses normalisées
- Erreurs explicites
- Pas d'exceptions non gérées

---

### **5. Logging**

```python
logger = logging.getLogger("app.providers.sofascore")
```

- Logs structurés
- Niveaux appropriés (DEBUG, INFO, WARNING, ERROR)
- Traçabilité complète

---

## 📝 Utilisation

### **Exemple 1 : Mock Provider**

```python
from app.providers import MockDataProvider

# Create provider
provider = MockDataProvider()

# Get today's matches
response = provider.get_today_matches()

if response.success:
    for match in response.data:
        print(f"{match.home_team.name} vs {match.away_team.name}")
```

---

### **Exemple 2 : Avec Cache**

```python
from app.providers import MockDataProvider, ProviderConfig

config = ProviderConfig(
    name="cached",
    cache_enabled=True,
    cache_ttl_seconds=300
)

provider = MockDataProvider(config)

# First request (fetches data)
response = provider.get_today_matches()
print(f"Cached: {response.cached}")  # False

# Second request (from cache)
response = provider.get_today_matches()
print(f"Cached: {response.cached}")  # True
print(f"Age: {response.cache_age_seconds}s")
```

---

### **Exemple 3 : Filtrage**

```python
# Filter by competition
response = provider.get_today_matches(
    competition_ids=["eng_women_champ", "eng_u21"]
)

# Get competition matches
response = provider.get_competition_matches("eng_women_champ")

# Get team recent matches
response = provider.get_team_recent_matches("team_id", limit=10)
```

---

### **Exemple 4 : Odds**

```python
response = provider.get_odds("match_id")

if response.success:
    for odds in response.data:
        print(f"Market: {odds.market_type}")
        print(f"  Under {odds.line}: {odds.under_odds}")
        print(f"  Over {odds.line}: {odds.over_odds}")
```

---

## 🧪 Tests

### **Tests Unitaires**

```bash
pytest tests/test_providers.py -v
```

**Couverture** :
- ✅ MockProvider toutes méthodes
- ✅ Gestion erreurs
- ✅ Cache fonctionnel
- ✅ Filtrage
- ✅ Modèles Pydantic

---

### **Tests avec Réponses Mockées**

```python
def test_provider_with_mock_response():
    """Test provider with mocked HTTP response"""
    
    # Mock HTTP response
    mock_response = {
        "events": [
            {"id": "123", "homeTeam": {...}, ...}
        ]
    }
    
    # Test provider mapping
    provider = SofaScoreProvider(config)
    # ... test logic
```

---

## 🔌 Providers Disponibles

### **1. MockProvider** ✅

**Statut** : Opérationnel  
**Usage** : Tests et développement

```python
from app.providers import MockDataProvider

provider = MockDataProvider()
```

**Données** :
- 4 compétitions obscures
- 8 équipes
- 4 matchs du jour
- Historiques synthétiques
- Odds réalistes

---

### **2. SofaScoreProvider** ⚠️

**Statut** : Template/Structure  
**Usage** : Nécessite implémentation complète

```python
from app.providers.sofascore_provider import SofaScoreProvider

config = ProviderConfig(
    name="sofascore",
    base_url="https://api.sofascore.com/api/v1",
    rate_limit_per_minute=30
)

provider = SofaScoreProvider(config)
```

**Avant utilisation** :
1. ⚠️ Vérifier Terms of Service SofaScore
2. ⚠️ Obtenir accès API si nécessaire
3. ⚠️ Implémenter authentification
4. ⚠️ Tester structure réponses API
5. ⚠️ Ajuster mapping des données

---

### **3. FlashScoreProvider** 🔜

**Statut** : À créer  
**Usage** : Futur

Structure similaire à SofaScoreProvider.

---

## 🎯 Intégration avec Scanner

### **Étape 1 : Créer Provider**

```python
from app.providers import MockDataProvider

provider = MockDataProvider()
```

---

### **Étape 2 : Récupérer Matchs**

```python
response = provider.get_today_matches(
    competition_ids=["eng_women_champ", "eng_u21"]
)

matches = response.data if response.success else []
```

---

### **Étape 3 : Pour Chaque Match**

```python
for match in matches:
    # Get team stats
    home_response = provider.get_team_recent_matches(
        match.home_team.id,
        limit=15
    )
    
    away_response = provider.get_team_recent_matches(
        match.away_team.id,
        limit=15
    )
    
    # Get odds
    odds_response = provider.get_odds(match.id)
    
    # Pass to StatsEngine
    home_stats = stats_engine.calculate_from_matches(
        home_response.data
    )
    
    # Pass to AnomalyEngine
    anomalies = anomaly_engine.analyze_market(
        match_id=match.id,
        bookmaker_odds=odds_response.data[0].under_odds,
        home_stats=home_stats,
        ...
    )
```

---

## ⚙️ Configuration

### **ProviderConfig**

```python
class ProviderConfig(BaseModel):
    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 2
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_dir: str = ".cache/providers"
```

---

## 📊 Cache Management

### **Cache Stats**

```python
stats = provider.get_cache_stats()

print(f"Total files: {stats['total_files']}")
print(f"Total size: {stats['total_size_mb']} MB")
```

---

### **Clear Cache**

```python
provider.clear_cache()
```

---

## 🚀 Prochaines Étapes

### **Court Terme**

1. ✅ Tester MockProvider
2. ⏳ Implémenter SofaScoreProvider complet
3. ⏳ Intégrer avec DailyScannerService
4. ⏳ Ajouter tests intégration

### **Moyen Terme**

1. ⏳ Créer FlashScoreProvider
2. ⏳ Ajouter provider odds dédié
3. ⏳ Optimiser cache
4. ⏳ Ajouter métriques providers

### **Long Terme**

1. ⏳ Provider manager (switch automatique)
2. ⏳ Fallback entre providers
3. ⏳ Agrégation multi-providers
4. ⏳ Dashboard monitoring providers

---

## ✅ Avantages Architecture

1. **Séparation claire** - Extraction ≠ Logique métier
2. **Extensible** - Nouveaux providers faciles
3. **Testable** - MockProvider pour tests
4. **Robuste** - Retry, cache, rate limiting
5. **Maintenable** - Code organisé, logs clairs
6. **Flexible** - Providers interchangeables

---

## 📚 Fichiers Créés

1. ✅ `app/providers/__init__.py`
2. ✅ `app/providers/models.py` (modèles normalisés)
3. ✅ `app/providers/base_provider.py` (interface)
4. ✅ `app/providers/mock_provider.py` (opérationnel)
5. ✅ `app/providers/sofascore_provider.py` (template)
6. ✅ `tests/test_providers.py` (tests)
7. ✅ `examples/providers_usage.py` (exemples)
8. ✅ `DATA_PROVIDERS.md` (ce fichier)

---

**Couche data providers propre et prête !** 🔌✨
