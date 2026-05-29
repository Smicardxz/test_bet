"""
Data Source Configuration
Centralized configuration for data providers

Usage:
    from app.config.data_source_config import DataSourceConfig, DataSourceType
    
    config = DataSourceConfig()
    provider = config.get_provider()
"""

import os
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class DataSourceType(str, Enum):
    """Available data source types"""
    MOCK = "mock"              # Synthetic data for testing
    API_FOOTBALL = "api_football"  # API-Football / API-Sports (recommended)
    SOFASCORE = "sofascore"    # SofaScore public API (deprecated - 403 errors)
    AUTO = "auto"              # Try real first, fallback to mock


@dataclass
class DataSourceConfig:
    """
    Data source configuration
    
    Reads from environment variable DATA_PROVIDER or defaults to mock
    """
    
    # Primary data source
    source_type: DataSourceType = DataSourceType.MOCK
    
    # API configuration
    sofascore_base_url: str = "https://api.sofascore.com/api/v1"
    sofascore_rate_limit: int = 30  # requests per minute
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    
    # Odds provider
    odds_provider: str = "mock"  # or "external" with API key
    odds_api_key: Optional[str] = None
    
    # Display settings
    show_data_source_labels: bool = True
    warn_on_mock: bool = True
    
    def __post_init__(self):
        """Initialize from environment variables"""
        
        # Read DATA_PROVIDER from environment
        env_provider = os.getenv("DATA_PROVIDER", "mock").lower()
        
        if env_provider == "api_football":
            self.source_type = DataSourceType.API_FOOTBALL
        elif env_provider == "sofascore":
            self.source_type = DataSourceType.SOFASCORE
        elif env_provider == "auto":
            self.source_type = DataSourceType.AUTO
        else:
            self.source_type = DataSourceType.MOCK
        
        # Read other env vars
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.show_data_source_labels = os.getenv("SHOW_SOURCE_LABELS", "true").lower() == "true"
        self.warn_on_mock = os.getenv("WARN_ON_MOCK", "true").lower() == "true"
        
        # Odds API key
        self.odds_api_key = os.getenv("ODDS_API_KEY")
        if self.odds_api_key:
            self.odds_provider = "external"
    
    @property
    def is_real_data(self) -> bool:
        """Check if using real data"""
        return self.source_type in (DataSourceType.API_FOOTBALL, DataSourceType.SOFASCORE, DataSourceType.AUTO)
    
    @property
    def is_mock_data(self) -> bool:
        """Check if using mock data"""
        return self.source_type == DataSourceType.MOCK
    
    @property
    def source_label(self) -> str:
        """Get human-readable source label"""
        labels = {
            DataSourceType.MOCK: "MOCK DATA",
            DataSourceType.API_FOOTBALL: "REAL DATA (API-Football)",
            DataSourceType.SOFASCORE: "REAL DATA (SofaScore)",
            DataSourceType.AUTO: "REAL DATA (Auto)"
        }
        return labels.get(self.source_type, "UNKNOWN")
    
    def get_provider(self):
        """
        Get configured data provider instance
        
        Returns:
            BaseDataProvider instance
        """
        from app.providers import MockDataProvider, ProviderConfig
        from app.providers.sofascore_provider import SofaScoreProvider
        from app.providers.api_football_provider import ApiFootballProvider
        
        if self.source_type == DataSourceType.MOCK:
            return MockDataProvider()
        
        elif self.source_type == DataSourceType.API_FOOTBALL:
            # API-Football provider (recommended)
            # STRICT MODE: No fallback to mock
            import logging
            logger = logging.getLogger(__name__)
            
            # Check if API key is present
            api_key = os.getenv("API_FOOTBALL_KEY", "")
            
            if not api_key:
                error_msg = (
                    "API_FOOTBALL_KEY not found in environment.\n"
                    "DATA_PROVIDER is set to 'api_football' but API key is missing.\n"
                    "Please set API_FOOTBALL_KEY in .env file.\n"
                    "Example: API_FOOTBALL_KEY=your_key_here\n"
                    "\n"
                    "STRICT MODE: No fallback to mock data in api_football mode."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"API_FOOTBALL_KEY present: YES (length: {len(api_key)})")
            
            try:
                provider = ApiFootballProvider()
                logger.info("ApiFootballProvider initialized successfully")
                return provider
            except Exception as e:
                logger.error(f"Failed to initialize ApiFootballProvider: {e}")
                raise
        
        elif self.source_type == DataSourceType.SOFASCORE:
            config = ProviderConfig(
                name="sofascore",
                enabled=True,
                cache_enabled=self.cache_enabled,
                cache_ttl_seconds=self.cache_ttl_seconds,
                rate_limit_per_minute=self.sofascore_rate_limit
            )
            return SofaScoreProvider(config)
        
        elif self.source_type == DataSourceType.AUTO:
            # Try API-Football first, fallback to mock
            try:
                provider = ApiFootballProvider()
                # Test connection
                status = provider.test_connection()
                if status.get("key_valid"):
                    return provider
            except Exception:
                pass
            
            # Fallback to mock
            return MockDataProvider()
        
        return MockDataProvider()
    
    def get_odds_provider(self):
        """Get configured odds provider"""
        from app.providers.odds import MockOddsProvider
        from app.providers.odds.external_odds_provider import ExternalOddsProvider
        
        if self.odds_provider == "external" and self.odds_api_key:
            return ExternalOddsProvider(api_key=self.odds_api_key)
        
        return MockOddsProvider()
    
    def to_dict(self) -> dict:
        """Serialize configuration"""
        return {
            "source_type": self.source_type.value,
            "source_label": self.source_label,
            "is_real_data": self.is_real_data,
            "is_mock_data": self.is_mock_data,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "odds_provider": self.odds_provider,
            "show_data_source_labels": self.show_data_source_labels,
            "warn_on_mock": self.warn_on_mock
        }
