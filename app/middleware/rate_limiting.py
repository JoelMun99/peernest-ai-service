"""
Rate limiting middleware for API protection.

Implements sliding window rate limiting to prevent abuse and protect
against excessive API usage.
"""

import time
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter.
    
    Tracks requests per client and enforces rate limits to prevent abuse.
    """
    
    def __init__(self):
        """Initialize the rate limiter."""
        # Store request timestamps per client
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Rate limit configurations (requests per minute)
        self.limits = {
            "categorization": {"requests": 60, "window": 60},  # 60 requests per minute
            "bulk_categorization": {"requests": 10, "window": 60},  # 10 batch requests per minute
            "health_check": {"requests": 120, "window": 60},  # 120 health checks per minute
            "categories": {"requests": 30, "window": 60},  # 30 category requests per minute
            "test": {"requests": 30, "window": 60},  # 30 test requests per minute
            "default": {"requests": 100, "window": 60}  # Default limit
        }
        
        # Burst limits (short-term protection)
        self.burst_limits = {
            "categorization": {"requests": 10, "window": 10},  # 10 requests per 10 seconds
            "bulk_categorization": {"requests": 2, "window": 10},  # 2 batch requests per 10 seconds
            "default": {"requests": 20, "window": 10}  # Default burst limit
        }
        
        logger.info("Rate limiter initialized with sliding window algorithm")
    
    def get_client_id(self, request: Request) -> str:
        """
        Generate client identifier for rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client identifier
        """
        # Use IP address as client identifier
        # In production, you might use authentication tokens or more sophisticated methods
        client_ip = request.client.host if request.client else "unknown"
        
        # Consider X-Forwarded-For header for proxy scenarios
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return client_ip
    
    def get_endpoint_category(self, request: Request) -> str:
        """
        Categorize the endpoint for appropriate rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Endpoint category
        """
        path = request.url.path
        
        if "/categorize" in path and "/bulk" in path:
            return "bulk_categorization"
        elif "/categorize" in path:
            return "categorization"
        elif "/health" in path:
            return "health_check"
        elif "/categories" in path:
            return "categories"
        elif "/test" in path:
            return "test"
        else:
            return "default"
    
    def is_allowed(self, client_id: str, endpoint_category: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if a request should be allowed based on rate limits.
        
        Args:
            client_id: Client identifier
            endpoint_category: Category of endpoint being accessed
            
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        now = time.time()
        client_key = f"{client_id}:{endpoint_category}"
        
        # Get rate limit configuration
        rate_config = self.limits.get(endpoint_category, self.limits["default"])
        burst_config = self.burst_limits.get(endpoint_category, self.burst_limits["default"])
        
        # Clean old requests
        self._cleanup_old_requests(client_key, now, rate_config["window"])
        
        # Check burst limit (short-term)
        burst_requests = self._count_requests_in_window(client_key, now, burst_config["window"])
        if burst_requests >= burst_config["requests"]:
            return False, {
                "limit_type": "burst",
                "limit": burst_config["requests"],
                "window": burst_config["window"],
                "current": burst_requests,
                "reset_in": burst_config["window"]
            }
        
        # Check regular rate limit
        rate_requests = self._count_requests_in_window(client_key, now, rate_config["window"])
        if rate_requests >= rate_config["requests"]:
            oldest_request = self.requests[client_key][0] if self.requests[client_key] else now
            reset_in = int(oldest_request + rate_config["window"] - now)
            
            return False, {
                "limit_type": "rate",
                "limit": rate_config["requests"],
                "window": rate_config["window"],
                "current": rate_requests,
                "reset_in": max(0, reset_in)
            }
        
        # Request is allowed - record it
        self.requests[client_key].append(now)
        
        return True, {
            "limit_type": "none",
            "limit": rate_config["requests"],
            "window": rate_config["window"],
            "current": rate_requests + 1,
            "remaining": rate_config["requests"] - rate_requests - 1
        }
    
    def _cleanup_old_requests(self, client_key: str, now: float, window: int) -> None:
        """Remove requests outside the time window."""
        cutoff = now - window
        while self.requests[client_key] and self.requests[client_key][0] < cutoff:
            self.requests[client_key].popleft()
    
    def _count_requests_in_window(self, client_key: str, now: float, window: int) -> int:
        """Count requests within the specified time window."""
        cutoff = now - window
        return sum(1 for timestamp in self.requests[client_key] if timestamp >= cutoff)
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """
        Get rate limiting statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict: Client rate limiting statistics
        """
        now = time.time()
        stats = {}
        
        for endpoint_category in self.limits.keys():
            client_key = f"{client_id}:{endpoint_category}"
            rate_config = self.limits[endpoint_category]
            
            # Clean and count recent requests
            self._cleanup_old_requests(client_key, now, rate_config["window"])
            recent_requests = len(self.requests[client_key])
            
            stats[endpoint_category] = {
                "requests_in_window": recent_requests,
                "limit": rate_config["requests"],
                "window": rate_config["window"],
                "remaining": max(0, rate_config["requests"] - recent_requests)
            }
        
        return stats
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get global rate limiting statistics.
        
        Returns:
            Dict: Global statistics across all clients
        """
        now = time.time()
        total_clients = len(set(key.split(":")[0] for key in self.requests.keys()))
        total_requests = sum(len(requests) for requests in self.requests.values())
        
        # Calculate requests per endpoint
        endpoint_stats = defaultdict(int)
        for key, requests in self.requests.items():
            endpoint = key.split(":")[1] if ":" in key else "unknown"
            endpoint_stats[endpoint] += len(requests)
        
        return {
            "total_clients": total_clients,
            "total_active_requests": total_requests,
            "endpoint_breakdown": dict(endpoint_stats),
            "rate_limits": self.limits,
            "burst_limits": self.burst_limits,
            "timestamp": now
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit_middleware(request: Request) -> None:
    """
    FastAPI middleware function for rate limiting.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_id = rate_limiter.get_client_id(request)
    endpoint_category = rate_limiter.get_endpoint_category(request)
    
    is_allowed, limit_info = rate_limiter.is_allowed(client_id, endpoint_category)
    
    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for client {client_id} on {endpoint_category}: "
            f"{limit_info['current']}/{limit_info['limit']} requests"
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests for {endpoint_category}",
                "limit_type": limit_info["limit_type"],
                "limit": limit_info["limit"],
                "window_seconds": limit_info["window"],
                "current_requests": limit_info["current"],
                "reset_in_seconds": limit_info["reset_in"],
                "client_id": client_id[:8] + "..." if len(client_id) > 8 else client_id
            },
            headers={
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": str(limit_info.get("remaining", 0)),
                "X-RateLimit-Reset": str(int(time.time() + limit_info["reset_in"])),
                "Retry-After": str(limit_info["reset_in"])
            }
        )
    
    # Add rate limit headers to successful requests
    request.state.rate_limit_info = limit_info


def rate_limit_decorator(endpoint_category: str = None):
    """
    Decorator for applying rate limiting to specific endpoints.
    
    Args:
        endpoint_category: Override endpoint category detection
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_id = rate_limiter.get_client_id(request)
            category = endpoint_category or rate_limiter.get_endpoint_category(request)
            
            is_allowed, limit_info = rate_limiter.is_allowed(client_id, category)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "category": category,
                        **limit_info
                    }
                )
            
            # Store rate limit info for response headers
            request.state.rate_limit_info = limit_info
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator