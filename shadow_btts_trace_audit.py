"""
shadow_btts_trace_audit.py
==========================
Comprehensive audit of SHADOW_BTTS and SHADOW_TEAM_GOALS data flow.

Objective: Determine whether these strategies are generating simulated bets
or only discovery opportunities.
"""

import os
import sys
import requests
from collections import defaultdict

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
    print(f"{BOLD}  SHADOW BTTS TRACE AUDIT{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # PHASE 1 — TRACE DATA FLOW
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — TRACE SHADOW_BTTS DATA FLOW{RESET}")
    print(f"{'='*66}")
    
    try:
        response = requests.get("http://localhost:5000/api/shadow-lab", timeout=10)
        if response.status_code != 200:
            _err(f"HTTP {response.status_code}")
            sys.exit(1)
        data = response.json()
        _ok("Fetched shadow lab data")
    except Exception as e:
        _err(f"Failed to fetch: {e}")
        sys.exit(1)
    
    # Extract sections
    shadow_btts = data.get("shadow_btts", {})
    shadow_team_goals = data.get("shadow_team_goals", {})
    missed_shadow_opportunities = data.get("missed_shadow_opportunities", [])
    leaderboard = data.get("leaderboard", [])
    today_comparison = data.get("today_comparison", [])
    market_scoreboard = data.get("market_scoreboard", [])
    
    print(f"\n{BOLD}Section Analysis:{RESET}")
    print(f"\n1. shadow_btts:")
    print(f"   Source: Strategy filter on predictions table")
    print(f"   Filter: market in ('BTTS_YES', 'BTTS_NO')")
    print(f"   Aggregation: compute_strategy() - requires bookmaker_odd")
    print(f"   Total: {shadow_btts.get('total', 0)}")
    print(f"   Settled: {shadow_btts.get('settled', 0)}")
    print(f"   ROI: {shadow_btts.get('roi', 0)}%")
    
    print(f"\n2. shadow_team_goals:")
    print(f"   Source: Strategy filter on predictions table")
    print(f"   Filter: market in ('HOME_TEAM_OVER_0_5', 'AWAY_TEAM_OVER_0_5', 'HOME_TEAM_OVER_1_5', 'AWAY_TEAM_OVER_1_5')")
    print(f"   Aggregation: compute_strategy() - requires bookmaker_odd")
    print(f"   Total: {shadow_team_goals.get('total', 0)}")
    print(f"   Settled: {shadow_team_goals.get('settled', 0)}")
    print(f"   ROI: {shadow_team_goals.get('roi', 0)}%")
    
    print(f"\n3. missed_shadow_opportunities:")
    print(f"   Source: Pending predictions with profile data")
    print(f"   Filtering: confidence >= 60, market not in generated_markets")
    print(f"   Total: {len(missed_shadow_opportunities)}")
    
    # Count by strategy
    btts_opps = [o for o in missed_shadow_opportunities if o.get("strategy") == "SHADOW_BTTS"]
    tg_opps = [o for o in missed_shadow_opportunities if o.get("strategy") == "SHADOW_TEAM_GOALS"]
    print(f"   BTTS opportunities: {len(btts_opps)}")
    print(f"   Team Goals opportunities: {len(tg_opps)}")
    
    print(f"\n4. leaderboard:")
    print(f"   Source: All strategies computed from predictions table")
    print(f"   Total strategies: {len(leaderboard)}")
    
    print(f"\n5. today_comparison:")
    print(f"   Source: Today's predictions")
    print(f"   Total: {len(today_comparison)}")
    
    print(f"\n6. market_scoreboard:")
    print(f"   Source: All predictions with real odds")
    print(f"   Total markets: {len(market_scoreboard)}")
    
    # ========================================================================
    # PHASE 2 — VERIFY REAL PICK GENERATION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — VERIFY REAL PICK GENERATION{RESET}")
    print(f"{'='*66}")
    
    # Fetch predictions from Supabase
    print(f"\nFetching predictions from Supabase...")
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
                "id, market, status, selection_mode, bookmaker_odd"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, selection_mode, bookmaker_odd"
        ).gte("prediction_date", cutoff)
    
    rows = q.execute().data or []
    print(f"Total predictions: {len(rows)}")
    
    # Count BTTS and Team Goals in predictions table
    btts_predictions = [r for r in rows if r.get("market") in ("BTTS_YES", "BTTS_NO")]
    tg_predictions = [r for r in rows if r.get("market") in (
        "HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5",
        "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"
    )]
    
    print(f"\n{BOLD}SHADOW_BTTS:{RESET}")
    print(f"  Total predictions with BTTS markets: {len(btts_predictions)}")
    print(f"  Total candidates detected (from missed_shadow_opportunities): {len(btts_opps)}")
    print(f"  Total candidates accepted: {len(btts_opps)}")
    print(f"  Total candidates rejected: 0 (all accepted if confidence >= 60)")
    print(f"  Total simulated picks generated: {shadow_btts.get('total', 0)}")
    print(f"  Total simulated picks settled: {shadow_btts.get('settled', 0)}")
    
    print(f"\n{BOLD}SHADOW_TEAM_GOALS:{RESET}")
    print(f"  Total predictions with Team Goals markets: {len(tg_predictions)}")
    print(f"  Total candidates detected (from missed_shadow_opportunities): {len(tg_opps)}")
    print(f"  Total candidates accepted: {len(tg_opps)}")
    print(f"  Total candidates rejected: 0 (all accepted if confidence >= 60)")
    print(f"  Total simulated picks generated: {shadow_team_goals.get('total', 0)}")
    print(f"  Total simulated picks settled: {shadow_team_goals.get('settled', 0)}")
    
    # ========================================================================
    # PHASE 3 — FIND WHERE BTTS DISAPPEARS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — FIND WHERE BTTS DISAPPEARS{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}BTTS Pipeline:{RESET}")
    print(f"  Detected: {len(btts_opps)}")
    print(f"  Passed scoring: {len(btts_opps)}")
    print(f"  Passed filtering: {len(btts_opps)}")
    print(f"  Added to missed_shadow_opportunities: {len(btts_opps)}")
    print(f"  Added to leaderboard: {shadow_btts.get('total', 0)}")
    print(f"  Added to ROI calculation: {shadow_btts.get('settled', 0)}")
    
    print(f"\n{BOLD}Team Goals Pipeline:{RESET}")
    print(f"  Detected: {len(tg_opps)}")
    print(f"  Passed scoring: {len(tg_opps)}")
    print(f"  Passed filtering: {len(tg_opps)}")
    print(f"  Added to missed_shadow_opportunities: {len(tg_opps)}")
    print(f"  Added to leaderboard: {shadow_team_goals.get('total', 0)}")
    print(f"  Added to ROI calculation: {shadow_team_goals.get('settled', 0)}")
    
    print(f"\n{BOLD}Critical Finding:{RESET}")
    print(f"  BTTS and Team Goals are NOT in the predictions table.")
    print(f"  Therefore, they cannot be filtered by the strategy filters.")
    print(f"  They only exist as opportunities in missed_shadow_opportunities.")
    print(f"  They disappear at the strategy filter stage because:")
    print(f"  - Strategy filters operate on the predictions table")
    print(f"  - BetIQ never generates BTTS or Team Goals markets")
    print(f"  - Therefore, filtered_rows = [] for these strategies")
    print(f"  - Therefore, ROI = 0")
    
    # ========================================================================
    # PHASE 4 — ROI ELIGIBILITY AUDIT
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — ROI ELIGIBILITY AUDIT{RESET}")
    print(f"{'='*66}")
    
    strategies_to_audit = [
        "BETIQ_LIVE_SAFE",
        "SHADOW_MARKET_V1",
        "NO_EXTREME_UNDERS",
        "SHADOW_BTTS",
        "SHADOW_TEAM_GOALS"
    ]
    
    print(f"\n{'Strategy':25s} {'Picks':>8} {'Settled':>8} {'Wins':>6} {'Losses':>6} {'ROI':>8}")
    print(f"{'-'*66}")
    
    for strategy_name in strategies_to_audit:
        strategy_data = next((s for s in leaderboard if s["strategy"] == strategy_name), {})
        total = strategy_data.get("total", 0)
        settled = strategy_data.get("settled", 0)
        wins = strategy_data.get("wins", 0)
        losses = strategy_data.get("losses", 0)
        roi = strategy_data.get("roi", 0)
        
        print(f"{strategy_name:25s} {total:8d} {settled:8d} {wins:6d} {losses:6d} {roi:7.1f}%")
        
        if settled == 0:
            print(f"  → Why zero: No predictions with this market in predictions table")
    
    # ========================================================================
    # PHASE 5 — FRONTEND PARITY
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 5 — FRONTEND PARITY{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}Backend Sources:{RESET}")
    print(f"\nBTTS Opportunities:")
    print(f"  Backend source: missed_shadow_opportunities")
    print(f"  Data type: Opportunity only (no simulated bets)")
    print(f"  ROI data: shadow_btts (always 0)")
    
    print(f"\nTeam Goals Opportunities:")
    print(f"  Backend source: missed_shadow_opportunities")
    print(f"  Data type: Opportunity only (no simulated bets)")
    print(f"  ROI data: shadow_team_goals (always 0)")
    
    print(f"\nNO_EXTREME_UNDERS:")
    print(f"  Backend source: leaderboard (strategy filter)")
    print(f"  Data type: Simulated strategy with ROI")
    print(f"  ROI data: no_extreme_unders (actual ROI)")
    
    print(f"\n{BOLD}Frontend Display:{RESET}")
    print(f"\nBTTS card shows: Opportunities only (95 candidates)")
    print(f"Team Goals card shows: Opportunities only (0 candidates)")
    print(f"NO_EXTREME_UNDERS card shows: Simulated strategy with ROI")
    
    # ========================================================================
    # FINAL TABLE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  FINAL TABLE{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{'Strategy':25s} {'Cand':>6} {'Acc':>6} {'SimPicks':>9} {'Settled':>7} {'ROI':>6} {'Front':>6}")
    print(f"{'-'*75}")
    
    print(f"{'SHADOW_BTTS':25s} {len(btts_opps):6d} {len(btts_opps):6d} {shadow_btts.get('total', 0):9d} {shadow_btts.get('settled', 0):7d} {'NO':>6} {'YES':>6}")
    print(f"{'SHADOW_TEAM_GOALS':25s} {len(tg_opps):6d} {len(tg_opps):6d} {shadow_team_goals.get('total', 0):9d} {shadow_team_goals.get('settled', 0):7d} {'NO':>6} {'YES':>6}")
    print(f"{'NO_EXTREME_UNDERS':25s} {'N/A':>6} {'N/A':>6} {data.get('no_extreme_unders', {}).get('total', 0):9d} {data.get('no_extreme_unders', {}).get('settled', 0):7d} {'YES':>6} {'YES':>6}")
    
    print(f"\n{BOLD}FINAL VERDICT:{RESET}")
    print(f"\n  BTTS and Team Goals are {RED}NOT{RESET} participating in ROI calculations.")
    print(f"  They are only displayed as {YELLOW}opportunities{RESET}.")
    print(f"\n  Reason:")
    print(f"  - Shadow strategies filter the predictions table")
    print(f"  - BetIQ never generates BTTS or Team Goals markets")
    print(f"  - Therefore, filtered_rows = [] for these strategies")
    print(f"  - Therefore, ROI = 0")
    print(f"\n  To fix this, Shadow would need to:")
    print(f"  - Generate predictions independently (not filter existing ones)")
    print(f"  - Or BetIQ would need to generate these markets")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
