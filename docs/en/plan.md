# Budgie 🐦 — Project Plan

🌐 [Version française](../fr/plan.md)

---

## Overview

Personal household budget management web app.
Import bank transactions, auto-categorize, manage envelope budgets, plan future purchases with virtual transactions.

---

## Stack

| Layer | Choice |
|---|---|
| Name | **Budgie** 🐦 |
| Backend | Python 3.12+, FastAPI, Poetry |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Database | SQLite (amounts in integer centimes) |
| Frontend | Vue.js 3, Composition API, TypeScript, Vite |
| CSS | DaisyUI (Tailwind CSS) |
| Auth | JWT + bcrypt + WebAuthn (Passkeys) |
| Encryption | AES-256-GCM, Argon2 (key derivation) |
| Import | CSV, Excel, QIF, OFX |
| Categorization | Rules + payee history (MVP) |
| Deployment | Docker Compose on Synology NAS |
| Testing | pytest + pytest-asyncio, Vitest |
| Linting | ruff, mypy, ESLint, Prettier |

---

## Phase 0 — Foundations

### 0.1 — Poetry project init

- [x] Initialize Poetry project in workspace root
- [x] `pyproject.toml` with metadata, Python >=3.12
- [x] Runtime dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `pydantic-settings`, `python-multipart`, `bcrypt`, `python-jose[cryptography]`
- [x] Import dependencies: `pandas`, `openpyxl`, `quiffen`, `ofxtools`
- [x] Dev dependencies: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pytest-cov`

### 0.2 — Backend project structure

- [x] Create `budgie/` package with `__init__.py`
- [x] Create subpackages: `models/`, `schemas/`, `api/`, `services/`, `importers/`
- [x] Create `budgie/config.py` — Pydantic `BaseSettings` loading from `.env`
- [x] Create `budgie/database.py` — async SQLAlchemy engine + session factory
- [x] Create `budgie/main.py` — FastAPI app with CORS, router mounting, health check
- [x] Create `.env.example` with all config variables
- [x] Create `tests/conftest.py` with async test fixtures (test DB, test client)

### 0.3 — Frontend project init

- [x] Initialize Vue.js 3 project in `frontend/` via `create-vue` (Vite + TS + Router + Pinia)
- [x] Install DaisyUI + Tailwind CSS
- [x] Install axios
- [x] Configure Vite proxy to forward `/api` to FastAPI dev server
- [x] Configure ESLint + Prettier

### 0.4 — Tooling & CI

- [x] Configure `ruff` in `pyproject.toml` (linting + formatting rules)
- [x] Configure `mypy` in `pyproject.toml` (strict mode)
- [x] VS Code workspace settings: ruff, mypy, Pylance, ESLint integration
- [x] Create `.gitignore` (Python, Node, data/, .env, `__pycache__`, etc.)

### 0.5 — Docker

- [x] `Dockerfile` — multi-stage: (1) Node build of Vue → static files, (2) Python slim runtime
- [x] `docker-compose.yml` — single service, volume for `data/`, port 8080, health check, `mem_limit: 256m`, `restart: unless-stopped`
- [x] `entrypoint.sh` — PUID/PGID support (LinuxServer.io pattern) via `gosu` for Synology bind-mount permission handling
- [x] `scripts/backup.sh` — timestamped SQLite backup with configurable retention (default 7 days)

---

## Phase 1 — Data Model

### 1.1 — SQLAlchemy models

All amounts stored as **integer centimes** (e.g., `1050` = 10.50€).

- [x] `User` — `id`, `username` (unique), `hashed_password`, `created_at`
- [x] `Account` — `id`, `user_id`, `name`, `type` (checking/savings/credit/cash), `on_budget`, `created_at`
- [x] `CategoryGroup` — `id`, `user_id`, `name`, `sort_order`
- [x] `Category` — `id`, `group_id`, `name`, `sort_order`, `hidden`
- [x] `Payee` — `id`, `user_id`, `name`, `auto_category_id` (FK nullable → Category)
- [x] `Transaction` — `id`, `account_id`, `date`, `payee_id`, `category_id`, `amount` (centimes), `memo`, `cleared` (enum: uncleared/cleared/reconciled), `is_virtual`, `virtual_linked_id` (FK nullable → Transaction), `import_hash` (unique nullable), `created_at`
- [x] `SplitTransaction` — `id`, `parent_id` (FK → Transaction), `category_id`, `amount`, `memo`
- [x] `BudgetAllocation` — `id`, `category_id`, `month` (YYYY-MM), `budgeted` (centimes). Unique constraint on `(category_id, month)`
- [x] `CategoryRule` — `id`, `user_id`, `pattern`, `match_field` (payee/memo), `match_type` (contains/exact/regex), `category_id`, `priority`

### 1.2 — Pydantic schemas

- [x] Request/response schemas for each model
- [x] Validation rules (amount > 0 for budgets, date formats, etc.)

### 1.3 — Alembic setup

- [x] `alembic init` with async config
- [x] Generate initial migration from models
- [x] Auto-run migrations on app startup (dev mode)

---

## Phase 2 — Auth & Base API

### 2.1 — Authentication

- [x] `POST /api/auth/register` — first user only (or open registration, TBD)
- [x] `POST /api/auth/login` — returns JWT access token
- [x] JWT verification middleware / dependency `get_current_user`
- [x] Password hashing with bcrypt

### 2.2 — CRUD API endpoints

- [x] `GET/POST /api/accounts`, `GET/PUT/DELETE /api/accounts/{id}`
- [x] `GET/POST /api/category-groups` (with nested categories)
- [x] `GET/POST /api/categories`, `PUT/DELETE /api/categories/{id}`
- [x] `GET/POST /api/payees`
- [x] `GET/POST /api/transactions` (with filters: account, category, dates, virtual)
- [x] `PUT/DELETE /api/transactions/{id}`
- [x] `GET/PUT /api/budget/{month}` — monthly envelope view

---

## Phase 3 — Bank Transaction Import

### 3.1 — Parsers

Each parser implements `BaseImporter` with `parse(file) → list[ImportedTransaction]`.

- [x] `ImportedTransaction` Pydantic schema: `date`, `amount`, `description`, `payee_name`, `reference`, `import_hash`
- [x] `BaseImporter` — abstract interface in `budgie/importers/base.py`
- [x] `CsvImporter` — configurable column mapping, encoding detection, French decimal support
- [x] `ExcelImporter` — via `pandas.read_excel()` + `openpyxl`; supports `header=None` for positional indexing
- [x] `QifImporter` — via `quiffen`
- [x] `OfxImporter` — via `ofxtools`, uses FITID as `import_hash`; ElementTree-based parsing (no strict schema)

### 3.2 — Import workflow

- [x] `POST /api/imports/parse` — upload file + format → returns parsed transactions (preview)
- [x] `POST /api/imports/confirm` — receives validated transactions (with assigned categories) → inserts into DB
- [x] Deduplication by `import_hash` — warns if transactions already exist

---

## Phase 4 — Categorization

### 4.1 — Categorization engine

- [x] Step 1: Exact payee match (case-insensitive) → `Payee.auto_category_id`
- [x] Step 2: Evaluate `CategoryRule` rows ordered by priority DESC (`contains` / `exact` / `regex` on `payee` or `memo` field)
- [x] Returns `category_id` + `confidence` (`"auto"` / `"rule"` / `"none"`)
- [x] `POST /api/categorize` — batch categorization endpoint
- [x] `GET/POST/PUT/DELETE /api/category-rules` — CategoryRule CRUD

### 4.2 — Passive learning

- [ ] On manual categorization, propose updating `Payee.auto_category_id`
- [ ] Propose creating a `CategoryRule` from repeated manual assignments
- [ ] Track categorization accuracy metrics (optional)

---

## Phase 5 — Budget Engine

### 5.1 — Envelope calculations

- [x] `get_month_budget_view(month)` — for each category:
  - `budgeted`: amount from `BudgetAllocation` for this month
  - `activity`: sum of transactions (incl. virtual) for this month in this category
  - `available`: cumulative sum (`Σ budgeted − Σ spending` over all months ≤ current)
- [x] `get_to_be_budgeted(month)` — income received − total budgeted. Goal = 0
- [x] Virtual transactions (`is_virtual=True`) reduce envelope `available` but NOT real account balance

### 5.2 — API endpoint

- [x] `GET /api/budget/{month}` — returns full month view with all envelopes + `to_be_budgeted`

---

## Phase 6 — Frontend

### 6.1 — Core setup

- [x] API client module (`src/api/client.ts`) — axios instance with JWT interceptor
- [x] Auth store (Pinia) + login page (`LoginView.vue`)
- [x] App layout: sidebar/navbar, responsive menu (DaisyUI drawer)
- [x] Vue Router with auth guard

### 6.2 — Main views

- [x] **Dashboard** (`DashboardView.vue`) — month summary, account balances, alerts (negative envelopes), recent transactions
- [x] **Transactions** (`TransactionsView.vue`) — paginated table, filters (account, category, date range, virtual/real), inline category editing
- [x] **Budget** (`BudgetView.vue`) — monthly grid, editable `budgeted` amounts, `activity`/`available` display with color coding, month navigation, "to be budgeted" bar
- [x] **Import** (`ImportView.vue`) — file upload (drag & drop), format selection, parsed transaction preview, auto-filled category suggestions, confirm/skip per row, duplicate indicator
- [x] **Settings** (`SettingsView.vue`) — accounts CRUD, category groups/categories CRUD, categorization rules CRUD, password change

### 6.3 — Reusable components

- [x] `EnvelopeCard.vue` — single envelope display with budget/activity/available
- [x] `TransactionRow.vue` — single transaction with inline edit
- [x] `CategoryPicker.vue` — dropdown with grouped categories
- [x] `FileUploader.vue` — drag & drop file upload
- [x] `MonthPicker.vue` — month navigation (prev/next/current)

---

## Phase 7 — Virtual Transactions

- [x] Creation form: toggle "virtual" on transaction form, fields: amount, estimated date, category, description
- [x] Linking: on import, suggest matching with existing virtual transactions (similar amount + payee + date range). Linked virtual → marked `realized`, real transaction gets `virtual_linked_id`
- [x] Display: virtual transactions shown with distinct style (dashed border, forecast icon). Count toward envelope `available` but not real account balance

---

## Phase 8 — Polish & Deployment

- [x] Dark/light theme support (DaisyUI themes)
- [x] PWA manifest for mobile "install" capability
- [x] Error handling: global error toasts, API error interceptor
- [x] Loading states: skeleton loaders for data fetching
- [x] Docker build & test on local machine
- [x] Backup strategy for SQLite DB file (`scripts/backup.sh`)
- [x] Deploy to Synology NAS via Docker Compose
- [x] Synology reverse proxy configuration (HTTPS)

---

## Phase 9 — Security & Encryption

### Overview

All user data is encrypted at rest using **AES-256-GCM** with a key derived from the user's passphrase via **Argon2id**. The encryption key is **never stored on the server** — it exists only in server RAM for the duration of the authenticated session. Daily login uses **WebAuthn (Passkeys)** for biometric convenience, with a **PIN fallback** for devices without biometric support.

**Approach**: Server-side decryption — the derived key is sent to the server over HTTPS, held in memory during the session, and purged on logout or token expiry.

### 9.1 — Encryption key derivation

- [ ] User chooses a **passphrase** (distinct from login password) at account creation
- [ ] Derive a 256-bit encryption key using **Argon2id** (time_cost=3, memory_cost=65536, parallelism=4)
- [ ] Generate a **challenge blob**: encrypt a random 32-byte salt with AES-256-GCM using the derived key → store `(nonce, ciphertext, tag, salt)` on the server
- [ ] Key verification: decrypt the challenge blob — if GCM tag validates, the key is correct
- [ ] Store **Argon2 parameters** (salt, time_cost, memory_cost, parallelism) in the `users` table — never the key itself
- [ ] Add `encryption_salt`, `challenge_blob`, `argon2_params` columns to `User` model
- [ ] Alembic migration for new columns

### 9.2 — WebAuthn / Passkeys registration & login

- [ ] Backend: integrate `py_webauthn` library
- [ ] `POST /api/auth/webauthn/register/begin` — generate registration options (challenge, RP info)
- [ ] `POST /api/auth/webauthn/register/complete` — verify attestation, store credential in DB
- [ ] `POST /api/auth/webauthn/login/begin` — generate authentication options
- [ ] `POST /api/auth/webauthn/login/complete` — verify assertion, return JWT
- [ ] New model `WebAuthnCredential`: `id`, `user_id`, `credential_id`, `public_key`, `sign_count`, `transports`, `created_at`
- [ ] Frontend: `navigator.credentials.create()` / `navigator.credentials.get()` API
- [ ] Store encrypted encryption key in **IndexedDB** on the device, unlocked by successful Passkey auth
- [ ] Alembic migration for `webauthn_credentials` table

### 9.3 — PIN-based local key storage

- [ ] User sets a **4-6 digit PIN** on the device
- [ ] Derive a wrapping key from PIN using **PBKDF2** (100k iterations, device-specific salt)
- [ ] Encrypt the encryption key with the wrapping key → store in **IndexedDB**
- [ ] On PIN entry: derive wrapping key, decrypt encryption key, send to server
- [ ] **5 failed PIN attempts** → purge local key storage (user must re-enter passphrase)
- [ ] PIN is device-local only — never sent to or stored on the server

### 9.4 — Server-side encryption service

- [ ] `budgie/services/crypto.py` — `encrypt(plaintext, key)` / `decrypt(ciphertext, key)` using AES-256-GCM
- [ ] Each field encrypted with a unique **random nonce** (96-bit) — stored alongside ciphertext
- [ ] Encrypted fields stored as `base64(nonce + ciphertext + tag)` in the database
- [ ] Key held in server RAM only — associated with session/JWT, **never written to disk or logs**
- [ ] Key purged on: logout, token expiry, server restart
- [ ] In-memory key store: `dict[user_id, bytes]` with TTL matching JWT expiry

### 9.5 — Data encryption

All user-owned data fields are encrypted. This includes amounts (integer centimes), names, memos, dates — everything except structural IDs and foreign keys.

- [ ] Encrypt/decrypt happens in the **service layer** (transparent to API routes)
- [ ] Encrypted models: `Account`, `Transaction`, `Category`, `CategoryGroup`, `Payee`, `CategoryRule`, `Envelope`, `BudgetAllocation`
- [ ] Encrypted fields per model:
  - `Account`: `name`, `type`
  - `Transaction`: `date`, `amount`, `memo`, `cleared`, `import_hash`
  - `Category`: `name`
  - `CategoryGroup`: `name`
  - `Payee`: `name`
  - `CategoryRule`: `pattern`
  - `Envelope`: `name`, `emoji`
  - `BudgetAllocation`: `budgeted`, `month`
- [ ] SQL aggregation (budget engine) operates on **decrypted data in RAM** — no SQL SUM on encrypted columns
- [ ] Alembic migration: alter encrypted columns from typed to `Text` (base64 blobs)

### 9.6 — Password reset & encryption key recovery

- [ ] **Password reset** (login password): standard flow — does NOT affect encryption key
- [ ] **Encryption key recovery**: user must provide the passphrase to re-derive the key
- [ ] If passphrase is lost → data is **irrecoverable** (by design)
- [ ] Challenge blob verification: attempt to decrypt with candidate key → GCM tag validates = correct key
- [ ] Admin cannot recover data — only the user's passphrase can derive the key

### 9.7 — PDF recovery document

- [ ] Generate a PDF at account creation containing:
  - User's **passphrase** (in clear text — printed once, never stored)
  - **QR code** encoding the passphrase for quick re-entry
  - First 8 characters of the derived key hash (for verification without revealing the key)
  - Instructions for recovery
- [ ] User is strongly advised to **print and store** this document in a safe place
- [ ] PDF generation: `reportlab` or `fpdf2` library
- [ ] `GET /api/auth/recovery-document` — download PDF (requires current passphrase confirmation)

### 9.8 — Migration of existing accounts

- [ ] Existing users (pre-encryption) have `is_encrypted = False`; data remains in plaintext
- [ ] Alembic migration: encrypted field columns changed to `Text` type
- [ ] Alembic migration adds `is_encrypted` column to `User` (default `False`)
- [ ] On next login: users with `is_encrypted = False` redirected to **"Set up your passphrase"** screen
- [ ] One-shot migration: server reads all plaintext data, encrypts every field in a **single SQLite transaction** (rollback on failure), sets `is_encrypted = True`
- [ ] Passkeys are **never required** — password + passphrase always works as fallback

### 9.9 — Dependencies

- [ ] Backend: add `py_webauthn`, `argon2-cffi`, `fpdf2` to `pyproject.toml`
- [ ] Frontend: no additional dependencies (WebAuthn and IndexedDB are browser-native)

---

## Testing Strategy

| What | How | Where |
|---|---|---|
| Importers (parsers) | Unit tests with fixture files | `tests/test_importers/` |
| Budget engine | Unit tests with known scenarios | `tests/test_services/` |
| Categorization engine | Unit tests with rules + payee data | `tests/test_services/` |
| API routes | Integration tests via `httpx.AsyncClient` | `tests/test_api/` |
| Vue components | Component tests via Vitest + Vue Test Utils | `frontend/src/**/*.spec.ts` |
| Pinia stores | Unit tests via Vitest | `frontend/src/**/*.spec.ts` |
| Full workflow | E2E: import → categorize → budget impact | `tests/test_services/` |
| Encryption service | Unit tests: encrypt/decrypt round-trip, wrong key rejection | `tests/test_services/` |
| WebAuthn flow | Integration tests with mocked credentials | `tests/test_api/` |
| Key derivation | Unit tests: Argon2 params, challenge blob | `tests/test_services/` |

---

## Status

- [x] Plan finalized
- [x] Stack decided
- [x] Copilot instructions written
- [x] Phase 0 — Foundations
- [x] Phase 1 — Data model
- [x] Phase 2 — Auth & API
- [x] Phase 3 — Import
- [x] Phase 4 — Categorization
- [x] Phase 5 — Budget engine
- [x] Phase 6 — Frontend
- [x] Phase 7 — Virtual transactions
- [x] Phase 8 — Polish & deployment
- [ ] Phase 9 — Security & Encryption
