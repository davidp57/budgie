# Budgie 🐦 — Référence Technique

## Table des matières

1. [Structure du projet](#structure-du-projet)
2. [Stack technique](#stack-technique)
3. [Mise en place du développement](#mise-en-place-du-développement)
4. [Architecture](#architecture)
5. [Référence API](#référence-api)
6. [Pipeline d'import](#pipeline-dimport)
7. [Moteur de catégorisation](#moteur-de-catégorisation)
8. [Moteur de budget](#moteur-de-budget)
9. [Transactions virtuelles](#transactions-virtuelles)
10. [Composants & Stores frontend](#composants--stores-frontend)
11. [Tests](#tests)
12. [Qualité du code](#qualité-du-code)
13. [Docker & Déploiement](#docker--déploiement)
14. [Configuration](#configuration)

---

## Structure du projet

```
budgetizer/
├── budgie/                      # Package Python backend
│   ├── api/                     # Routeurs FastAPI (minces — délèguent aux services)
│   │   ├── accounts.py
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categories.py
│   │   ├── category_groups.py
│   │   ├── category_rules.py
│   │   ├── categorize.py
│   │   ├── envelopes.py
│   │   ├── imports.py
│   │   ├── payees.py
│   │   └── transactions.py
│   ├── importers/               # Parseurs de fichiers bancaires
│   │   ├── base.py              # ImportedTransaction + ABC BaseImporter
│   │   ├── csv_importer.py      # Détection auto séparateur, décimal, colonnes
│   │   ├── excel_importer.py
│   │   ├── qif_importer.py      # via quiffen
│   │   └── ofx_importer.py      # ElementTree, FITID → import_hash
│   ├── models/                  # Modèles ORM SQLAlchemy
│   ├── schemas/                 # Schémas Pydantic requête/réponse
│   ├── services/                # Toute la logique métier
│   │   ├── budget.py
│   │   ├── categorizer.py
│   │   ├── envelope.py
│   │   ├── importer.py
│   │   └── transaction.py
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # Moteur SQLAlchemy async + fabrique de sessions
│   └── main.py                  # App FastAPI, lifespan, fallback SPA
├── alembic/                     # Migrations base de données
│   └── versions/
├── frontend/                    # SPA Vue.js 3
│   ├── src/
│   │   ├── api/                 # Wrappers HTTP typés (axios)
│   │   │   ├── client.ts        # Instance Axios, intercepteur JWT, toasts d'erreur
│   │   │   ├── types.ts         # Interfaces TypeScript partagées
│   │   │   ├── accounts.ts
│   │   │   ├── categories.ts
│   │   │   ├── envelopes.ts
│   │   │   ├── imports.ts
│   │   │   └── transactions.ts
│   │   ├── components/
│   │   │   ├── CategoryPicker.vue
│   │   │   ├── CreateCategoryModal.vue
│   │   │   ├── EnvelopeCard.vue
│   │   │   ├── EnvelopeManager.vue
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
│   ├── USER.md           # Guide utilisateur (EN)
│   ├── UTILISATEUR.md    # Guide utilisateur (FR)
│   ├── TECHNICAL.md      # Référence technique (EN)
│   └── TECHNIQUE.md      # Ce fichier
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Stack technique

| Couche | Choix | Notes |
|---|---|---|
| Langage backend | Python 3.12+ | |
| Framework web | FastAPI | Async, docs OpenAPI auto à `/docs` |
| ORM | SQLAlchemy 2.0 (async) | Toutes les requêtes via `AsyncSession` |
| Migrations | Alembic | Exécutées auto au démarrage via lifespan |
| Base de données | SQLite | `data/budgie.db`, montants en centimes entiers |
| Framework frontend | Vue.js 3 | Composition API, `<script setup lang="ts">` |
| Outil de build | Vite 7 | Proxy dev `/api` → `:8000` |
| CSS | Tailwind CSS + DaisyUI 5 | Thèmes : `emerald` (clair), `night` (sombre) |
| État | Pinia | Store `auth` + store `toast` |
| Client HTTP | Axios | Intercepteurs JWT + toast d'erreur |
| Auth | JWT + bcrypt | Token 24 h, `localStorage` |
| Conteneurisation | Docker Compose | Build multi-stage, port 8080 |
| Tests backend | pytest + pytest-asyncio | 159 tests |
| Tests frontend | Vitest + Vue Test Utils | 39 tests (4 store, 35 composants) |
| Linting | ruff (Python), ESLint (TS) | Politique zéro avertissement |
| Typage | mypy (Python), tsc (TS) | Strict, zéro erreur |
| Formatage | ruff format (Python), Prettier (TS) | |

**Invariant clé** : tous les montants monétaires sont stockés et calculés en **centimes entiers** (ex. `5050` = 50,50 €). Les flottants ne sont jamais utilisés pour l'argent.

---

## Mise en place du développement

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

API : `http://localhost:8000/api`  
Docs OpenAPI : `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite proxifie toutes les requêtes `/api/*` vers `http://localhost:8000`.

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

---

## Architecture

### Couches backend

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

Les routes doivent rester minces. Toute la logique appartient aux `services/`.

### Flux d'authentification

1. `POST /api/auth/login` → `{ access_token, token_type }`
2. Le frontend stocke le token dans `localStorage`
3. Intercepteur de requête Axios : `Authorization: Bearer <token>` sur chaque requête
4. Dépendance FastAPI `get_current_user` : décode le JWT, charge l'utilisateur depuis la DB
5. Sur 401 : l'intercepteur de réponse Axios efface le token, redirige vers `/login`

### Service du SPA en production

`budgie/main.py` monte `frontend/dist/assets/` sous `/assets` et enregistre une route catch-all `GET /{full_path:path}` retournant `frontend/dist/index.html`. Activé uniquement quand `frontend/dist/` existe (i.e. dans un build Docker).

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

Gestion des erreurs : l'intercepteur de réponse Axios déclenche `useToastStore().error(message)` pour toutes les erreurs non-401 (sauf 422 et 409, gérées localement par les vues).

---

## Référence API

Tous les endpoints nécessitent `Authorization: Bearer <token>` sauf `/api/auth/*`.

### Auth

| Méthode | Chemin | Corps / Params | Retourne |
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
| `GET` | `/api/transactions` | `account_id`, `is_virtual` (bool) |
| `POST` | `/api/transactions` | — |
| `PUT` | `/api/transactions/{id}` | — |
| `DELETE` | `/api/transactions/{id}` | — |
| `GET` | `/api/transactions/virtual/unlinked` | Prévisions en attente |
| `POST` | `/api/transactions/virtual/match` | `{transaction_id, virtual_id}` |

> **Ordre des routes** : `/virtual/unlinked` doit être déclaré **avant** `/{id}` dans le routeur pour éviter que la chaîne littérale `virtual` soit interprétée comme un identifiant entier.

### Budget

| Méthode | Chemin | Notes |
|---|---|---|
| `GET` | `/api/budget/{month}` | Format `month` : `AAAA-MM` |
| `PUT` | `/api/budget/{month}` | Upsert des allocations |

### Import

| Méthode | Chemin | Notes |
|---|---|---|
| `POST` | `/api/imports/parse` | `multipart/form-data` ; retourne la liste de prévisualisation |
| `POST` | `/api/imports/confirm` | Corps JSON ; persiste les transactions |

### Catégorisation

| Méthode | Chemin | Notes |
|---|---|---|
| `POST` | `/api/categorize` | Catégoriser par lot une liste de transactions |
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
| `GET` | `/api/envelopes` | Lister toutes les enveloppes avec leurs catégories affectées |
| `POST` | `/api/envelopes` | Créer une enveloppe `{name, rollover?, category_ids?}` |
| `PUT` | `/api/envelopes/{id}` | Mettre à jour le nom, le flag rollover ou les catégories affectées |
| `DELETE` | `/api/envelopes/{id}` | Supprimer l'enveloppe et ses allocations de budget |

---

## Pipeline d'import

### Parseurs (`budgie/importers/`)

| Format | Classe | Détails |
|---|---|---|
| CSV | `CsvImporter` | Détection auto du séparateur (`;`, `,`, `\t`), du séparateur décimal (`.`, `,`), des noms de colonnes depuis des listes candidates (`_DATE_CANDIDATES`, `_DESC_CANDIDATES`, etc.) |
| Excel | `ExcelImporter` | Même détection de colonnes que CSV, via `openpyxl` |
| QIF | `QifImporter` | Via la bibliothèque `quiffen` |
| OFX | `OfxImporter` | Parsing ElementTree (pas de schéma OFX strict), FITID utilisé comme `import_hash` |

Tous les parseurs étendent `BaseImporter` et produisent `list[ImportedTransaction]`.

### Hash d'import

```python
import_hash = sha256(f"{date}{amount_centimes}{description}{reference}".encode()).hexdigest()
```

Pour OFX : `import_hash = sha256(fitid.encode()).hexdigest()`

Stocké sur le modèle `Transaction`. Contrainte `UNIQUE` pour garantir l'idempotence des imports.

### Confirmation de l'import (`services/importer.py`)

1. Pour chaque `ImportedTransaction` du payload :
   - Ignorer si `import_hash` déjà en base
   - Insérer la ligne `Transaction`
   - Si `virtual_linked_id` est défini : charger la transaction virtuelle, définir son `cleared = "reconciled"`
2. Commit unique à la fin.

### Note sur le téléversement de fichiers

Lors de l'appel à `POST /api/imports/parse` depuis le frontend, Axios ne doit **pas** définir `Content-Type: application/json` — le navigateur définit automatiquement `multipart/form-data` avec le boundary. Surcharger avec `{ headers: { 'Content-Type': undefined } }`.

---

## Moteur de catégorisation

Point d'entrée : `services/categorizer.py` → `categorize_transaction(session, user_id, txn)`

### Étape 1 — Correspondance bénéficiaire

```python
payee = await session.execute(
    select(Payee).where(Payee.user_id == user_id, func.lower(Payee.name) == func.lower(txn.payee))
)
if payee and payee.auto_category_id:
    return payee.auto_category_id, "auto"
```

### Étape 2 — Correspondance règle

Les règles sont évaluées triées par `priority DESC`. Pour chaque règle :

| `match_field` | `match_type` | Logique |
|---|---|---|
| `payee` / `memo` | `contains` | `field.lower() in pattern.lower()` |
| `payee` / `memo` | `exact` | `field.lower() == pattern.lower()` |
| `payee` / `memo` | `regex` | `re.search(pattern, field, re.IGNORECASE)` |

Retourne le `category_id` de la première correspondance et `confidence = "rule"`.

Retourne `(None, "none")` si aucune correspondance.

Après catégorisation, le bénéficiaire est mis à jour avec `auto_category_id` pour les prochaines recherches rapides.

---

## Moteur de budget

Point d'entrée : `services/budget.py` → `get_budget_month(session, user_id, month)`

### Calcul par enveloppe

La grille de budget est organisée par **enveloppes**. Chaque enveloppe agrège les transactions de toutes ses catégories affectées.

```
Pour chaque enveloppe :
  budgeted  = BudgetAllocation.budgeted WHERE envelope_id = X AND month = mois_cible
              (0 si aucune allocation)
  activity  = SUM(Transaction.amount) WHERE category_id IN envelope.category_ids
              AND month(date) = mois_cible
              AND user_id = utilisateur_courant    ← inclut is_virtual=True

  SI envelope.rollover :
    available = SUM(budgeted_m - activity_m) sur tous les mois m ≤ mois_cible
  SINON :
    available = budgeted + activity  (mois en cours uniquement ; activity est négatif pour les dépenses)
```

### Calcul global

```
income          = SUM(amount) WHERE amount > 0 AND month = mois_cible
total_budgeted  = SUM(BudgetAllocation.budgeted) WHERE month = mois_cible
to_be_budgeted  = income - total_budgeted
```

**Invariant clé** : les transactions `is_virtual=True` affectent `activity` (et donc `available`) mais sont exclues des calculs de solde des comptes réels.

---

## Transactions virtuelles

### Modèle DB

Table `Transaction`, colonnes :
- `is_virtual: bool` — `True` pour les prévisions
- `virtual_linked_id: int | None` — FK vers la transaction virtuelle qu'une transaction réelle « réalise »
- `cleared: str | None` — défini à `"reconciled"` quand la transaction virtuelle est liée

### Couche service (`services/transaction.py`)

```python
async def get_virtual_unlinked(session, user_id) -> list[Transaction]:
    """Retourne les transactions virtuelles pas encore réconciliées."""

async def link_virtual(session, transaction_id, virtual_id, user_id):
    """Lie une txn réelle à une virtuelle ; marque la virtuelle comme réconciliée."""
```

### Algorithme de correspondance frontend (`ImportView.vue`)

Pour chaque transaction importée (non confirmée), score par rapport à chaque transaction virtuelle non liée :

```
amount_match = abs(importée.montant - virtuelle.montant) / abs(virtuelle.montant) <= 0.10
date_match   = abs((importée.date - virtuelle.date).jours) <= 60
suggestion   = amount_match ET date_match
```

Si une correspondance est acceptée, `virtual_linked_id` est défini sur l'`ImportedTransaction` avant l'appel à `POST /api/imports/confirm`.

---

## Composants & Stores frontend

### Composants

| Composant | Props | Émet | Notes |
|---|---|---|---|
| `TransactionRow` | `txn: Transaction`, `groups: CategoryGroupWithCategories[]` | `category-saved({id, category_id})`, `error(string)`, `category-created(Category)` | `<tr>` autonome ; gère son propre état d'édition ; transmet les nouvelles catégories au parent |
| `CategoryPicker` | `modelValue: number\|null`, `groups` | `update:modelValue`, `category-created(Category)` | Combobox avec recherche ; ouvre `CreateCategoryModal` quand l'utilisateur saisit un nouveau nom |
| `CreateCategoryModal` | `initialName?: string`, `groups` | `created(Category)`, `close` | Modale de création de catégorie inline |
| `EnvelopeCard` | `envelope: EnvelopeLine` | `edit-budgeted(envelope_id, centimes)` | Cellule de la grille budget ; affiche le nom de l'enveloppe, les chips de catégories, le badge rollover |
| `EnvelopeManager` | `groups: CategoryGroupWithCategories[]` | — | Panneau paramètres — CRUD complet des enveloppes avec formulaires d'édition inline |
| `FileUploader` | — | `file-selected(File)` | Glisser-déposer + clic |
| `MonthPicker` | `modelValue: string` (AAAA-MM) | `update:modelValue` | |
| `SkeletonRow` | `rows?: number` (défaut 5), `cols?: number` (défaut 5) | — | `<tr>` placeholder de chargement |
| `ToastContainer` | — | — | Lit `useToastStore()`, position fixe bas-droite |

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
Auto-dismiss via `setTimeout`. Durée par défaut : 4000 ms.

### Composables

**`src/composables/useTheme.ts`**

Singleton de niveau module `ref<'emerald'|'night'>`. Au premier appel :
1. Lit `localStorage.getItem('theme')`
2. Se rabat sur `window.matchMedia('(prefers-color-scheme: dark)')`
3. Applique `document.documentElement.setAttribute('data-theme', theme)`

`toggleTheme()` bascule entre `emerald` et `night`, persiste dans `localStorage`.

### Client Axios (`src/api/client.ts`)

**Intercepteur de requête** : attache `Authorization: Bearer <token>` si le token existe dans le store auth.

**Intercepteur de réponse** :
- 401 : efface le token + redirige vers `/login`
- Autres erreurs (sauf 422, 409) : `useToastStore().error(extractMessage(error))`

---

## Tests

### Backend (pytest)

```bash
poetry run pytest                       # 159 tests
poetry run pytest --cov=budgie          # avec rapport de couverture
poetry run pytest -x                    # s'arrête au premier échec
poetry run pytest tests/test_api/       # couche API
poetry run pytest tests/test_services/  # couche service
poetry run pytest tests/test_importers/ # parseurs
```

**`tests/conftest.py`** fournit :
- Fixture `engine` : DB `aiosqlite` en mémoire, schéma créé fresh par test
- Fixture `session` : `AsyncSession` scopée par test
- Fixture `client` : `httpx.AsyncClient` contre l'app FastAPI
- Fixture `auth_client` : utilisateur pré-inscrit + en-tête `Authorization` défini

Les fichiers de test reflètent la source : `budgie/services/budget.py` → `tests/test_services/test_budget.py`.

### Frontend (Vitest)

```bash
cd frontend
npm run test:unit -- --run    # passage unique (CI)
npm run test:unit             # mode watch
```

Tests dans `src/components/__tests__/*.spec.ts` avec Vue Test Utils `mount()` et `flushPromises()`.

| Fichier spec | Tests | Couverture |
|---|---|---|
| `EnvelopeCard.spec.ts` | 7 | Rendu, badge rollover, couleur disponible, édition budget en ligne |
| `EnvelopeManager.spec.ts` | 11 | Liste, état vide, création, édition, annulation, suppression |
| `MonthPicker.spec.ts` | 5 | Navigation, passage de mois |
| `TransactionRow.spec.ts` | 12 | Rendu, couleur montant, nom catégorie, flux d'édition, émissions |

Les tests de store sont dans `src/stores/__tests__/auth.test.ts` (4 tests).

---

## Qualité du code

### Python

```bash
poetry run ruff check budgie/ tests/    # lint (zéro avertissement)
poetry run ruff format budgie/ tests/   # formatage
poetry run mypy budgie/ tests/          # typage (zéro erreur, 73 fichiers source)
```

Règles :
- Docstrings style Google sur toutes les fonctions, classes, modules publics
- Annotations de type complètes sur toutes les fonctions
- Les commentaires `# noqa` doivent être justifiés ; les entrées `noqa` inutilisées sont des erreurs

### TypeScript / Vue

```bash
cd frontend
npx tsc --noEmit     # vérification des types stricte
npm run lint         # ESLint
```

Règles :
- `<script setup lang="ts">` sur chaque composant
- Tous les appels API dans les modules `src/api/` — jamais en ligne dans les composants ou stores
- Classes de composants DaisyUI préférées au CSS personnalisé
- Pas de types `any`

---

## Docker & Déploiement

### Dockerfile multi-stage

**Stage 1** (`node:22-alpine`) :
```dockerfile
COPY frontend/ .
RUN npm ci && npm run build
```

**Stage 2** (`python:3.12-slim`) :
```dockerfile
COPY --from=0 /app/frontend/dist ./frontend/dist
COPY budgie/ pyproject.toml ...
RUN pip install poetry && poetry install --only main
USER budgie
CMD ["uvicorn", "budgie.main:app", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/api/health
```

Le conteneur expose le port 8000 ; `docker-compose.yml` le mappe sur le port hôte **8080**.

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

### Commandes

```bash
docker compose up --build    # build + démarrage
docker compose up -d         # détaché
docker compose logs -f       # suivre les logs
docker compose down          # arrêter
docker compose exec app poetry run alembic history   # vérifier les migrations
```

### Déploiement sur NAS Synology

1. `git clone` ou SCP du projet sur le NAS
2. Créer `.env` avec un `SECRET_KEY` approprié
3. `docker compose up -d`
4. DSM Synology → Panneau de configuration → Portail de connexion → Avancé → Proxy inverse :
   - Source : `budget.votredomaine.com` HTTPS 443
   - Destination : `localhost` 8080
   - Activer les en-têtes WebSocket

---

## Configuration

Tous les paramètres chargés par `budgie/config.py` (Pydantic `BaseSettings`) depuis l'environnement / `.env`.

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///data/budgie.db` | URL SQLAlchemy async |
| `SECRET_KEY` | `change-me-in-production` | Clé de signature HMAC JWT — **à changer impérativement** |
| `ALGORITHM` | `HS256` | Algorithme JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Durée du token (24 h) |
| `UPLOAD_DIR` | `data/uploads` | Répertoire temporaire pour les fichiers téléversés |
| `HOST` | `0.0.0.0` | Hôte de liaison Uvicorn |
| `PORT` | `8000` | Port de liaison Uvicorn |
| `DEBUG` | `false` | Mode debug FastAPI |

Copier `.env.example` → `.env` et définir `SECRET_KEY` avec une chaîne aléatoire cryptographiquement sûre de 32+ caractères avant le premier démarrage.
