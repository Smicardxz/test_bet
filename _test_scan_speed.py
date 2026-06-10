"""Quick scan speed diagnostic — no analysis, just targeting"""
from dotenv import load_dotenv; load_dotenv(override=True)
import logging, time
logging.basicConfig(level=logging.WARNING)

from app.providers.data_source_manager import DataSourceManager
from app.services.scanner.smart_scanner import SmartScanner

manager = DataSourceManager()

# Step 1: fetch today's matches
t0 = time.time()
response = manager.provider.get_today_matches()
t1 = time.time()
print(f"[1] get_today_matches: {t1-t0:.1f}s")
if not response.success:
    print("FAIL:", response.error); exit(1)

all_m = response.data
print(f"    total={len(all_m)}")
status_counts = {}
for m in all_m:
    s = getattr(m, 'status', 'UNKNOWN').upper()
    status_counts[s] = status_counts.get(s, 0) + 1
print("    statuses:", dict(sorted(status_counts.items())))

# Step 2: targeting only (no analysis)
from app.services.targeting.league_targeting_service import LeagueTargetingService
targeting = LeagueTargetingService()
t2 = time.time()
targeted = []
for match in all_m:
    s = getattr(match, 'status', '').upper()
    if s not in ('UPCOMING', 'NS', 'LIVE', 'IN_PLAY', 'PAUSED'):
        continue
    profile = targeting.analyze_competition(
        competition_name=match.competition.name if hasattr(match, 'competition') else "",
        country=match.competition.country if hasattr(match, 'competition') else ""
    )
    if targeting.should_include(profile):
        targeted.append({"match": match, "profile": profile})
t3 = time.time()
print(f"\n[2] targeting: {t3-t2:.1f}s → {len(targeted)} targeted matches")

# Leagues distribution
leagues = {}
for item in targeted:
    m = item["match"]
    league = m.competition.name if hasattr(m, 'competition') else "?"
    country = m.competition.country if hasattr(m, 'competition') else "?"
    k = f"{league} ({country})"
    leagues[k] = leagues.get(k, 0) + 1
print("    Top leagues:")
for lg, cnt in sorted(leagues.items(), key=lambda x: -x[1])[:10]:
    print(f"      {cnt:3d}  {lg}")

# Step 3: odds sport_key resolution
from app.providers.odds.external_odds_provider import TheOddsAPIProvider
import os
provider = TheOddsAPIProvider(api_key=os.getenv("ODDS_API_KEY","").strip())
needed = set()
for item in targeted:
    m = item["match"]
    comp = m.competition.name if hasattr(m, 'competition') else ""
    ctry = m.competition.country if hasattr(m, 'competition') else ""
    sk = provider.resolve_sport_key(comp, ctry)
    if sk:
        needed.add(sk)
print(f"\n[3] Sport keys needed: {len(needed)} → {sorted(needed)}")

# Step 4: odds prefetch for targeted matches
match_list = [{"competition": item["match"].competition.name if hasattr(item["match"], "competition") else "",
               "country": item["match"].competition.country if hasattr(item["match"], "competition") else ""}
              for item in targeted]
t4 = time.time()
provider.prefetch_for_matches(match_list)
t5 = time.time()
print(f"\n[4] prefetch_for_matches: {t5-t4:.1f}s → {provider.events_fetched} events / {len(provider._event_cache)} sports / quota={provider.quota_remaining}")

# Step 5: analyze ONE match to measure per-match cost
if targeted:
    item = targeted[0]
    match = item["match"]
    profile = item["profile"]
    print(f"\n[5] Single match analysis: {match.home_team.name} vs {match.away_team.name}")
    t6 = time.time()
    from app.services.data.match_data_loader import MatchDataLoader
    loader = MatchDataLoader(manager.provider)
    try:
        bundle = loader.load_match_data(
            home_team_id=str(match.home_team.id),
            away_team_id=str(match.away_team.id)
        )
        t7 = time.time()
        print(f"    load_match_data: {t7-t6:.1f}s")
        print(f"    home_matches={len(bundle.home_matches)}, away_matches={len(bundle.away_matches)}, h2h={len(bundle.h2h_matches)}")
    except Exception as e:
        print(f"    Error: {e}")
