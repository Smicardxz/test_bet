# 🧮 Formules Mathématiques Complètes

## 📐 STATISTIQUES DE BASE

### **1. Moyenne Arithmétique**

```
μ = (Σ xi) / n

où :
- xi = valeur individuelle
- n = nombre d'observations
```

**Application** :
```python
avg_goals_ft = sum(total_goals) / len(matches)
```

---

### **2. Variance**

```
σ² = Σ(xi - μ)² / n

ou (formule computationnelle) :
σ² = [Σ(xi²) / n] - μ²
```

**Application** :
```python
variance = sum((x - mean)**2 for x in values) / len(values)
```

---

### **3. Écart-Type (Standard Deviation)**

```
σ = √σ²
```

**Application** :
```python
std_dev = sqrt(variance)
```

---

### **4. Coefficient de Variation**

```
CV = σ / μ

où :
- σ = écart-type
- μ = moyenne
```

**Interprétation** :
- CV < 0.3 : Faible variabilité
- 0.3 ≤ CV ≤ 0.6 : Variabilité modérée
- CV > 0.6 : Forte variabilité

**Application** :
```python
cv = std_dev / mean if mean > 0 else 0
```

---

## 📊 DISTRIBUTIONS PROBABILISTES

### **5. Distribution de Poisson**

**Fonction de Masse** :
```
P(X = k) = (λ^k × e^(-λ)) / k!

où :
- λ = paramètre (moyenne)
- k = nombre d'événements
- e = constante d'Euler (≈ 2.71828)
```

**Fonction de Répartition (CDF)** :
```
P(X ≤ k) = Σ(i=0 to k) [(λ^i × e^(-λ)) / i!]
```

**Application Over/Under** :
```python
from scipy.stats import poisson

lambda_param = avg_goals_ft
prob_under_25 = poisson.cdf(2, lambda_param)
prob_over_25 = 1 - prob_under_25
```

---

### **6. Distribution Binomiale Négative**

**Utilisée quand variance > moyenne (overdispersion)**

**Paramètres** :
```
r = μ² / (σ² - μ)
p = μ / σ²

où :
- μ = moyenne
- σ² = variance
- r = paramètre de dispersion
- p = probabilité de succès
```

**Fonction de Masse** :
```
P(X = k) = C(k+r-1, k) × (1-p)^r × p^k
```

**Application** :
```python
from scipy.stats import nbinom

mu = avg_goals
variance = var_goals

if variance > mu:
    r = mu**2 / (variance - mu)
    p = mu / variance
    prob_under_25 = nbinom.cdf(2, r, 1-p)
```

---

## 📈 RÉGRESSION & TENDANCES

### **7. Régression Linéaire Simple**

**Équation de la droite** :
```
y = a + bx

où :
b = Σ[(xi - x̄)(yi - ȳ)] / Σ(xi - x̄)²
a = ȳ - b×x̄
```

**Coefficient de Corrélation** :
```
r = Σ[(xi - x̄)(yi - ȳ)] / √[Σ(xi - x̄)² × Σ(yi - ȳ)²]
```

**Application Trend** :
```python
from scipy.stats import linregress

x = np.arange(len(goals))
y = np.array(goals)
slope, intercept, r_value, p_value, std_err = linregress(x, y)

trend_coefficient = slope / (np.mean(y) + 0.01)
```

---

## 🎲 PROBABILITÉS & BAYÉSIEN

### **8. Théorème de Bayes**

```
P(A|B) = [P(B|A) × P(A)] / P(B)

où :
- P(A|B) = probabilité a posteriori
- P(B|A) = vraisemblance
- P(A) = probabilité a priori
- P(B) = évidence
```

**Application Bayesian Smoothing** :
```
θ_smoothed = (n × θ_team + k × θ_league) / (n + k)

où :
- θ_team = statistique équipe
- θ_league = statistique ligue (prior)
- n = nombre de matchs
- k = force du prior (typiquement 5-10)
```

**Code** :
```python
def bayesian_smooth(team_stat, league_stat, n_matches, k=5):
    return (n_matches * team_stat + k * league_stat) / (n_matches + k)
```

---

### **9. Probabilité Implicite (Odds)**

**Conversion Cotes → Probabilité** :
```
P = 1 / cote

Exemple :
Cote 2.00 → P = 1/2.00 = 0.50 = 50%
Cote 1.50 → P = 1/1.50 = 0.667 = 66.7%
```

**Marge du Bookmaker** :
```
Marge = (1/cote_A + 1/cote_B) - 1

Exemple Over/Under 2.5 :
Over @ 1.90, Under @ 2.00
Marge = (1/1.90 + 1/2.00) - 1 = 0.0263 = 2.63%
```

**Probabilité Fair (sans marge)** :
```
P_fair = P_implied / (1 + marge)
```

---

## 📊 EXPECTED GOALS (xG)

### **10. xG Simplifié**

```
xG_home = (AS_home × DS_away) × λ_league × HF
xG_away = (AS_away × DS_home) × λ_league

où :
- AS = Attack Strength = avg_goals_scored / league_avg
- DS = Defense Strength = avg_goals_conceded / league_avg
- λ_league = moyenne buts ligue
- HF = Home Factor (1.2-1.5 selon ligue)
```

**Code** :
```python
def calculate_xg(home_attack, home_defense, away_attack, away_defense, 
                 league_avg=2.5, home_factor=1.3):
    
    xg_home = (home_attack + away_defense) / 2 * home_factor
    xg_away = (away_attack + home_defense) / 2
    
    return xg_home, xg_away
```

---

## 📉 STABILITÉ & CONFIANCE

### **11. Stability Score**

**Version Simple** :
```
Stability = 1 / (1 + CV)

où CV = coefficient de variation
```

**Version Avancée** :
```
Stability = e^(-CV) × (1 - |trend_coef|)

où :
- e = constante d'Euler
- trend_coef = coefficient de tendance normalisé
```

**Code** :
```python
def calculate_stability(cv, trend_coef=0):
    base_stability = 1 / (1 + cv)
    
    if trend_coef != 0:
        stability = np.exp(-cv) * (1 - abs(trend_coef))
    else:
        stability = base_stability
    
    return max(0, min(1, stability))
```

---

### **12. Confidence Interval**

**Intervalle de Confiance 95%** :
```
IC_95% = μ ± 1.96 × (σ / √n)

où :
- μ = moyenne
- σ = écart-type
- n = taille échantillon
- 1.96 = valeur critique pour 95%
```

**Code** :
```python
import scipy.stats as stats

def confidence_interval(data, confidence=0.95):
    mean = np.mean(data)
    std_err = stats.sem(data)
    margin = std_err * stats.t.ppf((1 + confidence) / 2, len(data) - 1)
    
    return mean - margin, mean + margin
```

---

## 🎯 DÉTECTION D'ANOMALIES

### **13. Z-Score**

```
z = (x - μ) / σ

où :
- x = valeur observée
- μ = moyenne population
- σ = écart-type population
```

**Interprétation** :
- |z| < 1 : Normal (68% des cas)
- 1 ≤ |z| < 2 : Inhabituel (27% des cas)
- 2 ≤ |z| < 3 : Rare (4% des cas)
- |z| ≥ 3 : Très rare (<1% des cas)

**Application Anomalie** :
```python
def detect_anomaly(team_stat, league_mean, league_std, threshold=2.0):
    z_score = (team_stat - league_mean) / league_std
    is_anomaly = abs(z_score) > threshold
    
    return is_anomaly, z_score
```

---

### **14. Percentile Rank**

```
Percentile = (nombre de valeurs < x) / n × 100
```

**Code** :
```python
from scipy.stats import percentileofscore

percentile = percentileofscore(league_values, team_value)

# Anomalie si percentile < 10 ou > 90
is_anomaly = percentile < 10 or percentile > 90
```

---

## 🔄 MOYENNES PONDÉRÉES

### **15. Weighted Moving Average (WMA)**

```
WMA = Σ(wi × xi) / Σwi

où :
- wi = poids pour observation i
- xi = valeur observation i
```

**Poids Décroissants** :
```
wi = 1 - (i × decay_rate)

Exemple avec 10 matchs :
w = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
```

**Code** :
```python
def weighted_moving_average(values, decay_rate=0.1):
    n = len(values)
    weights = np.array([1.0 - (i * decay_rate) for i in range(n)])
    weights = weights[::-1]  # inverser (récent = plus de poids)
    weights = weights / weights.sum()  # normaliser
    
    wma = np.sum(np.array(values) * weights)
    return wma
```

---

### **16. Exponential Moving Average (EMA)**

```
EMA_t = α × x_t + (1 - α) × EMA_(t-1)

où :
- α = smoothing factor (typiquement 0.2-0.3)
- x_t = valeur actuelle
- EMA_(t-1) = EMA précédente
```

**Code** :
```python
def exponential_moving_average(values, alpha=0.2):
    ema = values[0]
    
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    
    return ema
```

---

## 📊 COMBINAISON DE PROBABILITÉS

### **17. Probabilité Conjointe (Indépendance)**

```
P(A ∩ B) = P(A) × P(B)

Exemple BTTS & Over 2.5 :
P(BTTS ∩ Over2.5) = P(BTTS) × P(Over2.5)
```

**Ajustement Dépendance** :
```
P(A ∩ B) = P(A) × P(B) × correlation_factor

où correlation_factor ≈ 1.2-1.3 pour BTTS & Over
```

---

### **18. Probabilité Conditionnelle**

```
P(A|B) = P(A ∩ B) / P(B)

Exemple :
P(Over3.5 | Over2.5) = P(Over3.5) / P(Over2.5)
```

---

## 🎲 KELLY CRITERION (Gestion Bankroll)

### **19. Kelly Formula**

```
f* = (bp - q) / b

où :
- f* = fraction optimale du bankroll à miser
- b = cote - 1 (net odds)
- p = probabilité de gagner
- q = probabilité de perdre = 1 - p
```

**Exemple** :
```
Cote 2.50, Probabilité estimée 45%
b = 2.50 - 1 = 1.50
p = 0.45
q = 0.55

f* = (1.50 × 0.45 - 0.55) / 1.50
   = (0.675 - 0.55) / 1.50
   = 0.083 = 8.3% du bankroll
```

**Kelly Fractionnaire (plus conservateur)** :
```
f_fractional = f* × fraction

Typiquement : fraction = 0.25 (Quarter Kelly)
```

---

## 📈 VALUE BETTING

### **20. Expected Value (EV)**

```
EV = (P_win × profit) - (P_lose × stake)

ou en pourcentage :
EV% = (P_win × odds) - 1
```

**Exemple** :
```
Cote 2.20, Probabilité estimée 50%
EV% = (0.50 × 2.20) - 1 = 0.10 = +10%
```

**Seuil de Value** :
```
Value existe si : P_model > P_bookmaker

où :
P_bookmaker = 1 / cote
```

---

## 🔢 FORMULES COMPOSITES

### **21. Anomaly Score (Composite)**

```
AS = w1×(prob_gap × 10) + w2×line_diff + w3×stability - w4×variance_penalty

où :
- prob_gap = |P_model - P_bookmaker|
- line_diff = |expected_line - bookmaker_line|
- stability = stability_score
- variance_penalty = 1 - min(variance/5, 1)
- w1, w2, w3, w4 = poids
```

**Code** :
```python
def calculate_anomaly_score(prob_gap, line_diff, stability, variance):
    base_score = prob_gap * 10
    line_weight = min(abs(line_diff) * 0.5, 2.0)
    variance_penalty = max(0, 1 - (variance / 5))
    stability_bonus = stability * 0.5
    
    score = base_score + line_weight + stability_bonus - (1 - variance_penalty)
    
    return max(0, score)
```

---

### **22. Confidence Score (Multi-Factor)**

```
CS = Σ(wi × fi)

où :
- wi = poids facteur i
- fi = score facteur i (normalisé 0-1)

Facteurs :
- f1 = sample_size_score
- f2 = stability_score
- f3 = anomaly_magnitude_score
- f4 = probability_gap_score
- f5 = variance_score
```

**Code** :
```python
def calculate_confidence_score(factors, weights):
    confidence = sum(f * w for f, w in zip(factors.values(), weights.values()))
    
    if confidence >= 0.75:
        level = "HIGH"
    elif confidence >= 0.50:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return confidence, level
```

---

## 📊 NORMALISATION

### **23. Min-Max Normalization**

```
x_norm = (x - x_min) / (x_max - x_min)

Résultat : valeur entre 0 et 1
```

---

### **24. Z-Score Normalization**

```
x_norm = (x - μ) / σ

Résultat : distribution centrée sur 0, écart-type 1
```

---

### **25. Logistic Function (Sigmoid)**

```
f(x) = 1 / (1 + e^(-x))

Utilisée pour convertir valeurs → probabilités [0,1]
```

**Code** :
```python
def sigmoid(x):
    return 1 / (1 + np.exp(-x))
```

---

**Toutes les formules mathématiques nécessaires pour le système de détection d'anomalies.**
