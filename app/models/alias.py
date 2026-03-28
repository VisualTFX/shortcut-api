"""Alias ORM model."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AliasStatus(str, enum.Enum):
    reserved = "reserved"
    waiting = "waiting"
    received = "received"
    extracted = "extracted"
    expired = "expired"
    failed = "failed"
    retired = "retired"


class Alias(Base):
    __tablename__ = "aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    local_part: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(253), nullable=False, default="mail-one4all.uk")
    full_address: Mapped[str] = mapped_column(String(382), unique=True, nullable=False, index=True)
    status: Mapped[AliasStatus] = mapped_column(
        Enum(AliasStatus, name="aliasstatus"), nullable=False, default=AliasStatus.reserved
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    was_recycled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sessions: Mapped[list["VerificationSession"]] = relationship(  # type: ignore[name-defined]
        "VerificationSession", back_populates="alias_rel", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Alias {self.full_address} [{self.status}]>"
