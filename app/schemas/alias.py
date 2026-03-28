"""Alias schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.alias import AliasStatus


class AliasOut(BaseModel):
    id: int
    local_part: str
    domain: str
    full_address: str
    status: AliasStatus
    created_at: datetime
    reserved_at: datetime | None = None
    used_at: datetime | None = None
    expired_at: datetime | None = None
    retired_at: datetime | None = None
    was_recycled: bool

    model_config = {"from_attributes": True}
