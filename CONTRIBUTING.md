# Contributing to Budgie 🐦

Thank you for your interest in contributing! Budgie is open to contributions of all kinds — bug reports, feature requests, documentation improvements, and code contributions.

---

## Ways to Contribute

### 🐛 Report a Bug

1. Search [existing issues](https://github.com/davidp57/budgie/issues) first to avoid duplicates.
2. Open a new issue using the **Bug report** template.
3. Include: steps to reproduce, expected vs actual behavior, screenshots if relevant, and your platform / browser.

### 💡 Request a Feature

1. Search [existing issues](https://github.com/davidp57/budgie/issues) — someone may have suggested it already.
2. Open a new issue using the **Feature request** template.
3. Be as specific as possible: what problem does it solve? What should it look like?

### 📝 Improve the Documentation

Documentation lives in `docs/en/` and `docs/fr/`. Both languages must be kept in sync. If your English is better than your French (or vice versa), open a PR with the language you know and note in the description that the translation needs review.

### 🔧 Submit a Pull Request

---

## Development Setup

### Prerequisites

- Python 3.12+, [Poetry](https://python-poetry.org/)
- Node.js 22+, npm

### Install

```bash
git clone https://github.com/davidp57/budgie.git
cd budgie

# Backend
poetry install
cp .env.example .env          # Edit → set SECRET_KEY
mkdir -p data/uploads
poetry run uvicorn budgie.main:app --reload   # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                                    # http://localhost:5173
```

---

## Workflow

1. **Fork** the repository and clone your fork.
2. **Branch** from `develop` (not `main`): `git checkout -b feat/my-feature develop`
3. **Write tests first** — Budgie follows TDD. See [developer guide](docs/en/developer-guide.md).
4. **Implement** the minimum code to make the tests pass.
5. **Quality checks** — all checks must pass before opening a PR:

```bash
# Backend
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy budgie/
poetry run pytest

# Frontend
cd frontend
npx vue-tsc --noEmit -p tsconfig.app.json
npx eslint src/
npx vitest run
```

6. **Commit** with a clear message using [Conventional Commits](https://www.conventionalcommits.org/) style:
   - `feat: add envelope rollover toggle`
   - `fix: correct CSV amount parsing for negative values`
   - `docs: update French user guide`
   - `test: add coverage for OFX importer edge case`
7. **Push** your branch and **open a Pull Request** against `develop`.

---

## Code Standards

| Rule | Details |
|---|---|
| Language | All code, comments, docstrings, and commit messages in **English** |
| Python | Type hints on all functions, Google-style docstrings, ruff + mypy clean |
| Vue | `<script setup lang="ts">`, Composition API, DaisyUI components |
| Amounts | Always integer centimes (never floats) — e.g. `1050` = €10.50 |
| Tests | Test files mirror source: `budgie/services/foo.py` → `tests/test_services/test_foo.py` |
| Docs | Every PR that changes behavior must update both `docs/en/` and `docs/fr/` |

Full details in the [developer guide](docs/en/developer-guide.md).

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable releases only |
| `develop` | Integration branch — base all PRs here |
| `feat/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation-only changes |

---

## Questions?

Open a [Discussion](https://github.com/davidp57/budgie/discussions) or an issue with the **question** label. We're happy to help.

---

☕ If Budgie saves you time or money, consider [buying me a coffee](https://buymeacoffee.com/veaf_zip) — it's appreciated!
