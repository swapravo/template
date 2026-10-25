"""
utils.py — Pure helper functions with no side effects.
No imports from other project modules.
Every function here is unit-testable without mocks.
"""
import os
import re
import uuid
from datetime import datetime, timezone

import bcrypt


def ensure_env(name: str) -> str:
    """
    Read an environment variable and raise RuntimeError if it is not defined.
    This is the ONLY function outside config.py allowed to access os.environ.
    Used as a safety net — config.py is the canonical way to read config.
    """
    value = os.environ.get(name)
    if value is None:
        raise RuntimeError(
            f"Required environment variable '{name}' is not defined. "
            "Check your .env file."
        )
    return value


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def new_uuid() -> str:
    """Return a new UUID v4 as a string."""
    return str(uuid.uuid4())
