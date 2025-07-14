"""
Caching service for categorization results.

Provides fast response caching to improve performance and reduce LLM API calls
for similar struggle descriptions.
"""

import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from config.settings import Settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    In-memory caching service with TTL support.
    
    In production, this would typically use Redis, but for development
    we'll use an in-memory cache with cleanup mechanisms.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the cache service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.ttl_seconds = settings.cache_ttl_seconds
        self.max_cache_size = 1000  # Prevent memory issues
        
        logger.info(f"Cache service initialized with TTL: {self.ttl_seconds}s")
    
    def generate_cache_key(self, struggle_text: str, context: Dict[str, Any] = None) -> str:
        """
        Generate a consistent cache key for struggle text.
        
        Args:
            struggle_text: User's struggle description
            context: Additional context that affects categorization
            
        Returns:
            str: Cache key
        """
        # Normalize text for consistent caching
        normalized_text = struggle_text.lower().strip()
        
        # Include relevant context in key generation
        cache_data = {
            "text": normalized_text,
            "model": self.settings.model_name,
            "version": "1.0"  # Increment when categorization logic changes
        }
        
        if context:
            # Only include context that affects categorization
            relevant_context = {
                k: v for k, v in context.items() 
                if k in ["priority", "session_type", "user_history"]
            }
            cache_data["context"] = relevant_context
        
        # Generate hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached categorization result.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Optional[Dict]: Cached result or None if not found/expired
        """
        # Check if key exists
        if cache_key not in self.cache:
            return None
        
        # Check if expired
        cached_data = self.cache[cache_key]
        if self._is_expired(cached_data):
            self._remove(cache_key)
            return None
        
        # Update access time
        self.access_times[cache_key] = time.time()
        
        # Mark as cache hit
        cached_result = cached_data["result"].copy()
        cached_result["processing_metrics"]["cache_hit"] = True
        cached_result["processing_metrics"]["cached_at"] = cached_data["cached_at"]
        
        logger.debug(f"Cache hit for key: {cache_key[:8]}...")
        return cached_result
    
    def set(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Store a categorization result in cache.
        
        Args:
            cache_key: Cache key
            result: Categorization result to cache
        """
        # Cleanup if cache is getting too large
        if len(self.cache) >= self.max_cache_size:
            self._cleanup_expired()
            if len(self.cache) >= self.max_cache_size:
                self._evict_lru()
        
        # Store with metadata
        cache_entry = {
            "result": result.copy(),
            "cached_at": time.time(),
            "expires_at": time.time() + self.ttl_seconds
        }
        
        self.cache[cache_key] = cache_entry
        self.access_times[cache_key] = time.time()
        
        logger.debug(f"Cached result for key: {cache_key[:8]}...")
    
    def invalidate(self, pattern: str = None) -> int:
        """
        Invalidate cache entries by pattern or clear all.
        
        Args:
            pattern: Pattern to match keys (None = clear all)
            
        Returns:
            int: Number of entries removed
        """
        if pattern is None:
            # Clear all cache
            count = len(self.cache)
            self.cache.clear()
            self.access_times.clear()
            logger.info(f"Cleared entire cache ({count} entries)")
            return count
        
        # Remove entries matching pattern
        keys_to_remove = [
            key for key in self.cache.keys() 
            if pattern in key
        ]
        
        for key in keys_to_remove:
            self._remove(key)
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
        return len(keys_to_remove)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dict: Cache statistics
        """
        now = time.time()
        expired_count = sum(
            1 for entry in self.cache.values()
            if entry["expires_at"] < now
        )
        
        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "max_size": self.max_cache_size,
            "ttl_seconds": self.ttl_seconds,
            "memory_usage_estimate": len(str(self.cache)),  # Rough estimate
            "oldest_entry": min(self.access_times.values()) if self.access_times else None,
            "newest_entry": max(self.access_times.values()) if self.access_times else None
        }
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        return time.time() > cache_entry["expires_at"]
    
    def _remove(self, cache_key: str) -> None:
        """Remove a cache entry and its access time."""
        self.cache.pop(cache_key, None)
        self.access_times.pop(cache_key, None)
    
    def _cleanup_expired(self) -> int:
        """Remove all expired cache entries."""
        now = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry["expires_at"] < now
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries to make space."""
        if not self.access_times:
            return
        
        # Remove 10% of oldest entries
        entries_to_remove = max(1, len(self.cache) // 10)
        
        # Sort by access time (oldest first)
        sorted_keys = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        keys_to_remove = [key for key, _ in sorted_keys[:entries_to_remove]]
        
        for key in keys_to_remove:
            self._remove(key)
        
        logger.info(f"Evicted {len(keys_to_remove)} LRU cache entries")


class CacheMetrics:
    """
    Cache performance metrics tracking.
    """
    
    def __init__(self):
        """Initialize metrics tracking."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0
        self.start_time = time.time()
    
    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
    
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
    
    def record_set(self):
        """Record a cache set operation."""
        self.sets += 1
    
    def record_eviction(self):
        """Record a cache eviction."""
        self.evictions += 1
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hits + self.misses
        return self.hits / total_requests if total_requests > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        uptime = time.time() - self.start_time
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "evictions": self.evictions,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self.hits + self.misses,
            "uptime_seconds": uptime,
            "requests_per_second": (self.hits + self.misses) / uptime if uptime > 0 else 0
        }
    
    def reset(self):
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0
        self.start_time = time.time()


# Global cache metrics instance
cache_metrics = CacheMetrics()