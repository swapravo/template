"""
main.py — FastAPI application entry point.
Registers middleware, mounts routers, and manages the app lifecycle.
No business logic. No DB calls. No direct route handlers.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from config import settings
from rate_limit import init_limiter
from request_log import RequestLogMiddleware
from routers import files, health, jobs, users

app = FastAPI(
    title="Template API",
    description="FastAPI + asyncpg + Celery + RustFS backend template.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ---------------------------------------------------------------------------
# Middleware  (outermost registered = outermost executed on the way in)
# ---------------------------------------------------------------------------

app.add_middleware(RequestLogMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        f"http://localhost:{settings.LANDING_PORT}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(users.router)
app.include_router(files.router)
app.include_router(jobs.router)

# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup() -> None:
    pool = await database.init_pool()
    await database.run_schema(pool)
    await database.seed_initial_user(pool)
    await init_limiter()


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.close_pool()


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=True,
    )
