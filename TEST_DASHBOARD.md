# Guide de Test - Dashboard Intelligence

## 🧪 TESTS À EFFECTUER

### Test 1: Vérifier Flask
```bash
# Flask doit tourner
# Vérifier dans terminal: "Running on http://127.0.0.1:5000"
```

**✅ Attendu:**
```
============================================================
 DASHBOARD FLASK
============================================================

Dashboard URL: http://localhost:5000

 * Running on http://127.0.0.1:5000
 * Debugger is active!
```

---

### Test 2: Ouvrir Dashboard

**URL:** http://localhost:5000/

**✅ Attendu:**
- Page charge en 1-2 secondes
- Header violet visible
- "🎯 Betting Intelligence Dashboard"
- Stats header: Opportunities, Analyzed, Live

**❌ Si problème:**
- Page blanche → Vérifier console (F12)
- Chargement infini → Vérifier Network (F12)
- Erreur 500 → Vérifier logs Flask

---

### Test 3: Console Browser (F12)

**Ouvrir:** F12 → Console

**✅ Attendu:**
```javascript
[DATA] Loaded: {success: true, provider: "API-Football", ...}
```

**Vérifier:**
- Pas d'erreur rouge
- `data.categories` existe
- `allMatches` array rempli

**❌ Si erreur:**
```javascript
// Erreur commune:
Cannot read property 'length' of undefined
→ Structure données incorrecte

fetch failed
→ API ne répond pas

Unexpected token < in JSON
→ Flask retourne HTML au lieu de JSON
```

---

### Test 4: Network (F12 → Network)

**Vérifier requête:**
```
GET /api/data
Status: 200 OK
Type: xhr
Size: ~XX KB
```

**Cliquer sur requête → Preview:**
```json
{
  "success": true,
  "provider": "API-Football",
  "is_real_data": true,
  "categories": {
    "upcoming_pending": [...],
    "upcoming_inefficiencies": [...],
    "live": [...]
  },
  "diagnostic": {
    "analyzed": 0,
    "awaiting_user_action": 10
  }
}
```

**✅ Attendu:**
- `success: true`
- `categories` object présent
- Arrays non vides (si matchs disponibles)

---

### Test 5: Affichage Matches

**✅ Attendu:**

**Si matchs disponibles:**
```
🇬🇧 England · Premier League
Manchester United vs Liverpool
⏰ 18:00

[📊 Analyze Match]
```

**Si aucun match:**
```
📭
No opportunities found
Try adjusting your filters or refresh the data
```

**Vérifier:**
- Cards bien formatées
- Country flag visible
- Teams names corrects
- Kickoff time affiché
- Badge status (⏰ UPCOMING ou 🔴 LIVE)

---

### Test 6: Filtres

**Tester:**
1. Cliquer dropdown "League"
2. Sélectionner une league
3. Matches filtrés

**✅ Attendu:**
- Dropdown rempli avec leagues
- Filtrage fonctionne
- "No opportunities found" si aucun match

**Tester aussi:**
- Country filter
- Confidence filter (95%+, 85%+, 75%+)

---

### Test 7: Analyze Match

**Cliquer "📊 Analyze Match":**

**✅ Attendu:**
1. Bouton → "⏳ Analyzing..."
2. Attente 2-5 secondes
3. Card se transforme:

```
🔥 BEST BET
HT UNDER 1.5

Confidence: 80%
Fair Odd: 1.25
Sample: 20

WHY DETECTED:
• Signal type: HT_UNDER
• Confidence: 80%
• Strength: STRONG

[📊 Quick View] [🔬 Deep Analysis]
```

**Console doit afficher:**
```javascript
[ANALYZE] Button clicked for match: {...}
[ANALYZE] Request data: {...}
[ANALYZE] Calling /api/analyze_match...
[ANALYZE] HTTP status: 200
[ANALYZE] Response: {...}
[ANALYZE] Analysis complete!
  - Status: ANALYZABLE_NO_ODDS
  - Data origin: REAL
  - Home history: 2
  - Away history: 1
  - HT rows: 4
  - FT rows: 10
  - Signals: 2
```

**❌ Si erreur:**
```javascript
Analysis failed: DATA_INSUFFICIENT
→ Pas assez d'historique

Analysis failed: Unknown error
→ Vérifier logs Flask
```

---

### Test 8: Quick View Modal

**Après analyze, cliquer "📊 Quick View":**

**✅ Attendu:**
- Modal s'ouvre
- Titre: "Team A vs Team B"
- Section "🔥 Top Signals"
- 2-3 signals affichés
- Key Stats (Avg Goals, Avg HT Goals, Max, Sample)
- Last 5 Matches visuellement

**Vérifier:**
- Confidence colorée (vert/jaune/rouge)
- Stats numériques correctes
- Bouton × ferme modal
- Click background ferme modal

---

### Test 9: Deep Analysis Modal

**Cliquer "🔬 Deep Analysis":**

**✅ Attendu:**
- Modal s'ouvre
- Section "🔥 Best Opportunities" OUVERTE
- Autres sections REPLIÉES:
  - 📊 HT Analysis
  - 📊 FT Analysis
  - 🔧 Debug Data

**Tester accordions:**
1. Cliquer "📊 HT Analysis"
2. Section se déplie
3. Table visible (U0.5, U1.5, U2.5, U3.5)
4. Re-cliquer → Section se replie

**Vérifier tables:**
- Colonnes: Line, Hit Rate, Fair Odd, Sample
- Données numériques correctes
- Hit rate en %
- Fair odd en décimal

---

### Test 10: Responsive Mobile

**Tester:**
1. F12 → Toggle device toolbar
2. Sélectionner iPhone/iPad
3. Vérifier affichage

**✅ Attendu:**
- Cards s'adaptent
- Grids → 1 colonne
- Modals plein écran
- Boutons touch-friendly
- Pas de scroll horizontal

---

### Test 11: Refresh Data

**Cliquer "🔄 Refresh":**

**✅ Attendu:**
1. Loading spinner
2. "Refreshing data..."
3. Données rechargées
4. Matches mis à jour

**Console:**
```javascript
[DATA] Loaded: {...}
```

---

### Test 12: Multiple Analyses

**Analyser 3-4 matchs différents:**

**✅ Attendu:**
- Chaque match analysé indépendamment
- Cards se transforment
- analyzedMatches Map stocke résultats
- Quick View/Deep Analysis fonctionnent pour tous

---

### Test 13: Performance

**Vérifier:**
- Chargement initial < 3 secondes
- Analyze match < 10 secondes
- Modal open/close instantané
- Filtres réactifs
- Pas de freeze UI

**Console Performance:**
```javascript
// Pas de warning:
- [Violation] Long task
- Memory leak
- Too many re-renders
```

---

### Test 14: Logs Flask

**Terminal Flask doit afficher:**

```
[INFO] Scan result keys: dict_keys([...])
[INFO] Total matches: 10
[INFO] Analyzed matches: 0

[HISTORY] Fetching team history
[HISTORY] team_id=12345
[HISTORY] Strategy 'team+last+season' returned 2 fixtures

[ANALYSIS] History counts: home=2, away=1
[ANALYSIS] HT rows calculated: 4
[ANALYSIS] FT rows calculated: 10
[ANALYSIS] Signals generated: 2
[ANALYSIS] Status: ANALYZABLE_NO_ODDS
```

---

## 🐛 TROUBLESHOOTING

### Problème: Chargement Infini

**Vérifier:**
1. Console → Erreur JavaScript?
2. Network → `/api/data` retourne 200?
3. Response → Structure correcte?

**Solution:**
```javascript
// Vérifier dans console:
fetch('/api/data')
  .then(r => r.json())
  .then(d => console.log(d))
```

### Problème: Pas de Matches

**Causes possibles:**
1. Aucun match aujourd'hui
2. Tous filtrés
3. API-Football limite atteinte

**Vérifier:**
```bash
# Test API directement
curl http://localhost:5000/api/data
```

### Problème: Analyze Échoue

**Vérifier:**
1. Logs Flask → Erreur?
2. Console → Response?
3. Network → Status code?

**Causes communes:**
- DATA_INSUFFICIENT (pas assez d'historique)
- API rate limit
- Parsing error

### Problème: Modal Ne S'ouvre Pas

**Vérifier:**
1. Console → Erreur?
2. `analyzedMatches.get(matchId)` retourne data?
3. Modal HTML présent?

**Debug:**
```javascript
// Dans console:
console.log(analyzedMatches)
console.log(allMatches)
```

---

## ✅ CHECKLIST COMPLÈTE

### Affichage
- [ ] Dashboard charge
- [ ] Header stats affichées
- [ ] Matches cards visibles
- [ ] Filtres remplis
- [ ] Badges status corrects
- [ ] Country flags affichés

### Fonctionnalités
- [ ] Analyze Match fonctionne
- [ ] Quick View s'ouvre
- [ ] Deep Analysis s'ouvre
- [ ] Accordions fonctionnent
- [ ] Modals se ferment
- [ ] Filtres filtrent
- [ ] Refresh recharge

### Performance
- [ ] Chargement < 3s
- [ ] Analyze < 10s
- [ ] UI réactive
- [ ] Pas de freeze
- [ ] Pas d'erreur console

### Design
- [ ] Cards bien formatées
- [ ] Confidence colors correctes
- [ ] Spacing cohérent
- [ ] Shadows visibles
- [ ] Hover effects fonctionnent
- [ ] Responsive mobile OK

### Backend
- [ ] Flask démarre
- [ ] API retourne JSON
- [ ] Logs corrects
- [ ] Pas d'exception
- [ ] Historique chargé
- [ ] Analyse fonctionne

---

## 🎯 VALIDATION FINALE

**Si TOUS les tests passent:**

✅ **Dashboard Intelligence est OPÉRATIONNEL**

**Vous pouvez maintenant:**
1. Analyser des matchs réels
2. Voir les best bets
3. Consulter les analyses détaillées
4. Prendre des décisions rapides

**Le système est PRÊT pour utilisation ! 🚀**

---

## 📝 NOTES

### Données Réelles
- API-Football V3
- Historique réel
- Scores HT/FT réels
- Fair odds calculées
- **0% mock data**

### Limitations Actuelles
- ❌ Odds bookmaker (tier supérieur requis)
- ❌ H2H parfois manquant (non bloquant)
- ✅ Tout le reste fonctionne

### Prochaines Améliorations
- Graphiques hit rate
- Historique analyses
- Dark mode
- Notifications
- Export PDF

---

**Bon test ! 🧪**
