#!/usr/bin/env python3
"""
test_direct_parsing.py
======================
Test direct parsing of API-Football data.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

from app.providers.api_football_provider import ApiFootballProvider
from app.providers.models import MatchDetails


def test_direct_parsing():
    """Test direct parsing of API-Football data."""
    print(f"\n{'='*80}")
    print(f"🔍 DIRECT PARSING TEST")
    print(f"{'='*80}")
    
    # Create provider
    provider = ApiFootballProvider()
    
    # Get today's matches
    print(f"\n🔍 FETCHING TODAY'S MATCHES")
    print(f"{'='*60}")
    
    response = provider.get_today_matches()
    
    if not response.success:
        print(f"  ❌ Failed to fetch matches: {response.error}")
        return False
    
    matches = response.data
    print(f"  Total matches: {len(matches)}")
    
    # Find live matches
    live_matches = [m for m in matches if m.status.value == "live"]
    print(f"  Live matches: {len(live_matches)}")
    
    if not live_matches:
        print(f"  ⚠️  No live matches found")
        return False
    
    # Analyze first live match
    print(f"\n🔍 ANALYZING FIRST LIVE MATCH")
    print(f"{'='*60}")
    
    match = live_matches[0]
    
    print(f"  Match ID: {match.id}")
    print(f"  Teams: {match.home_team.name} vs {match.away_team.name}")
    print(f"  Status: {match.status.value}")
    print(f"  Status Short: {match.status_short}")
    print(f"  Status Long: {match.status_long}")
    print(f"  Elapsed: {match.elapsed}")
    print(f"  Score Fulltime: {match.score_fulltime}")
    print(f"  Score Halftime: {match.score_halftime}")
    
    if match.score_fulltime:
        print(f"  Current Score: {match.score_fulltime.home}-{match.score_fulltime.away}")
    
    if match.score_halftime:
        print(f"  Halftime Score: {match.score_halftime.home}-{match.score_halftime.away}")
    
    # Test _extract_match_data
    print(f"\n🔍 TESTING _extract_match_data")
    print(f"{'='*60}")
    
    from app.services.scanner.smart_scanner import SmartScanner
    from app.providers.odds.odds_provider_manager import OddsProviderManager
    
    # Create scanner
    odds_mgr = OddsProviderManager(
        apifootball_key=os.getenv("API_FOOTBALL_KEY", ""),
        oddsapi_key=os.getenv("ODDS_API_KEY", ""),
    )
    
    scanner = SmartScanner(
        provider=provider,
        is_real_data=True,
        include_extreme_obscure=True,
        odds_provider=odds_mgr
    )
    
    match_data = scanner._extract_match_data(match)
    
    print(f"  Extracted match_data keys: {list(match_data.keys())}")
    print(f"  home_score: {match_data.get('home_score')}")
    print(f"  away_score: {match_data.get('away_score')}")
    print(f"  minute: {match_data.get('minute')}")
    print(f"  elapsed: {match_data.get('elapsed')}")
    print(f"  ht_home_score: {match_data.get('ht_home_score')}")
    print(f"  ht_away_score: {match_data.get('ht_away_score')}")
    print(f"  status_short: {match_data.get('status_short')}")
    print(f"  status_long: {match_data.get('status_long')}")
    
    # Test _normalize_match
    print(f"\n🔍 TESTING _normalize_match")
    print(f"{'='*60}")
    
    # Import the function
    from app_flask import _normalize_match
    
    # Create mock match item
    match_item = {
        "match_data": match_data,
        "profile": {
            "target_level": "minor",
            "country": match.competition.country,
            "competition_name": match.competition.name
        },
        "analysis": {
            "match_profile": {
                "interest_score": 50.0,
                "confidence_score": 75.0,
                "volatility_score": 0.5,
                "variance_score": 0.25,
                "data_quality": "GOOD",
                "tempo_profile": "NORMAL",
                "scoring_profile": "NORMAL",
                "specific_profiles": [],
                "characteristics": []
            },
            "tier_level": "NO_VALUE",
            "ranking_score": 0.0,
            "ev_opportunities": [],
            "best_ev_opportunity": None,
            "odds_status": "NO_KEY",
            "matched_odds": [],
            "market_mapping_confidence": 0.0,
            "waiting_for_odds": True,
            "matchup_profile": {},
            "statistical_tier": "NO_VALUE",
            "statistical_ranking_score": 0.0,
            "match_universe": "STATISTICAL_ONLY",
            "coverage_quality": "NONE",
            "odds_count": 0,
            "signals": [],
            "best_edges": []
        }
    }
    
    normalized = _normalize_match(match_item)
    
    print(f"  Normalized match keys: {list(normalized.keys())}")
    print(f"  home_score: {normalized.get('home_score')}")
    print(f"  away_score: {normalized.get('away_score')}")
    print(f"  minute: {normalized.get('minute')}")
    print(f"  elapsed: {normalized.get('elapsed')}")
    print(f"  ht_home_score: {normalized.get('ht_home_score')}")
    print(f"  ht_away_score: {normalized.get('ht_away_score')}")
    print(f"  status_short: {normalized.get('status_short')}")
    print(f"  status_long: {normalized.get('status_long')}")
    print(f"  status: {normalized.get('status')}")
    
    return True


if __name__ == "__main__":
    success = test_direct_parsing()
    sys.exit(0 if success else 1)
