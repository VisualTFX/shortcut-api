"""Programmatic Alembic migration helpers (used by startup)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from pathlib import Path


def run_migrations() -> None:
    """Run alembic upgrade head — safe to call on every startup."""
    alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
