"""
Stats calculation services
"""

# Export TeamStats and provider_adapter for database-free stats calculation
from app.services.stats.provider_adapter import (
    TeamStats,
    add_provider_support_to_stats_engine,
    StatsEngineProviderAdapter
)

__all__ = [
    "TeamStats",
    "add_provider_support_to_stats_engine",
    "StatsEngineProviderAdapter"
]
