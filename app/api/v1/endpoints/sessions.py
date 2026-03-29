"""Session endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_validated_security_token
from app.models.verification_session import SessionStatus
from app.schemas.message import IncomingMessageOut
from app.schemas.session import (
    MessageSummary,
    SessionCancelResponse,
    SessionCreate,
    SessionCreateResponse,
    SessionResultResponse,
    SessionStatusResponse,
)
from app.services import session_service
from app.models.incoming_message import IncomingMessage
from sqlalchemy import select

router = APIRouter()


def _require_token(x_client_token: str | None = Header(None, alias="X-Client-Token")) -> str:
    if not x_client_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Client-Token header required",
        )
    return x_client_token


@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    _security_token: str = Depends(require_validated_security_token),
) -> SessionCreateResponse:
    session, raw_token = await session_service.create_session(
        db,
        domain=body.domain,
        alias_length=body.alias_length,
        source_label=body.source_label,
        device_name=body.device_name,
        metadata=body.metadata,
    )
    return SessionCreateResponse(
        session_id=session.public_id,
        client_token=raw_token,
        alias=session.alias_address,
        expires_at=session.expires_at,
        status=session.status,
        device_name=session.device_name,
    )


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_require_token),
    _security_token: str = Depends(require_validated_security_token),
) -> SessionStatusResponse:
    session = await session_service.get_status(db, session_id, token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionStatusResponse(
        session_id=session.public_id,
        status=session.status,
        alias=session.alias_address,
        expires_at=session.expires_at,
        last_checked_at=session.last_checked_at,
        code_found=session.extracted_code is not None,
        completed=session.status == SessionStatus.extracted,
        device_name=session.device_name,
        error_message=session.error_message,
    )


@router.get("/sessions/{session_id}/result", response_model=SessionResultResponse, response_model_exclude_none=True)
async def get_session_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_require_token),
    _security_token: str = Depends(require_validated_security_token),
) -> SessionResultResponse:
    session = await session_service.get_result(db, session_id, token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    summary: MessageSummary | None = None
    if session.matched_message_id:
        msg = await db.scalar(
            select(IncomingMessage).where(
                IncomingMessage.gmail_message_id == session.matched_message_id
            )
        )
        if msg:
            summary = MessageSummary(
                gmail_message_id=msg.gmail_message_id,
                from_address=msg.from_address,
                subject=msg.subject,
                internal_date=msg.internal_date,
            )

    return SessionResultResponse(
        session_id=session.public_id,
        status=session.status,
        code=session.extracted_code,
        matched_message_summary=summary,
        completed_at=session.completed_at,
    )


@router.post("/sessions/{session_id}/cancel", response_model=SessionCancelResponse)
async def cancel_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_require_token),
    _security_token: str = Depends(require_validated_security_token),
) -> SessionCancelResponse:
    session = await session_service.cancel_session(db, session_id, token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionCancelResponse(session_id=session.public_id, status=session.status)
