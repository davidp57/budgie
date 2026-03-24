# Budgie 🐦 — Plan du projet

🌐 [English version](../en/plan.md)

---

## Vue d'ensemble

Application web de gestion de budget personnel pour un ménage.
Import de transactions bancaires, catégorisation automatique, gestion d'enveloppes budgétaires, prévision d'achats futurs via transactions virtuelles.

---

## Stack

| Couche | Choix |
|---|---|
| Nom | **Budgie** 🐦 |
| Backend | Python 3.12+, FastAPI, Poetry |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Base de données | SQLite (montants en centimes entiers) |
| Frontend | Vue.js 3, Composition API, TypeScript, Vite |
| CSS | DaisyUI (Tailwind CSS) |
| Auth | JWT + bcrypt + WebAuthn (Passkeys) |
| Chiffrement | AES-256-GCM, Argon2 (dérivation de clé) |
| Import | CSV, Excel, QIF, OFX |
| Catégorisation | Règles + historique bénéficiaires (MVP) |
| Déploiement | Docker Compose sur NAS Synology |
| Tests | pytest + pytest-asyncio, Vitest |
| Linting | ruff, mypy, ESLint, Prettier |

---

## Phase 0 — Fondations

### 0.1 — Initialisation du projet Poetry

- [x] Initialiser le projet Poetry à la racine du dépôt
- [x] `pyproject.toml` avec métadonnées, Python >=3.12
- [x] Dépendances runtime : `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `pydantic-settings`, `python-multipart`, `bcrypt`, `python-jose[cryptography]`
- [x] Dépendances d'import : `pandas`, `openpyxl`, `quiffen`, `ofxtools`
- [x] Dépendances dev : `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pytest-cov`

### 0.2 — Structure du projet backend

- [x] Créer le package `budgie/` avec `__init__.py`
- [x] Créer les sous-packages : `models/`, `schemas/`, `api/`, `services/`, `importers/`
- [x] Créer `budgie/config.py` — `BaseSettings` Pydantic chargé depuis `.env`
- [x] Créer `budgie/database.py` — moteur SQLAlchemy async + fabrique de sessions
- [x] Créer `budgie/main.py` — app FastAPI avec CORS, montage des routeurs, health check
- [x] Créer `.env.example` avec toutes les variables de configuration
- [x] Créer `tests/conftest.py` avec fixtures async (DB de test, client de test)

### 0.3 — Initialisation du projet frontend

- [x] Initialiser le projet Vue.js 3 dans `frontend/` via `create-vue` (Vite + TS + Router + Pinia)
- [x] Installer DaisyUI + Tailwind CSS
- [x] Installer axios
- [x] Configurer le proxy Vite pour transmettre `/api` au serveur FastAPI de dev
- [x] Configurer ESLint + Prettier

### 0.4 — Outillage & CI

- [x] Configurer `ruff` dans `pyproject.toml` (règles de lint et de formatage)
- [x] Configurer `mypy` dans `pyproject.toml` (mode strict)
- [x] Paramètres VS Code : intégration ruff, mypy, Pylance, ESLint
- [x] Créer `.gitignore` (Python, Node, data/, .env, `__pycache__`, etc.)

### 0.5 — Docker

- [x] `Dockerfile` — multi-stage : (1) build Vue → fichiers statiques, (2) runtime Python slim
- [x] `docker-compose.yml` — service unique, volume pour `data/`, port 8080, health check, `mem_limit: 256m`, `restart: unless-stopped`
- [x] `entrypoint.sh` — support PUID/PGID (pattern LinuxServer.io) via `gosu` pour les permissions de bind-mount Synology
- [x] `scripts/backup.sh` — sauvegarde SQLite horodatée avec rétention configurable (7 jours par défaut)

---

## Phase 1 — Modèle de données

### 1.1 — Modèles SQLAlchemy

Tous les montants en **centimes entiers** (ex : `1050` = 10,50 €).

- [x] `User` — `id`, `username` (unique), `hashed_password`, `created_at`
- [x] `Account` — `id`, `user_id`, `name`, `type` (checking/savings/credit/cash), `on_budget`, `created_at`
- [x] `CategoryGroup` — `id`, `user_id`, `name`, `sort_order`
- [x] `Category` — `id`, `group_id`, `name`, `sort_order`, `hidden`
- [x] `Payee` — `id`, `user_id`, `name`, `auto_category_id` (FK nullable → Category)
- [x] `Transaction` — `id`, `account_id`, `date`, `payee_id`, `category_id`, `amount` (centimes), `memo`, `cleared` (enum : uncleared/cleared/reconciled), `is_virtual`, `virtual_linked_id` (FK nullable → Transaction), `import_hash` (unique nullable), `created_at`
- [x] `SplitTransaction` — `id`, `parent_id` (FK → Transaction), `category_id`, `amount`, `memo`
- [x] `BudgetAllocation` — `id`, `category_id`, `month` (YYYY-MM), `budgeted` (centimes). Contrainte unique sur `(category_id, month)`
- [x] `CategoryRule` — `id`, `user_id`, `pattern`, `match_field` (payee/memo), `match_type` (contains/exact/regex), `category_id`, `priority`

### 1.2 — Schémas Pydantic

- [x] Schémas requête/réponse pour chaque modèle
- [x] Règles de validation (montant > 0 pour les budgets, formats de date, etc.)

### 1.3 — Configuration Alembic

- [x] `alembic init` avec configuration async
- [x] Générer la migration initiale depuis les modèles
- [x] Exécution automatique des migrations au démarrage (mode dev)

---

## Phase 2 — Auth & API de base

### 2.1 — Authentification

- [x] `POST /api/auth/register` — premier utilisateur uniquement (ou inscription ouverte, à définir)
- [x] `POST /api/auth/login` — retourne un token JWT d'accès
- [x] Middleware de vérification JWT / dépendance `get_current_user`
- [x] Hachage du mot de passe avec bcrypt

### 2.2 — Endpoints CRUD

- [x] `GET/POST /api/accounts`, `GET/PUT/DELETE /api/accounts/{id}`
- [x] `GET/POST /api/category-groups` (avec catégories imbriquées)
- [x] `GET/POST /api/categories`, `PUT/DELETE /api/categories/{id}`
- [x] `GET/POST /api/payees`
- [x] `GET/POST /api/transactions` (avec filtres : compte, catégorie, dates, virtuel)
- [x] `PUT/DELETE /api/transactions/{id}`
- [x] `GET/PUT /api/budget/{month}` — vue mensuelle des enveloppes

---

## Phase 3 — Import de transactions bancaires

### 3.1 — Parseurs

Chaque parseur implémente `BaseImporter` avec `parse(file) → list[ImportedTransaction]`.

- [x] Schéma Pydantic `ImportedTransaction` : `date`, `amount`, `description`, `payee_name`, `reference`, `import_hash`
- [x] `BaseImporter` — interface abstraite dans `budgie/importers/base.py`
- [x] `CsvImporter` — mapping de colonnes configurable, détection d'encodage, support décimales françaises
- [x] `ExcelImporter` — via `pandas.read_excel()` + `openpyxl` ; supporte `header=None` pour l'indexation positionnelle
- [x] `QifImporter` — via `quiffen`
- [x] `OfxImporter` — via `ofxtools`, utilise FITID comme `import_hash` ; parsing ElementTree (pas de schéma strict)

### 3.2 — Flux d'import

- [x] `POST /api/imports/parse` — upload fichier + format → retourne les transactions parsées (aperçu)
- [x] `POST /api/imports/confirm` — reçoit les transactions validées (avec catégories assignées) → insère en DB
- [x] Déduplication par `import_hash` — avertit si les transactions existent déjà

---

## Phase 4 — Catégorisation

### 4.1 — Moteur de catégorisation

- [x] Étape 1 : correspondance exacte du bénéficiaire (insensible à la casse) → `Payee.auto_category_id`
- [x] Étape 2 : évaluation des lignes `CategoryRule` triées par priorité DESC (`contains` / `exact` / `regex` sur le champ `payee` ou `memo`)
- [x] Retourne `category_id` + `confidence` (`"auto"` / `"rule"` / `"none"`)
- [x] `POST /api/categorize` — endpoint de catégorisation en lot
- [x] `GET/POST/PUT/DELETE /api/category-rules` — CRUD des CategoryRule

### 4.2 — Apprentissage passif

- [ ] Lors d'une catégorisation manuelle, proposer la mise à jour de `Payee.auto_category_id`
- [ ] Proposer la création d'une `CategoryRule` depuis des affectations manuelles répétées
- [ ] Suivre les métriques de précision de la catégorisation (optionnel)

---

## Phase 5 — Moteur de budget

### 5.1 — Calculs d'enveloppes

- [x] `get_month_budget_view(month)` — pour chaque catégorie :
  - `budgeted` : montant de `BudgetAllocation` pour ce mois
  - `activity` : somme des transactions (incl. virtuelles) pour ce mois dans cette catégorie
  - `available` : somme cumulative (`Σ budgeted − Σ dépenses` sur tous les mois ≤ courant)
- [x] `get_to_be_budgeted(month)` — revenus perçus − total budgétisé. Objectif = 0
- [x] Les transactions virtuelles (`is_virtual=True`) réduisent le `available` des enveloppes mais PAS le solde réel du compte

### 5.2 — Endpoint API

- [x] `GET /api/budget/{month}` — retourne la vue mensuelle complète avec toutes les enveloppes + `to_be_budgeted`

---

## Phase 6 — Frontend

### 6.1 — Setup de base

- [x] Module client API (`src/api/client.ts`) — instance axios avec intercepteur JWT
- [x] Store auth (Pinia) + page de connexion (`LoginView.vue`)
- [x] Layout de l'application : sidebar/navbar, menu responsive (drawer DaisyUI)
- [x] Vue Router avec garde d'authentification

### 6.2 — Vues principales

- [x] **Dashboard** (`DashboardView.vue`) — résumé mensuel, soldes des comptes, alertes (enveloppes négatives), transactions récentes
- [x] **Transactions** (`TransactionsView.vue`) — tableau paginé, filtres (compte, catégorie, plage de dates, virtuel/réel), édition de catégorie inline
- [x] **Budget** (`BudgetView.vue`) — grille mensuelle, montants `budgeted` éditables, affichage `activity`/`available` avec code couleur, navigation par mois, barre "à budgétiser"
- [x] **Import** (`ImportView.vue`) — upload de fichier (glisser-déposer), sélection du format, aperçu des transactions parsées, suggestions de catégories, confirmer/ignorer par ligne, indicateur de doublon
- [x] **Paramètres** (`SettingsView.vue`) — CRUD comptes, CRUD groupes/catégories, CRUD règles de catégorisation, changement de mot de passe

### 6.3 — Composants réutilisables

- [x] `EnvelopeCard.vue` — affichage d'une enveloppe avec budget/activité/disponible
- [x] `TransactionRow.vue` — transaction unique avec édition inline
- [x] `CategoryPicker.vue` — liste déroulante avec catégories groupées
- [x] `FileUploader.vue` — upload de fichier par glisser-déposer
- [x] `MonthPicker.vue` — navigation mensuelle (précédent/suivant/courant)

---

## Phase 7 — Transactions virtuelles

- [x] Formulaire de création : bascule "virtuel" sur le formulaire de transaction, champs : montant, date estimée, catégorie, description
- [x] Liaison : à l'import, suggérer la correspondance avec les transactions virtuelles existantes (montant similaire + bénéficiaire + plage de dates). Virtuel lié → marqué `realized`, la transaction réelle reçoit `virtual_linked_id`
- [x] Affichage : transactions virtuelles avec style distinct (bordure pointillée, icône prévision). Comptent dans le `available` des enveloppes mais pas dans le solde réel du compte

---

## Phase 8 — Finitions & Déploiement

- [x] Support thème sombre/clair (thèmes DaisyUI)
- [x] Manifest PWA pour l'installation mobile
- [x] Gestion d'erreurs : toasts globaux, intercepteur d'erreurs API
- [x] États de chargement : squelettes animés pour le chargement des données
- [x] Build et test Docker en local
- [x] Stratégie de sauvegarde pour le fichier SQLite (`scripts/backup.sh`)
- [x] Déploiement sur NAS Synology via Docker Compose
- [x] Configuration du proxy inverse Synology (HTTPS)

---

## Phase 9 — Sécurité & Chiffrement

### Vue d'ensemble

Toutes les données utilisateur sont chiffrées au repos avec **AES-256-GCM** et une clé dérivée de la passphrase utilisateur via **Argon2id**. La clé de chiffrement n'est **jamais stockée sur le serveur** — elle n'existe qu'en RAM le temps de la session authentifiée. L'authentification quotidienne utilise **WebAuthn (Passkeys)** pour le confort biométrique, avec un **PIN** en solution de repli.

**Approche** : Déchiffrement côté serveur — la clé dérivée est envoyée au serveur via HTTPS, conservée en mémoire pendant la session, et purgée à la déconnexion ou à l'expiration du token.

### 9.1 — Dérivation de la clé de chiffrement

- [ ] L'utilisateur choisit une **passphrase** (distincte du mot de passe de connexion) à la création du compte
- [ ] Dériver une clé de 256 bits via **Argon2id** (time_cost=3, memory_cost=65536, parallelism=4)
- [ ] Générer un **challenge blob** : chiffrer un sel aléatoire de 32 octets avec AES-256-GCM → stocker `(nonce, ciphertext, tag, salt)` sur le serveur
- [ ] Vérification de la clé : déchiffrer le challenge blob — si le tag GCM valide, la clé est correcte
- [ ] Stocker les **paramètres Argon2** (sel, time_cost, memory_cost, parallelism) dans la table `users` — jamais la clé elle-même
- [ ] Ajouter les colonnes `encryption_salt`, `challenge_blob`, `argon2_params` au modèle `User`
- [ ] Migration Alembic pour les nouvelles colonnes

### 9.2 — WebAuthn / Passkeys : inscription & connexion

- [ ] Backend : intégrer la bibliothèque `py_webauthn`
- [ ] `POST /api/auth/webauthn/register/begin` — générer les options d'inscription (challenge, infos RP)
- [ ] `POST /api/auth/webauthn/register/complete` — vérifier l'attestation, stocker le credential en DB
- [ ] `POST /api/auth/webauthn/login/begin` — générer les options d'authentification
- [ ] `POST /api/auth/webauthn/login/complete` — vérifier l'assertion, retourner le JWT
- [ ] Nouveau modèle `WebAuthnCredential` : `id`, `user_id`, `credential_id`, `public_key`, `sign_count`, `transports`, `created_at`
- [ ] Frontend : API `navigator.credentials.create()` / `navigator.credentials.get()`
- [ ] Stocker la clé de chiffrement chiffrée dans **IndexedDB** sur l'appareil, déverrouillée par une Passkey réussie
- [ ] Migration Alembic pour la table `webauthn_credentials`

### 9.3 — Stockage local de la clé par PIN

- [ ] L'utilisateur définit un **PIN de 4 à 6 chiffres** sur l'appareil
- [ ] Dériver une clé d'enveloppe depuis le PIN via **PBKDF2** (100 000 itérations, sel spécifique à l'appareil)
- [ ] Chiffrer la clé de chiffrement avec la clé d'enveloppe → stocker dans **IndexedDB**
- [ ] À la saisie du PIN : dériver la clé d'enveloppe, déchiffrer la clé de chiffrement, envoyer au serveur
- [ ] **5 tentatives PIN échouées** → purger le stockage local de la clé (l'utilisateur doit ressaisir la passphrase)
- [ ] Le PIN est local à l'appareil — jamais envoyé ni stocké sur le serveur

### 9.4 — Service de chiffrement côté serveur

- [ ] `budgie/services/crypto.py` — `encrypt(plaintext, key)` / `decrypt(ciphertext, key)` via AES-256-GCM
- [ ] Chaque champ chiffré avec un **nonce aléatoire unique** (96 bits) — stocké avec le ciphertext
- [ ] Champs chiffrés stockés sous forme `base64(nonce + ciphertext + tag)` en DB
- [ ] Clé conservée uniquement en RAM serveur — associée à la session/JWT, **jamais écrite sur disque ni dans les logs**
- [ ] Clé purgée à : déconnexion, expiration du token, redémarrage du serveur
- [ ] Stockage en mémoire : `dict[user_id, bytes]` avec TTL correspondant à l'expiration JWT

### 9.5 — Chiffrement des données

Tous les champs de données utilisateur sont chiffrés. Cela inclut les montants (centimes), noms, mémos, dates — tout sauf les IDs structurels et les clés étrangères.

- [ ] Le chiffrement/déchiffrement se fait dans la **couche service** (transparent pour les routes API)
- [ ] Modèles chiffrés : `Account`, `Transaction`, `Category`, `CategoryGroup`, `Payee`, `CategoryRule`, `Envelope`, `BudgetAllocation`
- [ ] Champs chiffrés par modèle :
  - `Account` : `name`, `type`
  - `Transaction` : `date`, `amount`, `memo`, `cleared`, `import_hash`
  - `Category` : `name`
  - `CategoryGroup` : `name`
  - `Payee` : `name`
  - `CategoryRule` : `pattern`
  - `Envelope` : `name`, `emoji`
  - `BudgetAllocation` : `budgeted`, `month`
- [ ] Les agrégations SQL (moteur de budget) opèrent sur les **données déchiffrées en RAM** — pas de SUM SQL sur des colonnes chiffrées
- [ ] Migration Alembic : modifier les colonnes chiffrées de leur type natif vers `Text` (blobs base64)

### 9.6 — Réinitialisation du mot de passe & récupération de la clé

- [ ] **Réinitialisation du mot de passe** (connexion) : flux standard — ne touche PAS à la clé de chiffrement
- [ ] **Récupération de la clé de chiffrement** : l'utilisateur doit fournir la passphrase pour re-dériver la clé
- [ ] Si la passphrase est perdue → les données sont **irrécupérables** (par conception)
- [ ] Vérification du challenge blob : tenter de déchiffrer avec la clé candidate → tag GCM valide = clé correcte
- [ ] L'administrateur ne peut pas récupérer les données — seule la passphrase de l'utilisateur peut dériver la clé

### 9.7 — Document de récupération PDF

- [ ] Générer un PDF à la création du compte contenant :
  - La **passphrase** de l'utilisateur (en clair — imprimée une fois, jamais stockée)
  - Un **QR code** encodant la passphrase pour une resaisie rapide
  - Les 8 premiers caractères du hash de la clé dérivée (pour vérification sans révéler la clé)
  - Les instructions de récupération
- [ ] L'utilisateur est fortement invité à **imprimer et conserver** ce document en lieu sûr
- [ ] Génération PDF : bibliothèque `reportlab` ou `fpdf2`
- [ ] `GET /api/auth/recovery-document` — téléchargement du PDF (nécessite la passphrase courante)

### 9.8 — Migration des comptes existants

- [ ] Les utilisateurs existants (avant chiffrement) ont `is_encrypted = False` ; données en texte clair
- [ ] Migration Alembic : colonnes des champs chiffrés converties en type `Text`
- [ ] Migration Alembic : ajout de la colonne `is_encrypted` à `User` (défaut `False`)
- [ ] À la prochaine connexion : les utilisateurs avec `is_encrypted = False` sont redirigés vers l'écran **"Configurer votre passphrase"**
- [ ] Migration one-shot : le serveur lit toutes les données en clair, chiffre chaque champ dans une **unique transaction SQLite** (rollback en cas d'échec), passe `is_encrypted = True`
- [ ] Les Passkeys ne sont **jamais obligatoires** — mot de passe + passphrase fonctionne toujours en solution de repli

### 9.9 — Dépendances

- [ ] Backend : ajouter `py_webauthn`, `argon2-cffi`, `fpdf2` dans `pyproject.toml`
- [ ] Frontend : aucune dépendance supplémentaire (WebAuthn et IndexedDB sont natifs au navigateur)

---

## Stratégie de test

| Quoi | Comment | Où |
|---|---|---|
| Parseurs d'import | Tests unitaires avec fixtures | `tests/test_importers/` |
| Moteur de budget | Tests unitaires avec scénarios connus | `tests/test_services/` |
| Moteur de catégorisation | Tests unitaires avec règles + bénéficiaires | `tests/test_services/` |
| Routes API | Tests d'intégration via `httpx.AsyncClient` | `tests/test_api/` |
| Composants Vue | Tests de composants via Vitest + Vue Test Utils | `frontend/src/**/*.spec.ts` |
| Stores Pinia | Tests unitaires via Vitest | `frontend/src/**/*.spec.ts` |
| Flux complet | E2E : import → catégorisation → impact budget | `tests/test_services/` |
| Service de chiffrement | Tests unitaires : aller-retour chiffrement/déchiffrement, rejet mauvaise clé | `tests/test_services/` |
| Flux WebAuthn | Tests d'intégration avec credentials mockés | `tests/test_api/` |
| Dérivation de clé | Tests unitaires : params Argon2, challenge blob | `tests/test_services/` |

---

## Statut

- [x] Plan finalisé
- [x] Stack décidée
- [x] Instructions Copilot rédigées
- [x] Phase 0 — Fondations
- [x] Phase 1 — Modèle de données
- [x] Phase 2 — Auth & API
- [x] Phase 3 — Import
- [x] Phase 4 — Catégorisation
- [x] Phase 5 — Moteur de budget
- [x] Phase 6 — Frontend
- [x] Phase 7 — Transactions virtuelles
- [x] Phase 8 — Finitions & déploiement
- [ ] Phase 9 — Sécurité & Chiffrement
