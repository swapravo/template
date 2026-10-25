"""
request_log.py — FastAPI middleware for structured, append-only request logging.
Writes one row to request_logs per request. Never updates or deletes rows.
Read-only: never modifies the request or response objects.
"""
from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

import database
from sessions import COOKIE_NAME, decode_token


class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    Times every HTTP request and appends a log row to the DB.
    Logging failures are swallowed — they must never break a response.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id: str | None = None
        session_id: str | None = None

        # Best-effort identity extraction from the session cookie
        try:
            token = request.cookies.get(COOKIE_NAME)
            if token:
                payload = decode_token(token)
                user_id = payload.get("sub")
                session_id = token[-12:]  # opaque short ref, not the full token
        except Exception:
            pass

        ip_address = request.client.host if request.client else None

        try:
            pool = await database.get_pool()
            await database.log_request(
                pool=pool,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )
        except Exception:
            pass  # logging failure is non-fatal

        return response
