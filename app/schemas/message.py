"""Message schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IncomingMessageOut(BaseModel):
    id: int
    gmail_message_id: str
    thread_id: str | None = None
    to_address: str
    delivered_alias: str
    from_address: str | None = None
    subject: str | None = None
    internal_date: datetime | None = None
    snippet: str | None = None
    parsed_code: str | None = None
    parsed_at: datetime | None = None
    session_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
