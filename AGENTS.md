# Budgie

Ce fichier est la consigne de tout agent qui travaille dans le dépôt (Claude Code le lit par `CLAUDE.md`, qui l'importe ; Copilot, opencode et les autres le lisent directement).

Application web de budget personnel par enveloppes, auto-hébergée (Docker sur NAS Synology), PWA mobile-first.
Import des relevés bancaires (CSV, Excel, QIF, OFX), catégorisation automatique, transactions virtuelles (achats planifiés), chiffrement des libellés et des mémos.
Licence AGPL v3 (`LICENSE`), dépôt public : rien de personnel (relevé, montant réel, nom de commerçant tiré d'un vrai compte) dans un commit, un ticket ou une PR.
Le README présente l'application ; les guides utilisateur et développeur sont dans `docs/en/` et `docs/fr/`.

## Suivi : lots et tickets dans GitHub, comme IronGall

Le détail est dans [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md) et [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md).

- Le PRD de l'application est [#43](https://github.com/davidp57/budgie/issues/43) ; ses lots en sont les sous-tickets.
- Un **lot** est un ticket étiqueté `lot`, titré `<LOT-ID> — …` (`FEAT-…`, `FIX-…`, `CHORE-…`, `DOC-…`, `INVESTIGATE-…`), son PRD dans le corps, ses conditions de fin en cases à cocher.
- Ses **tickets** sont ses sous-tickets, étiquetés `ticket`, titrés `<LOT-ID> NN — …`, numérotés dans l'ordre des dépendances ; ils se découpent avant d'écrire du code, découpage soumis à David avant publication.
- Le **statut** est une étiquette : ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused. Fermé « completed » = ✅ done, fermé « not planned » = 🚫 won't fix.
  Un changement de statut se fait sur le ticket au moment où il arrive.
- La feuille de route (`docs/*/roadmap.md`) reste la vision publique ; un de ses items ne devient un lot qu'au moment où on le prend, et on coche l'item dans les deux langues quand le lot est livré.

## Branches et releases

- `develop` est la branche par défaut et reçoit le travail ; `main` ne reçoit que des releases.
- Un lot = une branche `feature/<LOT-ID>`, `fix/<LOT-ID>` ou `chore/<LOT-ID>` créée depuis `develop`, **une seule PR** vers `develop` pour tout le lot, qui ferme ses tickets et le lot (`Closes #…`).
- Une release se fait avec le skill **`release`** (`.claude/skills/release/SKILL.md`, `/release` dans Claude Code ; un autre agent le lit et le suit) : le numéro, l'entretien avec David, `RELEASE_NOTES.md` (titre `# Budgie — X.Y.Z`, pour les utilisateurs, en français puis en anglais, validé par David), `[Unreleased]` passé sous le numéro et rouvert vide, la version dans `pyproject.toml` (seule source : le frontend la lit sur `/api/health`), puis deux PR : `chore/RELEASE-X.Y.Z` → `develop`, et `develop` → `main` fusionnée par un commit de fusion après le feu vert de David.
  À cette fusion, `.github/workflows/docker.yml` construit et pousse l'image (`latest` et `X.Y.Z`), crée le tag `vX.Y.Z` et la release GitHub ; une fusion sans changement de version ne publie rien.
  `tests/test_changelog.py` garde `[Unreleased]`, l'entrée de la version et le titre des notes.
- La CI (`ci.yml`) tourne sur chaque PR et sur les poussées vers `develop` et `main`.
- Chaque fusion dans `develop` publie l'image `develop-latest` (et `develop-<sha>`), que l'instance de développement du VPS (budgie-dev.zipsoft.fr, conteneur `budgie-develop`) tire pour se mettre à jour ; la production (budgie.zipsoft.fr, conteneur `budgie`) tourne sur `latest`.

## Démarche par défaut

Pour chaque demande, dans l'ordre :

0. **Se synchroniser** : `git fetch` puis `git pull --ff-only` sur `develop` avant de lire les tickets ou le code.
1. **Analyser** la demande ; une question ou une analyse sans code s'arrête là. En commençant un ticket, le reformuler en 1 à 3 phrases (ce qu'il est, ce que « fini » veut dire) avant tout outil.
2. **Le lot** : s'il n'existe pas, créer son ticket `lot` (PRD dans le corps, statut ⬜ ready) en sous-ticket de #43, et découper ses tickets.
3. **La branche** depuis `develop` ; le lot et le ticket en cours passent à 🔄 in-progress.
4. **Coder en TDD** : le test qui échoue d'abord, puis le code, puis le nettoyage ; documentation touchée par le changement dans les deux langues (`docs/en/` et `docs/fr/`), dans le même mouvement.
5. **Tester** et passer la porte de qualité (commandes ci-dessous) ; tout corriger avant de continuer.
6. **`CHANGELOG.md`** : une entrée claire à la fin de la bonne rubrique de `[Unreleased]` (en anglais) ; ne jamais monter la version hors d'une release.
7. **Si David doit vérifier dans l'application** : s'arrêter et attendre son feu vert ; le ticket passe à 🧑 waiting-human.
8. **Committer** (Conventional Commits, en anglais) et pousser ; **ouvrir la PR** vers `develop`, description en anglais.
9. **Relire** la PR avec `pr-code-review`, attendre la CI ; corriger, puis fusionner quand les deux sont propres.
10. **Après la fusion** : revenir sur `develop`, `pull`, cocher les conditions de fin tenues.

## Structure

- `budgie/` : le backend FastAPI, en couches : `api/` (routes minces) → `services/` (logique) → `models/` (ORM SQLAlchemy) et `schemas/` (Pydantic) ; `importers/` lit les fichiers bancaires ; `config.py` charge `.env` par `pydantic-settings`.
- `alembic/` : les migrations ; tout changement de schéma passe par elles, jamais par la base à la main.
- `tests/` : pytest, qui suit l'arborescence du code (`budgie/services/foo.py` → `tests/test_services/test_foo.py`), fixtures dans `tests/conftest.py`.
- `frontend/` : la SPA Vue 3 (Composition API, `<script setup lang="ts">`), Pinia, appels HTTP centralisés dans `src/api/`, Tailwind + DaisyUI ; tests Vitest.
- `docs/en/`, `docs/fr/` : guides utilisateur et développeur, feuille de route, tutoriels ; `docs/agents/` : les conventions de suivi pour les agents.
- `Dockerfile`, `docker-compose.yml`, `entrypoint.sh` : l'image et le déploiement.

## Commandes

```bash
# Backend
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy budgie/
poetry run pytest

# Frontend (dans frontend/)
npx vue-tsc --noEmit                       # la commande de la CI
npx vue-tsc --noEmit -p tsconfig.app.json  # les options strictes de l'application
npx eslint src/
npx vitest run

# Lancer
poetry run uvicorn budgie.main:app --reload   # http://localhost:8000
npm run dev                                   # dans frontend/, http://localhost:5173
docker compose up -d --build                  # http://localhost:8080
```

- C'est la porte de qualité de la CI, plus `vue-tsc -p tsconfig.app.json` : tout doit passer avant un commit.
- Après toute modification d'un `.vue`, lancer les deux `vue-tsc` : celui avec `-p tsconfig.app.json` applique les options strictes de l'application (`noUncheckedIndexedAccess`), et Vite ne signale ces erreurs qu'à l'exécution.
- Une contrainte d'unicité en base garde la déduplication (`import_hash` par compte) : un doublon se refuse en base, pas seulement dans le code.

## Règles

- Les montants sont des **centimes entiers** (`1050` = 10,50 €), jamais des flottants, en base comme dans le code.
- Les libellés de bénéficiaires, les mémos et les descriptions sont chiffrés en base (AES-256-GCM, clé de session de l'utilisateur) : tout regroupement ou toute recherche sur ces champs se fait en Python après déchiffrement, jamais en SQL.
- Chaque requête vérifie que les objets touchés ou référencés appartiennent à l'utilisateur courant.
- Les routes restent minces et délèguent aux services ; toute entrée et toute sortie d'API passe par un schéma Pydantic.
- Pas de nombre magique : des constantes nommées ou des enums.
- Annotations de type complètes et docstrings Google sur tout ce qui est public ; mypy à zéro erreur.
- Côté frontend : petits composants à responsabilité unique, classes DaisyUI plutôt que du CSS maison.
- Nommage : `snake_case` pour les fichiers, fonctions et colonnes Python, `PascalCase` pour les classes et les composants Vue, `useX` pour les composables, `kebab-case` pour les routes d'API, tables au pluriel.
- Le code, les commentaires, les commits, les PR et le `CHANGELOG.md` sont en anglais ; ce fichier, `docs/agents/` et les tickets en français ; la documentation utilisateur et développeur dans les deux langues ; les notes de version en français puis en anglais.
