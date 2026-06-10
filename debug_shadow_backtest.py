"""
debug_shadow_backtest.py
========================
Debug script to check shadow backtest data.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(override=True)

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

def main():
    print(f"\n{'='*66}")
    print(f"  SHADOW BACKTEST DEBUG")
    print(f"{'='*66}")

    reset_at = _parse_reset_at()
    if reset_at:
        print(f"\nTRACKING_RESET_AT = {reset_at}")
    else:
        print(f"\nTRACKING_RESET_AT not set")

    from app.database.supabase_repository import get_repository, reset_repository
    reset_repository()
    repo = get_repository()
    if not repo.supabase_connected:
        print("ERROR: Supabase not connected")
        sys.exit(1)
    print("✓ Supabase connected")

    # Fetch predictions
    print(f"\n{'─'*66}")
    print(f"Fetching predictions...")
    print(f"{'─'*66}")
    
    if reset_at:
        if "T" in reset_at:
            q = repo._client.table("predictions").select(
                "id, market, status, fixture_id, home_team, away_team"
            ).gte("created_at", reset_at)
        else:
            q = repo._client.table("predictions").select(
                "id, market, status, fixture_id, home_team, away_team"
            ).gte("prediction_date", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        q = repo._client.table("predictions").select(
            "id, market, status, fixture_id, home_team, away_team"
        ).gte("prediction_date", cutoff)
    
    rows = q.execute().data or []
    print(f"Total predictions: {len(rows)}")
    
    settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
    print(f"Settled predictions: {len(settled)}")
    
    # Fetch fixtures
    print(f"\n{'─'*66}")
    print(f"Fetching fixtures...")
    print(f"{'─'*66}")
    
    if reset_at:
        if "T" in reset_at:
            fq = repo._client.table("fixtures").select(
                "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
            ).gte("created_at", reset_at)
        else:
            fq = repo._client.table("fixtures").select(
                "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
            ).gte("kickoff_time", reset_at)
    else:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        fq = repo._client.table("fixtures").select(
            "id, fixture_id, home_team, away_team, home_score, away_score, ht_home_score, ht_away_score, kickoff_time, status"
        ).gte("kickoff_time", cutoff)
    
    fixtures = fq.execute().data or []
    print(f"Total fixtures: {len(fixtures)}")
    
    fixtures_with_scores = [f for f in fixtures if f.get("home_score") is not None and f.get("away_score") is not None]
    print(f"Fixtures with scores: {len(fixtures_with_scores)}")
    
    # Show sample fixture_ids from fixtures table
    print(f"\nSample fixture_ids in fixtures table:")
    for f in fixtures[:5]:
        print(f"  {f.get('fixture_id')}: {f.get('home_team')} vs {f.get('away_team')}")
    
    # Show sample fixture_ids from predictions
    print(f"\nSample fixture_ids in predictions:")
    for pred in settled[:5]:
        print(f"  {pred.get('fixture_id')}: {pred.get('home_team')} vs {pred.get('away_team')}")
    
    # Use fixture_id (API ID) for lookup since predictions reference it
    fixture_lookup = {f["fixture_id"]: f for f in fixtures if f.get("fixture_id")}
    
    # Check fixture_id mapping
    print(f"\n{'─'*66}")
    print(f"Checking fixture_id mapping...")
    print(f"{'─'*66}")
    
    mapped = 0
    unmapped = 0
    for pred in settled[:10]:
        fixture_id = pred.get("fixture_id")
        if fixture_id in fixture_lookup:
            mapped += 1
            fixture = fixture_lookup[fixture_id]
            print(f"✓ {pred.get('home_team')} vs {pred.get('away_team')} -> home_score={fixture.get('home_score')}, away_score={fixture.get('away_score')}")
        else:
            unmapped += 1
            print(f"✗ {pred.get('home_team')} vs {pred.get('away_team')} -> fixture_id={fixture_id} NOT FOUND")
    
    print(f"\nMapped: {mapped}, Unmapped: {unmapped}")
    
    # Run backtest
    print(f"\n{'─'*66}")
    print(f"Running shadow backtest...")
    print(f"{'─'*66}")
    
    shadow_backtest = {
        "BTTS_YES": {"sample": 0, "wins": 0},
        "BTTS_NO": {"sample": 0, "wins": 0},
        "HOME_TEAM_OVER_0_5": {"sample": 0, "wins": 0},
        "AWAY_TEAM_OVER_0_5": {"sample": 0, "wins": 0},
        "HOME_TEAM_OVER_1_5": {"sample": 0, "wins": 0},
        "AWAY_TEAM_OVER_1_5": {"sample": 0, "wins": 0}
    }
    
    for pred in settled:
        fixture_id = pred.get("fixture_id")
        fixture = fixture_lookup.get(fixture_id)
        
        if not fixture:
            continue
        
        home_score = fixture.get("home_score")
        away_score = fixture.get("away_score")
        
        if home_score is None or away_score is None:
            continue
        
        # BTTS_YES
        shadow_backtest["BTTS_YES"]["sample"] += 1
        if home_score > 0 and away_score > 0:
            shadow_backtest["BTTS_YES"]["wins"] += 1
        
        # BTTS_NO
        shadow_backtest["BTTS_NO"]["sample"] += 1
        if home_score == 0 or away_score == 0:
            shadow_backtest["BTTS_NO"]["wins"] += 1
        
        # HOME_TEAM_OVER_0_5
        shadow_backtest["HOME_TEAM_OVER_0_5"]["sample"] += 1
        if home_score >= 1:
            shadow_backtest["HOME_TEAM_OVER_0_5"]["wins"] += 1
        
        # AWAY_TEAM_OVER_0_5
        shadow_backtest["AWAY_TEAM_OVER_0_5"]["sample"] += 1
        if away_score >= 1:
            shadow_backtest["AWAY_TEAM_OVER_0_5"]["wins"] += 1
        
        # HOME_TEAM_OVER_1_5
        shadow_backtest["HOME_TEAM_OVER_1_5"]["sample"] += 1
        if home_score >= 2:
            shadow_backtest["HOME_TEAM_OVER_1_5"]["wins"] += 1
        
        # AWAY_TEAM_OVER_1_5
        shadow_backtest["AWAY_TEAM_OVER_1_5"]["sample"] += 1
        if away_score >= 2:
            shadow_backtest["AWAY_TEAM_OVER_1_5"]["wins"] += 1
    
    print(f"\nShadow Backtest Results:")
    for market, stats in shadow_backtest.items():
        if stats["sample"] > 0:
            accuracy = stats["wins"] / stats["sample"] * 100
            print(f"  {market}: sample={stats['sample']}, wins={stats['wins']}, accuracy={accuracy:.1f}%")
        else:
            print(f"  {market}: sample=0 (no data)")
    
    print(f"\n{'='*66}\n")


if __name__ == "__main__":
    main()
