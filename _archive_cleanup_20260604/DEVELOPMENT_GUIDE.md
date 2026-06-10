# 🚀 Guide de Développement - Scanner Local

**Version** : 2.0.0  
**Type** : Local uniquement  
**Objectif** : Scanner d'anomalies bookmakers sur ligues obscures

---

## 🎯 PRINCIPES FONDAMENTAUX

### **Ce que le projet EST**

✅ **Scanner local** d'anomalies bookmakers  
✅ **Outil personnel** pour analyse statistique  
✅ **SQLite** local uniquement  
✅ **Simple** et maintenable  
✅ **Rapide** à tester  

### **Ce que le projet N'EST PAS**

❌ **PAS** un SaaS  
❌ **PAS** destiné au public  
❌ **PAS** de live betting  
❌ **PAS** de cloud (Redis, Celery)  
❌ **PAS** d'authentification  
❌ **PAS** de paiement  
❌ **PAS** de websockets  

---

## 📁 ARCHITECTURE ACTUELLE

### **Structure**

```
app/
├── core/
│   └── config.py              # Configuration locale (SQLite)
├── db/
│   ├── base.py                # SQLAlchemy Base
│   └── session.py             # Session factory
├── models/
│   ├── __init__.py            # Exports consolidés
│   └── database_models.py     # TOUS les modèles
├── services/
│   ├── stats_engine/          # Calcul statistiques
│   │   ├── advanced_stats_calculator.py
│   │   ├── league_stats_calculator.py
│   │   └── first_half_stats_calculator.py
│   ├── anomaly_engine/        # Détection anomalies
│   │   ├── advanced_anomaly_detector.py
│   │   └── first_half_anomaly_detector.py
│   ├── confidence_engine/     # Scoring confiance
│   │   └── confidence_scorer.py
│   ├── explanation/           # Génération explications
│   │   └── premium_explanation_generator.py
│   └── scanner/               # Scanner principal
│       └── anomaly_scanner.py
├── api/
│   ├── routes/                # Routes FastAPI
│   │   ├── anomalies.py
│   │   ├── matches.py
│   │   ├── analysis.py
│   │   └── stats.py
│   └── schemas.py             # Pydantic schemas
├── utils/
│   └── mock_data.py           # Données de test
└── main.py                    # Point d'entrée unique
```

---

## 🔧 SERVICES EXISTANTS

### **1. Stats Engine** ✅

**Localisation** : `app/services/stats_engine/`

**Fichiers** :
- `advanced_stats_calculator.py` - Calculs stats avancés
- `league_stats_calculator.py` - Stats ligue
- `first_half_stats_calculator.py` - Stats première mi-temps

**Usage** :
```python
from app.services.stats_engine import AdvancedStatsCalculator

calculator = AdvancedStatsCalculator(db)
stats = calculator.calculate_team_stats(team_id=1, last_n=15)
```

---

### **2. Anomaly Engine** ✅

**Localisation** : `app/services/anomaly_engine/`

**Fichiers** :
- `advanced_anomaly_detector.py` - Détection anomalies avancée
- `first_half_anomaly_detector.py` - Détection HT spécialisée

**Usage** :
```python
from app.services.anomaly_engine import AdvancedAnomalyDetector

detector = AdvancedAnomalyDetector(db)
anomaly = detector.detect_anomaly(match_id=1, market="over_25", odds=2.50)
```

---

### **3. Confidence Engine** ✅

**Localisation** : `app/services/confidence_engine/`

**Fichiers** :
- `confidence_scorer.py` - Calcul score confiance

**Usage** :
```python
from app.services.confidence_engine import ConfidenceScorer

scorer = ConfidenceScorer()
confidence = scorer.calculate_confidence(anomaly, home_stats, away_stats)
```

---

### **4. Explanation Engine** ✅

**Localisation** : `app/services/explanation/`

**Fichiers** :
- `premium_explanation_generator.py` - Génération explications premium

**Usage** :
```python
from app.services.explanation import PremiumExplanationGenerator, ExplanationContext

generator = PremiumExplanationGenerator()
context = ExplanationContext(...)
explanation = generator.generate_explanation(context)
```

---

### **5. Scanner** ✅

**Localisation** : `app/services/scanner/`

**Fichiers** :
- `anomaly_scanner.py` - Scanner automatique

**Usage** :
```python
from app.services.scanner import AnomalyScanner

scanner = AnomalyScanner(db)
results = scanner.scan_all_matches(days_ahead=1, max_results=10)
```

---

## 📝 CONVENTIONS DE CODE

### **1. Naming**

```python
# Fichiers
snake_case.py

# Classes
class PascalCase:
    pass

# Fonctions
def snake_case():
    pass

# Constantes
UPPER_SNAKE_CASE = 42

# Variables
snake_case = "value"
```

---

### **2. Documentation**

```python
"""
Module docstring
Brief description of module purpose
"""

def function_name(param: str) -> str:
    """
    Function docstring
    
    Args:
        param: Description
    
    Returns:
        Description
    """
    # Inline comment for complex logic
    result = process(param)
    return result
```

---

### **3. Typage**

```python
from typing import List, Dict, Optional

def calculate_score(
    values: List[float],
    weights: Dict[str, float],
    threshold: Optional[float] = None
) -> float:
    """Calculate weighted score"""
    pass
```

---

### **4. Imports**

```python
# Standard library
import os
from typing import List, Dict

# Third-party
from fastapi import FastAPI
from sqlalchemy.orm import Session

# Local
from app.core.config import settings
from app.models import Match, Team
from app.services.stats_engine import AdvancedStatsCalculator
```

---

## 🚫 RÈGLES STRICTES

### **Avant d'ajouter du code**

1. ✅ **Vérifier** si un service similaire existe déjà
2. ✅ **Lire** la documentation du service existant
3. ✅ **Réutiliser** le code existant
4. ✅ **Éviter** toute duplication

### **Interdictions**

❌ **NE JAMAIS** créer un nouveau engine sans vérifier  
❌ **NE JAMAIS** dupliquer la logique existante  
❌ **NE JAMAIS** ajouter Redis/Celery  
❌ **NE JAMAIS** ajouter d'authentification  
❌ **NE JAMAIS** ajouter de websockets  
❌ **NE JAMAIS** créer de système de paiement  
❌ **NE JAMAIS** utiliser d'API externes sans validation  

### **Obligations**

✅ **TOUJOURS** documenter le code  
✅ **TOUJOURS** typer les fonctions  
✅ **TOUJOURS** tester localement  
✅ **TOUJOURS** garder la simplicité  
✅ **TOUJOURS** utiliser SQLite  

---

## 🧪 TESTS

### **Lancer l'application**

```bash
# Méthode 1 : Directement
python -m app.main

# Méthode 2 : Uvicorn
uvicorn app.main:app --reload

# Méthode 3 : Via main.py
python app/main.py
```

### **Accès**

- **API** : http://localhost:8000
- **Docs** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

### **Endpoints disponibles**

```
GET  /                      # Info API
GET  /health                # Health check
GET  /api/matches           # Liste matchs
GET  /api/anomalies         # Liste anomalies
POST /api/analysis/{id}     # Analyser match
GET  /api/stats/{team_id}   # Stats équipe
```

---

## 📊 WORKFLOW DÉVELOPPEMENT

### **1. Nouvelle Fonctionnalité**

```
1. Vérifier si existe déjà
   ↓
2. Lire documentation services existants
   ↓
3. Réutiliser ou étendre service existant
   ↓
4. Si nouveau service nécessaire:
   - Créer dans services/
   - Documenter
   - Typer
   - Tester
   ↓
5. Mettre à jour ce guide
```

---

### **2. Modification Service Existant**

```
1. Lire le code existant
   ↓
2. Comprendre la logique
   ↓
3. Modifier sans casser l'existant
   ↓
4. Tester tous les endpoints
   ↓
5. Documenter les changements
```

---

### **3. Ajout Endpoint API**

```
1. Créer dans api/routes/
   ↓
2. Utiliser services existants
   ↓
3. Ajouter schema Pydantic
   ↓
4. Documenter endpoint
   ↓
5. Tester avec /docs
```

---

## 🗂️ DONNÉES

### **Base de données**

**Type** : SQLite local  
**Fichier** : `anomaly_scanner.db`  
**Localisation** : Racine du projet  

### **Modèles disponibles**

```python
from app.models import (
    Team,           # Équipes
    Competition,    # Compétitions
    Match,          # Matchs
    Odds,           # Cotes bookmaker
    MatchStats,     # Stats matchs
    Analysis        # Analyses anomalies
)
```

### **Import données**

```python
# Utiliser mock_data.py pour tests
from app.utils.mock_data import create_mock_data

db = SessionLocal()
create_mock_data(db)
```

---

## 🎯 PROCHAINES ÉTAPES

### **Développement à venir**

1. ⏳ **Data Loader** (`utils/data_loader.py`)
   - Import CSV/JSON local
   - Remplacer ingestion API

2. ⏳ **Dashboard Local**
   - Interface web simple
   - Visualisation anomalies
   - Pas de framework complexe

3. ⏳ **CLI Simple**
   - Commandes pour scanner
   - Pas de framework CLI complexe

4. ⏳ **Export Résultats**
   - CSV/JSON
   - Rapports PDF simples

---

## 📚 RESSOURCES

### **Documentation**

- `README.md` - Vue d'ensemble projet
- `ARCHITECTURE.md` - Architecture détaillée
- `AUDIT_ARCHITECTURE.md` - Audit complet
- `REFACTORING_APPLIED.md` - Changements appliqués
- `DEVELOPMENT_GUIDE.md` - Ce guide

### **Documentation Services**

- `docs/STATISTICAL_INDICATORS.md` - Indicateurs stats
- `docs/ANOMALY_DETECTION_SYSTEM.md` - Système anomalies
- `docs/FIRST_HALF_SYSTEM.md` - Système HT
- `docs/SCANNER_SYSTEM.md` - Système scanner
- `docs/EXPLANATION_TEMPLATES.md` - Templates explications

### **Exemples**

- `examples/usage_examples.py` - Exemples stats
- `examples/anomaly_detection_example.py` - Exemples anomalies
- `examples/first_half_examples.py` - Exemples HT

---

## ✅ CHECKLIST AVANT COMMIT

- [ ] Code documenté (docstrings)
- [ ] Fonctions typées
- [ ] Pas de duplication
- [ ] Services existants réutilisés
- [ ] Testé localement
- [ ] Endpoints fonctionnels
- [ ] SQLite uniquement
- [ ] Pas de dépendances cloud
- [ ] Guide mis à jour si nécessaire

---

**Le projet est maintenant prêt pour un développement cohérent et maintenable.** 🚀
