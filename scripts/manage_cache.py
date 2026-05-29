"""
Cache Management Script
View stats, clear cache, test caching
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cache import CacheService, CacheConfig
from app.cache.cache_service import CacheType
from app.providers import MockDataProvider
from app.providers.cached_provider import CachedProvider


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def show_cache_stats():
    """Show cache statistics"""
    
    print("\n" + "="*80)
    print("CACHE STATISTICS")
    print("="*80)
    
    cache = CacheService()
    stats = cache.get_stats()
    
    if not stats["enabled"]:
        print("\n❌ Cache is disabled")
        return
    
    print(f"\n📊 General:")
    print(f"  Cache Dir: {stats['cache_dir']}")
    print(f"  Total Entries: {stats['total_entries']}")
    print(f"  Total Size: {stats['total_size_mb']} MB")
    print(f"  Expired: {stats['expired_count']}")
    
    if stats["by_type"]:
        print(f"\n📦 By Type:")
        for cache_type, type_stats in stats["by_type"].items():
            size_kb = type_stats["size_bytes"] / 1024
            print(f"  {cache_type}:")
            print(f"    Count: {type_stats['count']}")
            print(f"    Size: {size_kb:.2f} KB")


def clear_cache():
    """Clear all cache"""
    
    print("\n" + "="*80)
    print("CLEAR CACHE")
    print("="*80)
    
    cache = CacheService()
    
    # Get stats before
    stats_before = cache.get_stats()
    print(f"\nBefore: {stats_before['total_entries']} entries, {stats_before['total_size_mb']} MB")
    
    # Clear
    print("\n🗑️  Clearing cache...")
    cache.invalidate()
    
    # Get stats after
    stats_after = cache.get_stats()
    print(f"After: {stats_after['total_entries']} entries, {stats_after['total_size_mb']} MB")
    
    print("\n✅ Cache cleared")


def clear_expired():
    """Clear expired entries only"""
    
    print("\n" + "="*80)
    print("CLEAR EXPIRED")
    print("="*80)
    
    cache = CacheService()
    
    stats_before = cache.get_stats()
    expired_before = stats_before['expired_count']
    
    print(f"\nExpired entries: {expired_before}")
    
    if expired_before > 0:
        print("\n🗑️  Clearing expired entries...")
        cache.clear_expired()
        
        stats_after = cache.get_stats()
        print(f"✅ Cleared {expired_before} expired entries")
    else:
        print("\n✅ No expired entries to clear")


def test_caching():
    """Test caching functionality"""
    
    print("\n" + "="*80)
    print("TEST CACHING")
    print("="*80)
    
    # Create cached provider
    base_provider = MockDataProvider()
    cached_provider = CachedProvider(base_provider)
    
    # Test 1: First call (cache miss)
    print("\n📥 Test 1: First call (should be cache MISS)")
    response1 = cached_provider.get_today_matches()
    print(f"  Success: {response1.success}")
    print(f"  Matches: {len(response1.data) if response1.data else 0}")
    
    # Test 2: Second call (cache hit)
    print("\n📥 Test 2: Second call (should be cache HIT)")
    response2 = cached_provider.get_today_matches()
    print(f"  Success: {response2.success}")
    print(f"  Matches: {len(response2.data) if response2.data else 0}")
    
    # Test 3: Match details
    print("\n📥 Test 3: Match details")
    if response1.data:
        match_id = response1.data[0].id
        print(f"  Fetching match {match_id}...")
        
        response3 = cached_provider.get_match_details(match_id)
        print(f"  Success: {response3.success}")
        
        # Second call (cached)
        response4 = cached_provider.get_match_details(match_id)
        print(f"  Second call success: {response4.success}")
    
    # Show cache stats
    print("\n📊 Cache Stats:")
    stats = cached_provider.get_cache_stats()
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    
    print("\n✅ Caching test complete")


def cleanup_cache():
    """Run cache cleanup"""
    
    print("\n" + "="*80)
    print("CACHE CLEANUP")
    print("="*80)
    
    cache = CacheService()
    
    stats_before = cache.get_stats()
    print(f"\nBefore cleanup:")
    print(f"  Entries: {stats_before['total_entries']}")
    print(f"  Size: {stats_before['total_size_mb']} MB")
    print(f"  Expired: {stats_before['expired_count']}")
    
    print("\n🧹 Running cleanup...")
    cache.cleanup()
    
    stats_after = cache.get_stats()
    print(f"\nAfter cleanup:")
    print(f"  Entries: {stats_after['total_entries']}")
    print(f"  Size: {stats_after['total_size_mb']} MB")
    print(f"  Expired: {stats_after['expired_count']}")
    
    print("\n✅ Cleanup complete")


def main():
    """Main menu"""
    
    print("\n" + "="*80)
    print("🗄️  CACHE MANAGEMENT")
    print("="*80)
    
    print("\nOptions:")
    print("  1. Show cache statistics")
    print("  2. Clear all cache")
    print("  3. Clear expired entries")
    print("  4. Test caching")
    print("  5. Run cleanup")
    print("  6. Exit")
    
    while True:
        choice = input("\nChoice [1-6]: ").strip()
        
        if choice == "1":
            show_cache_stats()
        
        elif choice == "2":
            confirm = input("\n⚠️  Clear ALL cache? [y/N]: ").strip().lower()
            if confirm == 'y':
                clear_cache()
        
        elif choice == "3":
            clear_expired()
        
        elif choice == "4":
            test_caching()
        
        elif choice == "5":
            cleanup_cache()
        
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("\n❌ Invalid choice")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
