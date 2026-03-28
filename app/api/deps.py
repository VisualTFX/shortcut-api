"""FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings
from app.db.session import get_db  # re-export for convenience

__all__ = ["get_db", "require_admin"]


async def require_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> None:
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
