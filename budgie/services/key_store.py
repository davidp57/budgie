"""In-memory session encryption key store.

Holds AES-256-GCM encryption keys in server RAM during authenticated sessions.
Keys are **never** persisted to disk or written to logs.

The store maps ``user_id`` → ``(key, expiry)``, where ``expiry`` is a monotonic
timestamp after which the entry is treated as absent.  Keys are added on
passphrase unlock and removed on logout, expiry, or server restart.
"""

import threading
import time
from typing import ClassVar

# Default TTL matches the JWT access-token lifetime (24 h).
_DEFAULT_TTL_SECONDS: int = 60 * 60 * 24


class _KeyStore:
    """Thread-safe in-memory store mapping user IDs to timed encryption keys."""

    _store: ClassVar[dict[int, tuple[bytes, float]]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def set(
        cls,
        user_id: int,
        key: bytes,
        expires_in: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        """Store an encryption key for a user session.

        Args:
            user_id: The user's primary key.
            key: Raw 32-byte AES-256 key.
            expires_in: TTL in seconds before the key is considered expired.
                Defaults to ``_DEFAULT_TTL_SECONDS`` (24 h).
        """
        expiry = time.monotonic() + expires_in
        with cls._lock:
            cls._store[user_id] = (key, expiry)

    @classmethod
    def get(cls, user_id: int) -> bytes | None:
        """Retrieve the encryption key for a user session.

        Expired entries are purged automatically on access.

        Args:
            user_id: The user's primary key.

        Returns:
            The 32-byte key, or ``None`` if not present or already expired.
        """
        with cls._lock:
            entry = cls._store.get(user_id)
            if entry is None:
                return None
            key, expiry = entry
            if time.monotonic() > expiry:
                del cls._store[user_id]
                return None
            return key

    @classmethod
    def delete(cls, user_id: int) -> None:
        """Remove the encryption key for a user (e.g. on logout).

        Args:
            user_id: The user's primary key.
        """
        with cls._lock:
            cls._store.pop(user_id, None)

    @classmethod
    def purge_expired(cls) -> None:
        """Remove all entries whose TTL has elapsed."""
        now = time.monotonic()
        with cls._lock:
            expired = [uid for uid, (_, exp) in cls._store.items() if now > exp]
            for uid in expired:
                del cls._store[uid]

    @classmethod
    def clear(cls) -> None:
        """Purge all stored keys (e.g. on server shutdown)."""
        with cls._lock:
            cls._store.clear()


# Module-level singleton
key_store = _KeyStore()
