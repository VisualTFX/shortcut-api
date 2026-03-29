"""Security endpoints: token creation and validation."""
from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_token
from app.models.security_token import SecurityToken
from app.schemas.security_token import SecurityTokenCreateResponse, SecurityTokenValidateResponse

router = APIRouter()

_ALPHABET = string.ascii_letters + string.digits
_PREFIX = "TFX-iOS-"
_TOKEN_RANDOM_LENGTH = 32


def _generate_security_token() -> str:
    random_part = "".join(secrets.choice(_ALPHABET) for _ in range(_TOKEN_RANDOM_LENGTH))
    return f"{_PREFIX}{random_part}"


@router.post(
    "/securitytoken",
    response_model=SecurityTokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_security_token(
    db: AsyncSession = Depends(get_db),
) -> SecurityTokenCreateResponse:
    settings = get_settings()
    raw_token = _generate_security_token()
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.security_token_ttl_seconds)

    db_token = SecurityToken(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        validated=False,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.commit()

    return SecurityTokenCreateResponse(token=raw_token, expires_at=expires_at)


@router.post("/validate", response_model=SecurityTokenValidateResponse)
async def validate_security_token(
    x_security_token: str = Header(..., alias="X-Security-Token"),
    db: AsyncSession = Depends(get_db),
) -> SecurityTokenValidateResponse:
    token_hash = hash_token(x_security_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(SecurityToken).where(SecurityToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security token not found",
        )

    if db_token.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security token has expired",
        )

    if db_token.validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security token already validated",
        )

    db_token.validated = True
    await db.commit()

    return SecurityTokenValidateResponse(
        validated=True, message="Security token validated successfully"
    )
