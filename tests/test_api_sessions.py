"""Integration tests for session API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "client_token" in data
    assert "alias" in data
    assert data["alias"].endswith("@mail-one4all.uk")
    assert data["status"] == "waiting"


@pytest.mark.asyncio
async def test_get_status_requires_token(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/sessions", json={})
    session_id = create_resp.json()["session_id"]

    resp = await client.get(f"/api/v1/sessions/{session_id}/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_status_wrong_token(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/sessions", json={})
    session_id = create_resp.json()["session_id"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": "wrong"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_correct_token(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/sessions", json={})
    data = create_resp.json()
    session_id = data["session_id"]
    token = data["client_token"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": token},
    )
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["session_id"] == session_id
    assert status_data["status"] == "waiting"
    assert status_data["code_found"] is False


@pytest.mark.asyncio
async def test_get_result_waiting(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/sessions", json={})
    data = create_resp.json()

    resp = await client.get(
        f"/api/v1/sessions/{data['session_id']}/result",
        headers={"X-Client-Token": data["client_token"]},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "waiting"
    assert result["code"] is None


@pytest.mark.asyncio
async def test_cancel_session(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/sessions", json={})
    data = create_resp.json()

    resp = await client.post(
        f"/api/v1/sessions/{data['session_id']}/cancel",
        headers={"X-Client-Token": data["client_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["db"]["status"] == "ok"


@pytest.mark.asyncio
async def test_admin_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/sessions")
    assert resp.status_code in (403, 422)  # missing header


@pytest.mark.asyncio
async def test_admin_with_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/admin/sessions", headers={"X-Admin-Token": "change-me"}
    )
    assert resp.status_code == 200
