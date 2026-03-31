# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| Latest on `main` | ✅ |
| Older versions | ❌ |

Budgie is a self-hosted personal application. Only the latest release is actively maintained.

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in Budgie, report it responsibly:

1. **Open a [GitHub Security Advisory](https://github.com/davidp57/budgie/security/advisories/new)** (preferred — keeps the report private until a fix is ready).
2. Or contact the maintainer directly via their [GitHub profile](https://github.com/davidp57).

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Your suggested fix (if any)

We will acknowledge your report within **72 hours** and aim to release a fix within **14 days** for critical issues.

---

## Security Design

### Authentication

- Passwords are hashed with **bcrypt** (cost factor 12)
- Sessions use **JWT** (HS256) with a configurable expiry (default: 24 h)
- The `SECRET_KEY` in `.env` is the JWT signing key — **never commit it to a repository**
- **WebAuthn / Passkeys** are supported as a second authentication factor

### Data

- All data is stored locally in a **SQLite** database — nothing is sent to any external service
- Monetary amounts are stored as **integer centimes** (no floating-point rounding errors)
- Uploaded bank files are stored temporarily and deleted after import

### Network

- **CORS** is enforced via an explicit `CORS_ORIGINS` allowlist
- The API rejects requests from unauthorized origins
- Deployed behind a reverse proxy (nginx, Synology DSM) for TLS termination

### Dependencies

- Backend dependencies are pinned in `poetry.lock`
- Frontend dependencies are pinned in `package-lock.json`
- Dependabot is configured to alert on outdated dependencies

---

## Out of Scope

The following are **not considered security issues** for this project:

- Vulnerabilities in dependencies not yet fixed upstream
- Issues requiring physical access to the host machine
- Denial-of-service attacks against a personal self-hosted instance
- Security issues in the Docker host or Synology DSM itself

---

## Responsible Disclosure

We follow a **coordinated disclosure** policy. We ask that you give us reasonable time to fix the issue before publishing details publicly.

We appreciate responsible security researchers and will credit you in the release notes (unless you prefer to remain anonymous).
