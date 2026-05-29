"""
Data Providers Package
Clean abstraction layer for external data sources
"""

from app.providers.base_provider import BaseDataProvider, ProviderConfig
from app.providers.mock_provider import MockDataProvider

__all__ = [
    "BaseDataProvider",
    "ProviderConfig",
    "MockDataProvider",
]
