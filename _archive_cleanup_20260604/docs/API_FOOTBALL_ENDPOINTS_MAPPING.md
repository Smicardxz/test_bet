# API-Football Endpoints Mapping

## 📋 Vue d'ensemble

**Base URL:** `https://v3.football.api-sports.io`
**Authentication:** Header `x-apisports-key: YOUR_API_KEY`
**Free Tier:** 100 requests/day

---

## 1. Fixtures du Jour

### Endpoint
```
GET /fixtures?date={YYYY-MM-DD}
```

### Paramètres
- `date`: Format YYYY-MM-DD (ex: 2024-01-15)
- `timezone`: Optionnel (ex: Europe/Paris)

### Réponse
```json
{
  "response": [
    {
      "fixture": {
        "id": 12345,
        "date": "2024-01-15T15:00:00+00:00",
        "timestamp": 1705330800,
        "status": {
          "short": "NS",
          "long": "Not Started",
          "elapsed": null
        }
      },
      "league": {
        "id": 39,
        "name": "Premier League",
        "country": "England",
        "season": 2023
      },
      "teams": {
        "home": {
          "id": 33,
          "name": "Manchester United"
        },
        "away": {
          "id": 34,
          "name": "Newcastle"
        }
      },
      "goals": {
        "home": null,
        "away": null
      },
      "score": {
        "halftime": {
          "home": null,
          "away": null
        },
        "fulltime": {
          "home": null,
          "away": null
        }
      }
    }
  ]
}
```

### Champs Utilisés
- `fixture.id` → fixture_id
- `fixture.date` → date_utc
- `fixture.status.short` → status (NS, 1H, HT, 2H, FT, etc.)
- `fixture.status.elapsed` → minutes écoulées
- `league.id`, `league.name`, `league.country`
- `teams.home.id`, `teams.home.name`
- `teams.away.id`, `teams.away.name`
- `goals.home`, `goals.away` → score actuel
- `score.halftime` → score HT
- `score.fulltime` → score FT

### Coût
**1 request** par appel

---

## 2. Historique Équipe

### Endpoint
```
GET /fixtures?team={TEAM_ID}&last={LIMIT}
```

### Paramètres
- `team`: ID de l'équipe
- `last`: Nombre de matchs (ex: 10)
- `season`: Optionnel (ex: 2023)
- `status`: Optionnel (FT pour matchs terminés)

### Exemple
```
GET /fixtures?team=33&last=10&status=FT
```

### Réponse
Même structure que fixtures, mais filtrée par équipe.

### Champs Utilisés
- Tous les champs de fixture
- `teams.home.id` vs `team` → déterminer si home/away
- `score.halftime` → HT goals
- `score.fulltime` → FT goals

### Coût
**1 request** par équipe
**2 requests** pour home + away

---

## 3. Head to Head (H2H)

### Endpoint
```
GET /fixtures/headtohead?h2h={TEAM1_ID}-{TEAM2_ID}
```

### Paramètres
- `h2h`: Format `{home_id}-{away_id}`
- `last`: Nombre de matchs (ex: 10)
- `status`: FT recommandé

### Exemple
```
GET /fixtures/headtohead?h2h=33-34&last=10
```

### Réponse
Liste de fixtures entre les 2 équipes.

### Champs Utilisés
- Même structure que fixtures
- Historique des confrontations directes

### Coût
**1 request** par paire d'équipes

---

## 4. Odds (Optionnel)

### Endpoint
```
GET /odds?fixture={FIXTURE_ID}
```

### Paramètres
- `fixture`: ID du match
- `bookmaker`: Optionnel (ex: 8 pour Bet365)
- `bet`: Optionnel (ex: 1 pour Match Winner)

### Exemple
```
GET /odds?fixture=12345&bookmaker=8
```

### Réponse
```json
{
  "response": [
    {
      "fixture": {
        "id": 12345
      },
      "bookmakers": [
        {
          "id": 8,
          "name": "Bet365",
          "bets": [
            {
              "id": 1,
              "name": "Match Winner",
              "values": [
                {
                  "value": "Home",
                  "odd": "2.10"
                },
                {
                  "value": "Draw",
                  "odd": "3.40"
                },
                {
                  "value": "Away",
                  "odd": "3.25"
                }
              ]
            },
            {
              "id": 8,
              "name": "Goals Over/Under",
              "values": [
                {
                  "value": "Over 2.5",
                  "odd": "1.85"
                },
                {
                  "value": "Under 2.5",
                  "odd": "1.95"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Champs Utilisés
- `bookmakers[].bets[]` → marchés disponibles
- `values[].value` → type de pari
- `values[].odd` → cote

### Coût
**1 request** par fixture
**Attention:** Odds souvent absentes pour ligues mineures

---

## 5. Fixture Details

### Endpoint
```
GET /fixtures?id={FIXTURE_ID}
```

### Paramètres
- `id`: ID du match

### Réponse
Détails complets d'un match spécifique.

### Coût
**1 request**

---

## 6. Leagues (Si nécessaire)

### Endpoint
```
GET /leagues?id={LEAGUE_ID}
GET /leagues?country={COUNTRY}
```

### Usage
Récupérer infos sur une ligue spécifique.

### Coût
**1 request**

---

## 📊 Résumé des Coûts

### Analyse d'un Match Complet

| Action | Endpoint | Coût |
|--------|----------|------|
| Fixtures du jour | `/fixtures?date=today` | 1 |
| History Home | `/fixtures?team={home_id}&last=10` | 1 |
| History Away | `/fixtures?team={away_id}&last=10` | 1 |
| H2H | `/fixtures/headtohead?h2h={ids}` | 1 |
| Odds (optionnel) | `/odds?fixture={id}` | 1 |
| **TOTAL** | | **4-5 requests** |

### Free Tier (100 requests/day)

**Capacité:**
- ~20-25 matchs analysés par jour
- Ou ~100 fixtures du jour seulement

**Recommandation:**
- Cache agressif (24h pour history)
- Analyse à la demande uniquement
- Pas d'auto-refresh toutes les minutes

---

## 🔒 Limitations Free Tier

**Quotas:**
- 100 requests/day
- 10 requests/minute
- Pas de webhooks
- Pas de live updates temps réel

**Données disponibles:**
- ✅ Fixtures
- ✅ Teams
- ✅ Leagues
- ✅ Standings
- ✅ H2H
- ⚠️ Odds (limitées)
- ❌ Live commentary
- ❌ Player stats détaillées

---

## ⚡ Optimisations

### Cache Strategy

**Fixtures du jour:**
- TTL: 30-60 minutes
- Refresh si status change

**Team History:**
- TTL: 24 heures
- Invalider si nouveau match joué

**H2H:**
- TTL: 24 heures
- Rarement modifié

**Odds:**
- TTL: 15 minutes
- Très volatiles

### Batch Requests

**Éviter:**
```
GET /fixtures?team=1
GET /fixtures?team=2
GET /fixtures?team=3
```

**Préférer:**
```
GET /fixtures?date=today
→ Récupère tous les matchs du jour
→ Extraire teams IDs
→ Fetch history seulement pour matchs ciblés
```

---

## ✅ Checklist Implémentation

- [ ] Fixtures du jour
- [ ] Team history (home)
- [ ] Team history (away)
- [ ] H2H
- [ ] Odds (optionnel)
- [ ] Cache JSON
- [ ] Rate limiting
- [ ] Error handling
- [ ] Retry logic
- [ ] Timeout handling

---

## 🚨 Erreurs Courantes

### 429 Too Many Requests
```json
{
  "message": "You have exceeded the rate limit per minute for your subscription"
}
```
**Solution:** Implémenter rate limiting

### 404 Not Found
```json
{
  "message": "The requested resource was not found"
}
```
**Solution:** Vérifier IDs, retourner DATA_MISSING

### 401 Unauthorized
```json
{
  "message": "Invalid API key"
}
```
**Solution:** Vérifier API_FOOTBALL_KEY dans .env

---

## 📝 Notes

**Status Codes:**
- `NS` - Not Started
- `1H` - First Half
- `HT` - Halftime
- `2H` - Second Half
- `ET` - Extra Time
- `P` - Penalty
- `FT` - Full Time
- `AET` - After Extra Time
- `PEN` - Penalties
- `BT` - Break Time
- `SUSP` - Suspended
- `INT` - Interrupted
- `PST` - Postponed
- `CANC` - Cancelled
- `ABD` - Abandoned
- `AWD` - Technical Loss
- `WO` - WalkOver
- `LIVE` - In Progress

**Seuls FT, AET, PEN sont utilisables pour historique.**
