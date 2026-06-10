# Environment Setup Guide

## Quick Setup

### Step 1: Copy .env template

```powershell
Copy-Item .env.template .env
```

The `.env` file is already configured with the API key.

### Step 2: Run Dashboard

**Option A: Use PowerShell script (Recommended)**
```powershell
.\run_dashboard.ps1
```

**Option B: Set environment variable manually**
```powershell
$env:DATA_PROVIDER="api_football"
$env:API_FOOTBALL_KEY="a977a26c11eb494d3462b6a3cbc0aecc"
streamlit run dashboard_v5.py
```

**Option C: Use .env file**
```powershell
# Ensure .env exists with API key
streamlit run dashboard_v5.py
```

## Verification

The dashboard should show:
```
🟢 REAL DATA (API-Football)
⚠️ NO ODDS (Free Tier)
```

If you see:
```
🔴 MOCK DATA
```

Then the API key is not loaded. Try:

1. **Check .env file exists:**
```powershell
Test-Path .env
```

2. **Check .env content:**
```powershell
Get-Content .env
```

3. **Use run_dashboard.ps1:**
```powershell
.\run_dashboard.ps1
```

## Troubleshooting

### "API_FOOTBALL_KEY not found"

**Solution 1: Use run_dashboard.ps1**
```powershell
.\run_dashboard.ps1
```

**Solution 2: Create .env file**
```powershell
# Copy template
Copy-Item .env.template .env

# Verify
Get-Content .env
```

**Solution 3: Set environment variable**
```powershell
$env:API_FOOTBALL_KEY="a977a26c11eb494d3462b6a3cbc0aecc"
$env:DATA_PROVIDER="api_football"
streamlit run dashboard_v5.py
```

### Dashboard shows MOCK data

The dashboard will fallback to MOCK data if:
- API key not found
- API key invalid
- API unreachable

Check the warning message in the dashboard for instructions.

### .env file not loading

Streamlit may not load .env automatically. Use:

```powershell
.\run_dashboard.ps1
```

This script sets environment variables before launching Streamlit.

## Files

- `.env.template` - Template with API key
- `.env` - Your actual environment file (create from template)
- `run_dashboard.ps1` - PowerShell launch script
- `dashboard_v5.py` - Dashboard application

## API Key

The provided API key is:
```
a977a26c11eb494d3462b6a3cbc0aecc
```

This is a **free tier** key with:
- 100 requests/day
- No odds data
- Basic statistics

## Next Steps

1. ✅ Setup environment (this guide)
2. ✅ Run dashboard
3. ✅ Verify real data connection
4. ✅ Explore matches and leagues
5. ⏳ Decide on odds provider (optional)

## Support

If issues persist:

1. Check API quota: https://dashboard.api-football.com
2. Verify API key is valid
3. Check internet connection
4. View dashboard diagnostics tab
