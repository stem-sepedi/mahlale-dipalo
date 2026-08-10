"""Tests for /auth endpoints — register, login, refresh, logout."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_register_and_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register
        resp = await client.post("/auth/register", json={
            "username": "testuser_auth",
            "password": "testpass123",
            "role": "learner",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

        # Login
        resp = await client.post("/auth/login", json={
            "username": "testuser_auth",
            "password": "testpass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/login", json={
            "username": "nonexistent_user",
            "password": "wrong",
        })
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/auth/register", json={
            "username": "testuser_dup",
            "password": "pass123",
        })
        resp = await client.post("/auth/register", json={
            "username": "testuser_dup",
            "password": "pass123",
        })
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_refresh_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/register", json={
            "username": "testuser_refresh",
            "password": "pass123",
        })
        refresh = resp.json()["refresh_token"]
        resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_logout():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/auth/register", json={
            "username": "testuser_logout",
            "password": "pass123",
        })
        token = resp.json()["access_token"]
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"
