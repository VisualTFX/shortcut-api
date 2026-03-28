"""Tests for session service."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import session_service
from app.models.verification_session import SessionStatus


@pytest.mark.asyncio
async def test_create_session(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    assert session.public_id
    assert token
    assert session.status == SessionStatus.waiting
    assert session.alias_address.endswith("@mail-one4all.uk")


@pytest.mark.asyncio
async def test_session_token_required(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    # Wrong token returns None
    result = await session_service.authenticate_session(db, session.public_id, "wrong-token")
    assert result is None
    # Correct token returns session
    result = await session_service.authenticate_session(db, session.public_id, token)
    assert result is not None
    assert result.public_id == session.public_id


@pytest.mark.asyncio
async def test_session_expiry(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    # Backdate expiry
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    result = await session_service.get_status(db, session.public_id, token)
    assert result is not None
    assert result.status == SessionStatus.expired


@pytest.mark.asyncio
async def test_cancel_session(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    cancelled = await session_service.cancel_session(db, session.public_id, token)
    assert cancelled is not None
    assert cancelled.status == SessionStatus.cancelled


@pytest.mark.asyncio
async def test_cancel_wrong_token(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    result = await session_service.cancel_session(db, session.public_id, "bad-token")
    assert result is None


@pytest.mark.asyncio
async def test_expire_old_sessions(db: AsyncSession) -> None:
    session, token = await session_service.create_session(db)
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    await db.commit()

    count = await session_service.expire_old_sessions(db)
    assert count >= 1
