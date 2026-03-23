# Deployment Guide / Guide de déploiement

## Docker Deployment on Synology NAS

### Prerequisites / Prérequis

- Synology NAS with **Container Manager** (Docker) installed
- SSH access to the NAS
- A domain name (optional, for HTTPS via reverse proxy)

---

### 1. Prepare the NAS / Préparer le NAS

```bash
# SSH into your NAS
ssh admin@your-nas-ip

# Create the project directory
mkdir -p /volume1/docker/budgie
cd /volume1/docker/budgie

# Clone the repository (or copy the files)
git clone https://github.com/davidp57/budgie.git .

# Find your UID/GID (needed for file permissions)
id -u   # → e.g. 1026
id -g   # → e.g. 100
```

### 2. Configure environment / Configurer l'environnement

```bash
# Copy the example config
cp .env.example .env

# Edit .env with your values
vi .env
```

**Required changes in `.env`:**

```bash
# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Set your NAS UID/GID
PUID=1026    # ← your id -u result
PGID=100     # ← your id -g result

# Set CORS for your domain (if using reverse proxy)
CORS_ORIGINS=https://budgie.your-domain.com,http://localhost:8080

# Optional: change external port
BUDGIE_PORT=8080
```

### 3. Build and start / Construire et démarrer

```bash
# Build the Docker image and start the container
docker compose up -d --build

# Check logs
docker compose logs -f budgie

# Verify health
curl http://localhost:8080/api/health
# → {"status":"ok"}
```

### 4. Synology Reverse Proxy (HTTPS) / Proxy inverse Synology

To access Budgie via HTTPS with a proper certificate:

1. Open **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. Click **Create** and configure:

| Field | Value |
|-------|-------|
| Description | Budgie |
| Source Protocol | HTTPS |
| Source Hostname | `budgie.your-domain.com` |
| Source Port | 443 |
| Destination Protocol | HTTP |
| Destination Hostname | `localhost` |
| Destination Port | 8080 |

3. In **Custom Header** tab, add:
   - `Upgrade` → `$http_upgrade`
   - `Connection` → `$connection_upgrade`

4. Configure your SSL certificate in **Control Panel** → **Security** → **Certificate**
   - Use Let's Encrypt (free) or import your own certificate
   - Assign the certificate to the reverse proxy entry

5. Update `CORS_ORIGINS` in `.env`:
```bash
CORS_ORIGINS=https://budgie.your-domain.com
```

6. Restart the container:
```bash
docker compose restart
```

### 5. Automatic backups / Sauvegardes automatiques

Set up a daily backup via **Task Scheduler** in DSM:

1. **Control Panel** → **Task Scheduler** → **Create** → **Scheduled Task** → **User-defined script**
2. Schedule: Daily at 02:00
3. Script:

```bash
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

Backups are stored in `./data/backups/` and automatically pruned after 7 days.

To change retention: set `KEEP_DAYS=14` before the command.

### 6. Updates / Mises à jour

```bash
cd /volume1/docker/budgie

# Pull latest code
git pull

# Rebuild and restart (zero-downtime with health checks)
docker compose up -d --build

# Verify
docker compose logs -f --tail=20 budgie
```

The container automatically runs database migrations on startup — no manual step needed.

### 7. Troubleshooting / Dépannage

| Problem | Solution |
|---------|----------|
| Permission denied on `data/` | Check `PUID`/`PGID` match your NAS user (`id -u && id -g`) |
| Container keeps restarting | Check logs: `docker compose logs budgie` |
| Can't reach from other devices | Verify firewall allows port 8080 (or your custom `BUDGIE_PORT`) |
| CORS errors in browser | Add your URL to `CORS_ORIGINS` in `.env` and restart |
| Database locked | Only one instance should run at a time (SQLite limitation) |
| Geolocation not working | Must access via HTTPS (reverse proxy or `localhost`) |

---

## Guide de déploiement sur Synology NAS (FR)

### Prérequis

- NAS Synology avec **Container Manager** (Docker) installé
- Accès SSH au NAS
- Un nom de domaine (optionnel, pour HTTPS via proxy inverse)

### Étapes rapides

1. **SSH** sur le NAS et cloner le dépôt dans `/volume1/docker/budgie/`
2. **Copier** `.env.example` → `.env` et configurer `SECRET_KEY`, `PUID`, `PGID`
3. **Lancer** : `docker compose up -d --build`
4. **Proxy inverse** : Panneau de configuration → Portail de connexion → Avancé → Proxy inverse
   - Source : HTTPS / `budgie.votre-domaine.com` / 443
   - Destination : HTTP / `localhost` / 8080
5. **Certificat SSL** : Let's Encrypt via Panneau de configuration → Sécurité → Certificat
6. **Sauvegardes** : Planificateur de tâches → Script quotidien à 02h00
7. **Mises à jour** : `git pull && docker compose up -d --build`

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f budgie

# Redémarrer
docker compose restart

# Sauvegarde manuelle
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups

# Vérifier la santé
curl http://localhost:8080/api/health

# Entrer dans le conteneur
docker exec -it budgie /bin/bash
```
