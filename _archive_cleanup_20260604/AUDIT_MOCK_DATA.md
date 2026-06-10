# Audit Mock Data - Résultats Critiques

## 🚨 ÉTAT ACTUEL: SYSTÈME INVALIDE

### Problèmes Détectés

#### 1. API_KEY Non Configurée ❌
```
DATA_PROVIDER: api_football
API_KEY: NOT SET
→ Fallback sur MOCK automatique
```

#### 2. Mock Data dans smart_scanner.py ❌
**Fichier:** `app/services/scanner/smart_scanner.py`
**Lignes:** 286-298

```python
# Mock data based on league type
if profile.is_women or profile.is_youth:
    goal_history = [1, 2, 1, 0, 2, 1, 2, 1, 0, 2, 1, 2, 1, 1, 2]  # MOCK !
    ht_goal_history = [0, 0, 1, 0, 0, 1, 0, 1, 0, 0]  # MOCK !
elif "reserve" in profile.competition.lower():
    goal_history = [2, 3, 2, 1, 3, 2, 2, 3, 1, 2, 3, 2, 2, 1, 3]  # MOCK !
    ht_goal_history = [0, 1, 0, 0, 1, 1, 0, 1, 0, 1]  # MOCK !
else:
    goal_history = [2, 3, 1, 4, 2, 3, 2, 1, 3, 2, 4, 2, 3, 1, 2]  # MOCK !
    ht_goal_history = [0, 1, 0, 1, 0, 1, 1, 0, 1, 0]  # MOCK !
```

**Impact:**
- TOUS les hit rates sont calculés sur données fictives
- TOUS les fair odds sont basés sur mock
- TOUTES les analyses sont invalides

#### 3. Endpoints Manquants ❌

**get_team_history():** NOT IMPLEMENTED
**get_h2h():** NOT IMPLEMENTED

---

## ✅ ACTIONS REQUISES

### Action 1: Supprimer TOUT le Mock de smart_scanner.py

**Fichier:** `app/services/scanner/smart_scanner.py`
**Méthode:** `_analyze_match()`

**Remplacer:**
```python
# Mock data based on league type
if profile.is_women or profile.is_youth:
    goal_history = [1, 2, 1, 0, 2, ...]
    ht_goal_history = [0, 0, 1, 0, ...]
# ...
```

**Par:**
```python
# Fetch REAL historical data from provider
try:
    # Get team IDs
    home_team_id = match.home_team.id if hasattr(match.home_team, 'id') else None
    away_team_id = match.away_team.id if hasattr(match.away_team, 'id') else None
    
    if not home_team_id or not away_team_id:
        logger.warning(f"Missing team IDs for {match.home_team.name} vs {match.away_team.name}")
        return {
            "status": "DATA_INSUFFICIENT",
            "reason": "MISSING_TEAM_IDS",
            "signals": []
        }
    
    # Fetch team histories
    home_history = self.provider.get_team_history(home_team_id, limit=10)
    away_history = self.provider.get_team_history(away_team_id, limit=10)
    
    if not home_history or not away_history:
        logger.warning(f"No history available for teams")
        return {
            "status": "DATA_INSUFFICIENT",
            "reason": "NO_HISTORY_AVAILABLE",
            "signals": []
        }
    
    # Extract goal data
    goal_history = []
    ht_goal_history = []
    
    for match_data in home_history + away_history:
        if hasattr(match_data, 'goals'):
            total_goals = match_data.goals.home + match_data.goals.away
            goal_history.append(total_goals)
            
            if hasattr(match_data, 'score') and hasattr(match_data.score, 'halftime'):
                ht_total = match_data.score.halftime.home + match_data.score.halftime.away
                ht_goal_history.append(ht_total)
    
    if len(goal_history) < 5:
        return {
            "status": "DATA_INSUFFICIENT",
            "reason": "INSUFFICIENT_SAMPLE_SIZE",
            "sample_size": len(goal_history),
            "signals": []
        }
    
except Exception as e:
    logger.error(f"Error fetching historical data: {e}")
    return {
        "status": "DATA_INSUFFICIENT",
        "reason": "PROVIDER_ERROR",
        "error": str(e),
        "signals": []
    }
```

### Action 2: Implémenter get_team_history()

**Fichier:** `app/providers/api_football_provider.py`

**Ajouter:**
```python
def get_team_history(self, team_id: int, limit: int = 10) -> List[Any]:
    """
    Get team's recent matches
    
    Endpoint: /fixtures
    Params: team={team_id}&last={limit}
    """
    try:
        response = self._make_request(
            endpoint="fixtures",
            params={
                "team": team_id,
                "last": limit
            }
        )
        
        if response and "response" in response:
            return [self._parse_fixture(f) for f in response["response"]]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching team history: {e}")
        return []
```

### Action 3: Implémenter get_h2h()

**Fichier:** `app/providers/api_football_provider.py`

**Ajouter:**
```python
def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> List[Any]:
    """
    Get head-to-head matches
    
    Endpoint: /fixtures/headtohead
    Params: h2h={team1_id}-{team2_id}&last={limit}
    """
    try:
        response = self._make_request(
            endpoint="fixtures/headtohead",
            params={
                "h2h": f"{team1_id}-{team2_id}",
                "last": limit
            }
        )
        
        if response and "response" in response:
            return [self._parse_fixture(f) for f in response["response"]]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching H2H: {e}")
        return []
```

### Action 4: Configurer API_KEY

**Fichier:** `.env`

**Ajouter:**
```
DATA_PROVIDER=api_football
API_FOOTBALL_KEY=your_api_key_here
```

---

## 🎯 VALIDATION

**Après corrections, relancer:**
```bash
python scripts/audit_real_data_endpoints.py
```

**Résultat attendu:**
```
✅ SYSTEM VALID
   - Fixtures endpoint OK
   - No mock data detected
   - Team history implemented
   - H2H implemented
```

---

## 📊 RÈGLES STRICTES

### En Mode API Réel (DATA_PROVIDER=api_football)

**JAMAIS:**
- ❌ Utiliser goal_history = [1, 2, 3, ...]
- ❌ Fallback sur mock si données manquantes
- ❌ Calculer hit rates sur données fictives
- ❌ Afficher NO_VALUE sans odds réelles

**TOUJOURS:**
- ✅ Fetch données réelles du provider
- ✅ Retourner DATA_INSUFFICIENT si indisponible
- ✅ Retourner MISSING_HISTORY si pas d'historique
- ✅ Retourner WAITING_FOR_ODDS si pas d'odds
- ✅ Logger les raisons précises

---

## ✅ RÉSUMÉ

**État actuel:** INVALIDE
**Mock détecté:** OUI
**Endpoints manquants:** 2 (team_history, h2h)

**Actions critiques:**
1. Supprimer mock de smart_scanner.py
2. Implémenter get_team_history()
3. Implémenter get_h2h()
4. Configurer API_KEY

**Prochaine étape:**
Implémenter le pipeline réel avec vraies données API-Football
