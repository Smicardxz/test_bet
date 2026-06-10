"""
backfill_selection_mode.py
==========================
Retroactively applies SAFE_SELECTION_MODE rules to all POST_RESET predictions.

Updates selection_mode and selection_reason for existing predictions based on:
- tier in ["S_TIER", "B_TIER"]
- odds_source in ["API_FOOTBALL", "ODDS_API"]
- bookmaker_odd: 1.20 ≤ odd ≤ 2.50
- ev_percentage: 3 ≤ ev ≤ 25
- market_probability: 0.50 ≤ prob ≤ 0.80
- market NOT IN ["FT_UNDER_1_5", "FT_OVER_3_5"]

Usage:
  python backfill_selection_mode.py

WARNING: This will UPDATE existing rows in Supabase.
"""

import os
import sys
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


def _apply_since_filter(query, since_date: str):
    """Apply date/datetime filter to a Supabase query builder."""
    if not since_date:
        return query
    if "T" in since_date:
        return query.gte("created_at", since_date)
    return query.gte("prediction_date", since_date)


def _evaluate_safe_mode(row: dict) -> tuple:
    """
    Evaluate if a prediction passes SAFE_SELECTION_MODE criteria.
    Returns (selection_mode, selection_reason).
    """
    tier_val = (row.get("statistical_tier") or row.get("ev_tier") or "NO_VALUE").upper()
    odds_src = row.get("odds_source")
    bookmaker_odd = row.get("bookmaker_odd")
    market_prob = row.get("market_probability")
    ev_pct = row.get("ev_percentage") or row.get("ev_percent") or 0
    market = row.get("market", "")

    reasons = []

    if tier_val not in ("S_TIER", "B_TIER"):
        reasons.append("RESEARCH_TOXIC_TIER")
    if odds_src not in ("API_FOOTBALL", "ODDS_API"):
        reasons.append("RESEARCH_NO_ODDS_SOURCE")
    if bookmaker_odd is None or bookmaker_odd < 1.20:
        reasons.append("RESEARCH_ODD_TOO_LOW")
    if bookmaker_odd and bookmaker_odd > 2.50:
        reasons.append("RESEARCH_ODD_TOO_HIGH")
    if ev_pct is None or ev_pct < 3:
        reasons.append("RESEARCH_EV_TOO_LOW")
    if ev_pct and ev_pct > 25:
        reasons.append("RESEARCH_EV_TOO_HIGH")
    if market_prob is None or market_prob < 0.50:
        reasons.append("RESEARCH_PROB_TOO_LOW")
    if market_prob and market_prob > 0.80:
        reasons.append("RESEARCH_PROB_TOO_HIGH")
    if market in ("FT_UNDER_1_5", "FT_OVER_3_5"):
        reasons.append("RESEARCH_TOXIC_MARKET")

    if not reasons:
        return "LIVE_SAFE", "PASSED_SAFE_MODE"
    else:
        return "RESEARCH", "; ".join(reasons)


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  BACKFILL SELECTION MODE{RESET}")
    print(f"{'═'*66}")

    reset_at = _parse_reset_at()
    if reset_at:
        _info(f"TRACKING_RESET_AT = {reset_at}")
    else:
        _warn("TRACKING_RESET_AT not set — backfilling ALL predictions")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Fetch POST_RESET predictions ───────────────────────────────────────────
    print(f"\n{BOLD}── Fetching predictions for backfill {'─'*41}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, statistical_tier, ev_tier, bookmaker_odd, "
                "market_probability, implied_probability, ev_percentage, "
                "market, odds_source, created_at, prediction_date"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.limit(5000).execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} predictions for backfill")

    # ── Evaluate SAFE mode for each row ───────────────────────────────────────
    print(f"\n{BOLD}── Evaluating SAFE mode criteria {'─'*41}{RESET}")
    live_safe_count = 0
    research_count = 0
    updates = []

    for r in rows:
        mode, reason = _evaluate_safe_mode(r)
        current_mode = r.get("selection_mode") or "UNKNOWN"

        if mode == "LIVE_SAFE":
            live_safe_count += 1
        else:
            research_count += 1

        if mode != current_mode or not r.get("selection_reason"):
            updates.append({
                "prediction_id": r["prediction_id"],
                "selection_mode": mode,
                "selection_reason": reason,
            })

    _info(f"LIVE_SAFE: {live_safe_count}")
    _info(f"RESEARCH: {research_count}")
    _info(f"Rows needing update: {len(updates)}")

    # ── Preview updates ────────────────────────────────────────────────────────
    if updates:
        print(f"\n{BOLD}── Preview updates (first 10) {'─'*48}{RESET}")
        print(f"  {'prediction_id':<12} {'selection_mode':<15} {'selection_reason':<30}")
        print(f"  {'─'*12} {'─'*15} {'─'*30}")
        for u in updates[:10]:
            print(f"  {u['prediction_id'][:12]:<12} {u['selection_mode']:<15} {u['selection_reason'][:30]}")

    # ── Confirm before applying ───────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{YELLOW}  WARNING: This will UPDATE {len(updates)} rows in Supabase{RESET}")
    print(f"{YELLOW}  Type 'YES' to confirm backfill: {RESET}", end="")
    try:
        confirm = input().strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled")
        sys.exit(0)

    if confirm != "YES":
        print("Cancelled")
        sys.exit(0)

    # ── Apply updates ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Applying backfill updates {'─'*47}{RESET}")
    success_count = 0
    error_count = 0

    for u in updates:
        try:
            repo._client.table("predictions").update({
                "selection_mode": u["selection_mode"],
                "selection_reason": u["selection_reason"],
            }).eq("prediction_id", u["prediction_id"]).execute()
            success_count += 1
        except Exception as exc:
            _err(f"Failed to update {u['prediction_id']}: {exc}")
            error_count += 1

    _ok(f"Updated {success_count} rows successfully")
    if error_count > 0:
        _err(f"Failed to update {error_count} rows")

    # ── Verify results ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── Verifying backfill results {'─'*46}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select("selection_mode", count="exact")
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
        mode_counts = {}
        for r in rows:
            mode = r.get("selection_mode") or "NULL"
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        print(f"  {'selection_mode':<15} {'Count':<10}")
        print(f"  {'─'*15} {'─'*10}")
        for mode in sorted(mode_counts.keys()):
            print(f"  {mode:<15} {mode_counts[mode]:<10}")
    except Exception as exc:
        _err(f"Verification failed: {exc}")

    print(f"\n{BOLD}{GREEN}  BACKFILL COMPLETE{RESET}")
    print()


if __name__ == "__main__":
    main()
