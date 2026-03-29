"""Tests for security token endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _get_validated_token(client: AsyncClient) -> str:
    """Create and validate a security token, returning the raw token string."""
    create_resp = await client.post("/api/v1/securitytoken")
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]

    validate_resp = await client.post(
        "/api/v1/validate", headers={"X-Security-Token": token}
    )
    assert validate_resp.status_code == 200
    return token


# ── POST /api/v1/securitytoken ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_security_token_returns_tfx_prefix(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/securitytoken")
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert "expires_at" in data
    token = data["token"]
    assert token.startswith("TFX-iOS-")
    # 32 alphanumeric characters after the prefix
    random_part = token[len("TFX-iOS-"):]
    assert len(random_part) == 32
    assert random_part.isalnum()


# ── POST /api/v1/validate ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_token_succeeds(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/securitytoken")
    token = create_resp.json()["token"]

    resp = await client.post("/api/v1/validate", headers={"X-Security-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["validated"] is True


@pytest.mark.asyncio
async def test_validate_unknown_token_returns_400(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/validate", headers={"X-Security-Token": "TFX-iOS-not-a-real-token12345678901"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_validate_already_validated_token_returns_400(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/securitytoken")
    token = create_resp.json()["token"]

    # First validation succeeds
    resp1 = await client.post("/api/v1/validate", headers={"X-Security-Token": token})
    assert resp1.status_code == 200

    # Second validation on the same token fails
    resp2 = await client.post("/api/v1/validate", headers={"X-Security-Token": token})
    assert resp2.status_code == 400


# ── Session endpoints: security token enforcement ────────────────────────────


@pytest.mark.asyncio
async def test_create_session_without_security_token_returns_400(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_session_with_unvalidated_security_token_returns_400(
    client: AsyncClient,
) -> None:
    create_resp = await client.post("/api/v1/securitytoken")
    raw_token = create_resp.json()["token"]

    # Do NOT validate — use the unvalidated token directly
    resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": raw_token}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_session_with_validated_security_token_succeeds(
    client: AsyncClient,
) -> None:
    token = await _get_validated_token(client)

    resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": token}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "client_token" in data


@pytest.mark.asyncio
async def test_session_status_requires_security_token(client: AsyncClient) -> None:
    token = await _get_validated_token(client)

    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": token}
    )
    session_id = create_resp.json()["session_id"]
    client_token = create_resp.json()["client_token"]

    # Without security token → 400
    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": client_token},
    )
    assert resp.status_code == 400

    # With security token → 200
    resp = await client.get(
        f"/api/v1/sessions/{session_id}/status",
        headers={"X-Client-Token": client_token, "X-Security-Token": token},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_session_result_requires_security_token(client: AsyncClient) -> None:
    token = await _get_validated_token(client)

    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": token}
    )
    session_id = create_resp.json()["session_id"]
    client_token = create_resp.json()["client_token"]

    # Without security token → 400
    resp = await client.get(
        f"/api/v1/sessions/{session_id}/result",
        headers={"X-Client-Token": client_token},
    )
    assert resp.status_code == 400

    # With security token → 200
    resp = await client.get(
        f"/api/v1/sessions/{session_id}/result",
        headers={"X-Client-Token": client_token, "X-Security-Token": token},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cancel_session_requires_security_token(client: AsyncClient) -> None:
    token = await _get_validated_token(client)

    create_resp = await client.post(
        "/api/v1/sessions", json={}, headers={"X-Security-Token": token}
    )
    session_id = create_resp.json()["session_id"]
    client_token = create_resp.json()["client_token"]

    # Without security token → 400
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/cancel",
        headers={"X-Client-Token": client_token},
    )
    assert resp.status_code == 400

    # With security token → 200
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/cancel",
        headers={"X-Client-Token": client_token, "X-Security-Token": token},
    )
    assert resp.status_code == 200
