"""Shared pytest fixtures."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db import session as db_session_module
from app.main import create_app
from app.parsing.default_rules import DEFAULT_RULES
from app.models.parsing_rule import ParsingRule

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    """DB session with default parsing rules seeded."""
    from sqlalchemy import select, func
    count = await db.scalar(select(func.count()).select_from(ParsingRule))
    if count == 0:
        for rule_data in DEFAULT_RULES:
            db.add(ParsingRule(**rule_data))
        await db.commit()
    return db


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with in-memory DB."""
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    # Monkey-patch the session factory
    db_session_module._engine = engine
    db_session_module._session_factory = factory

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
