# 🎯 Bookmaker Inefficiency Detector - Flask

Système d'analyse de paris sportifs avec interface Flask (compatible Python 3.14).

## 🚀 Démarrage Rapide

### 1. Installer Flask

```bash
pip install flask
```

### 2. Lancer le Dashboard

**Double-cliquez sur:** `LANCER_FLASK.bat`

**Ou en ligne de commande:**
```bash
python app_flask.py
```

### 3. Ouvrir le Navigateur

Le dashboard s'ouvre automatiquement sur: **http://localhost:5000**

---

## 📁 Structure du Projet

### Backend (Fonctionne parfaitement)
```
app/
├── providers/          # API-Football integration
├── services/
│   ├── targeting/     # League targeting V2
│   ├── scanner/       # Smart scanner
│   ├── signals/       # Signal detection
│   ├── anomaly/       # Line breach analysis
│   ├── value/         # Value detector
│   └── validation/    # Data validation
└── utils/             # Match status helpers
```

### Frontend (Flask)
```
app_flask.py           # Application Flask
templates/
└── dashboard.html     # Interface HTML/CSS/JS
```

---

## 🎯 Fonctionnalités

### ✅ Backend
- **Smart Targeting**: Ligues mineures bettables
- **Signal Detection**: EXTREME_UNDER, HT_UNDER, BTTS
- **Value Detection**: Statistical confidence vs Market value
- **Match Status**: Upcoming / Live / Finished
- **Coverage Estimation**: Bookmaker coverage 0-100%

### ✅ Frontend Flask
- **Interface Simple**: HTML/CSS/JS pur
- **Compatible**: Toutes versions Python (3.9-3.14)
- **Léger**: Pas de dépendances lourdes
- **Rapide**: Chargement < 1 seconde
- **Auto-refresh**: Toutes les 5 minutes

---

## 🔧 Scripts Disponibles

### Lancement
- **`LANCER_FLASK.bat`** - Lance le dashboard Flask

### Nettoyage
- **`NETTOYER_PROJET.bat`** - Supprime les fichiers obsolètes
- **`KILL_ALL.bat`** - Arrête tous les processus

### Tests
- **`test_dashboard_loading.py`** - Test backend

---

## 📊 Ce Que Vous Verrez

### Stats Globales
- Total Matches: 117
- Target Matches: 31
- Analyzed: 10
- Scan Time: 1.1s

### Matchs Analysés
Pour chaque match:
- Équipes et compétition
- Target Level et Score
- Coverage bookmaker
- Signaux détectés (type, confidence, value)

---

## 🧹 Nettoyage du Projet

Pour supprimer tous les fichiers obsolètes (anciens dashboards Streamlit, docs, etc.):

```bash
NETTOYER_PROJET.bat
```

**Supprime:**
- Tous les dashboard_vX.py (Streamlit)
- Scripts de réinstallation obsolètes
- Documentation obsolète
- Environnement virtuel venv_clean

**Conserve:**
- app_flask.py (nouveau dashboard)
- app/ (backend)
- Scripts essentiels
- Documentation utile

---

## ⚠️ Pourquoi Flask au lieu de Streamlit ?

**Streamlit ne fonctionne PAS avec Python 3.14**

Erreur: `OSError: [WinError -2147217358]`

**Flask fonctionne avec:**
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13
- ✅ Python 3.14 ← Votre version

---

## 🎯 Résumé

**Lancer:** `LANCER_FLASK.bat`
**URL:** http://localhost:5000
**Arrêter:** Fermer la fenêtre ou Ctrl+C
**Nettoyer:** `NETTOYER_PROJET.bat`

**Le système est opérationnel avec Flask ! 🎯**
