"""Tests for user registration, login, logout, and /me."""
import pytest


@pytest.mark.asyncio
async def test_register_returns_201(client):
    r = await client.post(
        "/api/v1/users/register",
        json={"email": "newuser@example.com", "password": "Secure1!Pass"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_login_sets_cookie(client):
    await client.post(
        "/api/v1/users/register",
        json={"email": "cookieuser@example.com", "password": "Secure1!Pass"},
    )
    r = await client.post(
        "/api/v1/users/login",
        json={"email": "cookieuser@example.com", "password": "Secure1!Pass"},
    )
    assert r.status_code == 200
    assert "session" in r.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post(
        "/api/v1/users/login",
        json={"email": "nobody@example.com", "password": "WrongPass1!"},
    )
    assert r.status_code == 401
