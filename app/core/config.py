"""
Configuration for local anomaly scanner
Simple configuration for local usage only
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings for local scanner"""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True
    
    # Stats calculation thresholds
    MIN_MATCHES_FOR_STATS: int = 5
    MIN_SAMPLE_SIZE: int = 8
    
    # Anomaly detection thresholds
    ANOMALY_THRESHOLD: float = 2.0
    MIN_ANOMALY_SCORE: float = 45.0
    MIN_PROBABILITY_GAP: float = 0.15
    
    # Confidence scoring thresholds
    CONFIDENCE_HIGH_THRESHOLD: float = 0.75
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50
    MAX_FALSE_POSITIVE_RISK: float = 0.30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
