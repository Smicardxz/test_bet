# Prochaines Améliorations - Edge Detector

## 🎯 OBJECTIFS

Le système est actuellement **biaisé UNDER**.

Il faut ajouter:
- OVER profiles
- BTTS detection
- Aggressive teams
- Late scoring patterns
- Contextual intelligence

---

## 📋 ROADMAP

### Phase 1: OVER Profiles ⏳

**Objectif:** Détecter les équipes/matchs à fort potentiel de buts

**Signaux à détecter:**

#### 1. EXTREME_OVER
```python
# Critères:
avg_goals >= 4.0
over_2.5_hit_rate >= 85%
over_3.5_hit_rate >= 70%

# Exemple:
avg goals = 4.2
Over 2.5 = 92%
Over 3.5 = 78%

→ EXTREME_OVER detected
```

#### 2. HIGH_SCORING_PROFILE
```python
# Critères:
avg_goals >= 3.0
over_2.5_hit_rate >= 75%

# Exemple:
avg goals = 3.4
Over 2.5 = 80%

→ HIGH_SCORING_PROFILE
```

#### 3. HT_GOAL_PROFILE
```python
# Critères:
ht_over_0.5_hit_rate >= 85%
avg_ht_goals >= 1.2

# Exemple:
HT Over 0.5 = 95%
Avg HT goals = 1.4

→ HT_GOAL_PROFILE
```

**Implémentation:**

```python
# Dans edge_detector.py

def detect_over_profiles(
    self,
    ft_goals: List[int],
    ht_goals: List[int]
) -> List[str]:
    """Detect OVER scoring profiles"""
    profiles = []
    
    avg_goals = sum(ft_goals) / len(ft_goals)
    avg_ht_goals = sum(ht_goals) / len(ht_goals) if ht_goals else 0
    
    # EXTREME_OVER
    over_2_5 = sum(1 for g in ft_goals if g > 2.5) / len(ft_goals)
    over_3_5 = sum(1 for g in ft_goals if g > 3.5) / len(ft_goals)
    
    if avg_goals >= 4.0 and over_2_5 >= 0.85 and over_3_5 >= 0.70:
        profiles.append("EXTREME_OVER")
    
    # HIGH_SCORING_PROFILE
    elif avg_goals >= 3.0 and over_2_5 >= 0.75:
        profiles.append("HIGH_SCORING_PROFILE")
    
    # HT_GOAL_PROFILE
    if ht_goals:
        ht_over_0_5 = sum(1 for g in ht_goals if g > 0.5) / len(ht_goals)
        if ht_over_0_5 >= 0.85 and avg_ht_goals >= 1.2:
            profiles.append("HT_GOAL_PROFILE")
    
    return profiles
```

---

### Phase 2: BTTS Detection ⏳

**Objectif:** Détecter Both Teams To Score

**Critères:**

```python
def detect_btts_edge(
    self,
    match_history: List[Dict],
    bookmaker_odds: Optional[Dict] = None
) -> Optional[EdgeOpportunity]:
    """Detect BTTS edge"""
    
    # Calculer BTTS hit rate
    btts_count = 0
    for match in match_history:
        home_scored = match.get("home_goals", 0) > 0
        away_scored = match.get("away_goals", 0) > 0
        if home_scored and away_scored:
            btts_count += 1
    
    btts_hit_rate = btts_count / len(match_history)
    
    # Minimum 70% pour BTTS edge
    if btts_hit_rate < 0.70:
        return None
    
    # Calculer fair odd
    fair_odd = 1 / btts_hit_rate if btts_hit_rate > 0 else None
    
    # Si bookmaker odd disponible
    if bookmaker_odds and "BTTS_YES" in bookmaker_odds:
        market_odd = bookmaker_odds["BTTS_YES"]
        implied_prob = 1 / market_odd
        edge = btts_hit_rate - implied_prob
        
        if edge >= self.MIN_EDGE_PERCENT:
            return EdgeOpportunity(
                market="BTTS YES",
                market_type="BTTS",
                line=0,
                historical_probability=btts_hit_rate,
                implied_probability=implied_prob,
                market_odd=market_odd,
                fair_odd=fair_odd,
                edge_percent=edge,
                edge_value=self.calculate_expected_value(btts_hit_rate, market_odd),
                sample_size=len(match_history),
                hit_rate=btts_hit_rate * 100,
                confidence=self.assess_confidence(len(match_history), btts_hit_rate * 100, 0),
                variance="MEDIUM",
                reasons=[
                    f"BTTS hit rate: {btts_hit_rate * 100:.0f}%",
                    f"Edge: +{edge * 100:.1f}%",
                    f"Both teams scored in {btts_count}/{len(match_history)} matches"
                ]
            )
    
    return None
```

---

### Phase 3: Contextual Intelligence ⏳

**Objectif:** Croiser plusieurs dimensions

#### 1. Team Style Analysis

```python
class TeamStyleAnalyzer:
    """Analyze team playing style"""
    
    def analyze_team_style(
        self,
        team_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze team style from history
        
        Returns:
            {
                "offensive_strength": "HIGH" | "MEDIUM" | "LOW",
                "defensive_strength": "HIGH" | "MEDIUM" | "LOW",
                "tempo": "FAST" | "MEDIUM" | "SLOW",
                "scoring_distribution": {
                    "first_half": 0.45,
                    "second_half": 0.55
                },
                "consistency": "HIGH" | "MEDIUM" | "LOW"
            }
        """
        
        goals_scored = [m["goals_scored"] for m in team_history]
        goals_conceded = [m["goals_conceded"] for m in team_history]
        
        avg_scored = sum(goals_scored) / len(goals_scored)
        avg_conceded = sum(goals_conceded) / len(goals_conceded)
        
        # Offensive strength
        if avg_scored >= 2.0:
            offensive = "HIGH"
        elif avg_scored >= 1.2:
            offensive = "MEDIUM"
        else:
            offensive = "LOW"
        
        # Defensive strength
        if avg_conceded <= 0.8:
            defensive = "HIGH"
        elif avg_conceded <= 1.5:
            defensive = "MEDIUM"
        else:
            defensive = "LOW"
        
        return {
            "offensive_strength": offensive,
            "defensive_strength": defensive,
            "avg_goals_scored": avg_scored,
            "avg_goals_conceded": avg_conceded
        }
```

#### 2. Home/Away Split

```python
def analyze_home_away_split(
    self,
    home_history: List[Dict],
    away_history: List[Dict]
) -> Dict[str, Any]:
    """Analyze home vs away performance"""
    
    home_avg = sum(m["total_goals"] for m in home_history) / len(home_history)
    away_avg = sum(m["total_goals"] for m in away_history) / len(away_history)
    
    split_diff = home_avg - away_avg
    
    return {
        "home_avg_goals": home_avg,
        "away_avg_goals": away_avg,
        "split_difference": split_diff,
        "home_advantage": split_diff > 0.5,
        "away_advantage": split_diff < -0.5
    }
```

#### 3. Opponent Type

```python
def classify_opponent(
    self,
    opponent_history: List[Dict]
) -> str:
    """Classify opponent type"""
    
    avg_goals = sum(m["total_goals"] for m in opponent_history) / len(opponent_history)
    
    if avg_goals >= 3.5:
        return "ATTACKING"
    elif avg_goals <= 1.5:
        return "DEFENSIVE"
    else:
        return "BALANCED"
```

---

### Phase 4: LATE_GOAL_PROFILE ⏳

**Objectif:** Détecter équipes qui marquent tard

**Données nécessaires:**
- Temps des buts (minute)
- Distribution temporelle

**Critères:**

```python
def detect_late_goal_profile(
    self,
    goal_times: List[int]  # Minutes des buts
) -> bool:
    """
    Detect if team scores late
    
    Args:
        goal_times: List of goal minutes [23, 67, 89, 45, 78, ...]
    
    Returns:
        True if late goal profile detected
    """
    
    if len(goal_times) < 10:
        return False
    
    # Compter buts après 70e minute
    late_goals = sum(1 for t in goal_times if t >= 70)
    late_goal_rate = late_goals / len(goal_times)
    
    # 70%+ des buts après 70e minute
    return late_goal_rate >= 0.70
```

**Note:** API-Football ne fournit pas les temps de buts dans l'historique basique.
Nécessite endpoint `/fixtures/events` (tier supérieur ou requête supplémentaire).

---

### Phase 5: League Profile Integration ⏳

**Objectif:** Utiliser profil de league

```python
def integrate_league_profile(
    self,
    match_analysis: Dict,
    league_profile: Dict
) -> Dict:
    """
    Adjust edge detection based on league profile
    
    Args:
        match_analysis: Match analysis results
        league_profile: League characteristics
    
    Returns:
        Adjusted analysis with league context
    """
    
    league_tempo = league_profile.get("tempo", "MEDIUM")
    league_avg_goals = league_profile.get("avg_goals", 2.5)
    
    # Ajuster confidence si match align avec league
    match_avg = match_analysis.get("avg_goals", 0)
    
    if abs(match_avg - league_avg_goals) < 0.5:
        # Match aligne avec league → boost confidence
        match_analysis["confidence_boost"] = "LEAGUE_ALIGNED"
    
    if league_tempo == "FAST" and match_avg >= 3.0:
        match_analysis["context_flags"] = ["FAST_LEAGUE", "HIGH_SCORING"]
    
    return match_analysis
```

---

## 🔧 MODIFICATIONS NÉCESSAIRES

### 1. EdgeDetector Extension

**Fichier:** `app/services/analysis/edge_detector.py`

**Ajouter:**
```python
def detect_over_profiles(self, ft_goals, ht_goals) -> List[str]
def detect_btts_edge(self, match_history, bookmaker_odds) -> Optional[EdgeOpportunity]
def analyze_team_style(self, team_history) -> Dict
def analyze_home_away_split(self, home_history, away_history) -> Dict
```

### 2. SmartScanner Integration

**Fichier:** `app/services/scanner/smart_scanner.py`

**Ajouter:**
```python
# Après edge detection
over_profiles = self.edge_detector.detect_over_profiles(
    ft_goals=goal_history,
    ht_goals=ht_goal_history
)

# Ajouter dans analysis
analysis["over_profiles"] = over_profiles
analysis["contextual_intelligence"] = {
    "team_style": team_style,
    "home_away_split": split,
    "league_alignment": alignment
}
```

### 3. Dashboard Display

**Fichier:** `templates/dashboard_intelligence.html`

**Ajouter badges:**
```html
${over_profiles.includes('EXTREME_OVER') ? 
  '<span class="badge" style="background: var(--red);">🔥 EXTREME OVER</span>' 
  : ''}

${over_profiles.includes('HT_GOAL_PROFILE') ? 
  '<span class="badge" style="background: var(--orange);">⚡ HT GOALS</span>' 
  : ''}
```

---

## 📊 EXEMPLE COMPLET

### Données Match

```python
# Historique
ft_goals = [4, 5, 3, 4, 6, 3, 5, 4, 3, 4]  # Avg: 4.1
ht_goals = [2, 2, 1, 2, 3, 1, 2, 2, 1, 2]  # Avg: 1.8

# BTTS
btts_matches = 9/10  # 90%
```

### Détection

```python
# OVER Profiles
over_profiles = [
    "EXTREME_OVER",      # avg >= 4.0
    "HT_GOAL_PROFILE"    # HT avg >= 1.2
]

# BTTS Edge
btts_edge = {
    "market": "BTTS YES",
    "hit_rate": 90,
    "fair_odd": 1.11,
    "edge_percent": 0.15  # Si bookmaker @ 1.30
}

# Over 2.5 Edge
over_2_5_edge = {
    "market": "OVER 2.5",
    "hit_rate": 100,
    "fair_odd": 1.00,  # ← IGNORED (too low)
}

# Over 3.5 Edge
over_3_5_edge = {
    "market": "OVER 3.5",
    "hit_rate": 80,
    "fair_odd": 1.25,
    "edge_percent": 0.12  # Si bookmaker @ 1.45
}
```

### Affichage Dashboard

```
🔥 BEST EDGE
OVER 3.5
Market Odd: 1.45

Edge: +12%
Fair Odd: 1.25
Sample: 10

🔥 EXTREME OVER  ⚡ HT GOALS

WHY DETECTED:
• Edge: +12% vs bookmaker
• 80% hit rate (8/10)
• Avg goals: 4.1
• EXTREME_OVER profile
• HT avg: 1.8 (fast starts)
• BTTS 90% (both teams score)
```

---

## ✅ CHECKLIST IMPLÉMENTATION

### Phase 1: OVER Profiles
- [ ] Créer `detect_over_profiles()`
- [ ] Détecter EXTREME_OVER
- [ ] Détecter HIGH_SCORING_PROFILE
- [ ] Détecter HT_GOAL_PROFILE
- [ ] Intégrer dans SmartScanner
- [ ] Afficher badges dashboard
- [ ] Tester avec données réelles

### Phase 2: BTTS
- [ ] Créer `detect_btts_edge()`
- [ ] Calculer BTTS hit rate
- [ ] Calculer edge vs bookmaker
- [ ] Ajouter dans best_edges
- [ ] Afficher dashboard
- [ ] Tester

### Phase 3: Contextual Intelligence
- [ ] Créer `TeamStyleAnalyzer`
- [ ] Analyser offensive/defensive strength
- [ ] Analyser home/away split
- [ ] Classifier opponent type
- [ ] Intégrer league profile
- [ ] Afficher contexte dashboard

### Phase 4: LATE_GOAL_PROFILE
- [ ] Vérifier disponibilité goal times API
- [ ] Créer `detect_late_goal_profile()`
- [ ] Intégrer si données disponibles
- [ ] Afficher badge dashboard

---

## 🎯 PRIORITÉS

### Haute Priorité
1. ✅ OVER Profiles (facile, impact élevé)
2. ✅ BTTS Detection (facile, impact élevé)

### Moyenne Priorité
3. ⏳ Team Style Analysis (moyen, impact moyen)
4. ⏳ Home/Away Split (facile, impact moyen)

### Basse Priorité
5. ⏳ LATE_GOAL_PROFILE (difficile, données manquantes)
6. ⏳ League Profile Integration (moyen, impact faible)

---

**Prochaine étape: Implémenter OVER Profiles ! 🚀**
