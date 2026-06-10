"""
Data Source Manager
Manages provider selection and tracks data provenance

Ensures every piece of data is labeled as REAL or MOCK
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.config.data_source_config import DataSourceConfig, DataSourceType
from app.providers.base_provider import BaseDataProvider


logger = logging.getLogger(__name__)


@dataclass
class DataProvenance:
    """Tracks the source of a piece of data"""
    source_type: str  # "REAL" or "MOCK"
    provider_name: str
    endpoint: str
    timestamp: str
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "provider": self.provider_name,
            "endpoint": self.endpoint,
            "timestamp": self.timestamp,
            "cached": self.cached
        }


class DataSourceManager:
    """
    Data Source Manager
    
    Handles provider switching and data provenance tracking.
    All data fetched through this manager is labeled REAL or MOCK.
    """
    
    def __init__(self, config: Optional[DataSourceConfig] = None):
        """Initialize manager with configuration"""
        self.config = config or DataSourceConfig()
        self._provider: Optional[BaseDataProvider] = None
        self._odds_provider = None
        self._provenance_log: list = []
        
        logger.info(f"DataSourceManager initialized: {self.config.source_label}")
        
        if self.config.is_mock_data and self.config.warn_on_mock:
            logger.warning("⚠️  USING MOCK DATA - Results are synthetic")
    
    @property
    def provider(self) -> BaseDataProvider:
        """Get current data provider (lazy init)"""
        if self._provider is None:
            self._provider = self.config.get_provider()
            logger.info(f"Provider loaded: {self._provider.config.name}")
        return self._provider
    
    @property
    def odds_provider(self):
        """Get current odds provider (lazy init)"""
        if self._odds_provider is None:
            self._odds_provider = self.config.get_odds_provider()
        return self._odds_provider
    
    @property
    def is_real_data(self) -> bool:
        """Check if using real data"""
        return self.config.is_real_data
    
    @property
    def is_mock_data(self) -> bool:
        """Check if using mock data"""
        return self.config.is_mock_data
    
    @property
    def source_label(self) -> str:
        """Get current source label"""
        return self.config.source_label
    
    def _log_provenance(self, endpoint: str, is_real: bool, cached: bool = False):
        """Log data provenance"""
        provenance = DataProvenance(
            source_type="REAL" if is_real else "MOCK",
            provider_name=self.provider.config.name,
            endpoint=endpoint,
            timestamp=datetime.now().isoformat(),
            cached=cached
        )
        self._provenance_log.append(provenance)
        
        prefix = "REAL_DATA" if is_real else "MOCK_DATA"
        cache_info = " [CACHED]" if cached else ""
        logger.info(f"{prefix}: {endpoint}{cache_info}")
    
    def get_today_matches(self, competition_ids=None):
        """Fetch today's matches with provenance tracking"""
        response = self.provider.get_today_matches(competition_ids)
        
        is_real = self.provider.config.name != "mock"
        self._log_provenance("get_today_matches", is_real)
        
        return response
    
    def get_team_recent_matches(self, team_id: str, limit: int = 10):
        """Fetch team history with provenance tracking"""
        response = self.provider.get_team_recent_matches(team_id, limit)
        
        is_real = self.provider.config.name != "mock"
        self._log_provenance(f"get_team_recent_matches({team_id})", is_real)
        
        return response
    
    def get_head_to_head(self, team_a_id: str, team_b_id: str):
        """Fetch H2H with provenance tracking"""
        response = self.provider.get_head_to_head(team_a_id, team_b_id)
        
        is_real = self.provider.config.name != "mock"
        self._log_provenance("get_head_to_head", is_real)
        
        return response
    
    def get_match_odds(
        self,
        match_id: str,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None
    ):
        """Fetch odds with provenance tracking - Phase 6: pass team names for fuzzy matching"""
        response = self.odds_provider.get_match_odds(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team
        )

        is_real = self.odds_provider.config.name != "mock_odds"
        self._log_provenance("get_match_odds", is_real)

        return response
    
    def get_source_status(self) -> Dict[str, Any]:
        """
        Get complete source status
        
        Returns:
            Dict with source info and provenance log
        """
        return {
            "source_type": self.config.source_type.value,
            "source_label": self.source_label,
            "is_real_data": self.is_real_data,
            "is_mock_data": self.is_mock_data,
            "provider_name": self.provider.config.name,
            "odds_provider": self.odds_provider.config.name,
            "cache_enabled": self.config.cache_enabled,
            "data_source_labels_enabled": self.config.show_data_source_labels,
            "provenance_log": [p.to_dict() for p in self._provenance_log[-20:]],
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_provenance_log(self):
        """Clear provenance log"""
        self._provenance_log.clear()
    
    def __repr__(self):
        return f"DataSourceManager({self.source_label})"
