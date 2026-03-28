"""Tests for Gmail message processor."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.gmail.processor import (
    _extract_body,
    _html_to_text,
    _identify_recipient,
    process_message,
)
from app.models.incoming_message import IncomingMessage
from app.models.parsing_rule import ParsingRule
from app.models.verification_session import SessionStatus, VerificationSession
from app.services.session_service import create_session


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _make_message(
    msg_id: str,
    delivered_to: str,
    from_addr: str,
    subject: str,
    plain_body: str,
    html_body: str | None = None,
) -> dict:
    headers = [
        {"name": "Delivered-To", "value": delivered_to},
        {"name": "To", "value": delivered_to},
        {"name": "From", "value": from_addr},
        {"name": "Subject", "value": subject},
    ]
    parts = [
        {
            "mimeType": "text/plain",
            "body": {"data": _b64(plain_body)},
        }
    ]
    if html_body:
        parts.append(
            {
                "mimeType": "text/html",
                "body": {"data": _b64(html_body)},
            }
        )
    return {
        "id": msg_id,
        "threadId": "thread1",
        "internalDate": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "snippet": plain_body[:100],
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": headers,
            "parts": parts,
        },
    }


UBER_HTML = """<html><body>
<td>Verification code:</td>
<td class="p1b" style="font-family: 'UberMoveText-Bold'"><p>6601</p></td>
</body></html>"""


def test_identify_recipient_delivered_to() -> None:
    headers = [{"name": "Delivered-To", "value": "abc123@mail-one4all.uk"}]
    result = _identify_recipient(headers, "mail-one4all.uk")
    assert result == "abc123@mail-one4all.uk"


def test_identify_recipient_no_match() -> None:
    headers = [{"name": "Delivered-To", "value": "user@gmail.com"}]
    result = _identify_recipient(headers, "mail-one4all.uk")
    assert result is None


def test_extract_body_plain() -> None:
    payload = {
        "mimeType": "text/plain",
        "body": {"data": _b64("Hello world")},
        "parts": [],
    }
    plain, html = _extract_body(payload)
    assert plain == "Hello world"
    assert html is None


def test_html_to_text() -> None:
    html = "<p>Hello <b>world</b></p>"
    text = _html_to_text(html)
    assert "Hello" in text
    assert "world" in text


@pytest.mark.asyncio
async def test_process_message_no_match_alias(seeded_db: AsyncSession) -> None:
    msg = _make_message(
        "msg001",
        "user@gmail.com",  # not our domain
        "noreply@uber.com",
        "Uber",
        "Your code is 1234",
    )
    result = await process_message(seeded_db, msg)
    assert result is None


@pytest.mark.asyncio
async def test_process_message_stores_record(seeded_db: AsyncSession) -> None:
    session, token = await create_session(seeded_db)
    msg = _make_message(
        "msg002",
        session.alias_address,
        "noreply@test.com",
        "Test",
        "No code here at all.",
    )
    result = await process_message(seeded_db, msg)
    assert result is not None
    assert result.delivered_alias == session.alias_address
    assert result.gmail_message_id == "msg002"


@pytest.mark.asyncio
async def test_process_message_extracts_code(seeded_db: AsyncSession) -> None:
    session, token = await create_session(seeded_db)
    msg = _make_message(
        "msg003",
        session.alias_address,
        "noreply@uber.com",
        "Verification",
        "Your verification code: 8765",
    )
    result = await process_message(seeded_db, msg)
    assert result is not None
    assert result.parsed_code == "8765"

    # Session should now be extracted
    await seeded_db.refresh(session)
    assert session.status == SessionStatus.extracted
    assert session.extracted_code == "8765"


@pytest.mark.asyncio
async def test_process_message_uber_html(seeded_db: AsyncSession) -> None:
    session, token = await create_session(seeded_db)
    msg = _make_message(
        "msg004",
        session.alias_address,
        "noreply@uber.com",
        "Welcome to Uber",
        "A one-time password has been created for you.",
        html_body=UBER_HTML,
    )
    result = await process_message(seeded_db, msg)
    assert result is not None
    assert result.parsed_code == "6601"


@pytest.mark.asyncio
async def test_duplicate_message_ignored(seeded_db: AsyncSession) -> None:
    session, token = await create_session(seeded_db)
    msg = _make_message(
        "msg005",
        session.alias_address,
        "noreply@test.com",
        "Test",
        "Code 1111",
    )
    r1 = await process_message(seeded_db, msg)
    r2 = await process_message(seeded_db, msg)
    assert r1 is not None
    assert r2 is None  # duplicate skipped
