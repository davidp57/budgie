"""Tests for the in-memory key store with TTL support."""

import time
from collections.abc import Generator

import pytest
from budgie.services.key_store import _KeyStore


@pytest.fixture(autouse=True)
def clean_store() -> Generator[None, None, None]:
    """Clear the store before and after each test."""
    _KeyStore.clear()
    yield
    _KeyStore.clear()


SAMPLE_KEY = b"\x42" * 32  # arbitrary 32-byte key


def test_set_and_get_returns_key() -> None:
    """Stored key must be retrievable before expiry."""
    _KeyStore.set(1, SAMPLE_KEY)
    assert _KeyStore.get(1) == SAMPLE_KEY


def test_get_unknown_user_returns_none() -> None:
    """Getting a key for an unknown user ID must return None."""
    assert _KeyStore.get(999) is None


def test_delete_removes_key() -> None:
    """Deleting a key must prevent subsequent retrieval."""
    _KeyStore.set(1, SAMPLE_KEY)
    _KeyStore.delete(1)
    assert _KeyStore.get(1) is None


def test_delete_nonexistent_is_silent() -> None:
    """Deleting a non-existent key must not raise."""
    _KeyStore.delete(999)  # must not raise


def test_clear_removes_all_keys() -> None:
    """clear() must remove all stored keys."""
    _KeyStore.set(1, SAMPLE_KEY)
    _KeyStore.set(2, SAMPLE_KEY)
    _KeyStore.clear()
    assert _KeyStore.get(1) is None
    assert _KeyStore.get(2) is None


def test_expired_key_returns_none() -> None:
    """A key stored with a TTL of 0 must immediately be considered expired."""
    _KeyStore.set(1, SAMPLE_KEY, expires_in=0)
    # Sleep briefly to ensure monotonic time advances past the (now-or-past) expiry.
    time.sleep(0.01)
    assert _KeyStore.get(1) is None


def test_expired_key_is_auto_purged() -> None:
    """An expired key must be removed from the store on access."""
    _KeyStore.set(1, SAMPLE_KEY, expires_in=0)
    time.sleep(0.01)
    _KeyStore.get(1)  # triggers purge
    # Internal store must no longer hold the entry
    assert 1 not in _KeyStore._store


def test_purge_expired_removes_only_expired() -> None:
    """purge_expired() must remove only the expired entries."""
    _KeyStore.set(1, SAMPLE_KEY, expires_in=0)
    _KeyStore.set(2, SAMPLE_KEY, expires_in=3600)
    time.sleep(0.01)
    _KeyStore.purge_expired()
    assert _KeyStore.get(1) is None
    assert _KeyStore.get(2) == SAMPLE_KEY


def test_set_overwrites_existing_key() -> None:
    """Setting a key for the same user twice must use the latest key and TTL."""
    old_key = b"\x01" * 32
    new_key = b"\x02" * 32
    _KeyStore.set(1, old_key)
    _KeyStore.set(1, new_key)
    assert _KeyStore.get(1) == new_key
