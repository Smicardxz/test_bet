# SignalEngine - Refactored ✅

## Objectif

Produire des signaux statistiques directement compatibles avec InefficiencyDetector.

## Pipeline Complet

```
Historical Data
    ↓
SignalEngine (Refactored)
    ↓
StatisticalSignal
    ↓
[Waiting for Odds]
    ↓
Bookmaker Line Available
    ↓
InefficiencyDetector
    ↓
InefficiencyResult
```

## StatisticalSignal Structure

Chaque signal inclut maintenant:

```python
@dataclass
class StatisticalSignal:
    # Signal identification
    signal_type: str  # EXTREME_UNDER, HT_UNDER, etc.
    signal_strength: str  # WEAK, MODERATE, STRONG, EXTREME
    confidence: float  # 0-1
    
    # Match context
    match_id: str
    home_team: str
    away_team: str
    competition: str
    country: str
    
    # Market suggestions (NEW)
    suggested_markets: List[str]  # ["UNDER_5_5", "UNDER_6_5"]
    compatible_lines: List[float]  # [5.5, 6.5, 7.5]
    expected_goal_range: Tuple[float, float]  # (2.1, 6.0)
    
    # Historical analysis (NEW)
    historical_hit_rates_by_line: Dict[float, float]  # {5.5: 1.00, 6.5: 1.00}
    max_observed_goals: int
    avg_goals: float
    
    # Quality metrics (NEW)
    variance_score: float  # 0-1 (lower variance = higher score)
    stability_score: float  # 0-1 (higher = more stable)
    sample_size: int
    data_quality: float  # 0-1
    
    # Status (NEW)
    waiting_for_odds: bool  # True until odds available
    
    # Explanation
    reasons: List[str]
```

## Signal Types Detected

### 1. EXTREME_UNDER

**Critères:**
- Average goals < 5.0
- Lines avec 95%+ hit rate au-dessus du max
- Variance faible

**Output Example:**
```python
{
    "signal_type": "EXTREME_UNDER",
    "signal_strength": "STRONG",
    "confidence": 0.80,
    "suggested_markets": ["UNDER_5_5", "UNDER_6_5", "UNDER_7_5"],
    "compatible_lines": [5.5, 6.5, 7.5, 8.5, 9.5],
    "expected_goal_range": (2.1, 6.0),
    "historical_hit_rates_by_line": {
        5.5: 1.00,
        6.5: 1.00,
        7.5: 1.00,
        8.5: 1.00
    },
    "max_observed_goals": 5,
    "avg_goals": 3.1,
    "variance_score": 0.85,
    "stability_score": 0.85,
    "sample_size": 15,
    "data_quality": 0.94,
    "waiting_for_odds": true
}
```

### 2. HT_UNDER

**Critères:**
- HT Under 1.5 hit rate >= 70%
- Minimum 5 matchs HT

**Output Example:**
```python
{
    "signal_type": "HT_UNDER",
    "signal_strength": "EXTREME",
    "confidence": 0.90,
    "suggested_markets": ["HT_UNDER_0_5", "HT_UNDER_1_5"],
    "compatible_lines": [0.5, 1.5],
    "historical_hit_rates_by_line": {
        0.5: 0.60,
        1.5: 1.00,
        2.5: 1.00
    },
    "max_observed_goals": 1,
    "avg_goals": 0.4,
    "waiting_for_odds": true
}
```

### 3. FT_UNDER

**Critères:**
- Under 2.5 hit rate >= 60%

**Output Example:**
```python
{
    "signal_type": "FT_UNDER",
    "signal_strength": "MODERATE",
    "confidence": 0.75,
    "suggested_markets": ["UNDER_2_5", "UNDER_3_5"],
    "compatible_lines": [2.5, 3.5],
    "waiting_for_odds": true
}
```

### 4. LOW_VARIANCE

**Critères:**
- Variance < 1.0 (variance_score >= 0.7)

**Output Example:**
```python
{
    "signal_type": "LOW_VARIANCE",
    "signal_strength": "STRONG",
    "confidence": 0.85,
    "variance_score": 0.98,
    "stability_score": 0.95,
    "waiting_for_odds": true
}
```

## Tests Validés

### Test 1: Extreme Under Signal ✅

```
Input: [3, 2, 4, 1, 5, 3, 2, 4, 3, 2, 5, 3, 4, 2, 3]

Output:
- Signal: EXTREME_UNDER
- Strength: STRONG
- Confidence: 0.80
- Max: 5 goals
- Average: 3.1 goals
- Variance score: 0.85
- Suggested markets: UNDER_5.5, UNDER_6.5, UNDER_7.5
- Hit rates: 100% for all suggested lines
```

### Test 2: HT Under Signal ✅

```
Input HT: [0, 0, 1, 0, 1, 0, 1, 0, 0, 1]

Output:
- Signal: HT_UNDER
- Strength: EXTREME
- Confidence: 0.90
- HT Max: 1 goal
- HT Average: 0.4 goals
- Under 1.5: 100% hit rate
```

### Test 3: Low Variance Signal ✅

```
Input: [2, 2, 3, 2, 2, 3, 2, 2, 3, 2, 2, 3, 2, 2, 3]

Output:
- Signal: LOW_VARIANCE
- Variance score: 0.98
- Stability score: 0.95
```

### Test 4: Pipeline Integration ✅

```
SignalEngine → InefficiencyDetector

Signal detected: EXTREME_UNDER
Bookmaker line: Under 12.5 @ 1.85

Inefficiency Result:
- Mode: INEFFICIENCY_DETECTION
- Inefficiency Level: STRONG
- Divergence: 78.4/100
- Edge: 31.9/100
- Action: COMPARE_ODDS
```

## Usage Example

```python
from app.services.signals.signal_engine import SignalEngine
from app.services.anomaly.inefficiency_detector import InefficiencyDetector

# Step 1: Detect signals
engine = SignalEngine()

goal_history = [3, 2, 4, 1, 5, 3, 2, 4, 3, 2, 5, 3, 4, 2, 3]
ht_goal_history = [0, 0, 1, 0, 1, 0, 1, 0, 0, 1]

match = {
    "match_id": "12345",
    "home_team": "Kazakhstan U21",
    "away_team": "Uzbekistan U21",
    "competition": "Youth League",
    "country": "Kazakhstan"
}

signals = engine.detect_signals(match, goal_history, ht_goal_history)

# Step 2: Display signals (waiting for odds)
for signal in signals:
    print(f"Signal: {signal.signal_type}")
    print(f"Suggested markets: {signal.suggested_markets}")
    print(f"Waiting for odds: {signal.waiting_for_odds}")
    
    for line in signal.compatible_lines:
        hit_rate = signal.historical_hit_rates_by_line[line]
        print(f"  - Under {line}: {hit_rate*100:.0f}% historical hit rate")

# Step 3: When odds become available
detector = InefficiencyDetector()

# For each suggested line, check inefficiency
for line in signal.compatible_lines[:3]:
    result = detector.detect(
        match=match,
        market_type="FT Under",
        bookmaker_line=line,
        odd=1.85,  # Example odd
        bookmaker="Bet365",
        historical_stats={
            "max_goals": signal.max_observed_goals,
            "avg_goals": signal.avg_goals,
            "variance": 1.0 - signal.variance_score,
            "sample_size": signal.sample_size
        },
        data_quality_score=signal.data_quality
    )
    
    if result.inefficiency_level in ["STRONG", "EXTREME"]:
        print(f"\n⚠️ INEFFICIENCY DETECTED")
        print(f"Line: Under {line}")
        print(f"Divergence: {result.divergence_score:.0f}/100")
        print(f"Action: {result.recommended_action}")
```

## Compatibility Matrix

| SignalEngine Output | InefficiencyDetector Input | Status |
|---------------------|----------------------------|--------|
| suggested_markets | market_type | ✅ Compatible |
| compatible_lines | bookmaker_line | ✅ Compatible |
| historical_hit_rates_by_line | line_breach_analysis | ✅ Compatible |
| max_observed_goals | historical_stats.max_goals | ✅ Compatible |
| avg_goals | historical_stats.avg_goals | ✅ Compatible |
| variance_score | historical_stats.variance | ✅ Compatible |
| sample_size | historical_stats.sample_size | ✅ Compatible |
| data_quality | data_quality_score | ✅ Compatible |

## Workflow Complet

### Phase 1: Statistical Signal (Sans Odds)

```python
# Detect signals
signals = engine.detect_signals(match, goal_history)

# Display to user
for signal in signals:
    print(f"⏳ {signal.signal_type}")
    print(f"Suggested: {signal.suggested_markets}")
    print(f"Waiting for odds...")
```

### Phase 2: Odds Comparison (Avec Odds)

```python
# When odds become available
for signal in signals:
    for line in signal.compatible_lines:
        # Get bookmaker odd for this line
        odd = get_bookmaker_odd(line)  # Your odds provider
        
        # Detect inefficiency
        result = detector.detect(
            match=match,
            market_type=signal.suggested_markets[0],
            bookmaker_line=line,
            odd=odd,
            historical_stats={...},  # From signal
            data_quality_score=signal.data_quality
        )
        
        if result.inefficiency_level == "EXTREME":
            print(f"⚠️ EXTREME INEFFICIENCY")
            print(f"Line: {line}")
            print(f"Edge: {result.edge_score:.0f}%")
```

## Fichiers

```
✅ app/services/signals/signal_engine.py
   - SignalEngine (refactored)
   - StatisticalSignal dataclass
   - 4 signal types

✅ tests/test_signal_engine.py
   - 4 test cases
   - All passing
   - Pipeline integration test

✅ app/services/anomaly/inefficiency_detector.py
   - InefficiencyDetector
   - Compatible with signals

✅ app/services/anomaly/line_breach_analyzer.py
   - LineBreachAnalyzer
   - Used by SignalEngine
```

## Résumé

**SignalEngine refactorisé:**

✅ Produit signaux compatibles avec InefficiencyDetector
✅ Inclut suggested_markets et compatible_lines
✅ Fournit historical_hit_rates_by_line
✅ Calcule variance_score et stability_score
✅ Flag waiting_for_odds
✅ 4 types de signaux détectés
✅ Tests validés (4/4 passed)
✅ Pipeline complet testé

**Le passage Statistical Signal → Odds Comparison → Inefficiency Detection est maintenant fluide ! 🎯**
