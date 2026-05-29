# Run Dashboard V5 with API-Football
$env:DATA_PROVIDER="api_football"
$env:API_FOOTBALL_KEY="a977a26c11eb494d3462b6a3cbc0aecc"
$env:API_FOOTBALL_URL="https://v3.football.api-sports.io"

Write-Host "Starting Dashboard V5 with API-Football..." -ForegroundColor Green
Write-Host "Provider: $env:DATA_PROVIDER" -ForegroundColor Cyan
Write-Host "API Key: $($env:API_FOOTBALL_KEY.Substring(0,10))..." -ForegroundColor Cyan

streamlit run dashboard_v5.py
