"""Tests for utils.py pure helper functions."""
import pytest
from utils import ensure_env, hash_password, new_uuid, slugify, verify_password


def test_hash_and_verify():
    hashed = hash_password("MySecret1!")
    assert verify_password("MySecret1!", hashed)
    assert not verify_password("WrongPass", hashed)


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Spaces & Stuff  ") == "spaces-stuff"
    assert slugify("already-slugged") == "already-slugged"


def test_new_uuid_is_v4():
    import uuid
    val = new_uuid()
    uuid.UUID(val, version=4)


def test_ensure_env_raises_on_missing(monkeypatch):
    monkeypatch.delenv("_MISSING_VAR_XYZ", raising=False)
    with pytest.raises(RuntimeError, match="_MISSING_VAR_XYZ"):
        ensure_env("_MISSING_VAR_XYZ")


def test_ensure_env_returns_value(monkeypatch):
    monkeypatch.setenv("_TEST_VAR", "hello")
    assert ensure_env("_TEST_VAR") == "hello"
