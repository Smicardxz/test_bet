# 🌐 API Locale - Documentation Complète

**Version** : 2.0.0  
**Type** : Local uniquement  
**Base URL** : `http://localhost:8000`  
**Documentation** : `http://localhost:8000/docs`

---

## 🎯 Vue d'Ensemble

API locale REST pour détecter les anomalies bookmakers sur des matchs de football de ligues obscures.

**Caractéristiques** :
- ✅ Local uniquement (pas de SaaS)
- ✅ Pas d'authentification
- ✅ Pas de live betting
- ✅ Documentation OpenAPI automatique
- ✅ Réponses JSON complètes

---

## 📋 ENDPOINTS

### **Scanner**

#### `GET /api/scanner/top-anomalies`

Récupère les meilleures anomalies détectées aujourd'hui.

**Query Parameters** :
- `max_results` (int, optional): Maximum résultats (1-50, default: 10)
- `min_anomaly_score` (float, optional): Score minimum (0-100, default: 50.0)

**Response** :
```json
{
  "total_anomalies": 8,
  "anomalies": [
    {
      "match_id": 1,
      "home_team": "London City Lionesses Women",
      "away_team": "Bristol City Women",
      "competition": "England Women's Championship",
      "match_date": "2026-05-27T15:00:00",
      "market_type": "ht_under_05",
      "market_priority": "CRITICAL",
      "line": 0.5,
      "bookmaker_odds": 2.50,
      "bookmaker_probability": 0.40,
      "model_probability": 0.72,
      "anomaly_score": 78.5,
      "discrepancy_score": 64.0,
      "variance_safety_score": 82.0,
      "stability_score": 85.0,
      "confidence_category": "HIGH",
      "confidence_score": 0.82,
      "positive_signals": [
        {
          "type": "EXTREME_DISCREPANCY",
          "strength": "STRONG",
          "description": "Écart extrême de 32.0%",
          "value": 0.32
        }
      ],
      "negative_signals": [],
      "risk_factors": [],
      "explanation_summary": "Écart détecté de 32.0%...",
      "explanation_full": "Analyse complète...",
      "data_quality_score": 1.0,
      "sample_size": 15,
      "final_score": 85.5,
      "rank": 1
    }
  ],
  "summary": {
    "total_anomalies": 8,
    "total_matches": 5,
    "by_priority": {
      "CRITICAL": 3,
      "HIGH": 4,
      "MEDIUM": 1
    },
    "by_confidence": {
      "HIGH": 4,
      "MEDIUM": 3,
      "LOW": 1
    },
    "avg_anomaly_score": 68.5,
    "avg_confidence_score": 0.72
  }
}
```

---

### **Matches**

#### `GET /api/matches/today`

Récupère tous les matchs du jour.

**Response** :
```json
[
  {
    "id": 1,
    "home_team": "London City Lionesses Women",
    "away_team": "Bristol City Women",
    "competition": "England Women's Championship",
    "match_date": "2026-05-27T15:00:00",
    "status": "scheduled"
  }
]
```

---

#### `GET /api/matches/{match_id}`

Récupère un match spécifique.

**Path Parameters** :
- `match_id` (int): ID du match

**Response** :
```json
{
  "id": 1,
  "home_team": "London City Lionesses Women",
  "away_team": "Bristol City Women",
  "competition": "England Women's Championship",
  "match_date": "2026-05-27T15:00:00",
  "status": "scheduled"
}
```

---

### **Analysis**

#### `GET /api/analysis/{match_id}`

Analyse complète d'un match spécifique.

**Path Parameters** :
- `match_id` (int): ID du match

**Response** :
```json
{
  "match_id": 1,
  "home_team": "London City Lionesses Women",
  "away_team": "Bristol City Women",
  "competition": "England Women's Championship",
  "match_date": "2026-05-27T15:00:00",
  "anomalies": [
    {
      "market_type": "ht_under_05",
      "line": 0.5,
      "bookmaker_odds": 2.50,
      "anomaly_score": 78.5,
      "confidence_category": "HIGH",
      "explanation_summary": "Écart détecté de 32.0%..."
    },
    {
      "market_type": "ft_under_105",
      "line": 10.5,
      "bookmaker_odds": 1.50,
      "anomaly_score": 82.3,
      "confidence_category": "HIGH",
      "explanation_summary": "Ligne extrême..."
    }
  ]
}
```

---

### **Markets**

#### `GET /api/markets/top-ht-under`

Récupère les meilleures anomalies HT Under.

**Query Parameters** :
- `max_results` (int, optional): Maximum résultats (1-50, default: 10)

**Response** :
```json
{
  "market_category": "HT Under",
  "total_anomalies": 3,
  "anomalies": [
    {
      "match_id": 1,
      "home_team": "London City Lionesses Women",
      "away_team": "Bristol City Women",
      "market_type": "ht_under_05",
      "anomaly_score": 78.5,
      "confidence_category": "HIGH",
      "explanation_summary": "..."
    }
  ]
}
```

---

#### `GET /api/markets/top-extreme-under`

Récupère les meilleures anomalies Extreme Under (6.5, 8.5, 10.5).

**Query Parameters** :
- `max_results` (int, optional): Maximum résultats (1-50, default: 10)

**Response** :
```json
{
  "market_category": "Extreme Under",
  "total_anomalies": 2,
  "anomalies": [...]
}
```

---

#### `GET /api/markets/top-btts-anomalies`

Récupère les meilleures anomalies BTTS.

**Query Parameters** :
- `max_results` (int, optional): Maximum résultats (1-50, default: 10)

**Response** :
```json
{
  "market_category": "BTTS",
  "total_anomalies": 1,
  "anomalies": [...]
}
```

---

## 📊 STRUCTURE RÉPONSE ANOMALIE

### **Champs Principaux**

| Champ | Type | Description |
|-------|------|-------------|
| `match_id` | int | ID du match |
| `home_team` | string | Équipe domicile |
| `away_team` | string | Équipe extérieur |
| `competition` | string | Compétition |
| `match_date` | string | Date/heure match (ISO 8601) |
| `market_type` | string | Type de marché |
| `market_priority` | string | Priorité (CRITICAL/HIGH/MEDIUM/LOW) |
| `line` | float | Ligne bookmaker |
| `bookmaker_odds` | float | Cote bookmaker |
| `bookmaker_probability` | float | Probabilité implicite (0-1) |
| `model_probability` | float | Probabilité modèle (0-1) |
| `anomaly_score` | float | Score anomalie (0-100) |
| `discrepancy_score` | float | Score écart (0-100) |
| `variance_safety_score` | float | Score sécurité variance (0-100) |
| `stability_score` | float | Score stabilité (0-100) |
| `confidence_category` | string | Catégorie confiance (LOW/MEDIUM/HIGH) |
| `confidence_score` | float | Score confiance (0-1) |
| `positive_signals` | array | Signaux positifs |
| `negative_signals` | array | Signaux négatifs |
| `risk_factors` | array | Facteurs de risque |
| `explanation_summary` | string | Résumé explication |
| `explanation_full` | string | Explication complète |
| `data_quality_score` | float | Qualité données (0-1) |
| `sample_size` | int | Taille échantillon |
| `final_score` | float | Score final ranking |
| `rank` | int | Rang |

---

## 🚀 UTILISATION

### **Démarrer l'API**

```bash
# Depuis le dossier racine
python -m app.main

# Ou avec uvicorn
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Output** :
```
🚀 Local Anomaly Scanner started
📚 Documentation: http://localhost:8000/docs
🏠 Local mode - SQLite database
```

---

### **Accéder à la Documentation**

**Swagger UI** : `http://localhost:8000/docs`  
**ReDoc** : `http://localhost:8000/redoc`

---

### **Exemples cURL**

#### Top Anomalies

```bash
curl http://localhost:8000/api/scanner/top-anomalies?max_results=5
```

#### Matchs du Jour

```bash
curl http://localhost:8000/api/matches/today
```

#### Analyse Match

```bash
curl http://localhost:8000/api/analysis/1
```

#### HT Under Anomalies

```bash
curl http://localhost:8000/api/markets/top-ht-under?max_results=3
```

---

### **Exemples Python**

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api"

# Get top anomalies
response = requests.get(f"{BASE_URL}/scanner/top-anomalies", params={
    "max_results": 10,
    "min_anomaly_score": 60.0
})
anomalies = response.json()

# Get today's matches
response = requests.get(f"{BASE_URL}/matches/today")
matches = response.json()

# Analyze specific match
response = requests.get(f"{BASE_URL}/analysis/1")
analysis = response.json()

# Get HT Under anomalies
response = requests.get(f"{BASE_URL}/markets/top-ht-under")
ht_anomalies = response.json()
```

---

### **Exemples JavaScript**

```javascript
const BASE_URL = "http://localhost:8000/api";

// Get top anomalies
fetch(`${BASE_URL}/scanner/top-anomalies?max_results=10`)
  .then(res => res.json())
  .then(data => console.log(data));

// Get today's matches
fetch(`${BASE_URL}/matches/today`)
  .then(res => res.json())
  .then(matches => console.log(matches));

// Analyze match
fetch(`${BASE_URL}/analysis/1`)
  .then(res => res.json())
  .then(analysis => console.log(analysis));
```

---

## 🎨 DASHBOARD LOCAL

### **Endpoints pour Dashboard**

```javascript
// Dashboard principal
GET /api/scanner/top-anomalies?max_results=20

// Filtres par marché
GET /api/markets/top-ht-under
GET /api/markets/top-extreme-under
GET /api/markets/top-btts-anomalies

// Détail match
GET /api/analysis/{match_id}

// Liste matchs
GET /api/matches/today
```

---

### **Exemple Intégration Dashboard**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Anomaly Scanner Dashboard</title>
</head>
<body>
    <h1>Top Anomalies</h1>
    <div id="anomalies"></div>

    <script>
        fetch('http://localhost:8000/api/scanner/top-anomalies')
            .then(res => res.json())
            .then(data => {
                const container = document.getElementById('anomalies');
                data.anomalies.forEach(anomaly => {
                    const div = document.createElement('div');
                    div.innerHTML = `
                        <h3>${anomaly.home_team} vs ${anomaly.away_team}</h3>
                        <p>Market: ${anomaly.market_type}</p>
                        <p>Anomaly Score: ${anomaly.anomaly_score.toFixed(1)}</p>
                        <p>Confidence: ${anomaly.confidence_category}</p>
                        <p>${anomaly.explanation_summary}</p>
                    `;
                    container.appendChild(div);
                });
            });
    </script>
</body>
</html>
```

---

## ✅ CARACTÉRISTIQUES

✅ **Local uniquement** - Pas de cloud, pas de SaaS  
✅ **Pas d'auth** - API ouverte localement  
✅ **Documentation OpenAPI** - Swagger UI automatique  
✅ **Réponses complètes** - Toutes les données nécessaires  
✅ **Explications incluses** - Textes professionnels  
✅ **CORS configuré** - Pour dashboard local  

---

## 📝 NOTES

- **Port** : 8000 (configurable)
- **Host** : 127.0.0.1 (localhost uniquement)
- **Database** : SQLite local
- **CORS** : localhost:3000 et localhost:8000
- **Reload** : Auto-reload en développement

---

**API locale complète et prête pour dashboard !** 🌐✨
