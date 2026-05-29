"""
Cached Provider Wrapper
Wraps any provider with automatic caching
"""

from typing import List, Optional
from datetime import date
import logging

from app.providers.base_provider import BaseDataProvider, ProviderResponse
from app.cache import CacheService, CacheConfig
from app.cache.cache_service import CacheType


logger = logging.getLogger(__name__)


class CachedProvider(BaseDataProvider):
    """
    Wrapper that adds caching to any provider
    
    Usage:
        base_provider = SofaScoreProvider()
        cached_provider = CachedProvider(base_provider)
        
        # Now all calls are automatically cached
        response = cached_provider.get_today_matches()
    """
    
    def __init__(
        self,
        provider: BaseDataProvider,
        cache_service: Optional[CacheService] = None,
        cache_config: Optional[CacheConfig] = None
    ):
        """
        Initialize cached provider
        
        Args:
            provider: Base provider to wrap
            cache_service: Optional cache service instance
            cache_config: Optional cache configuration
        """
        # Use provider's config
        super().__init__(provider.config)
        
        self.provider = provider
        
        # Setup cache
        if cache_service:
            self.cache = cache_service
        else:
            self.cache = CacheService(cache_config or CacheConfig())
        
        logger.info(f"CachedProvider wrapping: {provider.config.name}")
    
    def get_today_matches(
        self,
        competition_ids: Optional[List[str]] = None
    ) -> ProviderResponse:
        """Get today's matches (cached)"""
        
        def fetch():
            response = self.provider.get_today_matches(competition_ids)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.TODAY_MATCHES,
            fetch_func=fetch,
            provider=self.provider.config.name,
            competition_ids=competition_ids or []
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response("Failed to fetch today's matches")
    
    def get_match_details(self, match_id: str) -> ProviderResponse:
        """Get match details (cached)"""
        
        def fetch():
            response = self.provider.get_match_details(match_id)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.MATCH_DETAILS,
            fetch_func=fetch,
            provider=self.provider.config.name,
            match_id=match_id
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response(f"Failed to fetch match {match_id}")
    
    def get_team_recent_matches(
        self,
        team_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get team recent matches (cached)"""
        
        def fetch():
            response = self.provider.get_team_recent_matches(team_id, limit)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.TEAM_RECENT,
            fetch_func=fetch,
            provider=self.provider.config.name,
            team_id=team_id,
            limit=limit
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response(f"Failed to fetch team {team_id} recent matches")
    
    def get_head_to_head(
        self,
        team_a_id: str,
        team_b_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """Get head-to-head (cached)"""
        
        def fetch():
            response = self.provider.get_head_to_head(team_a_id, team_b_id, limit)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.HEAD_TO_HEAD,
            fetch_func=fetch,
            provider=self.provider.config.name,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            limit=limit
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response(f"Failed to fetch H2H")
    
    def get_competition_matches(
        self,
        competition_id: str,
        match_date: Optional[date] = None
    ) -> ProviderResponse:
        """Get competition matches (cached)"""
        
        def fetch():
            response = self.provider.get_competition_matches(competition_id, match_date)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.COMPETITION_MATCHES,
            fetch_func=fetch,
            provider=self.provider.config.name,
            competition_id=competition_id,
            match_date=match_date
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response(f"Failed to fetch competition {competition_id} matches")
    
    def get_odds(self, match_id: str) -> ProviderResponse:
        """Get odds (cached)"""
        
        def fetch():
            response = self.provider.get_odds(match_id)
            return response.dict() if response.success else None
        
        cached_data = self.cache.get_or_fetch(
            cache_type=CacheType.ODDS,
            fetch_func=fetch,
            provider=self.provider.config.name,
            match_id=match_id
        )
        
        if cached_data:
            return ProviderResponse(**cached_data)
        
        return self._create_error_response(f"Failed to fetch odds for match {match_id}")
    
    def invalidate_cache(
        self,
        cache_type: Optional[CacheType] = None,
        **params
    ):
        """
        Invalidate cache entries
        
        Args:
            cache_type: Type to invalidate (None = all)
            **params: Parameters to identify specific entry
        """
        self.cache.invalidate(cache_type, **params)
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def cleanup_cache(self):
        """Cleanup cache (remove expired, enforce size limit)"""
        self.cache.cleanup()
