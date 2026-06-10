# Environment Setup

## Create .env file

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

## Configure API-Football

Edit `.env` and add your API key:

```env
# Data Provider
DATA_PROVIDER=api_football

# API-Football Configuration
API_FOOTBALL_KEY=a977a26c11eb494d3462b6a3cbc0aecc
API_FOOTBALL_URL=https://v3.football.api-sports.io

# Odds Provider
ODDS_PROVIDER=api_football
```

## Test Connection

```bash
python scripts/test_api_football.py
```

Expected output:
```
✅ API REACHABLE
✅ KEY VALID
✅ REAL DATA CONNECTED
```

## Run Dashboard

```bash
streamlit run dashboard_v4.py
```

The dashboard will show:
- 🟢 REAL DATA (API-Football)
- Real matches from today
- Actual odds (if available)
