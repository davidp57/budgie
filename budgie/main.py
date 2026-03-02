"""FastAPI application entry point.

Creates and configures the FastAPI app with CORS, routers,
and a health check endpoint.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from budgie.api import (
    accounts,
    auth,
    budget,
    categories,
    categorize,
    category_groups,
    category_rules,
    envelopes,
    imports,
    payees,
    transactions,
)
from budgie.config import BASE_DIR, settings


def _run_migrations() -> None:
    """Run Alembic ``upgrade head`` synchronously.

    Intended to be called once at application startup via
    :func:`asyncio.to_thread` so as not to block the event loop.
    """
    cfg = AlembicConfig(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler.

    Runs Alembic migrations and creates required directories on startup.

    Args:
        app: The FastAPI application instance.
    """
    # Apply any pending database migrations before accepting traffic
    await asyncio.to_thread(_run_migrations)
    # Ensure data directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Budgie",
    description="Personal household budget management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Docker production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker and monitoring.

    Returns:
        A dict with status "ok".
    """
    return {"status": "ok"}


# Register all API routers
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(category_groups.router)
app.include_router(categories.router)
app.include_router(payees.router)
app.include_router(transactions.router)
app.include_router(envelopes.router)
app.include_router(budget.router)
app.include_router(imports.router)
app.include_router(categorize.router)
app.include_router(category_rules.router)

# ── Production static file serving ──────────────────────────────────────────
# When the Vue dist folder exists (Docker production build), serve the SPA.
# In development, Vite runs its own dev server; this block is skipped.
_FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    # Serve compiled assets (JS, CSS, icons)
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Catch-all route — serves the Vue SPA index for client-side routing.

        Args:
            full_path: Any unmatched URL path.

        Returns:
            The Vue dist/index.html file.
        """
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
