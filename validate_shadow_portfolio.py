"""
validate_shadow_portfolio.py
============================
Validate shadow portfolio generation and ROI participation.
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
    print(f"{BOLD}  SHADOW PORTFOLIO VALIDATION{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # FETCH SHADOW LAB DATA
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — FETCH SHADOW LAB DATA{RESET}")
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
    # VALIDATE SHADOW PORTFOLIO
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — VALIDATE SHADOW PORTFOLIO{RESET}")
    print(f"{'='*66}")
    
    shadow_portfolio = data.get("shadow_portfolio", [])
    print(f"\nShadow portfolio size: {len(shadow_portfolio)}")
    
    if len(shadow_portfolio) == 0:
        _warn("No shadow picks generated")
        print(f"\nPossible reasons:")
        print(f"  1. Profile data not available in predictions")
        print(f"  2. Confidence thresholds not met")
        print(f"  3. No predictions in the time range")
        return
    
    # Count by strategy
    btts_picks = [p for p in shadow_portfolio if p.get("strategy") == "SHADOW_BTTS"]
    tg_picks = [p for p in shadow_portfolio if p.get("strategy") == "SHADOW_TEAM_GOALS"]
    
    print(f"\nSHADOW_BTTS picks: {len(btts_picks)}")
    print(f"SHADOW_TEAM_GOALS picks: {len(tg_picks)}")
    
    # Count by market
    btts_yes = [p for p in btts_picks if p.get("market") == "BTTS_YES"]
    btts_no = [p for p in btts_picks if p.get("market") == "BTTS_NO"]
    
    print(f"\nBTTS_YES: {len(btts_yes)}")
    print(f"BTTS_NO: {len(btts_no)}")
    
    ho05 = [p for p in tg_picks if p.get("market") == "HOME_TEAM_OVER_0_5"]
    ho15 = [p for p in tg_picks if p.get("market") == "HOME_TEAM_OVER_1_5"]
    ao05 = [p for p in tg_picks if p.get("market") == "AWAY_TEAM_OVER_0_5"]
    ao15 = [p for p in tg_picks if p.get("market") == "AWAY_TEAM_OVER_1_5"]
    
    print(f"\nHOME_TEAM_OVER_0_5: {len(ho05)}")
    print(f"HOME_TEAM_OVER_1_5: {len(ho15)}")
    print(f"AWAY_TEAM_OVER_0_5: {len(ao05)}")
    print(f"AWAY_TEAM_OVER_1_5: {len(ao15)}")
    
    # ========================================================================
    # VALIDATE SETTLEMENT
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 3 — VALIDATE SETTLEMENT{RESET}")
    print(f"{'='*66}")
    
    settled = [p for p in shadow_portfolio if p.get("simulated_result") in ("WON", "LOST")]
    pending = [p for p in shadow_portfolio if p.get("simulated_result") is None]
    
    print(f"\nSettled picks: {len(settled)}")
    print(f"Pending picks: {len(pending)}")
    
    if settled:
        wins = [p for p in settled if p.get("simulated_result") == "WON"]
        losses = [p for p in settled if p.get("simulated_result") == "LOST"]
        
        print(f"\nWins: {len(wins)}")
        print(f"Losses: {len(losses)}")
        
        accuracy = len(wins) / len(settled) * 100
        print(f"Accuracy: {accuracy:.1f}%")
        
        profit = sum(p.get("simulated_profit_loss", 0) for p in settled)
        roi = profit / len(settled) * 100
        print(f"Profit: {profit:.2f}")
        print(f"ROI: {roi:.1f}%")
    
    # ========================================================================
    # VALIDATE ROI PARTICIPATION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 4 — VALIDATE ROI PARTICIPATION{RESET}")
    print(f"{'='*66}")
    
    shadow_btts = data.get("shadow_btts", {})
    shadow_team_goals = data.get("shadow_team_goals", {})
    
    print(f"\nSHADOW_BTTS from leaderboard:")
    print(f"  Total: {shadow_btts.get('total', 0)}")
    print(f"  Settled: {shadow_btts.get('settled', 0)}")
    print(f"  Wins: {shadow_btts.get('wins', 0)}")
    print(f"  Losses: {shadow_btts.get('losses', 0)}")
    print(f"  ROI: {shadow_btts.get('roi', 0)}%")
    
    print(f"\nSHADOW_TEAM_GOALS from leaderboard:")
    print(f"  Total: {shadow_team_goals.get('total', 0)}")
    print(f"  Settled: {shadow_team_goals.get('settled', 0)}")
    print(f"  Wins: {shadow_team_goals.get('wins', 0)}")
    print(f"  Losses: {shadow_team_goals.get('losses', 0)}")
    print(f"  ROI: {shadow_team_goals.get('roi', 0)}%")
    
    # Check if shadow portfolio matches leaderboard
    if shadow_btts.get('total') == len(btts_picks):
        _ok("SHADOW_BTTS total matches shadow portfolio")
    else:
        _warn(f"SHADOW_BTTS total mismatch: {shadow_btts.get('total')} vs {len(btts_picks)}")
    
    if shadow_team_goals.get('total') == len(tg_picks):
        _ok("SHADOW_TEAM_GOALS total matches shadow portfolio")
    else:
        _warn(f"SHADOW_TEAM_GOALS total mismatch: {shadow_team_goals.get('total')} vs {len(tg_picks)}")
    
    # ========================================================================
    # SAMPLE PICKS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 5 — SAMPLE PICKS{RESET}")
    print(f"{'='*66}")
    
    if btts_picks:
        print(f"\nSample BTTS picks:")
        for p in btts_picks[:3]:
            print(f"  {p.get('market')}: {p.get('home_team')} vs {p.get('away_team')}")
            print(f"    Confidence: {p.get('confidence')}%")
            print(f"    Reason: {p.get('reason')}")
            print(f"    Result: {p.get('simulated_result')}")
            print(f"    P/L: {p.get('simulated_profit_loss')}")
    
    if tg_picks:
        print(f"\nSample Team Goals picks:")
        for p in tg_picks[:3]:
            print(f"  {p.get('market')}: {p.get('home_team')} vs {p.get('away_team')}")
            print(f"    Confidence: {p.get('confidence')}%")
            print(f"    Reason: {p.get('reason')}")
            print(f"    Result: {p.get('simulated_result')}")
            print(f"    P/L: {p.get('simulated_profit_loss')}")
    
    # ========================================================================
    # FINAL VERDICT
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  FINAL VERDICT{RESET}")
    print(f"{'='*66}")
    
    if shadow_btts.get('total') > 0 or shadow_team_goals.get('total') > 0:
        _ok("Shadow portfolio is participating in ROI calculations")
        print(f"\nGenerated BTTS picks: {len(btts_picks)}")
        print(f"Generated Team Goals picks: {len(tg_picks)}")
        print(f"Entering ROI calculations: YES")
        print(f"\nSHADOW_BTTS ROI: {shadow_btts.get('roi', 0)}%")
        print(f"SHADOW_TEAM_GOALS ROI: {shadow_team_goals.get('roi', 0)}%")
    else:
        _warn("Shadow portfolio not participating in ROI calculations")
        print(f"\nReason: No picks generated or confidence thresholds not met")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
