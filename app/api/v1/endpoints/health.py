"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.health import ComponentHealth, HealthResponse
from app.workers import cleanup_worker, gmail_worker

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    # DB check
    db_ok = False
    db_detail = None
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_detail = str(exc)

    # Gmail worker check
    worker_ok = gmail_worker.is_running()
    cleanup_ok = cleanup_worker.is_running()

    overall = "ok" if (db_ok and worker_ok) else "degraded"

    return HealthResponse(
        status=overall,
        app=ComponentHealth(status="ok"),
        db=ComponentHealth(status="ok" if db_ok else "error", detail=db_detail),
        gmail=ComponentHealth(status="ok" if worker_ok else "stopped"),
        worker=ComponentHealth(status="ok" if cleanup_ok else "stopped"),
    )
