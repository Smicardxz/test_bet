#!/usr/bin/env python3
"""
audit_event_mode.py
==================
PHASE 4: Event Mode Analytics

Comprehensive audit and reporting for international tournaments and friendlies.
Tracks event matches separately from domestic league performance.

Usage:
    python audit_event_mode.py
    python audit_event_mode.py --days 30
    python audit_event_mode.py --event WORLD_CUP
    python audit_event_mode.py --since-reset
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA = "\033[95m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def _color_pl(v: float) -> str:
    c = GREEN if v >= 0 else RED
    return f"{c}{v:+.2f}u{RESET}"


def _color_roi(v: float) -> str:
    c = GREEN if v >= 0 else RED
    return f"{c}{v:+.1f}%{RESET}"


def _get_event_color(event_context: str) -> str:
    """Get color for event context."""
    colors = {
        "DOMESTIC_LEAGUE": CYAN,
        "INTERNATIONAL_FRIENDLY": YELLOW,
        "WORLD_CUP": GREEN,
        "CONTINENTAL_TOURNAMENT": BLUE,
        "YOUTH_TOURNAMENT": MAGENTA,
        "UNKNOWN_EVENT": DIM
    }
    return colors.get(event_context, RESET)


def _parse_reset_at() -> str:
    """Return TRACKING_RESET_AT exactly as set in env."""
    raw = os.environ.get("TRACKING_RESET_AT", "").strip()
    if not raw:
        return ""
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            from datetime import date as _date
            _date.fromisoformat(raw[:10])
        return raw
    except Exception:
        return ""


def get_event_predictions(repo, days: int = 30, since_date: str = None, event_filter: str = None) -> List[Dict]:
    """Get event predictions with detailed breakdown."""
    
    # Build base query
    if since_date:
        cutoff = since_date
        if "T" in cutoff:
            q = repo._client.table("predictions").select(
                "event_context, event_name, event_phase, is_event_match, "
                "status, profit_loss, bookmaker_odd, selection_mode, "
                "market, prediction, confidence, created_at, prediction_date"
            ).gte("created_at", cutoff)
        else:
            q = repo._client.table("predictions").select(
                "event_context, event_name, event_phase, is_event_match, "
                "status, profit_loss, bookmaker_odd, selection_mode, "
                "market, prediction, confidence, created_at, prediction_date"
            ).gte("prediction_date", cutoff)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        q = repo._client.table("predictions").select(
            "event_context, event_name, event_phase, is_event_match, "
            "status, profit_loss, bookmaker_odd, selection_mode, "
            "market, prediction, confidence, created_at, prediction_date"
        ).gte("prediction_date", cutoff)
    
    # Filter by event if specified
    if event_filter:
        q = q.eq("event_context", event_filter)
    
    # Only event matches (exclude domestic leagues unless specifically requested)
    if event_filter != "DOMESTIC_LEAGUE":
        q = q.eq("is_event_match", True)
    
    rows = q.execute().data or []
    return rows


def analyze_event_performance(predictions: List[Dict]) -> Dict[str, Any]:
    """Analyze event performance with comprehensive metrics."""
    
    # Overall metrics
    total_picks = len(predictions)
    settled_picks = [p for p in predictions if p.get("status") in ["WON", "LOST", "VOID"]]
    wins = [p for p in settled_picks if p.get("status") == "WON"]
    losses = [p for p in settled_picks if p.get("status") == "LOST"]
    voids = [p for p in settled_picks if p.get("status") == "VOID"]
    
    # Odds analysis
    with_odds = [p for p in predictions if p.get("bookmaker_odd")]
    settled_with_odds = [p for p in settled_picks if p.get("bookmaker_odd")]
    
    # EV picks (with probability inputs)
    ev_picks = [p for p in predictions if p.get("confidence") is not None]
    
    # LIVE_SAFE picks
    live_safe_picks = [p for p in predictions if p.get("selection_mode") == "LIVE_SAFE"]
    live_safe_settled = [p for p in live_safe_picks if p.get("status") in ["WON", "LOST", "VOID"]]
    
    # Calculate P/L
    total_pl = sum(p.get("profit_loss", 0) for p in settled_picks)
    odds_pl = sum(p.get("profit_loss", 0) for p in settled_with_odds)
    live_safe_pl = sum(p.get("profit_loss", 0) for p in live_safe_settled)
    
    # Calculate ROI
    odds_roi = (odds_pl / len(settled_with_odds) * 100) if settled_with_odds else 0
    live_safe_roi = (live_safe_pl / len(live_safe_settled) * 100) if live_safe_settled else 0
    
    # Accuracy
    accuracy = (len(wins) / len(settled_picks) * 100) if settled_picks else 0
    live_safe_accuracy = (len([p for p in live_safe_settled if p.get("status") == "WON"]) / len(live_safe_settled) * 100) if live_safe_settled else 0
    
    return {
        "total_picks": total_picks,
        "settled": len(settled_picks),
        "wins": len(wins),
        "losses": len(losses),
        "voids": len(voids),
        "accuracy": accuracy,
        "total_pl": total_pl,
        "with_odds": len(with_odds),
        "settled_with_odds": len(settled_with_odds),
        "odds_pl": odds_pl,
        "odds_roi": odds_roi,
        "ev_picks": len(ev_picks),
        "live_safe_picks": len(live_safe_picks),
        "live_safe_settled": len(live_safe_settled),
        "live_safe_pl": live_safe_pl,
        "live_safe_roi": live_safe_roi,
        "live_safe_accuracy": live_safe_accuracy
    }


def breakdown_by_event_context(predictions: List[Dict]) -> Dict[str, Dict]:
    """Break down performance by event context."""
    breakdown = {}
    
    for pred in predictions:
        ctx = pred.get("event_context", "UNKNOWN_EVENT")
        if ctx not in breakdown:
            breakdown[ctx] = {
                "predictions": [],
                "event_names": set()
            }
        breakdown[ctx]["predictions"].append(pred)
        breakdown[ctx]["event_names"].add(pred.get("event_name", "Unknown"))
    
    # Analyze each context
    for ctx, data in breakdown.items():
        data["performance"] = analyze_event_performance(data["predictions"])
        data["event_names"] = list(data["event_names"])
    
    return breakdown


def breakdown_by_market(predictions: List[Dict]) -> Dict[str, Dict]:
    """Break down performance by market."""
    breakdown = {}
    
    for pred in predictions:
        market = pred.get("market", "UNKNOWN")
        if market not in breakdown:
            breakdown[market] = []
        breakdown[market].append(pred)
    
    # Analyze each market
    for market, preds in breakdown.items():
        breakdown[market] = analyze_event_performance(preds)
    
    return breakdown


def breakdown_by_team(predictions: List[Dict]) -> Dict[str, Dict]:
    """Break down performance by team (extracted from prediction field)."""
    breakdown = {}
    
    for pred in predictions:
        # Try to extract team names from prediction or other fields
        pred_text = str(pred.get("prediction", "")).lower()
        
        # Simple team extraction (could be enhanced)
        teams = []
        if " vs " in pred_text:
            teams = [team.strip() for team in pred_text.split(" vs ")]
        elif " v " in pred_text:
            teams = [team.strip() for team in pred_text.split(" v ")]
        
        for team in teams:
            if len(team) > 2:  # Filter out very short strings
                if team not in breakdown:
                    breakdown[team] = []
                breakdown[team].append(pred)
    
    # Analyze each team
    for team, preds in breakdown.items():
        breakdown[team] = analyze_event_performance(preds)
    
    return breakdown


def breakdown_by_event_phase(predictions: List[Dict]) -> Dict[str, Dict]:
    """Break down performance by event phase."""
    breakdown = {}
    
    for pred in predictions:
        phase = pred.get("event_phase", "unknown_phase")
        if phase not in breakdown:
            breakdown[phase] = []
        breakdown[phase].append(pred)
    
    # Analyze each phase
    for phase, preds in breakdown.items():
        breakdown[phase] = analyze_event_performance(preds)
    
    return breakdown


def run_audit(days: int = 30, since_reset: bool = False, event_filter: str = None):
    """Run comprehensive event mode audit."""
    
    reset_at = _parse_reset_at() if since_reset else ""
    title_suffix = f"since {reset_at}" if reset_at else f"last {days} days"
    if event_filter:
        title_suffix += f" [{event_filter}]"
    
    print(f"\n{BOLD}{'═'*80}{RESET}")
    print(f"{BOLD}  EVENT MODE AUDIT — International Tournaments & Friendlies{RESET}")
    print(f"  {CYAN}Period: {title_suffix}{RESET}")
    print(f"{'═'*80}")
    
    # Connect to database
    from app.database.supabase_config import get_supabase_config
    from app.database.supabase_repository import get_repository, reset_repository
    
    reset_repository()
    cfg = get_supabase_config()
    repo = get_repository()
    
    if not cfg.supabase_connected:
        print(f"  {RED}✗ Supabase not connected: {cfg.supabase_error}{RESET}")
        return
    
    print(f"  {GREEN}✓ Supabase connected{RESET}\n")
    
    # Get event predictions
    since_date = reset_at or None
    predictions = get_event_predictions(repo, days=days, since_date=since_date, event_filter=event_filter)
    
    if not predictions:
        print(f"  {YELLOW}⚠ No event predictions found for the specified period.{RESET}")
        return
    
    print(f"  {CYAN}Found {len(predictions)} event predictions{RESET}\n")
    
    # Overall event performance
    print(f"  {BOLD}── OVERALL EVENT PERFORMANCE {'─'*44}{RESET}")
    overall = analyze_event_performance(predictions)
    
    print(f"  Total Picks          : {overall['total_picks']}")
    print(f"  Settled Picks        : {overall['settled']}")
    print(f"  Wins                 : {GREEN}{overall['wins']}{RESET}")
    print(f"  Losses               : {RED}{overall['losses']}{RESET}")
    print(f"  Voids                : {YELLOW}{overall['voids']}{RESET}")
    print(f"  Accuracy             : {overall['accuracy']:.1f}%")
    print(f"  Total P/L            : {_color_pl(overall['total_pl'])}")
    print(f"  Picks with Odds      : {overall['with_odds']}")
    print(f"  Settled with Odds    : {overall['settled_with_odds']}")
    print(f"  Odds ROI             : {_color_roi(overall['odds_roi'])}")
    print(f"  EV Picks             : {overall['ev_picks']}")
    print(f"  LIVE_SAFE Picks      : {overall['live_safe_picks']}")
    print(f"  LIVE_SAFE Settled    : {overall['live_safe_settled']}")
    print(f"  LIVE_SAFE ROI        : {_color_roi(overall['live_safe_roi'])}")
    print(f"  LIVE_SAFE Accuracy   : {overall['live_safe_accuracy']:.1f}%")
    
    # Breakdown by event context
    print(f"\n  {BOLD}── PERFORMANCE BY EVENT CONTEXT {'─'*36}{RESET}")
    context_breakdown = breakdown_by_event_context(predictions)
    
    print(f"  {'Event Context':<25}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
          f"{'Acc':>6}  {'ROI':>7}  {'P/L':>7}")
    print(f"  {'─'*25}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}  {'─'*7}")
    
    for ctx, data in sorted(context_breakdown.items()):
        perf = data["performance"]
        acc_str = f"{perf['accuracy']:.1f}%" if perf['settled'] > 0 else "N/A"
        roi_str = _color_roi(perf['odds_roi']) if perf['settled_with_odds'] > 0 else f"{DIM}N/A{RESET}"
        pl_str = _color_pl(perf['odds_pl'])
        color = _get_event_color(ctx)
        
        print(f"  {color}{ctx:<25}{RESET}  {perf['total_picks']:>5}  {perf['settled']:>7}  "
              f"{perf['wins']:>4}  {acc_str:>6}  {roi_str:>7}  {pl_str:>7}")
    
    # Breakdown by event phase
    print(f"\n  {BOLD}── PERFORMANCE BY EVENT PHASE {'─'*40}{RESET}")
    phase_breakdown = breakdown_by_event_phase(predictions)
    
    print(f"  {'Event Phase':<20}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
          f"{'Acc':>6}  {'ROI':>7}")
    print(f"  {'─'*20}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}")
    
    for phase, perf in sorted(phase_breakdown.items()):
        acc_str = f"{perf['accuracy']:.1f}%" if perf['settled'] > 0 else "N/A"
        roi_str = _color_roi(perf['odds_roi']) if perf['settled_with_odds'] > 0 else f"{DIM}N/A{RESET}"
        
        print(f"  {phase:<20}  {perf['total_picks']:>5}  {perf['settled']:>7}  "
              f"{perf['wins']:>4}  {acc_str:>6}  {roi_str:>7}")
    
    # Top markets (by volume)
    print(f"\n  {BOLD}── TOP MARKETS BY VOLUME {'─'*40}{RESET}")
    market_breakdown = breakdown_by_market(predictions)
    
    # Sort by total picks and show top 10
    top_markets = sorted(market_breakdown.items(), key=lambda x: x[1]["total_picks"], reverse=True)[:10]
    
    print(f"  {'Market':<25}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
          f"{'Acc':>6}  {'ROI':>7}")
    print(f"  {'─'*25}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}")
    
    for market, perf in top_markets:
        acc_str = f"{perf['accuracy']:.1f}%" if perf['settled'] > 0 else "N/A"
        roi_str = _color_roi(perf['odds_roi']) if perf['settled_with_odds'] > 0 else f"{DIM}N/A{RESET}"
        
        print(f"  {market:<25}  {perf['total_picks']:>5}  {perf['settled']:>7}  "
              f"{perf['wins']:>4}  {acc_str:>6}  {roi_str:>7}")
    
    # Top teams (by volume)
    print(f"\n  {BOLD}── TOP TEAMS BY VOLUME {'─'*46}{RESET}")
    team_breakdown = breakdown_by_team(predictions)
    
    # Sort by total picks and show top 10
    top_teams = sorted(team_breakdown.items(), key=lambda x: x[1]["total_picks"], reverse=True)[:10]
    
    print(f"  {'Team':<25}  {'Picks':>5}  {'Settled':>7}  {'Wins':>4}  "
          f"{'Acc':>6}  {'ROI':>7}")
    print(f"  {'─'*25}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*6}  {'─'*7}")
    
    for team, perf in top_teams:
        acc_str = f"{perf['accuracy']:.1f}%" if perf['settled'] > 0 else "N/A"
        roi_str = _color_roi(perf['odds_roi']) if perf['settled_with_odds'] > 0 else f"{DIM}N/A{RESET}"
        
        print(f"  {team:<25}  {perf['total_picks']:>5}  {perf['settled']:>7}  "
              f"{perf['wins']:>4}  {acc_str:>6}  {roi_str:>7}")
    
    # Event names
    print(f"\n  {BOLD}── EVENT NAMES DETECTED {'─'*46}{RESET}")
    event_names = set()
    for pred in predictions:
        event_names.add(pred.get("event_name", "Unknown"))
    
    for name in sorted(event_names):
        count = len([p for p in predictions if p.get("event_name") == name])
        print(f"  • {name}: {count} picks")
    
    print(f"\n{'═'*80}\n")
    
    # Summary
    print(f"  {BOLD}SUMMARY:{RESET}")
    print(f"  • Event predictions processed: {len(predictions)}")
    print(f"  • Event contexts detected: {len(context_breakdown)}")
    print(f"  • Markets analyzed: {len(market_breakdown)}")
    print(f"  • Teams tracked: {len(team_breakdown)}")
    print(f"  • Overall accuracy: {overall['accuracy']:.1f}%")
    print(f"  • Overall ROI (with odds): {_color_roi(overall['odds_roi'])}")
    print(f"  • LIVE_SAFE ROI: {_color_roi(overall['live_safe_roi'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Mode Analytics")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default: 30)")
    parser.add_argument("--since-reset", action="store_true", dest="since_reset", help="Filter from TRACKING_RESET_AT")
    parser.add_argument("--event", type=str, help="Filter by event context (WORLD_CUP, INTERNATIONAL_FRIENDLY, etc.)")
    
    args = parser.parse_args()
    
    try:
        run_audit(days=args.days, since_reset=args.since_reset, event_filter=args.event)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Audit interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}Error during audit: {e}{RESET}")
        import traceback
        traceback.print_exc()
