# Budgie 🐦 — Project Plan

# Plan du projet Budgie 🐦

---

## Overview / Vue d'ensemble

Personal household budget management web app.
Import bank transactions, auto-categorize, manage envelope budgets, plan future purchases with virtual transactions.

Application web de gestion de budget personnel pour un ménage.
Import de transactions bancaires, catégorisation automatique, gestion d'enveloppes budgétaires, prévision d'achats futurs via transactions virtuelles.

---

## Final Stack / Stack finale

| Layer / Couche | Choice / Choix                              |
|---------------|----------------------------------------------|
| Name          | **Budgie** 🐦                                |
| Backend       | Python 3.12+, FastAPI, Poetry                |
| ORM           | SQLAlchemy 2.0 (async) + Alembic             |
| Database      | SQLite (amounts in integer centimes)         |
| Frontend      | Vue.js 3, Composition API, TypeScript, Vite  |
| CSS           | DaisyUI (Tailwind CSS)                       |
| Auth          | JWT + bcrypt                                 |
| Import        | CSV, Excel, QIF, OFX                         |
| Categorization| Rules + payee history (MVP)                  |
| Deployment    | Docker Compose on Synology NAS               |
| Testing       | pytest + pytest-asyncio, Vitest              |
| Linting       | ruff, mypy, ESLint, Prettier                 |

---

## Phase 0 — Foundations / Fondations

### 0.1 — Poetry project init / Initialisation du projet Poetry

- [x] Initialize Poetry project in workspace root
- [x] `pyproject.toml` with metadata, Python >=3.12
- [x] Runtime dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `pydantic-settings`, `python-multipart`, `bcrypt`, `python-jose[cryptography]`
- [x] Import dependencies: `pandas`, `openpyxl`, `quiffen`, `ofxtools`
- [x] Dev dependencies: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pytest-cov`

### 0.2 — Backend project structure / Structure du projet backend

- [x] Create `budgie/` package with `__init__.py`
- [x] Create subpackages: `models/`, `schemas/`, `api/`, `services/`, `importers/`
- [x] Create `budgie/config.py` — Pydantic `BaseSettings` loading from `.env`
- [x] Create `budgie/database.py` — async SQLAlchemy engine + session factory
- [x] Create `budgie/main.py` — FastAPI app with CORS, router mounting, health check
- [x] Create `.env.example` with all config variables
- [x] Create `tests/conftest.py` with async test fixtures (test DB, test client)

### 0.3 — Frontend project init / Initialisation du projet frontend

- [x] Initialize Vue.js 3 project in `frontend/` via `create-vue` (Vite + TS + Router + Pinia)
- [x] Install DaisyUI + Tailwind CSS
- [x] Install axios
- [x] Configure Vite proxy to forward `/api` to FastAPI dev server
- [x] Configure ESLint + Prettier

### 0.4 — Tooling & CI / Outillage

- [x] Configure `ruff` in `pyproject.toml` (linting + formatting rules)
- [x] Configure `mypy` in `pyproject.toml` (strict mode)
- [x] VS Code workspace settings: ruff, mypy, Pylance, ESLint integration
- [x] Create `.gitignore` (Python, Node, data/, .env, __pycache__, etc.)

### 0.5 — Docker / Conteneurisation

- [x] `Dockerfile` — multi-stage: (1) Node build of Vue → static files, (2) Python slim runtime
- [x] `docker-compose.yml` — single service, volume for `data/`, port 8080, health check, `mem_limit: 256m`, `restart: unless-stopped`

---

## Phase 1 — Data Model / Modèle de données

### 1.1 — SQLAlchemy models / Modèles SQLAlchemy

All amounts stored as **integer centimes** (e.g., `1050` = 10.50€).
Tous les montants en **centimes entiers** (ex: `1050` = 10,50€).

- [x] `User` — `id`, `username` (unique), `hashed_password`, `created_at`
- [x] `Account` — `id`, `user_id`, `name`, `type` (checking/savings/credit/cash), `on_budget`, `created_at`
- [x] `CategoryGroup` — `id`, `user_id`, `name`, `sort_order`
- [x] `Category` — `id`, `group_id`, `name`, `sort_order`, `hidden`
- [x] `Payee` — `id`, `user_id`, `name`, `auto_category_id` (FK nullable → Category)
- [x] `Transaction` — `id`, `account_id`, `date`, `payee_id`, `category_id`, `amount` (centimes), `memo`, `cleared` (enum: uncleared/cleared/reconciled), `is_virtual`, `virtual_linked_id` (FK nullable → Transaction), `import_hash` (unique nullable), `created_at`
- [x] `SplitTransaction` — `id`, `parent_id` (FK → Transaction), `category_id`, `amount`, `memo`
- [x] `BudgetAllocation` — `id`, `category_id`, `month` (YYYY-MM), `budgeted` (centimes). Unique constraint on `(category_id, month)`
- [x] `CategoryRule` — `id`, `user_id`, `pattern`, `match_field` (payee/memo), `match_type` (contains/exact/regex), `category_id`, `priority`

### 1.2 — Pydantic schemas / Schémas Pydantic

- [x] Request/response schemas for each model
- [x] Validation rules (amount > 0 for budgets, date formats, etc.)

### 1.3 — Alembic setup / Configuration Alembic

- [x] `alembic init` with async config
- [x] Generate initial migration from models
- [x] Auto-run migrations on app startup (dev mode)

---

## Phase 2 — Auth & Base API / Auth & API de base

### 2.1 — Authentication / Authentification

- [x] `POST /api/auth/register` — first user only (or open registration, TBD)
- [x] `POST /api/auth/login` — returns JWT access token
- [x] JWT verification middleware / dependency `get_current_user`
- [x] Password hashing with bcrypt

### 2.2 — CRUD API endpoints / Endpoints CRUD

- [x] `GET/POST /api/accounts`, `GET/PUT/DELETE /api/accounts/{id}`
- [x] `GET/POST /api/category-groups` (with nested categories)
- [x] `GET/POST /api/categories`, `PUT/DELETE /api/categories/{id}`
- [x] `GET/POST /api/payees`
- [x] `GET/POST /api/transactions` (with filters: account, category, dates, virtual)
- [x] `PUT/DELETE /api/transactions/{id}`
- [x] `GET/PUT /api/budget/{month}` — monthly envelope view

---

## Phase 3 — Bank Transaction Import / Import de transactions bancaires

### 3.1 — Parsers / Analyseurs de fichiers

Each parser implements `BaseImporter` with `parse(file) → list[ImportedTransaction]`.
Chaque parser implémente `BaseImporter` avec `parse(file) → list[ImportedTransaction]`.

- [x] `ImportedTransaction` Pydantic schema: `date`, `amount`, `description`, `payee_name`, `reference`, `import_hash`
- [x] `BaseImporter` — abstract interface in `budgie/importers/base.py`
- [x] `CsvImporter` — configurable column mapping, encoding detection, French decimal support
- [x] `ExcelImporter` — via `pandas.read_excel()` + `openpyxl`; supports header=None for positional indexing
- [x] `QifImporter` — via `quiffen`
- [x] `OfxImporter` — via `ofxtools`, uses FITID as `import_hash`; ElementTree-based parsing (no strict schema)

### 3.2 — Import workflow / Flux d'import

- [x] `POST /api/imports/parse` — upload file + format → returns parsed transactions (preview)
- [x] `POST /api/imports/confirm` — receives validated transactions (with assigned categories) → inserts into DB
- [x] Deduplication by `import_hash` — warns if transactions already exist

---

## Phase 4 — Categorization / Catégorisation

### 4.1 — Categorization engine / Moteur de catégorisation

- [x] Step 1: Exact payee match (case-insensitive) → `Payee.auto_category_id`
- [x] Step 2: Evaluate `CategoryRule` rows ordered by priority DESC (`contains` / `exact` / `regex` on `payee` or `memo` field)
- [x] Returns `category_id` + `confidence` (`"auto"` / `"rule"` / `"none"`)
- [x] `POST /api/categorize` — batch categorization endpoint
- [x] `GET/POST/PUT/DELETE /api/category-rules` — CategoryRule CRUD (needed by tests and frontend settings)

### 4.2 — Passive learning / Apprentissage passif

- [ ] On manual categorization, propose updating `Payee.auto_category_id`
- [ ] Propose creating a `CategoryRule` from manual assignments
- [ ] Track categorization accuracy metrics (optional)

---

## Phase 5 — Budget Engine / Moteur de budget

### 5.1 — Envelope calculations / Calculs d'enveloppes

- [x] `get_month_budget_view(month)` — for each category:
  - `budgeted`: amount from `BudgetAllocation` for this month
  - `activity`: sum of transactions (incl. virtual) for this month in this category
  - `available`: cumulative sum (`Σ budgeted - Σ spending` over all months ≤ current)
- [x] `get_to_be_budgeted(month)` — income received − total budgeted. Goal = 0
- [x] Virtual transactions (`is_virtual=True`) reduce envelope `available` but NOT real account balance

### 5.2 — API endpoint

- [x] `GET /api/budget/{month}` — returns full month view with all envelopes + to_be_budgeted

---

## Phase 6 — Frontend / Interface utilisateur

### 6.1 — Core setup / Setup de base

- [x] API client module (`src/api/client.ts`) — axios instance with JWT interceptor
- [x] Auth store (Pinia) + login page (`LoginView.vue`)
- [x] App layout: sidebar/navbar, responsive menu (DaisyUI drawer)
- [x] Vue Router with auth guard

### 6.2 — Main views / Vues principales

- [x] **Dashboard** (`DashboardView.vue`) — month summary, account balances, alerts (negative envelopes), recent transactions
- [x] **Transactions** (`TransactionsView.vue`) — paginated table, filters (account, category, date range, virtual/real), inline category editing
- [x] **Budget** (`BudgetView.vue`) — monthly grid, editable `budgeted` amounts, `activity`/`available` display with color coding (green/orange/red), month navigation, "to be budgeted" bar
- [x] **Import** (`ImportView.vue`) — file upload (drag & drop), format selection, parsed transaction preview table, auto-filled category suggestions, confirm/skip per row, duplicate indicator
- [x] **Settings** (`SettingsView.vue`) — accounts CRUD, category groups/categories CRUD, categorization rules CRUD, password change

### 6.3 — Reusable components / Composants réutilisables

- [x] `EnvelopeCard.vue` — single envelope display with budget/activity/available
- [ ] `TransactionRow.vue` — single transaction with inline edit
- [x] `CategoryPicker.vue` — dropdown with grouped categories
- [x] `FileUploader.vue` — drag & drop file upload
- [x] `MonthPicker.vue` — month navigation (prev/next/current)

---

## Phase 7 — Virtual Transactions / Transactions virtuelles

- [ ] Creation form: toggle "virtual" on transaction form, fields: amount, estimated date, category, description
- [ ] Linking: on import, suggest matching with existing virtual transactions (similar amount + payee + date range). Linked virtual → marked `realized`, real transaction gets `virtual_linked_id`
- [ ] Display: virtual transactions shown with distinct style (dashed border, forecast icon) in transaction list. Count toward envelope `available` but not real account balance

---

## Phase 8 — Polish & Deployment / Finitions & Déploiement

- [ ] Dark/light theme support (DaisyUI themes)
- [ ] PWA manifest for mobile "install" capability
- [ ] Error handling: global error toasts, API error interceptor
- [ ] Loading states: skeleton loaders for data fetching
- [ ] Docker build & test on local machine
- [ ] Deploy to Synology NAS via Docker Compose
- [ ] Synology reverse proxy configuration (HTTPS)
- [ ] Backup strategy for SQLite DB file

---

## Testing Strategy / Stratégie de test

| What / Quoi                    | How / Comment                              | Where / Où                     |
|-------------------------------|--------------------------------------------|-------------------------------|
| Importers (parsers)           | Unit tests with fixture files              | `tests/test_importers/`       |
| Budget engine (calculations)  | Unit tests with known scenarios            | `tests/test_services/`        |
| Categorization engine         | Unit tests with rules + payee data         | `tests/test_services/`        |
| API routes                    | Integration tests via `httpx.AsyncClient`  | `tests/test_api/`             |
| Vue components                | Component tests via Vitest + Vue Test Utils| `frontend/src/**/*.test.ts`   |
| Pinia stores                  | Unit tests via Vitest                      | `frontend/src/**/*.test.ts`   |
| Full workflow                 | E2E: import → categorize → budget impact   | `tests/test_services/`        |

---

## Status / Statut

- [x] Plan finalized / Plan finalisé
- [x] Stack decided / Stack décidée
- [x] Copilot instructions written / Instructions Copilot rédigées
- [x] Phase 0 — Foundations / Fondations
- [x] Phase 1 — Data model / Modèle de données
- [x] Phase 2 — Auth & API
- [x] Phase 3 — Import
- [x] Phase 4 — Categorization / Catégorisation
- [x] Phase 5 — Budget engine / Moteur de budget
- [x] Phase 6 — Frontend
- [ ] Phase 7 — Virtual transactions / Transactions virtuelles
- [ ] Phase 8 — Polish & deployment / Finitions & déploiement
