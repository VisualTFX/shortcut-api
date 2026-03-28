"""Initial migration — create all tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # aliases
    op.create_table(
        "aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("local_part", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("full_address", sa.String(382), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "reserved", "waiting", "received", "extracted",
                "expired", "failed", "retired",
                name="aliasstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("was_recycled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("full_address"),
    )
    op.create_index("ix_aliases_full_address", "aliases", ["full_address"])

    # verification_sessions
    op.create_table(
        "verification_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("public_id", sa.String(32), nullable=False),
        sa.Column("client_token_hash", sa.String(64), nullable=False),
        sa.Column("alias_id", sa.Integer(), nullable=False),
        sa.Column("alias_address", sa.String(382), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "reserved", "waiting", "received", "extracted",
                "expired", "failed", "cancelled",
                name="sessionstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_label", sa.String(128), nullable=True),
        sa.Column("extracted_code", sa.String(64), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("matched_message_id", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["alias_id"], ["aliases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_verification_sessions_public_id", "verification_sessions", ["public_id"])

    # incoming_messages
    op.create_table(
        "incoming_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gmail_message_id", sa.String(64), nullable=False),
        sa.Column("thread_id", sa.String(64), nullable=True),
        sa.Column("to_address", sa.String(382), nullable=False),
        sa.Column("delivered_alias", sa.String(382), nullable=False),
        sa.Column("from_address", sa.String(382), nullable=True),
        sa.Column("subject", sa.String(998), nullable=True),
        sa.Column("internal_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snippet", sa.String(512), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("parsed_code", sa.String(64), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["verification_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id"),
    )
    op.create_index("ix_incoming_messages_gmail_message_id", "incoming_messages", ["gmail_message_id"])
    op.create_index("ix_incoming_messages_delivered_alias", "incoming_messages", ["delivered_alias"])

    # parsing_rules
    op.create_table(
        "parsing_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("sender_pattern", sa.String(256), nullable=True),
        sa.Column("subject_pattern", sa.String(256), nullable=True),
        sa.Column("body_regex", sa.Text(), nullable=False),
        sa.Column("code_capture_group", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("parsing_rules")
    op.drop_table("incoming_messages")
    op.drop_table("verification_sessions")
    op.drop_table("aliases")
