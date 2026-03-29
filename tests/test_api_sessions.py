"""Integration tests for session API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _get_validated_token(client: AsyncClient) -> str:
    """Create and validate a security token, returning the raw token string."""
    create_resp = await client.post("/api/v1/securitytoken")
    token = create_resp.json()["token"]
    await client.post("/api/v1/validate", headers={"X-Security-Token": token})
    return token


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient) -> None:
    token = await _get_validated_token(client)
    resp = await client.post("/api/v1/sessions", json={}, headers={"X-Security-Token": token})
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "client_token" in data
    assert "alias" in data
    assert data["alias"].endswith("@mail-one4all.uk")
    assert data["status"] == "waiting"


@pytest.mark.asyncio
async def test_get_status_requires_token(client: AsyncClient) -> None:
    sec_token = await _get_validated_token(client)
    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": sec_token}
    )
    session_id = create_resp.json()["session_id"]

    # Security token present but no client token → still 401
    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Security-Token": sec_token},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_status_wrong_token(client: AsyncClient) -> None:
    sec_token = await _get_validated_token(client)
    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": sec_token}
    )
    session_id = create_resp.json()["session_id"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": "wrong", "X-Security-Token": sec_token},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_correct_token(client: AsyncClient) -> None:
    sec_token = await _get_validated_token(client)
    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": sec_token}
    )
    data = create_resp.json()
    session_id = data["session_id"]
    token = data["client_token"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": token, "X-Security-Token": sec_token},
    )
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["session_id"] == session_id
    assert status_data["status"] == "waiting"
    assert status_data["code_found"] is False


@pytest.mark.asyncio
async def test_get_result_waiting(client: AsyncClient) -> None:
    sec_token = await _get_validated_token(client)
    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": sec_token}
    )
    data = create_resp.json()

    resp = await client.get(
        f"/api/v1/sessions/{data['session_id']}/result",
        headers={"X-Client-Token": data["client_token"], "X-Security-Token": sec_token},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "waiting"
    assert "code" not in result


@pytest.mark.asyncio
async def test_cancel_session(client: AsyncClient) -> None:
    sec_token = await _get_validated_token(client)
    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": sec_token}
    )
    data = create_resp.json()

    resp = await client.post(
        f"/api/v1/sessions/{data['session_id']}/cancel",
        headers={"X-Client-Token": data["client_token"], "X-Security-Token": sec_token},
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

