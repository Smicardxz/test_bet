"""
Main FastAPI application for the anomaly scanner
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.core.config import settings

app = FastAPI(
    title="Football Anomaly Scanner API",
    description="API for detecting bookmaker line anomalies in obscure football leagues",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["scanner"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Football Anomaly Scanner API",
        "version": "1.0.0",
        "endpoints": {
            "matches_today": "/api/v1/matches/today",
            "match_analysis": "/api/v1/analysis/{match_id}",
            "top_anomalies": "/api/v1/scanner/top-anomalies"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
