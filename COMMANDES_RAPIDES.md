# Commandes Rapides - Betting Intelligence

## 🚀 DÉMARRAGE RAPIDE

### 1. Démarrer le Système
```bash
# Démarrer Flask
python app_flask.py
```

**Attendu:**
```
============================================================
 DASHBOARD FLASK
============================================================

Dashboard URL: http://localhost:5000

 * Running on http://127.0.0.1:5000
```

### 2. Ouvrir Dashboard
```
http://localhost:5000/
```

### 3. Tester
- Vérifier header stats
- Voir matches cards
- Cliquer "Analyze Match"
- Tester Quick View / Deep Analysis

---

## 🔧 COMMANDES UTILES

### Arrêter Flask
```powershell
Get-Process python | Where-Object {$_.Path -like "*test bet*"} | Stop-Process -Force
```

### Redémarrer Flask
```bash
# Arrêter puis redémarrer
python app_flask.py
```

### Test API
```bash
# Test endpoint data
curl http://localhost:5000/api/data

# Ou dans PowerShell
Invoke-WebRequest http://localhost:5000/api/data
```

### Vérifier Logs
```bash
# Les logs s'affichent dans le terminal Flask
# Chercher:
[INFO] Total matches: X
[ANALYSIS] Status: ANALYZABLE_NO_ODDS
```

---

## 🧪 TESTS

### Test Upgrade API
```bash
python scripts/test_api_football_upgrade.py
```

**Attendu:**
```
Matches Tested: 10
Data Availability:
  - Home history: 10/10 (100%)
  - HT scores: 10/10 (100%)
[SUCCESS] Upgrade is EFFECTIVE
```

### Debug Historique
```bash
python scripts/debug_team_history.py --fixture_id FIXTURE_ID
```

---

## 📂 ROUTES DISPONIBLES

### Dashboards
```
http://localhost:5000/           # Nouveau (Intelligence)
http://localhost:5000/compact    # Ancien (Compact)
http://localhost:5000/full       # Complet
```

### API
```
GET  http://localhost:5000/api/data
POST http://localhost:5000/api/analyze_match
GET  http://localhost:5000/api/refresh
```

---

## 🐛 DÉPANNAGE RAPIDE

### Dashboard charge à l'infini
```
1. F12 → Console → Vérifier erreurs
2. F12 → Network → Vérifier /api/data
3. Redémarrer Flask
4. Vider cache (Ctrl+F5)
```

### Pas de matches
```
1. Vérifier logs Flask
2. Tester: curl http://localhost:5000/api/data
3. Vérifier API-Football quota
```

### Analyze échoue
```
1. Vérifier console browser
2. Vérifier logs Flask
3. Chercher: DATA_INSUFFICIENT
```

---

## 📊 FICHIERS IMPORTANTS

### Backend
```
app_flask.py                              # Routes Flask
app/providers/api_football_provider.py    # API-Football
app/services/scanner/smart_scanner.py     # Analyse
app/services/data/match_data_loader.py    # Historique
```

### Frontend
```
templates/dashboard_intelligence.html     # Nouveau dashboard
templates/dashboard_compact.html          # Ancien dashboard
```

### Scripts
```
scripts/test_api_football_upgrade.py      # Test upgrade
scripts/debug_team_history.py             # Debug historique
```

### Documentation
```
PROJET_COMPLET.md                         # Vue d'ensemble
DASHBOARD_READY.md                        # Dashboard prêt
TEST_DASHBOARD.md                         # Guide tests
COMMANDES_RAPIDES.md                      # Ce fichier
```

---

## ✅ CHECKLIST QUOTIDIENNE

### Avant de commencer
- [ ] Flask démarré
- [ ] Dashboard accessible
- [ ] API-Football quota OK
- [ ] Pas d'erreur console

### Pendant utilisation
- [ ] Matches chargés
- [ ] Analyze fonctionne
- [ ] Modals s'ouvrent
- [ ] Pas de freeze

### Fin de session
- [ ] Arrêter Flask (Ctrl+C)
- [ ] Vérifier logs erreurs
- [ ] Noter problèmes

---

## 🎯 RACCOURCIS CLAVIER

### Browser
```
F12          # Ouvrir DevTools
Ctrl+F5      # Refresh + vider cache
Ctrl+Shift+I # Ouvrir console
Ctrl+Shift+C # Inspect element
```

### Flask
```
Ctrl+C       # Arrêter serveur
```

---

## 📝 NOTES RAPIDES

### URLs à retenir
```
Dashboard:  http://localhost:5000/
API Data:   http://localhost:5000/api/data
Compact:    http://localhost:5000/compact
```

### Ports
```
Flask:      5000
```

### Logs importants
```
[INFO] Total matches: X
[ANALYSIS] Status: ANALYZABLE_NO_ODDS
[HISTORY] Strategy used: team+last+season
```

---

**Bon travail ! 🚀**
