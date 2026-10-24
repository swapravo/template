"""
tests/conftest.py — Shared pytest fixtures.
Secrets must come from .env.test — never the production .env.
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("ENV_FILE", ".env.test")

from main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
