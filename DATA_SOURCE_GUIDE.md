# Data Source Configuration Guide

## Overview

The project now supports switching between mock data and real data sources through a centralized configuration system. This ensures you always know whether you're analyzing synthetic test data or real match data.

## Configuration

### Environment Variables

Set the `DATA_PROVIDER` environment variable to control the data source:

```bash
# Use mock data (default)
DATA_PROVIDER=mock

# Use real data from SofaScore
DATA_PROVIDER=sofascore

# Try real data first, fallback to mock
DATA_PROVIDER=auto
```

### Full Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_PROVIDER` | `mock` | Data source: `mock`, `sofascore`, or `auto` |
| `CACHE_ENABLED` | `true` | Enable API response caching |
| `CACHE_TTL_SECONDS` | `300` | Cache time-to-live in seconds |
| `SHOW_SOURCE_LABELS` | `true` | Display REAL/MOCK labels in dashboard |
| `WARN_ON_MOCK` | `true` | Show warning when using mock data |
| `ODDS_API_KEY` | `null` | API key for external odds provider |

## Usage Examples

### 1. Run Dashboard with Real Data

```bash
# Windows (PowerShell)
$env:DATA_PROVIDER="sofascore"; streamlit run dashboard_v3.py

# Windows (CMD)
set DATA_PROVIDER=sofascore && streamlit run dashboard_v3.py

# Linux/Mac
DATA_PROVIDER=sofascore streamlit run dashboard_v3.py
```

### 2. Run Pipeline Test with Real Data

```bash
DATA_PROVIDER=sofascore python scripts/test_real_data_pipeline.py
```

### 3. Fetch Real Matches

```bash
DATA_PROVIDER=sofascore python scripts/fetch_real_matches.py
```

### 4. Use Mock Data (Default)

```bash
# No environment variable needed
python scripts/fetch_real_matches.py
streamlit run dashboard_v3.py
```

## Data Sources

### Mock Data (Default)

- **Source**: `MockDataProvider`
- **Data**: Synthetic, generated on-the-fly
- **Use Case**: Testing, development, offline work
- **Characteristics**:
  - 4 hardcoded competitions (England Women's Championship, etc.)
  - 20+ hardcoded teams
  - Realistic but fake match results
  - No network connection required

### SofaScore (Real Data)

- **Source**: `SofaScoreProvider`
- **Data**: Real-time from SofaScore public API
- **Use Case**: Production, real analysis
- **Characteristics**:
  - Real match data from api.sofascore.com
  - Rate limited to 30 requests/minute
  - Requires internet connection
  - Cached locally for 5 minutes by default

### Auto Mode

- **Source**: Attempts `SofaScoreProvider` first, falls back to `MockDataProvider`
- **Use Case**: Graceful degradation
- **Characteristics**:
  - Tries real data first
  - Falls back to mock if API unavailable
  - Useful for intermittent connectivity

## Dashboard Indicators

The dashboard now displays clear indicators of the data source:

### Sidebar Badge

- **🟢 REAL DATA (SofaScore)**: Using real match data
- **🔴 MOCK DATA**: Using synthetic test data

### Page Captions

Each page shows:
```
Data: [REAL] REAL DATA (SofaScore)
```
or
```
Data: [MOCK] MOCK DATA
```

### Warnings

When using mock data, a warning appears:
```
⚠️ Using synthetic data. Set DATA_PROVIDER=sofascore for real data.
```

## Data Provenance Tracking

The `DataSourceManager` tracks every data fetch with provenance information:

```python
from app.providers.data_source_manager import DataSourceManager

manager = DataSourceManager()

# Fetch data
matches = manager.get_today_matches()

# Check source
print(manager.is_real_data)  # True/False
print(manager.source_label)  # "REAL DATA (SofaScore)" or "MOCK DATA"

# Get full status
status = manager.get_source_status()
print(status['provenance_log'])  # List of all data fetches
```

### Log Format

Every data fetch is logged with:
```
REAL_DATA: get_today_matches
MOCK_DATA: get_team_recent_matches(team_123)
```

## Scripts Updated

All scripts now use `DataSourceManager`:

- `dashboard_v3.py` - Main dashboard
- `debug_pipeline.py` - Pipeline testing
- `calibrate_scoring.py` - Scoring calibration
- `test_scanner_integration.py` - Scanner tests
- `fetch_real_matches.py` - Data fetching
- `test_real_data_pipeline.py` - Pipeline tests

## Testing Real Data

### Quick Test

```bash
# Test SofaScore connection
python scripts/test_sofascore_provider.py

# Test full pipeline with real data
DATA_PROVIDER=sofascore python scripts/test_real_data_pipeline.py
```

### Expected Output

When using real data, you should see:
```
✅ SUCCESS: Found 45 matches
[REAL] Example:
  Manchester United vs Liverpool
  League: Premier League
  Date: 2026-05-27 15:00
```

## Troubleshooting

### No Matches Found

**Problem**: `No matches available` error

**Solutions**:
1. Check internet connection
2. Verify SofaScore API is accessible
3. Try `DATA_PROVIDER=auto` for fallback
4. Check rate limiting (30 req/min)

### Rate Limiting

**Problem**: Too many requests error

**Solution**: Increase `CACHE_TTL_SECONDS` to reduce API calls

### Mock Data Still Showing

**Problem**: Dashboard shows MOCK despite setting `DATA_PROVIDER=sofascore`

**Solutions**:
1. Verify environment variable is set correctly
2. Restart the application
3. Check logs for connection errors
4. Try `DATA_PROVIDER=auto` to see fallback behavior

## Best Practices

### Development

Use mock data for development:
```bash
# Default (no env var needed)
python scripts/debug_anomaly.py
```

### Testing

Test with both sources:
```bash
# Test with mock
python scripts/test_real_data_pipeline.py

# Test with real
DATA_PROVIDER=sofascore python scripts/test_real_data_pipeline.py
```

### Production

Always use real data with caching:
```bash
DATA_PROVIDER=sofascore CACHE_ENABLED=true streamlit run dashboard_v3.py
```

### CI/CD

Use mock data in CI/CD pipelines:
```bash
DATA_PROVIDER=mock pytest tests/
```

## Migration from Old Code

### Before

```python
from app.providers import MockDataProvider

provider = MockDataProvider()
matches = provider.get_today_matches()
```

### After

```python
from app.providers.data_source_manager import DataSourceManager

manager = DataSourceManager()
matches = manager.get_today_matches()

# Check source
if manager.is_real_data:
    print("Using real data")
else:
    print("Using mock data")
```

## API Reference

### DataSourceConfig

```python
from app.config.data_source_config import DataSourceConfig

config = DataSourceConfig()
print(config.source_type)  # DataSourceType.MOCK
print(config.is_real_data)  # False
print(config.source_label)  # "MOCK DATA"
```

### DataSourceManager

```python
from app.providers.data_source_manager import DataSourceManager

manager = DataSourceManager()

# Fetch data
matches = manager.get_today_matches()
history = manager.get_team_recent_matches(team_id, limit=10)
h2h = manager.get_head_to_head(team_a_id, team_b_id)
odds = manager.get_match_odds(match_id)

# Get status
status = manager.get_source_status()
```

## Summary

- **Default**: Mock data (safe, offline)
- **Real Data**: Set `DATA_PROVIDER=sofascore`
- **Auto Mode**: Set `DATA_PROVIDER=auto`
- **Dashboard**: Shows REAL/MOCK badges
- **Logs**: Every data fetch is labeled REAL_DATA or MOCK_DATA
- **Goal**: Always know if you're analyzing real or synthetic data
