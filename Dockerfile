# ── Stage 1: Build Vue.js frontend ──────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system dependencies:
#   gosu: privilege-drop tool used by entrypoint.sh for PUID/PGID support
RUN apt-get update && apt-get install -y --no-install-recommends \
        gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1 \
    && poetry config virtualenvs.create false

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi --no-root

# Copy backend source
COPY budgie/ ./budgie/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install the budgie package itself (generates metadata for importlib.metadata.version())
RUN poetry install --only-root --no-interaction --no-ansi

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create user and data directory
# Container starts as root; entrypoint.sh drops to budgie with correct UID/GID
RUN useradd --create-home --shell /bin/bash budgie \
    && mkdir -p /app/data/uploads \
    && chown -R budgie:budgie /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "budgie.main:app", "--host", "0.0.0.0", "--port", "8000"]
