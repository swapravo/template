"""
database.py — asyncpg connection pool and all database query functions.
Raw SQL only. Returns plain Python dicts. No business logic. No ORM.
Only this file imports asyncpg.
"""
from __future__ import annotations

import asyncpg

from config import settings
from utils import hash_password

_pool: asyncpg.Pool | None = None


# ---------------------------------------------------------------------------
# Pool lifecycle
# ---------------------------------------------------------------------------

async def init_pool() -> asyncpg.Pool:
    """Create and store the global asyncpg connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=2,
        max_size=10,
    )
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Return the active pool. Raises if init_pool() has not been called."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised. Call init_pool() first.")
    return _pool


async def close_pool() -> None:
    """Close the connection pool on app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ---------------------------------------------------------------------------
# Schema + seed
# ---------------------------------------------------------------------------

async def run_schema(pool: asyncpg.Pool) -> None:
    """Execute schema.sql to create tables and indexes (idempotent)."""
    with open("schema.sql") as f:
        sql = f.read()
    async with pool.acquire() as conn:
        await conn.execute(sql)


async def seed_initial_user(pool: asyncpg.Pool) -> None:
    """Insert the seed admin user on first startup. Safe to run multiple times."""
    pw_hash = hash_password(settings.SEED_USER_PASSWORD)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES ($1, $2)
            ON CONFLICT (email) DO NOTHING
            """,
            settings.SEED_USER_EMAIL,
            pw_hash,
        )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user_by_id(pool: asyncpg.Pool, user_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return dict(row) if row else None


async def get_user_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
    return dict(row) if row else None


async def create_user(pool: asyncpg.Pool, email: str, password_hash: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (email, password_hash)
            VALUES ($1, $2)
            RETURNING *
            """,
            email,
            password_hash,
        )
    return dict(row)


# ---------------------------------------------------------------------------
# Request logs  (append-only — INSERT only, never UPDATE or DELETE)
# ---------------------------------------------------------------------------

async def log_request(
    pool: asyncpg.Pool,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    user_id: str | None = None,
    session_id: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Append a request log row. This function must never issue UPDATE or DELETE."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO request_logs
                (method, path, status_code, duration_ms, user_id, session_id, ip_address)
            VALUES ($1, $2, $3, $4, $5::uuid, $6, $7)
            """,
            method,
            path,
            status_code,
            duration_ms,
            user_id,
            session_id,
            ip_address,
        )
