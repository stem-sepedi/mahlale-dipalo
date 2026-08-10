"""Tests for /screenshots endpoints — real URL capture."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_screenshot_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/screenshots/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["browser"] == "chromium"
    assert data["status"] in ("not_started", "ok")


@pytest.mark.asyncio
async def test_screenshot_capture_real_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/screenshots/capture", json={"url": "https://example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "path" in data
    assert data["path"].endswith(".png")


@pytest.mark.asyncio
async def test_screenshot_health_after_capture():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/screenshots/capture", json={"url": "https://example.com"})
        resp = await client.get("/screenshots/health")
    data = resp.json()
    assert data["status"] == "ok"
