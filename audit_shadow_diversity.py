"""
audit_shadow_diversity.py
=========================
Audit shadow strategy diversity and market distribution.

Analyzes:
1. Market distribution per strategy
2. Unique markets coverage ratio
3. Candidate generation vs selection
4. Top rejection reasons
5. Entropy/diversity score

Goal: Determine if Shadow is genuinely exploring new market spaces
or simply replacing UNDER bias with BTTS bias.
"""

import os
import sys
import math
from collections import defaultdict, Counter
from datetime import datetime

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


def compute_entropy(distribution):
    """Compute Shannon entropy of market distribution."""
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    
    entropy = 0.0
    for count in distribution.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    return entropy


def compute_max_entropy(num_categories):
    """Maximum possible entropy for given number of categories."""
    if num_categories <= 1:
        return 0.0
    return math.log2(num_categories)


def main():
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  SHADOW DIVERSITY AUDIT{RESET}")
    print(f"{'='*66}")
    
    # Fetch shadow lab data
    print(f"\n{BOLD}── Fetching Shadow Lab data{RESET}")
    
    import requests
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
    
    # Get shadow strategies
    shadow_strategies = {
        "SHADOW_MARKET_V1": data.get("shadow_market_v1", {}),
        "SHADOW_BTTS": data.get("shadow_btts", {}),
        "SHADOW_TEAM_GOALS": data.get("shadow_team_goals", {}),
        "NO_EXTREME_UNDERS": data.get("no_extreme_unders", {})
    }
    
    # Get missed shadow opportunities (candidates)
    missed_shadow = data.get("missed_shadow_opportunities", [])
    
    # Get market scoreboard (actual BetIQ markets)
    market_scoreboard = data.get("market_scoreboard", [])
    
    # Get all predictions for detailed analysis
    print(f"\n{BOLD}── Fetching detailed prediction data{RESET}")
    
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
                "home_team, away_team, league, fixture_id"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, created_at, prediction_date, "
                "home_team, away_team, league, fixture_id"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, selection_mode, bookmaker_odd, "
            "ev_percentage, created_at, prediction_date, "
            "home_team, away_team, league, fixture_id"
        ).gte("prediction_date", cutoff)
    
    rows = q.execute().data or []
    _info(f"Total predictions: {len(rows)}")
    
    # Define shadow strategy filters
    REAL_ODDS_THRESHOLD = 1.1
    
    shadow_filters = {
        "SHADOW_MARKET_V1": lambda r: (
            r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0
            and r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
            and (r.get("ev_percentage") or 0) <= 35
            and r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5")
        ),
        "SHADOW_BTTS": lambda r: r.get("market") in ("BTTS_YES", "BTTS_NO"),
        "SHADOW_TEAM_GOALS": lambda r: r.get("market") in (
            "HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5",
            "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"
        ),
        "NO_EXTREME_UNDERS": lambda r: (
            r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
            and not (("_UNDER_" in r.get("market", "") or r.get("market", "").startswith("UNDER")) and r.get("bookmaker_odd") and r.get("bookmaker_odd") > 4.0)
        )
    }
    
    # Apply shadow filters to get actual selections
    shadow_selections = {}
    for strategy, filter_fn in shadow_filters.items():
        shadow_selections[strategy] = [r for r in rows if filter_fn(r)]
    
    # ========================================================================
    # 1. MARKET DISTRIBUTION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  1. MARKET DISTRIBUTION PER STRATEGY{RESET}")
    print(f"{'='*66}")
    
    for strategy, selections in shadow_selections.items():
        print(f"\n{BOLD}{strategy}{RESET}")
        print(f"  Total selections: {len(selections)}")
        
        if not selections:
            _warn("  No selections")
            continue
        
        # Count market distribution
        market_counts = Counter(r.get("market") for r in selections)
        total = len(selections)
        
        # Sort by percentage
        sorted_markets = sorted(market_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n  Market distribution:")
        for market, count in sorted_markets:
            pct = count / total * 100
            bar = "█" * int(pct / 2)
            print(f"    {market:25s} {count:4d} ({pct:5.1f}%) {bar}")
        
        # Compute entropy
        distribution = dict(market_counts)
        entropy = compute_entropy(distribution)
        max_entropy = compute_max_entropy(len(distribution))
        diversity_score = (entropy / max_entropy * 100) if max_entropy > 0 else 0
        
        print(f"\n  Diversity metrics:")
        print(f"    Unique markets: {len(distribution)}")
        print(f"    Entropy: {entropy:.3f} / {max_entropy:.3f}")
        print(f"    Diversity score: {diversity_score:.1f}%")
    
    # ========================================================================
    # 2. UNIQUE MARKETS COVERAGE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  2. UNIQUE MARKETS COVERAGE{RESET}")
    print(f"{'='*66}")
    
    # All markets BetIQ actually uses
    betiq_markets = set(m.get("market") for m in market_scoreboard)
    print(f"\nBetIQ markets used: {len(betiq_markets)}")
    
    # Shadow markets actually selected
    shadow_markets = set()
    for selections in shadow_selections.values():
        shadow_markets.update(r.get("market") for r in selections)
    
    print(f"Shadow markets selected: {len(shadow_markets)}")
    
    # Markets available in shadow candidates
    candidate_markets = set(c.get("market") for c in missed_shadow)
    print(f"Shadow candidate markets: {len(candidate_markets)}")
    
    # Coverage ratios
    if len(betiq_markets) > 0:
        shadow_coverage = len(shadow_markets) / len(betiq_markets) * 100
        print(f"\nShadow vs BetIQ coverage: {shadow_coverage:.1f}%")
    
    if len(candidate_markets) > 0:
        selection_coverage = len(shadow_markets) / len(candidate_markets) * 100
        print(f"Selection vs candidate coverage: {selection_coverage:.1f}%")
    
    # Show which markets are in candidates but not selected
    unused_candidates = candidate_markets - shadow_markets
    if unused_candidates:
        print(f"\nMarkets in candidates but not selected:")
        for market in sorted(unused_candidates):
            count = sum(1 for c in missed_shadow if c.get("market") == market)
            print(f"  {market}: {count} candidates (0 selected)")
    
    # ========================================================================
    # 3. CANDIDATE GENERATION VS SELECTION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  3. CANDIDATE GENERATION VS SELECTION{RESET}")
    print(f"{'='*66}")
    
    # Count candidates by market
    candidate_counts = Counter(c.get("market") for c in missed_shadow)
    
    # Count selections by market
    selection_counts = {}
    for strategy, selections in shadow_selections.items():
        for r in selections:
            market = r.get("market")
            selection_counts[market] = selection_counts.get(market, 0) + 1
    
    # Compare
    all_markets = sorted(set(candidate_counts.keys()) | set(selection_counts.keys()))
    
    print(f"\n{'Market':30s} {'Generated':>10} {'Selected':>10} {'Ratio':>10}")
    print(f"{'-'*66}")
    
    for market in all_markets:
        generated = candidate_counts.get(market, 0)
        selected = selection_counts.get(market, 0)
        ratio = (selected / generated * 100) if generated > 0 else 0
        print(f"{market:30s} {generated:10d} {selected:10d} {ratio:9.1f}%")
    
    # ========================================================================
    # 4. TOP REJECTION REASONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  4. TOP REJECTION REASONS{RESET}")
    print(f"{'='*66}")
    
    # Analyze why candidates are not selected
    # Candidates are in missed_shadow but not in shadow_selections
    
    rejection_reasons = defaultdict(int)
    
    # For each candidate market, check if it would pass shadow filters
    for candidate in missed_shadow:
        market = candidate.get("market")
        confidence = candidate.get("confidence", 0)
        reason = candidate.get("reason", "")
        
        # Check if this market exists in actual predictions
        market_in_predictions = any(r.get("market") == market for r in rows)
        
        if not market_in_predictions:
            rejection_reasons["Market not generated by BetIQ"] += 1
        elif confidence < 60:
            rejection_reasons[f"Low confidence ({confidence}%)"] += 1
        else:
            rejection_reasons[reason] += 1
    
    print(f"\nRejection reasons:")
    sorted_reasons = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)
    for reason, count in sorted_reasons:
        pct = count / len(missed_shadow) * 100 if missed_shadow else 0
        print(f"  {reason}: {count} ({pct:.1f}%)")
    
    # ========================================================================
    # 5. ENTROPY / DIVERSITY SCORE RANKING
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  5. DIVERSITY SCORE RANKING{RESET}")
    print(f"{'='*66}")
    
    diversity_scores = []
    
    for strategy, selections in shadow_selections.items():
        if not selections:
            continue
        
        market_counts = Counter(r.get("market") for r in selections)
        distribution = dict(market_counts)
        entropy = compute_entropy(distribution)
        max_entropy = compute_max_entropy(len(distribution))
        diversity_score = (entropy / max_entropy * 100) if max_entropy > 0 else 0
        
        diversity_scores.append({
            "strategy": strategy,
            "total": len(selections),
            "unique_markets": len(distribution),
            "entropy": entropy,
            "max_entropy": max_entropy,
            "diversity_score": diversity_score
        })
    
    # Sort by diversity score
    diversity_scores.sort(key=lambda x: x["diversity_score"], reverse=True)
    
    print(f"\n{'Strategy':20s} {'Total':>8} {'Unique':>8} {'Entropy':>10} {'Diversity':>10}")
    print(f"{'-'*66}")
    
    for item in diversity_scores:
        print(f"{item['strategy']:20s} {item['total']:8d} {item['unique_markets']:8d} "
              f"{item['entropy']:10.3f} {item['diversity_score']:9.1f}%")
    
    # ========================================================================
    # 6. MARKET FAMILY ANALYSIS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  6. MARKET FAMILY DOMINANCE{RESET}")
    print(f"{'='*66}")
    
    # Group markets by family
    market_families = {
        "BTTS": ["BTTS_YES", "BTTS_NO"],
        "TEAM_GOALS": ["HOME_TEAM_OVER_0_5", "AWAY_TEAM_OVER_0_5", "HOME_TEAM_OVER_1_5", "AWAY_TEAM_OVER_1_5"],
        "OVER_UNDER": ["FT_OVER_1_5", "FT_UNDER_2_5", "HT_OVER_1_5", "HT_OVER_0_5"],
        "UNDER": ["FT_UNDER_1_5", "HT_UNDER_0_5", "FT_UNDER_2_5", "HT_UNDER_1_5", "UNDER_1_5", "UNDER_2_5", "UNDER_3_5"],
        "DOUBLE_CHANCE": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "DOUBLE_CHANCE_12"],
        "DRAW_NO_BET": ["DRAW_NO_BET_HOME", "DRAW_NO_BET_AWAY"]
    }
    
    # Count family distribution across all shadow strategies
    family_counts = defaultdict(int)
    total_shadow = sum(len(s) for s in shadow_selections.values())
    
    for selections in shadow_selections.values():
        for r in selections:
            market = r.get("market")
            for family, markets in market_families.items():
                if market in markets:
                    family_counts[family] += 1
                    break
    
    print(f"\nMarket family distribution (all shadow strategies):")
    print(f"Total shadow selections: {total_shadow}")
    print(f"\n{'Family':20s} {'Count':>10} {'Percentage':>12}")
    print(f"{'-'*66}")
    
    for family in sorted(family_counts.keys(), key=lambda x: family_counts[x], reverse=True):
        count = family_counts[family]
        pct = count / total_shadow * 100 if total_shadow > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"{family:20s} {count:10d} {pct:11.1f}% {bar}")
    
    # ========================================================================
    # CONCLUSION
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  CONCLUSION{RESET}")
    print(f"{'='*66}")
    
    # Check if BTTS bias exists
    btts_count = family_counts.get("BTTS", 0)
    btts_pct = btts_count / total_shadow * 100 if total_shadow > 0 else 0
    
    if btts_pct > 40:
        _warn(f"BTTS bias detected: {btts_pct:.1f}% of shadow selections")
    elif btts_pct > 25:
        _info(f"Moderate BTTS presence: {btts_pct:.1f}% of shadow selections")
    else:
        _ok(f"Low BTTS bias: {btts_pct:.1f}% of shadow selections")
    
    # Check diversity
    if diversity_scores:
        avg_diversity = sum(s["diversity_score"] for s in diversity_scores) / len(diversity_scores)
        if avg_diversity > 70:
            _ok(f"High diversity: {avg_diversity:.1f}% average")
        elif avg_diversity > 40:
            _info(f"Moderate diversity: {avg_diversity:.1f}% average")
        else:
            _warn(f"Low diversity: {avg_diversity:.1f}% average")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
