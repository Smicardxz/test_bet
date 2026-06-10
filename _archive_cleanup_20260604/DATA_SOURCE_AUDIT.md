# DATA SOURCE AUDIT

## PHASE 1 - Audit Results

### 1. SofaScore Provider Exists?
✅ **YES** - `app/providers/sofascore_provider.py` exists and is fully implemented

### 2. Is it used by the dashboard?
✅ **YES** - Dashboard uses `DataSourceManager` which can load SofaScore provider

### 3. Config to switch from MOCK to REAL?
✅ **YES** - Set environment variable:
```bash
# Windows PowerShell
$env:DATA_PROVIDER="sofascore"
streamlit run dashboard_v3.py

# Windows CMD
set DATA_PROVIDER=sofascore
streamlit run dashboard_v3.py

# Linux/Mac
export DATA_PROVIDER=sofascore
streamlit run dashboard_v3.py
```

### 4. Do matches come from SofaScore?
✅ **YES** - When `DATA_PROVIDER=sofascore`, matches are fetched from SofaScore API

### 5. Do odds come from real source?
⚠️ **PARTIAL** - SofaScore provider exists but odds are currently from MockOddsProvider
- Real odds require external API key via `ODDS_API_KEY` environment variable
- Without API key, odds are mocked even in REAL mode

### 6. Does cache contain real data?
✅ **YES** - Cache stores whatever provider returns (REAL or MOCK)
- Cache location: `.cache/` directory
- TTL: 300 seconds (5 minutes)

### 7. Why dashboard shows MOCK?
🔍 **REASON**: No environment variable set, defaults to MOCK
- Default in `DataSourceConfig`: `source_type = DataSourceType.MOCK`
- Dashboard reads from `os.getenv("DATA_PROVIDER", "mock")`

### 8. Which files control DATA_PROVIDER?
📁 **FILES**:
- `app/config/data_source_config.py` - Main configuration
- `app/providers/data_source_manager.py` - Provider management
- `dashboard_v3.py` - Uses DataSourceManager

### 9. How to launch in REAL mode?
```bash
# Set environment variable before running
$env:DATA_PROVIDER="sofascore"
streamlit run dashboard_v3.py
```

## Current Architecture

### Data Flow
```
Environment Variable (DATA_PROVIDER)
    ↓
DataSourceConfig (reads env)
    ↓
DataSourceManager (manages provider)
    ↓
Provider (MockDataProvider OR SofaScoreProvider)
    ↓
Scanner → BetCandidate → Dashboard
```

### Provider Selection Logic
- `MOCK`: Uses MockDataProvider (synthetic data)
- `sofascore`: Uses SofaScoreProvider (real API)
- `auto`: Tries SofaScore, falls back to Mock

### Data Source Labels
- Every scan result has `data_source` field: "MOCK" or "REAL"
- Source status tracked in scanner output
- Provenance logged by DataSourceManager

## Issues Found

### ❌ Issue 1: No visual DATA_PROVIDER selector in dashboard
**Impact**: User must set environment variable manually

### ❌ Issue 2: Odds always mocked unless ODDS_API_KEY set
**Impact**: Even in REAL mode, odds are synthetic

### ❌ Issue 3: No clear "Fetch Real Data" button
**Impact**: User doesn't know how to switch modes

### ❌ Issue 4: MOCK badge not prominent enough
**Impact**: User doesn't realize data is synthetic

### ❌ Issue 5: No source status section
**Impact**: Can't verify if SofaScore is actually working

## Recommendations

### 1. Add DATA SOURCE STATUS section
Show:
- Provider: mock / sofascore
- Mode: MOCK / REAL
- Matches fetched: X
- Odds source: mock / external
- Last update: timestamp
- Errors: list

### 2. Add mode switcher in UI
```python
data_mode = st.sidebar.selectbox(
    "Data Source",
    ["MOCK (Demo)", "REAL (SofaScore)"]
)
```

### 3. Add "Refresh Data" button
Clear cache and re-fetch from provider

### 4. Show prominent badge
Large, colored badge at top: 🟢 REAL DATA or 🔴 MOCK DATA

### 5. Separate odds status
Show if odds are real or mocked, even when matches are real

## Next Steps

1. ✅ Audit complete
2. ⏭️ Create dashboard_v4.py with new UX
3. ⏭️ Add DATA SOURCE STATUS section
4. ⏭️ Add mode switcher
5. ⏭️ Improve visual hierarchy
6. ⏭️ Document how to run in each mode
