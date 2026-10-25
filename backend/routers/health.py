"""
routers/health.py — Liveness and readiness endpoints.
GET /api/v1/health  — process-level liveness (always 200 if running)
GET /api/v1/ready   — dependency check (DB + Redis), returns 503 if unhealthy
"""
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, status

import database
from config import settings
from schemas import HealthResponse, ReadinessResponse
from utils import now_utc

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe — returns 200 if the process is alive."""
    return HealthResponse(status="ok", timestamp=now_utc())


@router.get("/ready", response_model=ReadinessResponse)
async def ready():
    """
    Readiness probe — checks DB and Redis.
    Returns 503 if any dependency is unavailable.
    """
    db_status = "ok"
    redis_status = "ok"

    try:
        pool = await database.get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "unavailable"

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "unavailable"

    if db_status != "ok" or redis_status != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"database": db_status, "redis": redis_status},
        )

    return ReadinessResponse(
        status="ok",
        database=db_status,
        redis=redis_status,
        timestamp=now_utc(),
    )
