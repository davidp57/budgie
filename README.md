# Budgie 🐦

> **EN** — Self-hosted personal budget web app · **FR** — Application web de gestion de budget personnel auto-hébergée

[![CI](https://github.com/davidp57/budgie/actions/workflows/ci.yml/badge.svg)](https://github.com/davidp57/budgie/actions/workflows/ci.yml)
[![Docker](https://github.com/davidp57/budgie/actions/workflows/docker.yml/badge.svg)](https://github.com/davidp57/budgie/actions/workflows/docker.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

---

## Features / Fonctionnalités

| | EN | FR |
|---|---|---|
| 📥 | Bank import (CSV, Excel, QIF, OFX) | Import bancaire (CSV, Excel, QIF, OFX) |
| 🏷️ | Auto-categorization (payee history + rules) | Catégorisation automatique (historique + règles) |
| 💰 | Envelope budgeting with optional rollover | Budget par enveloppes avec report optionnel |
| 🔮 | Virtual transactions (planned purchases) | Transactions virtuelles (achats planifiés) |
| ⚡ | Quick expense entry with presets | Saisie rapide avec préréglages |
| 🌓 | Dark / light theme | Thème sombre / clair |
| 📱 | Mobile-first PWA | PWA mobile-first |
| 🐳 | Docker self-hosted (Synology NAS) | Docker auto-hébergé (NAS Synology) |

---

## Tech Stack

| Layer / Couche | Technology / Technologie |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic, SQLite |
| Frontend | Vue.js 3, TypeScript, Vite, Tailwind CSS + DaisyUI 5 |
| Auth / Authentification | JWT + bcrypt + WebAuthn passkeys |
| Deployment / Déploiement | Docker Compose (Synology NAS) |
| Testing / Tests | pytest + pytest-asyncio · Vitest |
| CI/CD | GitHub Actions (lint, tests, Docker build) |

---

## Quick start / Démarrage rapide

### From source / Depuis les sources

```bash
# Backend
poetry install
cp .env.example .env          # then set SECRET_KEY / puis définir SECRET_KEY
mkdir -p data/uploads
poetry run uvicorn budgie.main:app --reload   # http://localhost:8000

# Frontend (separate terminal / terminal séparé)
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

### Docker

```bash
cp .env.example .env          # set SECRET_KEY / définir SECRET_KEY
docker compose up -d --build  # http://localhost:8080
```

### Quality checks / Contrôles qualité

```bash
# Backend
poetry run pytest                        # ~200 tests
poetry run ruff check budgie/ tests/     # lint
poetry run mypy budgie/                  # type check

# Frontend
cd frontend
npx vitest run                           # ~40 tests
npx vue-tsc --noEmit                     # type check
npx eslint src/                          # lint
```

---

## Documentation

| | 🇬🇧 English | 🇫🇷 Français |
|---|---|---|
| User Guide / Guide utilisateur | [docs/en/user-guide.md](docs/en/user-guide.md) | [docs/fr/user-guide.md](docs/fr/user-guide.md) |
| Developer Guide / Guide développeur | [docs/en/developer-guide.md](docs/en/developer-guide.md) | [docs/fr/developer-guide.md](docs/fr/developer-guide.md) |
| Project Plan / Plan du projet | [docs/en/plan.md](docs/en/plan.md) | [docs/fr/plan.md](docs/fr/plan.md) |
| Roadmap / Feuille de route | [docs/en/roadmap.md](docs/en/roadmap.md) | [docs/fr/roadmap.md](docs/fr/roadmap.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) | — |

---

## License / Licence

[GNU Affero General Public License v3.0](LICENSE)
