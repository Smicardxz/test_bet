# 🚀 Quick Start Guide

**Version** : 2.0.0  
**Date** : 27 Mai 2026

---

## ⚡ Démarrage Rapide (5 minutes)

### **1. Installation**

```bash
# Cloner/Accéder au projet
cd "test bet"

# Installer dépendances
pip install -r requirements.txt
```

---

### **2. Générer Dataset Mock**

```bash
# Générer données de test
python app/utils/mock_dataset_generator.py

# Charger dans database
python app/utils/load_mock_dataset.py
```

**Output attendu** :
```
✅ Generated 20 teams
✅ Generated ~300 historical matches
✅ Generated odds for ~10 matches
✅ Dataset loaded successfully!
```

---

### **3. Démarrer l'API**

```bash
# Terminal 1
python -m app.main
```

**Output attendu** :
```
🚀 Local Anomaly Scanner started
📚 Documentation: http://localhost:8000/docs
🏠 Local mode - SQLite database
```

---

### **4. Démarrer le Dashboard**

```bash
# Terminal 2
streamlit run dashboard.py
```

**Output attendu** :
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

---

### **5. Utiliser le Dashboard**

1. **Ouvrir** : `http://localhost:8501`
2. **Voir** : Top anomalies du jour
3. **Filtrer** : Par confidence, marché
4. **Explorer** : Détails, explications

---

## 📊 Workflow Complet

### **Option A: Avec Mock Dataset**

```bash
# 1. Générer données
python app/utils/mock_dataset_generator.py
python app/utils/load_mock_dataset.py

# 2. Démarrer API (Terminal 1)
python -m app.main

# 3. Démarrer Dashboard (Terminal 2)
streamlit run dashboard.py

# 4. Accéder
# Dashboard: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

---

### **Option B: Test Pipeline Complet**

```bash
# Test automatique complet
python test_complete_pipeline.py
```

**Ce test va** :
- ✅ Générer dataset
- ✅ Charger en database
- ✅ Scanner matchs
- ✅ Détecter anomalies
- ✅ Générer explications
- ✅ Exporter rapports

---

## 🎯 Endpoints API Principaux

### **Scanner**
```bash
GET http://localhost:8000/api/scanner/top-anomalies
```

### **Matchs**
```bash
GET http://localhost:8000/api/matches/today
```

### **Analyse**
```bash
GET http://localhost:8000/api/analysis/{match_id}
```

### **Marchés**
```bash
GET http://localhost:8000/api/markets/top-ht-under
GET http://localhost:8000/api/markets/top-extreme-under
GET http://localhost:8000/api/markets/top-btts-anomalies
```

---

## 📚 Documentation

### **Guides Complets**

1. `FINAL_PROJECT_SUMMARY.md` - Vue d'ensemble projet
2. `API_DOCUMENTATION.md` - Documentation API complète
3. `DASHBOARD_COMPLETE.md` - Documentation dashboard
4. `STATS_ENGINE_COMPLETE.md` - StatsEngine
5. `ANOMALY_ENGINE_COMPLETE.md` - AnomalyEngine
6. `EXPLANATION_ENGINE_COMPLETE.md` - ExplanationEngine

### **API Documentation**

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 Tests

### **Tests Unitaires**

```bash
# Tous les tests
pytest tests/ -v

# Avec coverage
pytest tests/ --cov=app.services

# Tests spécifiques
pytest tests/test_stats_engine.py -v
pytest tests/test_anomaly_engine.py -v
pytest tests/test_daily_scanner.py -v
```

---

### **Test Pipeline**

```bash
# Test stack complet
python test_full_stack.py

# Test avec explications
python test_complete_pipeline.py
```

---

## 📁 Structure Projet

```
test bet/
├── app/
│   ├── services/
│   │   ├── stats/          # StatsEngine
│   │   ├── anomaly/        # AnomalyEngine
│   │   ├── scanner/        # DailyScannerService
│   │   └── explanation/    # ExplanationEngine
│   ├── api/
│   │   └── routes/         # API endpoints
│   ├── utils/              # Mock dataset
│   └── main.py             # API entry point
├── tests/                  # Unit tests
├── examples/               # Usage examples
├── dashboard.py            # Streamlit dashboard
└── requirements.txt        # Dependencies
```

---

## ⚙️ Configuration

### **Ports**

- API: `8000`
- Dashboard: `8501`

### **Database**

- Type: SQLite
- Location: `./football_anomalies.db`

### **CORS**

- Allowed: `localhost:3000`, `localhost:8000`

---

## 🎨 Dashboard Pages

### **🏠 Main Dashboard**

- Top anomalies du jour
- Filtres (confidence, marché)
- Métriques summary

### **📊 Market Analysis**

- HT Under anomalies
- Extreme Under anomalies
- BTTS anomalies

### **🔍 Match Detail**

- Analyse complète match
- Tous marchés
- Explications détaillées

### **ℹ️ About**

- Information projet
- Documentation
- Usage

---

## 🐛 Troubleshooting

### **API ne démarre pas**

```bash
# Vérifier port 8000 disponible
netstat -ano | findstr :8000

# Changer port si nécessaire
uvicorn app.main:app --port 8001
```

---

### **Dashboard ne se connecte pas**

1. Vérifier API running: `http://localhost:8000/health`
2. Vérifier CORS configuré
3. Vérifier `API_BASE_URL` dans `dashboard.py`

---

### **Pas de données**

```bash
# Recharger mock dataset
python app/utils/mock_dataset_generator.py
python app/utils/load_mock_dataset.py
```

---

## ✅ Checklist Démarrage

- [ ] Python 3.8+ installé
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Dataset généré et chargé
- [ ] API démarrée (port 8000)
- [ ] Dashboard démarré (port 8501)
- [ ] Browser ouvert sur `localhost:8501`

---

## 🎉 Résultat Attendu

### **Dashboard Affiche**

✅ Top 10-20 anomalies  
✅ Scores 50-90/100  
✅ Confidence HIGH/MEDIUM  
✅ Marchés variés (HT, FT, BTTS)  
✅ Explications professionnelles  
✅ Signaux et risques  

### **Anomalies Typiques**

- **HT Under 0.5** - London City Lionesses vs Bristol City (Score: 78.5, HIGH)
- **FT Under 10.5** - Curzon Ashton vs Brackley Town (Score: 82.3, HIGH)
- **BTTS** - Manchester United U21 vs Liverpool U21 (Score: 68.0, MEDIUM)

---

**Prêt en 5 minutes !** 🚀✨
