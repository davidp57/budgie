"""Tests for startup configuration checks (JWT signing key)."""

import secrets

import pytest
from budgie import config, main
from budgie.config import SECRET_KEY_MIN_LENGTH, check_secret_key


@pytest.mark.parametrize("key", sorted(config._PUBLIC_SECRET_KEYS))
def test_public_placeholder_keys_rejected(key: str) -> None:
    """Keys published in the repository are refused."""
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        check_secret_key(key)


@pytest.mark.parametrize("key", ["", "x" * (SECRET_KEY_MIN_LENGTH - 1)])
def test_short_keys_rejected(key: str) -> None:
    """Empty or short keys are refused."""
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        check_secret_key(key)


def test_random_key_accepted() -> None:
    """A key generated as the documentation recommends is accepted."""
    check_secret_key(secrets.token_hex(32))


def test_settings_default_is_rejected() -> None:
    """Without SECRET_KEY in the environment, the default cannot be used."""
    default = config.Settings.model_fields["secret_key"].default
    with pytest.raises(RuntimeError):
        check_secret_key(default)


async def test_lifespan_refuses_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The app does not start, and runs no migration, with a public key."""
    migrations_run = False

    def _fake_migrations() -> None:
        nonlocal migrations_run
        migrations_run = True

    placeholder = next(iter(config._PUBLIC_SECRET_KEYS))
    monkeypatch.setattr(main.settings, "secret_key", placeholder)
    monkeypatch.setattr(main, "_run_migrations", _fake_migrations)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        async with main.lifespan(main.app):
            pass
    assert not migrations_run


async def test_lifespan_starts_with_valid_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """A valid key lets startup proceed to the migrations."""
    migrations_run = False

    def _fake_migrations() -> None:
        nonlocal migrations_run
        migrations_run = True

    monkeypatch.setattr(main.settings, "secret_key", secrets.token_hex(32))
    monkeypatch.setattr(main.settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(main, "_run_migrations", _fake_migrations)

    async with main.lifespan(main.app):
        pass
    assert migrations_run
