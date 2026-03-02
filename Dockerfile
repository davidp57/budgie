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

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1 \
    && poetry config virtualenvs.create false

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

# Copy backend source
COPY budgie/ ./budgie/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create data directory
RUN mkdir -p /app/data

# Non-root user
RUN useradd --create-home --shell /bin/bash budgie
RUN chown -R budgie:budgie /app/data
USER budgie

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "budgie.main:app", "--host", "0.0.0.0", "--port", "8000"]
