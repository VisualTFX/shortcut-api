"""Low-level Gmail API client with retry logic."""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.integrations.gmail.auth import get_credentials

logger = get_logger(__name__)

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = get_credentials()
        _service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _service


def reset_service() -> None:
    """Force re-initialisation (useful after token refresh)."""
    global _service
    _service = None


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def _sync_list_messages(query: str, label_ids: list[str], page_token: str | None) -> dict:
    svc = _get_service()
    kwargs: dict[str, Any] = {
        "userId": "me",
        "q": query,
        "labelIds": label_ids,
        "maxResults": 100,
    }
    if page_token:
        kwargs["pageToken"] = page_token
    return svc.users().messages().list(**kwargs).execute()


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def _sync_get_message(msg_id: str, fmt: str = "full") -> dict:
    svc = _get_service()
    return svc.users().messages().get(userId="me", id=msg_id, format=fmt).execute()


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def _sync_get_history(start_history_id: str, label_ids: list[str]) -> dict:
    svc = _get_service()
    return (
        svc.users()
        .history()
        .list(
            userId="me",
            startHistoryId=start_history_id,
            labelId=label_ids[0] if label_ids else "INBOX",
            historyTypes=["messageAdded"],
        )
        .execute()
    )


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def _sync_watch(topic_name: str, label_ids: list[str]) -> dict:
    svc = _get_service()
    return (
        svc.users()
        .watch(userId="me", body={"topicName": topic_name, "labelIds": label_ids})
        .execute()
    )


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
def _sync_stop_watch() -> None:
    svc = _get_service()
    svc.users().stop(userId="me").execute()


async def list_messages(
    query: str = "", label_ids: list[str] | None = None, page_token: str | None = None
) -> dict:
    label_ids = label_ids or ["INBOX"]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_sync_list_messages, query, label_ids, page_token)
    )


async def get_message(msg_id: str, fmt: str = "full") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_get_message, msg_id, fmt))


async def get_history(start_history_id: str, label_ids: list[str] | None = None) -> dict:
    label_ids = label_ids or ["INBOX"]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(_sync_get_history, start_history_id, label_ids)
    )


async def watch(topic_name: str, label_ids: list[str] | None = None) -> dict:
    label_ids = label_ids or ["INBOX"]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_watch, topic_name, label_ids))


async def stop_watch() -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_stop_watch)
