"""Tests for the Alembic migrations, run against a fresh SQLite file."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from budgie.config import settings

#: Revision before the recurring tags.
BEFORE_TAGS = "d7e8f9a0b1c2"
#: Revision adding the recurring tags.
TAGS = "e8f9a0b1c2d3"


def _config(db_file: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    # env.py takes the URL from the settings, not from the Alembic config.
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_file}")
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parent.parent / "alembic")
    )
    return config


def _tables(db_file: Path) -> set[str]:
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {name for (name,) in rows}


def test_recurring_tags_migration_goes_up_and_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "migrations.db"
    config = _config(db_file, monkeypatch)

    command.upgrade(config, TAGS)
    assert {"recurring_tags", "recurring_payment_tags"} <= _tables(db_file)
    with sqlite3.connect(db_file) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(recurring_tags)")}
        links = {
            row[1] for row in conn.execute("PRAGMA table_info(recurring_payment_tags)")
        }
    assert columns == {"id", "user_id", "name", "created_at"}
    assert links == {"payment_id", "tag_id"}

    command.downgrade(config, BEFORE_TAGS)
    assert not {"recurring_tags", "recurring_payment_tags"} & _tables(db_file)
    assert "recurring_payments" in _tables(db_file)
