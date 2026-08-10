"""Tests for /concepts CRUD endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


async def _get_teacher_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/register", json={
        "username": "test_teacher_concepts",
        "password": "pass123",
        "role": "teacher",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_concepts_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _get_teacher_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create
        resp = await client.post("/concepts", json={
            "name_en": "Test Concept CRUD",
            "definition_en": "A test concept for CRUD operations.",
            "domain": "Biology",
            "grade_levels": [8, 10],
        }, headers=headers)
        assert resp.status_code == 201
        concept = resp.json()["concept"]
        cid = concept["id"]
        assert concept["name_en"] == "Test Concept CRUD"
        assert concept["status"] == "draft"

        # Read
        resp = await client.get(f"/concepts/{cid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name_en"] == "Test Concept CRUD"

        # Update
        resp = await client.patch(f"/concepts/{cid}", json={
            "name_en": "Updated Concept",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name_en"] == "Updated Concept"

        # List
        resp = await client.get("/concepts?status=draft", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_concept_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _get_teacher_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/concepts/00000000-0000-0000-0000-000000000000", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_concept_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/concepts")
        assert resp.status_code == 401
