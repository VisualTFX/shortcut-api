"""Gmail message processor — converts raw API messages into IncomingMessage records."""
from __future__ import annotations

import base64
import email as stdlib_email
import email.policy
import quopri
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.discord.webhook import send_code_received_notification
from app.models.incoming_message import IncomingMessage
from app.models.parsing_rule import ParsingRule
from app.models.verification_session import SessionStatus, VerificationSession
from app.parsing.engine import apply_rules

logger = get_logger(__name__)


def _decode_b64(data: str) -> bytes:
    """URL-safe base64 decode (Gmail uses URL-safe variant)."""
    return base64.urlsafe_b64decode(data + "==")


def _header_value(headers: list[dict], name: str) -> str | None:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def _extract_body(payload: dict) -> tuple[str | None, str | None]:
    """
    Recursively walk MIME parts and extract plain text + HTML bodies.
    Returns (plain_text, html_text).
    """
    plain: list[str] = []
    html: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")

        if mime == "text/plain" and data:
            try:
                plain.append(_decode_b64(data).decode("utf-8", errors="replace"))
            except Exception:
                pass
        elif mime == "text/html" and data:
            try:
                html.append(_decode_b64(data).decode("utf-8", errors="replace"))
            except Exception:
                pass

        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return ("\n".join(plain) if plain else None, "\n".join(html) if html else None)


def _html_to_text(html: str) -> str:
    """Strip HTML tags and return readable plain text."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n")


def _identify_recipient(headers: list[dict], domain: str) -> str | None:
    """Extract the alias address from known recipient headers."""
    for header_name in ("Delivered-To", "X-Original-To", "To", "X-Forwarded-To"):
        val = _header_value(headers, header_name)
        if val and domain.lower() in val.lower():
            # Strip display name and angle brackets
            match = re.search(r"[\w.\-+]+@[\w.\-]+", val)
            if match:
                return match.group(0).lower()
    return None


async def process_message(
    db: AsyncSession,
    raw_message: dict,
) -> IncomingMessage | None:
    """
    Process a single Gmail API message dict.

    Returns the IncomingMessage record created (or None if irrelevant/duplicate).
    """
    settings = get_settings()
    msg_id: str = raw_message["id"]
    thread_id: str | None = raw_message.get("threadId")

    # Idempotency check
    existing = await db.scalar(
        select(IncomingMessage).where(IncomingMessage.gmail_message_id == msg_id)
    )
    if existing is not None:
        logger.debug("Message %s already processed, skipping", msg_id)
        return None

    payload: dict = raw_message.get("payload", {})
    headers: list[dict] = payload.get("headers", [])

    delivered_alias = _identify_recipient(headers, settings.alias_domain)
    if not delivered_alias:
        logger.debug("Message %s not for our domain, skipping", msg_id)
        return None

    to_address = _header_value(headers, "To") or delivered_alias
    from_address = _header_value(headers, "From")
    subject = _header_value(headers, "Subject")

    raw_internal_date = raw_message.get("internalDate")
    internal_date: datetime | None = None
    if raw_internal_date:
        try:
            internal_date = datetime.fromtimestamp(
                int(raw_internal_date) / 1000, tz=timezone.utc
            )
        except (ValueError, OSError):
            pass

    snippet: str | None = raw_message.get("snippet")

    plain_text, html_text = _extract_body(payload)

    # Build searchable body text
    body_for_parsing = plain_text or ""
    if html_text:
        body_for_parsing = body_for_parsing + "\n" + _html_to_text(html_text)
    if html_text:
        # Also include raw HTML for HTML-pattern rules
        body_for_parsing = body_for_parsing + "\n" + html_text

    # Retention policy
    stored_text = plain_text if settings.retention_enabled else None
    stored_html = html_text if settings.retention_enabled else None

    # Look up matching session
    session = await db.scalar(
        select(VerificationSession).where(
            VerificationSession.alias_address == delivered_alias,
            VerificationSession.status.in_(
                [SessionStatus.waiting, SessionStatus.received]
            ),
        )
    )

    # Run parsing rules
    rules = list(
        (
            await db.scalars(select(ParsingRule).where(ParsingRule.enabled == True))  # noqa: E712
        ).all()
    )
    parse_result = apply_rules(
        body_for_parsing,
        rules,
        from_address=from_address,
        subject=subject,
    )

    parsed_code: str | None = None
    parsed_at: datetime | None = None
    if parse_result:
        parsed_code = parse_result.code
        parsed_at = datetime.now(timezone.utc)

    msg = IncomingMessage(
        gmail_message_id=msg_id,
        thread_id=thread_id,
        to_address=to_address,
        delivered_alias=delivered_alias,
        from_address=from_address,
        subject=subject,
        internal_date=internal_date,
        snippet=snippet,
        raw_text=stored_text,
        raw_html=stored_html,
        parsed_code=parsed_code,
        parsed_at=parsed_at,
        session_id=session.id if session else None,
    )
    db.add(msg)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.warning("Duplicate message %s, skipping", msg_id)
        return None

    # Update session
    if session and parse_result:
        session.status = SessionStatus.extracted
        session.extracted_code = parsed_code
        session.extraction_confidence = parse_result.confidence
        session.matched_message_id = msg_id
        session.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Session %s: code extracted=%r from message %s",
            session.public_id,
            parsed_code,
            msg_id,
        )
    elif session:
        session.status = SessionStatus.received
        logger.info("Session %s: email received, no code yet", session.public_id)

    await db.commit()
    await db.refresh(msg)

    # Fire Discord notification after a code is successfully extracted
    if session and parse_result and parsed_code:
        await send_code_received_notification(
            device_name=session.device_name or "iPhone",
            alias_address=session.alias_address,
            code=parsed_code,
            session_id=session.public_id,
        )

    return msg
