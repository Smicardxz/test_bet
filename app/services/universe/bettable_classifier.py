"""
BettableUniverseClassifier
===========================
Classifies every match into one of three universes:
  BETTABLE      — strong bookmaker coverage, EV is calculable
  LIMITED       — partial bookmaker coverage
  RESEARCH_ONLY — virtually no coverage, statistical analysis only

Produces four scores that are added to the analysis dict without
touching any existing signal/scoring logic:
  market_access           : BETTABLE | LIMITED | RESEARCH_ONLY
  bettable_priority_score : 0-100
  odds_coverage_score     : 0-100
  market_liquidity_score  : 0-100
  bettable_tier           : statistical_tier + _EV / _STATISTICAL suffix

Zero dependencies on other app modules — pure classification.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


# ─── Country lists ─────────────────────────────────────────────────────────────

BETTABLE_COUNTRIES: frozenset = frozenset({
    # Asia
    "Japan", "China", "South Korea",
    # Scandinavia / Nordics
    "Finland", "Sweden", "Norway", "Denmark", "Iceland",
    # British Isles
    "Ireland", "Northern Ireland",
    # Central / Eastern Europe
    "Poland", "Czech Republic", "Slovakia", "Romania", "Bulgaria",
    "Croatia", "Serbia", "Slovenia", "Bosnia and Herzegovina",
    "Hungary", "Greece", "Cyprus",
    # South America
    "Colombia", "Peru", "Chile", "Ecuador", "Paraguay",
    "Uruguay", "Brazil", "Argentina",
    # North America
    "United States", "Canada",
    # Middle East (partial)
    "Israel",
})

# Countries that are ALWAYS research-only regardless of league
RESEARCH_ONLY_COUNTRIES: frozenset = frozenset({
    "Ethiopia", "Mali", "Kenya", "Niger", "Burkina Faso", "Togo",
    "Guinea", "Cameroon", "Congo", "Rwanda", "Tanzania", "Uganda",
    "Zambia", "Zimbabwe", "Malawi", "Mozambique", "Madagascar",
    "Sierra Leone", "Liberia", "Gambia", "Senegal",
    "Chad", "Sudan", "South Sudan", "Eritrea", "Djibouti",
    "Somalia", "Central African Republic", "Gabon",
    "Equatorial Guinea", "Benin", "Côte d'Ivoire",
    "Tajikistan", "Turkmenistan", "Kyrgyzstan", "Mongolia",
    "Maldives", "Bhutan", "Nepal", "Laos", "Cambodia",
    "Myanmar", "Timor-Leste", "Papua New Guinea",
    "Fiji", "Vanuatu", "Solomon Islands",
})

# Keyword fragments in league names that strongly indicate bookmaker presence
BETTABLE_LEAGUE_KEYWORDS: frozenset = frozenset({
    "j1", "j2", "j3", "j.league", "j league",
    "chinese super league", "china super league", "china league one",
    "k league",
    "veikkausliiga", "allsvenskan", "eliteserien", "superligaen",
    "urvalsdeild", "besta deild",
    "league of ireland", "premier division",
    "ekstraklasa", "fortuna liga",
    "liga i", "super liga", "hnl", "prva liga",
    "liga betplay",
    "liga 1", "liga profesional", "primera division",
    "mls next pro", "usl championship", "canadian premier",
    "serie b", "serie c",
    "primera nacional", "primera b",
    "championship", "league one", "league two",
    "segunda division", "segunda liga",
})

# Keyword fragments that flag RESEARCH_ONLY regardless of country
RESEARCH_LEAGUE_KEYWORDS: frozenset = frozenset({
    "regional", "amateur", "reserve", "youth", "u20", "u21", "u23",
    "women", "femenino", "feminin",
})


# ─── Classification logic ──────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    return (text or "").lower().strip()


def _check_league_keywords(league_lower: str, keywords: frozenset) -> bool:
    return any(kw in league_lower for kw in keywords)


def classify(
    country: str,
    league: str,
    has_bookmaker_odds: bool,
    odds_status: str = "",
    coverage_score: float = 0.0,
    statistical_tier: str = "",
) -> Dict[str, object]:
    """
    Classify a match into the bettable universe and compute priority scores.

    Parameters
    ----------
    country             : str  — country name from targeting profile
    league              : str  — competition/league name
    has_bookmaker_odds  : bool — whether odds_by_market is non-empty
    odds_status         : str  — "MATCHED" | "MATCHING_UNCERTAIN" | "NO_EVENTS" | "NO_KEY" | ...
    coverage_score      : float — 0-100 from targeting profile bookmaker_coverage
    statistical_tier    : str  — existing tier ("S_TIER", "A_TIER", "B_TIER", "WEAK", ...)

    Returns
    -------
    dict with keys:
        market_access           : str
        bettable_priority_score : int (0-100)
        odds_coverage_score     : int (0-100)
        market_liquidity_score  : int (0-100)
        bettable_tier           : str
    """
    country_n = _normalise(country)
    league_n  = _normalise(league)

    # ── Step 1: determine market_access ───────────────────────────────────────
    # Research-only flags override everything
    if (country in RESEARCH_ONLY_COUNTRIES
            or _check_league_keywords(league_n, RESEARCH_LEAGUE_KEYWORDS)):
        market_access = "RESEARCH_ONLY"

    elif (country in BETTABLE_COUNTRIES
          or _check_league_keywords(league_n, BETTABLE_LEAGUE_KEYWORDS)):
        market_access = "BETTABLE"

    else:
        # Middle ground: European/World leagues not explicitly listed
        _eu_hints = (
            "league", "premier", "division", "liga", "bundesliga",
            "ligue", "eredivisie", "primeira", "super league",
        )
        market_access = "LIMITED" if any(h in league_n for h in _eu_hints) else "RESEARCH_ONLY"

    # ── Step 2: odds_coverage_score (0-100) ───────────────────────────────────
    _odds_st = (odds_status or "").upper()
    if _odds_st == "MATCHED":
        odds_coverage_score = 90
    elif _odds_st == "MATCHING_UNCERTAIN":
        odds_coverage_score = 55
    elif has_bookmaker_odds:
        odds_coverage_score = 45
    elif market_access == "BETTABLE":
        odds_coverage_score = 20   # BETTABLE but no odds today — still known market
    elif market_access == "LIMITED":
        odds_coverage_score = 10
    else:
        odds_coverage_score = 3

    # ── Step 3: market_liquidity_score (0-100) ────────────────────────────────
    # Blend market_access tier with the coverage_score from the targeting profile
    _base_liq = {"BETTABLE": 60, "LIMITED": 30, "RESEARCH_ONLY": 5}[market_access]
    market_liquidity_score = min(100, int(_base_liq + coverage_score * 0.40))

    # ── Step 4: bettable_priority_score (0-100) ───────────────────────────────
    _base_prio = {
        "BETTABLE":      {"odds": 82, "no_odds": 55},
        "LIMITED":       {"odds": 45, "no_odds": 22},
        "RESEARCH_ONLY": {"odds": 18, "no_odds":  5},
    }[market_access]

    _prio_key  = "odds" if (has_bookmaker_odds or _odds_st == "MATCHED") else "no_odds"
    _base      = _base_prio[_prio_key]
    # Small bonus from coverage_score (max +15)
    _bonus     = min(15, int(coverage_score * 0.15))
    bettable_priority_score = min(100, _base + _bonus)

    # ── Step 5: bettable_tier ─────────────────────────────────────────────────
    _ev_eligible = (
        market_access == "BETTABLE"
        and _odds_st in ("MATCHED",)
        and bool(statistical_tier)
    )
    if _ev_eligible and statistical_tier in ("S_TIER", "A_TIER"):
        bettable_tier = f"{statistical_tier}_EV"
    elif bool(statistical_tier):
        bettable_tier = f"{statistical_tier}_STATISTICAL"
    else:
        bettable_tier = "UNCLASSIFIED"

    return {
        "market_access":           market_access,
        "bettable_priority_score": bettable_priority_score,
        "odds_coverage_score":     odds_coverage_score,
        "market_liquidity_score":  market_liquidity_score,
        "bettable_tier":           bettable_tier,
    }


# ─── Module-level singleton helper ────────────────────────────────────────────

def classify_match(
    match_data: dict,
    odds_by_market: dict,
    odds_status: str = "",
    coverage_score: float = 0.0,
    statistical_tier: str = "",
) -> Dict[str, object]:
    """
    Convenience wrapper accepting match_data dict instead of separate strings.
    """
    country = match_data.get("country") or ""
    league  = match_data.get("competition") or match_data.get("league") or ""
    return classify(
        country=country,
        league=league,
        has_bookmaker_odds=bool(odds_by_market),
        odds_status=odds_status,
        coverage_score=coverage_score,
        statistical_tier=statistical_tier,
    )
