"""
debug_kickoff_time.py
=====================
Debug kickoff_time in predictions table.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

def main():
    print(f"\n{'='*66}")
    print(f"  KICKOFF TIME DEBUG")
    print(f"{'='*66}")
    
    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        print("ERROR: Supabase not connected")
        sys.exit(1)
    print("✓ Supabase connected")
    
    reset_at = os.environ.get("TRACKING_RESET_AT", "").strip()
    
    if reset_at:
        if "T" in reset_at:
            q = repo._client.table("predictions").select(
                "id, home_team, away_team, prediction_date, kickoff_time, fixture_id"
            ).gte("created_at", reset_at).limit(10)
        else:
            q = repo._client.table("predictions").select(
                "id, home_team, away_team, prediction_date, kickoff_time, fixture_id"
            ).gte("prediction_date", reset_at).limit(10)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, home_team, away_team, prediction_date, kickoff_time, fixture_id"
        ).gte("prediction_date", cutoff).limit(10)
    
    rows = q.execute().data or []
    print(f"\nPredictions sample (first 10):")
    print(f"{'Home':20s} {'Away':20s} {'prediction_date':25s} {'kickoff_time':25s}")
    print(f"{'-'*90}")
    
    for r in rows:
        print(f"{r.get('home_team', '')[:20]:20s} {r.get('away_team', '')[:20]:20s} "
              f"{str(r.get('prediction_date', '')):25s} {str(r.get('kickoff_time', '')):25s}")
    
    # Check fixtures table
    print(f"\n{'='*66}")
    print(f"  FIXTURES TABLE KICKOFF TIME")
    print(f"{'='*66}")
    
    if reset_at:
        if "T" in reset_at:
            fq = repo._client.table("fixtures").select(
                "id, fixture_id, home_team, away_team, kickoff_time"
            ).gte("created_at", reset_at).limit(10)
        else:
            fq = repo._client.table("fixtures").select(
                "id, fixture_id, home_team, away_team, kickoff_time"
            ).gte("kickoff_time", reset_at).limit(10)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        fq = repo._client.table("fixtures").select(
            "id, fixture_id, home_team, away_team, kickoff_time"
        ).gte("kickoff_time", cutoff).limit(10)
    
    fixtures = fq.execute().data or []
    print(f"\nFixtures sample (first 10):")
    print(f"{'Home':20s} {'Away':20s} {'fixture_id':15s} {'kickoff_time':25s}")
    print(f"{'-'*90}")
    
    for f in fixtures:
        print(f"{f.get('home_team', '')[:20]:20s} {f.get('away_team', '')[:20]:20s} "
              f"{str(f.get('fixture_id', '')):15s} {str(f.get('kickoff_time', '')):25s}")
    
    print(f"\n{'='*66}\n")


if __name__ == "__main__":
    main()
