"""
apply_migration_007.py
========================
Applies migration 007 (event mode fields) using Supabase Python client.

Usage:
  python apply_migration_007.py
"""

import os
import sys
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
    print(f"{BOLD}  APPLY MIGRATION 007 — EVENT MODE FIELDS{RESET}")
    print(f"{'═'*66}")

    from app.database.supabase_config import reset_supabase_config, get_supabase_config
    from app.database.supabase_repository import reset_repository, get_repository

    reset_supabase_config()
    reset_repository()
    cfg = get_supabase_config()
    repo = get_repository()

    if not cfg.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")

    # Check if columns already exist
    print(f"\n{BOLD}── Checking existing columns{RESET}")
    try:
        # Query information schema to check columns
        result = repo._client.table("predictions").select("*").limit(1).execute()
        if result.data:
            row = result.data[0]
            existing_cols = set(row.keys())
            required_cols = {"event_context", "event_name", "is_event_match", "event_phase"}
            missing_cols = required_cols - existing_cols
            
            if not missing_cols:
                _ok("All event mode columns already exist")
                print(f"\n{BOLD}{GREEN}MIGRATION ALREADY APPLIED{RESET}")
                return
            else:
                _warn(f"Missing columns: {missing_cols}")
        else:
            _warn("No predictions found to check columns")
    except Exception as exc:
        _warn(f"Could not check existing columns: {exc}")

    # Apply migration using raw SQL
    print(f"\n{BOLD}── Applying migration{RESET}")
    print(f"{YELLOW}Note: Supabase Python client cannot execute DDL directly.{RESET}")
    print(f"{YELLOW}Please apply the SQL manually in Supabase SQL Editor:{RESET}\n")
    
    sql_path = os.path.join(os.path.dirname(__file__), "app", "database", "migrations", "007_event_mode.sql")
    try:
        with open(sql_path, "r") as f:
            sql_content = f.read()
        print(f"{CYAN}{sql_content}{RESET}")
    except Exception as exc:
        _err(f"Could not read migration file: {exc}")
        sys.exit(1)

    print(f"\n{BOLD}── Manual Instructions{RESET}")
    print(f"  1. Go to Supabase SQL Editor")
    print(f"  2. Paste the SQL above")
    print(f"  3. Execute")
    print(f"  4. Run: python check_event_columns.py to verify")


if __name__ == "__main__":
    main()
