# Dashboard V7 - Bookmaker Inefficiency Detector

## ✅ Deux Modes Clairement Séparés

### Mode 1: Statistical Signals 📊
**Sans odds - Toujours disponible**

### Mode 2: Bookmaker Inefficiencies ⚠️
**Avec odds - Détection active**

## Lancement

```powershell
streamlit run dashboard_v7.py
```

**URL:** http://localhost:8509

## Interface

### Header

```
⚠️ Bookmaker Inefficiency Detector
Detect pricing errors in obscure leagues
```

### Sidebar - Mode Selector

```
🎯 Analysis Mode

☐ Odds Available

📊 STATISTICAL SIGNALS
⏳ Statistical signal mode - waiting for odds
```

**Cocher "Odds Available"** pour activer le mode Inefficiency Detection.

## Mode 1: Statistical Signals (Sans Odds)

### Affichage

Chaque signal montre:

```
┌─────────────────────────────────────────────┐
│ Kazakhstan U21 vs Uzbekistan U21            │
│ 📍 Kazakhstan - Youth League                │
│                                              │
│ Signal: EXTREME_UNDER                        │
│ Strength: STRONG                             │
│                                              │
│ ⏳ WAITING ODDS                              │
│                                              │
│ Max Goals: 5  │ Average: 3.1                │
│ Variance: 0.85 │ Stability: 0.85            │
│                                              │
│ 📋 Suggested Markets & Hit Rates            │
│   Suggested Markets:                         │
│   - UNDER_5.5                                │
│   - UNDER_6.5                                │
│   - UNDER_7.5                                │
│                                              │
│   Historical Hit Rates:                      │
│   - Under 5.5: 100% (15 matches)            │
│   - Under 6.5: 100% (15 matches)            │
│   - Under 7.5: 100% (15 matches)            │
│                                              │
│   Reasons:                                   │
│   - Extreme under profile detected           │
│   - Average goals: 3.1                       │
│   - Historical max: 5                        │
│   - Low variance: 0.85                       │
└─────────────────────────────────────────────┘
```

### Informations Affichées

**Header:**
- Match (home vs away)
- Pays & compétition
- Type de signal
- Force du signal (WEAK/MODERATE/STRONG/EXTREME)
- Badge "⏳ WAITING ODDS"

**Métriques:**
- Max Goals (historique)
- Average (moyenne)
- Variance Score (0-1)
- Stability Score (0-1)

**Détails (Expandable):**
- Suggested Markets
- Historical Hit Rates par ligne
- Reasons (pourquoi ce signal)
- Data Quality & Sample Size

### Message Important

```
💡 Enable 'Odds Available' in sidebar to activate Inefficiency Detection mode
```

## Mode 2: Bookmaker Inefficiencies (Avec Odds)

### Activation

1. Cocher "Odds Available" dans sidebar
2. Le mode change automatiquement
3. Deux tabs apparaissent:
   - 📊 Statistical Signals
   - ⚠️ Bookmaker Inefficiencies

### Tab: Bookmaker Inefficiencies

Chaque inefficiency montre:

```
┌─────────────────────────────────────────────┐
│ Kazakhstan U21 vs Uzbekistan U21            │
│ 📍 Kazakhstan - Youth League                │
│                                              │
│ Market: FT Under                             │
│ Line: Under 12.5                             │
│                                              │
│ ⚠️ STRONG                                    │
│                                              │
│ Bookmaker: Bet365 | Odd: 1.85               │
│                                              │
│ Divergence: 78/100                           │
│ Edge: 32/100                                 │
│ Risk: 15/100                                 │
│ Confidence: MEDIUM                           │
│ Action: COMPARE_ODDS                         │
│                                              │
│ Historical Reality:                          │
│ - Max goals: 5                               │
│ - Average: 3.1                               │
│ - Sample size: 15                            │
│ - Historical probability: 100%               │
│                                              │
│ Bookmaker:                                   │
│ - Line: Under 12.5                           │
│ - Odd: 1.85                                  │
│ - Implied probability: 54%                   │
│ - Gap: 7.5 goals                             │
│                                              │
│ 🔍 Why This Is Inefficient                  │
│   ⚠️ Line 7.5 goals above historical max    │
│   ⚠️ Historical probability 100% vs 54%     │
│   ⚠️ Line 9.4 goals above average           │
└─────────────────────────────────────────────┘
```

### Informations Affichées

**Header:**
- Match
- Pays & compétition
- Market type
- Bookmaker line
- Inefficiency level (MEDIUM/STRONG/EXTREME)

**Bookmaker Info:**
- Bookmaker name
- Odd

**Métriques:**
- Divergence Score (0-100)
- Edge Score (0-100)
- Risk Score (0-100)
- Confidence (LOW/MEDIUM/HIGH)
- Recommended Action

**Comparaison:**
- **Historical Reality:**
  - Max goals
  - Average
  - Sample size
  - Historical probability
  
- **Bookmaker:**
  - Line
  - Odd
  - Implied probability
  - Gap (goals)

**Explication:**
- Why This Is Inefficient (liste des raisons)
- Risk Factors (si présents)

## Workflow Utilisateur

### Phase 1: Scouting (Sans Odds)

1. Lancer dashboard
2. Voir Statistical Signals
3. Identifier profils forts:
   - EXTREME_UNDER
   - HT_UNDER
   - LOW_VARIANCE
4. Noter suggested markets
5. Noter hit rates historiques

**Exemple:**
```
Signal: EXTREME_UNDER
Suggested: UNDER_5.5, UNDER_6.5, UNDER_7.5
Hit rates: 100% sur toutes ces lignes
Status: ⏳ WAITING ODDS
```

### Phase 2: Inefficiency Detection (Avec Odds)

1. Obtenir odds bookmaker
2. Cocher "Odds Available"
3. Aller dans tab "Bookmaker Inefficiencies"
4. Voir divergences détectées:
   - Divergence score
   - Edge estimate
   - Recommended action

**Exemple:**
```
Bookmaker: Under 12.5 @ 1.85
Historical Max: 5 goals
Gap: 7.5 goals
Divergence: 78/100
Action: COMPARE_ODDS
```

## Niveaux d'Inefficiency

### EXTREME ⚠️⚠️⚠️
```
Divergence >= 80
Edge >= 40
Confidence = HIGH
```
**Action:** VALIDATE (vérifier plusieurs bookmakers)

### STRONG ⚠️⚠️
```
Divergence >= 60
Edge >= 30
```
**Action:** COMPARE_ODDS (comparer avec autres bookmakers)

### MEDIUM ⚠️
```
Divergence >= 40
Edge >= 20
```
**Action:** WATCH (surveiller)

### WEAK
```
Divergence < 40
```
**Action:** IGNORE

## Différences Clés

### Sans Odds (Mode 1)

```
✅ Affiche: "Statistical Signal"
✅ Badge: "⏳ WAITING ODDS"
✅ Montre: Hit rates historiques
✅ Suggère: Markets à surveiller
❌ Pas de: Divergence bookmaker
❌ Pas de: Edge calculation
❌ Pas de: "Bet" ou "Inefficiency"
```

### Avec Odds (Mode 2)

```
✅ Affiche: "Bookmaker Inefficiency"
✅ Badge: "⚠️ STRONG/EXTREME"
✅ Montre: Divergence vs bookmaker
✅ Calcule: Edge estimate
✅ Compare: Historical vs Bookmaker probability
✅ Recommande: Action (VALIDATE/COMPARE/WATCH)
```

## KPIs Dashboard

```
Total Matches: 116
Target Matches: 27
Countries: 33
Mode: STATISTICAL_SIGNAL
```

Ou avec odds:

```
Total Matches: 116
Target Matches: 27
Countries: 33
Mode: INEFFICIENCY_DETECTION
```

## Exemple Complet

### Scénario: Kazakhstan U21 vs Uzbekistan U21

**Mode 1 (Sans Odds):**
```
📊 Statistical Signal Detected

Signal: EXTREME_UNDER
Strength: STRONG
Confidence: 0.80

Max Goals: 5
Average: 3.1
Variance: 0.85 (low)
Stability: 0.85 (high)

Suggested Markets:
- UNDER_5.5 (100% hit rate)
- UNDER_6.5 (100% hit rate)
- UNDER_7.5 (100% hit rate)

Status: ⏳ WAITING FOR ODDS
```

**Mode 2 (Avec Odds):**
```
⚠️ Bookmaker Inefficiency Detected

Market: Under 12.5 @ 1.85
Bookmaker: Bet365

Divergence: 78/100
Edge: 32/100
Risk: 15/100
Confidence: MEDIUM
Action: COMPARE_ODDS

Why Inefficient:
- Line 7.5 goals above historical max (5)
- Historical probability 100% vs bookmaker 54%
- Line 9.4 goals above average (3.1)

Historical Reality:
- 15 matches analyzed
- Max ever: 5 goals
- Average: 3.1 goals
- Under 5.5: 100% hit rate

Bookmaker Line:
- Under 12.5
- Implies only 54% probability
- Gap of 7.5 goals from historical max
```

## Résumé

**Dashboard V7 Features:**

✅ Deux modes clairement séparés
✅ Mode 1: Statistical Signals (sans odds)
✅ Mode 2: Bookmaker Inefficiencies (avec odds)
✅ Pas de "bet" sans odds
✅ Affichage "signal" vs "inefficiency"
✅ Hit rates historiques
✅ Divergence bookmaker
✅ Edge calculation
✅ Recommended actions
✅ Explications claires

**Le dashboard distingue clairement recherche statistique et détection d'inefficiencies ! 🎯**
