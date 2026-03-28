"""Session schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.verification_session import SessionStatus


class SessionCreate(BaseModel):
    domain: str | None = None
    alias_length: int | None = Field(None, ge=4, le=64)
    source_label: str | None = None
    device_name: str | None = None
    metadata: dict[str, Any] | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    client_token: str
    alias: str
    expires_at: datetime
    status: SessionStatus
    device_name: str | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus
    alias: str
    expires_at: datetime
    last_checked_at: datetime | None = None
    code_found: bool
    completed: bool
    device_name: str | None = None
    error_message: str | None = None


class MessageSummary(BaseModel):
    gmail_message_id: str
    from_address: str | None = None
    subject: str | None = None
    internal_date: datetime | None = None


class SessionResultResponse(BaseModel):
    session_id: str
    status: SessionStatus
    code: str | None = None
    matched_message_summary: MessageSummary | None = None
    completed_at: datetime | None = None


class SessionCancelResponse(BaseModel):
    session_id: str
    status: SessionStatus
