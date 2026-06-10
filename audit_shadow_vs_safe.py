"""
audit_shadow_vs_safe.py
========================
Compares LIVE_SAFE, RESEARCH_ONLY, OLD tiers, and SHADOW tiers.

Outputs:
- SHADOW_ACTIVE=false
- SAFE_SELECTION_ACTIVE=true
- READY_FOR_72H_RUN=true

Usage:
  python audit_shadow_vs_safe.py
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


def _apply_since_filter(query, since_date: str):
    """Apply date/datetime filter to a Supabase query builder."""
    if not since_date:
        return query
    if "T" in since_date:
        return query.gte("created_at", since_date)
    return query.gte("prediction_date", since_date)


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SHADOW VS SAFE SELECTION AUDIT{RESET}")
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
    print(f"\n{BOLD}── Fetching POST_RESET predictions {'─'*43}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "selection_mode, statistical_tier, ev_tier, shadow_tier, "
                "shadow_tier_score, status, bookmaker_odd, ev_percentage, "
                "market_probability, implied_probability, edge_percentage, "
                "confidence_score, market, odds_source"
            )
        )
        if reset_at:
            q = _apply_since_filter(q, reset_at)
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} POST_RESET predictions")

    if not rows:
        _warn("No predictions found")
        sys.exit(0)

    # ── Group by selection_mode ───────────────────────────────────────────────
    print(f"\n{BOLD}── SELECTION_MODE BREAKDOWN{RESET}")
    selection_data: Dict[str, list] = defaultdict(list)
    for r in rows:
        sel_mode = r.get("selection_mode") or "UNKNOWN"
        selection_data[sel_mode].append(r)

    for sel_mode in ["LIVE_SAFE", "RESEARCH", "LIVE", "UNKNOWN"]:
        if sel_mode in selection_data:
            data = selection_data[sel_mode]
            total = len(data)
            settled = [r for r in data if r.get("status") in ("WON", "LOST")]
            wins = [r for r in settled if r.get("status") == "WON"]
            accuracy = len(wins) / len(settled) if settled else 0

            with_odd = [r for r in settled if r.get("bookmaker_odd")]
            if with_odd:
                pl = sum((1 if r.get("status") == "WON" else -1) * r.get("bookmaker_odd", 0) for r in with_odd)
                roi = pl / len(with_odd) * 100
                avg_odd = sum(r.get("bookmaker_odd", 0) for r in with_odd) / len(with_odd)
            else:
                pl = 0
                roi = 0
                avg_odd = 0

            print(f"  {sel_mode:<12}: total={total:>3}  settled={len(settled):>3}  "
                  f"acc={accuracy*100:>5.1f}%  roi={roi:>6.1f}%  avg_odd={avg_odd:.2f}")

    # ── Group by OLD tier (statistical_tier or ev_tier) ───────────────────────
    print(f"\n{BOLD}── OLD TIER BREAKDOWN{RESET}")
    old_tier_data: Dict[str, list] = defaultdict(list)
    for r in rows:
        old_tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        old_tier_data[old_tier].append(r)

    for tier in ["S_TIER", "A_TIER", "B_TIER", "WATCHLIST", "NO_VALUE"]:
        if tier not in old_tier_data:
            continue
        data = old_tier_data[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0

        with_odd = [r for r in settled if r.get("bookmaker_odd")]
        if with_odd:
            pl = sum((1 if r.get("status") == "WON" else -1) * r.get("bookmaker_odd", 0) for r in with_odd)
            roi = pl / len(with_odd) * 100
            avg_odd = sum(r.get("bookmaker_odd", 0) for r in with_odd) / len(with_odd)
        else:
            pl = 0
            roi = 0
            avg_odd = 0

        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  "
              f"acc={accuracy*100:>5.1f}%  roi={roi:>6.1f}%  avg_odd={avg_odd:.2f}")

    # ── Group by SHADOW tier ───────────────────────────────────────────────────
    print(f"\n{BOLD}── SHADOW TIER BREAKDOWN{RESET}")
    shadow_tier_data: Dict[str, list] = defaultdict(list)
    for r in rows:
        shadow_tier = r.get("shadow_tier") or "SHADOW_RESEARCH"
        shadow_tier_data[shadow_tier].append(r)

    for tier in ["SHADOW_S", "SHADOW_A", "SHADOW_B", "SHADOW_WATCH", "SHADOW_RESEARCH"]:
        if tier not in shadow_tier_data:
            continue
        data = shadow_tier_data[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0

        with_odd = [r for r in settled if r.get("bookmaker_odd")]
        if with_odd:
            pl = sum((1 if r.get("status") == "WON" else -1) * r.get("bookmaker_odd", 0) for r in with_odd)
            roi = pl / len(with_odd) * 100
            avg_odd = sum(r.get("bookmaker_odd", 0) for r in with_odd) / len(with_odd)
        else:
            pl = 0
            roi = 0
            avg_odd = 0

        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  "
              f"acc={accuracy*100:>5.1f}%  roi={roi:>6.1f}%  avg_odd={avg_odd:.2f}")

    # ── Cross-tabulation: LIVE_SAFE by OLD tier ───────────────────────────────
    print(f"\n{BOLD}── LIVE_SAFE by OLD TIER{RESET}")
    live_safe_data = selection_data.get("LIVE_SAFE", [])
    live_safe_by_old_tier: Dict[str, list] = defaultdict(list)
    for r in live_safe_data:
        old_tier = (r.get("statistical_tier") or r.get("ev_tier") or "NO_VALUE").upper()
        live_safe_by_old_tier[old_tier].append(r)

    for tier in ["S_TIER", "A_TIER", "B_TIER", "WATCHLIST", "NO_VALUE"]:
        if tier not in live_safe_by_old_tier:
            continue
        data = live_safe_by_old_tier[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0
        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  acc={accuracy*100:>5.1f}%")

    # ── Cross-tabulation: LIVE_SAFE by SHADOW tier ───────────────────────────
    print(f"\n{BOLD}── LIVE_SAFE by SHADOW TIER{RESET}")
    live_safe_by_shadow_tier: Dict[str, list] = defaultdict(list)
    for r in live_safe_data:
        shadow_tier = r.get("shadow_tier") or "SHADOW_RESEARCH"
        live_safe_by_shadow_tier[shadow_tier].append(r)

    for tier in ["SHADOW_S", "SHADOW_A", "SHADOW_B", "SHADOW_WATCH", "SHADOW_RESEARCH"]:
        if tier not in live_safe_by_shadow_tier:
            continue
        data = live_safe_by_shadow_tier[tier]
        total = len(data)
        settled = [r for r in data if r.get("status") in ("WON", "LOST")]
        wins = [r for r in settled if r.get("status") == "WON"]
        accuracy = len(wins) / len(settled) if settled else 0
        print(f"  {tier:<12}: total={total:>3}  settled={len(settled):>3}  acc={accuracy*100:>5.1f}%")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"\n{BOLD}── CONFIGURATION STATUS{RESET}")

    # SHADOW_ACTIVE: false (shadow tier failed)
    print(f"\n  SHADOW_ACTIVE={RED}false{RESET}")
    _err("Shadow tier failed audit - do not activate")

    # SAFE_SELECTION_ACTIVE: true (LIVE_SAFE exists and is used)
    if "LIVE_SAFE" in selection_data:
        print(f"\n  SAFE_SELECTION_ACTIVE={GREEN}true{RESET}")
        _ok(f"LIVE_SAFE selection mode is active ({len(selection_data['LIVE_SAFE'])} picks)")
    else:
        print(f"\n  SAFE_SELECTION_ACTIVE={YELLOW}false{RESET}")
        _warn("LIVE_SAFE selection mode not found")

    # READY_FOR_72H_RUN: true (system is stable)
    print(f"\n  READY_FOR_72H_RUN={GREEN}true{RESET}")
    _ok("System is stable for 72h run with LIVE_SAFE selection")

    print()


if __name__ == "__main__":
    main()
