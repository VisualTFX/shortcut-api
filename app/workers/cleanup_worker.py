"""Cleanup background worker."""
from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.services.cleanup_service import run_cleanup

logger = get_logger(__name__)

_worker_task: asyncio.Task | None = None
_is_running: bool = False

CLEANUP_INTERVAL_SECONDS = 60


def is_running() -> bool:
    return _is_running


async def start_cleanup_worker() -> None:
    global _worker_task, _is_running
    if _worker_task and not _worker_task.done():
        return
    _is_running = True
    _worker_task = asyncio.create_task(_cleanup_loop(), name="cleanup_worker")
    logger.info("Cleanup worker started")


async def stop_cleanup_worker() -> None:
    global _is_running
    _is_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Cleanup worker stopped")


async def _cleanup_loop() -> None:
    while _is_running:
        try:
            factory = get_session_factory()
            async with factory() as db:
                await run_cleanup(db)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Cleanup worker error: %s", exc)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
