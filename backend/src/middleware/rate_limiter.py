"""Redis-based sliding window rate limiter middleware for FastAPI."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import redis

from src.config import settings

# Rate limit config per path prefix
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/upload": (5, 3600),       # 5 uploads per hour
    "/api/jobs": (60, 60),          # 60 status checks per minute
    "/api/results": (30, 60),       # 30 result fetches per minute
}

DEFAULT_LIMIT = (100, 60)  # 100 requests per minute for everything else


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_rate_limit(path: str) -> tuple[int, int]:
    """Get (max_requests, window_seconds) for a given path."""
    for prefix, limits in RATE_LIMITS.items():
        if path.startswith(prefix):
            return limits
    return DEFAULT_LIMIT


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        try:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            self._redis.ping()
            self._enabled = True
        except Exception:
            self._enabled = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        client_ip = _get_client_ip(request)
        max_requests, window_seconds = _get_rate_limit(request.url.path)
        key = f"rate_limit:{client_ip}:{request.url.path.split('/')[2] if len(request.url.path.split('/')) > 2 else 'default'}"

        now = time.time()
        window_start = now - window_seconds

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            results = pipe.execute()

            request_count = results[2]

            if request_count > max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                    },
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, max_requests - request_count)
            )
            return response

        except Exception:
            # If Redis fails, allow the request through
            return await call_next(request)
