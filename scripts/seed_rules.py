"""
Seed default parsing rules into the database.

Run once after initial migration if you want to pre-populate rules without
starting the full application server:

    python scripts/seed_rules.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select, func
from app.db.base import Base
from app.db.session import get_engine, get_session_factory
from app.models.parsing_rule import ParsingRule
from app.parsing.default_rules import DEFAULT_RULES


async def seed() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()
    async with factory() as db:
        count = await db.scalar(select(func.count()).select_from(ParsingRule))
        if count and count > 0:
            print(f"Already have {count} rules. Skipping seed.")
            return
        for rule_data in DEFAULT_RULES:
            db.add(ParsingRule(**rule_data))
        await db.commit()
        print(f"Seeded {len(DEFAULT_RULES)} default rules.")


if __name__ == "__main__":
    asyncio.run(seed())
