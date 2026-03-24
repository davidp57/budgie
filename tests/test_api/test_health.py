"""Tests for the health check endpoint."""

import pytest
from budgie import __version__
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient) -> None:
    """Health check should return status, app name and version."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Budgie"
    assert data["version"] == __version__
