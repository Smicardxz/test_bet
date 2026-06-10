"""
debug_profile_structure.py
===========================
Debug the actual structure of offensive_profile and defensive_profile.
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
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  DEBUG PROFILE STRUCTURE{RESET}")
    print(f"{'='*66}")
    
    # ========================================================================
    # FETCH PREDICTIONS
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 1 — FETCH PREDICTIONS{RESET}")
    print(f"{'='*66}")
    
    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        _err("Supabase not connected")
        sys.exit(1)
    _ok("Supabase connected")
    
    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
    
    if reset_at:
        if "T" in reset_at:
            q = repo._client.table("predictions").select(
                "id, offensive_profile, defensive_profile"
            ).gte("created_at", reset_at).limit(5)
        else:
            q = repo._client.table("predictions").select(
                "id, offensive_profile, defensive_profile"
            ).gte("prediction_date", reset_at).limit(5)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, offensive_profile, defensive_profile"
        ).gte("prediction_date", cutoff).limit(5)
    
    rows = q.execute().data or []
    print(f"Sample predictions: {len(rows)}")
    
    # ========================================================================
    # INSPECT PROFILE STRUCTURE
    # ========================================================================
    print(f"\n{BOLD}{'='*66}{RESET}")
    print(f"{BOLD}  PHASE 2 — INSPECT PROFILE STRUCTURE{RESET}")
    print(f"{'='*66}")
    
    for i, row in enumerate(rows):
        print(f"\n--- Prediction {i+1} ---")
        print(f"ID: {row.get('id')}")
        
        offensive = row.get("offensive_profile")
        defensive = row.get("defensive_profile")
        
        print(f"\noffensive_profile type: {type(offensive)}")
        if offensive:
            if isinstance(offensive, dict):
                print(f"Keys: {list(offensive.keys())}")
                print(f"Content: {offensive}")
            else:
                print(f"Content: {offensive}")
        else:
            print("offensive_profile: None")
        
        print(f"\ndefensive_profile type: {type(defensive)}")
        if defensive:
            if isinstance(defensive, dict):
                print(f"Keys: {list(defensive.keys())}")
                print(f"Content: {defensive}")
            else:
                print(f"Content: {defensive}")
        else:
            print("defensive_profile: None")
    
    print(f"\n{BOLD}{'='*66}{RESET}\n")


if __name__ == "__main__":
    main()
