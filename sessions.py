"""
sessions.py — Stateless JWT session management.
Handles token creation, decoding, and browser cookie operations.
No DB calls. Sessions live entirely in signed JWTs stored in HttpOnly cookies.
"""
from __future__ import annotations

from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, Request, Response, status

from config import settings
from utils import now_utc

COOKIE_NAME = "session"


def create_token(user_id: str, email: str) -> str:
    """Create a signed JWT for the given user identity."""
    expire = now_utc() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Raises HTTP 401 on expiry or any signature/format error.
    Returns the raw payload dict on success.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )


def set_session_cookie(response: Response, token: str) -> None:
    """
    Write the JWT into a secure HttpOnly cookie.
    secure=True  — only sent over HTTPS.
    samesite=lax — protects against most CSRF scenarios.
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie (logout)."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency. Extracts and validates the JWT from the session cookie.
    Raises HTTP 401 if the cookie is absent or the token is invalid/expired.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return decode_token(token)
