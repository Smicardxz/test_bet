# Guide de Débogage - Dashboard ✅

## 🔍 LOGS AJOUTÉS

### Console Browser (F12)

**Logs attendus:**
```javascript
[DATA] Loaded: {success: true, ...}
[DATA] Success: true
[DATA] Categories: {upcoming_inefficiencies: Array(5), ...}
[DATA] Total matches: 5
[DATA] First match: {home_team: "Ethiopia Nigd Bank", ...}
[DISPLAY] Starting displayMatches, allMatches: 5
[DISPLAY] Filtered matches: 5
[DISPLAY] Creating match cards...
[DISPLAY] Match cards created successfully
```

**Si erreur:**
```javascript
[ERROR] Loading data: ...
[DISPLAY] Error creating match cards: ...
```

---

## 🔧 ÉTAPES DE DÉBOGAGE

### 1. Ouvrir Console Browser

**Chrome/Edge:**
- F12
- Onglet "Console"

**Vérifier:**
- Pas d'erreurs rouges
- Logs `[DATA]` et `[DISPLAY]` présents

### 2. Vérifier Network

**F12 → Network:**
- Chercher `/api/data`
- Status: 200
- Preview: `success: true`

**Si 500:**
- Vérifier logs Flask
- Chercher traceback Python

### 3. Vérifier Logs Flask

**Terminal Flask:**
```
127.0.0.1 - - [29/May/2026 10:55:00] "GET /api/data HTTP/1.1" 200 -
```

**Si erreur:**
```
Error loading data: ...
Traceback (most recent call last):
  ...
```

---

## 🐛 ERREURS POSSIBLES

### Erreur 1: "Refreshing data..." infini

**Cause:** JavaScript error dans `createMatchCard`

**Solution:**
1. Ouvrir Console (F12)
2. Chercher erreur rouge
3. Vérifier ligne d'erreur

### Erreur 2: "No opportunities found"

**Cause:** `allMatches` vide

**Solution:**
1. Console: `console.log(allMatches)`
2. Vérifier `/api/data` retourne matchs
3. Vérifier catégorisation backend

### Erreur 3: API 500

**Cause:** Erreur Python backend

**Solution:**
1. Vérifier logs Flask
2. Chercher traceback
3. Fix erreur Python

### Erreur 4: TypeError undefined

**Cause:** Propriété manquante

**Solution:**
1. Vérifier safe checks: `match.property || null`
2. Vérifier `Array.isArray()` avant `.forEach()`
3. Vérifier `(value || 0).toFixed()`

---

## ✅ VÉRIFICATIONS

### Test 1: API Fonctionne

```bash
python test_api2.py
```

**Attendu:**
```
[TEST] Inefficiencies matches: 5
[TEST] First match:
  - Has match_profile: True
  - Has best_edges: True
```

### Test 2: Flask Tourne

```bash
curl http://localhost:5000/api/data
```

**Attendu:**
```json
{
  "success": true,
  "categories": {
    "upcoming_inefficiencies": [...]
  }
}
```

### Test 3: Dashboard Charge

**Ouvrir:** http://localhost:5000/

**Console:**
```
[DATA] Loaded: ...
[DISPLAY] Match cards created successfully
```

---

## 📝 COMMANDES UTILES

### Redémarrer Flask

```bash
# Arrêter
Get-Process python | Stop-Process -Force

# Démarrer
python app_flask.py
```

### Tester API

```bash
python test_api2.py
```

### Clear Cache

```bash
curl http://localhost:5000/api/refresh
```

---

## 🎯 CHECKLIST FINALE

**Backend:**
- [ ] Flask tourne (http://localhost:5000)
- [ ] `/api/data` retourne 200
- [ ] Response contient `success: true`
- [ ] Response contient matchs dans categories

**Frontend:**
- [ ] Console pas d'erreurs
- [ ] Logs `[DATA]` présents
- [ ] Logs `[DISPLAY]` présents
- [ ] `allMatches.length > 0`

**Display:**
- [ ] Match cards créés
- [ ] Profils affichés
- [ ] Pas de "Refreshing data..."

---

**Si tous les checks passent mais dashboard vide:**
1. Vider cache browser (Ctrl+Shift+Del)
2. Hard refresh (Ctrl+F5)
3. Attendre 2 minutes (cache API)
4. Refresh à nouveau

**Si problème persiste:**
1. Copier logs console
2. Copier logs Flask
3. Partager pour analyse
