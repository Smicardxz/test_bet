"""
Tests for CacheService
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import shutil

from app.cache import CacheService, CacheConfig
from app.cache.cache_service import CacheType


class TestCacheService:
    """Test CacheService functionality"""
    
    def setup_method(self):
        """Setup test cache"""
        self.test_cache_dir = Path(".cache/test")
        
        # Clean up if exists
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
        
        # Create test cache
        config = CacheConfig(
            enabled=True,
            cache_dir=str(self.test_cache_dir),
            ttl_hours=1,
            ttl_today_matches=1,
            ttl_team_recent=2
        )
        
        self.cache = CacheService(config)
    
    def teardown_method(self):
        """Cleanup test cache"""
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
    
    def test_cache_initialization(self):
        """Test cache initializes correctly"""
        assert self.cache.config.enabled is True
        assert self.cache.cache_dir.exists()
    
    def test_cache_set_and_get(self):
        """Test basic set and get"""
        test_data = {"match_id": "123", "home": "Team A", "away": "Team B"}
        
        # Set cache
        self.cache.set(
            CacheType.MATCH_DETAILS,
            test_data,
            provider="test",
            match_id="123"
        )
        
        # Get cache
        cached_data = self.cache.get(
            CacheType.MATCH_DETAILS,
            match_id="123"
        )
        
        assert cached_data == test_data
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cached_data = self.cache.get(
            CacheType.MATCH_DETAILS,
            match_id="nonexistent"
        )
        
        assert cached_data is None
    
    def test_cache_expiration(self):
        """Test cache entries expire"""
        test_data = {"test": "data"}
        
        # Create cache with very short TTL
        config = CacheConfig(
            enabled=True,
            cache_dir=str(self.test_cache_dir),
            ttl_today_matches=0  # 0 hours = immediate expiration
        )
        
        cache = CacheService(config)
        
        # Set cache
        cache.set(
            CacheType.TODAY_MATCHES,
            test_data,
            provider="test"
        )
        
        # Wait a moment
        time.sleep(0.1)
        
        # Should be expired
        cached_data = cache.get(CacheType.TODAY_MATCHES)
        assert cached_data is None
    
    def test_get_or_fetch_cache_hit(self):
        """Test get_or_fetch with cache hit"""
        test_data = {"cached": True}
        
        # Pre-populate cache
        self.cache.set(
            CacheType.MATCH_DETAILS,
            test_data,
            provider="test",
            match_id="123"
        )
        
        # Fetch function should not be called
        fetch_called = False
        
        def fetch_func():
            nonlocal fetch_called
            fetch_called = True
            return {"cached": False}
        
        result = self.cache.get_or_fetch(
            CacheType.MATCH_DETAILS,
            fetch_func,
            provider="test",
            match_id="123"
        )
        
        assert result == test_data
        assert fetch_called is False
    
    def test_get_or_fetch_cache_miss(self):
        """Test get_or_fetch with cache miss"""
        fresh_data = {"cached": False}
        
        def fetch_func():
            return fresh_data
        
        result = self.cache.get_or_fetch(
            CacheType.MATCH_DETAILS,
            fetch_func,
            provider="test",
            match_id="456"
        )
        
        assert result == fresh_data
        
        # Should now be cached
        cached_data = self.cache.get(
            CacheType.MATCH_DETAILS,
            match_id="456"
        )
        
        assert cached_data == fresh_data
    
    def test_invalidate_specific_entry(self):
        """Test invalidating specific cache entry"""
        # Set multiple entries
        self.cache.set(
            CacheType.MATCH_DETAILS,
            {"match": "1"},
            provider="test",
            match_id="1"
        )
        
        self.cache.set(
            CacheType.MATCH_DETAILS,
            {"match": "2"},
            provider="test",
            match_id="2"
        )
        
        # Invalidate one
        self.cache.invalidate(
            CacheType.MATCH_DETAILS,
            match_id="1"
        )
        
        # First should be gone
        assert self.cache.get(CacheType.MATCH_DETAILS, match_id="1") is None
        
        # Second should still exist
        assert self.cache.get(CacheType.MATCH_DETAILS, match_id="2") is not None
    
    def test_invalidate_by_type(self):
        """Test invalidating all entries of a type"""
        # Set entries of different types
        self.cache.set(
            CacheType.MATCH_DETAILS,
            {"match": "1"},
            provider="test",
            match_id="1"
        )
        
        self.cache.set(
            CacheType.TEAM_RECENT,
            {"team": "A"},
            provider="test",
            team_id="A"
        )
        
        # Invalidate match details
        self.cache.invalidate(CacheType.MATCH_DETAILS)
        
        # Match details should be gone
        assert self.cache.get(CacheType.MATCH_DETAILS, match_id="1") is None
        
        # Team recent should still exist
        assert self.cache.get(CacheType.TEAM_RECENT, team_id="A") is not None
    
    def test_invalidate_all(self):
        """Test invalidating all cache"""
        # Set multiple entries
        self.cache.set(
            CacheType.MATCH_DETAILS,
            {"match": "1"},
            provider="test",
            match_id="1"
        )
        
        self.cache.set(
            CacheType.TEAM_RECENT,
            {"team": "A"},
            provider="test",
            team_id="A"
        )
        
        # Invalidate all
        self.cache.invalidate()
        
        # All should be gone
        assert self.cache.get(CacheType.MATCH_DETAILS, match_id="1") is None
        assert self.cache.get(CacheType.TEAM_RECENT, team_id="A") is None
    
    def test_clear_expired(self):
        """Test clearing expired entries"""
        # Create cache with 0 TTL
        config = CacheConfig(
            enabled=True,
            cache_dir=str(self.test_cache_dir),
            ttl_today_matches=0
        )
        
        cache = CacheService(config)
        
        # Set entry that will expire immediately
        cache.set(
            CacheType.TODAY_MATCHES,
            {"test": "data"},
            provider="test"
        )
        
        # Wait
        time.sleep(0.1)
        
        # Clear expired
        cache.clear_expired()
        
        # Should be gone
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Set some entries
        self.cache.set(
            CacheType.MATCH_DETAILS,
            {"match": "1"},
            provider="test",
            match_id="1"
        )
        
        self.cache.set(
            CacheType.TEAM_RECENT,
            {"team": "A"},
            provider="test",
            team_id="A"
        )
        
        stats = self.cache.get_stats()
        
        assert stats["enabled"] is True
        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
        assert "by_type" in stats
        assert CacheType.MATCH_DETAILS.value in stats["by_type"]
    
    def test_different_ttl_per_type(self):
        """Test different TTL for different cache types"""
        config = CacheConfig(
            enabled=True,
            cache_dir=str(self.test_cache_dir),
            ttl_today_matches=1,
            ttl_team_recent=2
        )
        
        cache = CacheService(config)
        
        # Check TTL values
        assert cache._get_ttl_hours(CacheType.TODAY_MATCHES) == 1
        assert cache._get_ttl_hours(CacheType.TEAM_RECENT) == 2
    
    def test_disabled_cache(self):
        """Test cache when disabled"""
        config = CacheConfig(enabled=False)
        cache = CacheService(config)
        
        # Set should do nothing
        cache.set(
            CacheType.MATCH_DETAILS,
            {"test": "data"},
            provider="test",
            match_id="1"
        )
        
        # Get should return None
        result = cache.get(CacheType.MATCH_DETAILS, match_id="1")
        assert result is None


class TestCachedProvider:
    """Test CachedProvider wrapper"""
    
    def setup_method(self):
        """Setup test"""
        from app.providers import MockDataProvider
        from app.providers.cached_provider import CachedProvider
        
        self.test_cache_dir = Path(".cache/test_provider")
        
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
        
        cache_config = CacheConfig(
            enabled=True,
            cache_dir=str(self.test_cache_dir),
            ttl_hours=1
        )
        
        base_provider = MockDataProvider()
        self.provider = CachedProvider(base_provider, cache_config=cache_config)
    
    def teardown_method(self):
        """Cleanup"""
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
    
    def test_cached_provider_get_today_matches(self):
        """Test cached get_today_matches"""
        # First call - cache miss
        response1 = self.provider.get_today_matches()
        assert response1.success is True
        
        # Second call - cache hit
        response2 = self.provider.get_today_matches()
        assert response2.success is True
        
        # Should have same data
        assert len(response1.data) == len(response2.data)
    
    def test_cached_provider_get_match_details(self):
        """Test cached get_match_details"""
        response1 = self.provider.get_match_details("match_001")
        assert response1.success is True
        
        response2 = self.provider.get_match_details("match_001")
        assert response2.success is True
        
        assert response1.data.id == response2.data.id
    
    def test_cached_provider_invalidation(self):
        """Test cache invalidation"""
        # Populate cache
        self.provider.get_today_matches()
        
        # Invalidate
        self.provider.invalidate_cache(CacheType.TODAY_MATCHES)
        
        # Cache should be empty for this type
        stats = self.provider.get_cache_stats()
        if CacheType.TODAY_MATCHES.value in stats.get("by_type", {}):
            assert stats["by_type"][CacheType.TODAY_MATCHES.value]["count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
