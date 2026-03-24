# Changelog

All notable changes to Budgie will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-03-24

### Added

- **Desktop adaptation** — responsive sidebar (desktop) + bottom dock (mobile), keyboard input support, action buttons, hover-to-delete
- **CI workflow** — GitHub Actions `ci.yml` with backend (ruff, mypy, pytest) and frontend (vue-tsc, eslint, vitest) quality checks
- **Detailed documentation** — SECRET_KEY and CORS_ORIGINS configuration guides with examples (EN + FR)
- **README overhaul** — CI/Docker badges, features table, license, corrected doc links and commands

### Changed

- **Navigation** — replaced `BottomNav` with `AppNav` (responsive: sidebar on desktop, dock on mobile)
- **QuickExpense** — transparent input with autofocus, strict amount validation, Escape to close, dot accepted as comma

### Removed

- **MVP_MODE** — authentication is now always enforced via JWT; removed `mvp_mode` setting, auth bypass in `deps.py`, and test/CI overrides

### Fixed

- 8 failing backend tests caused by `MVP_MODE=true` leaking from `.env` into test suite
- 18 pytest-asyncio warnings from global `pytestmark` applied to sync tests
- 3 ruff errors (E402 import order, N806 uppercase local variables)
- `vue-tsc` command references (was incorrectly `tsc --noEmit`)
- Broken documentation links in README (pointed to nonexistent files)

---

## [0.1.0] — 2025-12-01

Initial release — all 8 project phases complete.

### Added

- **Backend** — FastAPI + SQLAlchemy 2.0 async + SQLite (integer centimes) + Alembic migrations
- **Authentication** — JWT + bcrypt, user registration and login
- **Accounts** — CRUD for bank accounts (checking, savings, credit, cash)
- **Categories & Groups** — hierarchical category management with sort order
- **Envelopes** — envelope-based budgeting with optional rollover, M2M category assignment
- **Transactions** — full CRUD with filters (account, category, date, virtual/real)
- **Bank import** — CSV (auto-detect separator/decimal/columns), Excel, QIF, OFX parsers with SHA-256 deduplication
- **Auto-categorization** — payee history match + priority-based custom rules (contains/exact/regex)
- **Budget engine** — monthly envelope view with budgeted/activity/available, cumulative rollover, to-be-budgeted calculation
- **Virtual transactions** — forecasts with budget impact, automatic matching on import (±10% amount, ±60 days)
- **Frontend** — Vue 3 + TypeScript + Pinia + Tailwind CSS + DaisyUI 5, mobile-first PWA
- **Quick Expense** — fast transaction entry with configurable presets and geolocation suggestions (OpenStreetMap)
- **Theme** — dark/light toggle (emerald/night), OS preference detection, localStorage persistence
- **Docker** — multi-stage Dockerfile (Node 22 + Python 3.12), docker-compose with PUID/PGID support, health check
- **CI/CD** — GitHub Actions Docker build + push to GHCR with smoke test
- **Backup** — `scripts/backup.sh` with configurable retention
- **Documentation** — bilingual user & developer guides (EN + FR), project plan
