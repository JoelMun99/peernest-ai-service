"""
Redis-based caching service for categorization results.

Provides distributed caching to improve performance and reduce LLM API calls
across multiple service instances.
"""

import json
import time
import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import timedelta

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from config.settings import Settings

logger = logging.getLogger(__name__)


class RedisCacheService:
    """
    Redis-based caching service with fallback to in-memory caching.
    
    Provides distributed caching for categorization results with proper
    error handling and connection management.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Redis cache service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.redis_config = settings.get_redis_config()
        self.ttl_seconds = settings.cache_ttl_seconds
        self.redis_enabled = settings.redis_enabled
        
        # Redis client (will be initialized in async context)
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        
        # Fallback in-memory cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._using_redis = False
        
        logger.info(f"Redis cache service initialized (enabled: {self.redis_enabled})")
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection.
        
        Returns:
            bool: True if Redis connection successful, False if using fallback
        """
        if not self.redis_enabled:
            logger.info("Redis disabled, using in-memory cache fallback")
            return False
        
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool.from_url(
                url=self.redis_config["url"],
                max_connections=self.redis_config["max_connections"],
                socket_timeout=self.redis_config["timeout"],
                socket_connect_timeout=self.redis_config["timeout"],
                decode_responses=self.redis_config["decode_responses"],
                retry_on_timeout=self.redis_config["retry_on_timeout"]
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._using_redis = True
            
            logger.info(f"Redis connection established: {self.redis_config['url']}")
            return True
            
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {str(e)}")
            self._using_redis = False
            return False
    
    async def close(self):
        """Close Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
    
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
            "version": "2.0"  # Increment when categorization logic changes
        }
        
        if context:
            # Only include context that affects categorization
            relevant_context = {
                k: v for k, v in context.items() 
                if k in ["priority", "session_type", "user_history"]
            }
            cache_data["context"] = relevant_context
        
        # Generate hash with prefix
        cache_string = json.dumps(cache_data, sort_keys=True)
        hash_key = hashlib.md5(cache_string.encode()).hexdigest()
        return f"categorization:{hash_key}"
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached categorization result.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Optional[Dict]: Cached result or None if not found/expired
        """
        if self._using_redis:
            return await self._get_from_redis(cache_key)
        else:
            return self._get_from_memory(cache_key)
    
    async def set(self, cache_key: str, result: Dict[str, Any]) -> bool:
        """
        Store a categorization result in cache.
        
        Args:
            cache_key: Cache key
            result: Categorization result to cache
            
        Returns:
            bool: True if stored successfully
        """
        if self._using_redis:
            return await self._set_in_redis(cache_key, result)
        else:
            return self._set_in_memory(cache_key, result)
    
    async def invalidate(self, pattern: str = None) -> int:
        """
        Invalidate cache entries by pattern or clear all.
        
        Args:
            pattern: Pattern to match keys (None = clear all categorization cache)
            
        Returns:
            int: Number of entries removed
        """
        if self._using_redis:
            return await self._invalidate_redis(pattern)
        else:
            return self._invalidate_memory(pattern)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dict: Cache statistics
        """
        base_stats = {
            "cache_type": "redis" if self._using_redis else "memory",
            "redis_enabled": self.redis_enabled,
            "ttl_seconds": self.ttl_seconds,
            "connection_status": "connected" if self._using_redis else "fallback"
        }
        
        if self._using_redis:
            try:
                info = await self.redis_client.info()
                base_stats.update({
                    "redis_memory_used": info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_total_commands": info.get("total_commands_processed", 0),
                    "redis_keyspace_hits": info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": info.get("keyspace_misses", 0)
                })
                
                # Get categorization key count
                categorization_keys = await self.redis_client.keys("categorization:*")
                base_stats["categorization_keys"] = len(categorization_keys)
                
            except RedisError as e:
                logger.error(f"Failed to get Redis stats: {str(e)}")
                base_stats["error"] = str(e)
        else:
            base_stats.update({
                "memory_cache_entries": len(self._memory_cache),
                "memory_usage_estimate": len(str(self._memory_cache))
            })
        
        return base_stats
    
    async def test_connection(self) -> bool:
        """
        Test Redis connection health.
        
        Returns:
            bool: True if Redis is healthy, False otherwise
        """
        if not self._using_redis:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except RedisError:
            return False
    
    # Redis-specific methods
    async def _get_from_redis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from Redis cache."""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data is None:
                return None
            
            # Parse JSON data
            result = json.loads(cached_data)
            
            # Mark as cache hit and add metadata
            result["processing_metrics"]["cache_hit"] = True
            result["processing_metrics"]["cache_type"] = "redis"
            
            logger.debug(f"Redis cache hit for key: {cache_key[:20]}...")
            return result
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def _set_in_redis(self, cache_key: str, result: Dict[str, Any]) -> bool:
        """Set in Redis cache."""
        try:
            # Prepare data for storage
            cache_data = result.copy()
            cache_data["processing_metrics"]["cached_at"] = time.time()
            cache_data["processing_metrics"]["cache_type"] = "redis"
            
            # Store with TTL
            await self.redis_client.setex(
                cache_key,
                timedelta(seconds=self.ttl_seconds),
                json.dumps(cache_data)
            )
            
            logger.debug(f"Stored in Redis cache: {cache_key[:20]}...")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    async def _invalidate_redis(self, pattern: str = None) -> int:
        """Invalidate Redis cache entries."""
        try:
            if pattern is None:
                # Clear all categorization keys
                pattern = "categorization:*"
            
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} Redis cache entries matching '{pattern}'")
                return deleted
            return 0
            
        except RedisError as e:
            logger.error(f"Redis invalidate error: {str(e)}")
            return 0
    
    # Memory fallback methods
    def _get_from_memory(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from memory cache."""
        if cache_key not in self._memory_cache:
            return None
        
        cached_data = self._memory_cache[cache_key]
        
        # Check if expired
        if time.time() > cached_data["expires_at"]:
            del self._memory_cache[cache_key]
            return None
        
        # Return result with cache hit metadata
        result = cached_data["result"].copy()
        result["processing_metrics"]["cache_hit"] = True
        result["processing_metrics"]["cache_type"] = "memory"
        result["processing_metrics"]["cached_at"] = cached_data["cached_at"]
        
        logger.debug(f"Memory cache hit for key: {cache_key[:20]}...")
        return result
    
    def _set_in_memory(self, cache_key: str, result: Dict[str, Any]) -> bool:
        """Set in memory cache."""
        try:
            # Simple cleanup if cache gets too large
            if len(self._memory_cache) > 1000:
                # Remove expired entries
                now = time.time()
                expired_keys = [
                    key for key, data in self._memory_cache.items()
                    if data["expires_at"] < now
                ]
                for key in expired_keys:
                    del self._memory_cache[key]
            
            # Store with metadata
            cache_entry = {
                "result": result.copy(),
                "cached_at": time.time(),
                "expires_at": time.time() + self.ttl_seconds
            }
            
            self._memory_cache[cache_key] = cache_entry
            logger.debug(f"Stored in memory cache: {cache_key[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Memory cache set error: {str(e)}")
            return False
    
    def _invalidate_memory(self, pattern: str = None) -> int:
        """Invalidate memory cache entries."""
        if pattern is None:
            # Clear all cache
            count = len(self._memory_cache)
            self._memory_cache.clear()
            logger.info(f"Cleared entire memory cache ({count} entries)")
            return count
        
        # Pattern matching for memory cache
        keys_to_remove = [
            key for key in self._memory_cache.keys()
            if pattern in key
        ]
        
        for key in keys_to_remove:
            del self._memory_cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} memory cache entries matching '{pattern}'")
        return len(keys_to_remove)