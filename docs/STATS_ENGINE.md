# 📊 StatsEngine - Documentation Complète

**Version** : 1.0.0  
**Type** : Local  
**Objectif** : Calculer statistiques pour détection anomalies

---

## 🎯 Vue d'Ensemble

**StatsEngine** calcule des statistiques complètes sur les équipes de football pour détecter des anomalies bookmakers.

### **Caractéristiques**

✅ **Fonctions pures** et testables  
✅ **Typage complet** (type hints)  
✅ **Gestion petits échantillons**  
✅ **Gestion données manquantes**  
✅ **Export JSON** propre  
✅ **Tests unitaires** complets  

---

## 📋 Statistiques Calculées

### **1. FULL TIME (11 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `avg_total_goals` | Moyenne buts total | float |
| `avg_goals_scored` | Moyenne buts marqués | float |
| `avg_goals_conceded` | Moyenne buts encaissés | float |
| `under_1_5_rate` | % matchs < 2 buts | % (0-100) |
| `under_2_5_rate` | % matchs < 3 buts | % (0-100) |
| `under_3_5_rate` | % matchs < 4 buts | % (0-100) |
| `under_4_5_rate` | % matchs < 5 buts | % (0-100) |
| `under_5_5_rate` | % matchs < 6 buts | % (0-100) |
| `under_extreme_line_rate` | % matchs < 10.5 buts | % (0-100) |
| `over_1_5_rate` | % matchs > 1 but | % (0-100) |
| `over_2_5_rate` | % matchs > 2 buts | % (0-100) |
| `over_3_5_rate` | % matchs > 3 buts | % (0-100) |
| `over_4_5_rate` | % matchs > 4 buts | % (0-100) |
| `over_5_5_rate` | % matchs > 5 buts | % (0-100) |
| `btts_rate` | % BTTS (both teams score) | % (0-100) |
| `clean_sheet_rate` | % clean sheets (total) | % (0-100) |
| `clean_sheet_for_rate` | % clean sheets pour | % (0-100) |
| `clean_sheet_against_rate` | % clean sheets contre | % (0-100) |

---

### **2. FIRST HALF (11 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `avg_ht_goals` | Moyenne buts HT | float |
| `avg_ht_scored` | Moyenne buts marqués HT | float |
| `avg_ht_conceded` | Moyenne buts encaissés HT | float |
| `ht_under_0_5_rate` | % HT < 1 but | % (0-100) |
| `ht_under_1_5_rate` | % HT < 2 buts | % (0-100) |
| `ht_over_0_5_rate` | % HT > 0 but | % (0-100) |
| `ht_over_1_5_rate` | % HT > 1 but | % (0-100) |
| `ht_over_2_5_rate` | % HT > 2 buts | % (0-100) |
| `ht_0_0_rate` | % HT 0-0 | % (0-100) |
| `ht_btts_rate` | % BTTS HT | % (0-100) |

---

### **3. SECOND HALF (4 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `avg_second_half_goals` | Moyenne buts 2ème MT | float |
| `avg_second_half_scored` | Moyenne buts marqués 2ème MT | float |
| `avg_second_half_conceded` | Moyenne buts encaissés 2ème MT | float |
| `late_goal_rate` | % buts après 75min | % (0-100) |

---

### **4. STABILITY (6 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `goals_variance` | Variance buts FT | float |
| `goals_std_dev` | Écart-type buts FT | float |
| `ht_goals_variance` | Variance buts HT | float |
| `ht_goals_std_dev` | Écart-type buts HT | float |
| `consistency_score` | Score cohérence (0-1) | float |
| `stability_score` | Score stabilité (0-1) | float |

**Formules** :
```python
# Consistency = inverse du coefficient de variation
CV = std_dev / mean
consistency = 1 / (1 + CV)

# Stability = moyenne de consistency et variance normalisée
stability = (consistency + (1 - min(variance / 5, 1))) / 2
```

---

### **5. TRENDING (5 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `last_5_avg_goals` | Moyenne 5 derniers matchs | float |
| `last_5_form_score` | Score forme 5 derniers (0-1) | float |
| `last_10_avg_goals` | Moyenne 10 derniers matchs | float |
| `last_10_form_score` | Score forme 10 derniers (0-1) | float |
| `momentum_score` | Momentum (-1 à 1) | float |

**Momentum** :
```python
# Compare première moitié vs deuxième moitié de l'échantillon
momentum = (recent_avg - older_avg) / max(older_avg, 1)
# Normalisé entre -1 et 1
# Positif = amélioration, Négatif = déclin
```

---

### **6. DATA QUALITY (3 métriques)**

| Métrique | Description | Type |
|----------|-------------|------|
| `missing_ht_data_count` | Nombre données HT manquantes | int |
| `missing_ft_data_count` | Nombre données FT manquantes | int |
| `data_quality_score` | Score qualité (0-1) | float |

**Formule** :
```python
completeness_ft = 1 - (missing_ft / total_matches)
completeness_ht = 1 - (missing_ht / total_matches)
quality = (completeness_ft + completeness_ht) / 2
```

---

## 💻 Utilisation

### **Import**

```python
from app.services.stats import StatsEngine
from app.db.session import SessionLocal
```

---

### **Exemple Basique**

```python
# Créer session database
db = SessionLocal()

# Initialiser engine
engine = StatsEngine(db)

# Calculer stats
stats = engine.calculate_team_stats(
    team_id=1,
    home_away="all",  # "home", "away", or "all"
    last_n=15  # Nombre de matchs
)

if stats:
    print(f"Avg goals: {stats.avg_total_goals:.2f}")
    print(f"Under 2.5 rate: {stats.under_2_5_rate:.1f}%")
    print(f"Stability: {stats.stability_score:.2f}")

db.close()
```

---

### **Export JSON**

```python
stats = engine.calculate_team_stats(team_id=1, home_away="all", last_n=15)

if stats:
    # Convertir en dict
    stats_dict = stats.to_dict()
    
    # Convertir en JSON
    stats_json = stats.to_json()
    
    # Sauvegarder
    import json
    with open("team_stats.json", "w") as f:
        json.dump(stats_json, f, indent=2)
```

---

### **Home/Away Split**

```python
# Stats à domicile
home_stats = engine.calculate_team_stats(
    team_id=1,
    home_away="home",
    last_n=10
)

# Stats à l'extérieur
away_stats = engine.calculate_team_stats(
    team_id=1,
    home_away="away",
    last_n=10
)

# Comparer
if home_stats and away_stats:
    print(f"Home avg goals: {home_stats.avg_goals_scored:.2f}")
    print(f"Away avg goals: {away_stats.avg_goals_scored:.2f}")
```

---

## 🔧 Configuration

### **Paramètres Engine**

```python
engine = StatsEngine(db)

# Modifier seuils
engine.min_sample_size = 8  # Minimum matchs requis (défaut: 5)
engine.extreme_line = 12.5  # Ligne extrême (défaut: 10.5)
```

---

## 🛡️ Gestion Erreurs

### **Données Insuffisantes**

```python
stats = engine.calculate_team_stats(team_id=1, home_away="all", last_n=15)

if stats is None:
    print("❌ Données insuffisantes (< 5 matchs)")
else:
    print(f"✅ Stats calculées ({stats.sample_size} matchs)")
```

---

### **Données Manquantes**

```python
if stats:
    # Vérifier qualité
    if stats.data_quality_score >= 0.9:
        print("✅ Excellente qualité")
    elif stats.data_quality_score >= 0.7:
        print("⚠️ Bonne qualité")
    else:
        print("❌ Qualité faible - prudence")
    
    # Détails
    print(f"Missing HT: {stats.missing_ht_data_count}")
    print(f"Missing FT: {stats.missing_ft_data_count}")
```

---

### **Petits Échantillons**

```python
if stats:
    if stats.sample_size < 8:
        print("⚠️ Échantillon petit - résultats moins fiables")
    elif stats.sample_size < 12:
        print("ℹ️ Échantillon modéré")
    else:
        print("✅ Échantillon robuste")
```

---

## 📊 Format JSON

### **Structure Complète**

```json
{
  "team_id": 1,
  "team_name": "Wrexham AFC",
  "sample_size": 15,
  "home_away": "all",
  "last_updated": "2026-05-27T12:00:00",
  
  "avg_total_goals": 2.5,
  "avg_goals_scored": 1.5,
  "avg_goals_conceded": 1.0,
  
  "under_1_5_rate": 30.0,
  "under_2_5_rate": 50.0,
  "under_3_5_rate": 70.0,
  "over_2_5_rate": 50.0,
  
  "btts_rate": 60.0,
  "clean_sheet_rate": 20.0,
  
  "avg_ht_goals": 0.8,
  "ht_0_0_rate": 40.0,
  "ht_under_0_5_rate": 40.0,
  
  "avg_second_half_goals": 1.7,
  
  "goals_variance": 1.5,
  "goals_std_dev": 1.22,
  "consistency_score": 0.75,
  "stability_score": 0.80,
  
  "last_5_avg_goals": 2.8,
  "last_10_avg_goals": 2.5,
  "momentum_score": 0.15,
  
  "missing_ht_data_count": 0,
  "missing_ft_data_count": 0,
  "data_quality_score": 1.0
}
```

---

## 🧪 Tests

### **Lancer Tests**

```bash
# Tous les tests
pytest tests/test_stats_engine.py -v

# Tests spécifiques
pytest tests/test_stats_engine.py::TestUtilityFunctions -v

# Avec coverage
pytest tests/test_stats_engine.py --cov=app.services.stats
```

---

### **Tests Inclus**

✅ **Utility functions** (8 tests)
- safe_mean, safe_variance, safe_stdev
- percentage, form_score, momentum

✅ **TeamStats dataclass** (2 tests)
- to_dict(), to_json()

✅ **Edge cases** (4 tests)
- Valeurs nulles, variance élevée, limites momentum

---

## 📈 Performance

### **Complexité**

- **Temps** : O(n) où n = nombre de matchs
- **Espace** : O(n) pour stockage temporaire

### **Optimisations**

✅ Requêtes database optimisées (LIMIT, ORDER BY)  
✅ Calculs en une passe  
✅ Pas de boucles imbriquées  
✅ Fonctions pures (pas d'effets de bord)  

---

## ✅ Checklist Utilisation

Avant d'utiliser les stats :

- [ ] Sample size ≥ 5 (minimum)
- [ ] Sample size ≥ 8 (recommandé)
- [ ] Data quality score ≥ 0.7
- [ ] Missing data < 20%
- [ ] Variance raisonnable (< 5.0)

---

## 🎯 Prochaines Étapes

Les stats sont prêtes pour :

✅ **AnomalyEngine** - Détection anomalies  
✅ **ConfidenceEngine** - Scoring confiance  
✅ **ExplanationEngine** - Génération explications  
✅ **Scanner** - Scan automatique  

---

**StatsEngine complet et prêt à l'emploi !** 📊✨
