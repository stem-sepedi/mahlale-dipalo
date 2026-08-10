"""Tests for /search, /review, /reviews, /users endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_search_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/search?q=photosynthesis")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_with_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/register", json={
            "username": "test_search_user",
            "password": "pass123",
        })
        token = resp.json()["access_token"]
        resp = await client.get("/search?q=test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "results" in resp.json()
        assert "facets" in resp.json()


@pytest.mark.asyncio
async def test_users_me():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/register", json={
            "username": "test_user_me",
            "password": "pass123",
            "role": "translator",
        })
        token = resp.json()["access_token"]
        resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "test_user_me"
        assert resp.json()["role"] == "translator"


@pytest.mark.asyncio
async def test_users_list_requires_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/register", json={
            "username": "test_user_list_nonadmin",
            "password": "pass123",
            "role": "learner",
        })
        token = resp.json()["access_token"]
        resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
