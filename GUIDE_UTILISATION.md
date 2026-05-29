# Guide d'Utilisation - Dashboard Final

## Démarrage

### 1. Lancer le Dashboard

```powershell
streamlit run dashboard.py
```

**URL:** http://localhost:8514 (ou port affiché)

---

## Interface

### Header

```
🎯 Bookmaker Inefficiency Detector
Detect pricing errors in bettable minor leagues

[🔄 Refresh]
```

### Data Freshness

```
✅ REAL DATA from api_football
📅 Today: 2026-05-28 12:56 Local
Mode: STATISTICAL_SIGNAL
```

### Stats

```
Total Matches: 116
Target Matches: 60
Deep Analyzed: 10
Scan Time: 0.8s
```

---

## Sidebar - Filtres et Paramètres

### ⚙️ Settings

#### Analysis Mode
```
☐ Odds Available
📊 STATISTICAL SIGNALS
⏳ Statistical signal mode - waiting for odds
```

**Utilisation:**
- Décoché: Mode STATISTICAL_SIGNALS (analyse sans odds)
- Coché: Mode INEFFICIENCY_DETECTION (comparaison avec odds)

#### Targeting
```
☐ Include Extreme Obscure
Max Deep Analysis: 10 (slider 5-20)
```

**Utilisation:**
- **Include Extreme Obscure:** Inclure Estonia/Georgia Liga 3 (déconseillé)
- **Max Deep Analysis:** Nombre de matchs à analyser en profondeur

### 🎯 Filters

#### Region Filter
```
☐ Europe East
☐ South America
☐ Asia
☐ Africa
☐ Women
☐ Youth
☐ Reserves
```

**Mapping:**
- **Europe East:** Kazakhstan, Bulgaria, Romania, Serbia, etc.
- **South America:** Brazil, Argentina, Colombia, Chile, etc.
- **Asia:** Vietnam, South Korea, Japan, China, etc.
- **Africa:** Egypt, Ethiopia, South Africa, etc.
- **Women:** Toutes ligues féminines
- **Youth:** Toutes ligues jeunes
- **Reserves:** Toutes équipes réserves

#### Country Filter
```
☐ Kazakhstan
☐ Vietnam
☐ Brazil
☐ Colombia
☐ Egypt
☐ Bulgaria
☐ Ethiopia
☐ South Korea
☐ Japan
☐ Argentina
```

**Utilisation:** Sélectionner pays spécifiques

#### League Type Filter
```
☐ Bettable Minor
☐ Extreme Obscure
☐ Women
☐ Youth
☐ Reserve
```

**Utilisation:**
- **Bettable Minor:** Ligues mineures avec bonne coverage bookmaker
- **Extreme Obscure:** Ligues ultra-obscures (faible coverage)
- **Women/Youth/Reserve:** Filtres spécifiques

#### Signal Type Filter
```
☐ EXTREME_UNDER
☐ HT_UNDER
☐ FT_UNDER
☐ LOW_VARIANCE
```

**Utilisation:** Filtrer par type de signal détecté

#### Confidence Filter
```
○ All
○ Medium+
○ High Only
```

**Utilisation:**
- **All:** Tous les matchs
- **Medium+:** Confidence ≥ 60%
- **High Only:** Confidence ≥ 80%

---

## Tabs

### Tab 1: 🎯 Analyzed Matches

**Contenu:** Matchs analysés en profondeur (top 10)

#### Exemple de Match

```
1. Kazakhstan U21 vs Uzbekistan U21
📍 Kazakhstan - Youth League
📊 80% Coverage (HIGH)
Score: 91/100

🎯 Detected Signals:

EXTREME_UNDER (STRONG)
Confidence: 80%
Max Goals: 5
Avg Goals: 3.1

[Expandable] 📋 EXTREME_UNDER Details
  Suggested Markets:
  - UNDER_5.5
  - UNDER_6.5
  - UNDER_7.5
  
  Quality Metrics:
  - Variance: 0.85
  - Stability: 0.85
  - Sample Size: 15
  - Data Quality: 0.94
  
  Reasons:
  - Extreme under profile detected
  - Average goals: 3.1
  - Historical max: 5

[Expandable] 📊 Historical Line Analysis
  Top Performing Lines:
  
  Under 5.5: 100% (15 under, 0 over)
  Under 6.5: 100% (15 under, 0 over)
  Under 4.5: 93% (14 under, 1 over)
  Under 3.5: 80% (12 under, 3 over)
  Under 2.5: 60% (9 under, 6 over)

[Expandable] 🎰 Bookmaker Coverage Estimate
  Coverage Score: 80/100
  Coverage Level: HIGH
  
  Likely Markets:
  - HT Under/Over
  - FT Under/Over
  - BTTS
  
  Reasoning:
  - Known high-coverage league
  - Kazakhstan has good bookmaker coverage
```

### Tab 2: 📋 Remaining Matches

**Contenu:** Matchs ciblés mais pas encore analysés

#### Exemple

```
11. FC Tallinn vs Maardu
📍 Estonia - Esiliiga A
📊 75% Coverage (MEDIUM)
Score: 85/100

💡 Increase 'Max Deep Analysis' to analyze this match
```

---

## Workflow Recommandé

### 1. Premier Scan

1. Lancer dashboard
2. Attendre scan (< 1 seconde)
3. Voir stats globales

### 2. Filtrage Initial

**Scénario A: Focus South America**
```
Sidebar → Region → ☑ South America
```

**Scénario B: Focus Women**
```
Sidebar → Region → ☑ Women
```

**Scénario C: Focus Kazakhstan + Vietnam**
```
Sidebar → Country → ☑ Kazakhstan, ☑ Vietnam
```

### 3. Analyse des Signaux

1. Aller dans tab "🎯 Analyzed Matches"
2. Pour chaque match:
   - Voir signal principal (EXTREME_UNDER, HT_UNDER, etc.)
   - Vérifier confidence (≥80% = fort)
   - Voir historical line analysis
   - Vérifier bookmaker coverage (HIGH = bon)

### 4. Sélection des Opportunités

**Critères:**
- ✅ Signal: EXTREME_UNDER ou HT_UNDER
- ✅ Confidence: ≥ 80%
- ✅ Hit rate: ≥ 90% sur ligne spécifique
- ✅ Coverage: HIGH (≥80%)
- ✅ Sample size: ≥ 10

**Exemple de bon match:**
```
Signal: EXTREME_UNDER (STRONG)
Confidence: 80%
Under 5.5: 100% (15/15)
Coverage: 80% (HIGH)
Sample: 15 matchs
→ ✅ OPPORTUNITÉ FORTE
```

### 5. Filtrage Avancé

**Pour signaux HT Under uniquement:**
```
Sidebar → Signal Type → ☑ HT_UNDER
Sidebar → Confidence → High Only
```

**Pour ligues bettables uniquement:**
```
Sidebar → League Type → ☑ Bettable Minor
```

### 6. Augmenter Analyse

Si besoin d'analyser plus de matchs:
```
Sidebar → Max Deep Analysis → 20
[Refresh]
```

---

## Interprétation des Résultats

### Bookmaker Coverage

**HIGH (80-100%):**
- ✅ Très bonne probabilité de trouver marchés
- ✅ Lignes élevées probablement disponibles
- ✅ HT markets probablement disponibles

**MEDIUM (50-80%):**
- ⚠️ Probabilité moyenne
- ⚠️ Certains bookmakers seulement
- ⚠️ Marchés basiques (FT Under/Over, BTTS)

**LOW (0-50%):**
- ❌ Faible probabilité
- ❌ Peu de bookmakers
- ❌ Marchés limités

### Signals

**EXTREME_UNDER:**
- Profil très défensif
- Avg goals très bas (< 3.5)
- Max goals observé bas
- Lignes élevées (5.5+) avec hit rate 100%

**HT_UNDER:**
- Première mi-temps défensive
- HT avg goals < 1.5
- HT Under 1.5 ou 2.5 fort

**FT_UNDER:**
- Match complet défensif
- FT Under 2.5 ou 3.5 fort

**LOW_VARIANCE:**
- Résultats très stables
- Peu de surprises
- Prédictibilité élevée

### Confidence

**≥ 80% (High):**
- ✅ Signal très fort
- ✅ Données de qualité
- ✅ Stabilité élevée
- ✅ Exploitable

**60-80% (Medium):**
- ⚠️ Signal moyen
- ⚠️ Vérifier sample size
- ⚠️ Vérifier variance

**< 60% (Low):**
- ❌ Signal faible
- ❌ Ne pas exploiter

---

## Cas d'Usage

### Cas 1: Trouver Meilleurs HT Under du Jour

```
1. Sidebar → Signal Type → ☑ HT_UNDER
2. Sidebar → Confidence → High Only
3. Tab "Analyzed Matches"
4. Trier par confidence
5. Vérifier coverage bookmaker
```

### Cas 2: Focus Women Leagues

```
1. Sidebar → Region → ☑ Women
2. Tab "Analyzed Matches"
3. Voir signaux détectés
4. Vérifier historical lines
```

### Cas 3: Focus Kazakhstan

```
1. Sidebar → Country → ☑ Kazakhstan
2. Tab "Analyzed Matches"
3. Analyser tous matchs Kazakhstan
```

### Cas 4: Extreme Under Profiles Only

```
1. Sidebar → Signal Type → ☑ EXTREME_UNDER
2. Sidebar → Confidence → High Only
3. Sidebar → League Type → ☑ Bettable Minor
4. Tab "Analyzed Matches"
```

---

## Troubleshooting

### Dashboard ne charge pas

```powershell
# Arrêter tous streamlit
Get-Process | Where-Object {$_.ProcessName -like "*streamlit*"} | Stop-Process -Force

# Relancer
streamlit run dashboard.py
```

### Pas de matchs analysés

**Cause:** Max Deep Analysis trop bas

**Solution:**
```
Sidebar → Max Deep Analysis → 20
[Refresh]
```

### Filtres ne fonctionnent pas

**Solution:**
```
[Refresh] button
```

### Erreur "module not found"

**Solution:**
```powershell
pip install -r requirements.txt
```

---

## Performance

### Temps de Scan

**Normal:** < 1 seconde
**Lent:** 2-3 secondes (si API lente)
**Très lent:** > 5 secondes (problème réseau)

### Nombre de Matchs

**Total:** ~100-150 matchs/jour
**Target:** ~50-70 matchs (après filtering)
**Analyzed:** 10-20 matchs (configurable)

---

## Prochaines Étapes

### Quand Odds Disponibles

1. Activer "Odds Available" dans sidebar
2. Mode passe à INEFFICIENCY_DETECTION
3. Dashboard compare odds vs historical
4. Affiche divergences et edge

### Export Résultats

**Futur:** Export CSV des opportunités détectées

---

## Résumé

**Dashboard Final:**
- ✅ UN SEUL fichier: `dashboard.py`
- ✅ Toutes phases 1-9 intégrées
- ✅ Filtres complets (région, pays, league type, signal, confidence)
- ✅ Priorisation intelligente (bettable + women + youth)
- ✅ Analyses visibles (signals + line breach + coverage)
- ✅ Production-ready

**Commande:**
```powershell
streamlit run dashboard.py
```

**Le système détecte des opportunités exploitables ! 🎯**
