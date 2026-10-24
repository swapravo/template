"""Tests for validation.py pure validators."""
import pytest
from validation import (
    check_sql_injection,
    sanitize_string,
    validate_email_format,
    validate_password_strength,
    validate_uuid_format,
)


def test_sql_injection_detected():
    with pytest.raises(ValueError):
        check_sql_injection("SELECT * FROM users")
    with pytest.raises(ValueError):
        check_sql_injection("1; DROP TABLE users")


def test_sql_injection_safe_inputs():
    assert check_sql_injection("hello world") is True
    assert check_sql_injection("user@example.com") is True


def test_email_valid():
    assert validate_email_format("user@example.com") is True


def test_email_invalid():
    with pytest.raises(ValueError):
        validate_email_format("not-an-email")


def test_password_strength_valid():
    assert validate_password_strength("Secure1!") is True


def test_password_strength_too_short():
    with pytest.raises(ValueError, match="8 characters"):
        validate_password_strength("Ab1!")


def test_password_no_uppercase():
    with pytest.raises(ValueError, match="uppercase"):
        validate_password_strength("alllower1!")


def test_password_no_digit():
    with pytest.raises(ValueError, match="digit"):
        validate_password_strength("NoDigits!")


def test_password_no_special():
    with pytest.raises(ValueError, match="special"):
        validate_password_strength("NoSpecial1")


def test_uuid_valid():
    import uuid
    assert validate_uuid_format(str(uuid.uuid4())) is True


def test_uuid_invalid():
    with pytest.raises(ValueError):
        validate_uuid_format("not-a-uuid")


def test_sanitize_strips_dangerous():
    result = sanitize_string('<script>alert("xss")</script>')
    assert "<" not in result
    assert ">" not in result
