"""
backfill_shadow_tiers.py
========================
Backfills shadow tier fields for all POST_RESET predictions.

Usage:
  python backfill_shadow_tiers.py
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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Auto-confirm without prompt")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  BACKFILL SHADOW TIERS{RESET}")
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
                "prediction_id, implied_probability, bookmaker_odd, "
                "market_probability, ev_percentage, edge_percentage, "
                "confidence_score, market, odds_source, statistical_tier, ev_tier, "
                "created_at"
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
        _warn("No predictions to backfill")
        sys.exit(0)

    # ── Compute shadow tiers ───────────────────────────────────────────────────
    print(f"\n{BOLD}── Computing shadow tiers {'─'*50}{RESET}")
    from app.services.tiering.shadow_tier_calculator import compute_shadow_tier_from_row

    updates = []
    tier_counts = {
        "SHADOW_S": 0,
        "SHADOW_A": 0,
        "SHADOW_B": 0,
        "SHADOW_WATCH": 0,
        "SHADOW_RESEARCH": 0,
    }

    for r in rows:
        shadow_tier, shadow_score, shadow_reason = compute_shadow_tier_from_row(r)
        tier_counts[shadow_tier] += 1
        updates.append({
            "prediction_id": r["prediction_id"],
            "shadow_tier": shadow_tier,
            "shadow_tier_score": shadow_score,
            "shadow_tier_reason": shadow_reason,
        })

    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    # ── Confirm update ───────────────────────────────────────────────────────
    print(f"\n{BOLD}── Ready to update {len(updates)} predictions{RESET}")
    print(f"  {YELLOW}This will update shadow_tier, shadow_tier_score, and shadow_tier_reason{RESET}")
    if not args.yes:
        response = input(f"\n  Proceed? (y/N): ")
        if response.lower() != "y":
            _warn("Aborted by user")
            sys.exit(0)

    # ── Batch update ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}── Updating predictions {'─'*50}{RESET}")
    updated = 0
    failed = 0

    for update in updates:
        try:
            repo._client.table("predictions").update({
                "shadow_tier": update["shadow_tier"],
                "shadow_tier_score": update["shadow_tier_score"],
                "shadow_tier_reason": update["shadow_tier_reason"],
            }).eq("prediction_id", update["prediction_id"]).execute()
            updated += 1
            if updated % 10 == 0:
                print(f"  Updated {updated}/{len(updates)}...")
        except Exception as exc:
            failed += 1
            _err(f"Failed to update {update['prediction_id']}: {exc}")

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}{GREEN}  BACKFILL COMPLETE{RESET}")
    _ok(f"Updated: {updated}")
    if failed > 0:
        _err(f"Failed: {failed}")
    print()


if __name__ == "__main__":
    main()
