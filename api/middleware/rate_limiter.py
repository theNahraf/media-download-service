"""
Rate limiting middleware — applies sliding window rate limiting per client IP.
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from api.services.cache_service import get_redis
from api.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiter for all API endpoints.
    Job-specific rate limiting is also done in the job creation route.
    This middleware protects against general API abuse.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/health"):
            return await call_next(request)

        # Skip for static assets
        if request.url.path.startswith("/static") or request.url.path == "/":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        try:
            r = await get_redis()
            key = f"global_rate:{client_ip}"
            now = time.time()
            window = 60  # 1-minute window for global rate limit

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            request_count = results[2]
            max_requests_per_minute = 120  # generous global limit

            if request_count > max_requests_per_minute:
                return Response(
                    content='{"error": "Too many requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"},
                )
        except Exception:
            # If Redis is down, allow the request (fail open for availability)
            pass

        response = await call_next(request)
        return response
