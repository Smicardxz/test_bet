"""
shadow_tier_calculator.py
=========================
Shadow tier calculation for tier redesign simulation.

This implements the new tiering logic based on forensic audit findings:
- implied_probability is strongest predictor (35% weight)
- market_probability secondary (20% weight)
- Hard penalties for toxic patterns
- New thresholds for shadow tiers
"""

from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


# Toxic markets with hard penalties
TOXIC_MARKETS = {
    "FT_UNDER_1_5",
    "FT_OVER_3_5",
}

# Safe odds sources for shadow EV tier
SAFE_ODDS_SOURCES = {
    "API_FOOTBALL",
    "ODDS_API",
}


def compute_shadow_tier(
    implied_probability: float,
    bookmaker_odd: float,
    market_probability: float,
    ev_percentage: float,
    edge_percentage: float,
    confidence_score: float,
    market: str,
    odds_source: str,
    existing_tier: str = "",
) -> Tuple[str, float, str]:
    """
    Compute shadow tier based on new weighting formula.

    Args:
        implied_probability: Implied probability from bookmaker odds (0-1)
        bookmaker_odd: Bookmaker odds (decimal)
        market_probability: Model's market probability (0-1)
        ev_percentage: Expected value percentage
        edge_percentage: Edge percentage
        confidence_score: Confidence score (0-100)
        market: Market name
        odds_source: Odds source
        existing_tier: Existing tier for tier prior

    Returns:
        (shadow_tier, shadow_tier_score, shadow_tier_reason)
    """
    penalties = []
    score = 0.0

    # ── Base score components (0-100) ────────────────────────────────────────

    # 35% implied_probability (strongest predictor)
    impl_score = implied_probability * 35
    score += impl_score

    # 20% market_probability
    mkt_prob_score = market_probability * 20
    score += mkt_prob_score

    # 15% odds sanity (lower odds = higher score)
    # Odds between 1.2 and 2.5 are ideal
    if bookmaker_odd:
        if 1.2 <= bookmaker_odd <= 2.5:
            odds_score = 15
        elif 1.0 <= bookmaker_odd < 1.2:
            odds_score = 10  # Too low, suspicious
        elif 2.5 < bookmaker_odd <= 3.0:
            odds_score = 8
        elif bookmaker_odd > 3.0:
            odds_score = 0
        else:
            odds_score = 5
    else:
        odds_score = 0
        penalties.append("no_odds")
    score += odds_score

    # 10% market safety (avoid toxic markets)
    if market in TOXIC_MARKETS:
        market_safety = 0
        penalties.append("toxic_market")
    else:
        market_safety = 10
    score += market_safety

    # 10% tier prior (existing tier as weak signal)
    tier_prior = 0
    if existing_tier == "S_TIER":
        tier_prior = 10
    elif existing_tier == "A_TIER":
        tier_prior = 5  # Reduced due to toxicity
    elif existing_tier == "B_TIER":
        tier_prior = 7
    elif existing_tier == "WATCHLIST":
        tier_prior = 3
    score += tier_prior

    # 5% EV capped (penalize high EV)
    if ev_percentage:
        if ev_percentage <= 10:
            ev_score = 5
        elif ev_percentage <= 20:
            ev_score = 3
        elif ev_percentage <= 25:
            ev_score = 1
        else:
            ev_score = 0
            penalties.append("high_ev")
    else:
        ev_score = 0
    score += ev_score

    # 5% confidence capped (reduced weight)
    if confidence_score:
        if confidence_score >= 70:
            conf_score = 5
        elif confidence_score >= 50:
            conf_score = 3
        elif confidence_score >= 30:
            conf_score = 1
        else:
            conf_score = 0
    else:
        conf_score = 0
    score += conf_score

    # ── Hard penalties ───────────────────────────────────────────────────────

    # EV > 25%: toxic trap
    if ev_percentage and ev_percentage > 25:
        score -= 25
        if "high_ev" not in penalties:
            penalties.append("high_ev_trap")

    # Edge > 20%: negatively correlated with wins
    if edge_percentage and edge_percentage > 20:
        score -= 20
        penalties.append("high_edge")

    # Odds > 3.0: too risky
    if bookmaker_odd and bookmaker_odd > 3.0:
        score -= 25
        penalties.append("high_odds")

    # Toxic markets: already penalized above, but add extra
    if market in TOXIC_MARKETS:
        score -= 30
        if "toxic_market" not in penalties:
            penalties.append("toxic_market_extra")

    # A_TIER: toxic until proven stable
    if existing_tier == "A_TIER":
        score -= 10
        penalties.append("a_tier_toxic")

    # Missing odds source: cannot be shadow EV tier
    if not odds_source or odds_source not in SAFE_ODDS_SOURCES:
        penalties.append("unsafe_odds_source")

    # ── Clamp score to 0-100 ─────────────────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── Determine shadow tier ─────────────────────────────────────────────────
    if score >= 75:
        shadow_tier = "SHADOW_S"
    elif score >= 65:
        shadow_tier = "SHADOW_A"
    elif score >= 55:
        shadow_tier = "SHADOW_B"
    elif score >= 45:
        shadow_tier = "SHADOW_WATCH"
    else:
        shadow_tier = "SHADOW_RESEARCH"

    # Build reason string
    reason_parts = []
    if penalties:
        reason_parts.append(f"penalties: {','.join(penalties)}")
    reason_parts.append(f"score: {score:.1f}")
    shadow_tier_reason = "; ".join(reason_parts)

    return shadow_tier, score, shadow_tier_reason


def compute_shadow_tier_from_row(row: Dict) -> Tuple[str, float, str]:
    """
    Convenience wrapper to compute shadow tier from a prediction row dict.
    """
    try:
        implied_prob = float(row.get("implied_probability") or 0)
        bookmaker_odd = float(row.get("bookmaker_odd") or 0)
        market_prob = float(row.get("market_probability") or 0)
        ev_pct = float(row.get("ev_percentage") or 0)
        edge_pct = float(row.get("edge_percentage") or 0)
        confidence = float(row.get("confidence_score") or 0)
        market = row.get("market", "")
        odds_source = row.get("odds_source", "")
        existing_tier = (row.get("statistical_tier") or row.get("ev_tier") or "").upper()

        return compute_shadow_tier(
            implied_probability=implied_prob,
            bookmaker_odd=bookmaker_odd,
            market_probability=market_prob,
            ev_percentage=ev_pct,
            edge_percentage=edge_pct,
            confidence_score=confidence,
            market=market,
            odds_source=odds_source,
            existing_tier=existing_tier,
        )
    except Exception as e:
        logger.error(f"Error computing shadow tier from row: {e}")
        return "SHADOW_RESEARCH", 0.0, f"error: {str(e)}"
