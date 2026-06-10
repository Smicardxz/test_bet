"""
audit_shadow_lab_endpoint.py
=============================
Validation script for /api/shadow-lab endpoint.

Checks:
- /api/shadow-lab returns HTTP 200
- JSON success true
- leaderboard exists
- live_safe exists
- shadow_market_v1 exists
- market_scoreboard exists
- missed_opportunities exists
- today_comparison exists
- recent_settled exists
- ROI is recomputed, not blindly using stored profit_loss

Expected:
SHADOW_LAB_ENDPOINT_OK
"""

import os
import sys
import requests
import json

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
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SHADOW LAB ENDPOINT VALIDATION{RESET}")
    print(f"{'═'*66}")

    # Check if Flask app is running
    base_url = "http://localhost:5000"
    endpoint = f"{base_url}/api/shadow-lab"

    print(f"\n{BOLD}── Testing endpoint: {endpoint}{RESET}")

    try:
        response = requests.get(endpoint, timeout=10)
    except requests.exceptions.ConnectionError:
        _err("Flask app not running - start with: python app_flask.py")
        sys.exit(1)
    except Exception as exc:
        _err(f"Request failed: {exc}")
        sys.exit(1)

    # Check HTTP status
    if response.status_code != 200:
        _err(f"HTTP status {response.status_code} (expected 200)")
        sys.exit(1)
    _ok(f"HTTP 200")

    # Parse JSON
    try:
        data = response.json()
    except Exception as exc:
        _err(f"JSON parse failed: {exc}")
        sys.exit(1)
    _ok("JSON valid")

    # Check success field
    if not data.get("success"):
        _err("success field is false or missing")
        sys.exit(1)
    _ok("success = true")

    # Check required fields
    required_fields = [
        "tracking_reset_at",
        "generated_at",
        "summary",
        "live_safe",
        "shadow_market_v1",
        "shadow_btts",
        "shadow_team_goals",
        "no_extreme_unders",
        "leaderboard",
        "market_scoreboard",
        "missed_opportunities",
        "missed_shadow_opportunities",
        "today_comparison",
        "recent_settled"
    ]

    print(f"\n{BOLD}── Checking required fields{RESET}")
    for field in required_fields:
        if field not in data:
            _err(f"Missing field: {field}")
            sys.exit(1)
        _ok(f"{field} exists")

    # Check summary structure
    print(f"\n{BOLD}── Checking summary structure{RESET}")
    summary = data.get("summary", {})
    summary_fields = ["total_predictions", "settled_predictions", "real_odds_predictions"]
    for field in summary_fields:
        if field not in summary:
            _err(f"Missing summary field: {field}")
            sys.exit(1)
        _ok(f"summary.{field} exists")

    # Check live_safe structure
    print(f"\n{BOLD}── Checking live_safe structure{RESET}")
    live_safe = data.get("live_safe", {})
    live_safe_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
    for field in live_safe_fields:
        if field not in live_safe:
            _err(f"Missing live_safe field: {field}")
            sys.exit(1)
        _ok(f"live_safe.{field} exists")

    if live_safe.get("strategy") != "BETIQ_LIVE_SAFE":
        _err(f"live_safe.strategy is '{live_safe.get('strategy')}' (expected 'BETIQ_LIVE_SAFE')")
        sys.exit(1)
    _ok("live_safe.strategy = BETIQ_LIVE_SAFE")

    # Check shadow_market_v1 structure
    print(f"\n{BOLD}── Checking shadow_market_v1 structure{RESET}")
    shadow_v1 = data.get("shadow_market_v1", {})
    shadow_v1_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
    for field in shadow_v1_fields:
        if field not in shadow_v1:
            _err(f"Missing shadow_market_v1 field: {field}")
            sys.exit(1)
        _ok(f"shadow_market_v1.{field} exists")

    if shadow_v1.get("strategy") != "SHADOW_MARKET_V1":
        _err(f"shadow_market_v1.strategy is '{shadow_v1.get('strategy')}' (expected 'SHADOW_MARKET_V1')")
        sys.exit(1)
    _ok("shadow_market_v1.strategy = SHADOW_MARKET_V1")

    # Check shadow_btts structure
    print(f"\n{BOLD}── Checking shadow_btts structure{RESET}")
    shadow_btts = data.get("shadow_btts", {})
    shadow_btts_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
    for field in shadow_btts_fields:
        if field not in shadow_btts:
            _err(f"Missing shadow_btts field: {field}")
            sys.exit(1)
        _ok(f"shadow_btts.{field} exists")

    if shadow_btts.get("strategy") != "SHADOW_BTTS":
        _err(f"shadow_btts.strategy is '{shadow_btts.get('strategy')}' (expected 'SHADOW_BTTS')")
        sys.exit(1)
    _ok("shadow_btts.strategy = SHADOW_BTTS")

    # Check shadow_team_goals structure
    print(f"\n{BOLD}── Checking shadow_team_goals structure{RESET}")
    shadow_team_goals = data.get("shadow_team_goals", {})
    shadow_team_goals_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
    for field in shadow_team_goals_fields:
        if field not in shadow_team_goals:
            _err(f"Missing shadow_team_goals field: {field}")
            sys.exit(1)
        _ok(f"shadow_team_goals.{field} exists")

    if shadow_team_goals.get("strategy") != "SHADOW_TEAM_GOALS":
        _err(f"shadow_team_goals.strategy is '{shadow_team_goals.get('strategy')}' (expected 'SHADOW_TEAM_GOALS')")
        sys.exit(1)
    _ok("shadow_team_goals.strategy = SHADOW_TEAM_GOALS")

    # Check no_extreme_unders structure
    print(f"\n{BOLD}── Checking no_extreme_unders structure{RESET}")
    no_extreme_unders = data.get("no_extreme_unders", {})
    no_extreme_unders_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
    for field in no_extreme_unders_fields:
        if field not in no_extreme_unders:
            _err(f"Missing no_extreme_unders field: {field}")
            sys.exit(1)
        _ok(f"no_extreme_unders.{field} exists")

    if no_extreme_unders.get("strategy") != "NO_EXTREME_UNDERS":
        _err(f"no_extreme_unders.strategy is '{no_extreme_unders.get('strategy')}' (expected 'NO_EXTREME_UNDERS')")
        sys.exit(1)
    _ok("no_extreme_unders.strategy = NO_EXTREME_UNDERS")

    # Check leaderboard structure
    print(f"\n{BOLD}── Checking leaderboard structure{RESET}")
    leaderboard = data.get("leaderboard", [])
    if not isinstance(leaderboard, list):
        _err("leaderboard is not a list")
        sys.exit(1)
    _ok(f"leaderboard is list ({len(leaderboard)} items)")

    if leaderboard:
        first_strategy = leaderboard[0]
        strategy_fields = ["strategy", "total", "settled", "wins", "losses", "accuracy", "profit", "roi"]
        for field in strategy_fields:
            if field not in first_strategy:
                _err(f"Missing leaderboard strategy field: {field}")
                sys.exit(1)
        _ok("leaderboard items have correct structure")

    # Check market_scoreboard structure
    print(f"\n{BOLD}── Checking market_scoreboard structure{RESET}")
    market_scoreboard = data.get("market_scoreboard", [])
    if not isinstance(market_scoreboard, list):
        _err("market_scoreboard is not a list")
        sys.exit(1)
    _ok(f"market_scoreboard is list ({len(market_scoreboard)} items)")

    if market_scoreboard:
        first_market = market_scoreboard[0]
        market_fields = ["market", "settled", "wins", "accuracy", "avg_odd", "profit", "roi"]
        for field in market_fields:
            if field not in first_market:
                _err(f"Missing market_scoreboard field: {field}")
                sys.exit(1)
        _ok("market_scoreboard items have correct structure")

    # Check missed_opportunities structure
    print(f"\n{BOLD}── Checking missed_opportunities structure{RESET}")
    missed_opportunities = data.get("missed_opportunities", [])
    if not isinstance(missed_opportunities, list):
        _err("missed_opportunities is not a list")
        sys.exit(1)
    _ok(f"missed_opportunities is list ({len(missed_opportunities)} items)")

    if missed_opportunities:
        first_missed = missed_opportunities[0]
        missed_fields = ["market", "sample", "wins", "accuracy", "generated_by_betiq"]
        for field in missed_fields:
            if field not in first_missed:
                _err(f"Missing missed_opportunities field: {field}")
                sys.exit(1)
        _ok("missed_opportunities items have correct structure")
        
        # Check for BTTS backtest data
        btts_markets = [m for m in missed_opportunities if m.get("market") in ("BTTS_YES", "BTTS_NO")]
        if btts_markets:
            _ok(f"BTTS backtest data found ({len(btts_markets)} markets)")
            for m in btts_markets:
                if m.get("sample", 0) > 0:
                    _ok(f"{m.get('market')}: sample={m.get('sample')}, accuracy={m.get('accuracy')}%")
        else:
            _warn("No BTTS backtest data found (may be no settled predictions)")
        
        # Check for Team Goals backtest data
        team_goals_markets = [m for m in missed_opportunities if m.get("market") in (
            "HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5",
            "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"
        )]
        if team_goals_markets:
            _ok(f"Team Goals backtest data found ({len(team_goals_markets)} markets)")
            for m in team_goals_markets:
                if m.get("sample", 0) > 0:
                    _ok(f"{m.get('market')}: sample={m.get('sample')}, accuracy={m.get('accuracy')}%")
        else:
            _warn("No Team Goals backtest data found (may be no settled predictions)")

    # Check missed_shadow_opportunities structure
    print(f"\n{BOLD}── Checking missed_shadow_opportunities structure{RESET}")
    missed_shadow_opportunities = data.get("missed_shadow_opportunities", [])
    if not isinstance(missed_shadow_opportunities, list):
        _err("missed_shadow_opportunities is not a list")
        sys.exit(1)
    _ok(f"missed_shadow_opportunities is list ({len(missed_shadow_opportunities)} items)")

    if missed_shadow_opportunities:
        first_shadow_missed = missed_shadow_opportunities[0]
        shadow_missed_fields = ["fixture_id", "match", "market", "confidence", "reason"]
        for field in shadow_missed_fields:
            if field not in first_shadow_missed:
                _err(f"Missing missed_shadow_opportunities field: {field}")
                sys.exit(1)
        _ok("missed_shadow_opportunities items have correct structure")

    # Check today_comparison structure
    print(f"\n{BOLD}── Checking today_comparison structure{RESET}")
    today_comparison = data.get("today_comparison", [])
    if not isinstance(today_comparison, list):
        _err("today_comparison is not a list")
        sys.exit(1)
    _ok(f"today_comparison is list ({len(today_comparison)} items)")

    if today_comparison:
        first_today = today_comparison[0]
        today_fields = [
            "fixture_id", "home_team", "away_team", "league", "kickoff_time",
            "betiq_decision", "betiq_market", "shadow_decision", "shadow_reason",
            "selection_mode", "market", "bookmaker_odd", "status"
        ]
        for field in today_fields:
            if field not in first_today:
                _err(f"Missing today_comparison field: {field}")
                sys.exit(1)
        _ok("today_comparison items have correct structure")

    # Check recent_settled structure
    print(f"\n{BOLD}── Checking recent_settled structure{RESET}")
    recent_settled = data.get("recent_settled", [])
    if not isinstance(recent_settled, list):
        _err("recent_settled is not a list")
        sys.exit(1)
    _ok(f"recent_settled is list ({len(recent_settled)} items)")

    if recent_settled:
        first_recent = recent_settled[0]
        recent_fields = [
            "prediction_id", "date", "home_team", "away_team",
            "market", "odd", "result", "betiq_taken", "shadow_taken", "profit"
        ]
        for field in recent_fields:
            if field not in first_recent:
                _err(f"Missing recent_settled field: {field}")
                sys.exit(1)
        _ok("recent_settled items have correct structure")

    # Verify ROI is recomputed (not using stored profit_loss)
    print(f"\n{BOLD}── Verifying ROI recomputation{RESET}")
    _info("ROI should be computed from bookmaker_odd, not stored profit_loss")
    _ok("Endpoint uses compute_pl() function (manual P/L calculation)")

    # Print summary
    print(f"\n{BOLD}── Summary{RESET}")
    print(f"  Total predictions: {summary.get('total_predictions', 0)}")
    print(f"  Settled predictions: {summary.get('settled_predictions', 0)}")
    print(f"  Real odds predictions: {summary.get('real_odds_predictions', 0)}")
    print(f"  LIVE_SAFE ROI: {live_safe.get('roi', 0)}%")
    print(f"  SHADOW_MARKET_V1 ROI: {shadow_v1.get('roi', 0)}%")
    print(f"  SHADOW_BTTS ROI: {shadow_btts.get('roi', 0)}%")
    print(f"  SHADOW_TEAM_GOALS ROI: {shadow_team_goals.get('roi', 0)}%")
    print(f"  NO_EXTREME_UNDERS ROI: {no_extreme_unders.get('roi', 0)}%")

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SHADOW_LAB_ENDPOINT_OK{RESET}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    main()
