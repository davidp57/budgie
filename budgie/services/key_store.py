"""In-memory session encryption key store.

Holds AES-256-GCM encryption keys in server RAM during authenticated sessions.
Keys are **never** persisted to disk or written to logs.

The store maps ``user_id`` → raw 32-byte key.  Keys are added on passphrase
unlock and removed on logout or server restart.
"""

import threading
from typing import ClassVar


class _KeyStore:
    """Thread-safe in-memory store mapping user IDs to their encryption key bytes."""

    _store: ClassVar[dict[int, bytes]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def set(cls, user_id: int, key: bytes) -> None:
        """Store an encryption key for a user session.

        Args:
            user_id: The user's primary key.
            key: Raw 32-byte AES-256 key.
        """
        with cls._lock:
            cls._store[user_id] = key

    @classmethod
    def get(cls, user_id: int) -> bytes | None:
        """Retrieve the encryption key for a user session.

        Args:
            user_id: The user's primary key.

        Returns:
            The 32-byte key, or ``None`` if not unlocked for this session.
        """
        with cls._lock:
            return cls._store.get(user_id)

    @classmethod
    def delete(cls, user_id: int) -> None:
        """Remove the encryption key for a user (e.g. on logout).

        Args:
            user_id: The user's primary key.
        """
        with cls._lock:
            cls._store.pop(user_id, None)

    @classmethod
    def clear(cls) -> None:
        """Purge all stored keys (e.g. on server shutdown)."""
        with cls._lock:
            cls._store.clear()


# Module-level singleton
key_store = _KeyStore()
