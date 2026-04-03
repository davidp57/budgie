# Changelog

All notable changes to Budgie will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.9.1] - 2026-04-03

### Fixed

- **Reconciliation view labels decrypted** — transaction labels imported from a bank were displayed as raw base64 ciphertexts in the reconciliation view when end-to-end encryption was enabled; the reconciliation service now correctly decrypts `memo` fields using the session key before returning them to the UI

---

## [0.9.0] - 2026-04-02

### Added

- **Passkey unlock (PRF)** — logging in with a passkey (Face ID / Touch ID via 1Password or a compatible authenticator) now automatically unlocks end-to-end encryption without any PIN or passphrase prompt; the encryption passphrase is wrapped locally using the WebAuthn PRF extension and never sent to the server

### Fixed

- **PRF extension requested at registration** — `extensions: {prf: {}}` is now included in WebAuthn registration options so that FIDO2-compliant authenticators (1Password, etc.) expose PRF output on future authentications; existing passkeys must be deleted and re-registered once for PRF to take effect
- **In-memory PRF output reused** — when the user logs in with a passkey and then enters their passphrase manually, the PRF output already held in memory is used to save the wrapped passphrase silently, without requiring a second authenticator gesture
- **Auto-upgrade PIN → PRF** — if the user had a PIN stored and logs in with a passkey that provides PRF output, the passphrase is silently re-wrapped with PRF; subsequent logins no longer require the PIN

---

## [0.8.0] - 2026-04-02

### Added

- **Sticky budget inheritance** — for non-rollover envelopes with no explicit allocation in the current month, the budgeted amount is automatically carried forward from the most recent prior month; a `↩` indicator appears next to any inherited amount in the UI (budget table, drawer tiles, and drawer subtitle)
- **`is_budget_inherited` flag** — the budget API response now includes a boolean field per envelope signalling whether the displayed amount was inherited from a prior month rather than set explicitly

### Security

- **Encryption at rest** — payee names, transaction memos, descriptions, and notes are now encrypted server-side using AES-256-GCM; existing data is migrated transparently on first startup with the encryption key configured via `FIELD_ENCRYPTION_KEY`

### Changed

- **Budget query performance** — sticky-budget inheritance now uses a single window-function SQL query (`ROW_NUMBER OVER PARTITION BY`) instead of a second round-trip to find the most recent prior allocation

---

## [0.7.0] - 2026-03-31

### Added

- **Grouped expense dashboard** — the Expenses view now groups spending by category group, with drill-down into individual category breakdowns per envelope
- **Budget metrics** — envelope cards now show the number of expenses and the count of off-budget (unassigned) expenses directly on the Budget page
- **Expense editing** — any manually-entered expense can be edited inline from the Expenses page: change the date, amount, description, category or envelope, or delete with a confirmation step
- **Quick expense without a category** — the Quick Expense form no longer requires a configured category: expenses can be recorded directly linked to an envelope; off-budget expenses can also be entered from the Budget page banner
- **Community files** — `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` added for open-source contributors
- **Tutorials** — step-by-step installation and usage guides in English and French

### Changed

- **CI** — backend lint and test jobs now run in parallel; Poetry and mypy caches added; Docker images are built on Git tags only, with `develop-latest`/`latest`/`x.y.z` tagging strategy

---

## [0.6.1] - 2026-03-30

### Fixed

- **App startup failure** — application hung on first launch when the `data/` directory did not exist; directory is now created before Alembic migrations run
- **Double login loop after wrong PIN** — `/unlock` returned HTTP 401 for an incorrect passphrase, which the axios interceptor misinterpreted as an expired JWT, clearing the token and redirecting to login in a loop; fixed by returning HTTP 400 instead
- **Mobile dock hidden behind content** — DaisyUI dock (`z-index: 1`) was rendered below envelope cards; fixed with `z-50` on the dock, `viewport-fit=cover` in the viewport meta, and correct `env(safe-area-inset-bottom)` padding on the main content area
- **Geolocation timeout on iPhone** — GPS cold-start with `enableHighAccuracy: true` frequently timed out; added fallback retry with `enableHighAccuracy: false` (network-based positioning)
- **Category rule pattern length** — `max_length` corrected from 200 to 100 characters to match the database constraint

### Security

- **Rate limiting** — brute-force protection on auth endpoints (`/login`, `/unlock`, `/register`) via SlowAPI
- **JWT blocklist** — revoked tokens tracked server-side (HMAC-signed, no DB required); logout effectively invalidates the token
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`, and `Cache-Control: no-store` added to all API responses
- **Password hashing** — bcrypt rounds raised from 10 to 12
- **Request size limit** — incoming requests capped at 10 MB
- **Input sanitisation** — HTML stripped from all free-text inputs (payee name, memo, description)

---

## [0.6.0] - 2026-03-28

### Added

- **Expenses page** — new dedicated view (`/depenses`) to browse and manage manually-entered transactions month by month, with filters (envelope, category group), sort, and grouping options
- **Expense edit modal** — edit date, amount, description, category or envelope directly from the Expenses page; delete with confirmation
- **Dashboard mode** 🥧 — doughnut charts showing spending by category for each envelope; click a slice to drill down into the matching transactions
- **Linked bank transaction display** — reconciled expenses show a link to the corresponding bank import
- **Direct envelope link on transactions** — transactions now carry an optional `envelope_id` field linking them directly to an envelope, independently of any category; enables expense entry without a configured category
- **QuickExpense: category-free entry** — Quick Expense sends `envelope_id` directly; no category required
- **Reconciliation: envelope name display** — reconciliation view shows the envelope name on expenses entered via direct link
- **Filter transactions by envelope** — `GET /api/transactions?envelope_id=X`

### Changed

- **Navigation** — "Transactions" renamed to "Dépenses", route changed to `/depenses`
- **Budget activity dual-path** — budget engine aggregates activity from both direct `envelope_id` and category-based paths without double-counting
- **Reconciliation `link()`** — `envelope_id` is propagated from expense to bank transaction on linking

---

## [0.5.0] - 2026-03-27

### Added

- **Amount range on category rules** — `min_amount` / `max_amount` optional fields on `CategoryRule`; rules only match transactions whose absolute amount falls within the defined range
- **Transaction type on category rules** — `transaction_type` field (`debit` / `credit` / `any`) on `CategoryRule`; rules can now be restricted to debits or credits only
- **Skip-rule toggle in reconciliation wizard** — when linking a bank transaction to an expense, a toggle lets the user choose whether to create a matching rule (default: create)

### Fixed

- **Rule matching** — `_matches_rule` now correctly enforces amount bounds and transaction type; previously only the text pattern was checked
- **Rule options not sent** — in the reconciliation wizard, rule options (amount mode, tolerance, transaction type) were reset before being read; values are now captured before the modal closes

### Changed

- **Reconciliation view** — refreshes automatically when rules are created, edited or deleted from the Rules modal
- **Reconciliation view** — text search field now has a ✕ clear button
- **Reconciliation view** — header layout uses CSS container queries for reliable single-line display on wide screens

---

## [0.3.0] — 2026-03-24

### Added

- **WebAuthn passkeys** — FIDO2 passkey registration and authentication via `py_webauthn`; replaces password-only login as the primary authentication method
- **End-to-end encryption** — AES-256-GCM field encryption with Argon2id key derivation; `is_encrypted`, `encryption_salt`, `challenge_blob`, and `argon2_params` stored per user row
- **PIN-based key wrapping** — PBKDF2-HMAC-SHA-256 derived wrapping key encrypts the session key via AES-KW and persists it in `localStorage`
- **In-memory key store** — server-side `_KeyStore` holds per-user AES-256-GCM keys in RAM with TTL matching the JWT lifetime; keys are purged on logout or expiry
- **Passphrase wordlist generator** — 253-word BIP-39-style generator in `SetupEncryptionView` for strong, human-readable passphrases
- **Setup & unlock views** — `SetupEncryptionView.vue` and `UnlockEncryptionView.vue` with passphrase / PIN / WebAuthn flows

### Changed

- **Authentication** — JWT login now also supports WebAuthn passkey assertion; bcrypt password login retained as fallback
- **User model** — added `webauthn_credentials` relationship and encryption key material columns (Alembic migration)

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
