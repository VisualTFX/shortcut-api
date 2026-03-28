"""Health schemas."""
from __future__ import annotations

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: ComponentHealth
    db: ComponentHealth
    gmail: ComponentHealth
    worker: ComponentHealth
