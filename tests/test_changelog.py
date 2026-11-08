"""Guards for the changelog and release notes.

The changelog carries an open ``[Unreleased]`` section, and the version has its
release entry. A pull request adds its entry under ``## [Unreleased]`` and does
not touch the version; the release commit (``.claude/skills/release/SKILL.md``)
turns the heading into the version and re-opens an empty one. These checks bite
where that process rots: no section to write in, a version with no release
entry, release notes about another version (which ``docker.yml`` would publish
as they are).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNRELEASED = "## [Unreleased]"
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
VERSION: str = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]


def test_the_app_has_a_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION)


def test_an_unreleased_section_is_open() -> None:
    assert UNRELEASED in CHANGELOG, (
        "no `## [Unreleased]` in CHANGELOG.md: a release must re-open one"
    )


def test_unreleased_comes_before_every_version() -> None:
    first_version = re.search(r"(?m)^## \[\d+\.\d+\.\d+\]", CHANGELOG)
    assert first_version is not None, "no version heading in CHANGELOG.md"
    assert CHANGELOG.index(UNRELEASED) < first_version.start(), (
        "`## [Unreleased]` must come first"
    )


def test_the_version_has_its_release_entry() -> None:
    heading = rf"(?m)^## \[{re.escape(VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}\r?$"
    assert re.search(heading, CHANGELOG), (
        f"no `## [{VERSION}] - YYYY-MM-DD` heading for the version of pyproject.toml"
    )


def test_the_release_notes_are_about_the_version() -> None:
    notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert notes.splitlines()[0] == f"# Budgie — {VERSION}"
