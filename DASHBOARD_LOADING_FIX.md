# Dashboard Loading - Diagnostic et Fix

## 🐛 PROBLÈME IDENTIFIÉ

**Symptôme:** Dashboard charge à l'infini

**Cause:** API-Football rate limit atteint

**Logs Flask:**
```
Error loading odds: invalid literal for int() with base 10: ''
Rate limit reached. Waiting 57.1s
```

---

## 🔍 DIAGNOSTIC

### 1. Flask Status
```
✅ Flask démarre correctement
✅ Route / accessible (200 OK)
⚠️ Route /api/data lente (rate limit)
```

### 2. API-Football
```
⚠️ Rate limit atteint
⚠️ Attente 57 secondes entre requêtes
⚠️ Erreur parsing odds (champ vide)
```

### 3. Dashboard
```
✅ HTML chargé
⏳ JavaScript attend /api/data
⏳ Spinner visible pendant attente
```

---

## ✅ SOLUTIONS

### Solution 1: Attendre Rate Limit

**Le plus simple:**
1. Attendre 1-2 minutes
2. Rafraîchir dashboard (Ctrl+F5)
3. API-Football devrait répondre

**Commande:**
```
# Attendre puis tester
Start-Sleep -Seconds 120
curl http://localhost:5000/api/data
```

### Solution 2: Augmenter Cache Duration

**Fichier:** `app_flask.py`

**Modifier:**
```python
# AVANT
if age < 300:  # 5 minutes
    return cache["data"]

# APRÈS
if age < 900:  # 15 minutes
    return cache["data"]
```

**Avantage:** Moins de requêtes API

### Solution 3: Mock Data Temporaire

**Pour développement uniquement**

**Fichier:** `app_flask.py`

**Ajouter:**
```python
# En haut du fichier
USE_MOCK_FOR_DEV = True  # Mettre False en production

def load_data():
    # Si mock activé et rate limit
    if USE_MOCK_FOR_DEV and cache.get("rate_limited"):
        return get_mock_data()
    
    # Sinon logique normale
    ...
```

### Solution 4: Upgrade API-Football Tier

**Long terme:**
1. Upgrade vers tier supérieur
2. Plus de requêtes/minute
3. Plus de features (odds, etc.)

**Coût:** Variable selon tier

---

## 🔧 FIX IMMÉDIAT

### Fix 1: Augmenter Cache (RECOMMANDÉ)

```python
# app_flask.py ligne 31
if age < 900:  # 15 minutes au lieu de 5
    return cache["data"]
```

**Avantages:**
- ✅ Simple
- ✅ Réduit requêtes API
- ✅ Dashboard plus rapide

### Fix 2: Gérer Rate Limit Gracefully

**Fichier:** `app/providers/api_football_provider.py`

**Ajouter:**
```python
import time

class APIFootballProvider:
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 seconde entre requêtes
    
    def _rate_limit_wait(self):
        """Wait if needed to respect rate limit"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            logger.info(f"[RATE LIMIT] Waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint, params):
        self._rate_limit_wait()  # Attendre si besoin
        # Faire requête
        ...
```

### Fix 3: Error Handling Odds

**Le problème:**
```
Error loading odds: invalid literal for int() with base 10: ''
```

**Cause:** Champ odd vide dans réponse API

**Fix:**
```python
# Quelque part dans le code qui parse les odds
try:
    odd_value = int(odd_string)
except (ValueError, TypeError):
    odd_value = None  # ou valeur par défaut
    logger.warning(f"Invalid odd value: {odd_string}")
```

---

## 📊 VÉRIFICATION

### Test 1: Cache Fonctionne

```python
# Dans load_data()
logger.info(f"[CACHE] Age: {age:.0f}s, Using cache: {age < 900}")
```

**Attendu:**
```
[CACHE] Age: 120s, Using cache: True
```

### Test 2: Rate Limit Géré

```python
# Dans provider
logger.info(f"[RATE LIMIT] Last request: {elapsed:.1f}s ago")
```

**Attendu:**
```
[RATE LIMIT] Last request: 1.2s ago
[RATE LIMIT] Waiting 0.0s
```

### Test 3: Dashboard Charge

**Ouvrir:** http://localhost:5000/

**Vérifier:**
1. ✅ Page HTML charge
2. ✅ Spinner visible
3. ⏳ Attente /api/data
4. ✅ Matches affichés après réponse

**Console (F12):**
```javascript
[DATA] Loading...
[DATA] Loaded: {success: true, ...}
```

---

## 🚀 IMPLÉMENTATION RAPIDE

### Étape 1: Augmenter Cache

```bash
# Ouvrir app_flask.py
# Ligne 31, changer:
if age < 900:  # 15 minutes
```

### Étape 2: Redémarrer Flask

```bash
# Arrêter
Ctrl+C

# Redémarrer
python app_flask.py
```

### Étape 3: Tester

```bash
# Ouvrir dashboard
http://localhost:5000/

# Vérifier logs
# Devrait voir:
[CACHE] Using cache: True
```

---

## 📝 LOGS ATTENDUS

### Bon Fonctionnement

```
[CACHE] Age: 45s, Using cache: True
127.0.0.1 - - [29/May/2026 09:15:00] "GET /api/data HTTP/1.1" 200 -
```

### Rate Limit

```
Rate limit reached. Waiting 57.1s
[CACHE] Age: 600s, Cache expired, reloading...
```

### Erreur Odds

```
Error loading odds: invalid literal for int() with base 10: ''
→ Non bloquant, continue analyse
```

---

## ✅ CHECKLIST

### Immédiat
- [ ] Augmenter cache duration (5min → 15min)
- [ ] Redémarrer Flask
- [ ] Tester dashboard
- [ ] Vérifier logs cache

### Court Terme
- [ ] Ajouter rate limit handler
- [ ] Fix parsing odds errors
- [ ] Ajouter retry logic
- [ ] Améliorer error messages

### Long Terme
- [ ] Upgrade API-Football tier
- [ ] Implémenter queue système
- [ ] Ajouter caching Redis
- [ ] Monitoring rate limits

---

## 🎯 RÉSUMÉ

**Problème:** Rate limit API-Football

**Cause:** Trop de requêtes en peu de temps

**Solution immédiate:** Augmenter cache duration

**Solution long terme:** Upgrade tier + rate limit handler

---

## 🔧 CODE FIXES

### Fix 1: Cache Duration

```python
# app_flask.py
def load_data():
    now = datetime.now()
    
    if cache["data"] and cache["timestamp"]:
        age = (now - cache["timestamp"]).total_seconds()
        if age < 900:  # ← CHANGÉ: 15 minutes au lieu de 5
            logger.info(f"[CACHE] Using cached data (age: {age:.0f}s)")
            return cache["data"]
    
    logger.info("[CACHE] Cache expired or empty, loading fresh data...")
    # Charger nouvelles données
    ...
```

### Fix 2: Rate Limit Wait

```python
# app/providers/api_football_provider.py
import time

class APIFootballProvider:
    def __init__(self, config):
        self.config = config
        self.last_request = 0
        self.min_interval = 1.0  # 1 seconde minimum
    
    def _wait_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_request
        
        if elapsed < self.min_interval:
            wait = self.min_interval - elapsed
            logger.info(f"[RATE LIMIT] Waiting {wait:.1f}s")
            time.sleep(wait)
        
        self.last_request = time.time()
    
    def get_today_fixtures(self, date=None):
        self._wait_rate_limit()  # ← AJOUTER
        # Faire requête
        ...
```

### Fix 3: Odds Parsing

```python
# Quelque part où les odds sont parsées
def parse_odd_value(odd_str):
    """Parse odd value safely"""
    if not odd_str or odd_str == '':
        return None
    
    try:
        return float(odd_str)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid odd value: '{odd_str}' - {e}")
        return None
```

---

**Appliquez Fix 1 (Cache) immédiatement pour résoudre le problème ! 🚀**
