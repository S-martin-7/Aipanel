"""
Rate limiting middleware for AIPanel.

Uses Redis for distributed rate limiting with sliding window algorithm.
"""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis
import time
import hashlib

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., IP, user_id, api_key)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_info)
        """
        client = await self.get_client()
        now = time.time()
        window_start = now - window_seconds

        # Use sorted set with timestamp as score
        rate_key = f"rate_limit:{key}"

        pipe = client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(rate_key, 0, window_start)

        # Count current requests
        pipe.zcard(rate_key)

        # Add current request
        pipe.zadd(rate_key, {f"{now}": now})

        # Set expiry on the key
        pipe.expire(rate_key, window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]

        # Calculate rate info
        remaining = max(0, limit - current_count - 1)
        reset_time = int(now + window_seconds)

        rate_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "window": window_seconds,
        }

        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for key: {key}")
            return False, rate_info

        return True, rate_info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """

    def __init__(
        self,
        app,
        limiter: RateLimiter,
        default_limit: int = 100,
        window_seconds: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.limiter = limiter
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or ["/health", "/live", "/ready", "/prometheus"]

    def _default_key_func(self, request: Request) -> str:
        """Generate rate limit key from request."""
        # Try to get API key or user ID from headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through rate limiter."""
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get rate limit key
        key = self.key_func(request)

        # Check rate limit
        try:
            is_allowed, rate_info = await self.limiter.is_allowed(
                key=key,
                limit=self.default_limit,
                window_seconds=self.window_seconds,
            )
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Allow request if rate limiter fails
            return await call_next(request)

        if not is_allowed:
            return Response(
                content='{"detail": "Rate limit exceeded. Try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info["window"]),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response


# Endpoint-specific rate limits
RATE_LIMITS = {
    "/api/v1/auth/login": {"limit": 10, "window": 60},  # 10 per minute
    "/api/v1/auth/register": {"limit": 5, "window": 60},  # 5 per minute
    "/api/v1/chat/completions": {"limit": 60, "window": 60},  # 60 per minute
    "/api/v1/chat/stream": {"limit": 30, "window": 60},  # 30 per minute
    "/api/v1/documents/upload": {"limit": 20, "window": 60},  # 20 per minute
}


def rate_limit(limit: int = 100, window: int = 60):
    """
    Decorator for endpoint-specific rate limiting.

    Usage:
        @router.post("/endpoint")
        @rate_limit(limit=10, window=60)
        async def endpoint():
            ...
    """
    def decorator(func):
        func._rate_limit = {"limit": limit, "window": window}
        return func
    return decorator


# Global rate limiter instance
rate_limiter = RateLimiter()
