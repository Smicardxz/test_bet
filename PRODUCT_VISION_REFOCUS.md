# Product Vision - Recentrage Stratégique

## ❌ Ce Que Nous NE Sommes PAS

- Pas un simple scanner statistique
- Pas un agrégateur de données
- Pas un outil de visualisation générique

## ✅ Ce Que Nous SOMMES

**BOOKMAKER INEFFICIENCY DETECTOR**

Détecter les divergences entre:
1. Lignes bookmaker
2. Réalité statistique des ligues obscures

## Le Cœur du Produit

```
Historical Data
    +
League/Team Patterns
    +
HT/FT Trends
    +
Variance/Stability
    +
Bookmaker Lines
    =
INEFFICIENCY DETECTION
```

## Les 2 Modes

### Mode 1: STATISTICAL_SIGNAL_MODE

**Quand:** Pas d'odds disponibles (API free tier)

**Fonction:**
- Analyse historique uniquement
- Détecte profils statistiques
- Prépare pour comparaison future
- Identifie patterns extrêmes

**Output:**
```json
{
  "mode": "STATISTICAL_SIGNAL",
  "signal_type": "EXTREME_UNDER_PROFILE",
  "suggested_markets": ["UNDER_4_5", "UNDER_5_5"],
  "expected_goal_range": [2, 5],
  "historical_max_goals": 7,
  "hit_rates": {
    "under_0_5": 0.20,
    "under_1_5": 0.60,
    "under_2_5": 0.87,
    "under_3_5": 0.93,
    "under_4_5": 1.00
  },
  "status": "WAITING_FOR_ODDS"
}
```

### Mode 2: INEFFICIENCY_MODE

**Quand:** Odds disponibles

**Fonction:**
- Analyse historique
- Compare avec lignes bookmaker
- Calcule edge/divergence
- Détecte inefficiencies

**Output:**
```json
{
  "mode": "INEFFICIENCY_DETECTION",
  "signal_type": "EXTREME_UNDER_PROFILE",
  "bookmaker_line": "UNDER_12_5",
  "bookmaker_odds": 1.85,
  "historical_hit_rate": 1.00,
  "historical_max_goals": 7,
  "divergence_score": 95,
  "anomaly_score": 92,
  "edge_detected": true,
  "explanation": "Bookmaker line at 12.5 but historical max is 7 goals with 100% under rate"
}
```

## Architecture Refocusée

### SignalEngine (Phase 1)

**Rôle:** Détecter patterns statistiques

**Détecte:**
- HT under profiles
- FT under profiles
- Low variance
- Slow tempo
- Defensive patterns
- Extreme under profiles
- No BTTS profiles
- League scoring patterns

**Output enrichi:**
```python
class StatisticalSignal:
    signal_type: str  # "EXTREME_UNDER", "HT_UNDER", etc.
    confidence: float
    
    # Préparation pour bookmaker
    suggested_markets: List[str]
    compatible_lines: List[float]
    expected_ranges: Dict[str, tuple]
    
    # Historique
    hit_rates: Dict[str, float]  # Par ligne
    max_observed: int
    avg_goals: float
    variance: float
```

### AnomalyEngine (Phase 2)

**Rôle:** Détecter divergences bookmaker

**Compare:**
- Bookmaker line
- Signal statistique
- Variance
- Historical hit rate
- Line breach history
- Stability
- League profile

**Calcule:**
```python
class BookmakerInefficiency:
    # Bookmaker
    bookmaker_line: float
    bookmaker_odds: float
    implied_probability: float
    
    # Historical
    historical_probability: float
    line_breach_rate: float
    max_observed_goals: int
    
    # Divergence
    divergence_score: float  # 0-100
    anomaly_score: float
    edge_percentage: float
    
    # Risk
    confidence: float
    variance_risk: str  # LOW/MEDIUM/HIGH
    sample_size: int
```

### LineBreachAnalyzer (Nouveau - Critique)

**Rôle:** Analyser chaque ligne possible

**Pour chaque ligne (0.5, 1.5, 2.5, ..., 12.5):**

```python
class LineBreachAnalysis:
    line: float
    
    # Hit rates
    hit_rate: float  # % matches under this line
    breach_rate: float  # % matches over this line
    
    # Distance
    avg_distance_to_line: float
    max_distance: int
    
    # Stability
    variance: float
    consistency: float
    
    # Sample
    sample_size: int
    recent_trend: str  # "STABLE", "INCREASING", "DECREASING"
```

**Exemple:**
```
Under 12.5:
  hit_rate: 100% (15/15)
  max_goals: 7
  avg_goals: 4.1
  avg_distance: -8.4 (très loin de la ligne)
  variance: LOW
  
=> Ligne potentiellement incohérente
```

## Dashboard Recentré

### Page 1: Statistical Signals

**Affiche:** Profils détectés (même sans odds)

```
🔍 EXTREME UNDER PROFILE

Match: Kazakhstan vs Uzbekistan
League: Kazakhstan - First Division
Expected goals: 2-5
Historical max: 7 goals
Under 4.5 hit rate: 100%

⏳ WAITING FOR ODDS COMPARISON
```

### Page 2: Bookmaker Inefficiencies

**Affiche:** UNIQUEMENT si odds disponibles

```
⚠️ BOOKMAKER INEFFICIENCY DETECTED

Match: Kazakhstan vs Uzbekistan
League: Kazakhstan - First Division

Bookmaker Line: UNDER 12.5 @ 1.85
Historical Hit Rate: 100% (15/15)
Historical Max Goals: 7

Divergence Score: 95/100
Anomaly Score: 92/100
Edge: ~8.5%

Why Inefficient:
- Line set at 12.5 goals
- Historical max is only 7 goals
- Average 4.1 goals per match
- 100% hit rate on Under 4.5
- Low variance league
- Bookmaker line appears 5+ goals too high
```

## Odds Architecture

### Couche Enrichissante

**Sans odds:**
```
✅ Détecte profils statistiques
✅ Calcule hit rates
✅ Identifie patterns
⏳ Attend odds pour comparaison
```

**Avec odds:**
```
✅ Tout ce qui précède
✅ Compare avec bookmaker
✅ Calcule divergence
✅ Détecte inefficiencies
✅ Estime edge
```

## Marchés Prioritaires

### Focus Principal

1. **HT Under** - Mi-temps sous X buts
2. **Extreme Under** - Lignes élevées (8.5+, 10.5+, 12.5+)
3. **Under lines élevées** - Où bookmaker surestime
4. **Low-scoring leagues** - Ligues défensives

### Ligues Cibles

- Women obscure leagues
- Youth low tempo
- Reserve leagues
- Obscure countries (Kazakhstan, Vietnam, etc.)
- Lower divisions

## Workflow Utilisateur Final

### Matin - Scouting

```
1. Dashboard charge (1-2s)
2. Voir "Statistical Signals"
3. Identifier profils extrêmes:
   - "EXTREME UNDER PROFILE"
   - "HT UNDER PROFILE"
   - "NO BTTS PROFILE"
4. Noter matchs intéressants
```

### Après-midi - Inefficiency Detection

```
Si odds disponibles:
1. Dashboard passe en "INEFFICIENCY_MODE"
2. Compare signals vs bookmaker lines
3. Affiche divergences:
   - "Line 12.5 vs Historical Max 7"
   - "Divergence Score: 95/100"
4. Prendre décisions
```

### Sans Odds (Free Tier)

```
1. Voir signals statistiques
2. Noter profils extrêmes
3. Chercher odds manuellement
4. Comparer soi-même
5. OU attendre upgrade API
```

## Exemple Concret

### Match Détecté

```
Kazakhstan U21 vs Uzbekistan U21
League: Youth - Central Asia
```

### Statistical Signal (Mode 1)

```
Signal Type: EXTREME UNDER PROFILE

Historical Data (last 15 matches):
- Average goals: 3.8
- Max goals: 6
- Under 4.5: 14/15 (93%)
- Under 5.5: 15/15 (100%)
- Variance: LOW

Suggested Markets:
- Under 4.5
- Under 5.5
- Under 6.5

Status: WAITING FOR ODDS
```

### Bookmaker Inefficiency (Mode 2)

```
INEFFICIENCY DETECTED

Bookmaker: Bet365
Line: Under 10.5 @ 1.90

Analysis:
- Historical max: 6 goals
- Line set at: 10.5 goals
- Gap: 4.5 goals
- Historical hit rate: 100%
- Implied probability: 52.6%
- True probability: ~100%

Divergence Score: 98/100
Edge Estimate: ~47%

Why Inefficient:
Bookmaker line is 4.5 goals higher than
historical maximum. This appears to be a
significant pricing error for this league.
```

## Implémentation

### Fichiers à Créer

```
✅ app/core/modes.py
   - AnalysisMode enum
   - STATISTICAL_SIGNAL
   - INEFFICIENCY_DETECTION

✅ app/services/signals/signal_engine.py
   - Détection patterns
   - Hit rates calculation
   - Suggested markets

✅ app/services/anomaly/line_breach_analyzer.py
   - Analyse par ligne
   - Hit rates historiques
   - Distance to line

✅ app/services/anomaly/inefficiency_detector.py
   - Compare bookmaker vs historical
   - Calcule divergence
   - Détecte edge

✅ dashboard_v7.py
   - 2 modes clairs
   - Statistical Signals tab
   - Inefficiencies tab (si odds)
```

## Résumé

**Le produit est:**
Un détecteur de divergences entre bookmakers et réalité statistique des ligues obscures.

**Pas:**
Un simple scanner statistique.

**Les odds sont:**
Une couche enrichissante, pas un prérequis absolu.

**Le système fonctionne:**
En mode signal (sans odds) puis s'enrichit en mode inefficiency (avec odds).

**L'edge vient de:**
La divergence entre ligne bookmaker et réalité historique.

**Focus:**
Ligues obscures où bookmakers ont moins de données et font plus d'erreurs de pricing.
