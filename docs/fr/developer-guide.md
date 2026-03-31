# Budgie 🐦 — Guide développeur

🌐 [English version](../en/developer-guide.md)

## Sommaire

1. [Structure du projet](#1-structure-du-projet)
2. [Vue d'ensemble de l'architecture](#2-vue-densemble-de-larchitecture)
3. [Mise en place du développement](#3-mise-en-place-du-développement)
4. [Modèles de données](#4-modèles-de-données)
5. [Schéma de la base de données](#5-schéma-de-la-base-de-données)
6. [Référence API](#6-référence-api)
7. [Pipeline d'import](#7-pipeline-dimport)
8. [Moteur de catégorisation](#8-moteur-de-catégorisation)
9. [Moteur de budget](#9-moteur-de-budget)
10. [Transactions virtuelles](#10-transactions-virtuelles)
11. [Composants & Stores frontend](#11-composants--stores-frontend)
12. [Lancer les tests](#12-lancer-les-tests)
13. [Lint et vérification de types](#13-lint-et-vérification-de-types)
14. [CI/CD](#14-cicd)
15. [Docker & Déploiement](#15-docker--déploiement)
16. [Configuration](#16-configuration)
17. [Conventions et bonnes pratiques](#17-conventions-et-bonnes-pratiques)
18. [Sécurité & Chiffrement](#18-sécurité--chiffrement)

---

## 1. Structure du projet

```
budgie/
├── .github/
│   ├── copilot-instructions.md    # Instructions Copilot
│   └── workflows/
│       ├── ci.yml                 # CI — lint, vérification de types, tests
│       └── docker.yml             # CI/CD — build image Docker sur GHCR
├── alembic/                       # Migrations de base de données
│   └── versions/
├── budgie/                        # Package Python backend
│   ├── api/                       # Routeurs FastAPI (minces — délèguent aux services)
│   │   ├── accounts.py
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categories.py
│   │   ├── categorize.py
│   │   ├── category_groups.py
│   │   ├── category_rules.py
│   │   ├── deps.py                # Dépendances FastAPI (get_current_user, get_session)
│   │   ├── envelopes.py
│   │   ├── imports.py
│   │   ├── payees.py
│   │   ├── transactions.py
│   │   └── users.py
│   ├── importers/                 # Parseurs de fichiers bancaires
│   │   ├── base.py                # ImportedTransaction + ABC BaseImporter
│   │   ├── csv_importer.py        # Détection auto séparateur, décimal, colonnes
│   │   ├── excel_importer.py      # Via openpyxl
│   │   ├── qif_importer.py        # Via quiffen
│   │   └── ofx_importer.py        # ElementTree, FITID → import_hash
│   ├── models/                    # Modèles ORM SQLAlchemy
│   │   ├── account.py
│   │   ├── budget.py
│   │   ├── category.py
│   │   ├── category_rule.py
│   │   ├── envelope.py
│   │   ├── payee.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── schemas/                   # Schémas Pydantic requête/réponse
│   ├── services/                  # Toute la logique métier
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
│   ├── database.py                # Moteur SQLAlchemy async + fabrique de sessions
│   └── main.py                    # App FastAPI, lifespan, fallback SPA
├── frontend/                      # SPA Vue.js 3
│   ├── src/
│   │   ├── api/                   # Wrappers HTTP typés (axios)
│   │   │   ├── client.ts          # Instance Axios, intercepteur JWT, toasts d'erreur
│   │   │   ├── types.ts           # Interfaces TypeScript partagées
│   │   │   ├── accounts.ts
│   │   │   ├── auth.ts
│   │   │   ├── budget.ts
│   │   │   ├── categories.ts
│   │   │   ├── envelopes.ts
│   │   │   ├── imports.ts
│   │   │   ├── transactions.ts
│   │   │   └── users.ts
│   │   ├── components/            # Composants Vue réutilisables
│   │   │   ├── AppNav.vue         # Navigation responsive (sidebar desktop, dock mobile)
│   │   │   ├── CategoryPicker.vue
│   │   │   ├── CreateCategoryModal.vue
│   │   │   ├── DrawerCard.vue
│   │   │   ├── EnvelopeCard.vue
│   │   │   ├── EnvelopeManager.vue
│   │   │   ├── FileUploader.vue
│   │   │   ├── MonthPicker.vue
│   │   │   ├── QuickExpense.vue   # Saisie rapide (bottom sheet / modale)
│   │   │   ├── SkeletonRow.vue
│   │   │   ├── ToastContainer.vue
│   │   │   ├── DonutChart.vue     # Graphique donut réutilisable (Chart.js)
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
│   │   │   ├── DepensesView.vue   # Vue Dépenses + dashboard (ancien TransactionsView)
│   │   │   ├── HomeView.vue
│   │   │   ├── ImportView.vue
│   │   │   ├── LoginView.vue
│   │   │   ├── SettingsView.vue
│   │   │   └── TransactionsView.vue # Transactions bancaires (imports)
│   │   └── router/
│   └── public/
│       └── manifest.json          # PWA manifest
├── tests/                         # Tests backend
│   ├── conftest.py
│   ├── test_api/
│   ├── test_importers/
│   ├── test_models/
│   ├── test_schemas/
│   └── test_services/
├── scripts/
│   └── backup.sh                  # Script de sauvegarde SQLite
├── docs/
│   ├── en/                        # Documentation anglaise
│   └── fr/                        # Documentation française
├── Dockerfile                     # Build multi-stage
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
└── .env.example
```

---

## 2. Vue d'ensemble de l'architecture

### Architecture backend

```
Requête HTTP
    │
    ▼
api/           ← valide via schémas Pydantic, appelle le service, retourne le schéma
    │
    ▼
services/      ← toute la logique métier ; pas d'HTTP, pas d'ORM direct dans les routes
    │
    ▼
models/        ← modèles ORM SQLAlchemy
database.py    ← fabrique AsyncSession (injection de dépendances via FastAPI Depends)
    │
    ▼
SQLite (data/budgie.db)
```

Les routes doivent rester **minces**. Toute la logique appartient aux `services/`.

### Flux d'authentification

1. `POST /api/auth/login` → `{ access_token, token_type }`
2. Le frontend stocke le token dans `localStorage`
3. Intercepteur Axios de requête : `Authorization: Bearer <token>` sur chaque requête
4. Dépendance FastAPI `get_current_user` : décode le JWT, charge l'utilisateur depuis la DB
5. Sur 401 : l'intercepteur Axios de réponse efface le token, redirige vers `/login`

### SPA en production

`budgie/main.py` monte `frontend/dist/assets/` sous `/assets` et enregistre une route catch-all `GET /{full_path:path}` retournant `frontend/dist/index.html`. Activé uniquement quand `frontend/dist/` existe (dans le build Docker).

### Flux de données frontend

```
Vue / Composant
    │ importe
    ▼
src/api/*.ts       ← wrappers typés (appels axios)
    │
    ▼
FastAPI /api/*
```

L'intercepteur de réponse Axios déclenche `useToastStore().error(message)` pour toutes les erreurs non-401 (sauf 422 et 409, gérées localement par les vues).

---

## 3. Mise en place du développement

### Prérequis

- Python 3.12+ et [Poetry](https://python-poetry.org/)
- Node.js 22+ et npm

### Backend

```bash
poetry install
mkdir -p data/uploads
cp .env.example .env          # puis définir SECRET_KEY

# Serveur de dev — les migrations Alembic s'exécutent automatiquement au démarrage
poetry run uvicorn budgie.main:app --reload
```

- API : `http://localhost:8000/api`
- Docs OpenAPI : `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite proxifie toutes les requêtes `/api/*` vers `http://localhost:8000`.

---

## 4. Modèles de données

Tous les modèles sont des classes SQLAlchemy dans `budgie/models/`. Les schémas Pydantic correspondants se trouvent dans `budgie/schemas/`.

**Invariant clé** : tous les montants monétaires sont stockés en **centimes entiers** (ex. `5050` = 50,50 €). Les flottants ne sont jamais utilisés pour l'argent.

### `User`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | Identifiant auto-incrémenté |
| `username` | `str` unique | Nom d'utilisateur |
| `hashed_password` | `str` | Hash bcrypt du mot de passe |
| `budget_mode` | `str` | Mode de budget (`envelope`) |
| `created_at` | `datetime` | Date de création |

### `Account`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Nom du compte (ex. « Compte courant ») |
| `type` | `str` | `checking`, `savings`, `credit`, `cash` |
| `on_budget` | `bool` | Inclus dans le budget |
| `created_at` | `datetime` | |

### `CategoryGroup`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Nom du groupe (ex. « Logement ») |
| `sort_order` | `int` | Ordre d'affichage |

### `Category`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `group_id` | `int` FK → CategoryGroup | |
| `name` | `str` | Nom de la catégorie (ex. « Loyer ») |
| `sort_order` | `int` | Ordre d'affichage dans le groupe |
| `hidden` | `bool` | Masquée dans l'interface |

### `Envelope`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Nom de l'enveloppe |
| `emoji` | `str` | Emoji affiché (ex. `🍞`) |
| `rollover` | `bool` | Report du solde non dépensé |
| `sort_order` | `int` | Ordre d'affichage |
| `category_ids` | relation M2M | Catégories rattachées (via table `envelope_categories`) |

### `Payee`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `name` | `str` | Nom du bénéficiaire |
| `auto_category_id` | `int` FK → Category (nullable) | Catégorie auto-assignée |

### `Transaction`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `account_id` | `int` FK → Account | |
| `date` | `date` | Date de la transaction |
| `payee_id` | `int` FK → Payee (nullable) | |
| `category_id` | `int` FK → Category (nullable) | |
| `amount` | `int` | Montant en **centimes** (négatif = dépense) |
| `memo` | `str` | Description |
| `cleared` | `str` | `uncleared`, `cleared`, `reconciled` |
| `is_virtual` | `bool` | `True` pour les prévisions |
| `virtual_linked_id` | `int` FK → Transaction (nullable) | Lien prévision ↔ réalisation |
| `envelope_id` | `int` FK → Envelope (nullable) | Lien direct à une enveloppe (sans catégorie) |
| `reconciled_with_id` | `int` FK → Transaction (nullable) | Transaction bancaire liée à cette dépense |
| `import_hash` | `str` unique (nullable) | Empreinte SHA-256 pour la déduplication |
| `created_at` | `datetime` | |

### `SplitTransaction`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `parent_id` | `int` FK → Transaction | Transaction parent |
| `category_id` | `int` FK → Category | |
| `amount` | `int` | Montant en centimes |
| `memo` | `str` | |

### `BudgetAllocation`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `envelope_id` | `int` FK → Envelope | |
| `month` | `str` | Format `AAAA-MM` |
| `budgeted` | `int` | Montant alloué en centimes |

Contrainte unique sur `(envelope_id, month)`.

### `CategoryRule`

| Champ | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `pattern` | `str` | Motif de recherche |
| `match_field` | `str` | `payee` ou `memo` |
| `match_type` | `str` | `contains`, `exact`, `regex` |
| `category_id` | `int` FK → Category | Catégorie à affecter |
| `priority` | `int` | Priorité (évaluée en ordre décroissant) |

---

## 5. Schéma de la base de données

Base SQLite avec Alembic pour les migrations. Mode journal WAL, clés étrangères activées.

### Migrations

Les migrations Alembic se trouvent dans `alembic/versions/`. Elles s'exécutent **automatiquement** au démarrage de l'application (via le lifespan FastAPI).

```bash
# Créer une nouvelle migration
poetry run alembic revision --autogenerate -m "description"

# Appliquer manuellement
poetry run alembic upgrade head

# Voir l'historique
poetry run alembic history
```

> ⚠️ Ne jamais modifier la DB manuellement. Toujours passer par Alembic.

---

## 6. Référence API

Tous les endpoints nécessitent `Authorization: Bearer <token>` sauf `/api/auth/*`.

Documentation interactive disponible à `http://localhost:8000/docs` (Swagger UI).

### Auth

| Méthode | Chemin | Corps | Retourne |
|---|---|---|---|
| `POST` | `/api/auth/register` | `{username, password}` | `UserOut` |
| `POST` | `/api/auth/login` | `{username, password}` | `{access_token, token_type}` |

### Comptes

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/accounts` | Lister tous pour l'utilisateur courant |
| `POST` | `/api/accounts` | Créer |
| `PUT` | `/api/accounts/{id}` | Mettre à jour |
| `DELETE` | `/api/accounts/{id}` | Supprimer |

### Transactions

| Méthode | Chemin | Params de requête |
|---|---|---|
| `GET` | `/api/transactions` | `account_id`, `is_virtual` (bool), `envelope_id` (int), `month` (AAAA-MM), `expenses_only` (bool) |
| `POST` | `/api/transactions` | — |
| `PUT` | `/api/transactions/{id}` | — |
| `DELETE` | `/api/transactions/{id}` | — |
| `GET` | `/api/transactions/virtual/unlinked` | Prévisions en attente |
| `POST` | `/api/transactions/virtual/match` | `{transaction_id, virtual_id}` |

> **Ordre des routes** : `/virtual/unlinked` doit être déclaré **avant** `/{id}` dans le routeur pour éviter que `virtual` soit interprété comme un identifiant.

### Budget

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/budget/{month}` | Format `month` : `AAAA-MM` |
| `PUT` | `/api/budget/{month}` | Upsert des allocations |

### Import

| Méthode | Chemin | Notes |
|---|---|---|
| `POST` | `/api/imports/parse` | `multipart/form-data` ; retourne la prévisualisation |
| `POST` | `/api/imports/confirm` | Corps JSON ; persiste les transactions |

### Catégorisation

| Méthode | Chemin | Notes |
|---|---|---|
| `POST` | `/api/categorize` | Catégoriser par lot |
| `GET` | `/api/category-rules` | Lister les règles |
| `POST` | `/api/category-rules` | Créer une règle |
| `PUT` | `/api/category-rules/{id}` | Mettre à jour |
| `DELETE` | `/api/category-rules/{id}` | Supprimer |

### Catégories & Groupes

| Méthode | Chemin |
|---|---|
| `GET/POST` | `/api/category-groups` |
| `PUT/DELETE` | `/api/category-groups/{id}` |
| `POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |

### Enveloppes

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/envelopes` | Lister avec catégories affectées |
| `POST` | `/api/envelopes` | `{name, emoji?, rollover?, category_ids?}` |
| `PUT` | `/api/envelopes/{id}` | Mettre à jour |
| `DELETE` | `/api/envelopes/{id}` | Supprimer (+ allocations) |

### Bénéficiaires

| Méthode | Chemin |
|---|---|
| `GET/POST` | `/api/payees` |
| `PUT/DELETE` | `/api/payees/{id}` |

### Utilisateurs

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/users/me` | Profil utilisateur courant |
| `PUT` | `/api/users/me` | Mettre à jour les préférences |

### Santé

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/health` | `{"status": "ok"}` — pas d'auth requise |

---

## 7. Pipeline d'import

### Parseurs (`budgie/importers/`)

| Format | Classe | Détails |
|---|---|---|
| CSV | `CsvImporter` | Détection auto du séparateur (`;`, `,`, `\t`), du séparateur décimal (`.`, `,`), des noms de colonnes depuis des listes candidates |
| Excel | `ExcelImporter` | Même détection, via `openpyxl` |
| QIF | `QifImporter` | Via la bibliothèque `quiffen` |
| OFX | `OfxImporter` | Parsing ElementTree (pas de schéma strict), FITID utilisé comme `import_hash` |

Tous les parseurs étendent `BaseImporter` et produisent `list[ImportedTransaction]`.

### Hash d'import

```python
import_hash = sha256(f"{date}{amount_centimes}{description}{reference}".encode()).hexdigest()
```

Pour OFX : `import_hash = sha256(fitid.encode()).hexdigest()`

Contrainte `UNIQUE` sur `import_hash` → idempotence des imports.

### Flux de confirmation (`services/importer.py`)

1. Pour chaque `ImportedTransaction` du payload :
   - Ignorer si `import_hash` déjà en base
   - Insérer la ligne `Transaction`
   - Si `virtual_linked_id` défini : marquer la transaction virtuelle comme `reconciled`
2. Commit unique à la fin

### Note technique

Lors de l'appel à `POST /api/imports/parse`, Axios ne doit pas définir `Content-Type: application/json` — le navigateur définit `multipart/form-data` avec le boundary automatiquement.

---

## 8. Moteur de catégorisation

Point d'entrée : `services/categorizer.py` → `categorize_transaction(session, user_id, txn)`

### Étape 1 — Correspondance bénéficiaire

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

### Étape 2 — Correspondance règle

Règles évaluées par `priority DESC` :

| `match_field` | `match_type` | Logique |
|---|---|---|
| `payee` / `memo` | `contains` | `pattern.lower() in field.lower()` |
| `payee` / `memo` | `exact` | `field.lower() == pattern.lower()` |
| `payee` / `memo` | `regex` | `re.search(pattern, field, re.IGNORECASE)` |

Retourne `(category_id, "rule")` à la première correspondance, ou `(None, "none")`.

Après catégorisation manuelle, le bénéficiaire est mis à jour avec `auto_category_id` pour les recherches futures.

---

## 9. Moteur de budget

Point d'entrée : `services/budget.py` → `get_budget_month(session, user_id, month)`

### Calcul par enveloppe

```
Pour chaque enveloppe :
  budgeted  = BudgetAllocation.budgeted WHERE envelope_id = X AND month = mois_cible
              (0 si aucune allocation)
  activity  = SUM(Transaction.amount) WHERE category_id IN envelope.category_ids
              AND month(date) = mois_cible           ← inclut is_virtual=True

  SI envelope.rollover :
    available = SUM(budgeted_m - activity_m) sur tous les mois m ≤ mois_cible
  SINON :
    available = budgeted + activity  (mois en cours uniquement)
```

### Calcul global

```
income          = SUM(amount) WHERE amount > 0 AND month = mois_cible
total_budgeted  = SUM(BudgetAllocation.budgeted) WHERE month = mois_cible
to_be_budgeted  = income - total_budgeted
```

**Invariant** : les transactions `is_virtual=True` affectent `activity` (et `available`) mais sont exclues des soldes de comptes réels.

---

## 10. Transactions virtuelles

### Modèle

Colonnes sur `Transaction` :
- `is_virtual: bool` — `True` pour les prévisions
- `virtual_linked_id: int | None` — FK vers la prévision réalisée
- `cleared: str | None` — `"reconciled"` quand la prévision est liée

### Services (`services/transaction.py`)

```python
async def get_virtual_unlinked(session, user_id) -> list[Transaction]:
    """Retourne les transactions virtuelles pas encore réconciliées."""

async def link_virtual(session, transaction_id, virtual_id, user_id):
    """Lie une txn réelle à une virtuelle ; marque la virtuelle comme réconciliée."""
```

### Algorithme de correspondance frontend (`ImportView.vue`)

```
amount_match = abs(importée.montant - virtuelle.montant) / abs(virtuelle.montant) <= 0.10
date_match   = abs((importée.date - virtuelle.date).jours) <= 60
suggestion   = amount_match ET date_match
```

---

## 11. Composants & Stores frontend

### Composants

| Composant | Description |
|---|---|
| `AppNav` | Navigation responsive (sidebar desktop + dock mobile) |
| `QuickExpense` | Saisie rapide de transaction (bottom sheet mobile, modale desktop) |
| `DrawerCard` | Carte avec palette de couleurs, support swipe |
| `EnvelopeCard` | Cellule budget : nom, emoji, chips catégories, badge rollover, édition inline |
| `EnvelopeManager` | Panneau paramètres — CRUD complet des enveloppes |
| `TransactionRow` | `<tr>` autonome avec édition de catégorie inline |
| `CategoryPicker` | Combobox de recherche avec création inline de catégorie |
| `CreateCategoryModal` | Modale de création de catégorie |
| `FileUploader` | Glisser-déposer + clic |
| `MonthPicker` | Navigation entre mois (AAAA-MM) |
| `SkeletonRow` | Placeholder de chargement |
| `ToastContainer` | Notifications toast (bas-droite, auto-dismiss 4 s) |

### Stores Pinia

**`auth.ts`** — Token JWT, login/logout, `isAuthenticated`

**`toast.ts`** — File de notifications (success/error/warning/info), auto-dismiss

**`budget.ts`** — Données du mois budget (enveloppes, allocations, activité)

**`presets.ts`** — Préréglages QuickExpense (mémo, montant, catégorie, compte)

### Composables

**`useTheme.ts`** — Singleton `ref<'emerald'|'night'>`. Lit `localStorage`, se rabat sur `prefers-color-scheme`. `toggleTheme()` bascule et persiste.

**`useNearbyPlaces.ts`** — Interroge l'API Overpass (OpenStreetMap) avec la position GPS pour suggérer des commerces proches avec emojis.

### Client Axios (`src/api/client.ts`)

- **Intercepteur de requête** : attache `Authorization: Bearer <token>`
- **Intercepteur de réponse** : 401 → clear token + redirect `/login` ; autres erreurs → toast d'erreur (sauf 422/409)

---

## 12. Lancer les tests

### Backend (pytest)

```bash
# Tous les tests (~200 tests)
poetry run pytest

# Avec couverture
poetry run pytest --cov=budgie

# Arrêt au premier échec
poetry run pytest -x

# Par couche
poetry run pytest tests/test_api/           # Routes API
poetry run pytest tests/test_services/      # Services
poetry run pytest tests/test_importers/     # Parseurs
poetry run pytest tests/test_models/        # Modèles
poetry run pytest tests/test_schemas/       # Schémas Pydantic
```

**`tests/conftest.py`** fournit :
- `engine` : base `aiosqlite` en mémoire, schéma recréé à chaque test
- `session` : `AsyncSession` scopée par test
- `client` : `httpx.AsyncClient` contre l'app FastAPI
- `auth_client` : utilisateur pré-créé avec header `Authorization`

Les fichiers de test mirroir la structure source : `budgie/services/budget.py` → `tests/test_services/test_budget.py`.

### Frontend (Vitest)

```bash
cd frontend
npm run test:unit -- --run    # exécution unique (CI)
npm run test:unit             # mode watch
```

Tests dans `src/components/__tests__/*.spec.ts` utilisant Vue Test Utils.

| Fichier | Tests | Couverture |
|---|---|---|
| `EnvelopeCard.spec.ts` | 7 | Rendu, badge rollover, couleur disponible, édition budget |
| `EnvelopeManager.spec.ts` | 11 | Liste, état vide, création, édition, annulation, suppression |
| `MonthPicker.spec.ts` | 5 | Navigation, passage d'année |
| `TransactionRow.spec.ts` | 12 | Rendu, couleur montant, nom catégorie, flux d'édition, émissions |
| `DrawerCard.spec.ts` | — | Couleurs, swipe, contenu |
| `auth.test.ts` | 4 | Store auth, login, logout |

---

## 13. Lint et vérification de types

### Python

```bash
# Lint (zéro avertissement)
poetry run ruff check budgie/ tests/

# Auto-correction
poetry run ruff check budgie/ tests/ --fix

# Formatage
poetry run ruff format budgie/ tests/

# Vérification de types (strict, zéro erreur)
poetry run mypy budgie/
```

Configuration dans `pyproject.toml` sous `[tool.ruff]` et `[tool.mypy]`.

### TypeScript / Vue

```bash
cd frontend

# Vérification de types strict (Vue + TS)
npx vue-tsc --noEmit

# Lint ESLint
npm run lint

# Formatage Prettier
npx prettier --write src/
```

Règles :
- `<script setup lang="ts">` sur chaque composant
- Tous les appels API dans `src/api/` — jamais en inline dans les composants
- Préférer les classes DaisyUI au CSS custom
- Pas de type `any`

---

## 14. CI/CD

### `ci.yml` — Contrôles qualité

Situé dans `.github/workflows/ci.yml`.

| Propriété | Valeur |
|---|---|
| Déclencheur | Push sur `main` / `develop` + Pull requests |

**Job backend :** ruff lint, ruff format check, mypy, pytest.

**Job frontend :** vue-tsc, ESLint, Vitest.

### `docker.yml` — Build et publication Docker

Situé dans `.github/workflows/docker.yml`.

| Propriété | Valeur |
|---|---|
| Déclencheur | Push sur `main` / `develop` + workflow_dispatch (manuel) |
| Registry | GitHub Container Registry (GHCR) |
| Image | `ghcr.io/davidp57/budgie` |

**Étapes :**

1. Checkout du code
2. Login GHCR via `docker/login-action@v3`
3. Extraction metadata (tags : branche, semver, `latest`) via `docker/metadata-action@v5`
4. Build & push via `docker/build-push-action@v6`
5. Smoke test : démarre le conteneur et vérifie `curl /api/health`

### Déclencher un build

```bash
# Pousser sur main ou develop → build automatique
git push origin main

# Ou manuellement : Actions → docker → Run workflow
```

---

## 15. Docker & Déploiement

### Dockerfile multi-stage

**Stage 1** (`node:22-alpine`) :
- Copie `frontend/`, `npm ci`, `npm run build`
- Produit les fichiers statiques dans `frontend/dist/`

**Stage 2** (`python:3.12-slim`) :
- Installe `gosu` (drop de privilèges PUID/PGID)
- Installe Poetry + dépendances Python (production only)
- Copie le backend, Alembic, le frontend compilé
- Crée un utilisateur `budgie` non-root
- Health check sur `/api/health`

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

Le conteneur expose le port **8000** en interne ; `docker-compose.yml` le mappe sur **8080** par défaut.

### Déploiement Synology

Voir le [Guide utilisateur — section Déploiement Docker](user-guide.md#14-déploiement-docker) pour les instructions complètes (SSH, Portainer, proxy inverse HTTPS).

---

## 16. Configuration

Toutes les variables chargées par `budgie/config.py` (Pydantic `BaseSettings`) depuis l'environnement ou `.env`.

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///data/budgie.db` | URL de la base SQLAlchemy async |
| `SECRET_KEY` | `change-me-in-production` | Clé HMAC de signature JWT — **à changer** |
| `ALGORITHM` | `HS256` | Algorithme JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Durée de vie du token (24 h) |
| `UPLOAD_DIR` | `data/uploads` | Répertoire temporaire pour les fichiers importés |
| `HOST` | `0.0.0.0` | Adresse d'écoute Uvicorn |
| `PORT` | `8000` | Port d'écoute Uvicorn |
| `DEBUG` | `false` | Mode debug FastAPI |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Origines CORS autorisées |
| `WEBAUTHN_RP_ID` | `localhost` | Identifiant du Relying Party WebAuthn — doit correspondre exactement au domaine servi (sans schéma ni port) |
| `WEBAUTHN_RP_NAME` | `Budgie` | Nom lisible de l'application affiché dans les invites de clés d'accès |
| `WEBAUTHN_ORIGIN` | `https://localhost:5173` | URL d'origine complète du frontend (schéma + hôte + port si non standard) |

---

## 17. Conventions et bonnes pratiques

### Conventions de nommage

| Élément | Convention | Exemple |
|---|---|---|
| Fichiers Python | snake_case | `budget_engine.py` |
| Classes Python | PascalCase | `BudgetAllocation` |
| Fonctions Python | snake_case | `get_month_budget()` |
| Constantes Python | UPPER_SNAKE_CASE | `MAX_IMPORT_SIZE` |
| Composants Vue | PascalCase | `EnvelopeCard.vue` |
| Composables Vue | camelCase, préfixe `use` | `useTheme.ts` |
| Fichiers TypeScript | camelCase | `apiClient.ts` |
| Endpoints API | kebab-case | `/api/category-groups` |
| Tables DB | snake_case pluriel | `budget_allocations` |
| Colonnes DB | snake_case | `auto_category_id` |
| Fichiers de test | préfixe `test_` | `test_budget_engine.py` |

### Principes de développement

- **TDD** — Red → Green → Refactor. Toujours écrire le test avant l'implémentation.
- **Langue du code** — Tout en anglais (variables, fonctions, classes, commentaires, docstrings).
- **Type hints** — Annotations complètes sur toutes les fonctions Python. mypy strict.
- **Docstrings** — Style Google pour toutes les fonctions publiques.
- **Pas de nombres magiques** — Utiliser des constantes ou des enums.
- **Montants en centimes** — Jamais de flottants pour l'argent.
- **Routes minces** — Déléguer la logique aux services.
- **Documentation bilingue** — EN + FR pour toute la documentation.

---

## 18. Sécurité & Chiffrement

### Principes de conception

- **Toutes les données utilisateur chiffrées au repos** — noms, montants, dates, mémos… tout sauf les IDs structurels et les clés étrangères.
- **Clé de chiffrement jamais stockée sur le serveur** — elle n'existe qu'en RAM pendant la session authentifiée.
- **Déchiffrement côté serveur (Approche B)** — la clé dérivée est envoyée via HTTPS, maintenue en mémoire, et purgée lors de la déconnexion ou l'expiration du token.
- **Sécurité gérée par l'utilisateur** — seule la passphrase de l'utilisateur peut dériver la clé. Les administrateurs ne peuvent pas récupérer les données.

### Stack cryptographique

| Composant | Technologie | Détails |
|---|---|---|
| Chiffrement symétrique | **AES-256-GCM** | Chiffrement authentifié avec nonce aléatoire de 96 bits par champ |
| Dérivation de clé | **Argon2id** | time_cost=3, memory_cost=64 MiB, parallelism=4, sortie 256 bits |
| Vérification de la clé | **Challenge blob** | Chiffrement AES-GCM d'un sel aléatoire de 32 octets ; le tag GCM valide la clé |
| Authentification | **WebAuthn (Passkeys)** | `py_webauthn` (backend), API `navigator.credentials` (navigateur) |
| Repli PIN | **PBKDF2-HMAC-SHA256** | 100k itérations, sel spécifique à l'appareil, encapsule la clé dans `localStorage` (nécessite HTTPS) |
| Document de récupération | **fpdf2** | PDF unique avec passphrase + QR code |

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        CLIENT                              │
│                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │   Passkey     │   │  PIN + LS    │   │  Passphrase   │  │
│  │ (biométrie)  │   │  (repli)     │   │  (initial /   │  │
│  │              │   │              │   │  récupération)│  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬────────┘  │
│         │                  │                   │           │
│         ▼                  ▼                   ▼           │
│   Déverrouille la     Déchiffre la       Argon2id        │
│   clé locale chiffrée clé locale chiffrée dérive la clé   │
│         │                  │                   │           │
│         └──────────────────┴───────────────────┘           │
│                            │                               │
│                  clé_chiffrement (bytes)                    │
│                            │                               │
│                     HTTPS POST /api/...                     │
│                    Authorization: Bearer                    │
│                    X-Encryption-Key: <clé>                  │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│                       SERVEUR                              │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Key store en mémoire : dict[user_id → (clé, expiry)]│  │
│  │  TTL = expiration JWT (24h) — purgé à la déco/restart │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │  Couche service : encrypt() / decrypt()              │  │
│  │  AES-256-GCM par champ, nonce unique                 │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │  SQLite : données stockées en base64(nonce+ct+tag)   │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Modifications du modèle de données

#### Nouvelles colonnes sur `User`

| Colonne | Type | Description |
|---|---|---|
| `encryption_salt` | `bytes` | Sel Argon2 (16 octets) |
| `challenge_blob` | `str` | base64(nonce + texte chiffré + tag) — pour la vérification de la clé |
| `argon2_params` | `str` | JSON : `{time_cost, memory_cost, parallelism}` |
| `is_encrypted` | `bool` | Indique si le chiffrement a été *configuré* pour le compte (passphrase définie) |
| `fields_encrypted` | `bool` | Indique si les données en base (mémos, noms de bénéficiaires) sont réellement chiffrées |

#### Nouvelle table `webauthn_credentials`

| Colonne | Type | Description |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → User | |
| `credential_id` | `bytes` | Identifiant WebAuthn |
| `public_key` | `bytes` | Clé publique COSE |
| `sign_count` | `int` | Compteur de signatures |
| `transports` | `str` | Tableau JSON des transports |
| `created_at` | `datetime` | |

### Nouveaux modules

| Module | Rôle |
|---|---|
| `budgie/services/crypto.py` | `encrypt(plaintext, key)` / `decrypt(ciphertext, key)` — AES-256-GCM |
| `budgie/api/webauthn.py` | Endpoints WebAuthn (enregistrement & connexion) |
| `budgie/models/webauthn.py` | Modèle ORM `WebAuthnCredential` |
| `budgie/schemas/webauthn.py` | Schémas Pydantic WebAuthn |
| `frontend/src/composables/usePinStorage.ts` | Chiffrement PIN, stockage clé localStorage |
| `frontend/src/composables/useWebAuthn.ts` | Wrapper `navigator.credentials` |

### Flux de chiffrement

1. **Inscription** : l'utilisateur crée username + mot de passe + passphrase → Argon2id dérive la clé → challenge blob créé → document PDF de récupération généré.
2. **Connexion quotidienne (Passkey)** : authentification biométrique → obtention du JWT → la clé de chiffrement est déverrouillée séparément via PIN ou passphrase sur l'écran de déverrouillage.
3. **Connexion quotidienne (PIN)** : PIN saisi → PBKDF2 dérive la clé d'encapsulation → déchiffre la clé depuis `localStorage` → clé envoyée au serveur.
4. **Connexion de secours (passphrase)** : l'utilisateur saisit la passphrase → Argon2id redérive la clé → clé envoyée au serveur.
5. **Accès aux données** : la couche service déchiffre en RAM avec la clé de session → sert le texte clair via l'API → le client affiche normalement.
6. **Écriture de données** : la couche service chiffre chaque champ avec un nonce unique → stocke le blob base64 dans SQLite.
7. **Déconnexion / expiration du token** : clé purgée du store en mémoire.

### Migration des comptes existants

Les comptes créés avant la Phase 9 ont leurs données stockées en clair (`is_encrypted = False`). La migration est transparente et progressive.

#### Migration Alembic
- Les colonnes typées des champs à chiffrer sont remplacées par des colonnes `Text` (compatibles avec le texte clair et les blobs base64).
- Le flag `is_encrypted` est ajouté sur `User` (défaut `False`).

#### À la prochaine connexion
Les utilisateurs dont `is_encrypted = False` sont redirigés vers un écran unique **« Configurer votre passphrase »** :
1. L'utilisateur choisit sa passphrase.
2. Argon2id dérive la clé de chiffrement.
3. Le challenge blob est créé et stocké.
4. Le PDF de récupération est généré et téléchargé.
5. (Optionnel) Enregistrement d'une Passkey proposé immédiatement.

#### Migration one-shot des données
Une fois la passphrase validée, le serveur :
1. Lit toutes les données de l'utilisateur (en clair, déjà en RAM).
2. Chiffre chaque champ avec la nouvelle clé.
3. Enregistre tout dans une **transaction SQLite unique** — rollback en cas d'erreur.
4. Met `fields_encrypted = True` (et `is_encrypted = True` si ce n'était pas encore le cas).

#### Code de transition
Pendant le déploiement progressif, la couche service gère les deux états via le fallback de déchiffrement :

```python
# crypto.decrypt_str retourne la valeur brute si le déchiffrement échoue,
# gérant ainsi de façon transparente les lignes pas encore migrées.
memo = crypto.decrypt_str(txn.memo, session_key)
```

Le flag `fields_encrypted` permet à `/unlock` de détecter les comptes pour lesquels `is_encrypted=True`
a été écrit par une ancienne version du serveur qui n'avait jamais chiffré les données en base, et
de déclencher la migration de façon transparente au prochain déverrouillage.

#### Passkeys optionnelles
Les Passkeys ne sont jamais obligatoires. Un utilisateur migré peut toujours s'authentifier avec mot de passe + passphrase. Passkeys et PIN sont uniquement des couches de confort.

### Mesures de sécurité

| Menace | Atténuation |
|---|---|
| Interception de la clé en transit | HTTPS obligatoire (TLS 1.2+) |
| Clé sur disque | Jamais écrite sur disque — RAM uniquement, purgée à la déconnexion/redémarrage |
| Force brute du PIN | 5 tentatives échouées → purge de la clé locale |
| Dump de la mémoire serveur | Clé présente uniquement pendant la session active ; `mlock` recommandé en production |
| Vol de la base de données | Toutes les données sont chiffrées AES-256-GCM — inutilisables sans la clé |
| Passphrase perdue | Données irrécupérables par conception — le document PDF de récupération atténue ce risque |
| Attaques par rejeu | Nonce AES-GCM unique par chiffrement — aucune réutilisation de nonce |
