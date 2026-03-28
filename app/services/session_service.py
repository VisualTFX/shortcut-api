"""Session lifecycle service."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import generate_token, hash_token, verify_token
from app.models.alias import Alias, AliasStatus
from app.models.verification_session import SessionStatus, VerificationSession
from app.services.alias_service import generate_unique_alias
from app.utils.tokens import generate_public_id

logger = get_logger(__name__)


async def create_session(
    db: AsyncSession,
    *,
    domain: str | None = None,
    alias_length: int | None = None,
    source_label: str | None = None,
    metadata: dict | None = None,
) -> tuple[VerificationSession, str]:
    """
    Create a new VerificationSession.

    Returns (session, raw_client_token).  The raw token is only returned here
    and is never persisted — only its hash is stored.
    """
    settings = get_settings()
    alias = await generate_unique_alias(db, domain=domain, length=alias_length)

    raw_token = generate_token()
    token_hash = hash_token(raw_token)
    public_id = generate_public_id()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.session_ttl_seconds)

    session = VerificationSession(
        public_id=public_id,
        client_token_hash=token_hash,
        alias_id=alias.id,
        alias_address=alias.full_address,
        status=SessionStatus.waiting,
        created_at=now,
        expires_at=expires_at,
        source_label=source_label,
        metadata_=json.dumps(metadata) if metadata else None,
    )
    db.add(session)

    alias.status = AliasStatus.waiting
    alias.session_id = public_id

    await db.commit()
    await db.refresh(session)
    logger.info(
        "Created session %s alias=%s expires=%s",
        public_id,
        alias.full_address,
        expires_at.isoformat(),
    )
    return session, raw_token


async def get_session_by_public_id(
    db: AsyncSession, public_id: str
) -> VerificationSession | None:
    return await db.scalar(
        select(VerificationSession).where(VerificationSession.public_id == public_id)
    )


async def authenticate_session(
    db: AsyncSession, public_id: str, raw_token: str
) -> VerificationSession | None:
    """Return session if token matches, else None."""
    session = await get_session_by_public_id(db, public_id)
    if session is None:
        return None
    if not verify_token(raw_token, session.client_token_hash):
        return None
    return session


async def get_status(
    db: AsyncSession, public_id: str, raw_token: str
) -> VerificationSession | None:
    session = await authenticate_session(db, public_id, raw_token)
    if session is None:
        return None
    await _maybe_expire(db, session)
    session.last_checked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


async def get_result(
    db: AsyncSession, public_id: str, raw_token: str
) -> VerificationSession | None:
    return await get_status(db, public_id, raw_token)


async def cancel_session(
    db: AsyncSession, public_id: str, raw_token: str
) -> VerificationSession | None:
    session = await authenticate_session(db, public_id, raw_token)
    if session is None:
        return None

    if session.status in (
        SessionStatus.extracted,
        SessionStatus.expired,
        SessionStatus.failed,
        SessionStatus.cancelled,
    ):
        return session  # already terminal

    session.status = SessionStatus.cancelled
    session.completed_at = datetime.now(timezone.utc)

    # Retire the alias
    alias = await db.get(Alias, session.alias_id)
    if alias:
        alias.status = AliasStatus.retired
        alias.retired_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    logger.info("Cancelled session %s", public_id)
    return session


async def expire_old_sessions(db: AsyncSession) -> int:
    """Expire sessions past their TTL. Returns count expired."""
    now = datetime.now(timezone.utc)
    result = await db.scalars(
        select(VerificationSession).where(
            VerificationSession.status.in_(
                [SessionStatus.waiting, SessionStatus.received, SessionStatus.reserved]
            ),
            VerificationSession.expires_at < now,
        )
    )
    sessions = result.all()
    count = 0
    for sess in sessions:
        sess.status = SessionStatus.expired
        alias = await db.get(Alias, sess.alias_id)
        if alias:
            alias.status = AliasStatus.expired
            alias.expired_at = now
        count += 1
    if count:
        await db.commit()
        logger.info("Expired %d sessions", count)
    return count


async def _maybe_expire(db: AsyncSession, session: VerificationSession) -> None:
    if session.status in (SessionStatus.waiting, SessionStatus.received, SessionStatus.reserved):
        now = datetime.now(timezone.utc)
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            session.status = SessionStatus.expired
            alias = await db.get(Alias, session.alias_id)
            if alias:
                alias.status = AliasStatus.expired
                alias.expired_at = now
            await db.commit()
            await db.refresh(session)
