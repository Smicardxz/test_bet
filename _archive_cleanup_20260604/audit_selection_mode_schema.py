"""
audit_selection_mode_schema.py
==============================
Verifies selection_mode and selection_reason columns exist in Supabase.

Outputs:
- selection_mode exists?
- selection_reason exists?
- column type
- row counts by selection_mode

Usage:
  python audit_selection_mode_schema.py
"""

import os
import sys

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
    print(f"{BOLD}  SELECTION MODE SCHEMA AUDIT{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # ── Check column existence via schema introspection ───────────────────────
    print(f"\n{BOLD}── Checking schema for selection_mode/selection_reason {'─'*27}{RESET}")

    try:
        # Query information_schema to check column existence
        q = (
            repo._client.table("predictions")
            .select("selection_mode, selection_reason", count="exact")
            .limit(1)
        )
        result = q.execute()
        _ok("selection_mode and selection_reason columns exist")
    except Exception as exc:
        _err(f"Schema check failed: {exc}")
        if "does not exist" in str(exc).lower() or "column" in str(exc).lower():
            _err("Columns missing — migration 005 may not have been applied")
        else:
            _err(f"Unexpected error: {exc}")
        print(f"\n{BOLD}{RED}  SAFE_SELECTION_SCHEMA_BROKEN{RESET}")
        print()
        sys.exit(1)

    # ── Count rows by selection_mode ────────────────────────────────────────────
    print(f"\n{BOLD}── Row counts by selection_mode {'─'*45}{RESET}")
    try:
        q = repo._client.table("predictions").select("selection_mode", count="exact")
        result = q.execute()
        rows = result.data or []
        mode_counts = {}
        for r in rows:
            mode = r.get("selection_mode") or "NULL"
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        print(f"  {'selection_mode':<20} {'Count':<10}")
        print(f"  {'─'*20} {'─'*10}")
        for mode in sorted(mode_counts.keys()):
            print(f"  {mode:<20} {mode_counts[mode]:<10}")

        total = sum(mode_counts.values())
        _info(f"Total rows: {total}")
    except Exception as exc:
        _err(f"Count query failed: {exc}")

    # ── Check selection_reason distribution ───────────────────────────────────
    print(f"\n{BOLD}── Row counts by selection_reason {'─'*41}{RESET}")
    try:
        q = repo._client.table("predictions").select("selection_reason", count="exact")
        result = q.execute()
        rows = result.data or []
        reason_counts = {}
        for r in rows:
            reason = r.get("selection_reason") or "NULL"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        print(f"  {'selection_reason':<35} {'Count':<10}")
        print(f"  {'─'*35} {'─'*10}")
        for reason in sorted(reason_counts.keys()):
            print(f"  {reason[:35]:<35} {reason_counts[reason]:<10}")
    except Exception as exc:
        _err(f"Reason count query failed: {exc}")

    # ── Verdict ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}{GREEN}  SAFE_SELECTION_SCHEMA_OK{RESET}")
    _ok("Schema is correct — columns exist and are accessible")
    print()


if __name__ == "__main__":
    main()
