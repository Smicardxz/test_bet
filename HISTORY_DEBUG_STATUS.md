# History Debug Status - PHASES 1-3 Complètes

## ✅ Implémenté

### PHASE 1 — Debug Logs ✅
**Fichier:** `app/providers/api_football_provider.py`

**Ajouté dans `get_team_recent_matches`:**
- ✅ Log team_id, limit, before_date
- ✅ Log season utilisée
- ✅ Log endpoint et params
- ✅ Log HTTP status
- ✅ Log raw_fixtures_count
- ✅ Log samples (fixture_id, date, status, score)
- ✅ Log filtering results:
  - rejected_not_finished
  - rejected_missing_score
  - rejected_date_filter
  - rejected_parsing
  - accepted count

**Ajouté dans `get_head_to_head`:**
- ✅ Log home_team_id, away_team_id
- ✅ Log h2h_string
- ✅ Log endpoint et params
- ✅ Log raw_count
- ✅ Log filtering results

### PHASE 5 — H2H Logs ✅
Même niveau de détail que team history

### PHASE 10 — Script Debug ✅
**Fichier:** `scripts/debug_team_history.py`

**Fonctionnalités:**
- ✅ Prend fixture_id en argument
- ✅ Charge le fixture depuis today's matches
- ✅ Affiche IDs (fixture, teams, league, season)
- ✅ Teste home team history
- ✅ Teste away team history
- ✅ Teste H2H
- ✅ Affiche summary avec counts
- ✅ Affiche raisons si échec

**Usage:**
```bash
python scripts/debug_team_history.py --fixture_id 1527983
```

---

## 🔍 Découvertes

### Test Match: Kaisar vs Yelimay Semey (1527983)

**Fixture Info:**
- fixture_id: 1527983
- home_team_id: 4562 (Kaisar)
- away_team_id: 21011 (Yelimay Semey)
- league_id: 389 (Premier League Kazakhstan)
- Competition: Premier League (Kazakhstan)
- Date: 2026-05-28 14:00:00+00:00

**Résultat:**
- ❌ Home history: 0 matches
- ❌ Away history: 0 matches
- ❌ H2H: 0 matches

**Conclusion:**
L'API ne retourne AUCUN historique pour ces équipes.

---

## 🎯 Problème Identifié

### Cause Probable: API Free Tier Limitations

L'API-Football Free Tier a des limitations:
1. **Pas d'accès à toutes les ligues**
2. **Historique limité pour certaines compétitions**
3. **Kazakhstan Premier League** peut ne pas être dans le free tier

### Vérification Nécessaire

**PHASE 2 à implémenter:**
Tester plusieurs stratégies de récupération:

**A. Sans filtrage status=FT**
```python
params = {
    "team": team_id,
    "last": limit,
    "season": current_year
    # Pas de status=FT
}
```

**B. Sans season**
```python
params = {
    "team": team_id,
    "last": limit,
    "status": "FT"
    # Pas de season
}
```

**C. Juste team + last**
```python
params = {
    "team": team_id,
    "last": limit
}
```

**D. Via league + season**
```python
# Récupérer tous les matchs de la league
params = {
    "league": league_id,
    "season": season,
    "team": team_id
}
```

---

## 📋 Prochaines Étapes

### PHASE 2 — Stratégies Multiples ⏳

**Modifier `get_team_recent_matches` pour:**
1. Essayer stratégie 1: team + last + status + season
2. Si 0 résultats → stratégie 2: team + last + season
3. Si 0 résultats → stratégie 3: team + last
4. Si 0 résultats → stratégie 4: league + season + team
5. Retourner quelle stratégie a fonctionné

**Ajouter:**
```python
history_fetch_strategy_used: str  # Dans le retour
```

### PHASE 3 — Vérifier Team IDs ⏳

**Pour le match analysé, vérifier:**
- ✅ home_team_id: 4562 (confirmé)
- ✅ away_team_id: 21011 (confirmé)
- ✅ league_id: 389 (confirmé)
- ❓ season: ? (non retourné par API)

**Action:**
Vérifier si `season` est bien extrait du fixture

### PHASE 4 — Filtrage ⏳

**Actuellement:**
- Filtre status=FT ✅
- Filtre missing score ✅
- Filtre date ✅

**À vérifier:**
Si raw_fixtures_count > 0 mais accepted = 0:
- Afficher exactement pourquoi chaque match est rejeté

### PHASE 6 — Odds Non Bloquant ⏳

**Modifier smart_scanner.py:**
```python
if not odds:
    warnings.append("odds_not_available")
    # Continuer l'analyse quand même
    
if history OK:
    return {
        "status": "ANALYZED_WITHOUT_ODDS",
        "ht_analysis": {...},
        "ft_analysis": {...},
        "warnings": warnings
    }
```

---

## 🧪 Tests à Effectuer

### Test 1: Match avec Historique Connu

Tester avec une ligue majeure (Premier League, La Liga, etc.):
```bash
# Trouver un match EPL
python scripts/debug_team_history.py --fixture_id XXXXX
```

**Attendu:**
- home_history_count > 0
- away_history_count > 0

### Test 2: Stratégies Multiples

Après implémentation PHASE 2:
```bash
python scripts/debug_team_history.py --fixture_id 1527983
```

**Attendu:**
- Logs montrant chaque stratégie essayée
- Quelle stratégie a retourné des résultats
- Si aucune: confirmation que league non supportée

### Test 3: Analyse Complète

Après PHASE 6:
```bash
# Via dashboard ou endpoint
POST /api/analyze_match
{
    "fixture_id": "XXXXX",  # Match avec historique
    ...
}
```

**Attendu:**
```json
{
    "success": true,
    "analysis_status": "ANALYZED_WITHOUT_ODDS",
    "data_origin": "REAL",
    "home_history_count": 10,
    "away_history_count": 10,
    "ht_analysis": {...},
    "ft_analysis": {...},
    "warnings": ["odds_not_available"]
}
```

---

## 📊 État Actuel

**✅ Complété:**
- PHASE 1: Debug logs historique
- PHASE 5: Debug logs H2H
- PHASE 10: Script debug

**⏳ En Attente:**
- PHASE 2: Stratégies multiples
- PHASE 3: Vérification team IDs (partiellement fait)
- PHASE 4: Filtrage détaillé
- PHASE 6: Odds non bloquant
- PHASE 7-9: Dashboard UI
- PHASE 11: Condition de succès

**🎯 Objectif Immédiat:**

Implémenter PHASE 2 (stratégies multiples) pour voir si on peut récupérer l'historique avec d'autres paramètres API.

**Alternative:**

Si Kazakhstan Premier League n'est pas supportée en free tier:
- Tester avec une ligue majeure (EPL, La Liga)
- Confirmer que le pipeline fonctionne
- Documenter les ligues supportées

---

## 🔧 Commandes Utiles

**Debug historique:**
```bash
python scripts/debug_team_history.py --fixture_id FIXTURE_ID
```

**Test endpoint analyze:**
```bash
python scripts/test_analyze_endpoint.py
```

**Test API data:**
```bash
python scripts/test_api_data.py
```

**Logs Flask:**
Chercher `[HISTORY]` et `[H2H]` dans le terminal

---

**Prochaine action: Implémenter PHASE 2 (stratégies multiples) pour maximiser les chances de récupérer l'historique. 🎯**
