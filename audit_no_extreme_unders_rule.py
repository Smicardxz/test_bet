"""
audit_no_extreme_unders_rule.py
================================
Audit the NO_EXTREME_UNDERS shadow strategy rule.

Shows before/after stats for the rule fix:
- Total picks before/after
- Settled before/after
- ROI before/after
- Excluded examples

Expected: NO_EXTREME_UNDERS_RULE_OK
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
    print(f"{BOLD}  NO_EXTREME_UNDERS RULE AUDIT{RESET}")
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
    print(f"\n{BOLD}── Fetching POST_RESET predictions{'─'*36}{RESET}")
    try:
        if reset_at:
            if "T" in reset_at:
                q = repo._client.table("predictions").select(
                    "id, market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, created_at, prediction_date, "
                    "home_team, away_team, league"
                ).gte("created_at", reset_at)
            else:
                q = repo._client.table("predictions").select(
                    "id, market, status, selection_mode, bookmaker_odd, "
                    "ev_percentage, created_at, prediction_date, "
                    "home_team, away_team, league"
                ).gte("prediction_date", reset_at)
        else:
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            q = repo._client.table("predictions").select(
                "id, market, status, selection_mode, bookmaker_odd, "
                "ev_percentage, created_at, prediction_date, "
                "home_team, away_team, league"
            ).gte("prediction_date", cutoff)

        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} predictions")

    REAL_ODDS_THRESHOLD = 1.1

    # ── OLD RULE (incorrect) ───────────────────────────────────────────────────
    print(f"\n{BOLD}── OLD RULE (incorrect: startswith('UNDER')){RESET}")
    
    def old_rule(r):
        return (
            r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
            and not (r.get("market", "").startswith("UNDER") and r.get("bookmaker_odd") and r.get("bookmaker_odd") > 4.0)
        )
    
    old_filtered = [r for r in rows if old_rule(r)]
    old_with_odds = [r for r in old_filtered if r.get("bookmaker_odd")]
    old_settled = [r for r in old_with_odds if r.get("status") in ("WON", "LOST")]
    old_wins = [r for r in old_settled if r.get("status") == "WON"]
    old_losses = [r for r in old_settled if r.get("status") == "LOST"]
    
    old_accuracy = len(old_wins) / len(old_settled) * 100 if old_settled else 0
    old_profit = sum(_compute_pl(r.get("status"), r.get("bookmaker_odd")) for r in old_settled)
    old_roi = old_profit / len(old_settled) * 100 if old_settled else 0
    
    print(f"  Total picks: {len(old_filtered)}")
    print(f"  Settled: {len(old_settled)}")
    print(f"  Wins: {len(old_wins)}")
    print(f"  Losses: {len(old_losses)}")
    print(f"  Accuracy: {old_accuracy:.1f}%")
    print(f"  Profit: {old_profit:.2f}u")
    print(f"  ROI: {old_roi:.1f}%")

    # ── NEW RULE (correct) ────────────────────────────────────────────────────
    print(f"\n{BOLD}── NEW RULE (correct: '_UNDER_' in market or startswith('UNDER')){RESET}")
    
    def new_rule(r):
        return (
            r.get("market") not in ("FT_UNDER_1_5", "HT_UNDER_0_5")
            and not (("_UNDER_" in r.get("market", "") or r.get("market", "").startswith("UNDER")) and r.get("bookmaker_odd") and r.get("bookmaker_odd") > 4.0)
        )
    
    new_filtered = [r for r in rows if new_rule(r)]
    new_with_odds = [r for r in new_filtered if r.get("bookmaker_odd")]
    new_settled = [r for r in new_with_odds if r.get("status") in ("WON", "LOST")]
    new_wins = [r for r in new_settled if r.get("status") == "WON"]
    new_losses = [r for r in new_settled if r.get("status") == "LOST"]
    
    new_accuracy = len(new_wins) / len(new_settled) * 100 if new_settled else 0
    new_profit = sum(_compute_pl(r.get("status"), r.get("bookmaker_odd")) for r in new_settled)
    new_roi = new_profit / len(new_settled) * 100 if new_settled else 0
    
    print(f"  Total picks: {len(new_filtered)}")
    print(f"  Settled: {len(new_settled)}")
    print(f"  Wins: {len(new_wins)}")
    print(f"  Losses: {len(new_losses)}")
    print(f"  Accuracy: {new_accuracy:.1f}%")
    print(f"  Profit: {new_profit:.2f}u")
    print(f"  ROI: {new_roi:.1f}%")

    # ── COMPARISON ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}── BEFORE / AFTER COMPARISON{RESET}")
    print(f"  {'Metric':<20}  {'Before':>10}  {'After':>10}  {'Change':>10}")
    print(f"  {'─'*20}  {'─'*10}  {'─'*10}  {'─'*10}")
    print(f"  {'Total picks':<20}  {len(old_filtered):>10}  {len(new_filtered):>10}  {len(new_filtered)-len(old_filtered):>+10}")
    print(f"  {'Settled':<20}  {len(old_settled):>10}  {len(new_settled):>10}  {len(new_settled)-len(old_settled):>+10}")
    print(f"  {'Accuracy':<20}  {old_accuracy:>9.1f}%  {new_accuracy:>9.1f}%  {new_accuracy-old_accuracy:>+9.1f}%")
    print(f"  {'Profit':<20}  {old_profit:>9.2f}u  {new_profit:>9.2f}u  {new_profit-old_profit:>+9.2f}u")
    print(f"  {'ROI':<20}  {old_roi:>9.1f}%  {new_roi:>9.1f}%  {new_roi-old_roi:>+9.1f}%")

    # ── EXCLUDED EXAMPLES ───────────────────────────────────────────────────
    print(f"\n{BOLD}── EXCLUDED EXAMPLES (by new rule but not by old rule){RESET}")
    
    excluded_by_new = [r for r in rows if old_rule(r) and not new_rule(r)]
    
    if excluded_by_new:
        print(f"  Total excluded by new rule: {len(excluded_by_new)}")
        print(f"\n  {'Market':<25}  {'Odd':>6}  {'Status':<8}  {'Home':<20}  {'Away':<20}")
        print(f"  {'─'*25}  {'─'*6}  {'─'*8}  {'─'*20}  {'─'*20}")
        
        for r in excluded_by_new[:20]:
            print(f"  {r.get('market', ''):<25}  {r.get('bookmaker_odd') or 0:>6.2f}  {r.get('status', ''):<8}  {r.get('home_team', ''):<20}  {r.get('away_team', ''):<20}")
        
        if len(excluded_by_new) > 20:
            print(f"  ... and {len(excluded_by_new) - 20} more")
    else:
        _ok("No additional exclusions by new rule")

    # ── UNDER MARKETS IN DATA ────────────────────────────────────────────────
    print(f"\n{BOLD}── UNDER MARKETS IN DATA{RESET}")
    
    under_markets = set()
    for r in rows:
        market = r.get("market", "")
        if "_UNDER_" in market or market.startswith("UNDER"):
            under_markets.add(market)
    
    if under_markets:
        print(f"  Found {len(under_markets)} under markets:")
        for m in sorted(under_markets):
            count = len([r for r in rows if r.get("market") == m])
            print(f"    • {m}: {count} predictions")
    else:
        _warn("No under markets found in data")

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  NO_EXTREME_UNDERS_RULE_OK{RESET}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    main()
