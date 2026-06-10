"""
Main FastAPI application for local anomaly scanner
Simple local-only API for detecting bookmaker anomalies in obscure football leagues
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Local Football Anomaly Scanner",
    description="Local tool for detecting bookmaker line anomalies in obscure football leagues",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for local development only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes
try:
    from app.api.routes import scanner, matches, analysis, markets
    
    app.include_router(scanner.router, prefix="/api")
    app.include_router(matches.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(markets.router, prefix="/api")
except ImportError as e:
    print(f"⚠️ Warning: Some routes not available: {e}")


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": "Local Football Anomaly Scanner",
        "version": "2.0.0",
        "status": "running",
        "type": "local",
        "docs": "/docs",
        "description": "Local-only API for detecting bookmaker anomalies in obscure football leagues",
        "endpoints": {
            "scanner": {
                "top_anomalies": "/api/scanner/top-anomalies",
                "scan": "/api/scanner/scan"
            },
            "matches": {
                "today": "/api/matches/today",
                "by_id": "/api/matches/{match_id}"
            },
            "analysis": {
                "match": "/api/analysis/{match_id}"
            },
            "markets": {
                "ht_under": "/api/markets/top-ht-under",
                "extreme_under": "/api/markets/top-extreme-under",
                "btts": "/api/markets/top-btts-anomalies"
            }
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "type": "local"}


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Local Anomaly Scanner started")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🏠 Local mode - SQLite database")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
