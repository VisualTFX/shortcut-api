"""ParsingRule schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ParsingRuleCreate(BaseModel):
    name: str
    enabled: bool = True
    priority: int = Field(100, ge=0)
    sender_pattern: str | None = None
    subject_pattern: str | None = None
    body_regex: str
    code_capture_group: int = Field(1, ge=1)
    description: str | None = None


class ParsingRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    priority: int | None = Field(None, ge=0)
    sender_pattern: str | None = None
    subject_pattern: str | None = None
    body_regex: str | None = None
    code_capture_group: int | None = Field(None, ge=1)
    description: str | None = None


class ParsingRuleOut(BaseModel):
    id: int
    name: str
    enabled: bool
    priority: int
    sender_pattern: str | None = None
    subject_pattern: str | None = None
    body_regex: str
    code_capture_group: int
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
