# Dépannage Dashboard

## ✅ Corrections Appliquées

### Problème: Dashboard affiche "Loading matches..." indéfiniment

**Cause:** Erreur lors du chargement des données (ConnectionRefusedError)

**Solutions appliquées:**

#### 1. Gestion d'erreur dans load_data() ✅
**Fichier:** `app_flask.py` lignes 35-80

```python
try:
    manager = DataSourceManager()
    scanner = SmartScanner(...)
    scan_result = scanner.scan_today()
    return data
except Exception as e:
    logger.error(f"Error loading data: {e}")
    # Return minimal data structure
    return {
        "manager": None,
        "scanner": None,
        "scan_result": {
            "success": False,
            "error": str(e),
            ...
        }
    }
```

#### 2. Gestion d'erreur dans /api/data ✅
**Fichier:** `app_flask.py` lignes 100-130

```python
if data.get("manager") is None:
    return jsonify({
        "success": False,
        "error": data["scan_result"].get("error", "Failed to load data"),
        ...
    })
```

#### 3. Affichage d'erreur dans le frontend ✅
**Fichier:** `templates/dashboard_compact.html` lignes 498-511

```javascript
if (!data.success) {
    console.error('Data loading failed:', data.error);
    document.getElementById('loading').innerHTML = `
        <div>
            <h3>⚠️ Error Loading Data</h3>
            <p>${data.error}</p>
            <button onclick="location.reload()">🔄 Retry</button>
        </div>
    `;
    return;
}
```

---

## 🔍 Diagnostic des Erreurs Courantes

### Erreur 1: ConnectionRefusedError

**Symptômes:**
- Dashboard affiche "Loading matches..."
- Console: "Could not establish connection"

**Causes possibles:**
1. API_FOOTBALL_KEY invalide ou expirée
2. Quota API dépassé (100 requests/day)
3. API-Football temporairement indisponible
4. Problème réseau/firewall

**Solutions:**

**A. Vérifier la clé API:**
```bash
python scripts/diagnose_api_config.py
```

**B. Vérifier le quota:**
- Free tier: 100 requests/day
- Vérifier combien ont été utilisés
- Attendre 24h si quota dépassé

**C. Tester la connexion:**
```bash
python scripts/test_api_football.py
```

**D. Mode dégradé:**
Si l'API ne fonctionne pas, utiliser le mode mock temporairement:
```
# Dans .env
DATA_PROVIDER=mock
```

### Erreur 2: "Error loading data"

**Symptômes:**
- Dashboard affiche message d'erreur
- Bouton "Retry" visible

**Solutions:**

**A. Vérifier les logs Flask:**
```
Terminal Flask → Chercher "Error loading data:"
```

**B. Vérifier la console navigateur:**
```
F12 → Console → Chercher erreurs
```

**C. Rafraîchir le cache:**
```
http://localhost:5000/api/refresh
```

**D. Redémarrer Flask:**
```bash
Ctrl+C
python app_flask.py
```

### Erreur 3: Aucun match affiché

**Symptômes:**
- Stats: 0 / 0 / 0 / 0
- "No matches found"

**Causes:**
1. Aucun match aujourd'hui
2. Tous les matchs filtrés
3. Erreur de scan

**Solutions:**

**A. Vérifier la date:**
```javascript
// Console navigateur
console.log(new Date())
```

**B. Vérifier les filtres:**
- Reset filters
- Vérifier console logs

**C. Vérifier le scan:**
```bash
python scripts/test_single_real_analysis.py
```

---

## 🔧 Commandes de Dépannage

### 1. Diagnostic Complet
```bash
# Vérifier config
python scripts/diagnose_api_config.py

# Tester pipeline
python scripts/test_single_real_analysis.py

# Tester endpoint
python scripts/test_analyze_endpoint.py
```

### 2. Vérifier les Logs

**Backend (Terminal Flask):**
- Chercher "Error"
- Chercher "WARNING"
- Chercher traceback

**Frontend (Console F12):**
- Chercher erreurs rouges
- Vérifier "Received data"
- Vérifier "All matches combined"

### 3. Rafraîchir le Système

**A. Clear cache:**
```
http://localhost:5000/api/refresh
```

**B. Redémarrer Flask:**
```bash
Ctrl+C
python app_flask.py
```

**C. Hard refresh navigateur:**
```
Ctrl+Shift+R
```

---

## ✅ Checklist de Vérification

Avant de signaler un bug, vérifier:

- [ ] Flask est en cours d'exécution
- [ ] API_FOOTBALL_KEY est configurée
- [ ] Quota API non dépassé
- [ ] .env est chargé
- [ ] Console navigateur (F12) ouverte
- [ ] Logs Flask visibles
- [ ] Cache rafraîchi
- [ ] Page rafraîchie (Ctrl+Shift+R)

---

## 📊 État Actuel

**Corrections appliquées:**
- ✅ Gestion d'erreur load_data()
- ✅ Gestion d'erreur /api/data
- ✅ Affichage erreur frontend
- ✅ Bouton Retry
- ✅ Logs détaillés

**Le dashboard affiche maintenant:**
- ✅ Message d'erreur clair si problème
- ✅ Bouton Retry
- ✅ Logs console détaillés
- ✅ Pas de crash silencieux

**Prochaines étapes si erreur persiste:**
1. Ouvrir console (F12)
2. Vérifier le message d'erreur
3. Vérifier les logs Flask
4. Exécuter scripts de diagnostic
5. Vérifier quota API

---

## 🆘 Support

**Si le problème persiste:**

1. **Capturer les logs:**
   - Screenshot du message d'erreur
   - Console navigateur (F12)
   - Logs Flask (terminal)

2. **Informations système:**
   - DATA_PROVIDER=?
   - API_KEY configurée? (oui/non)
   - Quota utilisé?

3. **Tests effectués:**
   - diagnose_api_config.py
   - test_single_real_analysis.py
   - test_analyze_endpoint.py

**Le dashboard est maintenant robuste et affiche les erreurs clairement ! 🎯**
