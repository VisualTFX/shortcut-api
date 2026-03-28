"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import admin, health, sessions

router = APIRouter(prefix="/api/v1")
router.include_router(sessions.router, tags=["sessions"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])

health_router = APIRouter()
health_router.include_router(health.router)
