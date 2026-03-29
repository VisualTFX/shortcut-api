"""Security token schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SecurityTokenCreateResponse(BaseModel):
    token: str
    expires_at: datetime


class SecurityTokenValidateResponse(BaseModel):
    validated: bool
    message: str
