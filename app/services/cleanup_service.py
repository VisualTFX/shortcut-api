"""Cleanup service — remove/expire stale data."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.incoming_message import IncomingMessage
from app.services.session_service import expire_old_sessions, timeout_stale_sessions

logger = get_logger(__name__)


async def run_cleanup(db: AsyncSession) -> dict:
    settings = get_settings()
    timed_out = await timeout_stale_sessions(db)
    expired = await expire_old_sessions(db)
    result = {"expired_sessions": expired, "timed_out_sessions": timed_out}

    if settings.retention_enabled:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
        if settings.retention_redact_body:
            msgs = await db.scalars(
                select(IncomingMessage).where(IncomingMessage.created_at < cutoff)
            )
            redacted = 0
            for msg in msgs.all():
                if msg.raw_text or msg.raw_html:
                    msg.raw_text = None
                    msg.raw_html = None
                    redacted += 1
            if redacted:
                await db.commit()
            result["redacted_messages"] = redacted
        else:
            del_result = await db.execute(
                delete(IncomingMessage).where(IncomingMessage.created_at < cutoff)
            )
            await db.commit()
            result["deleted_messages"] = del_result.rowcount  # type: ignore[attr-defined]

    logger.info("Cleanup complete: %s", result)
    return result
