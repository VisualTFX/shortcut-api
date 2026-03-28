"""FastAPI application factory and startup/shutdown lifecycle."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import health_router, router as api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.session import get_engine
from app.parsing.default_rules import DEFAULT_RULES
from app.workers.cleanup_worker import start_cleanup_worker, stop_cleanup_worker
from app.workers.gmail_worker import start_worker as start_gmail_worker
from app.workers.gmail_worker import stop_worker as stop_gmail_worker

logger = get_logger(__name__)


async def _ensure_tables() -> None:
    """Create all tables on startup (dev/SQLite convenience)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_default_rules() -> None:
    """Insert default parsing rules if the table is empty."""
    from sqlalchemy import select, func
    from app.db.session import get_session_factory
    from app.models.parsing_rule import ParsingRule

    factory = get_session_factory()
    async with factory() as db:
        count = await db.scalar(select(func.count()).select_from(ParsingRule))
        if count == 0:
            for rule_data in DEFAULT_RULES:
                db.add(ParsingRule(**rule_data))
            await db.commit()
            logger.info("Seeded %d default parsing rules", len(DEFAULT_RULES))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    settings = get_settings()
    logger.info("Starting Shortcut API (strategy=%s)", settings.gmail_strategy)

    # Ensure DB schema exists
    await _ensure_tables()
    await _seed_default_rules()

    # Start background workers
    await start_gmail_worker()
    await start_cleanup_worker()

    yield

    # Graceful shutdown
    await stop_gmail_worker()
    await stop_cleanup_worker()
    logger.info("Shortcut API shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Shortcut Email Alias API",
        version="0.1.0",
        description=(
            "Backend for iOS Shortcut: generates one-time email aliases and "
            "extracts verification codes from incoming Gmail messages."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten for production
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
