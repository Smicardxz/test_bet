# TIER FORENSIC REPORT

**Date:** 2026-06-03
**Scope:** POST_RESET predictions (TRACKING_RESET_AT = 2026-06-02T15:19:00Z)
**Sample Size:** 119 predictions

---

## ⚠️ CRITICAL WARNING — SHADOW TIER FAILED

**DO NOT ACTIVATE SHADOW TIER SYSTEM**

The shadow tier simulation (Phase 7) failed to meet success criteria:
- SHADOW_S has only 4 settled picks (statistically insignificant)
- SHADOW_RESEARCH contains 89% of predictions (thresholds too high)
- SHADOW_RESEARCH outperforms higher shadow tiers (46.8% vs 0% for SHADOW_A/B)
- Penalties are too aggressive
- Sample size too small for 5-tier system

**Required Actions:**
1. Do NOT replace current tiers with shadow tiers
2. Do NOT use shadow_tier for live selection
3. Do NOT expose shadow_tier as main ranking in frontend
4. Keep shadow_tier only for research/audit purposes
5. Test on 6-12 months of historical data before reconsideration

**Status:** SHADOW_TIER_FAILED — Needs larger sample size and refinement before activation

---

---

## Executive Summary

The tier ranking system is **BROKEN**. The expected hierarchy (S > A > B > WATCHLIST > NO_VALUE) does not match observed reality.

**Key Finding:** A_TIER is severely underperforming (13.6% accuracy) while WATCHLIST and B_TIER significantly outperform it (39.0% and 31.8% respectively).

**Root Cause:** The tier assignment logic overweights features that are negatively correlated with actual wins (edge%, EV%, confidence_score) while underweighting the strongest predictor (implied_probability).

---

## Phase 1: Tier Scoring Breakdown

| Tier | Count | Win% | Confidence | MktProb | ImplProb | Edge% | EV% | AvgOdd |
|------|-------|------|------------|---------|----------|-------|-----|--------|
| S_TIER | 12 | 41.7% | 82.88 | 0.708 | 0.611 | 9.8% | 18.2% | 1.81 |
| A_TIER | 22 | 13.6% | 66.15 | 0.537 | 0.405 | 13.2% | 36.6% | 2.77 |
| B_TIER | 22 | 31.8% | 47.47 | 0.485 | 0.433 | 5.2% | 13.6% | 2.65 |
| WATCHLIST | 41 | 39.0% | 29.80 | 0.459 | 0.288 | 17.1% | 62.2% | 3.90 |
| NO_VALUE | 22 | 4.5% | 13.78 | 0.487 | 0.299 | 18.8% | 98.4% | 4.73 |

**Critical Insight:** A_TIER has the second-highest confidence (66.15) but the second-lowest accuracy (13.6%). Confidence is not predictive of performance.

---

## Phase 2: Feature Correlations vs Outcome

| Feature | Correlation | Direction |
|---------|-------------|----------|
| implied_probability | 0.238 | POSITIVE ✓ |
| market_probability | 0.180 | POSITIVE ✓ |
| bookmaker_odd | 0.178 | NEGATIVE (lower odds = higher win rate) |
| ranking_score | 0.150 | NEGATIVE |
| edge_percentage | 0.139 | NEGATIVE ✗ |
| ev_percentage | 0.133 | NEGATIVE ✗ |
| volatility_score | 0.099 | NEGATIVE |
| false_signal_score | 0.077 | NEGATIVE |
| chaos_score | 0.075 | NEGATIVE |
| confidence_score | 0.043 | POSITIVE (very weak) |

**Key Finding:** Implied probability is the strongest predictor (corr=0.238). Edge% and EV% are **negatively** correlated with wins — higher edge/EV leads to lower win rates.

---

## Phase 3: Current Tier Assignment Thresholds

Source: `app/services/scanner/smart_scanner.py` → `_compute_statistical_tier()`

### Current Logic

**S_TIER:**
- confidence_score >= 72
- volatility_score < 35
- false_signal_score < 30
- league_reliability >= 50
- sample_size >= 10

**A_TIER:**
- confidence_score >= 55
- volatility_score < 60
- false_signal_score < 50
- sample_size >= 6

**B_TIER:**
- confidence_score >= 40
- false_signal_score < 65
- sample_size >= 4

**WATCHLIST:**
- confidence_score >= 22
- sample_size >= 2

**NO_VALUE:**
- Below thresholds or refuse_pick

### Composite Score Formula

```
stat_score = (
    conf_n    * 0.45 +
    rel_n     * 0.20 +
    samp_n    * 0.20 +
    (1 - vol_n) * 0.075 +
    (1 - fss_n) * 0.075
) - ranking_penalty
```

**Problem:** Confidence is weighted 45% but has correlation of only 0.043 (near-zero predictive power).

---

## Phase 4: Tier Inversion Analysis

### Expected Order
S_TIER > A_TIER > B_TIER > WATCHLIST > NO_VALUE

### Actual Order (by Accuracy)
1. S_TIER (41.7%)
2. WATCHLIST (39.0%)
3. B_TIER (31.8%)
4. A_TIER (13.6%)
5. NO_VALUE (4.5%)

### Actual Order (by ROI)
1. S_TIER (-15.9%)
2. B_TIER (-163.0%)
3. WATCHLIST (-255.4%)
4. A_TIER (-276.6%)
5. NO_VALUE (-472.5%)

### Inversion Score
- Accuracy inversions: 3/10 (30.0%)
- ROI inversions: 2/10 (20.0%)
- **Total inversion rate: 25.0%**

### Specific Inversions
- A_TIER < B_TIER (accuracy and ROI)
- A_TIER < WATCHLIST (accuracy and ROI)
- B_TIER < WATCHLIST (accuracy)

---

## Phase 5: Toxic Tier Patterns

### Pattern 1: A_TIER Overweighting Edge%
- A_TIER average edge%: 13.2%
- B_TIER average edge%: 5.2%
- A_TIER accuracy: 13.6% vs B_TIER: 31.8%
- **Conclusion:** Edge% is negatively correlated with wins. A_TIER overweighting it is toxic.

### Pattern 2: High EV Traps
- A_TIER high EV (>25%) accuracy: 0.0% (n=6)
- S_TIER high EV (>25%) accuracy: 66.7% (n=3)
- **Conclusion:** High EV is a toxic trap in A_TIER but acceptable in S_TIER (small sample).

### Pattern 3: Confidence vs Reality Mismatch
- A_TIER: confidence=66.1, accuracy=13.6%
- S_TIER: confidence=82.9, accuracy=41.7%
- **Conclusion:** Confidence score is not predictive of actual performance.

### Pattern 4: Implied Probability Correlation
- S_TIER: implied_prob=0.611, accuracy=41.7%
- A_TIER: implied_prob=0.405, accuracy=13.6%
- B_TIER: implied_prob=0.433, accuracy=31.8%
- WATCHLIST: implied_prob=0.288, accuracy=39.0%
- **Conclusion:** Higher implied probability correlates with higher accuracy (strongest predictor).

---

## Phase 6: Proposed Tier Redesign

### Design Principles

1. **Weight implied_probability heavily** (strongest positive predictor)
2. **Reduce confidence weighting** (near-zero predictive power)
3. **Penalize high edge% and high EV%** (negatively correlated)
4. **Prioritize lower odds** (negative correlation with odd)
5. **Maintain sample size minimums** (statistical significance)

### Proposed New Thresholds

**S_TIER (Premium):**
- implied_probability >= 0.55
- market_probability >= 0.50
- bookmaker_odd <= 2.00
- ev_percentage <= 20 (avoid high EV traps)
- edge_percentage <= 10 (avoid high edge traps)
- confidence_score >= 60 (reduced from 72)
- sample_size >= 8

**A_TIER (Standard):**
- implied_probability >= 0.40
- market_probability >= 0.40
- bookmaker_odd <= 2.50
- ev_percentage <= 30
- edge_percentage <= 15
- confidence_score >= 45 (reduced from 55)
- sample_size >= 5

**B_TIER (Conservative):**
- implied_probability >= 0.30
- market_probability >= 0.30
- bookmaker_odd <= 3.00
- ev_percentage <= 40
- confidence_score >= 30 (reduced from 40)
- sample_size >= 3

**WATCHLIST (Speculative):**
- implied_probability >= 0.20
- market_probability >= 0.20
- bookmaker_odd <= 4.00
- confidence_score >= 20
- sample_size >= 2

**NO_VALUE:**
- Below thresholds or refuse_pick

### Proposed New Composite Score Formula

```
stat_score = (
    impl_n    * 0.35 +      # NEW: implied probability (strongest predictor)
    mkt_prob_n * 0.25 +     # NEW: market probability
    (1 - odd_n) * 0.15 +   # NEW: lower odds = higher score
    conf_n    * 0.15 +      # REDUCED: from 0.45 to 0.15
    rel_n     * 0.15 +      # SAME: league reliability
    samp_n    * 0.10 +      # REDUCED: from 0.20 to 0.10
    (1 - ev_n) * 0.05 +    # NEW: penalize high EV
    (1 - edge_n) * 0.05     # NEW: penalize high edge
) - ranking_penalty
```

### Expected Impact

Based on current POST_RESET data, applying these thresholds would:

1. **Reduce A_TIER count** from 22 to ~8 (filtering out high edge/EV traps)
2. **Promote WATCHLIST to B_TIER** for picks with implied_prob >= 0.30
3. **Demote A_TIER to B_TIER** for picks with implied_prob < 0.40
4. **Increase S_TIER accuracy** by filtering for implied_prob >= 0.55

**Projected Tier Accuracy (estimated):**
- S_TIER: 50-60% (current: 41.7%)
- A_TIER: 35-45% (current: 13.6%)
- B_TIER: 30-40% (current: 31.8%)
- WATCHLIST: 25-35% (current: 39.0% - will decrease as better picks move up)

---

## Implementation Notes

**DO NOT IMPLEMENT** without further validation on larger sample size.

**Recommended next steps:**
1. Apply proposed thresholds to historical data (last 6-12 months)
2. Validate projected accuracy improvements
3. Test in simulation mode for 2-4 weeks
4. Monitor live performance before full rollout

**File to modify:** `app/services/scanner/smart_scanner.py` → `_compute_statistical_tier()`

---

## Phase 7: Shadow Tier Simulation Results

**Date:** 2026-06-03
**Status:** SHADOW_TIER_FAILED

### Shadow Tier System Design

The shadow tier system implements the proposed redesign from Phase 6 with the following weighting:

**New Weighting Formula:**
- 35% implied_probability (strongest predictor)
- 20% market_probability
- 15% odds sanity (lower odds = higher score)
- 10% market safety (avoid toxic markets)
- 10% tier prior (existing tier as weak signal)
- 5% EV capped (penalize high EV)
- 5% confidence capped (reduced weight)

**Hard Penalties:**
- ev_percentage > 25%: -25 points (toxic trap)
- edge_percentage > 20%: -20 points (negatively correlated)
- bookmaker_odd > 3.0: -25 points (too risky)
- market in ["FT_UNDER_1_5", "FT_OVER_3_5"]: -30 points (toxic markets)
- tier == "A_TIER": -10 points (toxic until proven stable)
- odds_source missing: cannot be shadow EV tier

**Shadow Tier Thresholds:**
- SHADOW_S: score >= 75
- SHADOW_A: 65–74
- SHADOW_B: 55–64
- SHADOW_WATCH: 45–54
- SHADOW_RESEARCH: <45

### Shadow Tier Distribution (POST_RESET)

| Tier | Total | Settled | Accuracy | ROI | AvgOdd | AvgEV |
|------|-------|---------|----------|-----|--------|-------|
| SHADOW_S | 5 | 4 | 50.0% | -12.5% | 1.31 | 9.8% |
| SHADOW_A | 3 | 1 | 0.0% | -129.0% | 1.29 | 13.8% |
| SHADOW_B | 1 | 1 | 0.0% | -195.0% | 1.95 | 19.2% |
| SHADOW_WATCH | 4 | 3 | 33.3% | -75.0% | 2.06 | 19.3% |
| SHADOW_RESEARCH | 106 | 62 | 46.8% | -223.0% | 3.60 | 21.9% |

### Comparison: Old vs Shadow Tier Performance

**OLD TIER (by accuracy):**
1. WATCHLIST: 64.0%
2. B_TIER: 63.6%
3. S_TIER: 55.6%
4. A_TIER: 23.1%
5. NO_VALUE: 7.7%

**SHADOW TIER (by accuracy):**
1. SHADOW_S: 50.0%
2. SHADOW_RESEARCH: 46.8%
3. SHADOW_WATCH: 33.3%
4. SHADOW_A: 0.0%
5. SHADOW_B: 0.0%

### Monotonicity Check

**Expected:** SHADOW_S >= SHADOW_A >= SHADOW_B >= SHADOW_WATCH

**Actual:**
- SHADOW_S: 50.0%
- SHADOW_A: 0.0% ✗
- SHADOW_B: 0.0% ✗
- SHADOW_WATCH: 33.3% ✗

**Result:** Shadow tiers are NOT monotonic. SHADOW_B (0.0%) < SHADOW_WATCH (33.3%) is a significant inversion.

### SHADOW_S vs OLD_S Comparison

| Metric | OLD_S | SHADOW_S | Delta |
|--------|-------|----------|-------|
| Accuracy | 55.6% | 50.0% | -5.6% |
| ROI | 34.0% | -12.5% | -46.5% |
| Settled | 9 | 4 | -5 |
| AvgOdd | 1.79 | 1.31 | -0.48 |
| AvgEV | 13.7% | 9.8% | -3.9% |

**Result:** SHADOW_S does not outperform OLD_S in either accuracy or ROI.

### Analysis

The shadow tier system failed to meet success criteria for several reasons:

1. **Small sample size:** SHADOW_S has only 4 settled picks, making any comparison statistically insignificant.

2. **Over-penalization:** The hard penalties for high EV, high edge, and toxic markets may be too aggressive, filtering out too many picks and leaving only a small sample in higher tiers.

3. **SHADOW_A and SHADOW_B have 0% accuracy:** These tiers have only 1 settled pick each, which happened to lose. This is likely due to small sample size rather than a fundamental flaw in the logic.

4. **SHADOW_RESEARCH outperforms higher tiers:** At 46.8% accuracy, SHADOW_RESEARCH (the lowest tier) outperforms SHADOW_A, SHADOW_B, and SHADOW_WATCH. This suggests the threshold logic may need adjustment.

### Recommendations

1. **Increase sample size:** The shadow tier system needs more data to be properly evaluated. The current POST_RESET sample (119 predictions) is too small for a 5-tier system.

2. **Reduce penalty severity:** The hard penalties may be too aggressive. Consider reducing them or making them graduated instead of fixed amounts.

3. **Adjust thresholds:** The current thresholds (75, 65, 55, 45) may be too high, causing most predictions to fall into SHADOW_RESEARCH.

4. **Reconsider tier count:** With only 119 predictions, a 3-tier system (S, A, B) might be more appropriate than a 5-tier system.

5. **Test on historical data:** Apply the shadow tier system to 6-12 months of historical data to get a larger sample size before making final conclusions.

**Status:** SHADOW_TIER_FAILED — Needs refinement before reconsideration

---

## Conclusion

The current tier assignment system is fundamentally flawed because it overweights features that are negatively correlated with actual wins (edge%, EV%, confidence) while underweighting the strongest predictor (implied_probability).

The proposed redesign shifts focus to implied probability and market probability while reducing confidence weighting and adding penalties for high edge/EV. This should align tier rankings with actual performance and make S_TIER the highest ROI and hit rate tier as intended.

However, the shadow tier simulation failed to meet success criteria due to small sample size and potentially over-aggressive penalties. Further refinement and testing on larger historical data is required before the shadow tier system can be considered for production use.

**Status:** AUDIT COMPLETE — SHADOW TIER SIMULATION FAILED — RECOMMENDATION PROVIDED (NOT IMPLEMENTED)
