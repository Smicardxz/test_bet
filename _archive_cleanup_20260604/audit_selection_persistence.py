"""
audit_selection_persistence.py
===============================
Verifies save_prediction() outputs selection_mode and selection_reason.

Shows for recent predictions:
- prediction_id
- selection_mode
- selection_reason
- created_at

Usage:
  python audit_selection_persistence.py
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


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  SELECTION PERSISTENCE AUDIT{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Check if SAFE_SELECTION_MODE is enabled ───────────────────────────────
    safe_mode = os.environ.get("SAFE_SELECTION_MODE", "").lower() in ("1", "true", "yes")
    if safe_mode:
        _info(f"SAFE_SELECTION_MODE = TRUE")
    else:
        _warn(f"SAFE_SELECTION_MODE = FALSE (not enabled)")

    # ── Fetch recent predictions ───────────────────────────────────────────────
    print(f"\n{BOLD}── Recent predictions (last 20) {'─'*39}{RESET}")
    try:
        q = (
            repo._client.table("predictions")
            .select(
                "prediction_id, selection_mode, selection_reason, "
                "statistical_tier, ev_tier, bookmaker_odd, market_probability, "
                "ev_percentage, market, created_at"
            )
            .order("created_at", desc=True)
            .limit(20)
        )
        rows = q.execute().data or []
    except Exception as exc:
        _err(f"Query failed: {exc}")
        sys.exit(1)

    _info(f"Fetched {len(rows)} recent predictions")

    print(f"\n  {'prediction_id':<12} {'selection_mode':<15} {'selection_reason':<30} {'created_at':<20}")
    print(f"  {'─'*12} {'─'*15} {'─'*30} {'─'*20}")
    for r in rows:
        pid = r.get("prediction_id", "")[:12]
        mode = r.get("selection_mode") or "NULL"
        reason = (r.get("selection_reason") or "NULL")[:30]
        created = r.get("created_at", "")[:19] if r.get("created_at") else "NULL"
        print(f"  {pid:<12} {mode:<15} {reason:<30} {created:<20}")

    # ── Check for LIVE_SAFE picks ─────────────────────────────────────────────
    live_safe = [r for r in rows if r.get("selection_mode") == "LIVE_SAFE"]
    research = [r for r in rows if r.get("selection_mode") == "RESEARCH"]
    live = [r for r in rows if r.get("selection_mode") == "LIVE"]

    print(f"\n{BOLD}── Selection mode distribution (recent 20) {'─'*32}{RESET}")
    print(f"  LIVE_SAFE  : {len(live_safe)}")
    print(f"  RESEARCH   : {len(research)}")
    print(f"  LIVE       : {len(live)}")
    print(f"  NULL/OTHER : {len(rows) - len(live_safe) - len(research) - len(live)}")

    # ── Verdict ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")

    if safe_mode and len(live_safe) == 0:
        print(f"{BOLD}{YELLOW}  SAFE_SELECTION_PERSISTENCE_NEEDS_DATA{RESET}")
        _warn("SAFE_SELECTION_MODE is enabled but no LIVE_SAFE picks found")
        _warn("This means no new predictions have been saved since code change")
        _warn("Run backfill_selection_mode.py to retroactively apply SAFE rules")
    elif not safe_mode:
        print(f"{BOLD}{YELLOW}  SAFE_SELECTION_PERSISTENCE_NOT_ENABLED{RESET}")
        _warn("SAFE_SELECTION_MODE is not enabled")
        _warn("Enable SAFE_SELECTION_MODE=true in .env to activate")
    else:
        print(f"{BOLD}{GREEN}  SAFE_SELECTION_PERSISTENCE_OK{RESET}")
        _ok(f"Found {len(live_safe)} LIVE_SAFE picks in recent predictions")

    print()


if __name__ == "__main__":
    main()
