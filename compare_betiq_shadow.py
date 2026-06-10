"""
compare_betiq_shadow.py
========================
Compare BetIQ vs Shadow Team Goals on same fixtures.
"""

import os
import sys
import requests

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
    print(f"{BOLD}  BETIQ VS SHADOW TEAM GOALS COMPARISON{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # FETCH SHADOW LAB DATA
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — FETCH DATA{RESET}")
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
    
    # ========================================================================
    # FETCH BETIQ PREDICTIONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — FETCH BETIQ PREDICTIONS{RESET}")
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
                "fixture_id, home_team, away_team, league, kickoff_time"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "fixture_id, home_team, away_team, league, kickoff_time"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, selection_mode, bookmaker_odd, "
            "fixture_id, home_team, away_team, league, kickoff_time"
        ).gte("prediction_date", cutoff)
    
    betiq_predictions = q.execute().data or []
    print(f"BetIQ predictions: {len(betiq_predictions)}")
    
    # ========================================================================
    # GET SHADOW PORTFOLIO
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — GET SHADOW PORTFOLIO{RESET}")
    print(f"{'='*66}")
    
    shadow_portfolio = data.get("shadow_portfolio", [])
    shadow_tg = [p for p in shadow_portfolio if p.get("strategy") == "SHADOW_TEAM_GOALS"]
    print(f"Shadow Team Goals picks: {len(shadow_tg)}")
    
    # ========================================================================
    # MATCH BY FIXTURE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — MATCH BY FIXTURE{RESET}")
    print(f"{'='*66}")
    
    # Index BetIQ by fixture_id
    betiq_by_fixture = {}
    for pred in betiq_predictions:
        fixture_id = pred.get("fixture_id")
        if fixture_id:
            if fixture_id not in betiq_by_fixture:
                betiq_by_fixture[fixture_id] = []
            betiq_by_fixture[fixture_id].append(pred)
    
    # Index Shadow by fixture_id
    shadow_by_fixture = {}
    for pred in shadow_tg:
        fixture_id = pred.get("fixture_id")
        if fixture_id:
            if fixture_id not in shadow_by_fixture:
                shadow_by_fixture[fixture_id] = []
            shadow_by_fixture[fixture_id].append(pred)
    
    # Find overlapping fixtures
    overlapping_fixtures = set(betiq_by_fixture.keys()) & set(shadow_by_fixture.keys())
    print(f"Overlapping fixtures: {len(overlapping_fixtures)}")
    
    # ========================================================================
    # COMPARE RESULTS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 5 — COMPARE RESULTS{RESET}")
    print(f"{'='*66}")
    
    betiq_won_shadow_lost = 0
    betiq_lost_shadow_won = 0
    both_won = 0
    both_lost = 0
    betiq_pending_shadow_settled = 0
    shadow_pending_betiq_settled = 0
    both_pending = 0
    
    comparisons = []
    
    for fixture_id in overlapping_fixtures:
        betiq_preds = betiq_by_fixture[fixture_id]
        shadow_preds = shadow_by_fixture[fixture_id]
        
        # Get BetIQ result (use first prediction if multiple)
        betiq_pred = betiq_preds[0]
        betiq_status = betiq_pred.get("status")
        
        # Get Shadow result (use first prediction if multiple)
        shadow_pred = shadow_preds[0]
        shadow_status = shadow_pred.get("simulated_result")
        
        comparison = {
            "fixture_id": fixture_id,
            "home_team": betiq_pred.get("home_team"),
            "away_team": betiq_pred.get("away_team"),
            "betiq_market": betiq_pred.get("market"),
            "betiq_status": betiq_status,
            "shadow_market": shadow_pred.get("market"),
            "shadow_status": shadow_status
        }
        
        # Compare
        if betiq_status in ("WON", "LOST") and shadow_status in ("WON", "LOST"):
            if betiq_status == "WON" and shadow_status == "LOST":
                betiq_won_shadow_lost += 1
                comparison["outcome"] = "BETIQ_WON_SHADOW_LOST"
            elif betiq_status == "LOST" and shadow_status == "WON":
                betiq_lost_shadow_won += 1
                comparison["outcome"] = "BETIQ_LOST_SHADOW_WON"
            elif betiq_status == "WON" and shadow_status == "WON":
                both_won += 1
                comparison["outcome"] = "BOTH_WON"
            elif betiq_status == "LOST" and shadow_status == "LOST":
                both_lost += 1
                comparison["outcome"] = "BOTH_LOST"
        elif betiq_status in ("WON", "LOST") and shadow_status is None:
            betiq_pending_shadow_settled += 1
            comparison["outcome"] = "BETIQ_SETTLED_SHADOW_PENDING"
        elif betiq_status == "PENDING" and shadow_status in ("WON", "LOST"):
            shadow_pending_betiq_settled += 1
            comparison["outcome"] = "SHADOW_SETTLED_BETIQ_PENDING"
        else:
            both_pending += 1
            comparison["outcome"] = "BOTH_PENDING"
        
        comparisons.append(comparison)
    
    print(f"\nSettled comparisons: {betiq_won_shadow_lost + betiq_lost_shadow_won + both_won + both_lost}")
    print(f"  BetIQ won / Shadow lost: {betiq_won_shadow_lost}")
    print(f"  BetIQ lost / Shadow won: {betiq_lost_shadow_won}")
    print(f"  Both won: {both_won}")
    print(f"  Both lost: {both_lost}")
    
    print(f"\nPending comparisons: {betiq_pending_shadow_settled + shadow_pending_betiq_settled + both_pending}")
    print(f"  BetIQ settled / Shadow pending: {betiq_pending_shadow_settled}")
    print(f"  Shadow settled / BetIQ pending: {shadow_pending_betiq_settled}")
    print(f"  Both pending: {both_pending}")
    
    # ========================================================================
    # CALCULATE NET EDGE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 6 — NET EDGE{RESET}")
    print(f"{'='*66}")
    
    total_settled = betiq_won_shadow_lost + betiq_lost_shadow_won + both_won + both_lost
    
    if total_settled == 0:
        _warn("No settled comparisons")
        return
    
    # Net edge: (BetIQ won - Shadow won) / total
    betiq_wins = betiq_won_shadow_lost + both_won
    shadow_wins = betiq_lost_shadow_won + both_won
    
    betiq_win_rate = betiq_wins / total_settled * 100
    shadow_win_rate = shadow_wins / total_settled * 100
    
    net_edge = shadow_win_rate - betiq_win_rate
    
    print(f"\nTotal settled comparisons: {total_settled}")
    print(f"BetIQ wins: {betiq_wins} ({betiq_win_rate:.1f}%)")
    print(f"Shadow wins: {shadow_wins} ({shadow_win_rate:.1f}%)")
    print(f"\nNet edge (Shadow - BetIQ): {net_edge:+.1f}%")
    
    if net_edge > 0:
        _ok(f"Shadow outperforms BetIQ by {net_edge:.1f}%")
    elif net_edge < 0:
        _err(f"BetIQ outperforms Shadow by {-net_edge:.1f}%")
    else:
        _info("BetIQ and Shadow perform equally")
    
    # ========================================================================
    # SAMPLE COMPARISONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 7 — SAMPLE COMPARISONS{RESET}")
    print(f"{'='*66}")
    
    # Show disagreements
    disagreements = [c for c in comparisons if c["outcome"] in ("BETIQ_WON_SHADOW_LOST", "BETIQ_LOST_SHADOW_WON")]
    
    print(f"\nDisagreements: {len(disagreements)}")
    
    if disagreements:
        print(f"\nSample disagreements:")
        for comp in disagreements[:5]:
            print(f"  {comp['home_team']} vs {comp['away_team']}")
            print(f"    BetIQ: {comp['betiq_market']} - {comp['betiq_status']}")
            print(f"    Shadow: {comp['shadow_market']} - {comp['shadow_status']}")
            print(f"    Outcome: {comp['outcome']}")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
