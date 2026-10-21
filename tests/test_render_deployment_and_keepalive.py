"""Tests for Render Production Deployment readiness, Anti-Sleep Keep-Alive Service,
and Health/Root endpoints.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.keep_alive_service import (
    get_keep_alive_stats,
    resolve_keep_alive_url,
    start_keep_alive,
    stop_keep_alive,
)


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint_redirects_to_admin(client):
    """Verify visiting root / redirects seamlessly to the admin dashboard."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/admin/"


def test_health_endpoint_basic(client):
    """Verify /health returns 200 OK with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_endpoint_details(client):
    """Verify /health?details=true includes keep-alive stats and uptime."""
    response = client.get("/health?details=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "keep_alive" in data
    assert "total_pings" in data["keep_alive"]


def test_resolve_keep_alive_url_precedence():
    """Verify URL resolution from RENDER_EXTERNAL_URL, RENDER_EXTERNAL_HOSTNAME, and KEEP_ALIVE_URL."""
    # 1. RENDER_EXTERNAL_URL
    with patch.dict(os.environ, {"RENDER_EXTERNAL_URL": "https://my-clinic.onrender.com"}, clear=False):
        assert resolve_keep_alive_url() == "https://my-clinic.onrender.com"

    # 2. RENDER_EXTERNAL_HOSTNAME
    with patch.dict(os.environ, {"RENDER_EXTERNAL_URL": "", "RENDER_EXTERNAL_HOSTNAME": "my-clinic.onrender.com"}, clear=False):
        assert resolve_keep_alive_url() == "https://my-clinic.onrender.com"

    # 3. Explicit KEEP_ALIVE_URL override
    with patch.dict(os.environ, {
        "KEEP_ALIVE_URL": "https://custom-domain.com",
        "RENDER_EXTERNAL_URL": "https://my-clinic.onrender.com"
    }, clear=False):
        assert resolve_keep_alive_url() == "https://custom-domain.com"


@pytest.mark.asyncio
async def test_keep_alive_start_and_stop():
    """Verify background task lifecycle does not raise errors."""
    with patch.dict(os.environ, {"RENDER_EXTERNAL_URL": "https://test-clinic.onrender.com"}):
        task = start_keep_alive()
        assert task is not None
        stats = get_keep_alive_stats()
        assert stats["enabled"] is True
        assert stats["target_url"] == "https://test-clinic.onrender.com"

        # Stop task
        stop_keep_alive()
        await asyncio.sleep(0.01)
        assert task.cancelled() or task.done()

