# Budgie 🐦 — Guide utilisateur

🌐 [English version](../en/user-guide.md)

## Sommaire

1. [Qu'est-ce que Budgie ?](#1-quest-ce-que-budgie-)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Premiers pas](#4-premiers-pas)
5. [Navigation dans l'application](#5-navigation-dans-lapplication)
6. [Gérer les comptes](#6-gérer-les-comptes)
7. [Gérer les catégories et les enveloppes](#7-gérer-les-catégories-et-les-enveloppes)
8. [Importer des transactions bancaires](#8-importer-des-transactions-bancaires)
9. [Catégorisation automatique](#9-catégorisation-automatique)
10. [Le budget (enveloppes)](#10-le-budget-enveloppes)
11. [Transactions virtuelles (prévisions)](#11-transactions-virtuelles-prévisions)
12. [Dépense rapide (QuickExpense)](#12-dépense-rapide-quickexpense)
13. [Thème et installation mobile (PWA)](#13-thème-et-installation-mobile-pwa)
14. [Déploiement Docker](#14-déploiement-docker)
15. [Sauvegardes et mises à jour](#15-sauvegardes-et-mises-à-jour)
16. [FAQ / Dépannage](#16-faq--dépannage)
17. [Sécurité & Chiffrement](#17-sécurité--chiffrement)

---

## 1. Qu'est-ce que Budgie ?

Budgie est une **application de gestion de budget personnel auto-hébergée** qui fonctionne entièrement sur votre propre serveur — pas de service cloud tiers, pas d'abonnement.

Elle suit la méthode du **budget par enveloppes** : chaque centime de revenu est affecté à une catégorie de dépenses avant d'être dépensé. En regardant n'importe quelle enveloppe, vous savez immédiatement combien il vous reste.

### Fonctionnalités principales

| Fonctionnalité | Description |
|---|---|
| 📥 Import bancaire | CSV, Excel (.xlsx), QIF, OFX — colonnes détectées automatiquement |
| 🏷️ Catégorisation automatique | Basée sur l'historique des bénéficiaires et les règles personnalisées |
| 💰 Budget par enveloppes | Enveloppes avec report optionnel du solde non dépensé |
| 🔮 Transactions virtuelles | Planifiez des achats futurs et voyez leur impact immédiat |
| ⚡ Dépense rapide | Saisie rapide avec préréglages et suggestions par géolocalisation |
| 🌓 Thème sombre / clair | Bascule auto ou manuelle |
| 📱 PWA mobile | Ajout à l'écran d'accueil, plein écran |
| 🐳 Self-hosted | Docker / Docker Compose, idéal pour NAS Synology |

---

## 2. Installation

### Option A — Docker Compose (recommandé)

C'est la méthode la plus simple pour déployer Budgie sur un serveur ou un NAS.

```bash
# Cloner le dépôt
git clone https://github.com/davidp57/budgie.git
cd budgie

# Configurer l'environnement
cp .env.example .env
# Éditez .env → changez SECRET_KEY (voir section Configuration)

# Construire et lancer
docker compose up -d --build

# Vérifier
curl http://localhost:8080/api/health
# → {"status":"ok"}
```

L'application est accessible sur `http://localhost:8080`.

### Option B — Depuis les sources (développement)

Prérequis : Python 3.12+, Poetry, Node.js 22+, npm.

```bash
# Backend
git clone https://github.com/davidp57/budgie.git
cd budgie
poetry install
cp .env.example .env
# Éditez .env → changez SECRET_KEY
mkdir -p data/uploads
poetry run uvicorn budgie.main:app --reload
# → API sur http://localhost:8000

# Frontend (dans un second terminal)
cd frontend
npm install
npm run dev
# → Interface sur http://localhost:5173
```

En mode développement, Vite proxifie toutes les requêtes `/api/*` vers le backend FastAPI.

---

## 3. Configuration

Toute la configuration se fait via le fichier `.env` à la racine du projet (copié depuis `.env.example`).

### Variables essentielles

| Variable | Défaut | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-to-a-random-string` | **Obligatoire** — Clé de signature JWT (voir détails ci-dessous) |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/budgie.db` | URL de la base SQLite (en Docker, défini automatiquement) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Origines autorisées (voir détails ci-dessous) |
| `BUDGIE_PORT` | `8080` | Port externe du conteneur Docker |
| `PUID` / `PGID` | `1000` | UID/GID de l'utilisateur hôte (pour les permissions fichiers en Docker). Trouvez les vôtres avec `id -u && id -g` |

#### `SECRET_KEY` — Clé de signature JWT

Cette clé est utilisée pour **signer et vérifier les tokens d'authentification** (JWT). À chaque connexion, le serveur crée un token signé avec cette clé. Si un attaquant connaît la clé, il peut forger des tokens valides et accéder à n'importe quel compte.

**Règles :**
- **Ne jamais** utiliser la valeur par défaut en production
- Utiliser une **chaîne aléatoire d'au moins 32 caractères** (64 caractères hexadécimaux recommandés)
- **Ne jamais partager** la clé ni la commiter dans un dépôt
- En cas de suspicion de compromission, **changez-la immédiatement** — toutes les sessions en cours seront invalidées (les utilisateurs devront se reconnecter)

**Comment générer une clé sécurisée :**

```bash
# Linux / macOS / WSL
openssl rand -hex 32

# PowerShell (Windows)
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Exemple de résultat : `a3f7b9c1d4e8...` (64 caractères hexadécimaux). Copiez cette valeur dans votre fichier `.env`.

#### `CORS_ORIGINS` — Origines autorisées

CORS (Cross-Origin Resource Sharing) contrôle **quels sites web sont autorisés à appeler l'API Budgie**. Le navigateur bloque toute requête venant d'une origine absente de cette liste.

**La valeur est une liste d'URLs séparées par des virgules** (protocole + domaine + port, sans slash final).

**Configurations courantes :**

| Scénario | Valeur |
|---|---|
| Développement local uniquement | `http://localhost:5173,http://localhost:8080` |
| NAS Synology (réseau local) | `http://localhost:5173,http://192.168.1.50:8280` |
| NAS Synology + domaine personnalisé | `http://localhost:5173,https://budgie.votre-domaine.com` |
| Multiples points d'accès | `http://localhost:5173,http://192.168.1.50:8280,https://budgie.votre-domaine.com` |

**Règles :**
- Toujours inclure `http://localhost:5173` si vous utilisez `npm run dev` en local
- Ajouter l'**URL exacte** que vous utilisez pour accéder à Budgie dans votre navigateur (avec le bon port)
- Pour l'accès HTTPS via proxy inverse, utilisez `https://` — **pas** `http://`
- **Ne jamais** utiliser `*` (wildcard) — cela désactive entièrement la protection CORS
- Après modification, **redémarrez** le conteneur : `docker compose restart`

> **Symptôme d'une origine manquante** : la console du navigateur affiche `CORS policy: No 'Access-Control-Allow-Origin' header`. Ajoutez l'URL indiquée dans l'erreur à `CORS_ORIGINS`.

### Variables avancées

| Variable | Défaut | Description |
|---|---|---|
| `ALGORITHM` | `HS256` | Algorithme JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Durée de vie du token (24 h par défaut) |
| `UPLOAD_DIR` | `data/uploads` | Répertoire temporaire pour les fichiers importés |
| `HOST` | `0.0.0.0` | Adresse d'écoute du serveur |
| `PORT` | `8000` | Port interne du serveur |
| `DEBUG` | `false` | Mode debug FastAPI |

> ⚠️ **Important** : Changez toujours `SECRET_KEY` avant la première utilisation en production. Une clé faible compromet l'authentification JWT.

---

## 4. Premiers pas

### Créer votre compte

1. Ouvrez `http://VOTRE_SERVEUR:8080` (ou `http://localhost:5173` en dev)
2. Cliquez sur **S'inscrire** pour créer votre compte utilisateur

### Ordre de configuration recommandé

1. **Créer les comptes** — vos comptes bancaires (courant, épargne, carte…)
2. **Créer les groupes de catégories et les catégories** — ex. groupe *Logement* avec *Loyer*, *Électricité*, *Internet*
3. **Créer les enveloppes** — chaque enveloppe regroupe des catégories (ex. enveloppe *Logement* = Loyer + Électricité)
4. **Importer votre premier fichier bancaire**
5. **Définir votre budget** pour le mois en cours

---

## 5. Navigation dans l'application

L'interface responsive de Budgie s'adapte à l'appareil :

- **Mobile** : un **dock en bas** (5 icônes) pour un accès rapide.
- **Desktop** : une **barre latérale** à gauche avec des libellés.

La navigation (AppNav) propose 5 sections :

| Icône | Page | Description |
|---|---|---|
| 🏠 | **Accueil** | Résumé du mois : revenus, dépenses, solde, mois précédent/suivant |
| 💰 | **Budget** | Vue des enveloppes avec édition inline du budget alloué |
| ⚡ | **Dépense rapide** | Saisie rapide d'une transaction avec préréglages |
| 📋 | **Dépenses** | Vue des dépenses avec filtres, tri, regroupement, édition et dashboard mensuel |
| ⚙️ | **Paramètres** | Comptes, catégories, enveloppes, règles, import, thème |

### Page Accueil

La page d'accueil affiche un résumé synthétique du mois sélectionné :
- **Revenus** et **dépenses** du mois
- **Solde** net
- Navigation rapide vers le mois précédent / suivant

### Page Budget

La page budget affiche vos enveloppes sous forme de **cartes** (DrawerCards). Chaque carte montre :
- Le nom de l'enveloppe avec un emoji configurable
- Les catégories rattachées (chips colorés)
- **Budgété** : montant alloué (cliquez pour modifier)
- **Activité** : total des transactions du mois
- **Disponible** : reste à dépenser (vert si positif, rouge si négatif)
- **Badge triangle ambré** (coin supérieur droit) : nombre de transactions enregistrées sur ce tiroir ce mois-ci. Appuyez dessus pour accéder directement à la liste des dépenses correspondantes.

Cliquez sur une enveloppe pour filtrer les transactions correspondantes dans le panneau du bas.

En bas de la grille des tiroirs, une bannière **« Dépense hors budget »** permet de saisir une transaction sans tiroir associé :
- Tapez le côté gauche pour ouvrir la saisie rapide en mode hors budget.
- Si des dépenses hors budget existent, une pastille ambrée à droite indique le nombre — tapez dessus pour les voir dans la vue Dépenses.

### Page Dépenses

La page **Dépenses** (`/depenses`) affiche les transactions virtuelles (saisies manuellement) pour le mois sélectionné. Fonctionnalités principales :

- **Navigation par mois** ◄ / ► pour parcourir les mois
- **Filtres** : par tiroir (enveloppe) et par groupe de catégories
- **Tri** : par date, montant ou libellé
- **Regroupement** : par tiroir, catégorie ou groupe de catégories
- **Modal d'édition** : modifier la date, le montant, le mémo, la catégorie et le tiroir
- **Suppression** avec confirmation
- **Mode Dashboard** 🥧 : camemberts montrant les dépenses par catégorie
  - **Par tiroir** (par défaut) : un graphique par tiroir
  - **Par groupe de catégories** : un graphique par groupe — basculez avec le toggle au-dessus des graphiques
  - Cliquez sur un graphique pour afficher un panneau détaillé avec toutes les dépenses du tiroir/groupe, regroupées par catégorie
  - Cliquez sur une autre tranche pour la mettre en surbrillance ; cliquez à nouveau sur la même pour fermer le panneau
- Les dépenses réconciliées affichent un lien vers la transaction bancaire pointée

---

## 6. Gérer les comptes

Allez dans **Paramètres → Comptes**.

Chaque compte représente un compte bancaire réel :
- **Nom** (ex. « Compte courant », « Livret A »)
- **Type** : courant, épargne, carte de crédit, espèces

Les soldes sont calculés à partir des transactions réelles (les transactions virtuelles ne les affectent pas).

> **Conseil** : Créez un compte par compte bancaire réel. Ne mélangez pas différentes banques.

---

## 7. Gérer les catégories et les enveloppes

### Catégories

Allez dans **Paramètres → Catégories**.

Les catégories sont organisées en **groupes** :

| Terme | Signification |
|---|---|
| Groupe | Regroupement logique (ex. « Logement ») |
| Catégorie | Poste de dépense (ex. « Loyer ») |

### Enveloppes

Allez dans **Paramètres → Enveloppes**.

Une enveloppe agrège une ou plusieurs catégories dans une même zone de budget. Chaque enveloppe a :
- Un **nom** et un **emoji** configurable
- Un flag **Report** (rollover) — si activé, le solde non dépensé est reporté au mois suivant
- Une liste de **catégories rattachées** (une catégorie ne peut appartenir qu'à une seule enveloppe)

---

## 8. Importer des transactions bancaires

Allez dans **Paramètres → Import** (ou via la page Import).

### Étape 1 — Téléverser un fichier

Glissez-déposez ou cliquez pour sélectionner votre fichier bancaire. Formats supportés :
- **CSV** — colonnes détectées automatiquement (séparateur `;` ou `,`, décimales françaises supportées)
- **Excel** (.xlsx / .xls)
- **QIF** — format ancien, largement disponible
- **OFX / OFC** — format d'échange ouvert (banques européennes)

### Étape 2 — Prévisualisation

Vérifiez que les dates, montants et descriptions sont corrects. Les catégories déjà reconnues sont pré-affectées.

### Étape 3 — Confirmer

Cliquez sur **Confirmer l'import**. Les transactions sont sauvegardées.

### Déduplication

Budgie calcule une empreinte unique (SHA-256) pour chaque transaction. Importer le même fichier deux fois ne crée aucun doublon.

### Correspondance avec les prévisions

Si des transactions virtuelles correspondent à des transactions du fichier importé (montant à ±10%, date à ±60 jours), Budgie propose de les lier automatiquement. Acceptez la suggestion pour marquer la prévision comme réalisée.

---

## 9. Catégorisation automatique

La catégorisation fonctionne en deux étapes :

1. **Correspondance bénéficiaire** — Si le bénéficiaire (payee) a déjà été catégorisé manuellement, cette catégorie est réutilisée automatiquement
2. **Règles personnalisées** — Évaluées par priorité décroissante

### Configurer les règles

Dans **Paramètres → Règles** :
- **Champ** : rechercher dans le nom du bénéficiaire ou le mémo
- **Type** : contient, correspondance exacte, ou expression régulière
- **Catégorie** : la catégorie à affecter
- **Priorité** : les règles à haute priorité sont évaluées en premier
- **Plage de montant** *(optionnel)* : limiter la règle aux transactions dont le montant absolu est compris entre un minimum et/ou un maximum (en centimes ou en euros selon l'affichage)
- **Type de transaction** *(optionnel)* : restreindre la règle aux débits, aux crédits, ou l'appliquer dans les deux sens (défaut : tous)

### Création automatique de règles lors du pointage

Dans la **vue Pointage**, lorsque vous liez une transaction bancaire à une dépense via l'assistant, une règle de catégorisation peut être créée automatiquement. Un **toggle** dans l'assistant vous permet de désactiver cette création si vous ne souhaitez pas qu'une règle soit enregistrée pour ce lien particulier.

---

## 10. Le budget (enveloppes)

### Fonctionnement

Chaque enveloppe affiche trois valeurs :

| Valeur | Signification |
|---|---|
| **Budgété** | Montant alloué ce mois |
| **Activité** | Total des transactions (réelles + virtuelles) dans les catégories de l'enveloppe |
| **Disponible** | Budgété − Activité (cumulatif si report activé) |

### Report (Rollover)

- **Activé** : le disponible est la somme cumulative (Budgété − Activité) de tous les mois jusqu'au mois en cours. Idéal pour les dépenses irrégulières (réparations, vacances…).
- **Désactivé** : le disponible ne concerne que le mois en cours

### À budgéter

En haut de la page budget : **Revenu total − Total budgété**. L'objectif est d'atteindre **zéro** — chaque centime affecté.

### Modifier le budget

Cliquez sur le montant **Budgété** d'une enveloppe pour saisir un nouveau montant. La modification est sauvegardée automatiquement.

---

## 11. Transactions virtuelles (prévisions)

### Créer une prévision

Dans la vue **Dépenses**, créez une nouvelle transaction virtuelle avec :
- **Montant**, **date estimée**, **catégorie**, **mémo**, **compte**

La prévision apparaît avec une icône ⏳ et un style en pointillé. Le **Disponible** de l'enveloppe est immédiatement réduit.

### Réalisation

Lors de l'import du relevé bancaire, Budgie suggère de lier les transactions réelles aux prévisions correspondantes. La prévision est alors marquée comme *réconciliée*.

### Consulter les prévisions en attente

Dans **Dépenses**, filtrez par tiroir ou par groupe pour voir les prévisions non encore réalisées.

---

## 12. Dépense rapide (QuickExpense)

La page **QuickExpense** (⚡) permet de saisir une transaction en quelques secondes :

1. Appuyez sur un **tiroir** dans la vue Budget pour ouvrir la saisie rapide
2. Entrez le **montant**
3. Ajoutez optionnellement un **mémo**, une **date**, ou marquez la dépense comme **prévue**
4. Validez

La transaction est liée directement au tiroir (enveloppe) — aucune catégorie n’est requise. Si vous souhaitez préciser une catégorie, vous pouvez modifier la transaction après saisie.
### Mode hors budget

Appuyez sur la bannière **« Dépense hors budget »** en bas de la grille des tiroirs pour enregistrer une transaction sans tiroir. La saisie s'ouvre avec l'en-tête « Hors budget » et sauvegarde la transaction avec `envelope_id = null`. Vous pourrez l'affecter à un tiroir ultérieurement via le modal d'édition de la page Dépenses.
### Préréglages

Vous pouvez créer des **préréglages** pour les dépenses fréquentes (ex. « Boulangerie — 1,20 € »). Un clic suffit ensuite pour pré-remplir le formulaire.

### Suggestions par géolocalisation

Si vous autorisez l'accès à votre position (nécessite HTTPS), Budgie interroge les commerces proches via OpenStreetMap et suggère des lieux avec leur emoji correspondante.

> 📍 La géolocalisation nécessite un accès via HTTPS (proxy inverse) ou `localhost`. Sur iOS Safari, HTTPS est obligatoire.

---

## 13. Thème et installation mobile (PWA)

### Thème sombre / clair

Cliquez sur le bouton ☀️ / 🌙 pour basculer entre les thèmes `emerald` (clair) et `night` (sombre). Votre choix est sauvegardé et appliqué automatiquement.

Au premier chargement, le thème suit les préférences de votre système d'exploitation.

### Ajouter à l'écran d'accueil

Sur mobile (Android / iOS), ouvrez Budgie dans votre navigateur et utilisez **Ajouter à l'écran d'accueil** dans le menu. L'application s'ouvre alors en plein écran, comme une app native.

---

## 14. Déploiement Docker

### Déploiement sur Synology NAS (SSH)

#### Prérequis

- NAS Synology avec **Container Manager** (Docker) installé
- Accès SSH au NAS

#### Étapes

```bash
# 1. Se connecter au NAS
ssh admin@votre-nas-ip

# 2. Créer le répertoire du projet
mkdir -p /volume1/docker/budgie
cd /volume1/docker/budgie

# 3. Cloner le dépôt
git clone https://github.com/davidp57/budgie.git .

# 4. Configurer l'environnement
cp .env.example .env
vi .env
# → SECRET_KEY=$(openssl rand -hex 32)
# → PUID=votre_uid (trouvez-le avec: id -u)
# → PGID=votre_gid (trouvez-le avec: id -g)
# → CORS_ORIGINS=https://budgie.votre-domaine.com

# 5. Construire et lancer
docker compose up -d --build

# 6. Vérifier
curl http://localhost:8080/api/health
# → {"status":"ok"}
```

### Déploiement via Portainer

Si vous utilisez **Portainer** pour gérer vos conteneurs Docker :

1. **Accédez** à votre instance Portainer (ex. `https://votre-nas:9443`)
2. **Stacks** → **Add stack** → donnez un nom (ex. `budgie`)
3. **Web editor** — collez le YAML suivant :

```yaml
services:
  budgie:
    image: ghcr.io/davidp57/budgie:latest
    container_name: budgie
    restart: unless-stopped
    ports:
      - "8280:8000"
    volumes:
      - budgie-data:/app/data
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite+aiosqlite:////app/data/budgie.db
      - UPLOAD_DIR=/app/data/uploads
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
      - CORS_ORIGINS=${CORS_ORIGINS:-}
      - WEBAUTHN_RP_ID=${WEBAUTHN_RP_ID:-localhost}
      - WEBAUTHN_RP_NAME=${WEBAUTHN_RP_NAME:-Budgie}
      - WEBAUTHN_ORIGIN=${WEBAUTHN_ORIGIN:-https://localhost:5173}
    mem_limit: 256m
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  budgie-data:
```

4. **Environment variables** (en bas du formulaire) — ajoutez :
   - `SECRET_KEY` = votre clé (générez-en une avec `openssl rand -hex 32` sur votre machine)
   - `PUID` = votre UID (ex. `1026` — trouvez-le avec `id -u` en SSH)
   - `PGID` = votre GID (ex. `100` — trouvez-le avec `id -g` en SSH)
   - `CORS_ORIGINS` = `https://budgie.votre-domaine.com`
   - `WEBAUTHN_RP_ID` = votre domaine sans schéma ni port (ex. `budgie.votre-domaine.com`) — requis pour que les Passkeys fonctionnent
   - `WEBAUTHN_ORIGIN` = URL complète du frontend (ex. `https://budgie.votre-domaine.com`) — doit correspondre exactement à ce qu'affiche le navigateur

5. **Deploy the stack**

> **Points importants** :
> - **`image:` et non `build:`** — Portainer ne peut pas construire d'images à partir de sources. L'image est publiée automatiquement sur GHCR par le CI.
> - **Volume nommé** (`budgie-data`) — les chemins relatifs (`./data`) ne fonctionnent pas dans Portainer. Pour un bind mount, utilisez un chemin absolu : `/volume1/docker/budgie/data:/app/data`.
> - **Port 8080 souvent occupé** — sur Synology, le port 8080 peut être pris par DSM ou un autre conteneur. Si vous obtenez l'erreur `port is already allocated`, choisissez un autre port (ex. `8280:8000`). Vérifiez les ports utilisés : `docker ps --format "table {{.Names}}\t{{.Ports}}" | grep 8080`.
> - **Registre privé** — si Portainer ne peut pas pull l'image, rendez le package public sur GitHub (Settings → Visibility → Public), ou ajoutez un registre dans Portainer (Settings → Registries → Custom : URL `ghcr.io`, username `davidp57`, password = Personal Access Token avec le scope `read:packages`).

### Proxy inverse Synology (HTTPS)

Pour accéder à Budgie via HTTPS avec un certificat SSL :

1. **Panneau de configuration** → **Portail de connexion** → **Avancé** → **Proxy inverse**
2. Cliquez **Créer** et configurez :

| Champ | Valeur |
|---|---|
| Description | Budgie |
| Source — Protocole | HTTPS |
| Source — Nom d'hôte | `budgie.votre-domaine.com` |
| Source — Port | 443 |
| Destination — Protocole | HTTP |
| Destination — Nom d'hôte | `localhost` |
| Destination — Port | 8280 (ou le port choisi dans votre stack) |

3. Onglet **En-tête personnalisé** → ajoutez :
   - `Upgrade` → `$http_upgrade`
   - `Connection` → `$connection_upgrade`

4. **Certificat SSL** : Panneau de configuration → Sécurité → Certificat
   - Utilisez Let's Encrypt (gratuit) ou importez votre certificat
   - Assignez le certificat à l'entrée du proxy inverse

5. Mettez à jour `CORS_ORIGINS` dans `.env` puis redémarrez :
```bash
docker compose restart
```

---

## 15. Sauvegardes et mises à jour

### Sauvegardes automatiques

Configurez une tâche planifiée dans DSM :
1. **Panneau de configuration** → **Planificateur de tâches** → **Créer** → **Script défini par l'utilisateur**
2. Planification : quotidienne à 02h00
3. Script :
```bash
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

Les sauvegardes sont stockées dans `./data/backups/` et automatiquement purgées après **7 jours** (configurable via `KEEP_DAYS`).

### Sauvegarde manuelle

```bash
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

### Mises à jour

```bash
cd /volume1/docker/budgie

# Récupérer les dernières modifications
git pull

# Reconstruire et redémarrer
docker compose up -d --build

# Vérifier les logs
docker compose logs -f --tail=20 budgie
```

Les migrations de base de données s'exécutent **automatiquement** au démarrage — aucune étape manuelle nécessaire.

---

## 16. FAQ / Dépannage

| Problème | Solution |
|---|---|
| **Permission denied** sur `data/` | Vérifiez que `PUID`/`PGID` correspondent à votre utilisateur NAS (`id -u && id -g`) |
| **Le conteneur redémarre en boucle** | Consultez les logs : `docker compose logs budgie` |
| **Inaccessible depuis d'autres appareils** | Vérifiez que le pare-feu autorise le port choisi (ex. 8280) |
| **Port is already allocated** | Le port est déjà utilisé par un autre service. Changez le port dans votre stack (ex. `8280:8000`). Vérifiez : `docker ps \| grep 8080` |
| **Erreurs CORS dans le navigateur** | Ajoutez votre URL à `CORS_ORIGINS` dans `.env` et redémarrez |
| **Base de données verrouillée** | Une seule instance doit tourner (limitation SQLite) |
| **Géolocalisation ne fonctionne pas** | L'accès doit se faire via HTTPS (proxy inverse ou `localhost`) |
| **Import échoue silencieusement** | Vérifiez le format du fichier. CSV : séparateur `;` ou `,`, encodage UTF-8 ou Latin-1 |
| **Doublon non détecté** | Vérifiez que les colonnes date/montant/description sont bien détectées dans la prévisualisation |

### Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f budgie

# Redémarrer le conteneur
docker compose restart

# Vérifier la santé
curl http://localhost:8080/api/health

# Entrer dans le conteneur
docker exec -it budgie /bin/bash

# Sauvegarde manuelle
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

---

## 17. Sécurité & Chiffrement

### Qu'est-ce qui est chiffré ?

Budgie chiffre **toutes vos données financières** au repos dans la base de données :
- Noms de comptes
- Montants, dates et mémos des transactions
- Noms des catégories et enveloppes
- Noms des bénéficiaires
- Allocations budgétaires
- Règles de catégorisation

Seuls les identifiants structurels (IDs, clés étrangères) restent non chiffrés — ils ne révèlent aucune information personnelle.

### Comment ça fonctionne ?

Lors de la création de votre compte Budgie, vous choisissez une **passphrase** (une phrase mémorable ou un ensemble de mots). Cette passphrase est utilisée pour générer une clé de chiffrement via un algorithme sécurisé (Argon2id). Toutes vos données sont ensuite chiffrées avec cette clé selon un chiffrement de grade militaire (AES-256-GCM).

**Points clés :**
- Votre clé de chiffrement n'est **jamais stockée** sur le serveur — elle n'existe qu'en mémoire pendant votre connexion.
- Lorsque vous vous déconnectez (ou que votre session expire), la clé est purgée de la mémoire.
- Même l'administrateur du serveur **ne peut pas lire vos données** sans votre passphrase.
- Si vous perdez votre passphrase, vos données sont **définitivement irrécupérables** — c'est un choix de conception.

### Connexion

Budgie propose trois méthodes d'authentification, équilibrant sécurité et confort :

| Méthode | Quand l'utiliser | Fonctionnement |
|---|---|---|
| **Passkey (biométrie)** | Usage quotidien | Empreinte digitale ou Face ID sur votre appareil → déverrouille la clé stockée localement |
| **PIN** | Accès rapide de secours | PIN à 4–6 chiffres → déchiffre la clé stockée localement |
| **Passphrase** | Configuration initiale, nouvel appareil, récupération | Vous saisissez la passphrase → la clé est redérivée |

**Sécurité du PIN** : après 5 tentatives échouées, la clé stockée localement est effacée. Vous devrez ressaisir votre passphrase.

> **Le PIN nécessite HTTPS** — le PIN utilise l'API Web Crypto (`crypto.subtle`) qui n'est disponible que sur des origines sécurisées (HTTPS ou `localhost`). Si l'application est servie en HTTP simple, le PIN ne sera pas proposé.

### Configurer les Passkeys

1. Connectez-vous avec votre passphrase
2. Allez dans **Paramètres → Sécurité**
3. Cliquez sur **Enregistrer une Passkey**
4. Suivez l'invite biométrique de votre appareil (empreinte, Face ID, Windows Hello…)
5. C'est fait — la prochaine fois, vous pourrez vous connecter avec votre biométrie

Vous pouvez enregistrer des Passkeys sur plusieurs appareils (téléphone, tablette, ordinateur).

### Document de récupération (PDF)

À la création du compte, Budgie génère un **PDF de récupération** contenant :
- Votre passphrase en clair
- Un QR code pour ressaisie rapide
- Des informations de vérification (8 premiers caractères du hash de la clé)

**Imprimez ce document et conservez-le en lieu sûr** (coffre-fort, coffre bancaire…). C'est votre seul moyen de récupérer l'accès si vous oubliez votre passphrase et perdez tous vos appareils.

> ⚠️ **Ne stockez jamais ce PDF numériquement** (ni sur votre téléphone, ni dans le cloud, ni par email). Toute personne possédant ce document peut accéder à vos données.

### Que se passe-t-il si…

| Scénario | Résultat |
|---|---|
| Je change de téléphone | Enregistrez une nouvelle Passkey. Utilisez la passphrase pour la première connexion. |
| J'oublie mon PIN | Ressaisissez votre passphrase. Vous pourrez définir un nouveau PIN ensuite. |
| J'oublie ma passphrase mais j'ai le PDF | Utilisez la passphrase du PDF imprimé pour récupérer l'accès. |
| J'oublie ma passphrase ET je perds le PDF | **Données définitivement perdues.** C'est le compromis sécurité : pas de porte dérobée admin. |
| Mon NAS est volé | Le voleur a des blobs chiffrés — inutilisables sans votre passphrase. |
| Je veux partager avec ma famille | Chaque utilisateur a sa propre passphrase et clé. Les données sont isolées par utilisateur. |

---

☕ Si Budgie t'est utile, pense à [m'offrir un café](https://buymeacoffee.com/veaf_zip) — c'est vraiment apprécié !
