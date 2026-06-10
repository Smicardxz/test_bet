# Guide Simple - Dashboard

## 🚀 Lancer le Dashboard

### Méthode Simple (Recommandée)

**Double-cliquez sur:** `LANCER_DASHBOARD.bat`

**Résultat:**
- Une fenêtre CMD s'ouvre
- Streamlit démarre
- Le navigateur s'ouvre automatiquement sur http://localhost:8501
- Le dashboard s'affiche

---

## 🛑 Arrêter le Dashboard

### Méthode 1: Fermer la Fenêtre

Fermez simplement la fenêtre CMD qui a été ouverte.

### Méthode 2: Script

**Double-cliquez sur:** `KILL_ALL.bat`

Cela arrête tous les processus Streamlit et Python.

---

## 🔧 Si Ça Ne Marche Pas

### Étape 1: Arrêter Tout

Double-cliquez sur `KILL_ALL.bat`

### Étape 2: Attendre 5 Secondes

Attendez que tous les processus soient arrêtés.

### Étape 3: Relancer

Double-cliquez sur `LANCER_DASHBOARD.bat`

---

## 📊 Vérifier que le Système Fonctionne

### Test Backend

Ouvrez PowerShell et tapez:
```powershell
python test_dashboard_loading.py
```

**Si vous voyez "✅ ALL TESTS PASSED":** Le système fonctionne !

---

## ⚠️ Problèmes Connus

### PowerShell Bloque les Commandes

**Symptôme:** Les commandes ne répondent pas dans PowerShell

**Solution:** Utilisez les fichiers .bat au lieu de PowerShell
- `LANCER_DASHBOARD.bat` pour lancer
- `KILL_ALL.bat` pour arrêter

### Streamlit Ne Démarre Pas

**Symptôme:** Rien ne se passe après avoir lancé

**Solution:**
1. Lancez `KILL_ALL.bat`
2. Attendez 5 secondes
3. Relancez `LANCER_DASHBOARD.bat`

### Le Navigateur Ne S'Ouvre Pas

**Solution:** Ouvrez manuellement http://localhost:8501

---

## 📝 Fichiers Importants

### Pour Lancer
- **`LANCER_DASHBOARD.bat`** ← Double-cliquez ici

### Pour Arrêter
- **`KILL_ALL.bat`** ← Double-cliquez ici

### Pour Tester
- **`test_dashboard_loading.py`** ← `python test_dashboard_loading.py`

### Dashboard
- **`dashboard_fixed.py`** ← Version qui fonctionne

---

## 🎯 Résumé

**Pour lancer:** Double-clic sur `LANCER_DASHBOARD.bat`

**Pour arrêter:** Double-clic sur `KILL_ALL.bat`

**URL:** http://localhost:8501

**C'est tout ! 🎯**
