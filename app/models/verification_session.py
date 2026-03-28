"""VerificationSession ORM model."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionStatus(str, enum.Enum):
    reserved = "reserved"
    waiting = "waiting"
    received = "received"
    extracted = "extracted"
    expired = "expired"
    failed = "failed"
    cancelled = "cancelled"


class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    client_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    alias_id: Mapped[int] = mapped_column(Integer, ForeignKey("aliases.id"), nullable=False)
    alias_address: Mapped[str] = mapped_column(String(382), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="sessionstatus"), nullable=False, default=SessionStatus.waiting
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extracted_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

    alias_rel: Mapped["Alias"] = relationship(  # type: ignore[name-defined]
        "Alias", back_populates="sessions", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<VerificationSession {self.public_id} [{self.status}]>"
