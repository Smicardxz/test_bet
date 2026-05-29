# 🔌 SofaScore Provider - Implémentation Complète

**Version** : 1.0.0  
**Date** : 27 Mai 2026  
**Statut** : ✅ OPÉRATIONNEL

---

## 🎯 Objectif Atteint

**Provider SofaScore fonctionnel** qui récupère automatiquement les données depuis l'API publique SofaScore.

---

## ✅ Fonctionnalités Implémentées

### **Extraction de Données**

1. ✅ **Matchs du jour** - Tous les matchs schedulés
2. ✅ **Détails match** - Info complète par match
3. ✅ **Historique équipe** - Derniers matchs d'une équipe
4. ✅ **Head-to-Head** - Face-à-face entre 2 équipes
5. ✅ **Matchs compétition** - Tous les matchs d'une compétition
6. ✅ **Odds** - Cotes (best-effort)

### **Normalisation**

1. ✅ **Mapping propre** - Données SofaScore → Modèles internes
2. ✅ **Gestion données manquantes** - Valeurs par défaut
3. ✅ **Filtrage ligues obscures** - Détection automatique
4. ✅ **Scores FT/HT** - Extraction complète

### **Robustesse**

1. ✅ **Cache local** - TTL 5 minutes
2. ✅ **Rate limiting** - 30 req/min
3. ✅ **Retry avec backoff** - 3 tentatives
4. ✅ **Gestion erreurs HTTP** - Logs clairs
5. ✅ **Logs lisibles** - DEBUG/INFO/WARNING/ERROR

---

## 📊 Données Récupérées

### **Pour Chaque Match**

```python
{
    "id": "12345",
    "home_team": {
        "id": "123",
        "name": "London City Lionesses",
        "short_name": "London City",
        "country": "England"
    },
    "away_team": {...},
    "competition": {
        "id": "456",
        "name": "England Women's Championship",
        "country": "England",
        "tier": 2,
        "is_obscure": True
    },
    "match_date": "2026-05-27T15:00:00",
    "status": "scheduled",
    "score_fulltime": {"home": 2, "away": 1},  # Si terminé
    "score_halftime": {"home": 1, "away": 0},  # Si disponible
    "venue": "Stadium Name",
    "provider": "sofascore",
    "provider_url": "https://www.sofascore.com/match/12345"
}
```

---

## 🔧 Utilisation

### **Exemple Simple**

```python
from app.providers.sofascore_provider import SofaScoreProvider

# Create provider
provider = SofaScoreProvider()

# Get today's matches
response = provider.get_today_matches()

if response.success:
    for match in response.data:
        print(f"{match.home_team.name} vs {match.away_team.name}")
        print(f"  Competition: {match.competition.name}")
        print(f"  Obscure: {match.competition.is_obscure}")
```

---

### **Avec Configuration**

```python
from app.providers import ProviderConfig
from app.providers.sofascore_provider import SofaScoreProvider

config = ProviderConfig(
    name="sofascore",
    rate_limit_per_minute=20,  # Plus conservateur
    cache_ttl_seconds=600,      # Cache 10 minutes
    timeout_seconds=20
)

provider = SofaScoreProvider(config)
```

---

### **Historique Équipe**

```python
# Get team recent matches
response = provider.get_team_recent_matches(
    team_id="12345",
    limit=15
)

if response.success:
    for match in response.data:
        print(f"{match.home_team.name} vs {match.away_team.name}")
        if match.score_fulltime:
            print(f"  Score: {match.score_fulltime.home}-{match.score_fulltime.away}")
```

---

### **Head-to-Head**

```python
# Get H2H
response = provider.get_head_to_head(
    team_a_id="123",
    team_b_id="456",
    limit=10
)

if response.success:
    h2h = response.data
    print(f"Total matches: {h2h.total_matches}")
    print(f"Team A wins: {h2h.team_a_wins}")
    print(f"Team B wins: {h2h.team_b_wins}")
    print(f"Draws: {h2h.draws}")
```

---

## 🚀 Scripts Disponibles

### **1. Fetch Today's Matches**

```bash
python scripts/fetch_today_matches.py
```

**Fonctionnalités** :
- Choix provider (SofaScore ou Mock)
- Affichage détaillé des matchs
- Sauvegarde JSON locale
- Statistiques par compétition

**Output** :
```
Select provider:
  1. SofaScore (real data)
  2. Mock (test data)

Choice [1/2]: 1

📥 Fetching matches...
✅ Successfully fetched 15 matches
🌐 Fresh from API

Match #1
================================================================================
🏟️  London City Lionesses vs Bristol City Women
🏆 Competition: England Women's Championship
🌍 Country: England
📅 Date: 2026-05-27 15:00
📊 Status: scheduled
✅ Obscure league: YES

[...]

✅ Matches saved to: data/fetched/today_matches.json

SUMMARY
================================================================================
Total matches: 15

By competition:
  • England Women's Championship: 5 matches
  • England U21 Premier League: 4 matches
  • England National League North: 3 matches
  [...]

Obscure leagues: 15/15 (100.0%)
```

---

### **2. Test Provider**

```bash
python scripts/test_sofascore_provider.py
```

**Tests** :
1. ✅ Today's Matches
2. ✅ Match Details
3. ✅ Team Recent
4. ✅ Cache
5. ✅ Error Handling

**Output** :
```
🧪 SOFASCORE PROVIDER TESTS
================================================================================

TEST 1: Fetch Today's Matches
================================================================================
📥 Fetching today's matches...
✅ Success! Found 15 matches

[...]

TEST SUMMARY
================================================================================
  ✅ PASS - Today's Matches
  ✅ PASS - Match Details
  ✅ PASS - Team Recent
  ✅ PASS - Cache
  ✅ PASS - Error Handling

Total: 5/5 tests passed (100%)

🎉 All tests passed!
```

---

## 🎯 Filtrage Ligues Obscures

### **Critères de Détection**

```python
obscure_keywords = [
    "women", "u21", "u19", "u18", "u23", "reserve",
    "national league", "regional", "championship",
    "division 3", "division 4", "division 5",
    "national 3", "national 2"
]
```

**Logique** :
1. Tier ≥ 3 → Obscure
2. Nom contient keyword → Obscure
3. Catégorie contient keyword → Obscure

**Exemples Obscures** :
- ✅ England Women's Championship
- ✅ England U21 Premier League
- ✅ England National League North
- ✅ France National 3
- ✅ Germany Regionalliga

**Exemples Non-Obscures** :
- ❌ Premier League
- ❌ La Liga
- ❌ Serie A
- ❌ Bundesliga

---

## 📦 Cache Local

### **Fonctionnement**

- **Location** : `.cache/providers/sofascore/`
- **TTL** : 5 minutes (configurable)
- **Format** : JSON
- **Key** : Hash MD5 (méthode + paramètres)

### **Gestion**

```python
# Cache stats
stats = provider.get_cache_stats()
print(f"Files: {stats['total_files']}")
print(f"Size: {stats['total_size_mb']} MB")

# Clear cache
provider.clear_cache()
```

---

## ⚠️ Gestion Erreurs

### **Types d'Erreurs**

1. **HTTP Errors** - 404, 500, timeout
2. **Rate Limiting** - Trop de requêtes
3. **Parsing Errors** - Données malformées
4. **Network Errors** - Pas de connexion

### **Comportement**

```python
response = provider.get_today_matches()

if not response.success:
    print(f"Error: {response.error}")
    # Log automatique
    # Retry automatique (3x)
    # Cache fallback si disponible
```

---

## 🔗 Intégration avec Engines

### **Workflow Complet**

```python
from app.providers.sofascore_provider import SofaScoreProvider
from app.services.stats import StatsEngine
from app.services.anomaly import AnomalyEngine

# 1. Fetch matches
provider = SofaScoreProvider()
response = provider.get_today_matches()
matches = response.data

# 2. For each match
for match in matches:
    # Get team stats
    home_recent = provider.get_team_recent_matches(
        match.home_team.id,
        limit=15
    )
    
    away_recent = provider.get_team_recent_matches(
        match.away_team.id,
        limit=15
    )
    
    # Calculate stats
    stats_engine = StatsEngine()
    home_stats = stats_engine.calculate_from_matches(home_recent.data)
    away_stats = stats_engine.calculate_from_matches(away_recent.data)
    
    # Get odds (if available)
    odds_response = provider.get_odds(match.id)
    
    # Detect anomalies
    anomaly_engine = AnomalyEngine()
    if odds_response.success:
        for odds in odds_response.data:
            result = anomaly_engine.analyze_market(
                match_id=match.id,
                market_type=odds.market_type,
                bookmaker_odds=odds.under_odds,
                home_stats=home_stats,
                away_stats=away_stats
            )
            
            if result.anomaly_score >= 60:
                print(f"Anomaly detected: {result.anomaly_score}")
```

---

## 📊 Données Sauvegardées

### **Format JSON**

```json
{
  "fetched_at": "2026-05-27T14:30:00",
  "total_matches": 15,
  "matches": [
    {
      "id": "12345",
      "home_team": {
        "id": "123",
        "name": "London City Lionesses"
      },
      "away_team": {
        "id": "456",
        "name": "Bristol City Women"
      },
      "competition": {
        "id": "789",
        "name": "England Women's Championship",
        "country": "England",
        "is_obscure": true
      },
      "match_date": "2026-05-27T15:00:00",
      "status": "scheduled",
      "score_fulltime": null,
      "score_halftime": null,
      "venue": "Stadium Name",
      "provider": "sofascore",
      "provider_url": "https://www.sofascore.com/match/12345"
    }
  ]
}
```

---

## ⚙️ Configuration Recommandée

### **Production**

```python
config = ProviderConfig(
    name="sofascore",
    rate_limit_per_minute=20,  # Conservative
    timeout_seconds=20,
    retry_attempts=3,
    cache_enabled=True,
    cache_ttl_seconds=600  # 10 minutes
)
```

### **Développement**

```python
config = ProviderConfig(
    name="sofascore_dev",
    rate_limit_per_minute=60,
    timeout_seconds=10,
    retry_attempts=2,
    cache_enabled=True,
    cache_ttl_seconds=60  # 1 minute
)
```

---

## 🚨 Limitations

1. **Odds** - SofaScore ne fournit pas toujours les odds
2. **Rate Limiting** - API publique limitée
3. **Données Manquantes** - Certains matchs n'ont pas HT scores
4. **Délai** - Données pas toujours en temps réel

**Solutions** :
- Utiliser provider odds dédié (The Odds API)
- Cache agressif
- Fallback sur MockProvider pour tests

---

## ✅ Checklist Implémentation

- ✅ Extraction matchs du jour
- ✅ Extraction détails match
- ✅ Extraction historique équipe
- ✅ Extraction H2H
- ✅ Normalisation données
- ✅ Mapping vers modèles internes
- ✅ Gestion erreurs HTTP
- ✅ Gestion données manquantes
- ✅ Cache local
- ✅ Rate limiting
- ✅ Retry avec backoff
- ✅ Logs lisibles
- ✅ Filtrage ligues obscures
- ✅ Scripts fetch/test
- ✅ Documentation complète

---

**SofaScore Provider opérationnel et prêt pour intégration !** 🔌✨
