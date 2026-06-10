"""
audit_shadow_market_strategy.py
================================
Comprehensive shadow strategy + market discovery audit.

READ ONLY - NO DATABASE WRITES - NO MIGRATIONS - NO CONFIG CHANGES

Objective: Gather evidence to answer:
1) Is LIVE_SAFE actually the best strategy?
2) Which shadow strategy would have performed better?
3) Are we over-generating bad markets?
4) Are we completely missing profitable market families?
5) Is EV actually predictive?
6) Are we suffering from market generation bias?

Usage:
  python audit_shadow_market_strategy.py
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


def _compute_pl(status: str, odd: float) -> float:
    """Compute P/L manually: WIN: odd - 1, LOSS: -1, VOID: 0"""
    if status == "WON":
        return odd - 1
    elif status == "LOST":
        return -1.0
    else:
        return 0.0


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  COMPREHENSIVE SHADOW STRATEGY + MARKET DISCOVERY AUDIT{RESET}")
    print(f"{'═'*66}")
    print(f"{YELLOW}READ ONLY - NO DATABASE WRITES - NO MIGRATIONS - NO CONFIG CHANGES{RESET}")

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
    print(f"\n{BOLD}── Fetching POST_RESET predictions{'─'*36}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, created_at, "
                    "home_team, away_team, league"
                ).gte("created_at", reset_at)
            else:
                q = repo._client.table("predictions").select(
                    "market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, prediction_date, "
                    "home_team, away_team, league"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = repo._client.table("predictions").select(
                "market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, prediction_date, "
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

    # ── Fetch fixtures for score data (for missed market opportunities) ───────
    print(f"\n{BOLD}── Fetching fixtures for score data{'─'*33}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                fq = repo._client.table("fixtures").select(
                    "id, home_team, away_team, ft_home, ft_away, ht_home, ht_away"
                ).gte("created_at", reset_at)
            else:
                fq = repo._client.table("fixtures").select(
                    "id, home_team, away_team, ft_home, ft_away, ht_home, ht_away"
                ).gte("fixture_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            fq = repo._client.table("fixtures").select(
                "id, home_team, away_team, ft_home, ft_away, ht_home, ht_away"
            ).gte("fixture_date", cutoff)

        fixtures = fq.execute().data or []
    except Exception as exc:
        _warn(f"Could not fetch fixtures: {exc}")
        fixtures = []

    _info(f"Fetched {len(fixtures)} fixtures")

    # Build fixture lookup
    fixture_lookup = {f["id"]: f for f in fixtures}

    # ── PART 1: STRATEGY COMPARISON ───────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 1: STRATEGY COMPARISON{RESET}")
    print(f"{'═'*66}")

    REAL_ODDS_THRESHOLD = 1.1

    # Define strategy filters
    strategies = {
        "A) BETIQ_LIVE_SAFE": lambda r: r.get("selection_mode") == "LIVE_SAFE",
        "B) ALL_REAL_ODDS": lambda r: r.get("bookmaker_odd") and r.get("bookmaker_odd") >= REAL_ODDS_THRESHOLD,
        "C) NO_TOXIC_MARKETS": lambda r: r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5"),
        "D) PREFERRED_MARKETS": lambda r: r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5"),
        "E) POSITIVE_TIERS": lambda r: False,  # Disabled - tier field not available
        "F) ODDS_CAP_5": lambda r: r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0,
        "G) ODDS_CAP_3": lambda r: r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 3.0,
        "H) EV_0_TO_10": lambda r: r.get("ev_percentage") is not None and 0 <= r.get("ev_percentage") <= 10,
        "I) EV_0_TO_30": lambda r: r.get("ev_percentage") is not None and 0 <= r.get("ev_percentage") <= 30,
        "J) SHADOW_MARKET_V1": lambda r: (
            r.get("bookmaker_odd") and REAL_ODDS_THRESHOLD <= r.get("bookmaker_odd") <= 5.0
            and r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
            and (r.get("ev_percentage") or 0) <= 35
            and r.get("market") in ("HT_OVER_1_5", "HT_OVER_0_5", "FT_OVER_1_5", "FT_UNDER_2_5")
        )
    }

    print(f"\n  {'Strategy':<20}  {'Total':>5}  {'Settled':>7}  {'Wins':>4}  "
          f"{'Loss':>4}  {'Acc%':>5}  {'AvgOdd':>7}  {'Profit':>7}  {'ROI':>6}")
    print(f"  {'─'*20}  {'─'*5}  {'─'*7}  {'─'*4}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*7}  {'─'*6}")

    strategy_results = {}

    for name, filter_fn in strategies.items():
        filtered = [r for r in rows if filter_fn(r)]
        total = len(filtered)
        
        # Only consider picks with odds for ROI calculation
        with_odds = [r for r in filtered if r.get("bookmaker_odd")]
        settled = [r for r in with_odds if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        losses = [r for r in settled if r.get("status") == "LOST"]
        
        accuracy = len(wins) / len(settled) * 100 if settled else 0
        avg_odd = sum(r.get("bookmaker_odd") for r in with_odds) / len(with_odds) if with_odds else 0
        
        # Recompute P/L manually
        profit = sum(_compute_pl(r.get("status"), r.get("bookmaker_odd")) for r in settled)
        roi = profit / len(settled) * 100 if settled else 0
        
        strategy_results[name] = {
            "total": total,
            "settled": len(settled),
            "wins": len(wins),
            "losses": len(losses),
            "accuracy": accuracy,
            "avg_odd": avg_odd,
            "profit": profit,
            "roi": roi
        }
        
        print(f"  {name:<20}  {total:>5}  {len(settled):>7}  {len(wins):>4}  "
              f"{len(losses):>4}  {accuracy:>4.1f}%  {avg_odd:>6.2f}  {profit:>6.2f}u  {roi:>5.1f}%")

    # ── PART 2: MARKET FORENSICS ───────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 2: MARKET FORENSICS{RESET}")
    print(f"{'═'*66}")

    market_data: Dict[str, dict] = defaultdict(lambda: {
        "generated": 0, "settled": 0, "wins": 0, "total_odd": 0.0, "with_odd_count": 0, "profit": 0.0
    })

    for r in rows:
        market = r.get("market") or "UNKNOWN"
        market_data[market]["generated"] += 1
        
        if r.get("bookmaker_odd") and r.get("bookmaker_odd") >= REAL_ODDS_THRESHOLD:
            if r.get("status") in ("WON", "LOST"):
                market_data[market]["settled"] += 1
                if r.get("status") == "WON":
                    market_data[market]["wins"] += 1
                market_data[market]["total_odd"] += r.get("bookmaker_odd")
                market_data[market]["with_odd_count"] += 1
                market_data[market]["profit"] += _compute_pl(r.get("status"), r.get("bookmaker_odd"))

    # Calculate metrics
    for market, d in market_data.items():
        d["accuracy"] = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0
        d["avg_odd"] = d["total_odd"] / d["with_odd_count"] if d["with_odd_count"] > 0 else 0
        d["roi"] = d["profit"] / d["with_odd_count"] * 100 if d["with_odd_count"] > 0 else 0

    print(f"\n  {'Market':<25}  {'Gen':>4}  {'Set':>4}  {'Win':>4}  "
          f"{'Acc%':>5}  {'AvgOdd':>7}  {'Profit':>7}  {'ROI':>6}")
    print(f"  {'─'*25}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*5}  {'─'*7}  {'─'*7}  {'─'*6}")

    for market in sorted(market_data.keys(), key=lambda x: market_data[x]["generated"], reverse=True):
        d = market_data[market]
        print(f"  {market:<25}  {d['generated']:>4}  {d['settled']:>4}  {d['wins']:>4}  "
              f"{d['accuracy']:>4.1f}%  {d['avg_odd']:>6.2f}  {d['profit']:>6.2f}u  {d['roi']:>5.1f}%")

    # Best ROI (min 5 settled)
    print(f"\n{BOLD}── Top 10 Profitable Markets (min 5 settled){RESET}")
    profitable = [(m, d) for m, d in market_data.items() if d["settled"] >= 5]
    profitable.sort(key=lambda x: x[1]["roi"], reverse=True)
    
    print(f"  {'Market':<25}  {'Settled':>7}  {'Win%':>5}  {'AvgOdd':>7}  {'ROI':>6}")
    print(f"  {'─'*25}  {'─'*7}  {'─'*5}  {'─'*7}  {'─'*6}")
    for market, d in profitable[:10]:
        print(f"  {market:<25}  {d['settled']:>7}  {d['accuracy']:>4.1f}%  "
              f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")

    # Worst ROI (min 5 settled)
    print(f"\n{BOLD}── Top 10 Losing Markets (min 5 settled){RESET}")
    for market, d in profitable[-10:]:
        print(f"  {market:<25}  {d['settled']:>7}  {d['accuracy']:>4.1f}%  "
              f"{d['avg_odd']:>6.2f}  {d['roi']:>5.1f}%")

    # ── PART 3: MARKET COVERAGE AUDIT ───────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 3: MARKET COVERAGE AUDIT{RESET}")
    print(f"{'═'*66}")

    available_markets = [
        "BTTS_YES", "BTTS_NO",
        "HOME_TEAM_TO_SCORE", "AWAY_TEAM_TO_SCORE",
        "TEAM_OVER_0_5", "TEAM_OVER_1_5", "TEAM_UNDER_1_5",
        "DOUBLE_CHANCE", "DRAW_NO_BET",
        "FIRST_HALF_GOAL", "HT_GOAL",
        "FT_OVER_0_5", "FT_UNDER_0_5",
        "OVER_0_5", "UNDER_0_5",
        "OVER_TEAM_0_5", "OVER_TEAM_1_5"
    ]

    generated_markets = set(market_data.keys())
    never_generated = [m for m in available_markets if m not in generated_markets]

    print(f"\n{BOLD}── GENERATED MARKETS{RESET}")
    for m in sorted(generated_markets):
        print(f"  • {m}")

    print(f"\n{BOLD}── AVAILABLE BUT NEVER GENERATED{RESET}")
    if never_generated:
        for m in sorted(never_generated):
            _warn(f"  • {m}")
    else:
        _ok("All available markets have been generated")

    # ── PART 4: MISSED MARKET OPPORTUNITY AUDIT ───────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 4: MISSED MARKET OPPORTUNITY AUDIT{RESET}")
    print(f"{'═'*66}")

    if not fixtures:
        _warn("No fixture data available - cannot reconstruct missed market outcomes")
        missed_opportunities = {}
    else:
        # Reconstruct outcomes for missed markets
        missed_markets = [
            "BTTS_YES", "BTTS_NO",
            "HOME_TEAM_TO_SCORE", "AWAY_TEAM_TO_SCORE",
            "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "DOUBLE_CHANCE_12",
            "DRAW_NO_BET_HOME", "DRAW_NO_BET_AWAY",
            "FIRST_HALF_GOAL",
            "OVER_0_5", "OVER_1_5", "OVER_2_5", "OVER_3_5",
            "UNDER_0_5", "UNDER_1_5", "UNDER_2_5", "UNDER_3_5"
        ]

        missed_opportunities: Dict[str, dict] = defaultdict(lambda: {"settled": 0, "wins": 0})

        for fixture in fixtures:
            ft_home = fixture.get("ft_home")
            ft_away = fixture.get("ft_away")
            ht_home = fixture.get("ht_home")
            ht_away = fixture.get("ht_away")

            if ft_home is None or ft_away is None:
                continue

            ft_total = ft_home + ft_away
            ht_total = (ht_home or 0) + (ht_away or 0)

            # Evaluate each missed market
            for market in missed_markets:
                result = None
                if market == "BTTS_YES":
                    result = "WON" if ft_home > 0 and ft_away > 0 else "LOST"
                elif market == "BTTS_NO":
                    result = "WON" if ft_home == 0 or ft_away == 0 else "LOST"
                elif market == "HOME_TEAM_TO_SCORE":
                    result = "WON" if ft_home > 0 else "LOST"
                elif market == "AWAY_TEAM_TO_SCORE":
                    result = "WON" if ft_away > 0 else "LOST"
                elif market == "DOUBLE_CHANCE_1X":
                    result = "WON" if ft_home >= ft_away else "LOST"
                elif market == "DOUBLE_CHANCE_X2":
                    result = "WON" if ft_away >= ft_home else "LOST"
                elif market == "DOUBLE_CHANCE_12":
                    result = "WON" if ft_home != ft_away else "LOST"
                elif market == "DRAW_NO_BET_HOME":
                    result = "WON" if ft_home > ft_away else "LOST"
                elif market == "DRAW_NO_BET_AWAY":
                    result = "WON" if ft_away > ft_home else "LOST"
                elif market == "FIRST_HALF_GOAL":
                    result = "WON" if ht_total > 0 else "LOST"
                elif market == "OVER_0_5":
                    result = "WON" if ft_total >= 1 else "LOST"
                elif market == "OVER_1_5":
                    result = "WON" if ft_total >= 2 else "LOST"
                elif market == "OVER_2_5":
                    result = "WON" if ft_total >= 3 else "LOST"
                elif market == "OVER_3_5":
                    result = "WON" if ft_total >= 4 else "LOST"
                elif market == "UNDER_0_5":
                    result = "WON" if ft_total == 0 else "LOST"
                elif market == "UNDER_1_5":
                    result = "WON" if ft_total <= 1 else "LOST"
                elif market == "UNDER_2_5":
                    result = "WON" if ft_total <= 2 else "LOST"
                elif market == "UNDER_3_5":
                    result = "WON" if ft_total <= 3 else "LOST"

                if result:
                    missed_opportunities[market]["settled"] += 1
                    if result == "WON":
                        missed_opportunities[market]["wins"] += 1

        print(f"\n  {'Market':<25}  {'Settled':>7}  {'Wins':>4}  {'Accuracy':>9}")
        print(f"  {'─'*25}  {'─'*7}  {'─'*4}  {'─'*9}")
        for market in sorted(missed_opportunities.keys()):
            d = missed_opportunities[market]
            acc = d["wins"] / d["settled"] * 100 if d["settled"] > 0 else 0
            print(f"  {market:<25}  {d['settled']:>7}  {d['wins']:>4}  {acc:>8.1f}%")

    # ── PART 5: MISSED OPPORTUNITIES ───────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 5: MISSED OPPORTUNITIES{RESET}")
    print(f"{'═'*66}")

    print(f"\n{BOLD}── Criteria: sample >= 30, accuracy >= 60%, market never generated{RESET}")

    qualified = []
    for market, d in missed_opportunities.items():
        if d["settled"] >= 30:
            acc = d["wins"] / d["settled"] * 100
            if acc >= 60 and market not in generated_markets:
                qualified.append((market, d["settled"], acc))

    qualified.sort(key=lambda x: x[1], reverse=True)

    if qualified:
        print(f"\n  {'Market':<25}  {'Sample':>6}  {'Accuracy':>9}")
        print(f"  {'─'*25}  {'─'*6}  {'─'*9}")
        for market, sample, acc in qualified:
            print(f"  {market:<25}  {sample:>6}  {acc:>8.1f}%")
    else:
        _warn("No missed opportunities meet criteria (sample >= 30, accuracy >= 60%)")

    # ── PART 6: RISK / REWARD BIAS AUDIT ───────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 6: RISK / REWARD BIAS AUDIT{RESET}")
    print(f"{'═'*66}")

    # Odds distribution
    odds_data = [r.get("bookmaker_odd") for r in rows if r.get("bookmaker_odd")]
    if odds_data:
        odds_data.sort()
        print(f"\n{BOLD}── Odds Distribution{RESET}")
        print(f"  Total picks with odds: {len(odds_data)}")
        print(f"  Min odd: {min(odds_data):.2f}")
        print(f"  Median odd: {odds_data[len(odds_data)//2]:.2f}")
        print(f"  Mean odd: {sum(odds_data)/len(odds_data):.2f}")
        print(f"  Max odd: {max(odds_data):.2f}")

        # Percentage of picks at high odds
        total = len(odds_data)
        pct_3 = len([o for o in odds_data if o >= 3]) / total * 100
        pct_5 = len([o for o in odds_data if o >= 5]) / total * 100
        pct_8 = len([o for o in odds_data if o >= 8]) / total * 100

        print(f"\n  Percentage of picks:")
        print(f"    odd >= 3: {pct_3:.1f}%")
        print(f"    odd >= 5: {pct_5:.1f}%")
        print(f"    odd >= 8: {pct_8:.1f}%")

    # ROI by odds bucket
    print(f"\n{BOLD}── ROI by Odds Bucket{RESET}")
    
    odds_buckets = {
        "1.1-2.0": {"settled": 0, "wins": 0, "profit": 0.0},
        "2.0-3.0": {"settled": 0, "wins": 0, "profit": 0.0},
        "3.0-5.0": {"settled": 0, "wins": 0, "profit": 0.0},
        "5.0-8.0": {"settled": 0, "wins": 0, "profit": 0.0},
        "8.0+": {"settled": 0, "wins": 0, "profit": 0.0}
    }

    for r in rows:
        odd = r.get("bookmaker_odd")
        if not odd or odd < REAL_ODDS_THRESHOLD:
            continue
        if r.get("status") not in ("WON", "LOST"):
            continue

        if odd < 2.0:
            bucket = "1.1-2.0"
        elif odd < 3.0:
            bucket = "2.0-3.0"
        elif odd < 5.0:
            bucket = "3.0-5.0"
        elif odd < 8.0:
            bucket = "5.0-8.0"
        else:
            bucket = "8.0+"

        odds_buckets[bucket]["settled"] += 1
        if r.get("status") == "WON":
            odds_buckets[bucket]["wins"] += 1
        odds_buckets[bucket]["profit"] += _compute_pl(r.get("status"), odd)

    print(f"\n  {'Bucket':<10}  {'Settled':>7}  {'Wins':>4}  {'Acc%':>5}  {'ROI':>6}")
    print(f"  {'─'*10}  {'─'*7}  {'─'*4}  {'─'*5}  {'─'*6}")
    for bucket, d in odds_buckets.items():
        if d["settled"] == 0:
            continue
        acc = d["wins"] / d["settled"] * 100
        roi = d["profit"] / d["settled"] * 100
        print(f"  {bucket:<10}  {d['settled']:>7}  {d['wins']:>4}  {acc:>4.1f}%  {roi:>5.1f}%")

    # ── PART 7: EV VALIDATION AUDIT ───────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 7: EV VALIDATION AUDIT{RESET}")
    print(f"{'═'*66}")

    ev_buckets = {
        "0-10": {"settled": 0, "wins": 0, "profit": 0.0},
        "10-20": {"settled": 0, "wins": 0, "profit": 0.0},
        "20-30": {"settled": 0, "wins": 0, "profit": 0.0},
        "30-40": {"settled": 0, "wins": 0, "profit": 0.0},
        "40+": {"settled": 0, "wins": 0, "profit": 0.0}
    }

    for r in rows:
        ev = r.get("ev_percentage")
        if ev is None:
            continue
        if not r.get("bookmaker_odd") or r.get("bookmaker_odd") < REAL_ODDS_THRESHOLD:
            continue
        if r.get("status") not in ("WON", "LOST"):
            continue

        if ev < 10:
            bucket = "0-10"
        elif ev < 20:
            bucket = "10-20"
        elif ev < 30:
            bucket = "20-30"
        elif ev < 40:
            bucket = "30-40"
        else:
            bucket = "40+"

        ev_buckets[bucket]["settled"] += 1
        if r.get("status") == "WON":
            ev_buckets[bucket]["wins"] += 1
        ev_buckets[bucket]["profit"] += _compute_pl(r.get("status"), r.get("bookmaker_odd"))

    print(f"\n  {'EV Bucket':<10}  {'Settled':>7}  {'Wins':>4}  {'Acc%':>5}  {'ROI':>6}")
    print(f"  {'─'*10}  {'─'*7}  {'─'*4}  {'─'*5}  {'─'*6}")
    for bucket, d in ev_buckets.items():
        if d["settled"] == 0:
            continue
        acc = d["wins"] / d["settled"] * 100
        roi = d["profit"] / d["settled"] * 100
        print(f"  {bucket:<10}  {d['settled']:>7}  {d['wins']:>4}  {acc:>4.1f}%  {roi:>5.1f}%")

    # ── PART 8: FINAL VERDICT ─────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  PART 8: FINAL VERDICT{RESET}")
    print(f"{'═'*66}")

    live_safe = strategy_results.get("A) BETIQ_LIVE_SAFE", {})
    shadow_v1 = strategy_results.get("J) SHADOW_MARKET_V1", {})

    print(f"\n{BOLD}── BETIQ_LIVE_SAFE vs SHADOW_MARKET_V1{RESET}")
    print(f"\n  {'Strategy':<20}  {'Settled':>7}  {'Acc%':>5}  {'ROI':>6}")
    print(f"  {'─'*20}  {'─'*7}  {'─'*5}  {'─'*6}")
    print(f"  {'BETIQ_LIVE_SAFE':<20}  {live_safe.get('settled', 0):>7}  {live_safe.get('accuracy', 0):>4.1f}%  {live_safe.get('roi', 0):>5.1f}%")
    print(f"  {'SHADOW_MARKET_V1':<20}  {shadow_v1.get('settled', 0):>7}  {shadow_v1.get('accuracy', 0):>4.1f}%  {shadow_v1.get('roi', 0):>5.1f}%")

    if shadow_v1.get("settled", 0) < 20:
        print(f"\n{YELLOW}INSUFFICIENT_SAMPLE{RESET}")
        _warn("SHADOW_MARKET_V1 has < 20 settled picks - cannot make definitive conclusion")
    else:
        if shadow_v1.get("roi", 0) > live_safe.get("roi", 0):
            print(f"\n{GREEN}SHADOW_MARKET_V1 outperforms BETIQ_LIVE_SAFE{RESET}")
            _ok(f"SHADOW_MARKET_V1 ROI: {shadow_v1.get('roi', 0):.1f}% vs LIVE_SAFE ROI: {live_safe.get('roi', 0):.1f}%")
        else:
            print(f"\n{YELLOW}BETIQ_LIVE_SAFE outperforms SHADOW_MARKET_V1{RESET}")
            _warn(f"SHADOW_MARKET_V1 ROI: {shadow_v1.get('roi', 0):.1f}% vs LIVE_SAFE ROI: {live_safe.get('roi', 0):.1f}%")

    print(f"\n{BOLD}STATUS:{RESET}")
    print(f"  {GREEN}SHADOW_MARKET_AUDIT_OK{RESET}")
    print(f"\n{BOLD}{'═'*66}{RESET}\n")
    print(f"{YELLOW}IMPORTANT: This audit exists only to collect evidence.{RESET}")
    print(f"{YELLOW}Do NOT recommend production changes.{RESET}")
    print(f"{YELLOW}Do NOT tune thresholds.{RESET}")
    print(f"{YELLOW}Do NOT modify market generation.{RESET}")
    print(f"{YELLOW}Do NOT modify EV.{RESET}")


if __name__ == "__main__":
    main()
