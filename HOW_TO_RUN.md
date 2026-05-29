# How to Run the Dashboard

## Dashboard V4 - Market Inefficiency Scanner

### Quick Start (MOCK Mode - Demo Data)

```bash
streamlit run dashboard_v4.py
```

This will start the dashboard with **synthetic demo data**.

---

## Running with REAL Data (SofaScore)

### Windows PowerShell

```powershell
$env:DATA_PROVIDER="sofascore"
streamlit run dashboard_v4.py
```

### Windows CMD

```cmd
set DATA_PROVIDER=sofascore
streamlit run dashboard_v4.py
```

### Linux / Mac

```bash
export DATA_PROVIDER=sofascore
streamlit run dashboard_v4.py
```

---

## Data Source Modes

### 1. MOCK Mode (Default)
- **Provider:** MockDataProvider
- **Data:** Synthetic, realistic demo data
- **Use case:** Testing, development, demo
- **Badge:** 🔴 MOCK DATA (Demo)

```bash
# No environment variable needed
streamlit run dashboard_v4.py
```

### 2. REAL Mode (SofaScore)
- **Provider:** SofaScoreProvider
- **Data:** Real matches from SofaScore API
- **Use case:** Production, real analysis
- **Badge:** 🟢 REAL DATA (SofaScore)

```bash
# Set DATA_PROVIDER environment variable
$env:DATA_PROVIDER="sofascore"
streamlit run dashboard_v4.py
```

### 3. AUTO Mode (Try Real, Fallback to Mock)
- **Provider:** Tries SofaScore, falls back to Mock if error
- **Data:** Real if available, synthetic otherwise
- **Use case:** Resilient production

```bash
$env:DATA_PROVIDER="auto"
streamlit run dashboard_v4.py
```

---

## Odds Configuration

### Mock Odds (Default)
Odds are synthetic even in REAL mode unless you configure an external odds provider.

### Real Odds (Requires API Key)
To use real odds from an external provider:

```bash
$env:ODDS_API_KEY="your-api-key-here"
streamlit run dashboard_v4.py
```

---

## Cache Configuration

### Enable Cache (Default)
```bash
$env:CACHE_ENABLED="true"
streamlit run dashboard_v4.py
```

### Disable Cache
```bash
$env:CACHE_ENABLED="false"
streamlit run dashboard_v4.py
```

---

## Verifying Data Source

### Check the Dashboard
1. Look at the header badge:
   - 🔴 MOCK DATA (Demo) = Synthetic data
   - 🟢 REAL DATA (SofaScore) = Real data from SofaScore

2. Go to **Data Source** tab
   - Shows provider name
   - Shows data mode
   - Shows matches fetched
   - Shows any errors

### Check the Console
When you run the dashboard, you'll see logs like:

```
⚠️  USING MOCK DATA - Results are synthetic
```

or

```
✅ USING REAL DATA - SofaScore provider active
```

---

## Troubleshooting

### Dashboard shows MOCK but I set DATA_PROVIDER=sofascore

**Solution:** Environment variable might not be set correctly.

Try:
```powershell
# Verify it's set
echo $env:DATA_PROVIDER

# Set it again
$env:DATA_PROVIDER="sofascore"

# Run dashboard
streamlit run dashboard_v4.py
```

### SofaScore returns errors

**Possible causes:**
- Rate limiting (too many requests)
- Network issues
- API changes

**Solution:** Use AUTO mode to fallback to mock:
```bash
$env:DATA_PROVIDER="auto"
streamlit run dashboard_v4.py
```

### No odds available in REAL mode

**Explanation:** SofaScore provider fetches matches but odds require a separate API.

**Solution:** Either:
1. Accept mock odds (default)
2. Configure ODDS_API_KEY for real odds

---

## Dashboard Features

### Tab 1: Today Scanner
- View top single bets
- See anomaly scores, confidence, risk
- Expand for detailed signals and explanations

### Tab 2: Bet Builder
- View recommended combinations (max 5)
- See combined odds and confidence
- Understand why combinations are suggested

### Tab 3: Match Detail
- Detailed match analysis (coming soon)
- Historical stats, H2H, variance

### Tab 4: Data Source
- Verify provider status
- Check for errors
- See how to switch modes

### Tab 5: Debug
- View raw JSON data
- Inspect scan results
- Debug data structures

---

## Performance Tips

### 1. Enable Caching
Caching reduces API calls and speeds up the dashboard:
```bash
$env:CACHE_ENABLED="true"
```

### 2. Limit Results
The scanner limits results to 30 by default. This is configurable in the code.

### 3. Refresh Strategically
Use the "🔄 Refresh Data" button only when needed. Data is cached for 5 minutes.

---

## Next Steps

1. **Start with MOCK mode** to understand the interface
2. **Switch to REAL mode** when ready for live data
3. **Monitor the Data Source tab** to verify everything works
4. **Check combinations** in Bet Builder tab
5. **Explore match details** for deeper analysis

---

## Support

For issues or questions:
1. Check the **Data Source** tab for errors
2. Check the **Debug** tab for raw data
3. Review console logs for detailed error messages
4. Verify environment variables are set correctly
