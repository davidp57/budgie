# Budgie 🐦 — Tutoriel d'installation

🌐 [English version](../../en/tutorials/installation.md)

> **Objectif** : avoir Budgie qui tourne sur ta machine ou ton serveur en moins de 10 minutes.

---

## Option A — Docker (recommandé pour l'auto-hébergement)

C'est la façon la plus simple et la plus fiable de faire tourner Budgie sur un serveur ou un NAS.

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose installés
- Un terminal / accès SSH à ton serveur

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/davidp57/budgie.git
cd budgie
```

> Sur un NAS Synology, exécute ces commandes via SSH :
> ```bash
> ssh admin@ip-du-nas
> mkdir -p /volume1/docker/budgie
> cd /volume1/docker/budgie
> git clone https://github.com/davidp57/budgie.git .
> ```

### Étape 2 — Configurer l'environnement

```bash
cp .env.example .env
```

Ouvre `.env` et remplis les valeurs **obligatoires** :

```dotenv
# Génère une clé aléatoire (copie le résultat dans SECRET_KEY) :
#   Linux/macOS : openssl rand -hex 32
#   Windows PowerShell : -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
SECRET_KEY=colle-ta-clé-aléatoire-ici

# Si tu accèdes à Budgie depuis un serveur ou un NAS, ajoute l'URL exacte :
CORS_ORIGINS=http://localhost:5173,http://localhost:8080,http://192.168.1.50:8080
```

> ⚠️ **Ne laisse jamais** `SECRET_KEY` à sa valeur par défaut en production.

### Étape 3 — Construire et démarrer

```bash
docker compose up -d --build
```

Le premier build prend 2–3 minutes (téléchargement et compilation des dépendances). Les démarrages suivants sont quasi instantanés.

### Étape 4 — Vérifier

```bash
curl http://localhost:8080/api/health
# Attendu : {"status":"ok"}
```

Ouvre **http://localhost:8080** dans ton navigateur. Tu devrais voir la page de connexion Budgie.

### Étape 5 — Créer ton compte

Clique sur **Register** (S'inscrire), choisis un nom d'utilisateur et un mot de passe, et c'est parti.

---

## Option B — Portainer (interface graphique Docker)

Si tu gères tes conteneurs avec Portainer (courant sur Synology) :

1. Ouvre Portainer → **Stacks** → **Add stack**
2. Nomme la stack `budgie`
3. Colle le YAML suivant dans l'**éditeur web** :

```yaml
services:
  budgie:
    image: ghcr.io/davidp57/budgie:latest
    container_name: budgie
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - budgie-data:/app/data
    environment:
      - SECRET_KEY=colle-ta-clé-aléatoire-ici
      - DATABASE_URL=sqlite+aiosqlite:////app/data/budgie.db
      - CORS_ORIGINS=http://localhost:8080,http://192.168.1.50:8080
      - PUID=1000
      - PGID=1000

volumes:
  budgie-data:
```

4. Clique sur **Deploy the stack**
5. Ouvre `http://ton-serveur:8080`

---

## Option C — Depuis les sources (développeurs / contributeurs)

Pour le développement local ou si tu veux lancer le backend et le frontend séparément.

### Prérequis

- Python 3.12+ et [Poetry](https://python-poetry.org/docs/#installation)
- Node.js 22+ et npm

### Backend

```bash
git clone https://github.com/davidp57/budgie.git
cd budgie

poetry install
cp .env.example .env
# Édite .env et remplis SECRET_KEY
mkdir -p data/uploads

poetry run uvicorn budgie.main:app --reload
# API disponible sur http://localhost:8000
```

### Frontend

Dans un **deuxième terminal** :

```bash
cd frontend
npm install
npm run dev
# Interface disponible sur http://localhost:5173
```

Vite proxie automatiquement toutes les requêtes `/api/*` vers le backend.

---

## Mettre à jour Budgie

```bash
cd /chemin/vers/budgie

# Récupérer la dernière version
git pull

# Reconstruire et redémarrer
docker compose up -d --build
```

Les migrations de base de données s'exécutent automatiquement au démarrage — tes données sont préservées.

---

## Sauvegardes

Tes données se trouvent dans le dossier `data/` (ou le volume Docker `budgie-data`).

```bash
# Sauvegarde simple
cp -r data/ data-backup-$(date +%Y%m%d)/

# Ou compressée
tar -czf budgie-backup-$(date +%Y%m%d).tar.gz data/
```

Consulte [scripts/backup.sh](../../../scripts/backup.sh) pour un script de sauvegarde prêt à l'emploi.

---

## Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `{"status":"ok"}` pas retourné | Conteneur non démarré ou conflit de port | `docker compose logs budgie` |
| Erreur CORS dans le navigateur | URL du serveur absente de `CORS_ORIGINS` | Ajouter l'URL exacte à `CORS_ORIGINS` et redémarrer |
| Connexion impossible | Mauvais identifiants | Utiliser la page Register pour créer un compte |
| `Permission denied` sur data/ | `PUID`/`PGID` incorrects | Exécuter `id -u && id -g` sur le serveur et renseigner les valeurs dans `.env` |

---

## Étape suivante

➡️ [Comment utiliser Budgie — Tutoriel de prise en main](./usage.md)

---

☕ Budgie est gratuit et open source — si c'est utile, pense à [m'offrir un café](https://buymeacoffee.com/veaf_zip) !
