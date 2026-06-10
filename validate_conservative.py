"""
validate_conservative.py
========================
Validate TEAM_GOALS_CONSERVATIVE results.
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
    print(f"{BOLD}  TEAM_GOALS_CONSERVATIVE VALIDATION{RESET}")
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
    # GET STRATEGY METRICS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — STRATEGY METRICS{RESET}")
    print(f"{'='*66}")
    
    live_safe = data.get("live_safe", {})
    shadow_team_goals = data.get("shadow_team_goals", {})
    team_goals_conservative = data.get("team_goals_conservative", {})
    
    print(f"\n{BOLD}BETIQ_LIVE_SAFE:{RESET}")
    print(f"  Total: {live_safe.get('total', 0)}")
    print(f"  Settled: {live_safe.get('settled', 0)}")
    print(f"  Wins: {live_safe.get('wins', 0)}")
    print(f"  Losses: {live_safe.get('losses', 0)}")
    print(f"  Accuracy: {live_safe.get('accuracy', 0)}%")
    print(f"  Profit: {live_safe.get('profit', 0)}")
    print(f"  ROI: {live_safe.get('roi', 0)}%")
    
    print(f"\n{BOLD}SHADOW_TEAM_GOALS:{RESET}")
    print(f"  Total: {shadow_team_goals.get('total', 0)}")
    print(f"  Settled: {shadow_team_goals.get('settled', 0)}")
    print(f"  Wins: {shadow_team_goals.get('wins', 0)}")
    print(f"  Losses: {shadow_team_goals.get('losses', 0)}")
    print(f"  Accuracy: {shadow_team_goals.get('accuracy', 0)}%")
    print(f"  Profit: {shadow_team_goals.get('profit', 0)}")
    print(f"  ROI: {shadow_team_goals.get('roi', 0)}%")
    
    print(f"\n{BOLD}TEAM_GOALS_CONSERVATIVE:{RESET}")
    print(f"  Total: {team_goals_conservative.get('total', 0)}")
    print(f"  Settled: {team_goals_conservative.get('settled', 0)}")
    print(f"  Wins: {team_goals_conservative.get('wins', 0)}")
    print(f"  Losses: {team_goals_conservative.get('losses', 0)}")
    print(f"  Accuracy: {team_goals_conservative.get('accuracy', 0)}%")
    print(f"  Profit: {team_goals_conservative.get('profit', 0)}")
    print(f"  ROI: {team_goals_conservative.get('roi', 0)}%")
    
    # ========================================================================
    # GET SHADOW PORTFOLIO
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — SHADOW PORTFOLIO BREAKDOWN{RESET}")
    print(f"{'='*66}")
    
    shadow_portfolio = data.get("shadow_portfolio", [])
    conservative_picks = [p for p in shadow_portfolio if p.get("strategy") == "TEAM_GOALS_CONSERVATIVE"]
    
    print(f"\nConservative picks: {len(conservative_picks)}")
    
    # By market
    ho05 = [p for p in conservative_picks if p.get("market") == "HOME_TEAM_OVER_0_5"]
    ho15 = [p for p in conservative_picks if p.get("market") == "HOME_TEAM_OVER_1_5"]
    ao05 = [p for p in conservative_picks if p.get("market") == "AWAY_TEAM_OVER_0_5"]
    ao15 = [p for p in conservative_picks if p.get("market") == "AWAY_TEAM_OVER_1_5"]
    
    print(f"\nBy market:")
    print(f"  HOME_TEAM_OVER_0_5: {len(ho05)}")
    print(f"  HOME_TEAM_OVER_1_5: {len(ho15)}")
    print(f"  AWAY_TEAM_OVER_0_5: {len(ao05)}")
    print(f"  AWAY_TEAM_OVER_1_5: {len(ao15)}")
    
    # ========================================================================
    # COMPARISON
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — STRATEGY COMPARISON{RESET}")
    print(f"{'='*66}")
    
    print(f"\n{BOLD}{'Strategy':<30} {'Total':<8} {'Settled':<8} {'ROI':<8}{RESET}")
    print(f"{'-'*66}")
    print(f"{'BETIQ_LIVE_SAFE':<30} {live_safe.get('total', 0):<8} {live_safe.get('settled', 0):<8} {live_safe.get('roi', 0):<8}%")
    print(f"{'SHADOW_TEAM_GOALS':<30} {shadow_team_goals.get('total', 0):<8} {shadow_team_goals.get('settled', 0):<8} {shadow_team_goals.get('roi', 0):<8}%")
    print(f"{'TEAM_GOALS_CONSERVATIVE':<30} {team_goals_conservative.get('total', 0):<8} {team_goals_conservative.get('settled', 0):<8} {team_goals_conservative.get('roi', 0):<8}%")
    
    # ========================================================================
    # SAMPLE PICKS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 5 — SAMPLE CONSERVATIVE PICKS{RESET}")
    print(f"{'='*66}")
    
    if conservative_picks:
        print(f"\nSample conservative picks:")
        for p in conservative_picks[:5]:
            print(f"  {p.get('market')}: {p.get('home_team')} vs {p.get('away_team')}")
            print(f"    Confidence: {p.get('confidence')}%")
            print(f"    Reason: {p.get('reason')}")
            print(f"    Result: {p.get('simulated_result')}")
            print(f"    P/L: {p.get('simulated_profit_loss')}")
    else:
        _warn("No conservative picks generated")
    
    # ========================================================================
    # CONCLUSION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  CONCLUSION{RESET}")
    print(f"{'='*66}")
    
    conservative_roi = team_goals_conservative.get('roi', 0)
    tg_roi = shadow_team_goals.get('roi', 0)
    betiq_roi = live_safe.get('roi', 0)
    
    print(f"\nGenerated picks: {team_goals_conservative.get('total', 0)}")
    print(f"Settled picks: {team_goals_conservative.get('settled', 0)}")
    print(f"Accuracy: {team_goals_conservative.get('accuracy', 0)}%")
    print(f"ROI: {conservative_roi}%")
    
    print(f"\n{BOLD}ROI Comparison:{RESET}")
    print(f"  BETIQ_LIVE_SAFE: {betiq_roi}%")
    print(f"  SHADOW_TEAM_GOALS: {tg_roi}%")
    print(f"  TEAM_GOALS_CONSERVATIVE: {conservative_roi}%")
    
    if conservative_roi > tg_roi:
        _ok(f"Conservative outperforms standard Team Goals by {conservative_roi - tg_roi:.1f}%")
    elif conservative_roi < tg_roi:
        _warn(f"Conservative underperforms standard Team Goals by {tg_roi - conservative_roi:.1f}%")
    else:
        _info("Conservative matches standard Team Goals")
    
    if conservative_roi > betiq_roi:
        _ok(f"Conservative outperforms BetIQ by {conservative_roi - betiq_roi:.1f}%")
    elif conservative_roi < betiq_roi:
        _warn(f"Conservative underperforms BetIQ by {betiq_roi - conservative_roi:.1f}%")
    else:
        _info("Conservative matches BetIQ")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
