"""
rate_limit.py — Redis-backed rate limiting using fastapi-limiter.
Initialised at app startup. Limits configurable per-route.
No business logic. No DB calls.
"""
import redis.asyncio as aioredis
from fastapi import Depends
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from config import settings

DEFAULT_TIMES = 60
DEFAULT_SECONDS = 60


async def init_limiter() -> None:
    """
    Connect to Redis and initialise fastapi-limiter.
    Must be called once during app startup.
    """
    redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await FastAPILimiter.init(redis)


def RateLimitDepend(times: int = DEFAULT_TIMES, seconds: int = DEFAULT_SECONDS):
    """
    Returns a FastAPI dependency for per-IP rate limiting.

    Usage:
        @router.post("/login", dependencies=[RateLimitDepend(times=5, seconds=60)])

    Default: 60 requests per 60 seconds.
    """
    return Depends(RateLimiter(times=times, seconds=seconds))
