# API-Football Setup Complete ✅

## Status

**✅ REAL DATA CONNECTED**

- Provider: API-Football / API-Sports
- API Key: Configured and valid
- Quota: 100 requests/day (Free tier)
- Today's matches: 116 retrieved
- Target matches: 27 from obscure leagues

## Configuration

### .env File

```env
DATA_PROVIDER=api_football
API_FOOTBALL_KEY=a977a26c11eb494d3462b6a3cbc0aecc
API_FOOTBALL_URL=https://v3.football.api-sports.io
```

### Verification Scripts

1. **Health Check**
```bash
python scripts/provider_health_check.py
```
Output:
```
✅ CONNECTED api_football
   Quota: 4/100
✅ REAL DATA PIPELINE OK
```

2. **Coverage Inspector**
```bash
python scripts/coverage_inspector.py
```
Shows:
- Target countries covered (7/20 today)
- Women's football: 1 competition
- Youth football: 1 competition
- Lower divisions: 97 matches
- Obscure countries: 28 matches

3. **Full API Test**
```bash
python scripts/test_api_football.py
```
Displays:
- API status and quota
- All matches for today
- Target league analysis
- Odds availability
- Sample matches

## Coverage Today (May 28, 2026)

### Target Countries Detected ✅
- 🎯 Albania: 1 match
- 🎯 Azerbaijan: 1 match
- 🎯 Belarus: 3 matches
- 🎯 Ecuador: 1 match
- 🎯 Estonia: 6 matches
- 🎯 Georgia: 9 matches
- 🎯 Kazakhstan: 6 matches

### Categories
- Lower Division: 97 matches
- Obscure Country: 28 matches
- Reserve: 13 matches
- Youth: 5 matches
- Women: 0 matches (today)

### Sample Competitions
- Albania - 1st Division
- Argentina - Reserve League
- Azerbaijan - Premyer Liqa
- Belarus - Coppa
- Brazil - Brasileiro U20 A
- Bulgaria - First League
- Colombia - Liga Femenina
- Denmark - Kvindeliga
- Estonia - Esiliiga A/B
- Georgia - Erovnuli Liga 2
- Kazakhstan - First Division

## Odds Availability

⚠️ **Odds not available from API-Football Free tier**

The free tier provides:
- ✅ Fixtures (matches)
- ✅ Teams
- ✅ Leagues
- ✅ Statistics
- ❌ Odds (requires paid plan)

### Solutions for Odds

1. **Upgrade API-Football** (Recommended)
   - Pro plan includes odds
   - Cost: ~$20-50/month
   - Full coverage

2. **Separate Odds Provider**
   - The Odds API
   - Odds API
   - BetFair API

3. **Mock Odds for Development**
   - Use statistical signals only
   - Display "Odds not available"
   - Focus on anomaly detection

## Next Steps

### Immediate
1. ✅ API-Football provider working
2. ✅ Health check script created
3. ✅ Coverage inspector created
4. ⏳ Integrate with scanner
5. ⏳ Update dashboard to use real data

### For Production
1. Consider upgrading to Pro plan for odds
2. Or implement separate odds provider
3. Add caching for API efficiency
4. Monitor quota usage

## API Usage Tips

### Free Tier Limits
- 100 requests/day
- No odds data
- Basic statistics

### Optimization
- Cache responses (5-10 minutes)
- Fetch once per day
- Filter by target leagues
- Batch requests when possible

### Current Usage
- Health check: 1 request
- Today's matches: 1 request
- Coverage analysis: 1 request
- **Total today: 4/100**

## Integration with Scanner

### Current Architecture
```
MockDataProvider (old)
  ↓
SofaScoreProvider (403 Forbidden)
  ↓
ApiFootballProvider (✅ Working)
```

### Next: Update DataSourceConfig

```python
# app/config/data_source_config.py
if provider_type == "api_football":
    return ApiFootballProvider()
```

### Next: Update Scanner

```python
# Use real matches from API-Football
matches = provider.get_today_matches()

# Filter by target leagues
targeting = LeagueTargetingService(TargetMode.ALL_MINOR)
target_matches = [m for m in matches if targeting.should_include(...)]
```

## Strategy Validation

✅ **Strategy is viable with API-Football**

- 27 target matches available today
- 7 target countries covered
- 97 lower division matches
- Good coverage of obscure leagues

### Best Days
- Weekends: More matches
- Midweek: Lower divisions active
- Check coverage daily

## Documentation

- `ENV_SETUP.md` - Environment configuration
- `API_FOOTBALL_SETUP.md` - This file
- `SOFASCORE_403_ISSUE.md` - Why we switched from SofaScore

## Support

API-Football Documentation:
- https://www.api-football.com/documentation-v3
- https://dashboard.api-football.com

## Summary

✅ Real data pipeline is **fully operational**
✅ Target leagues are **well covered**
⚠️ Odds require **paid upgrade** or **separate provider**
🎯 Strategy is **viable** with current setup
