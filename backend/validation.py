"""
validation.py — Custom business-rule validators.
All functions are pure: no DB calls, no HTTP calls, no file I/O.
Each function takes a value, returns True if valid, or raises ValueError.
"""
from __future__ import annotations

import re
import uuid


# ---------------------------------------------------------------------------
# SQL injection detection
# ---------------------------------------------------------------------------

_SQL_INJECTION_RE = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|UNION|"
    r"DECLARE|CAST|CONVERT|CHAR|NCHAR|VARCHAR|OR|AND)\b"
    r"|--|;|/\*|\*/|xp_|0x[0-9a-fA-F]+)",
    re.IGNORECASE,
)


def check_sql_injection(value: str) -> bool:
    """
    Raise ValueError if the value contains common SQL injection patterns.
    Returns True if the input appears safe.
    """
    if _SQL_INJECTION_RE.search(value):
        raise ValueError("Input contains potentially unsafe SQL patterns.")
    return True


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def validate_email_format(email: str) -> bool:
    """Raise ValueError if the email address format is invalid."""
    if not _EMAIL_RE.match(email.strip()):
        raise ValueError(f"Invalid email format: {email!r}")
    return True


# ---------------------------------------------------------------------------
# Password strength
# ---------------------------------------------------------------------------

def validate_password_strength(password: str) -> bool:
    """
    Enforce password strength rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one digit
    - At least one special character

    Raises ValueError with a specific message for each failed rule.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character.")
    return True


# ---------------------------------------------------------------------------
# UUID v4
# ---------------------------------------------------------------------------

def validate_uuid_format(value: str) -> bool:
    """Raise ValueError if the string is not a valid UUID v4."""
    try:
        parsed = uuid.UUID(value, version=4)
        if str(parsed) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid UUID v4 format: {value!r}")
    return True


# ---------------------------------------------------------------------------
# String sanitisation
# ---------------------------------------------------------------------------

_DANGEROUS_CHARS_RE = re.compile(r'[<>"\'`;\\]')


def sanitize_string(value: str) -> str:
    """Strip characters that are dangerous in HTML/SQL contexts."""
    return _DANGEROUS_CHARS_RE.sub("", value)
