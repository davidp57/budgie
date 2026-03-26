# Budgie — Copilot Instructions

## Project Overview

**Budgie** 🐦 is a personal household budget management web application.
Core features: bank transaction import (CSV, Excel, QIF, OFX), assisted/automatic categorization, envelope budgeting, virtual transactions (planned future purchases).

## Tech Stack

| Layer        | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.12+, FastAPI, Poetry                 |
| ORM         | SQLAlchemy 2.0 (async) + Alembic (migrations) |
| Database    | SQLite (amounts stored as integer centimes)    |
| Frontend    | Vue.js 3, Composition API, TypeScript, Vite   |
| CSS         | Tailwind CSS + DaisyUI                        |
| Auth        | JWT (bcrypt password hashing)                 |
| Deployment  | Docker Compose (Synology NAS target)          |
| Testing     | pytest + pytest-asyncio (back), Vitest (front)|
| Linting     | ruff, mypy (back), ESLint + Prettier (front)  |

## Development Principles

### TDD — Test-Driven Development

- **Always write tests BEFORE implementation code.**
- Workflow: Red → Green → Refactor.
  1. Write a failing test that defines the expected behavior.
  2. Write the minimum code to make the test pass.
  3. Refactor while keeping tests green.
- Every new feature, bugfix, or behavior change MUST start with a test.
- Test files mirror source structure: `budgie/services/budget_engine.py` → `tests/test_services/test_budget_engine.py`.
- Use fixtures and factories for test data (see `tests/conftest.py`) — avoid hardcoding.
- Aim for high coverage on business logic (services, importers, categorization). API routes tested via `httpx.AsyncClient`.

### Code Quality

- **Code language**: All code (variables, functions, classes, comments, docstrings, commit messages) MUST be in **English**.
- **Type hints**: All Python functions must have complete type annotations. `mypy` must pass with zero errors.
- **Linting**: `ruff` is the single tool for linting AND formatting Python code. Zero warnings policy.
- **VS Code integration**: The project is configured so that ruff, mypy, Pylance, ESLint and Vue language tools report errors/warnings directly in VS Code. Fix all reported issues before considering code complete.
- **Docstrings**: Use Google-style docstrings for all public functions, classes, and modules.
- **No magic numbers**: Use constants or enums. Monetary amounts are always in **integer centimes** (e.g., `1050` = 10.50€).

### Documentation

- **Documentation MUST be kept up to date** with every code change.
- **Bilingual**: All documentation files must be written in **both English and French**, in separate files under `docs/en/` and `docs/fr/`.
- Code-level documentation (docstrings, inline comments) is in **English only**.
- Update relevant docs in the SAME commit/PR as the code change.

### Architecture Rules

- **Backend**:
  - Layered architecture: `api/` (routes) → `services/` (business logic) → `models/` (ORM) / `schemas/` (Pydantic).
  - Routes must be thin — delegate logic to services.
  - All database operations go through SQLAlchemy async sessions.
  - Use Pydantic schemas for ALL request/response validation.
  - Configuration via `pydantic-settings` loading from `.env`.

- **Frontend**:
  - Use Vue 3 Composition API with `<script setup lang="ts">` syntax.
  - State management via Pinia stores.
  - API calls centralized in `src/api/` module using axios.
  - Components should be small, single-responsibility.
  - Use DaisyUI component classes — avoid custom CSS when a DaisyUI component exists.
  - **After every change to a `.vue` file, run `npx vue-tsc --noEmit -p tsconfig.app.json` (frontend equivalent of `mypy`) before considering the task done.** This catches template errors, broken bindings, and type mismatches that Vite only reports at runtime. Always use `-p tsconfig.app.json` to ensure all strict options (e.g. `noUncheckedIndexedAccess`) are applied — matching exactly what the CI runs.

- **Database**:
  - Monetary values are **integer centimes** (never floats).
  - Use Alembic for ALL schema changes — never modify the DB manually.
  - Unique constraints for deduplication (e.g., `import_hash` on transactions).

### Project Structure

```
budgie/
├── .github/
│   └── copilot-instructions.md   # This file
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/
├── budgie/                        # Backend Python package
│   ├── __init__.py
│   ├── config.py                  # Pydantic Settings
│   ├── database.py                # SQLAlchemy engine & session
│   ├── main.py                    # FastAPI app
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── api/                       # FastAPI routers
│   ├── services/                  # Business logic
│   └── importers/                 # Bank file parsers
├── frontend/                      # Vue.js 3 SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── api/                   # HTTP client
│       ├── components/            # Reusable Vue components
│       ├── views/                 # Page-level components
│       ├── stores/                # Pinia stores
│       └── router/                # Vue Router
├── tests/                         # Backend tests
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_importers/
├── docs/                          # Documentation (EN + FR)
│   ├── en/
│   │   ├── user-guide.md
│   │   └── developer-guide.md
│   └── fr/
│       ├── user-guide.md
│       └── developer-guide.md
└── data/                          # Runtime data (gitignored)
```

### Commit workflow

When the user asks to commit, follow these steps **in order** before creating the commit:

1. **Tests** — verify existing tests still pass; add or update tests for all new/changed behavior.
2. **Quality checks** — run all checks and fix all issues before proceeding:
   - Backend: `poetry run ruff check .`, `poetry run mypy budgie/`, `poetry run pytest`
   - Frontend: `cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json`, `npx eslint src/`, `npx vitest run`
3. **Documentation** — verify and update all relevant docs:
   - `docs/en/` and `docs/fr/` user/developer guides — update if the change affects user-facing behavior or architecture.
   - Docstrings — update if public API signatures or behavior changed.
4. **Commit** — stage all modified files (code + tests + docs) and commit in one clean commit with a descriptive message.

### PR preparation workflow

When the user asks to prepare a PR, follow these steps in order:

1. **Tests** — verify existing tests still pass; add or complete tests for all new/changed behavior.
2. **Documentation** — verify and update all relevant docs (user guides EN + FR, README, docstrings).
3. **Quality checks** — run all backend and frontend checks; fix all issues before proceeding.
4. **Temporary PR description** — create a temporary markdown file (e.g. `.github/pull_request_description.md`) to help the user fill in the PR on GitHub. This file must **not** be committed.
5. **Commit** — commit all the above changes (tests, docs) in one clean commit. Do **not** commit the PR description file.

### Release workflow

When the user asks to do a release, follow these steps in order:

1. **Ask for the version number** — never choose it yourself. Wait for the user to confirm (e.g. `v1.0.0`).
2. **Bump version** — update `version` in `pyproject.toml` to the new value.
3. **Update README** — update any version-specific info if needed.
4. **Quality checks** — run all backend and frontend checks; fix all issues before proceeding.
5. **Commit** — one clean commit: `release: vX.Y.Z`.
6. **Tag** — create an annotated git tag `vX.Y.Z`.
7. **Push** — ask the user before pushing the commit and tag to GitHub.

### Commands

> **Version policy**: Never change the version number in `pyproject.toml` or anywhere else unless explicitly asked by the user.

```bash
# Backend
poetry install                          # Install dependencies
poetry run pytest                       # Run tests
poetry run pytest --cov=budgie          # Run tests with coverage
poetry run ruff check .                 # Lint
poetry run ruff format .                # Format
poetry run mypy budgie/                 # Type checking
poetry run uvicorn budgie.main:app --reload  # Dev server

# Frontend
cd frontend
npm install                             # Install dependencies
npm run dev                             # Vite dev server
npm run build                           # Production build
npx vitest run                          # Tests
npx eslint src/                         # ESLint
npx vue-tsc --noEmit -p tsconfig.app.json  # TypeScript check (matches CI exactly)

# Docker
docker compose up --build               # Build & run
docker compose up -d                    # Run detached
```

### Naming Conventions

| Element            | Convention        | Example                          |
|-------------------|-------------------|----------------------------------|
| Python files      | snake_case        | `budget_engine.py`               |
| Python classes    | PascalCase        | `BudgetAllocation`               |
| Python functions  | snake_case        | `get_month_budget()`             |
| Python constants  | UPPER_SNAKE_CASE  | `MAX_IMPORT_SIZE`                |
| Private helpers   | `_` prefix        | `_parse_amount()`               |
| Vue components    | PascalCase        | `EnvelopeCard.vue`               |
| Vue composables   | camelCase, `use`  | `useBudget.ts`                   |
| TypeScript files  | camelCase         | `apiClient.ts`                   |
| API endpoints     | kebab-case        | `/api/category-groups`           |
| DB tables         | snake_case plural | `budget_allocations`             |
| DB columns        | snake_case        | `auto_category_id`               |
| Test files        | `test_` prefix    | `test_budget_engine.py`          |
