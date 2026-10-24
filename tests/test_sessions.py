"""Tests for sessions.py JWT utilities."""
import pytest
from fastapi import HTTPException
from sessions import create_token, decode_token


def test_create_and_decode_token():
    token = create_token("user-123", "user@example.com")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "user@example.com"
    assert "exp" in payload


def test_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_tampered_token_raises_401():
    token = create_token("user-abc", "x@y.com")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401
