"""Tests for alias generation service."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.alias_service import _random_string, generate_unique_alias
from app.models.alias import AliasStatus


@pytest.mark.asyncio
async def test_generate_unique_alias(db: AsyncSession) -> None:
    alias = await generate_unique_alias(db)
    assert alias.id is not None
    assert "@" in alias.full_address
    assert alias.domain == "mail-one4all.uk"
    assert alias.status == AliasStatus.reserved


@pytest.mark.asyncio
async def test_alias_unique_constraint(db: AsyncSession) -> None:
    """Two calls must produce different addresses."""
    a1 = await generate_unique_alias(db)
    a2 = await generate_unique_alias(db)
    assert a1.full_address != a2.full_address


@pytest.mark.asyncio
async def test_alias_custom_domain(db: AsyncSession) -> None:
    alias = await generate_unique_alias(db, domain="example.com")
    assert alias.full_address.endswith("@example.com")


@pytest.mark.asyncio
async def test_alias_custom_length(db: AsyncSession) -> None:
    alias = await generate_unique_alias(db, length=6)
    local_part = alias.full_address.split("@")[0]
    assert len(local_part) == 6


def test_random_string_length() -> None:
    charset = "abc123"
    for length in (4, 8, 16):
        result = _random_string(charset, length)
        assert len(result) == length
        assert all(c in charset for c in result)


@pytest.mark.asyncio
async def test_alias_never_deleted(db: AsyncSession) -> None:
    """Expired aliases must stay in the DB."""
    from datetime import datetime, timezone
    from app.models.alias import AliasStatus

    alias = await generate_unique_alias(db)
    alias_id = alias.id
    alias.status = AliasStatus.expired
    alias.expired_at = datetime.now(timezone.utc)
    await db.commit()

    # Alias must still exist
    from sqlalchemy import select
    from app.models.alias import Alias
    found = await db.scalar(select(Alias).where(Alias.id == alias_id))
    assert found is not None
    assert found.status == AliasStatus.expired
