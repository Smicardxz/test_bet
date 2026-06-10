"""Time a single match analysis end-to-end"""
from dotenv import load_dotenv; load_dotenv(override=True)
import logging, time
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from app.providers.data_source_manager import DataSourceManager
from app.services.data.match_data_loader import MatchDataLoader

manager = DataSourceManager()

# Get today's matches (cached after first call)
t0 = time.time()
response = manager.provider.get_today_matches()
print(f"get_today_matches: {time.time()-t0:.1f}s")

# Find first upcoming match
from app.services.targeting.league_targeting_service import LeagueTargetingService
targeting = LeagueTargetingService()
for match in response.data:
    s = getattr(match, 'status', '').upper()
    if s not in ('UPCOMING', 'NS', 'SCHEDULED'):
        continue
    profile = targeting.analyze_competition(
        competition_name=match.competition.name if hasattr(match, 'competition') else "",
        country=match.competition.country if hasattr(match, 'competition') else ""
    )
    if not targeting.should_include(profile):
        continue

    print(f"\nAnalyzing: {match.home_team.name} vs {match.away_team.name}")
    print(f"  fixture_id: {getattr(match, 'match_id', '?')}")
    print(f"  home_id:    {match.home_team.id}")
    print(f"  away_id:    {match.away_team.id}")

    loader = MatchDataLoader(manager.provider)

    t1 = time.time()
    try:
        bundle = loader.load_match_data(
            fixture_id=str(getattr(match, 'match_id', '')),
            home_team_id=match.home_team.id,
            away_team_id=match.away_team.id,
            home_team_name=match.home_team.name,
            away_team_name=match.away_team.name,
            match_date=getattr(match, 'match_date', None),
            history_limit=10
        )
        elapsed = time.time() - t1
        print(f"  load_match_data: {elapsed:.1f}s")
        print(f"  home_history:    {len(bundle.home_history)} matches")
        print(f"  away_history:    {len(bundle.away_history)} matches")
        print(f"  h2h_matches:     {len(bundle.h2h_matches)} matches")
        print(f"  errors:          {bundle.errors}")
    except Exception as e:
        import traceback; traceback.print_exc()
    break
