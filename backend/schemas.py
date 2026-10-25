"""
schemas.py — All Pydantic models for requests, responses, and internal DTOs.
No database calls. No file I/O. No HTTP calls.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    status: str
    database: str
    redis: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Auth / Sessions
# ---------------------------------------------------------------------------

class TokenPayload(BaseModel):
    sub: str    # user_id
    email: str
    exp: int    # unix timestamp


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

class LLMFile(BaseModel):
    filename: str
    mime_type: str
    content_base64: str


class LLMRequest(BaseModel):
    prompt: str
    files: list[LLMFile] | None = None
    output_type: Literal["string", "integer", "json"] = "string"


class LLMResponse(BaseModel):
    output: Any
    output_type: str
    model: str
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class StorageUploadResponse(BaseModel):
    key: str
    url: str
    content_type: str
    size_bytes: int


class StorageFileInfo(BaseModel):
    key: str
    size_bytes: int
    last_modified: datetime


class StoragePresignedUrlResponse(BaseModel):
    key: str
    url: str
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class JobTriggerRequest(BaseModel):
    message: str


class JobStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None


# ---------------------------------------------------------------------------
# Request Logs
# ---------------------------------------------------------------------------

class RequestLogEntry(BaseModel):
    id: UUID
    method: str
    path: str
    status_code: int
    duration_ms: int
    user_id: UUID | None
    session_id: str | None
    ip_address: str | None
    created_at: datetime
