"""
Cache Service
Simple local caching system for external data
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Callable
from dataclasses import dataclass, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class CacheType(str, Enum):
    """Cache entry types"""
    TODAY_MATCHES = "today_matches"
    MATCH_DETAILS = "match_details"
    TEAM_RECENT = "team_recent"
    HEAD_TO_HEAD = "h2h"
    ODDS = "odds"
    COMPETITION_MATCHES = "competition_matches"


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    cache_dir: str = ".cache/data"
    ttl_hours: int = 6  # Default TTL: 6 hours
    max_cache_size_mb: int = 100
    
    # TTL per cache type (hours)
    ttl_today_matches: int = 1
    ttl_match_details: int = 6
    ttl_team_recent: int = 12
    ttl_h2h: int = 24
    ttl_odds: int = 1
    ttl_competition_matches: int = 6


@dataclass
class CacheEntry:
    """Cache entry metadata"""
    cache_type: str
    key: str
    data: Any
    created_at: str
    expires_at: str
    provider: str
    size_bytes: int


class CacheService:
    """
    Local cache service for external data
    
    Features:
    - Simple JSON file-based storage
    - TTL per cache type
    - Automatic expiration
    - Cache hit/miss logging
    - Size management
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache service
        
        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        
        if self.config.enabled:
            self.cache_dir = Path(self.config.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"CacheService initialized: {self.cache_dir}")
        else:
            logger.info("CacheService disabled")
    
    def _get_ttl_hours(self, cache_type: CacheType) -> int:
        """Get TTL for specific cache type"""
        ttl_map = {
            CacheType.TODAY_MATCHES: self.config.ttl_today_matches,
            CacheType.MATCH_DETAILS: self.config.ttl_match_details,
            CacheType.TEAM_RECENT: self.config.ttl_team_recent,
            CacheType.HEAD_TO_HEAD: self.config.ttl_h2h,
            CacheType.ODDS: self.config.ttl_odds,
            CacheType.COMPETITION_MATCHES: self.config.ttl_competition_matches
        }
        return ttl_map.get(cache_type, self.config.ttl_hours)
    
    def _generate_cache_key(self, cache_type: CacheType, **params) -> str:
        """
        Generate unique cache key
        
        Args:
            cache_type: Type of cache entry
            **params: Parameters to include in key
            
        Returns:
            Unique cache key
        """
        # Sort params for consistency
        params_str = json.dumps(params, sort_keys=True, default=str)
        
        # Generate hash
        hash_obj = hashlib.md5(f"{cache_type.value}:{params_str}".encode())
        cache_key = hash_obj.hexdigest()
        
        return cache_key
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        expires_at = datetime.fromisoformat(entry.expires_at)
        return datetime.utcnow() >= expires_at
    
    def get(
        self,
        cache_type: CacheType,
        **params
    ) -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            cache_type: Type of cache entry
            **params: Parameters to identify entry
            
        Returns:
            Cached data or None if not found/expired
        """
        if not self.config.enabled:
            return None
        
        cache_key = self._generate_cache_key(cache_type, **params)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            logger.debug(f"Cache MISS: {cache_type.value} {params}")
            return None
        
        try:
            # Read cache entry
            with open(cache_path, 'r', encoding='utf-8') as f:
                entry_dict = json.load(f)
            
            entry = CacheEntry(**entry_dict)
            
            # Check expiration
            if self._is_expired(entry):
                logger.debug(f"Cache EXPIRED: {cache_type.value} {params}")
                cache_path.unlink()  # Delete expired entry
                return None
            
            # Cache hit
            age_seconds = (datetime.utcnow() - datetime.fromisoformat(entry.created_at)).total_seconds()
            logger.info(f"Cache HIT: {cache_type.value} (age: {age_seconds:.0f}s)")
            
            return entry.data
        
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set(
        self,
        cache_type: CacheType,
        data: Any,
        provider: str = "unknown",
        **params
    ):
        """
        Store data in cache
        
        Args:
            cache_type: Type of cache entry
            data: Data to cache
            provider: Provider name
            **params: Parameters to identify entry
        """
        if not self.config.enabled:
            return
        
        cache_key = self._generate_cache_key(cache_type, **params)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            # Calculate expiration
            ttl_hours = self._get_ttl_hours(cache_type)
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(hours=ttl_hours)
            
            # Create cache entry
            entry = CacheEntry(
                cache_type=cache_type.value,
                key=cache_key,
                data=data,
                created_at=created_at.isoformat(),
                expires_at=expires_at.isoformat(),
                provider=provider,
                size_bytes=0  # Will be calculated after serialization
            )
            
            # Serialize
            entry_dict = asdict(entry)
            entry_json = json.dumps(entry_dict, default=str, ensure_ascii=False)
            entry.size_bytes = len(entry_json.encode('utf-8'))
            entry_dict['size_bytes'] = entry.size_bytes
            
            # Write to file
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(entry_dict, f, default=str, ensure_ascii=False, indent=2)
            
            logger.debug(
                f"Cache SET: {cache_type.value} "
                f"(TTL: {ttl_hours}h, size: {entry.size_bytes} bytes)"
            )
        
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def get_or_fetch(
        self,
        cache_type: CacheType,
        fetch_func: Callable[[], Any],
        provider: str = "unknown",
        **params
    ) -> Any:
        """
        Get from cache or fetch if not available
        
        Args:
            cache_type: Type of cache entry
            fetch_func: Function to fetch data if not cached
            provider: Provider name
            **params: Parameters to identify entry
            
        Returns:
            Cached or freshly fetched data
        """
        # Try cache first
        cached_data = self.get(cache_type, **params)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        logger.debug(f"Fetching fresh data: {cache_type.value}")
        fresh_data = fetch_func()
        
        # Cache it
        if fresh_data is not None:
            self.set(cache_type, fresh_data, provider, **params)
        
        return fresh_data
    
    def invalidate(
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
        if not self.config.enabled:
            return
        
        if cache_type and params:
            # Invalidate specific entry
            cache_key = self._generate_cache_key(cache_type, **params)
            cache_path = self._get_cache_path(cache_key)
            
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cache invalidated: {cache_type.value}")
        
        elif cache_type:
            # Invalidate all entries of type
            count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                    
                    if entry.get('cache_type') == cache_type.value:
                        cache_file.unlink()
                        count += 1
                
                except Exception as e:
                    logger.warning(f"Error reading cache file: {e}")
            
            logger.info(f"Cache invalidated: {cache_type.value} ({count} entries)")
        
        else:
            # Invalidate all
            count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
            
            logger.info(f"Cache invalidated: ALL ({count} entries)")
    
    def clear_expired(self):
        """Remove all expired cache entries"""
        if not self.config.enabled:
            return
        
        count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    entry_dict = json.load(f)
                
                entry = CacheEntry(**entry_dict)
                
                if self._is_expired(entry):
                    cache_file.unlink()
                    count += 1
            
            except Exception as e:
                logger.warning(f"Error checking expiration: {e}")
        
        if count > 0:
            logger.info(f"Cleared {count} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.config.enabled:
            return {"enabled": False}
        
        stats = {
            "enabled": True,
            "cache_dir": str(self.cache_dir),
            "total_entries": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "by_type": {},
            "expired_count": 0
        }
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    entry_dict = json.load(f)
                
                entry = CacheEntry(**entry_dict)
                
                stats["total_entries"] += 1
                stats["total_size_bytes"] += entry.size_bytes
                
                # Count by type
                cache_type = entry.cache_type
                if cache_type not in stats["by_type"]:
                    stats["by_type"][cache_type] = {
                        "count": 0,
                        "size_bytes": 0
                    }
                
                stats["by_type"][cache_type]["count"] += 1
                stats["by_type"][cache_type]["size_bytes"] += entry.size_bytes
                
                # Check expiration
                if self._is_expired(entry):
                    stats["expired_count"] += 1
            
            except Exception as e:
                logger.warning(f"Error reading cache stats: {e}")
        
        stats["total_size_mb"] = round(stats["total_size_bytes"] / 1024 / 1024, 2)
        
        return stats
    
    def cleanup(self):
        """
        Cleanup cache
        - Remove expired entries
        - Enforce size limit
        """
        if not self.config.enabled:
            return
        
        # Clear expired
        self.clear_expired()
        
        # Check size
        stats = self.get_stats()
        
        if stats["total_size_mb"] > self.config.max_cache_size_mb:
            logger.warning(
                f"Cache size ({stats['total_size_mb']} MB) exceeds limit "
                f"({self.config.max_cache_size_mb} MB)"
            )
            
            # Delete oldest entries until under limit
            cache_files = []
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry_dict = json.load(f)
                    
                    entry = CacheEntry(**entry_dict)
                    created_at = datetime.fromisoformat(entry.created_at)
                    
                    cache_files.append((created_at, cache_file, entry.size_bytes))
                
                except Exception:
                    continue
            
            # Sort by creation time (oldest first)
            cache_files.sort(key=lambda x: x[0])
            
            current_size_mb = stats["total_size_mb"]
            deleted_count = 0
            
            for created_at, cache_file, size_bytes in cache_files:
                if current_size_mb <= self.config.max_cache_size_mb:
                    break
                
                cache_file.unlink()
                current_size_mb -= size_bytes / 1024 / 1024
                deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} old cache entries to enforce size limit")


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache_service(config: Optional[CacheConfig] = None) -> CacheService:
    """Get or create global cache service instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = CacheService(config)
    
    return _cache_instance
