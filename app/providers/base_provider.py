"""
Base Data Provider
Abstract interface for all data providers
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
import logging
from pathlib import Path
import json
import time
import hashlib

from app.providers.models import (
    MatchDetails,
    TeamStats,
    HeadToHead,
    MatchOdds,
    ProviderResponse
)


logger = logging.getLogger(__name__)


class ProviderConfig(BaseModel):
    """Provider configuration"""
    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 2
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_dir: str = ".cache/providers"


class BaseDataProvider(ABC):
    """
    Abstract base class for data providers
    
    All providers must implement these methods to ensure
    consistent interface across different data sources.
    """
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration"""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
        
        # Setup cache directory
        if config.cache_enabled:
            self.cache_dir = Path(config.cache_dir) / config.name
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting
        self._last_request_time = 0
        self._request_count = 0
        self._request_window_start = time.time()
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    def get_today_matches(
        self,
        competition_ids: Optional[List[str]] = None
    ) -> ProviderResponse:
        """
        Get all matches scheduled for today
        
        Args:
            competition_ids: Optional list of competition IDs to filter
            
        Returns:
            ProviderResponse with List[MatchDetails]
        """
        pass
    
    @abstractmethod
    def get_match_details(self, match_id: str) -> ProviderResponse:
        """
        Get detailed information for a specific match
        
        Args:
            match_id: Provider-specific match ID
            
        Returns:
            ProviderResponse with MatchDetails
        """
        pass
    
    @abstractmethod
    def get_team_recent_matches(
        self,
        team_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """
        Get recent matches for a team
        
        Args:
            team_id: Provider-specific team ID
            limit: Maximum number of matches to return
            
        Returns:
            ProviderResponse with List[MatchDetails]
        """
        pass
    
    @abstractmethod
    def get_head_to_head(
        self,
        team_a_id: str,
        team_b_id: str,
        limit: int = 10
    ) -> ProviderResponse:
        """
        Get head-to-head statistics between two teams
        
        Args:
            team_a_id: Provider-specific team A ID
            team_b_id: Provider-specific team B ID
            limit: Maximum number of matches to return
            
        Returns:
            ProviderResponse with HeadToHead
        """
        pass
    
    @abstractmethod
    def get_competition_matches(
        self,
        competition_id: str,
        match_date: Optional[date] = None
    ) -> ProviderResponse:
        """
        Get matches for a specific competition
        
        Args:
            competition_id: Provider-specific competition ID
            match_date: Optional date to filter matches
            
        Returns:
            ProviderResponse with List[MatchDetails]
        """
        pass
    
    @abstractmethod
    def get_odds(self, match_id: str) -> ProviderResponse:
        """
        Get odds for a specific match (if available)
        
        Args:
            match_id: Provider-specific match ID
            
        Returns:
            ProviderResponse with List[MatchOdds]
        """
        pass
    
    # =========================================================================
    # HELPER METHODS - Available to all providers
    # =========================================================================
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        
        # Reset counter if window expired
        if current_time - self._request_window_start >= 60:
            self._request_count = 0
            self._request_window_start = current_time
        
        # Check if limit reached
        if self._request_count >= self.config.rate_limit_per_minute:
            wait_time = 60 - (current_time - self._request_window_start)
            if wait_time > 0:
                self.logger.warning(
                    f"Rate limit reached. Waiting {wait_time:.1f}s"
                )
                time.sleep(wait_time)
                self._request_count = 0
                self._request_window_start = time.time()
        
        self._request_count += 1
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key from method and parameters"""
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        hash_obj = hashlib.md5(f"{method}:{params_str}".encode())
        return hash_obj.hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[Any, Any]]:
        """Get data from cache if valid"""
        if not self.config.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            age_seconds = (datetime.utcnow() - cached_time).total_seconds()
            
            if age_seconds <= self.config.cache_ttl_seconds:
                self.logger.debug(
                    f"Cache hit for {cache_key} (age: {age_seconds:.1f}s)"
                )
                cached_data['cached'] = True
                cached_data['cache_age_seconds'] = int(age_seconds)
                return cached_data
            else:
                self.logger.debug(f"Cache expired for {cache_key}")
                cache_file.unlink()
                return None
        
        except Exception as e:
            self.logger.warning(f"Cache read error: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[Any, Any]):
        """Save data to cache"""
        if not self.config.cache_enabled:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            data['timestamp'] = datetime.utcnow().isoformat()
            with open(cache_file, 'w') as f:
                json.dump(data, f, default=str)
            
            self.logger.debug(f"Cached data for {cache_key}")
        
        except Exception as e:
            self.logger.warning(f"Cache write error: {e}")
    
    def _retry_request(self, func, *args, **kwargs):
        """Retry a request with exponential backoff"""
        last_error = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_error = e
                
                if attempt < self.config.retry_attempts - 1:
                    wait_time = self.config.retry_delay_seconds * (2 ** attempt)
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        f"Request failed after {self.config.retry_attempts} attempts: {e}"
                    )
        
        raise last_error
    
    def _create_error_response(self, error: str) -> ProviderResponse:
        """Create error response"""
        return ProviderResponse(
            success=False,
            error=error,
            provider=self.config.name
        )
    
    def _create_success_response(
        self,
        data: Any,
        cached: bool = False,
        cache_age_seconds: Optional[int] = None
    ) -> ProviderResponse:
        """Create success response"""
        return ProviderResponse(
            success=True,
            data=data,
            provider=self.config.name,
            cached=cached,
            cache_age_seconds=cache_age_seconds
        )
    
    def clear_cache(self):
        """Clear all cached data for this provider"""
        if not self.config.cache_enabled:
            return
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            self.logger.info("Cache cleared")
        
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.config.cache_enabled:
            return {"enabled": False}
        
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "enabled": True,
                "total_files": len(cache_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "cache_dir": str(self.cache_dir)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}
