"""
debug_shadow_generation.py
==========================
Debug why shadow portfolio is empty.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _ok(m):   print(f"  {GREEN}✓{RESET}  {m}")
def _err(m):  print(f"  {RED}✗{RESET}  {m}")
def _warn(m): print(f"  {YELLOW}⚠{RESET}  {m}")
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def main():
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  DEBUG SHADOW GENERATION{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # FETCH PREDICTIONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — FETCH PREDICTIONS{RESET}")
    print(f"{'='*66}")
    
    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")
    
    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
    
    if reset_at:
        if "T" in reset_at:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, created_at, prediction_date, "
                "home_team, away_team, league, fixture_id, "
                "offensive_profile, defensive_profile, market_generation_stats, "
                "recommended_market_direction, best_over_market, best_under_market, "
                "market_regime, confidence_score, volatility_score, chaos_score, "
                "event_context, country, kickoff_time"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, created_at, prediction_date, "
                "home_team, away_team, league, fixture_id, "
                "offensive_profile, defensive_profile, market_generation_stats, "
                "recommended_market_direction, best_over_market, best_under_market, "
                "market_regime, confidence_score, volatility_score, chaos_score, "
                "event_context, country, kickoff_time"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, selection_mode, bookmaker_odd, "
            "ev_percentage, created_at, prediction_date, "
            "home_team, away_team, league, fixture_id, "
            "offensive_profile, defensive_profile, market_generation_stats, "
            "recommended_market_direction, best_over_market, best_under_market, "
            "market_regime, confidence_score, volatility_score, chaos_score, "
            "event_context, country, kickoff_time"
        ).gte("prediction_date", cutoff)
    
    rows = q.execute().data or []
    print(f"Total predictions: {len(rows)}")
    
    # ========================================================================
    # CHECK PROFILE DATA
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — CHECK PROFILE DATA{RESET}")
    print(f"{'='*66}")
    
    with_offensive = [r for r in rows if r.get("offensive_profile")]
    with_defensive = [r for r in rows if r.get("defensive_profile")]
    with_market_regime = [r for r in rows if r.get("market_regime")]
    
    print(f"Predictions with offensive_profile: {len(with_offensive)}")
    print(f"Predictions with defensive_profile: {len(with_defensive)}")
    print(f"Predictions with market_regime: {len(with_market_regime)}")
    
    if len(with_offensive) == 0:
        _warn("No predictions have offensive_profile")
        print(f"\nSample prediction structure:")
        if rows:
            print(f"  Keys: {list(rows[0].keys())}")
        return
    
    # ========================================================================
    # CHECK PROFILE VALUES
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — CHECK PROFILE VALUES{RESET}")
    print(f"{'='*66}")
    
    import json
    def get_profile_value(profile, key, default=0):
        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except:
                return default
        if isinstance(profile, dict):
            return profile.get(key, default)
        return default
    
    btts_rates = []
    over_2_5_rates = []
    under_1_5_rates = []
    early_goal_rates = []
    
    for pred in rows:
        offensive = pred.get("offensive_profile") or {}
        defensive = pred.get("defensive_profile") or {}
        
        btts_rate = get_profile_value(offensive, "btts_rate", 0)
        over_2_5_rate = get_profile_value(offensive, "over_2_5_rate", 0)
        under_1_5_rate = get_profile_value(defensive, "under_1_5_rate", 0)
        early_goal_rate = get_profile_value(offensive, "early_goal_rate", 0)
        
        if btts_rate > 0:
            btts_rates.append(btts_rate)
        if over_2_5_rate > 0:
            over_2_5_rates.append(over_2_5_rate)
        if under_1_5_rate > 0:
            under_1_5_rates.append(under_1_5_rate)
        if early_goal_rate > 0:
            early_goal_rates.append(early_goal_rate)
    
    print(f"\nBTTS rates found: {len(btts_rates)}")
    if btts_rates:
        print(f"  Min: {min(btts_rates):.1f}%")
        print(f"  Max: {max(btts_rates):.1f}%")
        print(f"  Avg: {sum(btts_rates)/len(btts_rates):.1f}%")
        print(f"  >= 55%: {sum(1 for r in btts_rates if r >= 55)}")
    
    print(f"\nOver 2.5 rates found: {len(over_2_5_rates)}")
    if over_2_5_rates:
        print(f"  Min: {min(over_2_5_rates):.1f}%")
        print(f"  Max: {max(over_2_5_rates):.1f}%")
        print(f"  Avg: {sum(over_2_5_rates)/len(over_2_5_rates):.1f}%")
        print(f"  >= 55%: {sum(1 for r in over_2_5_rates if r >= 55)}")
    
    print(f"\nUnder 1.5 rates found: {len(under_1_5_rates)}")
    if under_1_5_rates:
        print(f"  Min: {min(under_1_5_rates):.1f}%")
        print(f"  Max: {max(under_1_5_rates):.1f}%")
        print(f"  Avg: {sum(under_1_5_rates)/len(under_1_5_rates):.1f}%")
        print(f"  >= 55%: {sum(1 for r in under_1_5_rates if r >= 55)}")
    
    print(f"\nEarly goal rates found: {len(early_goal_rates)}")
    if early_goal_rates:
        print(f"  Min: {min(early_goal_rates):.1f}%")
        print(f"  Max: {max(early_goal_rates):.1f}%")
        print(f"  Avg: {sum(early_goal_rates)/len(early_goal_rates):.1f}%")
        print(f"  >= 60%: {sum(1 for r in early_goal_rates if r >= 60)}")
    
    # ========================================================================
    # CHECK MARKET REGIMES
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — CHECK MARKET REGIMES{RESET}")
    print(f"{'='*66}")
    
    regimes = {}
    for pred in rows:
        regime = pred.get("market_regime", "UNKNOWN")
        regimes[regime] = regimes.get(regime, 0) + 1
    
    print(f"\nMarket regimes:")
    for regime, count in sorted(regimes.items(), key=lambda x: x[1], reverse=True):
        print(f"  {regime}: {count}")
    
    high_tempo = regimes.get("HIGH_TEMPO", 0)
    chaotic = regimes.get("CHAOTIC", 0)
    open_regime = regimes.get("OPEN", 0)
    late_goal = regimes.get("LATE_GOAL_LEAGUE", 0)
    
    print(f"\nHigh tempo regimes: {high_tempo + chaotic + open_regime + late_goal}")
    
    # ========================================================================
    # SIMULATE SHADOW GENERATION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 5 — SIMULATE SHADOW GENERATION{RESET}")
    print(f"{'='*66}")
    
    shadow_predictions = []
    
    for pred in rows:
        offensive = pred.get("offensive_profile") or {}
        defensive = pred.get("defensive_profile") or {}
        market_regime = pred.get("market_regime", "")
        volatility_score = pred.get("volatility_score", 0) or 0
        chaos_score = pred.get("chaos_score", 0) or 0
        recommended_direction = pred.get("recommended_market_direction", "")
        
        btts_rate = get_profile_value(offensive, "btts_rate", 0)
        over_2_5_rate = get_profile_value(offensive, "over_2_5_rate", 0)
        under_1_5_rate = get_profile_value(defensive, "under_1_5_rate", 0)
        early_goal_rate = get_profile_value(offensive, "early_goal_rate", 0)
        
        # BTTS_YES
        btts_yes_confidence = 0
        if btts_rate >= 55 and over_2_5_rate >= 55:
            btts_yes_confidence = 75
        elif market_regime in ("HIGH_TEMPO", "CHAOTIC", "OPEN", "LATE_GOAL_LEAGUE"):
            btts_yes_confidence = 70
        elif volatility_score >= 60 and chaos_score >= 50:
            btts_yes_confidence = 65
        
        if btts_yes_confidence >= 65:
            shadow_predictions.append({
                "strategy": "SHADOW_BTTS",
                "market": "BTTS_YES",
                "confidence": btts_yes_confidence,
                "btts_rate": btts_rate,
                "over_2_5_rate": over_2_5_rate,
                "market_regime": market_regime
            })
        
        # BTTS_NO
        btts_no_confidence = 0
        if btts_rate <= 35 and under_1_5_rate >= 55:
            btts_no_confidence = 75
        elif market_regime in ("LOW_TEMPO", "DEFENSIVE"):
            btts_no_confidence = 70
        elif recommended_direction == "UNDER":
            btts_no_confidence = 65
        
        if btts_no_confidence >= 65:
            shadow_predictions.append({
                "strategy": "SHADOW_BTTS",
                "market": "BTTS_NO",
                "confidence": btts_no_confidence,
                "btts_rate": btts_rate,
                "under_1_5_rate": under_1_5_rate,
                "market_regime": market_regime
            })
        
        # HOME_TEAM_OVER_0_5
        if early_goal_rate >= 60 or (over_2_5_rate >= 50 and btts_rate >= 50):
            shadow_predictions.append({
                "strategy": "SHADOW_TEAM_GOALS",
                "market": "HOME_TEAM_OVER_0_5",
                "confidence": 75 if early_goal_rate >= 60 else 70,
                "early_goal_rate": early_goal_rate,
                "over_2_5_rate": over_2_5_rate
            })
    
    print(f"\nSimulated shadow predictions: {len(shadow_predictions)}")
    
    btts_yes = [p for p in shadow_predictions if p.get("market") == "BTTS_YES"]
    btts_no = [p for p in shadow_predictions if p.get("market") == "BTTS_NO"]
    ho05 = [p for p in shadow_predictions if p.get("market") == "HOME_TEAM_OVER_0_5"]
    
    print(f"BTTS_YES: {len(btts_yes)}")
    print(f"BTTS_NO: {len(btts_no)}")
    print(f"HOME_TEAM_OVER_0_5: {len(ho05)}")
    
    if shadow_predictions:
        print(f"\nSample shadow predictions:")
        for p in shadow_predictions[:5]:
            print(f"  {p.get('market')}: confidence={p.get('confidence')}%")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
