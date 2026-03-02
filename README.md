# Budgie 🐦

> **EN** — Personal household budget web app · **FR** — Application web de gestion de budget personnel

Import bank transactions, budget by envelopes, auto-categorize, plan future purchases.  
Import de transactions bancaires, budget par enveloppes, catégorisation automatique, prévision d'achats.

---

| Layer / Couche | Technology / Technologie |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic, SQLite |
| Frontend | Vue.js 3, TypeScript, Vite, Tailwind CSS + DaisyUI 5 |
| Auth | JWT + bcrypt |
| Deployment / Déploiement | Docker Compose (Synology NAS) |
| Testing / Tests | pytest + pytest-asyncio · Vitest |

---

## Quick start / Démarrage rapide

```bash
# Backend
poetry install
poetry run uvicorn budgie.main:app --reload   # http://localhost:8000

# Frontend (separate terminal / terminal séparé)
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

```bash
# All tests / Tous les tests
poetry run pytest
cd frontend && npm run test:unit -- --run

# Lint + type check / Lint + vérification de types
poetry run ruff check budgie/ tests/
poetry run mypy budgie/
cd frontend && npx tsc --noEmit
```

## Docker

```bash
docker compose up --build     # build + run
docker compose up -d          # detached / en arrière-plan
```

Production port: **8080** → `http://localhost:8080`

---

## Documentation

| Document | Description |
|---|---|
| [docs/USER.md](docs/USER.md) | End-user guide (English) |
| [docs/UTILISATEUR.md](docs/UTILISATEUR.md) | Guide utilisateur (Français) |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | Technical / developer reference (English) |
| [docs/TECHNIQUE.md](docs/TECHNIQUE.md) | Référence technique développeur (Français) |
| [docs/PLAN.md](docs/PLAN.md) | Project plan & roadmap / Plan du projet & feuille de route |
