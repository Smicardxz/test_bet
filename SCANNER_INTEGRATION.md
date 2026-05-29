# 🔗 Scanner Integration avec DataProvider - COMPLET

**Version** : 2.0.0  
**Date** : 27 Mai 2026  
**Statut** : ✅ OPÉRATIONNEL

---

## 🎯 OBJECTIF ATTEINT

**DailyScannerServiceV2** intégré avec DataProviders pour utiliser des données réelles ou mockées.

---

## 📁 FICHIERS CRÉÉS

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `app/services/scanner/daily_scanner_v2.py` | 550 | Scanner V2 avec providers |
| `app/services/stats/provider_adapter.py` | 250 | Adapter StatsEngine |
| `tests/test_scanner_with_provider.py` | 250 | Tests unitaires |
| `scripts/test_scanner_integration.py` | 300 | Script test intégration |
| `SCANNER_INTEGRATION.md` | 400 | Ce fichier |
| **TOTAL** | **1750** | **5 fichiers** |

---

## ✅ FONCTIONNALITÉS

### **Intégration DataProvider**

1. ✅ **MockProvider** - Tests sans API
2. ✅ **SofaScoreProvider** - Données réelles
3. ✅ **Configuration** - Provider sélectionnable
4. ✅ **Fallback** - Gestion données manquantes

### **Pipeline Complet**

1. ✅ Récupération matchs du jour
2. ✅ Récupération historiques équipes
3. ✅ Récupération H2H (optionnel)
4. ✅ Calcul StatsEngine
5. ✅ Détection AnomalyEngine
6. ✅ Ranking et filtrage

### **Gestion Données**

1. ✅ **Data quality score** - Indicateur qualité
2. ✅ **Sample size tracking** - Taille échantillon
3. ✅ **Missing data handling** - Gestion manquant
4. ✅ **Default odds** - Odds par défaut si manquantes

---

## 🚀 UTILISATION

### **Avec MockProvider**

```python
from app.providers import MockDataProvider
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2
from app.services.stats.provider_adapter import add_provider_support_to_stats_engine

# Load adapter
add_provider_support_to_stats_engine()

# Create provider and scanner
provider = MockDataProvider()
scanner = DailyScannerServiceV2(provider)

# Run scan
results = scanner.scan_today(max_results=10)

# Display results
for result in results:
    print(f"{result.home_team} vs {result.away_team}")
    print(f"  Market: {result.market_type}")
    print(f"  Score: {result.anomaly_result.anomaly_score:.1f}")
    print(f"  Quality: {result.data_quality_score:.2f}")
```

---

### **Avec SofaScoreProvider**

```python
from app.providers.sofascore_provider import SofaScoreProvider
from app.services.scanner.daily_scanner_v2 import DailyScannerServiceV2

# Create provider
provider = SofaScoreProvider()

# Create scanner
scanner = DailyScannerServiceV2(provider)

# Run scan
results = scanner.scan_today()
```

---

### **Avec Filtres**

```python
# Filter by competition
results = scanner.scan_today(
    competition_ids=["eng_women_champ", "eng_u21"],
    max_results=20
)

# Custom thresholds
scanner.min_anomaly_score = 70.0
scanner.min_sample_size = 12
scanner.min_data_quality = 0.7

results = scanner.scan_today()
```

---

## 📊 SCAN RESULT

### **Structure**

```python
ScanResult(
    # Match Info
    match_id="12345",
    home_team="London City Lionesses",
    away_team="Bristol City Women",
    league="England Women's Championship",
    match_date="2026-05-27T15:00:00",
    
    # Market Info
    market_type="ht_under_05",
    market_priority=MarketPriority.CRITICAL,
    line=0.5,
    bookmaker_odds=2.50,
    
    # Anomaly Analysis
    anomaly_result=AnomalyResult(...),
    
    # Data Quality
    data_quality_score=0.85,
    home_sample_size=15,
    away_sample_size=14,
    h2h_available=True,
    
    # Ranking
    final_score=125.5,
    rank=1,
    
    # Metadata
    scan_timestamp="2026-05-27T14:30:00",
    provider="sofascore"
)
```

---

## 🎯 DATA QUALITY SCORE

### **Calcul**

```python
# Sample size score (40%)
sample_score = min(1.0, min_sample_size / 15.0)

# Data quality scores (60%)
avg_quality = (home_quality + away_quality) / 2

# Combined
data_quality_score = sample_score * 0.4 + avg_quality * 0.6
```

### **Seuils**

- **≥ 0.8** - Excellente qualité
- **0.6-0.8** - Bonne qualité
- **< 0.6** - Qualité insuffisante (filtré)

---

## 🏆 RANKING FORMULA

### **Final Score**

```python
final_score = (
    anomaly_score * priority_weight +
    data_quality_score * 10 +
    h2h_bonus
)
```

### **Composants**

- **anomaly_score** - Score anomalie (0-100)
- **priority_weight** - Poids marché (0.9-1.5)
- **data_quality_score** - Qualité données (0-1)
- **h2h_bonus** - Bonus H2H (+5 si disponible)

### **Priority Weights**

| Priority | Weight | Exemples |
|----------|--------|----------|
| CRITICAL | 1.3-1.5 | HT Under 0.5, Extreme Under |
| HIGH | 1.1-1.2 | FT Under 2.5, HT Over 0.5 |
| MEDIUM | 0.9-1.0 | BTTS, FT Over 2.5 |
| LOW | 0.8 | Autres marchés |

---

## 🔍 FILTRAGE

### **Critères**

1. **Anomaly Score** ≥ 50.0
2. **Confidence** ≥ MEDIUM
3. **Sample Size** ≥ 8 matchs
4. **Data Quality** ≥ 0.6

### **Configuration**

```python
scanner.min_anomaly_score = 70.0  # Plus strict
scanner.min_sample_size = 12      # Plus de données
scanner.min_data_quality = 0.7    # Meilleure qualité
scanner.min_confidence = ConfidenceCategory.HIGH  # Haute confiance
```

---

## 📊 SUMMARY STATISTICS

```python
summary = scanner.get_summary(results)

{
    "total_results": 15,
    "by_priority": {
        "CRITICAL": 5,
        "HIGH": 7,
        "MEDIUM": 3
    },
    "by_confidence": {
        "HIGH": 8,
        "MEDIUM": 7
    },
    "avg_anomaly_score": 68.5,
    "avg_data_quality": 0.82,
    "provider": "sofascore"
}
```

---

## 🧪 TESTS

### **Tests Unitaires**

```bash
pytest tests/test_scanner_with_provider.py -v
```

**Couverture** :
- ✅ Initialization
- ✅ Basic scan
- ✅ Competition filter
- ✅ Max results
- ✅ Ranking
- ✅ Data quality
- ✅ Market priorities
- ✅ Filtering
- ✅ Summary generation
- ✅ Edge cases

---

### **Tests Intégration**

```bash
python scripts/test_scanner_integration.py
```

**Tests** :
1. ✅ Scanner avec MockProvider
2. ✅ Filtering functionality
3. ✅ Competition filtering
4. ✅ Scanner avec SofaScoreProvider (optionnel)

---

## 🔧 CONFIGURATION

### **Provider Selection**

```python
# Option 1: MockProvider (tests)
provider = MockDataProvider()

# Option 2: SofaScoreProvider (production)
provider = SofaScoreProvider()

# Create scanner
scanner = DailyScannerServiceV2(provider)
```

### **Environment Variable (futur)**

```bash
# .env
DATA_PROVIDER=mock  # or sofascore
```

---

## ⚠️ GESTION DONNÉES MANQUANTES

### **Historique Insuffisant**

```python
if not home_stats or not away_stats:
    logger.warning("Insufficient stats")
    return []  # Skip match
```

### **H2H Manquant**

```python
h2h_available = self._get_h2h(team_a_id, team_b_id)
# Continue sans H2H, pas de bonus
```

### **Odds Manquantes**

```python
if not odds_response.success:
    # Use default odds for priority markets
    odds_list = self._generate_default_odds()
```

### **Data Quality Faible**

```python
if data_quality < self.min_data_quality:
    logger.debug("Data quality too low")
    return []  # Skip match
```

---

## 📈 WORKFLOW COMPLET

```
1. Fetch Today's Matches
   ↓
2. For Each Match:
   ├─ Get Home Team Recent (15 matches)
   ├─ Get Away Team Recent (15 matches)
   ├─ Calculate Stats (StatsEngine)
   ├─ Calculate Data Quality
   ├─ Get H2H (optional)
   ├─ Get Odds (or use defaults)
   └─ For Each Market:
      ├─ Analyze (AnomalyEngine)
      └─ Create ScanResult
   ↓
3. Filter Weak Anomalies
   ↓
4. Rank by Final Score
   ↓
5. Return Top N Results
```

---

## 🎯 AVANTAGES

1. **Flexible** - Provider interchangeable
2. **Robuste** - Gestion données manquantes
3. **Testable** - MockProvider pour tests
4. **Transparent** - Data quality tracking
5. **Configurable** - Seuils ajustables
6. **Complet** - Pipeline end-to-end

---

## 🚀 PROCHAINES ÉTAPES

### **Court Terme**

1. ✅ Tests avec MockProvider
2. ⏳ Tests avec SofaScoreProvider
3. ⏳ Intégration Dashboard
4. ⏳ Configuration .env

### **Moyen Terme**

1. ⏳ Provider manager (auto-switch)
2. ⏳ Cache résultats scan
3. ⏳ Historique scans
4. ⏳ Alertes anomalies

---

## ✅ CHECKLIST

- ✅ DailyScannerServiceV2 créé
- ✅ Provider adapter créé
- ✅ Tests unitaires (15+)
- ✅ Script test intégration
- ✅ Documentation complète
- ✅ Gestion données manquantes
- ✅ Data quality tracking
- ✅ Ranking formula
- ✅ Filtrage configurable
- ✅ Summary statistics

---

**Scanner intégré avec DataProvider et opérationnel !** 🔗✨
