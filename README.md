# Budgie 🐦

Personal household budget web app — bank import, envelope budgeting, auto-categorization and virtual transactions.

---

## What it does

- **Import** bank transactions from CSV, Excel, QIF and OFX files
- **Categorize** automatically via payee history and configurable rules
- **Budget** using the envelope method (allocate every centime to a category)
- **Plan** future purchases with virtual transactions that affect envelope balances without touching real account balances
- **Self-hosted** — designed for Docker Compose deployment on a home server (Synology NAS)

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Alembic, SQLite |
| Frontend | Vue.js 3, TypeScript, Vite, Tailwind CSS + DaisyUI |
| Auth | JWT + bcrypt |
| Deployment | Docker Compose |

## Quick start (development)

```bash
# Backend
poetry install
poetry run uvicorn budgie.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

The API is available at `http://localhost:8000`, the frontend at `http://localhost:5173`.

## Running tests

```bash
# Backend (pytest + coverage)
poetry run pytest --cov=budgie

# Frontend
cd frontend && npm run test
```

## Documentation

Detailed documentation is in [`docs/`](docs/):

- [`docs/PLAN.md`](docs/PLAN.md) — full project plan and feature roadmap

---

---

# Budgie 🐦

Application web de gestion de budget personnel — import bancaire, budget par enveloppes, catégorisation automatique et transactions virtuelles.

---

## Fonctionnalités

- **Import** de transactions bancaires depuis des fichiers CSV, Excel, QIF et OFX
- **Catégorisation** automatique via l'historique des bénéficiaires et des règles configurables
- **Budget** par enveloppes (chaque centime est affecté à une catégorie)
- **Prévision** d'achats futurs via des transactions virtuelles qui impactent les enveloppes sans affecter les soldes réels des comptes
- **Auto-hébergé** — conçu pour un déploiement Docker Compose sur serveur domestique (NAS Synology)

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Alembic, SQLite |
| Frontend | Vue.js 3, TypeScript, Vite, Tailwind CSS + DaisyUI |
| Auth | JWT + bcrypt |
| Déploiement | Docker Compose |

## Démarrage rapide (développement)

```bash
# Backend
poetry install
poetry run uvicorn budgie.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

L'API est disponible sur `http://localhost:8000`, le frontend sur `http://localhost:5173`.

## Lancer les tests

```bash
# Backend (pytest + couverture)
poetry run pytest --cov=budgie

# Frontend
cd frontend && npm run test
```

## Documentation

La documentation détaillée se trouve dans [`docs/`](docs/) :

- [`docs/PLAN.md`](docs/PLAN.md) — plan complet du projet et feuille de route
