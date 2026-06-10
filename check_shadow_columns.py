"""
check_shadow_columns.py
=======================
Checks if shadow tier columns exist in the predictions table.

Usage:
  python check_shadow_columns.py
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
def _info(m): print(f"  {CYAN}→{RESET}  {m}")


def main():
    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}  CHECK SHADOW TIER COLUMNS{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # Try to select shadow tier columns
    print(f"\n{BOLD}── Checking shadow_tier columns{RESET}")
    try:
        q = repo._client.table("predictions").select("shadow_tier, shadow_tier_score, shadow_tier_reason").limit(1)
        result = q.execute()
        if result.data:
            _ok("Shadow tier columns exist")
            print(f"  Sample: {result.data[0]}")
        else:
            _warn("Shadow tier columns exist but no data")
    except Exception as exc:
        _err(f"Shadow tier columns do not exist: {exc}")
        print(f"\n{YELLOW}⚠{RESET}  Please apply migration manually via Supabase SQL editor:")
        print(f"  Open: https://app.supabase.com/project/{os.environ.get('SUPABASE_URL', '').split('//')[1].split('.')[0]}/sql")
        print(f"  Run the SQL from: app/database/migrations/006_shadow_tier.sql")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
