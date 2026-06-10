from dotenv import load_dotenv
load_dotenv(override=True)
import os, time

from app.providers.odds.external_odds_provider import TheOddsAPIProvider

provider = TheOddsAPIProvider(api_key=os.getenv("ODDS_API_KEY","").strip())

matches = [
    {"competition": "Premier League",  "country": "England"},
    {"competition": "Ligue 1",          "country": "France"},
    {"competition": "Super Liga Amateur","country": "Morocco"},
    {"competition": "Bundesliga",       "country": "Germany"},
    {"competition": "Liga MX",          "country": "Mexico"},
    {"competition": "Série A",          "country": "Brazil"},
]

print("=== resolve_sport_key ===")
for m in matches:
    sk = provider.resolve_sport_key(m["competition"], m["country"])
    print(f"  {m['competition']:30s} ({m['country']:10s}) -> {sk}")

print()
print("=== prefetch_for_matches (only supported leagues) ===")
t0 = time.time()
provider.prefetch_for_matches(matches)
elapsed = time.time() - t0
print(f"  Elapsed: {elapsed:.1f}s")
print(f"  events_fetched: {provider.events_fetched}")
print(f"  sports_loaded:  {len(provider._event_cache)}")
print(f"  quota_remaining:{provider.quota_remaining}")
print(f"  sports cached:  {list(provider._event_cache.keys())}")
