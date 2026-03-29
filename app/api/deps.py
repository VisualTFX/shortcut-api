"""FastAPI dependencies."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.session import get_db  # re-export for convenience

__all__ = ["get_db", "require_admin", "require_validated_security_token"]


async def require_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> None:
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")


async def require_validated_security_token(
    x_security_token: str | None = Header(None, alias="X-Security-Token"),
    db: AsyncSession = Depends(get_db),
) -> str:
    if not x_security_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Security-Token header required",
        )

    from app.models.security_token import SecurityToken  # avoid circular import at module level

    token_hash = hash_token(x_security_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(SecurityToken).where(SecurityToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if (
        db_token is None
        or not db_token.validated
        or db_token.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unvalidated security token",
        )

    return x_security_token
