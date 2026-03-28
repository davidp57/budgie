# Budgie 🐦 — Developer Guide

🌐 [Version française](../fr/developer-guide.md)

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Architecture Overview](#2-architecture-overview)
3. [Development Setup](#3-development-setup)
4. [Data Models](#4-data-models)
5. [Database Schema](#5-database-schema)
6. [API Reference](#6-api-reference)
7. [Import Pipeline](#7-import-pipeline)
8. [Categorization Engine](#8-categorization-engine)
9. [Budget Engine](#9-budget-engine)
10. [Virtual Transactions](#10-virtual-transactions)
11. [Frontend Components & Stores](#11-frontend-components--stores)
12. [Running Tests](#12-running-tests)
13. [Lint & Type Checking](#13-lint--type-checking)
14. [CI/CD](#14-cicd)
15. [Docker & Deployment](#15-docker--deployment)
16. [Configuration](#16-configuration)
17. [Conventions & Best Practices](#17-conventions--best-practices)
18. [Security & Encryption](#18-security--encryption)

---

## 1. Project Structure

```
budgie/
├── .github/
│   ├── copilot-instructions.md    # Copilot instructions
│   └── workflows/
│       ├── ci.yml                 # CI — lint, type check, tests
│       └── docker.yml             # CI/CD — Docker image build on GHCR
├── alembic/                       # Database migrations
│   └── versions/
├── budgie/                        # Backend Python package
│   ├── api/                       # FastAPI routers (thin — delegate to services)
│   │   ├── accounts.py
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categories.py
│   │   ├── categorize.py
│   │   ├── category_groups.py
│   │   ├── category_rules.py
│   │   ├── deps.py                # FastAPI dependencies (get_current_user, get_session)
│   │   ├── envelopes.py
│   │   ├── imports.py
│   │   ├── payees.py
│   │   ├── transactions.py
│   │   └── users.py
│   ├── importers/                 # Bank file parsers
│   │   ├── base.py                # ImportedTransaction + BaseImporter ABC
│   │   ├── csv_importer.py        # Auto-detect separator, decimal, columns
│   │   ├── excel_importer.py      # Via openpyxl
│   │   ├── qif_importer.py        # Via quiffen
│   │   └── ofx_importer.py        # ElementTree, FITID → import_hash
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── account.py
│   │   ├── budget.py
│   │   ├── category.py
│   │   ├── category_rule.py
│   │   ├── envelope.py
│   │   ├── payee.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── services/                  # All business logic
│   │   ├── account.py
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categorizer.py
│   │   ├── category.py
│   │   ├── category_rule.py
│   │   ├── envelope.py
│   │   ├── importer.py
│   │   ├── payee.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── config.py                  # Pydantic Settings
│   ├── database.py                # Async SQLAlchemy engine + session factory
│   └── main.py                    # FastAPI app, lifespan, SPA fallback
├── frontend/                      # Vue.js 3 SPA
│   ├── src/
│   │   ├── api/                   # Typed HTTP wrappers (axios)
│   │   │   ├── client.ts          # Axios instance, JWT interceptor, error toasts
│   │   │   ├── types.ts           # Shared TypeScript interfaces
│   │   │   ├── accounts.ts
│   │   │   ├── auth.ts
│   │   │   ├── budget.ts
│   │   │   ├── categories.ts
│   │   │   ├── envelopes.ts
│   │   │   ├── imports.ts
│   │   │   ├── transactions.ts
│   │   │   └── users.ts
│   │   ├── components/            # Reusable Vue components
│   │   │   ├── AppNav.vue         # Responsive nav (sidebar desktop, dock mobile)
│   │   │   ├── CategoryPicker.vue
│   │   │   ├── CreateCategoryModal.vue
│   │   │   ├── DrawerCard.vue
│   │   │   ├── EnvelopeCard.vue
│   │   │   ├── EnvelopeManager.vue
│   │   │   ├── FileUploader.vue
│   │   │   ├── MonthPicker.vue
│   │   │   ├── QuickExpense.vue   # Fast transaction entry (bottom sheet / modal)
│   │   │   ├── SkeletonRow.vue
│   │   │   ├── ToastContainer.vue
│   │   │   ├── DonutChart.vue     # Reusable doughnut chart (Chart.js)
│   │   │   └── TransactionRow.vue
│   │   ├── composables/
│   │   │   ├── useNearbyPlaces.ts
│   │   │   └── useTheme.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── budget.ts
│   │   │   ├── presets.ts
│   │   │   └── toast.ts
│   │   ├── views/
│   │   │   ├── BudgetView.vue
│   │   │   ├── DashboardView.vue
│   │   │   ├── DepensesView.vue   # Expenses list + dashboard (formerly TransactionsView)
│   │   │   ├── HomeView.vue
│   │   │   ├── ImportView.vue
│   │   │   ├── LoginView.vue
│   │   │   ├── SettingsView.vue
│   │   │   └── TransactionsView.vue # Bank transactions (imports)
│   │   └── router/
│   └── public/
│       └── manifest.json          # PWA manifest
├── tests/                         # Backend tests
│   ├── conftest.py
│   ├── test_api/
│   ├── test_importers/
│   ├── test_models/
│   ├── test_schemas/
│   └── test_services/
├── scripts/
│   └── backup.sh                  # SQLite backup script
├── docs/
│   ├── en/                        # English docs
│   └── fr/                        # French docs
├── Dockerfile                     # Multi-stage build
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
└── .env.example
```

---

## 2. Architecture Overview

### Backend Architecture

```
HTTP Request
    │
    ▼
api/           ← validates via Pydantic schemas, calls service, returns schema
    │
    ▼
services/      ← all business logic; no HTTP, no direct ORM in routes
    │
    ▼
models/        ← SQLAlchemy ORM models
database.py    ← AsyncSession factory (dependency injection via FastAPI Depends)
    │
    ▼
SQLite (data/budgie.db)
```

Routes must stay **thin**. All logic belongs in `services/`.

### Authentication Flow

1. `POST /api/auth/login` → `{ access_token, token_type }`
2. Frontend stores token in `localStorage`
3. Axios request interceptor: `Authorization: Bearer <token>` on every request
4. FastAPI dependency `get_current_user`: decodes JWT, loads user from DB
5. On 401: Axios response interceptor clears token, redirects to `/login`

### SPA Serving in Production

`budgie/main.py` mounts `frontend/dist/assets/` under `/assets` and registers a catch-all `GET /{full_path:path}` route returning `frontend/dist/index.html`. This is activated only when `frontend/dist/` exists (i.e. in the Docker build).

### Frontend Data Flow

```
View / Component
    │ imports
    ▼
src/api/*.ts       ← typed wrappers (axios calls)
    │
    ▼
FastAPI /api/*
```

The Axios response interceptor fires `useToastStore().error(message)` for all non-401 errors (except 422 and 409, handled locally by views).

---

## 3. Development Setup

### Prerequisites

- Python 3.12+ and [Poetry](https://python-poetry.org/)
- Node.js 22+ and npm

### Backend

```bash
poetry install
mkdir -p data/uploads
cp .env.example .env          # then set SECRET_KEY

# Dev server — Alembic migrations run automatically at startup
poetry run uvicorn budgie.main:app --reload
```

- API: `http://localhost:8000/api`
- OpenAPI docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite proxies all `/api/*` requests to `http://localhost:8000`.

---

## 4. Data Models

All models are SQLAlchemy classes in `budgie/models/`. Corresponding Pydantic schemas are in `budgie/schemas/`.

**Key invariant**: all monetary amounts are stored as **integer centimes** (e.g. `5050` = 50.50 €). Floats are never used for money.

### `User`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | Auto-incremented ID |
| `username` | `str` unique | Username |
| `hashed_password` | `str` | bcrypt password hash |
| `budget_mode` | `str` | Budget mode (`envelope`) |
| `created_at` | `datetime` | Creation date |

### `Account`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Account name (e.g. "Checking") |
| `type` | `str` | `checking`, `savings`, `credit`, `cash` |
| `on_budget` | `bool` | Included in budget |
| `created_at` | `datetime` | |

### `CategoryGroup`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Group name (e.g. "Housing") |
| `sort_order` | `int` | Display order |

### `Category`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `group_id` | `int` FK → CategoryGroup | |
| `name` | `str` | Category name (e.g. "Rent") |
| `sort_order` | `int` | Display order within group |
| `hidden` | `bool` | Hidden in UI |

### `Envelope`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Envelope name |
| `emoji` | `str` | Display emoji (e.g. `🍞`) |
| `rollover` | `bool` | Carry forward unspent balance |
| `sort_order` | `int` | Display order |
| `category_ids` | M2M relation | Assigned categories (via `envelope_categories` table) |

### `Payee`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Payee name |
| `auto_category_id` | `int` FK → Category (nullable) | Auto-assigned category |

### `Transaction`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `account_id` | `int` FK → Account | |
| `date` | `date` | Transaction date |
| `payee_id` | `int` FK → Payee (nullable) | |
| `category_id` | `int` FK → Category (nullable) | |
| `amount` | `int` | Amount in **centimes** (negative = expense) |
| `memo` | `str` | Description |
| `cleared` | `str` | `uncleared`, `cleared`, `reconciled` |
| `is_virtual` | `bool` | `True` for forecasts |
| `virtual_linked_id` | `int` FK → Transaction (nullable) | Forecast ↔ realization link |
| `envelope_id` | `int` FK → Envelope (nullable) | Direct envelope link (bypasses category) |
| `reconciled_with_id` | `int` FK → Transaction (nullable) | Bank tx linked to this expense |
| `import_hash` | `str` unique (nullable) | SHA-256 fingerprint for deduplication |
| `created_at` | `datetime` | |

### `SplitTransaction`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `parent_id` | `int` FK → Transaction | Parent transaction |
| `category_id` | `int` FK → Category | |
| `amount` | `int` | Amount in centimes |
| `memo` | `str` | |

### `BudgetAllocation`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `envelope_id` | `int` FK → Envelope | |
| `month` | `str` | Format `YYYY-MM` |
| `budgeted` | `int` | Allocated amount in centimes |

Unique constraint on `(envelope_id, month)`.

### `CategoryRule`

| Field | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `pattern` | `str` | Search pattern |
| `match_field` | `str` | `payee` or `memo` |
| `match_type` | `str` | `contains`, `exact`, `regex` |
| `category_id` | `int` FK → Category | Category to assign |
| `priority` | `int` | Priority (evaluated descending) |

---

## 5. Database Schema

SQLite database with Alembic for migrations. WAL journal mode, foreign keys enabled.

### Migrations

Alembic migrations are in `alembic/versions/`. They run **automatically** at application startup (via the FastAPI lifespan).

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply manually
poetry run alembic upgrade head

# View history
poetry run alembic history
```

> ⚠️ Never modify the DB manually. Always use Alembic.

---

## 6. API Reference

All endpoints require `Authorization: Bearer <token>` except `/api/auth/*`.

Interactive documentation available at `http://localhost:8000/docs` (Swagger UI).

### Auth

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/auth/register` | `{username, password}` | `UserOut` |
| `POST` | `/api/auth/login` | `{username, password}` | `{access_token, token_type}` |

### Accounts

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/accounts` | List all for current user |
| `POST` | `/api/accounts` | Create |
| `PUT` | `/api/accounts/{id}` | Update |
| `DELETE` | `/api/accounts/{id}` | Delete |

### Transactions

| Method | Path | Query params |
|---|---|---|
| `GET` | `/api/transactions` | `account_id`, `is_virtual` (bool), `envelope_id` (int), `month` (YYYY-MM), `expenses_only` (bool) |
| `POST` | `/api/transactions` | — |
| `PUT` | `/api/transactions/{id}` | — |
| `DELETE` | `/api/transactions/{id}` | — |
| `GET` | `/api/transactions/virtual/unlinked` | Pending forecasts |
| `POST` | `/api/transactions/virtual/match` | `{transaction_id, virtual_id}` |

> **Route ordering**: `/virtual/unlinked` must be declared **before** `/{id}` in the router to avoid `virtual` being matched as an integer ID.

### Budget

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/budget/{month}` | `month` format: `YYYY-MM` |
| `PUT` | `/api/budget/{month}` | Upsert allocations |

### Import

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/imports/parse` | `multipart/form-data`; returns preview |
| `POST` | `/api/imports/confirm` | JSON body; persists transactions |

### Categorization

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/categorize` | Batch categorize |
| `GET` | `/api/category-rules` | List rules |
| `POST` | `/api/category-rules` | Create rule |
| `PUT` | `/api/category-rules/{id}` | Update |
| `DELETE` | `/api/category-rules/{id}` | Delete |

### Categories & Groups

| Method | Path |
|---|---|
| `GET/POST` | `/api/category-groups` |
| `PUT/DELETE` | `/api/category-groups/{id}` |
| `POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |

### Envelopes

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/envelopes` | List with assigned categories |
| `POST` | `/api/envelopes` | `{name, emoji?, rollover?, category_ids?}` |
| `PUT` | `/api/envelopes/{id}` | Update |
| `DELETE` | `/api/envelopes/{id}` | Delete (+ allocations) |

### Payees

| Method | Path |
|---|---|
| `GET/POST` | `/api/payees` |
| `PUT/DELETE` | `/api/payees/{id}` |

### Users

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/users/me` | Current user profile |
| `PUT` | `/api/users/me` | Update preferences |

### Health

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/health` | `{"status": "ok"}` — no auth required |

---

## 7. Import Pipeline

### Parsers (`budgie/importers/`)

| Format | Class | Details |
|---|---|---|
| CSV | `CsvImporter` | Auto-detects separator (`;`, `,`, `\t`), decimal (`.`, `,`), column names from candidate lists |
| Excel | `ExcelImporter` | Same detection as CSV, via `openpyxl` |
| QIF | `QifImporter` | Via `quiffen` library |
| OFX | `OfxImporter` | ElementTree parsing (no strict schema), FITID used as `import_hash` |

All parsers extend `BaseImporter` and produce `list[ImportedTransaction]`.

### Import Hash

```python
import_hash = sha256(f"{date}{amount_centimes}{description}{reference}".encode()).hexdigest()
```

For OFX: `import_hash = sha256(fitid.encode()).hexdigest()`

`UNIQUE` constraint on `import_hash` → idempotent imports.

### Confirm Flow (`services/importer.py`)

1. For each `ImportedTransaction` in the payload:
   - Skip if `import_hash` already in DB
   - Insert `Transaction` row
   - If `virtual_linked_id` is set: mark the virtual transaction as `reconciled`
2. Single commit at the end

### Technical Note

When calling `POST /api/imports/parse`, Axios must not set `Content-Type: application/json` — the browser sets `multipart/form-data` with boundary automatically.

---

## 8. Categorization Engine

Entry point: `services/categorizer.py` → `categorize_transaction(session, user_id, txn)`

### Step 1 — Payee Match

```python
payee = await session.execute(
    select(Payee).where(
        Payee.user_id == user_id,
        func.lower(Payee.name) == func.lower(txn.payee),
    )
)
if payee and payee.auto_category_id:
    return payee.auto_category_id, "auto"
```

### Step 2 — Rule Match

Rules evaluated by `priority DESC`:

| `match_field` | `match_type` | Logic |
|---|---|---|
| `payee` / `memo` | `contains` | `pattern.lower() in field.lower()` |
| `payee` / `memo` | `exact` | `field.lower() == pattern.lower()` |
| `payee` / `memo` | `regex` | `re.search(pattern, field, re.IGNORECASE)` |

Returns `(category_id, "rule")` on first match, or `(None, "none")`.

After manual categorization, the payee is updated with `auto_category_id` for future fast lookups.

---

## 9. Budget Engine

Entry point: `services/budget.py` → `get_budget_month(session, user_id, month)`

### Per-Envelope Calculation

```
For each envelope:
  budgeted  = BudgetAllocation.budgeted WHERE envelope_id = X AND month = target_month
              (0 if no allocation)
  activity  = SUM(Transaction.amount) WHERE category_id IN envelope.category_ids
              AND month(date) = target_month           ← includes is_virtual=True

  IF envelope.rollover:
    available = SUM(budgeted_m - activity_m) over all months m ≤ target_month
  ELSE:
    available = budgeted + activity  (current month only)
```

### Top-Level Calculation

```
income          = SUM(amount) WHERE amount > 0 AND month = target_month
total_budgeted  = SUM(BudgetAllocation.budgeted) WHERE month = target_month
to_be_budgeted  = income - total_budgeted
```

**Key invariant**: `is_virtual=True` transactions affect `activity` (and `available`) but are excluded from real account balance calculations.

---

## 10. Virtual Transactions

### Model

Columns on `Transaction`:
- `is_virtual: bool` — `True` for forecasts
- `virtual_linked_id: int | None` — FK to the realized forecast
- `cleared: str | None` — `"reconciled"` when the forecast is linked

### Services (`services/transaction.py`)

```python
async def get_virtual_unlinked(session, user_id) -> list[Transaction]:
    """Returns virtual transactions not yet reconciled."""

async def link_virtual(session, transaction_id, virtual_id, user_id):
    """Links real txn to virtual; marks virtual as reconciled."""
```

### Frontend Matching Algorithm (`ImportView.vue`)

```
amount_match = abs(imported.amount - virtual.amount) / abs(virtual.amount) <= 0.10
date_match   = abs((imported.date - virtual.date).days) <= 60
suggestion   = amount_match AND date_match
```

---

## 11. Frontend Components & Stores

### Components

| Component | Description |
|---|---|
| `AppNav` | Responsive navigation (desktop sidebar + mobile dock) |
| `QuickExpense` | Fast transaction entry (bottom sheet on mobile, modal on desktop) |
| `DrawerCard` | Card with color palette, swipe support |
| `EnvelopeCard` | Budget cell: name, emoji, category chips, rollover badge, inline editing |
| `EnvelopeManager` | Settings panel — full CRUD for envelopes |
| `TransactionRow` | Self-contained `<tr>` with inline category editing |
| `CategoryPicker` | Searchable combobox with inline category creation |
| `CreateCategoryModal` | Category creation modal |
| `FileUploader` | Drag-and-drop + click |
| `MonthPicker` | Month navigation (YYYY-MM) |
| `SkeletonRow` | Loading placeholder |
| `ToastContainer` | Toast notifications (bottom-right, auto-dismiss 4 s) |

### Pinia Stores

**`auth.ts`** — JWT token, login/logout, `isAuthenticated`

**`toast.ts`** — Notification queue (success/error/warning/info), auto-dismiss

**`budget.ts`** — Budget month data (envelopes, allocations, activity)

**`presets.ts`** — QuickExpense presets (memo, amount, category, account)

### Composables

**`useTheme.ts`** — Singleton `ref<'emerald'|'night'>`. Reads `localStorage`, falls back to `prefers-color-scheme`. `toggleTheme()` toggles and persists.

**`useNearbyPlaces.ts`** — Queries the Overpass API (OpenStreetMap) with GPS position to suggest nearby shops with emojis.

### Axios Client (`src/api/client.ts`)

- **Request interceptor**: attaches `Authorization: Bearer <token>`
- **Response interceptor**: 401 → clear token + redirect `/login`; other errors → error toast (except 422/409)

---

## 12. Running Tests

### Backend (pytest)

```bash
# All tests (~200 tests)
poetry run pytest

# With coverage
poetry run pytest --cov=budgie

# Stop on first failure
poetry run pytest -x

# By layer
poetry run pytest tests/test_api/           # API routes
poetry run pytest tests/test_services/      # Services
poetry run pytest tests/test_importers/     # Parsers
poetry run pytest tests/test_models/        # Models
poetry run pytest tests/test_schemas/       # Pydantic schemas
```

**`tests/conftest.py`** provides:
- `engine`: in-memory `aiosqlite` DB, schema created fresh per test
- `session`: `AsyncSession` scoped per test
- `client`: `httpx.AsyncClient` against the FastAPI app
- `auth_client`: pre-registered user with `Authorization` header set

Test files mirror the source structure: `budgie/services/budget.py` → `tests/test_services/test_budget.py`.

### Frontend (Vitest)

```bash
cd frontend
npm run test:unit -- --run    # single pass (CI)
npm run test:unit             # watch mode
```

Tests in `src/components/__tests__/*.spec.ts` using Vue Test Utils.

| Test File | Tests | Coverage |
|---|---|---|
| `EnvelopeCard.spec.ts` | 7 | Rendering, rollover badge, available color, inline budget edit |
| `EnvelopeManager.spec.ts` | 11 | List, empty state, create, edit, cancel, delete |
| `MonthPicker.spec.ts` | 5 | Navigation, year wrap-around |
| `TransactionRow.spec.ts` | 12 | Rendering, amount color, category name, edit flow, emits |
| `DrawerCard.spec.ts` | — | Colors, swipe, content |
| `auth.test.ts` | 4 | Auth store, login, logout |

---

## 13. Lint & Type Checking

### Python

```bash
# Lint (zero warnings)
poetry run ruff check budgie/ tests/

# Auto-fix
poetry run ruff check budgie/ tests/ --fix

# Format
poetry run ruff format budgie/ tests/

# Type check (strict, zero errors)
poetry run mypy budgie/
```

Configuration in `pyproject.toml` under `[tool.ruff]` and `[tool.mypy]`.

### TypeScript / Vue

```bash
cd frontend

# Strict type check (Vue + TS)
npx vue-tsc --noEmit

# ESLint
npm run lint

# Prettier formatting
npx prettier --write src/
```

Rules:
- `<script setup lang="ts">` on every component
- All API calls in `src/api/` — never inline in components
- Prefer DaisyUI component classes over custom CSS
- No `any` types

---

## 14. CI/CD

### `ci.yml` — Quality Checks

Located in `.github/workflows/ci.yml`.

| Property | Value |
|---|---|
| Trigger | Push to `main` / `develop` + Pull requests |

**Backend job:** ruff lint, ruff format check, mypy, pytest.

**Frontend job:** vue-tsc, ESLint, Vitest.

### `docker.yml` — Docker Build & Publish

Located in `.github/workflows/docker.yml`.

| Property | Value |
|---|---|
| Trigger | Push to `main` / `develop` + workflow_dispatch (manual) |
| Registry | GitHub Container Registry (GHCR) |
| Image | `ghcr.io/davidp57/budgie` |

**Steps:**

1. Code checkout
2. GHCR login via `docker/login-action@v3`
3. Metadata extraction (tags: branch, semver, `latest`) via `docker/metadata-action@v5`
4. Build & push via `docker/build-push-action@v6`
5. Smoke test: starts the container and verifies `curl /api/health`

### Triggering a Build

```bash
# Push to main or develop → automatic build
git push origin main

# Or manually: Actions → docker → Run workflow
```

---

## 15. Docker & Deployment

### Multi-stage Dockerfile

**Stage 1** (`node:22-alpine`):
- Copies `frontend/`, `npm ci`, `npm run build`
- Produces static files in `frontend/dist/`

**Stage 2** (`python:3.12-slim`):
- Installs `gosu` (PUID/PGID privilege drop)
- Installs Poetry + Python dependencies (production only)
- Copies backend, Alembic, compiled frontend
- Creates non-root `budgie` user
- Health check on `/api/health`

### docker-compose.yml

```yaml
services:
  budgie:
    build: .
    container_name: budgie
    restart: unless-stopped
    ports:
      - "${BUDGIE_PORT:-8080}:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/budgie.db
      - UPLOAD_DIR=/app/data/uploads
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
    mem_limit: 256m
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

The container exposes port **8000** internally; `docker-compose.yml` maps it to **8080** by default.

### Synology Deployment

See the [User Guide — Docker Deployment section](user-guide.md#14-docker-deployment) for full instructions (SSH, Portainer, HTTPS reverse proxy).

---

## 16. Configuration

All settings loaded by `budgie/config.py` (Pydantic `BaseSettings`) from environment or `.env`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///data/budgie.db` | SQLAlchemy async DB URL |
| `SECRET_KEY` | `change-me-in-production` | JWT HMAC signing key — **must change** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime (24 h) |
| `UPLOAD_DIR` | `data/uploads` | Temp directory for uploaded files |
| `HOST` | `0.0.0.0` | Uvicorn bind host |
| `PORT` | `8000` | Uvicorn bind port |
| `DEBUG` | `false` | FastAPI debug mode |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins |
| `WEBAUTHN_RP_ID` | `localhost` | WebAuthn Relying Party ID — must match the serving domain exactly (no scheme, no port) |
| `WEBAUTHN_RP_NAME` | `Budgie` | Human-readable app name displayed in passkey prompts |
| `WEBAUTHN_ORIGIN` | `https://localhost:5173` | Full frontend origin URL (scheme + host + optional port) |

---

## 17. Conventions & Best Practices

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Python files | snake_case | `budget_engine.py` |
| Python classes | PascalCase | `BudgetAllocation` |
| Python functions | snake_case | `get_month_budget()` |
| Python constants | UPPER_SNAKE_CASE | `MAX_IMPORT_SIZE` |
| Vue components | PascalCase | `EnvelopeCard.vue` |
| Vue composables | camelCase, `use` prefix | `useTheme.ts` |
| TypeScript files | camelCase | `apiClient.ts` |
| API endpoints | kebab-case | `/api/category-groups` |
| DB tables | snake_case plural | `budget_allocations` |
| DB columns | snake_case | `auto_category_id` |
| Test files | `test_` prefix | `test_budget_engine.py` |

### Development Principles

- **TDD** — Red → Green → Refactor. Always write the test before the implementation.
- **Code language** — Everything in English (variables, functions, classes, comments, docstrings).
- **Type hints** — Complete annotations on all Python functions. Strict mypy.
- **Docstrings** — Google-style for all public functions.
- **No magic numbers** — Use constants or enums.
- **Amounts in centimes** — Never use floats for money.
- **Thin routes** — Delegate all logic to services.
- **Bilingual documentation** — EN + FR for all documentation files.

---

## 18. Security & Encryption

### Design Principles

- **All user data encrypted at rest** — names, amounts, dates, memos, everything except structural IDs and foreign keys.
- **Encryption key never stored on server** — exists only in server RAM during an authenticated session.
- **Server-side decryption (Approach B)** — the derived key is sent over HTTPS, held in memory, and purged on logout/token expiry.
- **User-owned security** — only the user's passphrase can derive the encryption key. Admins cannot recover data.

### Cryptographic Stack

| Component | Technology | Details |
|---|---|---|
| Symmetric encryption | **AES-256-GCM** | Authenticated encryption with random 96-bit nonce per field |
| Key derivation | **Argon2id** | time_cost=3, memory_cost=64 MiB, parallelism=4, 256-bit output |
| Key verification | **Challenge blob** | AES-GCM encryption of random 32-byte salt; GCM tag validates the key |
| Authentication | **WebAuthn (Passkeys)** | `py_webauthn` backend, `navigator.credentials` browser API |
| PIN fallback | **PBKDF2-HMAC-SHA256** | 100k iterations, device-specific salt, wraps encryption key in `localStorage` (requires HTTPS) |
| PDF recovery | **fpdf2** | One-time PDF with passphrase + QR code |

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        CLIENT                              │
│                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │   Passkey     │   │   PIN + LS   │   │  Passphrase   │  │
│  │  (biometric)  │   │  (fallback)  │   │  (initial /   │  │
│  │              │   │              │   │   recovery)   │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬────────┘  │
│         │                  │                   │           │
│         ▼                  ▼                   ▼           │
│     Unlock local       Decrypt local      Argon2id        │
│     encrypted key      encrypted key      derive key      │
│         │                  │                   │           │
│         └──────────────────┴───────────────────┘           │
│                            │                               │
│                  encryption_key (bytes)                     │
│                            │                               │
│                     HTTPS POST /api/...                     │
│                    Authorization: Bearer                    │
│                    X-Encryption-Key: <key>                  │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│                        SERVER                              │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  In-memory key store: dict[user_id → (key, expiry)] │  │
│  │  TTL = JWT expiry (24h) — purged on logout/restart  │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │  Service layer: encrypt() / decrypt()               │  │
│  │  AES-256-GCM per field, unique nonce                │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │  SQLite: all data stored as base64(nonce+ct+tag)    │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Data Model Changes

#### New columns on `User`

| Column | Type | Description |
|---|---|---|
| `encryption_salt` | `bytes` | Argon2 salt (16 bytes) |
| `challenge_blob` | `str` | base64(nonce + ciphertext + tag) — used for key verification |
| `argon2_params` | `str` | JSON: `{time_cost, memory_cost, parallelism}` |
| `is_encrypted` | `bool` | Whether data has been migrated to encrypted format |

#### New table `webauthn_credentials`

| Column | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `credential_id` | `bytes` | WebAuthn credential ID |
| `public_key` | `bytes` | COSE public key |
| `sign_count` | `int` | Signature counter |
| `transports` | `str` | JSON array of transports |
| `created_at` | `datetime` | |

### New Modules

| Module | Purpose |
|---|---|
| `budgie/services/crypto.py` | `encrypt(plaintext, key)` / `decrypt(ciphertext, key)` — AES-256-GCM |
| `budgie/api/webauthn.py` | WebAuthn registration & login endpoints |
| `budgie/models/webauthn.py` | `WebAuthnCredential` ORM model |
| `budgie/schemas/webauthn.py` | WebAuthn Pydantic schemas |
| `frontend/src/composables/usePinStorage.ts` | PIN-based key wrapping, localStorage key storage |
| `frontend/src/composables/useWebAuthn.ts` | `navigator.credentials` wrapper |

### Encryption Flow

1. **Registration**: user sets username + password + passphrase → Argon2id derives encryption key → challenge blob created → PDF recovery document generated.
2. **Daily login (Passkey)**: biometric authentication → obtains JWT → encryption key then unlocked via PIN or passphrase on the unlock screen.
3. **Daily login (PIN)**: PIN entered → PBKDF2 derives wrapping key → decrypts encryption key from `localStorage` → key sent to server.
4. **Fallback login (passphrase)**: user enters passphrase → Argon2id re-derives key → key sent to server.
5. **Data access**: service layer decrypts data in RAM using the session key → serves plaintext via API → client renders normally.
6. **Data write**: service layer encrypts each field with unique nonce → stores base64 blob in SQLite.
7. **Logout / token expiry**: key purged from in-memory store.

### Migration of Existing Accounts

Existing accounts created before Phase 9 have their data stored in plaintext (`is_encrypted = False`). Migration is transparent and progressive:

#### Alembic migration
- New `Text` columns replace typed columns for encrypted fields (compatible with both plaintext and base64 blobs).
- `is_encrypted` flag added to `User` (default `False`).

#### On next login
Users with `is_encrypted = False` are redirected to a one-time **"Set up your passphrase"** screen:
1. User chooses their passphrase.
2. Argon2id derives the encryption key.
3. Challenge blob is created and stored.
4. Recovery PDF is generated and downloaded.
5. (Optional) Passkey registration offered immediately.

#### One-shot data migration
Once the passphrase is validated, the server:
1. Reads all user data (plaintext, already in RAM).
2. Encrypts every field with the new key.
3. Writes everything in a **single SQLite transaction** — rollback on any error.
4. Sets `is_encrypted = True`.

#### Transition code
During the progressive rollout, the service layer must handle both states:

```python
# In service functions, after loading a record:
if user.is_encrypted:
    name = crypto.decrypt(account.name, session_key)
else:
    name = account.name  # plaintext fallback
```

This `if user.is_encrypted` guard can be removed once all users have migrated.

#### Passkeys are optional
Passkeys are never required. A migrated user can always authenticate with password + passphrase. Passkeys and PIN are convenience layers only.

### Security Mitigations

| Threat | Mitigation |
|---|---|
| Key interception in transit | HTTPS mandatory (TLS 1.2+) |
| Key on disk | Never written to disk — RAM only, purged on logout/restart |
| Brute-force PIN | 5 failed attempts → local key purge |
| Server memory dump | Key held only during active session; `mlock` recommended for production |
| Database theft | All data is AES-256-GCM encrypted — useless without key |
| Lost passphrase | Data irrecoverable by design — PDF recovery document mitigates |
| Replay attacks | AES-GCM unique nonce per encryption — no nonce reuse |
