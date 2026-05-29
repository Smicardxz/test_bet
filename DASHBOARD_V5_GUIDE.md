# Dashboard V5 - Real Data Guide

## Overview

Dashboard V5 is optimized for **real data from API-Football** without odds.

### Key Features

1. **Real Match Data** - Live matches from API-Football
2. **Statistical Signals** - Analysis without betting odds
3. **League Targeting** - Focus on obscure/lower leagues
4. **Clear Data Source** - Always shows REAL vs MOCK
5. **No Fake Odds** - Honest about free tier limitations

## Running the Dashboard

### Option 1: PowerShell Script (Recommended)

```powershell
.\run_dashboard.ps1
```

This automatically sets:
- `DATA_PROVIDER=api_football`
- `API_FOOTBALL_KEY`
- `API_FOOTBALL_URL`

### Option 2: Manual Environment Variables

```powershell
$env:DATA_PROVIDER="api_football"
$env:API_FOOTBALL_KEY="a977a26c11eb494d3462b6a3cbc0aecc"
$env:API_FOOTBALL_URL="https://v3.football.api-sports.io"
streamlit run dashboard_v5.py
```

### Option 3: .env File

Ensure `.env` exists with:
```env
DATA_PROVIDER=api_football
API_FOOTBALL_KEY=a977a26c11eb494d3462b6a3cbc0aecc
API_FOOTBALL_URL=https://v3.football.api-sports.io
```

Then run:
```bash
streamlit run dashboard_v5.py
```

## Dashboard Sections

### 1. Header & KPIs
- **Data Source Badge**: Shows REAL DATA (API-Football) or MOCK DATA
- **Odds Status**: Shows "NO ODDS (Free Tier)" warning
- **6 KPI Cards**:
  - Matches Fetched
  - Countries
  - Competitions
  - Target Matches
  - API Status
  - Odds Availability

### 2. Tab: Today Scanner 🎯
Shows real matches from target leagues:
- Match details (home vs away)
- Country & competition
- Kickoff time
- League categories (Lower Division, Obscure, Youth, Women, Reserve)
- Target score (0-100)
- Data source badge (REAL/MOCK)
- Statistical profile in expander

**Categories:**
- 🔵 Lower Division - 2nd tier and below
- 🟣 Obscure Country - Kazakhstan, Vietnam, etc.
- 🟢 Youth - U21, U19, U23
- 🔴 Women - Women's leagues
- 🟠 Reserve - Reserve teams

### 3. Tab: Statistical Signals 📊
Statistical analysis **without odds**:
- Grouped by market type (HT Under, FT Under, BTTS)
- Confidence scores
- Data quality scores
- Sample sizes

**Warning displayed:**
```
⚠️ NO REAL ODDS AVAILABLE
Free tier API-Football does not provide odds data.
Signals below are statistical only - not actionable bets.
```

### 4. Tab: Bet Builder 🎲
**Disabled without odds**

Shows message:
```
Combinations Disabled

Bet combinations require real odds data.

Solutions:
- Upgrade to API-Football Pro plan (~$20-50/month)
- Add separate odds provider (The Odds API, etc.)
- Use statistical signals for research only
```

### 5. Tab: Source Status 📡
Detailed provider information:
- Provider name (api_football)
- Mode (REAL/MOCK)
- API status
- Cache status
- Coverage stats
- Error log (if any)
- Odds status with upgrade suggestions

### 6. Tab: Diagnostics 🔍
Complete diagnostic data:
- Fixtures breakdown (real/mock/outdated)
- Countries detected (top 10)
- Leagues targeted (top 10)
- Cache information
- Raw JSON diagnostics

## What You'll See

### With API-Football (Real Data)
```
🟢 REAL DATA (API-Football)
⚠️ NO ODDS (Free Tier)

Matches Fetched: 116
Countries: 33
Competitions: 44
Target Matches: 27
API Status: ✅ OK
Odds: ❌ N/A
```

### Today Scanner Example
```
Kazakhstan vs Uzbekistan
📍 Kazakhstan - First Division
⏰ 14:30 UTC
🟢 REAL

[Lower Division] [Obscure Country]
Target Score: 75/100

📈 Statistical Profile
  Match Info:
  - Market: HT Under
  - Line: 0.5
  - Confidence: 0.72
  - Priority: 0.85
  
  Data Quality:
  - Quality Score: 0.68
  - Sample Size: 8
  
  ⚠️ NO ODDS — STATISTICAL SIGNAL ONLY
```

## Understanding the Data

### Target Score (0-100)
Indicates how well a league matches our strategy:
- **80-100**: Perfect target (obscure + lower division)
- **50-79**: Good target (one major criterion)
- **20-49**: Moderate target
- **0-19**: Not a target (major league)

### Categories Explained
- **Lower Division**: 2nd tier and below in any country
- **Obscure Country**: Kazakhstan, Vietnam, Thailand, etc.
- **Youth**: U21, U19, U23, U20 competitions
- **Women**: Women's football worldwide
- **Reserve**: Reserve/B teams

### Statistical Signals
Without odds, we show:
- **Confidence**: Statistical confidence in the pattern
- **Data Quality**: Quality of historical data
- **Sample Size**: Number of matches analyzed

These are **research signals**, not actionable bets.

## Limitations

### Free Tier API-Football
- ✅ Fixtures (matches) - Available
- ✅ Teams - Available
- ✅ Leagues - Available
- ✅ Basic stats - Available
- ❌ Odds - **NOT available**
- ❌ Advanced stats - Limited

### What This Means
1. **No real betting** - Can't place bets without odds
2. **Research only** - Use for scouting and analysis
3. **Statistical signals** - Patterns detected, but not actionable
4. **Upgrade needed** - For real betting, need Pro plan or odds provider

## Upgrade Options

### Option 1: API-Football Pro
- Cost: ~$20-50/month
- Includes: Real odds, more requests, advanced stats
- Best for: All-in-one solution

### Option 2: Separate Odds Provider
- The Odds API
- Odds API
- BetFair API
- Best for: Keeping fixtures free, paying only for odds

### Option 3: Stay Free Tier
- Use for: Research and scouting
- Identify: Target matches and leagues
- Prepare: For when you add odds later

## Troubleshooting

### "API_FOOTBALL_KEY not found"
- Use `run_dashboard.ps1` script
- Or set environment variable manually
- Or check `.env` file exists

### "No matches found"
- Normal on some days
- Try on match days (weekends, midweek)
- Check diagnostics tab for errors

### "MOCK DATA" showing
- Environment variable not set
- Use `run_dashboard.ps1`
- Or set `DATA_PROVIDER=api_football`

### Dashboard won't load
- Check API key is valid
- Check internet connection
- Check quota (100 requests/day)
- View diagnostics for errors

## Best Practices

1. **Run once per day** - Conserve API quota
2. **Use cache** - Data cached for 5 minutes
3. **Focus on target matches** - Filter by target score
4. **Research mode** - Use for scouting without odds
5. **Plan upgrades** - When ready for real betting

## Next Steps

1. **Explore matches** - See what leagues are available
2. **Identify patterns** - Note which leagues have signals
3. **Track coverage** - Monitor which countries appear
4. **Decide on odds** - Upgrade or add provider when ready
5. **Refine strategy** - Adjust targeting based on coverage

## Summary

Dashboard V5 is a **research tool** for:
- ✅ Discovering obscure matches
- ✅ Analyzing statistical patterns
- ✅ Scouting target leagues
- ✅ Preparing for real betting

It is **NOT** for:
- ❌ Placing real bets (no odds)
- ❌ Live betting (no live data)
- ❌ Guaranteed profits (research only)

Use it to **scout and prepare**, then upgrade for real betting when ready.
