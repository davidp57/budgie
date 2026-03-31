# Budgie 🐦 — Installation Tutorial

🌐 [Version française](../../fr/tutorials/installation.md)

> **Goal**: have Budgie running on your machine or server in under 10 minutes.

---

## Option A — Docker (recommended for self-hosting)

This is the simplest and most reliable way to run Budgie on a server or NAS.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed
- A terminal / SSH access to your server

### Step 1 — Clone the repository

```bash
git clone https://github.com/davidp57/budgie.git
cd budgie
```

> On a Synology NAS, run these commands via SSH:
> ```bash
> ssh admin@your-nas-ip
> mkdir -p /volume1/docker/budgie
> cd /volume1/docker/budgie
> git clone https://github.com/davidp57/budgie.git .
> ```

### Step 2 — Configure the environment

```bash
cp .env.example .env
```

Open `.env` and set the **mandatory** values:

```dotenv
# Generate a random key (copy the result into SECRET_KEY):
#   Linux/macOS: openssl rand -hex 32
#   Windows PowerShell: -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
SECRET_KEY=paste-your-random-key-here

# If running on a NAS or remote server, add the URL you use to access Budgie:
CORS_ORIGINS=http://localhost:5173,http://localhost:8080,http://192.168.1.50:8080
```

> ⚠️ **Never** leave `SECRET_KEY` as the default value in production.

### Step 3 — Build and start

```bash
docker compose up -d --build
```

The first build takes 2–3 minutes (downloads and compiles dependencies). Subsequent starts are instant.

### Step 4 — Verify

```bash
curl http://localhost:8080/api/health
# Expected: {"status":"ok"}
```

Open **http://localhost:8080** in your browser. You should see the Budgie login page.

### Step 5 — Create your account

Click **Register**, choose a username and password, and you're in.

---

## Option B — Portainer (Docker GUI)

If you manage your containers with Portainer (common on Synology):

1. Open Portainer → **Stacks** → **Add stack**
2. Name it `budgie`
3. Paste the following YAML in the **Web editor**:

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
      - SECRET_KEY=paste-your-random-key-here
      - DATABASE_URL=sqlite+aiosqlite:////app/data/budgie.db
      - CORS_ORIGINS=http://localhost:8080,http://192.168.1.50:8080
      - PUID=1000
      - PGID=1000

volumes:
  budgie-data:
```

4. Click **Deploy the stack**
5. Open `http://your-server:8080`

---

## Option C — From source (developers / contributors)

For local development or if you want to run the backend and frontend separately.

### Prerequisites

- Python 3.12+ and [Poetry](https://python-poetry.org/docs/#installation)
- Node.js 22+ and npm

### Backend

```bash
git clone https://github.com/davidp57/budgie.git
cd budgie

poetry install
cp .env.example .env
# Edit .env and set SECRET_KEY
mkdir -p data/uploads

poetry run uvicorn budgie.main:app --reload
# API available at http://localhost:8000
```

### Frontend

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

Vite automatically proxies all `/api/*` requests to the backend.

---

## Updating Budgie

```bash
cd /path/to/budgie

# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

Database migrations run automatically on startup — your data is preserved.

---

## Backups

Your data lives in the `data/` folder (or the Docker volume `budgie-data`).

```bash
# Simple backup script
cp -r data/ data-backup-$(date +%Y%m%d)/

# Or compress it
tar -czf budgie-backup-$(date +%Y%m%d).tar.gz data/
```

See [scripts/backup.sh](../../../scripts/backup.sh) for a ready-made backup script.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `{"status":"ok"}` not returned | Container not started or port conflict | `docker compose logs budgie` |
| Browser shows CORS error | Your server URL not in `CORS_ORIGINS` | Add the exact URL to `CORS_ORIGINS` and restart |
| Login fails immediately | Wrong username/password | Use the Register page to create a new account |
| `Permission denied` on data/ | Wrong `PUID`/`PGID` | Run `id -u && id -g` on your server and set the values in `.env` |

---

## Next Step

➡️ [How to use Budgie — Getting Started Tutorial](./usage.md)

---

☕ Budgie is free and open source — if it's useful to you, consider [buying me a coffee](https://buymeacoffee.com/veaf_zip)!
