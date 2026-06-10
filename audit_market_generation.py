"""
audit_market_generation.py
===========================
Market generation forensic audit since TRACKING_RESET_AT.

Analyzes:
- count generated
- count selected
- count settled
- winrate
- avg odd
- ROI
- EV

Compares specific markets:
- BTTS_YES, BTTS_NO
- OVER_TEAM_0_5, OVER_TEAM_1_5
- HT_GOAL
- OVER_2_5, UNDER_2_5, UNDER_1_5

Identifies:
1. markets never generated
2. markets under-generated
3. markets generated but never selected
4. most profitable markets

Usage:
  python audit_market_generation.py
"""

import os
import sys
from datetime import datetime
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


def _parse_reset_at() -> str:
    """Return TRACKING_RESET_AT exactly as set in env (full ISO datetime or date), or ''."""
    raw = os.environ.get("TRACKING_RESET_AT", "").strip()
    if not raw:
        return ""
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))  # validate
        else:
            from datetime import date as _date
            _date.fromisoformat(raw[:10])  # validate
        return raw
    except Exception:
        return ""


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  MARKET GENERATION FORENSIC AUDIT{RESET}")
    print(f"{'═'*66}")

    reset_at = _parse_reset_at()
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — using all predictions")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch POST_RESET predictions ───────────────────────────────────────────
    print(f"\n{BOLD}── Fetching predictions since TRACKING_RESET_AT{'─'*24}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "profit_loss, ev_percentage, created_at"
                ).gte("created_at", reset_at)
            else:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "profit_loss, ev_percentage, prediction_date"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = repo._client.table("predictions").select(
                "market, status, selection_mode, bookmaker_odd, "
                "profit_loss, ev_percentage, prediction_date"
            ).gte("prediction_date", cutoff)

        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} predictions")

    if not rows:
        _warn("No predictions found")
        sys.exit(0)

    # ── Market generation metrics ───────────────────────────────────────────────
    print(f"\n{BOLD}── Market Generation Metrics{RESET}")
    
    # Track metrics per market
    market_data: Dict[str, dict] = defaultdict(lambda: {
        "generated": 0,
        "selected": 0,
        "settled": 0,
        "wins": 0,
        "total_odd": 0.0,
        "with_odd_count": 0,
        "total_pl": 0.0,
        "total_ev": 0.0,
        "with_ev_count": 0
    })
    
    for r in rows:
        market = r.get("market") or "UNKNOWN"
        market_data[market]["generated"] += 1
        
        # Selected = LIVE_SAFE or RESEARCH (not PENDING)
        if r.get("selection_mode") in ("LIVE_SAFE", "RESEARCH"):
            market_data[market]["selected"] += 1
        
        # Settled = WON or LOST
        if r.get("status") in ("WON", "LOST"):
            market_data[market]["settled"] += 1
            if r.get("status") == "WON":
                market_data[market]["wins"] += 1
            
            # P/L
            market_data[market]["total_pl"] += r.get("profit_loss") or 0
            
            # Odd
            odd = r.get("bookmaker_odd")
            if odd:
                market_data[market]["total_odd"] += odd
                market_data[market]["with_odd_count"] += 1
            
            # EV
            ev = r.get("ev_percentage")
            if ev is not None:
                market_data[market]["total_ev"] += ev
                market_data[market]["with_ev_count"] += 1
    
    # Calculate derived metrics
    for market, d in market_data.items():
        d["winrate"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0
        d["avg_odd"] = d["total_odd"] / d["with_odd_count"] if d["with_odd_count"] > 0 else 0
        d["roi"] = d["total_pl"] / d["with_odd_count"] * 100 if d["with_odd_count"] > 0 else 0
        d["avg_ev"] = d["total_ev"] / d["with_ev_count"] if d["with_ev_count"] > 0 else 0
    
    # Print full market breakdown
    print(f"\n  {'Market':<25}  {'Gen':>4}  {'Sel':>4}  {'Set':>4}  "
          f"{'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}  {'AvgEV':>6}")
    print(f"  {'─'*25}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*6}  {'─'*6}")
    
    for market in sorted(market_data.keys(), key=lambda x: market_data[x]["generated"], reverse=True):
        d = market_data[market]
        print(f"  {market:<25}  {d['generated']:>4}  {d['selected']:>4}  {d['settled']:>4}  "
              f"{d['winrate']:>4.1f}%  {d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%  {d['avg_ev']:>5.1f}%")

    # ── Specific market comparison ─────────────────────────────────────────────
    print(f"\n{BOLD}── Specific Market Comparison{RESET}")
    
    target_markets = [
        "BTTS_YES", "BTTS_NO",
        "OVER_TEAM_0_5", "OVER_TEAM_1_5",
        "HT_GOAL",
        "OVER_2_5", "UNDER_2_5", "UNDER_1_5"
    ]
    
    print(f"\n  {'Market':<20}  {'Gen':>4}  {'Sel':>4}  {'Set':>4}  "
          f"{'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}  {'AvgEV':>6}")
    print(f"  {'─'*20}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*6}  {'─'*6}")
    
    for market in target_markets:
        if market in market_data:
            d = market_data[market]
            print(f"  {market:<20}  {d['generated']:>4}  {d['selected']:>4}  {d['settled']:>4}  "
                  f"{d['winrate']:>4.1f}%  {d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%  {d['avg_ev']:>5.1f}%")
        else:
            print(f"  {market:<20}  {'0':>4}  {'0':>4}  {'0':>4}  {'N/A':>5}  {'N/A':>7}  {'N/A':>6}  {'N/A':>6}")

    # ── Identification 1: Markets never generated ─────────────────────────────
    print(f"\n{BOLD}── 1. Markets Never Generated{RESET}")
    
    never_generated = [m for m in target_markets if m not in market_data]
    if never_generated:
        for m in never_generated:
            _warn(f"{m} - never generated")
    else:
        _ok("All target markets have been generated")

    # ── Identification 2: Markets under-generated ───────────────────────────
    print(f"\n{BOLD}── 2. Markets Under-Generated (< 5 picks){RESET}")
    
    under_generated = [m for m, d in market_data.items() if d["generated"] < 5]
    if under_generated:
        for m in sorted(under_generated, key=lambda x: market_data[x]["generated"]):
            d = market_data[m]
            _warn(f"{m} - only {d['generated']} generated")
    else:
        _ok("No markets under-generated (all have >= 5 picks)")

    # ── Identification 3: Markets generated but never selected ────────────────
    print(f"\n{BOLD}── 3. Markets Generated But Never Selected{RESET}")
    
    never_selected = [m for m, d in market_data.items() if d["generated"] > 0 and d["selected"] == 0]
    if never_selected:
        for m in sorted(never_selected, key=lambda x: market_data[x]["generated"], reverse=True):
            d = market_data[m]
            _warn(f"{m} - {d['generated']} generated, 0 selected")
    else:
        _ok("All generated markets have been selected")

    # ── Identification 4: Most profitable markets ────────────────────────────
    print(f"\n{BOLD}── 4. Most Profitable Markets (by ROI, min 5 settled){RESET}")
    
    profitable_markets = [
        (m, d) for m, d in market_data.items() 
        if d["settled"] >= 5 and d["with_odd_count"] >= 5
    ]
    profitable_markets.sort(key=lambda x: x[1]["roi"], reverse=True)
    
    if profitable_markets:
        print(f"\n  {'Market':<25}  {'Settled':>7}  {'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}")
        print(f"  {'─'*25}  {'─'*7}  {'─'*5}  {'─'*7}  {'─'*6}")
        for market, d in profitable_markets[:10]:
            print(f"  {market:<25}  {d['settled']:>7}  {d['winrate']:>4.1f}%  "
                  f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")
    else:
        _warn("No markets with >= 5 settled picks")

    # ── Least profitable markets ────────────────────────────────────────────
    print(f"\n{BOLD}── Least Profitable Markets (by ROI, min 5 settled){RESET}")
    
    if profitable_markets:
        print(f"\n  {'Market':<25}  {'Settled':>7}  {'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}")
        print(f"  {'─'*25}  {'─'*7}  {'─'*5}  {'─'*7}  {'─'*6}")
        for market, d in profitable_markets[-5:]:
            print(f"  {market:<25}  {d['settled']:>7}  {d['winrate']:>4.1f}%  "
                  f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Summary{RESET}")
    print(f"  Total markets analyzed : {len(market_data)}")
    print(f"  Total predictions      : {len(rows)}")
    print(f"  Total selected        : {sum(d['selected'] for d in market_data.values())}")
    print(f"  Total settled         : {sum(d['settled'] for d in market_data.values())}")
    print(f"  Total wins            : {sum(d['wins'] for d in market_data.values())}")
    
    overall_pl = sum(d['total_pl'] for d in market_data.values())
    overall_settled_with_odd = sum(d['with_odd_count'] for d in market_data.values())
    overall_roi = overall_pl / overall_settled_with_odd * 100 if overall_settled_with_odd > 0 else 0
    print(f"  Overall P/L           : {overall_pl:.2f}u")
    print(f"  Overall ROI           : {overall_roi:.1f}%")

    print(f"\n{BOLD}{'═'*66}{RESET}\n")


if __name__ == "__main__":
    main()
