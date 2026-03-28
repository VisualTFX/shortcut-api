"""IncomingMessage ORM model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IncomingMessage(Base):
    __tablename__ = "incoming_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gmail_message_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_address: Mapped[str] = mapped_column(String(382), nullable=False)
    delivered_alias: Mapped[str] = mapped_column(String(382), nullable=False, index=True)
    from_address: Mapped[str | None] = mapped_column(String(382), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    internal_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snippet: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("verification_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<IncomingMessage {self.gmail_message_id} -> {self.delivered_alias}>"
