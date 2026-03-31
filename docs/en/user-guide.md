# Budgie 🐦 — User Guide

🌐 [Version française](../fr/user-guide.md)

## Table of Contents

1. [What is Budgie?](#1-what-is-budgie)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [First Steps](#4-first-steps)
5. [Navigating the Application](#5-navigating-the-application)
6. [Managing Accounts](#6-managing-accounts)
7. [Managing Categories and Envelopes](#7-managing-categories-and-envelopes)
8. [Importing Bank Transactions](#8-importing-bank-transactions)
9. [Automatic Categorization](#9-automatic-categorization)
10. [The Budget (Envelopes)](#10-the-budget-envelopes)
11. [Virtual Transactions (Forecasts)](#11-virtual-transactions-forecasts)
12. [Quick Expense](#12-quick-expense)
13. [Theme & Mobile Installation (PWA)](#13-theme--mobile-installation-pwa)
14. [Docker Deployment](#14-docker-deployment)
15. [Backups & Updates](#15-backups--updates)
16. [FAQ / Troubleshooting](#16-faq--troubleshooting)
17. [Security & Encryption](#17-security--encryption)

---

## 1. What is Budgie?

Budgie is a **self-hosted personal budget management application** that runs entirely on your own server — no third-party cloud service, no subscription fees.

It follows the **envelope budgeting** method: every centime of income is assigned to a spending category before you spend it. Looking at any envelope tells you immediately how much is left.

### Key Features

| Feature | Description |
|---|---|
| 📥 Bank import | CSV, Excel (.xlsx), QIF, OFX — columns detected automatically |
| 🏷️ Auto-categorization | Based on payee history and custom rules |
| 💰 Envelope budgeting | Envelopes with optional rollover of unspent balance |
| 🔮 Virtual transactions | Plan future purchases and see their immediate budget impact |
| ⚡ Quick Expense | Fast transaction entry with presets and geolocation suggestions |
| 🌓 Dark / light theme | Automatic or manual toggle |
| 📱 Mobile PWA | Add to home screen, full-screen experience |
| 🐳 Self-hosted | Docker / Docker Compose, ideal for Synology NAS |

---

## 2. Installation

### Option A — Docker Compose (recommended)

This is the simplest way to deploy Budgie on a server or NAS.

```bash
# Clone the repository
git clone https://github.com/davidp57/budgie.git
cd budgie

# Configure the environment
cp .env.example .env
# Edit .env → change SECRET_KEY (see Configuration section)

# Build and start
docker compose up -d --build

# Verify
curl http://localhost:8080/api/health
# → {"status":"ok"}
```

The application is accessible at `http://localhost:8080`.

### Option B — From source (development)

Prerequisites: Python 3.12+, Poetry, Node.js 22+, npm.

```bash
# Backend
git clone https://github.com/davidp57/budgie.git
cd budgie
poetry install
cp .env.example .env
# Edit .env → change SECRET_KEY
mkdir -p data/uploads
poetry run uvicorn budgie.main:app --reload
# → API at http://localhost:8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
# → UI at http://localhost:5173
```

In development mode, Vite proxies all `/api/*` requests to the FastAPI backend.

---

## 3. Configuration

All configuration is done via the `.env` file at the project root (copied from `.env.example`).

### Essential Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-to-a-random-string` | **Required** — JWT signing key (see details below) |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/budgie.db` | SQLite database URL (set automatically in Docker) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed origins (see details below) |
| `BUDGIE_PORT` | `8080` | External Docker container port |
| `PUID` / `PGID` | `1000` | Host user UID/GID (for Docker file permissions). Find yours with `id -u && id -g` |

#### `SECRET_KEY` — JWT signing key

This key is used to **sign and verify authentication tokens** (JWT). Every time a user logs in, the server creates a token signed with this key. If an attacker knows the key, they can forge valid tokens and access any account.

**Rules:**
- **Never** use the default value in production
- Use a **random string of at least 32 characters** (64 hex characters recommended)
- **Never share** the key or commit it to a repository
- If you suspect the key has been compromised, **change it immediately** — all existing sessions will be invalidated (users must log in again)

**How to generate a secure key:**

```bash
# Linux / macOS / WSL
openssl rand -hex 32

# PowerShell (Windows)
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Example result: `a3f7b9c1d4e8...` (64 hex characters). Copy this value into your `.env` file.

#### `CORS_ORIGINS` — Allowed origins

CORS (Cross-Origin Resource Sharing) controls **which websites are allowed to call the Budgie API**. The browser blocks any request coming from an origin not in this list.

**The value is a comma-separated list of URLs** (protocol + domain + port, no trailing slash).

**Common configurations:**

| Scenario | Value |
|---|---|
| Local development only | `http://localhost:5173,http://localhost:8080` |
| Synology NAS (local network) | `http://localhost:5173,http://192.168.1.50:8280` |
| Synology NAS + custom domain | `http://localhost:5173,https://budgie.your-domain.com` |
| Multiple access points | `http://localhost:5173,http://192.168.1.50:8280,https://budgie.your-domain.com` |

**Rules:**
- Always include `http://localhost:5173` if you use `npm run dev` locally
- Add the **exact URL** you use to access Budgie in your browser (with the correct port)
- For HTTPS via reverse proxy, use `https://` — **not** `http://`
- **Never** use `*` (wildcard) — it disables CORS protection entirely
- After changing the value, **restart** the container: `docker compose restart`

> **Symptom of a missing origin**: the browser console shows `CORS policy: No 'Access-Control-Allow-Origin' header`. Add the URL shown in the error to `CORS_ORIGINS`.

### Advanced Variables

| Variable | Default | Description |
|---|---|---|
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime (default 24 h) |
| `UPLOAD_DIR` | `data/uploads` | Temporary directory for uploaded files |
| `HOST` | `0.0.0.0` | Server listen address |
| `PORT` | `8000` | Internal server port |
| `DEBUG` | `false` | FastAPI debug mode |

> ⚠️ **Important**: Always change `SECRET_KEY` before first production use. A weak key compromises JWT authentication.

---

## 4. First Steps

### Create Your Account

1. Open `http://YOUR_SERVER:8080` (or `http://localhost:5173` in dev)
2. Click **Register** to create your user account

### Recommended Setup Order

1. **Create accounts** — your bank accounts (checking, savings, credit card…)
2. **Create category groups and categories** — e.g. group *Housing* with *Rent*, *Electricity*, *Internet*
3. **Create envelopes** — each envelope groups categories (e.g. *Housing* envelope = Rent + Electricity)
4. **Import your first bank file**
5. **Assign your budget** for the current month

---

## 5. Navigating the Application

Budgie's responsive interface adapts to the device:

- **Mobile**: a **bottom dock** (5 icons) for quick access.
- **Desktop**: a **sidebar** on the left with labels.

The navigation (AppNav) offers 5 sections:

| Icon | Page | Description |
|---|---|---|
| 🏠 | **Home** | Month summary: income, expenses, balance, previous/next month navigation |
| 💰 | **Budget** | Envelope view with inline budget editing |
| ⚡ | **Quick Expense** | Fast transaction entry with presets |
| 📋 | **Expenses** | Expenses with filters, sort, grouping, edit and monthly dashboard |
| ⚙️ | **Settings** | Accounts, categories, envelopes, rules, import, theme |

### Home Page

The home page displays a summary of the selected month:
- **Income** and **expenses** for the month
- Net **balance**
- Quick navigation to previous / next month

### Budget Page

The budget page shows your envelopes as **cards** (DrawerCards). Each card displays:
- The envelope name with a configurable emoji
- Assigned categories (colored chips)
- **Budgeted**: allocated amount (click to edit)
- **Activity**: total transactions for the month
- **Available**: remaining to spend (green if positive, red if negative)
- **Amber triangle badge** (top-right corner): number of transactions recorded for this envelope this month. Tap the badge to jump to the matching expense list.

Click an envelope to filter the corresponding transactions in the bottom panel.

At the bottom of the envelope grid, an **"Off-budget expense"** banner lets you record a transaction not linked to any envelope:
- Tap the left side to open the Quick Expense sheet in off-budget mode.
- If unassigned expenses exist, an amber pill on the right shows the count — tap it to see them in the Expenses view.

### Expenses Page

The **Expenses** page (`/depenses`) shows virtual transactions (manually entered expenses) for the selected month. Key features:

- **Month navigation** ◄ / ► to browse months
- **Filters**: by envelope (drawer) and by category group
- **Sort**: by date, amount, or label
- **Group by**: envelope, category, or category group
- **Inline edit modal**: change date, amount, memo, category, and envelope
- **Delete** with confirmation
- **Dashboard mode** 🥧: doughnut charts showing spending by category
  - **Per envelope** (default): one chart per envelope
  - **Per category group**: one chart per category group — switch with the toggle above the charts
  - Click a chart to expand a drill-down panel showing all expenses grouped by category
  - Click a different slice to highlight it on the doughnut; click the same slice again to close the panel
- Reconciled expenses show a link to the matched bank transaction

---

## 6. Managing Accounts

Go to **Settings → Accounts**.

Each account represents a real bank account:
- **Name** (e.g. "Checking", "Savings")
- **Type**: checking, savings, credit card, cash

Balances are calculated from real transactions (virtual transactions do not affect them).

> **Tip**: Create one account per real bank account. Don't mix different banks.

---

## 7. Managing Categories and Envelopes

### Categories

Go to **Settings → Categories**.

Categories are organized in **groups**:

| Term | Meaning |
|---|---|
| Group | Logical collection (e.g. "Housing") |
| Category | Single spending area (e.g. "Rent") |

### Envelopes

Go to **Settings → Envelopes**.

An envelope aggregates one or more categories into a single budget area. Each envelope has:
- A **name** and a configurable **emoji**
- A **Rollover** flag — if enabled, unspent balance carries forward to next month
- A list of **assigned categories** (each category can belong to only one envelope)

---

## 8. Importing Bank Transactions

Go to **Settings → Import** (or via the Import page).

### Step 1 — Upload a File

Drag-and-drop or click to select your bank file. Supported formats:
- **CSV** — columns detected automatically (separator `;` or `,`, French decimals supported)
- **Excel** (.xlsx / .xls)
- **QIF** — older format, widely available
- **OFX / OFC** — open exchange format (European banks)

### Step 2 — Preview

Check that dates, amounts and descriptions are correct. Already-recognized categories are pre-assigned.

### Step 3 — Confirm

Click **Confirm import**. Transactions are saved.

### Deduplication

Budgie computes a unique fingerprint (SHA-256) for each transaction. Importing the same file twice creates no duplicates.

### Forecast Matching

If virtual transactions match imported transactions (amount within ±10%, date within ±60 days), Budgie suggests linking them automatically. Accept the suggestion to mark the forecast as realized.

---

## 9. Automatic Categorization

Categorization works in two steps:

1. **Payee match** — If the payee has already been manually categorized, that category is reused automatically
2. **Custom rules** — Evaluated by decreasing priority

### Configuring Rules

In **Settings → Rules**:
- **Field**: search in payee name or memo
- **Type**: contains, exact match, or regular expression
- **Category**: the category to assign
- **Priority**: higher priority rules are evaluated first
- **Amount range** *(optional)*: restrict the rule to transactions whose absolute amount falls between a minimum and/or maximum value
- **Transaction type** *(optional)*: restrict the rule to debits only, credits only, or both (default: any)

### Automatic Rule Creation During Reconciliation

In the **Reconciliation view**, when linking a bank transaction to an expense via the wizard, a categorization rule can be created automatically. A **toggle** in the wizard lets you skip rule creation if you do not want a rule saved for that particular link.

---

## 10. The Budget (Envelopes)

### How It Works

Each envelope shows three values:

| Value | Meaning |
|---|---|
| **Budgeted** | Amount allocated this month |
| **Activity** | Total transactions (real + virtual) across the envelope's categories |
| **Available** | Budgeted − Activity (cumulative if rollover is enabled) |

### Rollover

- **Enabled**: available is the cumulative sum of (Budgeted − Activity) across all months up to the current one. Ideal for irregular expenses (repairs, vacations…).
- **Disabled**: available covers the current month only

### To Be Budgeted

At the top of the budget page: **Total Income − Total Budgeted**. The goal is **zero** — every centime assigned.

### Editing the Budget

Click the **Budgeted** amount of any envelope to enter a new value. Changes are saved automatically.

---

## 11. Virtual Transactions (Forecasts)

### Creating a Forecast

In the **Expenses** view, create a new virtual transaction with:
- **Amount**, **estimated date**, **category**, **memo**, **account**

The forecast appears with an ⏳ icon and dashed style. The envelope's **Available** amount is immediately reduced.

### Realization

When importing a bank statement, Budgie suggests linking real transactions to matching forecasts. The forecast is then marked as *reconciled*.

### Viewing Pending Forecasts

In **Expenses**, filter by envelope or group to see forecasts not yet realized.

---

## 12. Quick Expense

The **Quick Expense** page (⚡) lets you enter a transaction in seconds:

1. Tap on an **envelope** in the budget view to open the Quick Expense sheet
2. Enter the **amount**
3. Optionally add a **memo**, **date**, or mark it as **planned**
4. Submit

The transaction is linked directly to the envelope — no category selection required. If you later want to assign a category, you can edit the transaction.

### Off-budget mode

Tap the **"Off-budget expense"** banner at the bottom of the envelope grid to record a transaction without an envelope. The sheet opens with the header "Off-budget" and saves the transaction with `envelope_id = null`. You can later assign it to an envelope via the Expenses edit modal.

### Presets

You can create **presets** for frequent expenses (e.g. “Bakery — €1.20”). One tap pre-fills the form.

### Geolocation Suggestions

If you allow location access (requires HTTPS), Budgie queries nearby shops via OpenStreetMap and suggests places with matching emojis.

> 📍 Geolocation requires access via HTTPS (reverse proxy) or `localhost`. On iOS Safari, HTTPS is mandatory.

---

## 13. Theme & Mobile Installation (PWA)

### Dark / Light Theme

Click the ☀️ / 🌙 button to toggle between `emerald` (light) and `night` (dark) themes. Your choice is saved and applied automatically.

On first load, the theme follows your operating system's preference.

### Add to Home Screen

On mobile (Android / iOS), open Budgie in your browser and use the **Add to Home Screen** option in the browser menu. The app then opens full-screen, just like a native app.

---

## 14. Docker Deployment

### Deployment on Synology NAS (SSH)

#### Prerequisites

- Synology NAS with **Container Manager** (Docker) installed
- SSH access to the NAS

#### Steps

```bash
# 1. Connect to the NAS
ssh admin@your-nas-ip

# 2. Create the project directory
mkdir -p /volume1/docker/budgie
cd /volume1/docker/budgie

# 3. Clone the repository
git clone https://github.com/davidp57/budgie.git .

# 4. Configure the environment
cp .env.example .env
vi .env
# → SECRET_KEY=$(openssl rand -hex 32)
# → PUID=your_uid (find it with: id -u)
# → PGID=your_gid (find it with: id -g)
# → CORS_ORIGINS=https://budgie.your-domain.com

# 5. Build and start
docker compose up -d --build

# 6. Verify
curl http://localhost:8080/api/health
# → {"status":"ok"}
```

### Deployment via Portainer

If you use **Portainer** to manage your Docker containers:

1. **Navigate** to your Portainer instance (e.g. `https://your-nas:9443`)
2. **Stacks** → **Add stack** → give it a name (e.g. `budgie`)
3. **Web editor** — paste the following YAML:

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

4. **Environment variables** (at the bottom of the form) — add:
   - `SECRET_KEY` = your key (generate one with `openssl rand -hex 32` on your machine)
   - `PUID` = your UID (e.g. `1026` — find it with `id -u` via SSH)
   - `PGID` = your GID (e.g. `100` — find it with `id -g` via SSH)
   - `CORS_ORIGINS` = `https://budgie.your-domain.com`
   - `WEBAUTHN_RP_ID` = your domain without scheme or port (e.g. `budgie.your-domain.com`) — required for Passkeys to work
   - `WEBAUTHN_ORIGIN` = full frontend URL (e.g. `https://budgie.your-domain.com`) — must match exactly what the browser shows

5. **Deploy the stack**

> **Important notes**:
> - **`image:` not `build:`** — Portainer cannot build images from source. The image is automatically published to GHCR by CI.
> - **Named volume** (`budgie-data`) — relative paths (`./data`) don't work in Portainer. For a bind mount, use an absolute path: `/volume1/docker/budgie/data:/app/data`.
> - **Port 8080 often taken** — on Synology, port 8080 may be used by DSM or another container. If you get `port is already allocated`, pick another port (e.g. `8280:8000`). Check which ports are in use: `docker ps --format "table {{.Names}}\t{{.Ports}}" | grep 8080`.
> - **Private registry** — if Portainer can't pull the image, make the package public on GitHub (Settings → Visibility → Public), or add a registry in Portainer (Settings → Registries → Custom: URL `ghcr.io`, username `davidp57`, password = Personal Access Token with `read:packages` scope).

### Synology Reverse Proxy (HTTPS)

To access Budgie via HTTPS with an SSL certificate:

1. **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. Click **Create** and configure:

| Field | Value |
|---|---|
| Description | Budgie |
| Source — Protocol | HTTPS |
| Source — Hostname | `budgie.your-domain.com` |
| Source — Port | 443 |
| Destination — Protocol | HTTP |
| Destination — Hostname | `localhost` |
| Destination — Port | 8280 (or the port chosen in your stack) |

3. **Custom Header** tab → add:
   - `Upgrade` → `$http_upgrade`
   - `Connection` → `$connection_upgrade`

4. **SSL Certificate**: Control Panel → Security → Certificate
   - Use Let's Encrypt (free) or import your own certificate
   - Assign the certificate to the reverse proxy entry

5. Update `CORS_ORIGINS` in `.env` then restart:
```bash
docker compose restart
```

---

## 15. Backups & Updates

### Automatic Backups

Set up a scheduled task in DSM:
1. **Control Panel** → **Task Scheduler** → **Create** → **User-defined script**
2. Schedule: daily at 02:00
3. Script:
```bash
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

Backups are stored in `./data/backups/` and automatically pruned after **7 days** (configurable via `KEEP_DAYS`).

### Manual Backup

```bash
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

### Updates

```bash
cd /volume1/docker/budgie

# Pull latest changes
git pull

# Rebuild and restart
docker compose up -d --build

# Check logs
docker compose logs -f --tail=20 budgie
```

Database migrations run **automatically** on startup — no manual step needed.

---

## 16. FAQ / Troubleshooting

| Problem | Solution |
|---|---|
| **Permission denied** on `data/` | Check that `PUID`/`PGID` match your NAS user (`id -u && id -g`) |
| **Container keeps restarting** | Check logs: `docker compose logs budgie` |
| **Can't reach from other devices** | Verify firewall allows the chosen port (e.g. 8280) |
| **Port is already allocated** | The port is already used by another service. Change the port in your stack (e.g. `8280:8000`). Check: `docker ps \| grep 8080` |
| **CORS errors in browser** | Add your URL to `CORS_ORIGINS` in `.env` and restart |
| **Database locked** | Only one instance should run at a time (SQLite limitation) |
| **Geolocation not working** | Must access via HTTPS (reverse proxy or `localhost`) |
| **Import fails silently** | Check file format. CSV: separator `;` or `,`, UTF-8 or Latin-1 encoding |
| **Duplicate not detected** | Ensure date/amount/description columns are correctly detected in preview |

### Useful Commands

```bash
# View logs in real time
docker compose logs -f budgie

# Restart the container
docker compose restart

# Check health
curl http://localhost:8080/api/health

# Enter the container
docker exec -it budgie /bin/bash

# Manual backup
docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups
```

---

## 17. Security & Encryption

### What Is Encrypted?

Budgie encrypts **all your financial data** at rest in the database:
- Account names
- Transaction amounts, dates, memos
- Category and envelope names
- Payee names
- Budget allocations
- Categorization rules

Only structural identifiers (IDs, foreign keys) remain unencrypted — they reveal no personal information.

### How Does It Work?

When you create your Budgie account, you choose a **passphrase** (a memorable sentence or set of words). This passphrase is used to generate an encryption key via a secure algorithm (Argon2id). All your data is then encrypted with this key using military-grade encryption (AES-256-GCM).

**Key facts:**
- Your encryption key is **never stored** on the server — it only exists in memory while you are logged in.
- When you log out (or your session expires), the key is purged from memory.
- Even the server administrator **cannot read your data** without your passphrase.
- If you lose your passphrase, your data is **permanently unrecoverable** — this is by design.

### Signing In

Budgie offers three ways to authenticate, balancing security with convenience:

| Method | When to use | How it works |
|---|---|---|
| **Passkey (biometric)** | Daily use | Fingerprint or Face ID on your device → unlocks your encryption key stored locally |
| **PIN** | Quick fallback | 4–6 digit PIN → decrypts your locally stored encryption key |
| **Passphrase** | Initial setup, new device, recovery | You type the passphrase → the encryption key is re-derived |

**PIN security**: after 5 failed PIN attempts, the locally stored encryption key is erased. You will need to re-enter your passphrase.

> **PIN requires HTTPS** — the PIN uses the Web Crypto API (`crypto.subtle`) which is only available on secure origins (HTTPS or `localhost`). If the app is served over plain HTTP, the PIN option will not be offered.

### Setting Up Passkeys

1. Log in with your passphrase
2. Go to **Settings → Security**
3. Click **Register Passkey**
4. Follow your device’s biometric prompt (fingerprint, Face ID, Windows Hello…)
5. Done — next time, you can sign in with just your biometric

You can register Passkeys on multiple devices (phone, tablet, laptop).

### Recovery Document (PDF)

At account creation, Budgie generates a **recovery PDF** containing:
- Your passphrase in clear text
- A QR code for quick re-entry
- Verification information (first 8 characters of a key hash)

**Print this document and store it in a safe place** (e.g. a fireproof safe, a safety deposit box). It is your only way to recover access if you forget your passphrase and lose all your devices.

> ⚠️ **Never store this PDF digitally** (not on your phone, not in the cloud, not in email). Anyone with this document can access your data.

### What Happens If…

| Scenario | Outcome |
|---|---|
| I change my phone | Register a new Passkey on the new device. Use passphrase to log in the first time. |
| I forget my PIN | Re-enter your passphrase. You can set a new PIN afterward. |
| I forget my passphrase but have the PDF | Use the passphrase from the printed PDF to recover access. |
| I forget my passphrase AND lose the PDF | **Data is permanently lost.** This is the security trade-off: no admin back door. |
| My NAS is stolen | Thief has encrypted blobs — useless without your passphrase. |
| I want to share with family | Each user has their own passphrase and encryption key. Data is isolated per user. |
