# Problème Python 3.14 + Streamlit

## 🔴 PROBLÈME MAJEUR IDENTIFIÉ

**Streamlit ne fonctionne PAS avec Python 3.14 !**

### Erreur
```
OSError: [WinError -2147217358] Windows Error 0x80041032
KeyboardInterrupt
```

**Cause:** Python 3.14 est trop récent, Streamlit n'est pas compatible.

---

## ✅ SOLUTIONS

### Solution 1: Installer Python 3.11 (Recommandé)

1. **Télécharger Python 3.11:**
   - Aller sur https://www.python.org/downloads/
   - Télécharger Python 3.11.x (dernière version 3.11)

2. **Installer:**
   - Cocher "Add Python to PATH"
   - Installer

3. **Réinstaller Streamlit:**
   ```cmd
   python -m pip install streamlit
   ```

---

### Solution 2: Utiliser un Environnement Virtuel avec Python 3.11

Si vous ne voulez pas désinstaller Python 3.14:

```cmd
cd "C:\Users\Benar\OneDrive\Documents\test bet"

REM Créer environnement avec Python 3.11 (si installé)
py -3.11 -m venv venv_py311

REM Activer
venv_py311\Scripts\activate

REM Installer dépendances
pip install streamlit pandas python-dotenv requests pydantic

REM Lancer dashboard
streamlit run dashboard_fixed.py
```

---

### Solution 3: Downgrader Streamlit (Peut ne pas fonctionner)

Essayer une version plus ancienne de Streamlit:

```cmd
python -m pip install streamlit==1.28.0
```

---

## 📊 Versions Compatibles

### ✅ Fonctionne
- Python 3.9 + Streamlit 1.x
- Python 3.10 + Streamlit 1.x
- Python 3.11 + Streamlit 1.x

### ❌ Ne Fonctionne PAS
- Python 3.14 + Streamlit (toutes versions)
- Python 3.13 + Streamlit (problèmes connus)

---

## 🎯 Recommandation

**Installer Python 3.11 en parallèle de Python 3.14**

### Étapes:

1. **Télécharger Python 3.11.9:**
   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

2. **Installer:**
   - Cocher "Add Python 3.11 to PATH"
   - Choisir "Customize installation"
   - Installer dans `C:\Python311`

3. **Vérifier:**
   ```cmd
   C:\Python311\python.exe --version
   ```

4. **Installer Streamlit:**
   ```cmd
   C:\Python311\python.exe -m pip install streamlit pandas python-dotenv requests pydantic
   ```

5. **Lancer Dashboard:**
   ```cmd
   C:\Python311\python.exe -m streamlit run dashboard_fixed.py
   ```

---

## 📝 Script Automatique

Créer `LANCER_AVEC_PYTHON311.bat`:

```batch
@echo off
title Dashboard avec Python 3.11
cls

echo Lancement avec Python 3.11...
C:\Python311\python.exe -m streamlit run dashboard_fixed.py

pause
```

---

## ⚠️ Pourquoi Python 3.14 ?

Python 3.14 est une version très récente (peut-être même alpha/beta).

**Problèmes connus:**
- Beaucoup de packages ne sont pas compatibles
- Streamlit ne supporte pas encore
- Pandas peut avoir des problèmes
- Pydantic peut avoir des problèmes

**Recommandation:** Utiliser Python 3.11 pour le développement.

---

## 🔧 Alternative: Utiliser le Backend Sans Streamlit

Le backend fonctionne parfaitement ! On peut créer une interface alternative:

### Option 1: Script Python Simple

```python
# test_backend.py
from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

manager = DataSourceManager()
scanner = SmartScanner(
    provider=manager.provider,
    is_real_data=manager.is_real_data,
    max_analysis=10
)

result = scanner.scan_today()

print(f"Total matches: {result['total_matches']}")
print(f"Target matches: {result['target_count']}")
print(f"Analyzed: {result['analyzed_count']}")

for match in result['analyzed_matches'][:5]:
    print(f"\n{match['match_data']['home_team']} vs {match['match_data']['away_team']}")
    print(f"  Country: {match['match_data']['country']}")
    print(f"  Target Score: {match['profile']['target_score']}")
```

Lancer avec:
```cmd
python test_backend.py
```

---

## ✅ Résumé

**Problème:** Python 3.14 incompatible avec Streamlit
**Solution:** Installer Python 3.11

**Actions:**
1. Télécharger Python 3.11.9
2. Installer dans C:\Python311
3. `C:\Python311\python.exe -m pip install streamlit`
4. `C:\Python311\python.exe -m streamlit run dashboard_fixed.py`

**Le backend fonctionne ! C'est juste Streamlit qui ne supporte pas Python 3.14. 🎯**
