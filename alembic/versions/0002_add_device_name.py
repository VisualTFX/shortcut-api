"""Add device_name column to verification_sessions."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_device_name"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verification_sessions",
        sa.Column("device_name", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verification_sessions", "device_name")
