# Architecture 2 Phases - Implémentation Complète

## Problème Résolu

**Avant:** Dashboard chargeait à l'infini en analysant tous les matchs
**Maintenant:** Chargement ultra-rapide avec analyse à la demande

## Architecture

### PHASE 1: Lightweight Fetch (< 3 secondes)

**Fichier:** `app/services/scanner/lightweight_scanner.py`

**Ce qui est fait:**
- ✅ Récupère matchs du jour (1 requête API)
- ✅ Calcule target_score (0 requête)
- ✅ Détecte catégories (women/youth/lower/obscure)
- ✅ Trie par priorité

**Ce qui N'est PAS fait:**
- ❌ Historique équipes
- ❌ H2H
- ❌ Analyse statistique
- ❌ Anomaly detection

**Coût API:** 1 requête

### PHASE 2: On-Demand Analysis (sur clic utilisateur)

**Fichier:** `app/services/analysis/match_analysis_loader.py`

**Ce qui est fait:**
- ✅ Historique home team (1 requête)
- ✅ Historique away team (1 requête)
- ✅ H2H (1 requête)
- ✅ Calcul stats
- ✅ Anomaly detection

**Coût API:** 3 requêtes par match analysé

## Utilisation

### Dashboard V5 Lite (Actuel - Rapide)

```powershell
streamlit run dashboard_v5_lite.py
```

**Caractéristiques:**
- Utilise `LightweightMatchScanner`
- Chargement: 1-2 secondes
- Affiche tous les matchs
- Pas d'analyse approfondie
- Coût: 1 requête API

### Dashboard V6 (À créer - Complet)

```powershell
streamlit run dashboard_v6.py
```

**Caractéristiques:**
- Page 1: Liste rapide (LightweightMatchScanner)
- Page 2: Détail match (MatchAnalysisLoader)
- Analyse à la demande
- Bouton "Analyze" sur chaque match
- Coût: 1 + (3 × nombre de matchs analysés)

## Fichiers Créés

```
✅ app/services/scanner/lightweight_scanner.py
   - LightweightMatchScanner
   - Fetch rapide sans analyse

✅ app/services/analysis/match_analysis_loader.py
   - MatchAnalysisLoader
   - Analyse à la demande
   - Estimation coût API
```

## Prochaines Étapes

### 1. ApiQuotaManager (Protection)

```python
class ApiQuotaManager:
    MAX_ANALYSES_PER_SESSION = 10
    QUOTA_WARNING_THRESHOLD = 80  # 80/100 requests
    
    def can_analyze(self) -> bool:
        """Check if analysis allowed"""
        
    def estimate_cost(self, action: str) -> int:
        """Estimate API cost"""
        
    def track_usage(self, requests: int):
        """Track API usage"""
```

### 2. Cache Agressif

```python
# TTL Configuration
CACHE_TTL = {
    "fixtures": 3600,      # 1h
    "team_history": 86400, # 24h
    "h2h": 86400,          # 24h
    "analysis": "session"  # Session only
}
```

### 3. Dashboard V6 UX

**Page 1: Match List (Rapide)**
- Chargement instantané
- Liste tous les matchs
- Target score visible
- Bouton "Analyze" sur chaque match

**Page 2: Match Detail (À la demande)**
- Loader visible:
  - "Fetching home team history..."
  - "Fetching away team history..."
  - "Computing statistics..."
  - "Running anomaly detection..."
- Affiche analyse complète
- Cache l'analyse

### 4. Debug Visible

```python
# Sidebar
st.sidebar.metric("API Quota Used", "5/100")
st.sidebar.metric("Analyses Today", "3")
st.sidebar.metric("Cache Hit Rate", "75%")

# Warning
if quota > 80:
    st.warning("⚠️ API quota almost exhausted (85/100)")
```

## Workflow Utilisateur

### Matin - Scouting (Rapide)

1. Ouvrir dashboard
2. Voir liste complète (1-2s)
3. Identifier matchs intéressants
4. Noter les cibles

**Coût:** 1 requête API

### Après-midi - Analyse (Sélectif)

1. Cliquer "Analyze" sur match ciblé
2. Attendre 2-3s (loader visible)
3. Voir analyse complète
4. Répéter pour 5-10 matchs max

**Coût:** 3 requêtes × nombre de matchs

### Total Quotidien

- Scouting: 1 requête
- Analyse 10 matchs: 30 requêtes
- **Total: 31/100** ✅ Largement sous la limite

## Comparaison

| Version | Chargement | Analyse | Coût API | Usage |
|---------|------------|---------|----------|-------|
| V5 Full | 🐌 Infini | Tous | 100+ | ❌ Inutilisable |
| V5 Lite | ⚡ 2s | Aucune | 1 | ✅ Scouting |
| V6 (nouveau) | ⚡ 2s | À la demande | 1-31 | ✅ Complet |

## Implémentation V6

### Structure

```python
# dashboard_v6.py

# Page 1: Match List
def render_match_list():
    scanner = LightweightMatchScanner(provider)
    data = scanner.scan_today()  # 1 API request
    
    for match in data["target_matches"]:
        st.write(match["home_team"], "vs", match["away_team"])
        
        if st.button("Analyze", key=match["match_id"]):
            st.session_state.selected_match = match["match_id"]
            st.switch_page("pages/match_detail.py")

# Page 2: Match Detail
def render_match_detail():
    match_id = st.session_state.selected_match
    
    # Check cache
    if match_id in st.session_state.analyses:
        analysis = st.session_state.analyses[match_id]
    else:
        # Load analysis
        loader = MatchAnalysisLoader(provider)
        
        with st.spinner("Analyzing match..."):
            analysis = loader.analyze_match(match_id, ...)
        
        # Cache result
        st.session_state.analyses[match_id] = analysis
    
    # Display analysis
    st.write("Home History:", analysis["home_history"])
    st.write("Statistics:", analysis["statistics"])
```

## Avantages

### Pour l'Utilisateur
- ✅ Dashboard réactif
- ✅ Pas d'attente au chargement
- ✅ Contrôle sur les analyses
- ✅ Feedback visible

### Pour l'API
- ✅ Quota préservé
- ✅ Pas de gaspillage
- ✅ Analyses ciblées
- ✅ Cache efficace

### Pour le Développement
- ✅ Code modulaire
- ✅ Facile à tester
- ✅ Facile à étendre
- ✅ Maintenable

## Résumé

**Architecture 2 phases implémentée:**

1. ✅ **LightweightMatchScanner** - Fetch rapide
2. ✅ **MatchAnalysisLoader** - Analyse à la demande
3. ⏳ **ApiQuotaManager** - Protection quota (à créer)
4. ⏳ **Dashboard V6** - UX optimisée (à créer)
5. ⏳ **Cache agressif** - Optimisation (à améliorer)

**Le système est prêt pour un dashboard ultra-rapide et efficace ! 🚀**
