# Budgie 🐦 — Technical Reference

## Table of Contents

1. [Project Structure](#project-structure)
2. [Tech Stack](#tech-stack)
3. [Development Setup](#development-setup)
4. [Architecture](#architecture)
5. [API Reference](#api-reference)
6. [Import Pipeline](#import-pipeline)
7. [Categorization Engine](#categorization-engine)
8. [Budget Engine](#budget-engine)
9. [Virtual Transactions](#virtual-transactions)
10. [Frontend Components & Stores](#frontend-components--stores)
11. [Testing](#testing)
12. [Code Quality](#code-quality)
13. [Docker & Deployment](#docker--deployment)
14. [Configuration](#configuration)

---

## Project Structure

```
budgetizer/
├── budgie/                      # Backend Python package
│   ├── api/                     # FastAPI routers (thin — delegate to services)
│   │   ├── accounts.py
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categories.py
│   │   ├── category_groups.py
│   │   ├── category_rules.py
│   │   ├── categorize.py
│   │   ├── imports.py
│   │   ├── payees.py
│   │   └── transactions.py
│   ├── importers/               # Bank file parsers
│   │   ├── base.py              # ImportedTransaction + BaseImporter ABC
│   │   ├── csv_importer.py      # Auto-detect separator, decimal, columns
│   │   ├── excel_importer.py
│   │   ├── qif_importer.py      # via quiffen
│   │   └── ofx_importer.py      # ElementTree-based, FITID → import_hash
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # All business logic
│   │   ├── budget.py
│   │   ├── categorizer.py
│   │   ├── importer.py
│   │   └── transaction.py
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # Async SQLAlchemy engine + session factory
│   └── main.py                  # FastAPI app, lifespan, SPA fallback
├── alembic/                     # Database migrations
│   └── versions/
├── frontend/                    # Vue.js 3 SPA
│   ├── src/
│   │   ├── api/                 # Typed HTTP wrappers (axios)
│   │   │   ├── client.ts        # Axios instance, JWT interceptor, error toasts
│   │   │   ├── types.ts         # Shared TypeScript interfaces
│   │   │   ├── accounts.ts
│   │   │   ├── categories.ts
│   │   │   ├── imports.ts
│   │   │   └── transactions.ts
│   │   ├── components/
│   │   │   ├── CategoryPicker.vue
│   │   │   ├── EnvelopeCard.vue
│   │   │   ├── FileUploader.vue
│   │   │   ├── MonthPicker.vue
│   │   │   ├── SkeletonRow.vue
│   │   │   ├── ToastContainer.vue
│   │   │   └── TransactionRow.vue
│   │   ├── composables/
│   │   │   └── useTheme.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   └── toast.ts
│   │   ├── views/
│   │   │   ├── BudgetView.vue
│   │   │   ├── DashboardView.vue
│   │   │   ├── ImportView.vue
│   │   │   ├── LoginView.vue
│   │   │   ├── SettingsView.vue
│   │   │   └── TransactionsView.vue
│   │   └── router/
│   └── public/
│       └── manifest.json
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_importers/
│   └── test_services/
├── docs/
│   ├── PLAN.md
│   ├── USER.md           # End-user guide (EN)
│   ├── UTILISATEUR.md    # End-user guide (FR)
│   ├── TECHNICAL.md      # This file
│   └── TECHNIQUE.md      # Technical reference (FR)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend language | Python 3.12+ | |
| Web framework | FastAPI | Async, OpenAPI auto-docs at `/docs` |
| ORM | SQLAlchemy 2.0 (async) | All queries via `AsyncSession` |
| Migrations | Alembic | Auto-run at startup via lifespan |
| Database | SQLite | `data/budgie.db`, amounts as integer centimes |
| Frontend framework | Vue.js 3 | Composition API, `<script setup lang="ts">` |
| Build tool | Vite 7 | Dev proxy `/api` → `:8000` |
| CSS | Tailwind CSS + DaisyUI 5 | Themes: `emerald` (light), `night` (dark) |
| State | Pinia | `auth` store + `toast` store |
| HTTP client | Axios | JWT + error-toast interceptors |
| Auth | JWT + bcrypt | 24 h token, `localStorage` |
| Containerization | Docker Compose | Multi-stage build, port 8080 |
| Backend tests | pytest + pytest-asyncio | 155 tests |
| Frontend tests | Vitest + Vue Test Utils | 18 component tests |
| Linting | ruff (Python), ESLint (TS) | Zero warnings policy |
| Type checking | mypy (Python), tsc (TS) | Strict, zero errors |
| Formatting | ruff format (Python), Prettier (TS) | |

**Key invariant**: all monetary amounts are stored and computed as **integer centimes** (e.g. `5050` = 50.50 €). Floats are never used for money.

---

## Development Setup

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

API: `http://localhost:8000/api`  
OpenAPI docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite proxies all `/api/*` requests to `http://localhost:8000`.

### Naming conventions

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

---

## Architecture

### Backend layering

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

Routes must stay thin. All logic belongs in `services/`.

### Authentication flow

1. `POST /api/auth/login` → `{ access_token, token_type }`
2. Frontend stores token in `localStorage`
3. Axios request interceptor: `Authorization: Bearer <token>` on every request
4. FastAPI dependency `get_current_user`: decodes JWT, loads user from DB
5. On 401: Axios response interceptor clears token, redirects to `/login`

### SPA serving in production

`budgie/main.py` mounts `frontend/dist/assets/` under `/assets` and registers a catch-all `GET /{full_path:path}` route returning `frontend/dist/index.html`. This is activated only when `frontend/dist/` exists (i.e. in a Docker build).

### Frontend data flow

```
View / Component
    │ imports
    ▼
src/api/*.ts       ← typed wrappers (axios calls)
    │
    ▼
FastAPI /api/*
```

Error handling: the Axios response interceptor fires a `useToastStore().error(message)` for all non-401 errors (except 422 and 409, handled locally by views).

---

## API Reference

All endpoints require `Authorization: Bearer <token>` except `/api/auth/*`.

### Auth

| Method | Path | Body / Params | Returns |
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
| `GET` | `/api/transactions` | `account_id`, `is_virtual` (bool) |
| `POST` | `/api/transactions` | — |
| `PUT` | `/api/transactions/{id}` | — |
| `DELETE` | `/api/transactions/{id}` | — |
| `GET` | `/api/transactions/virtual/unlinked` | Pending forecasts |
| `POST` | `/api/transactions/virtual/match` | `{transaction_id, virtual_id}` |

> **Route ordering**: `/virtual/unlinked` must be declared **before** `/{id}` in the router to avoid the literal string `virtual` being matched as an integer ID.

### Budget

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/budget/{month}` | `month` format: `YYYY-MM` |
| `PUT` | `/api/budget/{month}` | Upsert allocations |

### Import

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/imports/parse` | `multipart/form-data`; returns preview list |
| `POST` | `/api/imports/confirm` | JSON body; persists transactions |

### Categorization

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/categorize` | Batch categorize list of transactions |
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

---

## Import Pipeline

### Parsers (`budgie/importers/`)

| Format | Class | Details |
|---|---|---|
| CSV | `CsvImporter` | Auto-detects separator (`;`, `,`, `\t`), decimal (`.`, `,`), column names from candidate lists (`_DATE_CANDIDATES`, `_DESC_CANDIDATES`, etc.) |
| Excel | `ExcelImporter` | Same column detection as CSV, via `openpyxl` |
| QIF | `QifImporter` | Via `quiffen` library |
| OFX | `OfxImporter` | ElementTree parsing (no strict OFX schema), FITID used as `import_hash` |

All parsers extend `BaseImporter` and produce `list[ImportedTransaction]`.

### Import hash

```python
import_hash = sha256(f"{date}{amount_centimes}{description}{reference}".encode()).hexdigest()
```

For OFX: `import_hash = sha256(fitid.encode()).hexdigest()`

Stored on the `Transaction` model. `UNIQUE` constraint ensures idempotent imports.

### Confirm import (`services/importer.py`)

1. For each `ImportedTransaction` in the payload:
   - Skip if `import_hash` already in DB
   - Insert `Transaction` row
   - If `virtual_linked_id` is set: load the virtual transaction, set its `cleared = "reconciled"`
2. Commit once at the end.

### File upload note

When calling `POST /api/imports/parse` from the frontend, the Axios request must **not** set `Content-Type: application/json` — the browser sets `multipart/form-data` with boundary automatically. Override with `{ headers: { 'Content-Type': undefined } }`.

---

## Categorization Engine

Entry point: `services/categorizer.py` → `categorize_transaction(session, user_id, txn)`

### Step 1 — Payee match

```python
payee = await session.execute(
    select(Payee).where(Payee.user_id == user_id, func.lower(Payee.name) == func.lower(txn.payee))
)
if payee and payee.auto_category_id:
    return payee.auto_category_id, "auto"
```

### Step 2 — Rule match

Rules are evaluated ordered by `priority DESC`. For each rule:

| `match_field` | `match_type` | Logic |
|---|---|---|
| `payee` / `memo` | `contains` | `field.lower() in pattern.lower()` |
| `payee` / `memo` | `exact` | `field.lower() == pattern.lower()` |
| `payee` / `memo` | `regex` | `re.search(pattern, field, re.IGNORECASE)` |

Returns the first match's `category_id` and `confidence = "rule"`.

Returns `(None, "none")` if no match.

After categorization, the payee record is updated with `auto_category_id` for future fast lookups.

---

## Budget Engine

Entry point: `services/budget.py` → `get_budget_month(session, user_id, month)`

### Per-category calculation

```
budgeted  = BudgetAllocation.budgeted WHERE month = target_month  (0 if missing)
activity  = SUM(Transaction.amount) WHERE category_id = X
            AND month(date) = target_month
            AND user_id = current_user          ← includes is_virtual=True
available = SUM(budgeted - activity) over all months ≤ target_month
```

### Top-level calculation

```
income          = SUM(amount) WHERE amount > 0 AND month = target_month
total_budgeted  = SUM(BudgetAllocation.budgeted) WHERE month = target_month
to_be_budgeted  = income - total_budgeted
```

**Key invariant**: `is_virtual=True` transactions affect `activity` (and therefore `available`) but are excluded from real account balance calculations.

---

## Virtual Transactions

### DB model

`Transaction` table, columns:
- `is_virtual: bool` — `True` for forecasts
- `virtual_linked_id: int | None` — FK to the virtual transaction that a real transaction "realizes"
- `cleared: str | None` — set to `"reconciled"` when the virtual transaction is matched

### Service layer (`services/transaction.py`)

```python
async def get_virtual_unlinked(session, user_id) -> list[Transaction]:
    """Returns virtual transactions not yet reconciled."""

async def link_virtual(session, transaction_id, virtual_id, user_id):
    """Links real txn to virtual; marks virtual as reconciled."""
```

### Frontend matching algorithm (`ImportView.vue`)

For each imported (unconfirmed) transaction, score against each unlinked virtual transaction:

```
amount_match = abs(imported.amount - virtual.amount) / abs(virtual.amount) <= 0.10
date_match   = abs((imported.date - virtual.date).days) <= 60
suggestion   = amount_match AND date_match
```

If a match is accepted, `virtual_linked_id` is set on the `ImportedTransaction` before calling `POST /api/imports/confirm`.

---

## Frontend Components & Stores

### Components

| Component | Props | Emits | Notes |
|---|---|---|---|
| `TransactionRow` | `txn: Transaction`, `groups: CategoryGroupWithCategories[]` | `category-saved({id, category_id})`, `error(string)` | Self-contained `<tr>`; owns its own edit state |
| `CategoryPicker` | `modelValue: number\|null`, `groups` | `update:modelValue` | Searchable dropdown |
| `EnvelopeCard` | `envelope: EnvelopeRow` | — | Budget grid cell |
| `FileUploader` | — | `file-selected(File)` | Drag-and-drop + click |
| `MonthPicker` | `modelValue: string` (YYYY-MM) | `update:modelValue` | |
| `SkeletonRow` | `rows?: number` (default 5), `cols?: number` (default 5) | — | Loading placeholder `<tr>` |
| `ToastContainer` | — | — | Reads `useToastStore()`, fixed bottom-right |

### Stores

**`src/stores/auth.ts`**
```typescript
{ token, username, isAuthenticated }
login(username, password): Promise<void>
logout(): void
```

**`src/stores/toast.ts`**
```typescript
interface Toast { id: string; type: 'success'|'error'|'warning'|'info'; message: string; duration?: number }
toasts: Toast[]
success/error/warning/info(message, duration?): void
remove(id: string): void
```
Auto-dismiss via `setTimeout`. Default duration: 4000 ms.

### Composables

**`src/composables/useTheme.ts`**

Module-level singleton `ref<'emerald'|'night'>`. On first call:
1. Reads `localStorage.getItem('theme')`
2. Falls back to `window.matchMedia('(prefers-color-scheme: dark)')`
3. Applies `document.documentElement.setAttribute('data-theme', theme)`

`toggleTheme()` flips between `emerald` and `night`, persists to `localStorage`.

### Axios client (`src/api/client.ts`)

**Request interceptor**: attaches `Authorization: Bearer <token>` if token exists in auth store.

**Response interceptor**:
- 401: clear token + redirect to `/login`
- Other errors (except 422, 409): `useToastStore().error(extractMessage(error))`

---

## Testing

### Backend (pytest)

```bash
poetry run pytest                      # all 155 tests
poetry run pytest --cov=budgie         # with coverage report
poetry run pytest -x                   # stop on first failure
poetry run pytest tests/test_api/      # API layer
poetry run pytest tests/test_services/ # service layer
poetry run pytest tests/test_importers/ # parsers
```

**`tests/conftest.py`** provides:
- `engine` fixture: in-memory `aiosqlite` DB, schema created fresh per test
- `session` fixture: `AsyncSession` scoped per test
- `client` fixture: `httpx.AsyncClient` against the FastAPI app
- `auth_client` fixture: pre-registered user + `Authorization` header set

Test files mirror source: `budgie/services/budget.py` → `tests/test_services/test_budget.py`.

### Frontend (Vitest)

```bash
cd frontend
npm run test:unit -- --run    # single pass (CI)
npm run test:unit             # watch mode
```

Tests in `src/components/__tests__/*.spec.ts` use Vue Test Utils `mount()` and `flushPromises()`.

---

## Code Quality

### Python

```bash
poetry run ruff check budgie/ tests/    # lint (zero warnings)
poetry run ruff format budgie/ tests/   # format
poetry run mypy budgie/                 # type check (zero errors, 52 source files)
```

Rules:
- Google-style docstrings on all public functions, classes, modules
- Complete type annotations on all functions
- `# noqa` comments must be justified; unused `noqa` entries are errors

### TypeScript / Vue

```bash
cd frontend
npx tsc --noEmit     # strict type check
npm run lint         # ESLint
```

Rules:
- `<script setup lang="ts">` on every component
- All API calls in `src/api/` modules — never inline in components or stores
- DaisyUI component classes preferred over custom CSS
- No `any` types

---

## Docker & Deployment

### Multi-stage Dockerfile

**Stage 1** (`node:22-alpine`):
```dockerfile
COPY frontend/ .
RUN npm ci && npm run build
```

**Stage 2** (`python:3.12-slim`):
```dockerfile
COPY --from=0 /app/frontend/dist ./frontend/dist
COPY budgie/ pyproject.toml ...
RUN pip install poetry && poetry install --only main
USER budgie
CMD ["uvicorn", "budgie.main:app", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/api/health
```

The container exposes port 8000; `docker-compose.yml` maps it to host port **8080**.

### docker-compose.yml

```yaml
services:
  app:
    build: .
    ports:
      - "8080:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    restart: unless-stopped
```

### Commands

```bash
docker compose up --build    # build + start
docker compose up -d         # detached
docker compose logs -f       # follow logs
docker compose down          # stop
docker compose exec app poetry run alembic history   # check migrations
```

### Synology NAS deployment

1. `git clone` or SCP the project to the NAS
2. Create `.env` with a proper `SECRET_KEY`
3. `docker compose up -d`
4. Synology DSM → Control Panel → Login Portal → Advanced → Reverse Proxy:
   - Source: `budget.yourdomain.com` HTTPS 443
   - Destination: `localhost` 8080
   - Enable WebSocket headers

---

## Configuration

All settings loaded by `budgie/config.py` (Pydantic `BaseSettings`) from environment / `.env`.

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

Copy `.env.example` → `.env` and set `SECRET_KEY` to a cryptographically random string of 32+ characters before first run.
