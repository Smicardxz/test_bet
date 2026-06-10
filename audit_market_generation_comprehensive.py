"""
audit_market_generation_comprehensive.py
=========================================
Comprehensive market generation forensic audit since TRACKING_RESET_AT.

Analyzes:
1. MARKET INVENTORY - rank by frequency, profitability, sample size
2. MARKET COVERAGE ANALYSIS - identify available but never generated markets
3. SIGNAL → MARKET MAPPING - detect signal correctness vs market choice
4. LEAGUE-SPECIFIC MARKET BEHAVIOR - analyze by league
5. RISK/REWARD BIAS DETECTION - analyze odds/probability distribution

Usage:
  python audit_market_generation_comprehensive.py
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
    print(f"{BOLD}  COMPREHENSIVE MARKET GENERATION FORENSIC AUDIT{RESET}")
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

    # ── Fetch POST_RESET predictions with full context ───────────────────────
    print(f"\n{BOLD}── Fetching predictions with full context{'─'*30}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "profit_loss, ev_percentage, created_at, "
                    "home_team, away_team, league"
                ).gte("created_at", reset_at)
            else:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "profit_loss, ev_percentage, prediction_date, "
                    "home_team, away_team, league"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = repo._client.table("predictions").select(
                "market, status, selection_mode, bookmaker_odd, "
                "profit_loss, ev_percentage, prediction_date, "
                "home_team, away_team, league"
            ).gte("prediction_date", cutoff)

        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} predictions")

    if not rows:
        _warn("No predictions found")
        sys.exit(0)

    # ── 1. MARKET INVENTORY ───────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  1. MARKET INVENTORY{RESET}")
    print(f"{'═'*66}")
    
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
        
        if r.get("selection_mode") in ("LIVE_SAFE", "RESEARCH"):
            market_data[market]["selected"] += 1
        
        if r.get("status") in ("WON", "LOST"):
            market_data[market]["settled"] += 1
            if r.get("status") == "WON":
                market_data[market]["wins"] += 1
            market_data[market]["total_pl"] += r.get("profit_loss") or 0
            
            odd = r.get("bookmaker_odd")
            if odd:
                market_data[market]["total_odd"] += odd
                market_data[market]["with_odd_count"] += 1
            
            ev = r.get("ev_percentage")
            if ev is not None:
                market_data[market]["total_ev"] += ev
                market_data[market]["with_ev_count"] += 1
    
    for market, d in market_data.items():
        d["winrate"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0
        d["avg_odd"] = d["total_odd"] / d["with_odd_count"] if d["with_odd_count"] > 0 else 0
        d["roi"] = d["total_pl"] / d["with_odd_count"] * 100 if d["with_odd_count"] > 0 else 0
        d["avg_ev"] = d["total_ev"] / d["with_ev_count"] if d["with_ev_count"] > 0 else 0
    
    # Rank by frequency
    print(f"\n{BOLD}── Ranked by Frequency{RESET}")
    print(f"  {'Market':<25}  {'Gen':>4}  {'Sel':>4}  {'Set':>4}  "
          f"{'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}  {'AvgEV':>6}")
    print(f"  {'─'*25}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*6}  {'─'*6}")
    
    by_freq = sorted(market_data.items(), key=lambda x: x[1]["generated"], reverse=True)
    for market, d in by_freq:
        print(f"  {market:<25}  {d['generated']:>4}  {d['selected']:>4}  {d['settled']:>4}  "
              f"{d['winrate']:>4.1f}%  {d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%  {d['avg_ev']:>5.1f}%")
    
    # Rank by profitability (min 5 settled)
    print(f"\n{BOLD}── Ranked by Profitability (min 5 settled){RESET}")
    profitable = [(m, d) for m, d in market_data.items() if d["settled"] >= 5 and d["with_odd_count"] >= 5]
    profitable.sort(key=lambda x: x[1]["roi"], reverse=True)
    
    print(f"  {'Market':<25}  {'Settled':>7}  {'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}")
    print(f"  {'─'*25}  {'─'*7}  {'─'*5}  {'─'*7}  {'─'*6}")
    for market, d in profitable:
        print(f"  {market:<25}  {d['settled']:>7}  {d['winrate']:>4.1f}%  "
              f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")
    
    # Rank by sample size
    print(f"\n{BOLD}── Ranked by Sample Size{RESET}")
    print(f"  {'Market':<25}  {'Settled':>7}  {'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}")
    print(f"  {'─'*25}  {'─'*7}  {'─'*5}  {'─'*7}  {'─'*6}")
    for market, d in by_freq:
        if d["settled"] > 0:
            print(f"  {market:<25}  {d['settled']:>7}  {d['winrate']:>4.1f}%  "
                  f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")

    # ── 2. MARKET COVERAGE ANALYSIS ───────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  2. MARKET COVERAGE ANALYSIS{RESET}")
    print(f"{'═'*66}")
    
    # Known available markets in codebase
    available_markets = [
        "BTTS_YES", "BTTS_NO",
        "HOME_TEAM_TO_SCORE", "AWAY_TEAM_TO_SCORE",
        "TEAM_OVER_0_5", "TEAM_OVER_1_5", "TEAM_UNDER_1_5",
        "DOUBLE_CHANCE", "DRAW_NO_BET",
        "FIRST_HALF_GOAL", "HT_GOAL",
        "OVER_0_5", "OVER_1_5", "OVER_2_5", "OVER_3_5",
        "UNDER_0_5", "UNDER_1_5", "UNDER_2_5", "UNDER_3_5",
        "HT_OVER_0_5", "HT_OVER_1_5", "HT_UNDER_0_5", "HT_UNDER_1_5",
        "FT_OVER_0_5", "FT_OVER_1_5", "FT_OVER_2_5", "FT_OVER_3_5",
        "FT_UNDER_0_5", "FT_UNDER_1_5", "FT_UNDER_2_5", "FT_UNDER_3_5",
        "OVER_TEAM_0_5", "OVER_TEAM_1_5"
    ]
    
    print(f"\n{BOLD}── Available but Never Generated{RESET}")
    never_generated = [m for m in available_markets if m not in market_data]
    if never_generated:
        for m in sorted(never_generated):
            _warn(f"{m}")
    else:
        _ok("All available markets have been generated")
    
    print(f"\n{BOLD}── Generated but Never Selected{RESET}")
    never_selected = [m for m, d in market_data.items() if d["generated"] > 0 and d["selected"] == 0]
    if never_selected:
        for m in sorted(never_selected, key=lambda x: market_data[x]["generated"], reverse=True):
            d = market_data[m]
            _warn(f"{m} - {d['generated']} generated, 0 selected")
    else:
        _ok("All generated markets have been selected")
    
    print(f"\n{BOLD}── Selected but Never Profitable (min 5 settled){RESET}")
    unprofitable = [m for m, d in market_data.items() if d["settled"] >= 5 and d["with_odd_count"] >= 5 and d["roi"] < 0]
    if unprofitable:
        unprofitable.sort(key=lambda x: market_data[x]["roi"])
        for m in unprofitable:
            d = market_data[m]
            _warn(f"{m} - ROI: {d['roi']:.1f}%")
    else:
        _ok("All selected markets are profitable")

    # ── 3. SIGNAL → MARKET MAPPING ────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  3. SIGNAL → MARKET MAPPING{RESET}")
    print(f"{'═'*66}")
    
    print(f"\n{BOLD}── Signal Correctness vs Market Choice{RESET}")
    _warn("Score data (ft_home, ft_away, ht_home, ht_away) not available in predictions table")
    _info("Signal-to-market mapping analysis requires fixture result data")
    _info("This analysis would need to join with fixtures table to get actual scores")
    
    signal_mismatches = []

    # ── 4. LEAGUE-SPECIFIC MARKET BEHAVIOR ───────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  4. LEAGUE-SPECIFIC MARKET BEHAVIOR{RESET}")
    print(f"{'═'*66}")
    
    # Group by league
    league_market_data: Dict[str, Dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {
        "generated": 0, "settled": 0, "wins": 0, "total_pl": 0.0, "with_odd_count": 0
    }))
    
    for r in rows:
        league = r.get("league") or "UNKNOWN"
        market = r.get("market") or "UNKNOWN"
        league_market_data[league][market]["generated"] += 1
        
        if r.get("status") in ("WON", "LOST"):
            league_market_data[league][market]["settled"] += 1
            if r.get("status") == "WON":
                league_market_data[league][market]["wins"] += 1
            league_market_data[league][market]["total_pl"] += r.get("profit_loss") or 0
            if r.get("bookmaker_odd"):
                league_market_data[league][market]["with_odd_count"] += 1
    
    # Analyze specific leagues
    target_leagues = ["K League 2", "K3 League", "NPL Australia", "Youth", "Friendly", "Women"]
    
    for league in target_leagues:
        matching_leagues = [l for l in league_market_data.keys() if league.lower() in l.lower()]
        if not matching_leagues:
            continue
        
        print(f"\n{BOLD}── {league.upper()}{RESET}")
        
        for lg in matching_leagues:
            market_stats = league_market_data[lg]
            if not market_stats:
                continue
            
            # Calculate ROI per market
            for m, d in market_stats.items():
                d["roi"] = d["total_pl"] / d["with_odd_count"] * 100 if d["with_odd_count"] > 0 else 0
                d["winrate"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0
            
            # Best market
            best_market = max(market_stats.items(), key=lambda x: x[1]["roi"] if x[1]["with_odd_count"] >= 3 else -999)
            worst_market = min(market_stats.items(), key=lambda x: x[1]["roi"] if x[1]["with_odd_count"] >= 3 else 999)
            
            print(f"  League: {lg}")
            print(f"    Best market: {best_market[0]} (ROI: {best_market[1]['roi']:.1f}%, Win%: {best_market[1]['winrate']:.1f}%)")
            print(f"    Worst market: {worst_market[0]} (ROI: {worst_market[1]['roi']:.1f}%, Win%: {worst_market[1]['winrate']:.1f}%)")
            print(f"    Total markets: {len(market_stats)}")

    # ── 5. RISK/REWARD BIAS DETECTION ─────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  5. RISK/REWARD BIAS DETECTION{RESET}")
    print(f"{'═'*66}")
    
    # Analyze odds distribution
    odds_data = []
    for r in rows:
        odd = r.get("bookmaker_odd")
        if odd:
            odds_data.append(odd)
    
    if odds_data:
        odds_data.sort()
        print(f"\n{BOLD}── Odds Distribution{RESET}")
        print(f"  Total picks with odds: {len(odds_data)}")
        print(f"  Min odd: {min(odds_data):.2f}")
        print(f"  Max odd: {max(odds_data):.2f}")
        print(f"  Median odd: {odds_data[len(odds_data)//2]:.2f}")
        print(f"  Mean odd: {sum(odds_data)/len(odds_data):.2f}")
        
        # Odds buckets
        buckets = {
            "1.0-1.5": 0, "1.5-2.0": 0, "2.0-2.5": 0, "2.5-3.0": 0,
            "3.0-4.0": 0, "4.0-5.0": 0, "5.0+": 0
        }
        for odd in odds_data:
            if odd < 1.5:
                buckets["1.0-1.5"] += 1
            elif odd < 2.0:
                buckets["1.5-2.0"] += 1
            elif odd < 2.5:
                buckets["2.0-2.5"] += 1
            elif odd < 3.0:
                buckets["2.5-3.0"] += 1
            elif odd < 4.0:
                buckets["3.0-4.0"] += 1
            elif odd < 5.0:
                buckets["4.0-5.0"] += 1
            else:
                buckets["5.0+"] += 1
        
        print(f"\n  Odds Buckets:")
        for bucket, count in buckets.items():
            pct = count / len(odds_data) * 100
            print(f"    {bucket}: {count} ({pct:.1f}%)")
    
    # High odds analysis (FT_UNDER_1_5 @ 6.0+, HT_UNDER_0_5 @ 3.0+)
    print(f"\n{BOLD}── High Odds Analysis{RESET}")
    
    high_odds_markets = {
        "FT_UNDER_1_5": 6.0,
        "HT_UNDER_0_5": 3.0,
        "FT_UNDER_2_5": 4.0
    }
    
    for market, threshold in high_odds_markets.items():
        if market not in market_data:
            continue
        
        high_odds_picks = []
        for r in rows:
            if r.get("market") == market and r.get("bookmaker_odd"):
                if r.get("bookmaker_odd") >= threshold:
                    high_odds_picks.append(r)
        
        if high_odds_picks:
            settled = [r for r in high_odds_picks if r.get("status") in ("WON", "LOST")]
            wins = [r for r in settled if r.get("status") == "WON"]
            winrate = len(wins) / len(settled) * 100 if settled else 0
            avg_odd = sum(r.get("bookmaker_odd") for r in high_odds_picks) / len(high_odds_picks)
            
            print(f"\n  {market} (odd >= {threshold}):")
            print(f"    Total: {len(high_odds_picks)}")
            print(f"    Settled: {len(settled)}")
            print(f"    Win rate: {winrate:.1f}%")
            print(f"    Avg odd: {avg_odd:.2f}")
    
    # EV vs actual performance
    print(f"\n{BOLD}── EV vs Actual Performance{RESET}")
    
    ev_buckets = {
        "EV < 0": [], "0-10%": [], "10-20%": [], "20-30%": [], "30%+": []
    }
    
    for r in rows:
        if r.get("ev_percentage") is not None and r.get("status") in ("WON", "LOST"):
            ev = r.get("ev_percentage")
            if ev < 0:
                ev_buckets["EV < 0"].append(r)
            elif ev < 10:
                ev_buckets["0-10%"].append(r)
            elif ev < 20:
                ev_buckets["10-20%"].append(r)
            elif ev < 30:
                ev_buckets["20-30%"].append(r)
            else:
                ev_buckets["30%+"].append(r)
    
    print(f"\n  {'EV Bucket':<10}  {'Count':>5}  {'Win%':>5}  {'ROI':>6}")
    print(f"  {'─'*10}  {'─'*5}  {'─'*5}  {'─'*6}")
    
    for bucket, picks in ev_buckets.items():
        if not picks:
            continue
        settled = [r for r in picks if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        winrate = len(wins) / len(settled) * 100 if settled else 0
        
        with_odd = [r for r in settled if r.get("bookmaker_odd")]
        if with_odd:
            pl = sum(r.get("profit_loss") or 0 for r in with_odd)
            roi = pl / len(with_odd) * 100
        else:
            roi = 0
        
        print(f"  {bucket:<10}  {len(picks):>5}  {winrate:>4.1f}%  {roi:>5.1f}%")

    # ── CONCRETE FINDINGS ─────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  CONCRETE FINDINGS{RESET}")
    print(f"{'═'*66}")
    
    findings = []
    
    # Finding 1: Most profitable market
    if profitable:
        best = profitable[0]
        findings.append(f"Most profitable market: {best[0]} with {best[1]['roi']:.1f}% ROI ({best[1]['settled']} settled)")
    
    # Finding 2: Least profitable market
    if profitable:
        worst = profitable[-1]
        findings.append(f"Least profitable market: {worst[0]} with {worst[1]['roi']:.1f}% ROI ({worst[1]['settled']} settled)")
    
    # Finding 3: Missing markets
    if never_generated:
        findings.append(f"{len(never_generated)} available markets never generated: {', '.join(never_generated[:5])}")
    
    # Finding 4: High odds bias
    if "FT_UNDER_1_5" in market_data:
        d = market_data["FT_UNDER_1_5"]
        if d["avg_odd"] > 4.0:
            findings.append(f"FT_UNDER_1_5 shows high odds bias: avg odd {d['avg_odd']:.2f} (ROI: {d['roi']:.1f}%)")
    
    # Finding 5: Signal mismatches
    if signal_mismatches:
        findings.append(f"{len(signal_mismatches)} potential signal-to-market mismatches detected")
    
    # Finding 6: EV vs performance
    if ev_buckets["30%+"]:
        high_ev = ev_buckets["30%+"]
        settled = [r for r in high_ev if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        winrate = len(wins) / len(settled) * 100 if settled else 0
        findings.append(f"High EV picks (30%+): {len(high_ev)} picks, {winrate:.1f}% win rate")
    
    for finding in findings:
        print(f"  • {finding}")

    print(f"\n{BOLD}{'═'*66}{RESET}\n")


if __name__ == "__main__":
    main()
