# Dashboard V6 - Guide Complet

## ✅ Architecture 2 Phases Implémentée

### Problème Résolu

**Avant (V5):** Dashboard chargeait à l'infini en analysant tous les matchs
**Maintenant (V6):** Chargement ultra-rapide avec analyse à la demande

## Lancement

```powershell
streamlit run dashboard_v6.py
```

**URL:** http://localhost:8508

## Architecture

### PHASE 1: Lightweight Fetch (< 3 secondes)

**Au chargement:**
- ✅ Récupère tous les matchs du jour (1 requête API)
- ✅ Calcule target_score pour chaque match (0 requête)
- ✅ Détecte catégories (women/youth/lower/obscure)
- ✅ Trie par priorité
- ✅ Affiche liste complète

**Coût:** 1 requête API

### PHASE 2: On-Demand Analysis (sur clic)

**Quand l'utilisateur clique "Analyze":**
- ✅ Récupère historique home team (1 requête)
- ✅ Récupère historique away team (1 requête)
- ✅ Récupère H2H (1 requête)
- ✅ Calcule statistiques
- ✅ Détecte anomalies
- ✅ Cache le résultat

**Coût:** 3 requêtes API par match

## Interface

### Header

```
⚽ Market Scanner V6
Ultra-fast loading with on-demand analysis

🟢 REAL    ⚡ FAST
```

### Sidebar - API Status

```
📊 API Status

Quota Used: 7/100
Analyses Today: 2
Cached Analyses: 2

✅ Quota OK

Analyses remaining: 28/30
```

### KPI Cards

```
Total Matches: 116
Target Matches: 27
Countries: 33
Competitions: 44
Load Time: 1.2s
```

### Match List

Chaque match affiche:
- **Home vs Away**
- 📍 Country - Competition
- 🎯 Target Score (0-100)
- ⏰ Kickoff time
- Catégories (badges colorés)
- Bouton **🔍 Analyze** ou **📊 View**

### Filtres

- **Min Target Score:** Slider 0-100
- **Categories:** Multi-select (Lower, Obscure, Women, Youth, Reserve)
- **Sort by:** Target Score / Kickoff Time / Country

### Analyse (Expandable)

Quand un match est analysé:

```
📈 Analysis Results

Statistics                  Anomaly Detection
- Home avg goals: 0.8      - Detected: ✅ Yes
- Away avg conceded: 0.6   - Confidence: 0.72
- Data quality: 0.80       - Score: 72/100

Analysis time: 2.3s
API requests: 3
```

## Workflow Utilisateur

### Matin - Scouting Rapide

1. Ouvrir dashboard (chargement 1-2s)
2. Voir tous les matchs ciblés
3. Filtrer par score > 70
4. Noter les matchs intéressants

**Coût:** 1 requête API

### Après-midi - Analyse Sélective

1. Cliquer "Analyze" sur match intéressant
2. Attendre 2-3s
3. Voir analyse complète
4. Répéter pour 5-10 matchs

**Coût:** 3 requêtes × nombre de matchs

### Exemple Journée

```
Matin:
- Scan initial: 1 requête
- Identifier 10 matchs intéressants

Après-midi:
- Analyser 8 matchs: 24 requêtes

Total: 25/100 requêtes ✅
```

## Protection Quota

### Limites

- **Max analyses par session:** 30
- **Quota warning:** À 50/100 requêtes
- **Quota alert:** À 80/100 requêtes

### Messages

**< 50 requêtes:**
```
✅ Quota OK
```

**50-80 requêtes:**
```
⚠️ 50% quota used
```

**> 80 requêtes:**
```
⚠️ Quota almost exhausted!
```

**30 analyses atteintes:**
```
⛔ Analysis limit reached for this session
```

## Cache

### Analyses Cachées

Une fois qu'un match est analysé:
- ✅ Résultat stocké en session
- ✅ Bouton devient "📊 View"
- ✅ Pas de nouvelle requête API
- ✅ Affichage instantané

### Refresh

Cliquer "🔄 Refresh":
- Recharge les matchs (1 requête)
- Vide le cache d'analyses
- Reset compteurs

## Comparaison Versions

| Feature | V5 Full | V5 Lite | V6 |
|---------|---------|---------|-----|
| Chargement | 🐌 Infini | ⚡ 2s | ⚡ 2s |
| Matchs affichés | 5-10 | Tous | Tous |
| Analyse | Automatique | Aucune | À la demande |
| Quota initial | 100+ | 1 | 1 |
| Quota total | 100+ | 1 | 1-91 |
| Utilisable | ❌ Non | ✅ Scouting | ✅ Complet |

## Avantages V6

### Pour l'Utilisateur

- ✅ **Chargement instantané** (1-2s)
- ✅ **Tous les matchs visibles** immédiatement
- ✅ **Contrôle total** sur les analyses
- ✅ **Feedback clair** (quota, cache, temps)
- ✅ **Pas d'attente** inutile

### Pour l'API

- ✅ **Quota préservé** (1 requête au lieu de 100+)
- ✅ **Analyses ciblées** (seulement matchs intéressants)
- ✅ **Cache efficace** (pas de re-requêtes)
- ✅ **Limites claires** (max 30 analyses)

### Pour le Développement

- ✅ **Architecture claire** (2 phases séparées)
- ✅ **Code modulaire** (LightweightScanner + AnalysisLoader)
- ✅ **Facile à tester**
- ✅ **Facile à étendre**

## Fichiers Créés

```
✅ app/services/scanner/lightweight_scanner.py
   - LightweightMatchScanner
   - Fetch rapide sans analyse

✅ app/services/analysis/match_analysis_loader.py
   - MatchAnalysisLoader
   - Analyse à la demande

✅ dashboard_v6.py
   - Dashboard complet
   - UX optimisée
   - Protection quota
   - Cache session
```

## Debug

### Expander "Debug Info"

```json
{
  "scan_result": {
    "success": true,
    "total_matches": 116,
    "target_count": 27,
    "scan_duration": 1.2,
    "api_requests": 1
  },
  "session": {
    "analyses_cached": 2,
    "analyses_count": 2,
    "estimated_quota": 7
  }
}
```

## Recommandations

### Usage Quotidien

1. **Matin:** Scan rapide (1 requête)
2. **Sélection:** Identifier 10-15 matchs cibles
3. **Analyse:** Analyser 5-10 matchs (15-30 requêtes)
4. **Total:** 16-31 requêtes/jour ✅

### Optimisation

- Analyser seulement les matchs avec target_score > 70
- Utiliser filtres pour réduire la liste
- Profiter du cache (analyses déjà faites)
- Refresh seulement si nécessaire

### Limites à Respecter

- Max 30 analyses par session
- Max 100 requêtes par jour (API free tier)
- Recommandé: < 50 requêtes/jour pour marge

## Résumé

**Dashboard V6 est la version production-ready:**

✅ Chargement ultra-rapide (< 3s)
✅ Tous les matchs visibles immédiatement
✅ Analyse à la demande (contrôle utilisateur)
✅ Protection quota (limites claires)
✅ Cache efficace (pas de gaspillage)
✅ Feedback visible (quota, cache, temps)
✅ Architecture propre (2 phases séparées)

**Utilisable quotidiennement avec API-Football free tier ! 🚀**
