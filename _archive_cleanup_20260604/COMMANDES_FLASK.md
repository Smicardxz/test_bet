# Commandes Flask - Guide Rapide

## 🚀 Lancer Flask

### Commande Simple (Recommandée)

```powershell
python app_flask.py
```

**Résultat:**
```
============================================================
 DASHBOARD FLASK
============================================================

Dashboard URL: http://localhost:5000

 * Running on http://127.0.0.1:5000
```

**Puis ouvrir:** http://localhost:5000

---

## 🛑 Arrêter Flask

### Méthode 1: Dans le Terminal

Appuyez sur `Ctrl+C` dans le terminal où Flask tourne

### Méthode 2: Tuer Tous les Processus Python

```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 🔄 Redémarrer Flask

```powershell
# 1. Arrêter
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Attendre 2 secondes
Start-Sleep -Seconds 2

# 3. Relancer
python app_flask.py
```

---

## ⚠️ Si LANCER_FLASK.bat Ne Marche Pas

**Problème:** PowerShell bloque les .bat

**Solution:** Utiliser directement Python

```powershell
python app_flask.py
```

---

## 🌐 URLs Disponibles

### Dashboard Principal
**http://localhost:5000**

### API Endpoints

**Données:**
```
GET http://localhost:5000/api/data
```

**Refresh:**
```
GET http://localhost:5000/api/refresh
```

---

## 📊 Vérifier que Flask Tourne

### Méthode 1: Vérifier le Port

```powershell
netstat -ano | findstr ":5000"
```

**Si vous voyez une ligne:** Flask tourne

### Méthode 2: Vérifier le Processus

```powershell
Get-Process python
```

**Si vous voyez python.exe:** Flask tourne

### Méthode 3: Ouvrir le Navigateur

Allez sur http://localhost:5000

**Si le dashboard s'affiche:** ✅ Fonctionne

---

## 🔧 Troubleshooting

### Problème: "Address already in use"

**Solution:**
```powershell
Get-Process python | Stop-Process -Force
Start-Sleep -Seconds 2
python app_flask.py
```

### Problème: "ModuleNotFoundError"

**Solution:**
```powershell
pip install flask
python app_flask.py
```

### Problème: Page ne charge pas

**Vérifier:**
1. Flask tourne ? → `Get-Process python`
2. Port 5000 ouvert ? → `netstat -ano | findstr ":5000"`
3. Erreur dans le terminal ?

**Solution:**
```powershell
# Arrêter tout
Get-Process python | Stop-Process -Force

# Relancer avec sortie visible
python app_flask.py
```

---

## ✅ Résumé

**Lancer:** `python app_flask.py`
**Arrêter:** `Ctrl+C` ou `Get-Process python | Stop-Process -Force`
**URL:** http://localhost:5000

**C'est tout ! 🎯**
