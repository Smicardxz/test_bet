# SofaScore 403 Forbidden Issue

## Problem

When trying to use `DATA_PROVIDER=sofascore`, the API returns **403 Forbidden** errors:

```
Request failed (attempt 1): 403 Client Error: Forbidden for url: https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-05-28
```

## Root Cause

SofaScore's public API detects that requests are not coming from a legitimate browser and blocks access. This is a common anti-scraping measure.

### Why it happens:
1. **User-Agent detection** - API checks if request comes from real browser
2. **Rate limiting** - Too many requests from same IP
3. **Missing cookies/session** - Browser-based APIs expect session data
4. **CORS/Referer checks** - API validates request origin

## Current Status

✅ **SofaScoreProvider exists** - Code is implemented correctly
✅ **Configuration works** - `DATA_PROVIDER` variable is read properly
✅ **Headers are set** - User-Agent, Referer, Origin included
❌ **API blocks requests** - Returns 403 Forbidden
❌ **Real data not accessible** - Cannot fetch matches from SofaScore

## Verification

Run the diagnostic script:

```bash
python scripts/verify_real_data_pipeline.py
```

Output will show:
```
❌ REAL DATA NOT CONNECTED
   - API returned 403 Forbidden
   - SofaScore blocks non-browser requests
   - Recommendation: Use MOCK mode or official API
```

## Solutions

### Option 1: Use MOCK Data (Recommended for Development)

**Best for:** Development, testing, demo

```bash
# No environment variable needed
streamlit run dashboard_v4.py
```

**Pros:**
- ✅ Works immediately
- ✅ Realistic demo data
- ✅ No API limits
- ✅ Fast and reliable

**Cons:**
- ❌ Not real matches
- ❌ Cannot analyze live games

### Option 2: Official SofaScore API (Recommended for Production)

**Best for:** Production, real analysis, commercial use

Contact SofaScore for official API access:
- Website: https://www.sofascore.com
- Requires: Business agreement, API key
- Cost: Typically paid service

**Pros:**
- ✅ Legitimate access
- ✅ No 403 errors
- ✅ Reliable data
- ✅ Support available

**Cons:**
- ❌ Requires payment
- ❌ Business agreement needed

### Option 3: Alternative Data Provider

**Best for:** Real data without SofaScore

Use services like:
- **API-Football** (https://www.api-football.com)
- **Football-Data.org** (https://www.football-data.org)
- **RapidAPI Sports** (https://rapidapi.com/api-sports)

**Implementation:**
1. Sign up for API key
2. Create new provider class (e.g., `APIFootballProvider`)
3. Implement same interface as `SofaScoreProvider`
4. Set `DATA_PROVIDER=apifootball`

**Pros:**
- ✅ Real data
- ✅ Legitimate access
- ✅ Often have free tiers

**Cons:**
- ❌ May not cover obscure leagues
- ❌ Requires API key
- ❌ May have rate limits

### Option 4: Browser Automation (Not Recommended)

**Best for:** Desperate situations only

Use Selenium/Playwright to automate a real browser.

**Pros:**
- ✅ Bypasses 403 errors
- ✅ Works with public API

**Cons:**
- ❌ Slow and resource-intensive
- ❌ Fragile (breaks with UI changes)
- ❌ Against terms of service
- ❌ May get IP banned
- ❌ Not scalable

## Recommended Approach

### For Development & Demo
```bash
# Use MOCK data
streamlit run dashboard_v4.py
```

The dashboard clearly shows:
- 🔴 MOCK DATA (Demo) badge
- Data Source tab shows provider status
- Diagnostics available in Debug tab

### For Production

1. **Contact SofaScore** for official API access
2. **Or use alternative provider** (API-Football, etc.)
3. **Update configuration:**

```python
# In app/config/data_source_config.py
# Add official API key
sofascore_api_key: Optional[str] = None

# In __post_init__
self.sofascore_api_key = os.getenv("SOFASCORE_API_KEY")
```

4. **Use API key in requests:**

```python
# In app/providers/sofascore_provider.py
if self.config.api_key:
    self.session.headers.update({
        "Authorization": f"Bearer {self.config.api_key}"
    })
```

## Current Dashboard Behavior

The dashboard **honestly reports** the data source:

### When DATA_PROVIDER not set (default):
- Shows: 🔴 MOCK DATA (Demo)
- Provider: mock
- Data: Synthetic demo data

### When DATA_PROVIDER=sofascore but API blocked:
- Shows: ❌ REAL DATA NOT CONNECTED
- Provider: sofascore
- Error: 403 Forbidden
- Falls back to: MOCK data (if AUTO mode)

### When real data works:
- Shows: 🟢 REAL DATA (SofaScore)
- Provider: sofascore
- Data: Real matches from API

## Testing Real Data

To test if real data works:

```bash
# Set provider
$env:DATA_PROVIDER="sofascore"

# Run verification
python scripts/verify_real_data_pipeline.py

# If successful, run dashboard
streamlit run dashboard_v4.py
```

## Next Steps

1. **Accept MOCK mode** for development
2. **Contact SofaScore** or choose alternative provider for production
3. **Update documentation** with chosen provider
4. **Implement API key support** when available

## Important Notes

- ✅ The code is **correct** - SofaScoreProvider is properly implemented
- ✅ The dashboard is **honest** - clearly shows MOCK vs REAL
- ❌ The API is **blocked** - this is external, not a code issue
- 🎯 **Solution**: Use official API or alternative provider for real data

## Contact

For official SofaScore API access:
- Website: https://www.sofascore.com
- Email: Contact through their website
- Note: Mention you need API access for sports data analysis
