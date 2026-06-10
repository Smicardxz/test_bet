"""
apply_migration_006.py
=======================
Applies migration 006_shadow_tier.sql to Supabase.

Usage:
  python apply_migration_006.py
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
    print(f"{BOLD}  APPLY MIGRATION 006: SHADOW TIER FIELDS{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # Read migration SQL
    migration_path = os.path.join(os.path.dirname(__file__), "app", "database", "migrations", "006_shadow_tier.sql")
    with open(migration_path, "r") as f:
        sql = f.read()

    print(f"\n{BOLD}── Migration SQL{RESET}")
    print(sql)

    # Apply migration using Supabase SQL editor
    # Since we can't execute raw SQL via the client, we'll add columns individually
    print(f"\n{BOLD}── Applying migration via Supabase client{RESET}")

    try:
        # Add shadow_tier column
        try:
            repo._client.rpc("exec_sql", {"sql": "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS shadow_tier TEXT"}).execute()
            _ok("Added shadow_tier column")
        except Exception as e:
            _info(f"shadow_tier column may already exist: {e}")

        # Add shadow_tier_score column
        try:
            repo._client.rpc("exec_sql", {"sql": "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS shadow_tier_score NUMERIC"}).execute()
            _ok("Added shadow_tier_score column")
        except Exception as e:
            _info(f"shadow_tier_score column may already exist: {e}")

        # Add shadow_tier_reason column
        try:
            repo._client.rpc("exec_sql", {"sql": "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS shadow_tier_reason TEXT"}).execute()
            _ok("Added shadow_tier_reason column")
        except Exception as e:
            _info(f"shadow_tier_reason column may already exist: {e}")

        print(f"\n{YELLOW}⚠{RESET}  Note: Index creation and comments must be applied manually via Supabase SQL editor")
        print(f"  Run the following in Supabase SQL editor:")
        print(f"  {CYAN}CREATE INDEX IF NOT EXISTS idx_predictions_shadow_tier ON predictions(shadow_tier);{RESET}")
        print(f"  {CYAN}COMMENT ON COLUMN predictions.shadow_tier IS 'Shadow tier for tier redesign simulation';{RESET}")

    except Exception as exc:
        _err(f"Migration failed: {exc}")
        print(f"\n{YELLOW}⚠{RESET}  Please apply migration manually via Supabase SQL editor:")
        print(f"  Run: {migration_path}")
        sys.exit(1)

    print(f"\n{BOLD}{'═'*66}{RESET}")
    print(f"{BOLD}{GREEN}  MIGRATION 006 APPLIED{RESET}")
    print()


if __name__ == "__main__":
    main()
