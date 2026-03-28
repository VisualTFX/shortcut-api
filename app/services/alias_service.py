"""Alias generation service."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.alias import Alias, AliasStatus

logger = get_logger(__name__)

MAX_RETRIES = 100


async def generate_unique_alias(
    db: AsyncSession,
    *,
    domain: str | None = None,
    length: int | None = None,
) -> Alias:
    """
    Generate a cryptographically random alias that has NEVER existed in the
    database before.  Loops with retry until a unique address is obtained.
    Handles race conditions by catching IntegrityError on the unique constraint.
    """
    settings = get_settings()
    use_domain = domain or settings.alias_domain
    use_length = length or settings.alias_length
    charset = settings.alias_charset
    prefix = settings.alias_prefix
    suffix = settings.alias_suffix

    for attempt in range(MAX_RETRIES):
        local_part = prefix + _random_string(charset, use_length) + suffix
        full_address = f"{local_part}@{use_domain}"

        # Check existence first (fast path, avoids unnecessary INSERT)
        existing = await db.scalar(
            select(Alias).where(Alias.full_address == full_address)
        )
        if existing is not None:
            logger.debug("Alias %s already exists, retrying (%d)", full_address, attempt)
            continue

        now = datetime.now(timezone.utc)
        alias = Alias(
            local_part=local_part,
            domain=use_domain,
            full_address=full_address,
            status=AliasStatus.reserved,
            created_at=now,
            reserved_at=now,
        )
        db.add(alias)
        try:
            await db.flush()  # surfaces IntegrityError without committing
            logger.info("Generated alias %s (attempt %d)", full_address, attempt + 1)
            return alias
        except IntegrityError:
            await db.rollback()
            logger.warning(
                "Race condition on alias %s, retrying (%d)", full_address, attempt
            )
            continue

    raise RuntimeError(
        f"Could not generate a unique alias after {MAX_RETRIES} attempts. "
        "Consider increasing alias_length or charset."
    )


def _random_string(charset: str, length: int) -> str:
    return "".join(secrets.choice(charset) for _ in range(length))
