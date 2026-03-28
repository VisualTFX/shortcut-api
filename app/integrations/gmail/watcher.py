"""Gmail watch/push notification management."""
from __future__ import annotations

from app.core.logging import get_logger
from app.integrations.gmail import client as gmail_client

logger = get_logger(__name__)

_current_history_id: str | None = None
_watch_expiry_ms: int | None = None


async def setup_watch(topic_name: str, label_ids: list[str] | None = None) -> str:
    """Start a Gmail push watch and return the historyId."""
    result = await gmail_client.watch(topic_name, label_ids)
    history_id = result.get("historyId", "")
    expiry = result.get("expiration")
    global _current_history_id, _watch_expiry_ms
    _current_history_id = history_id
    if expiry:
        _watch_expiry_ms = int(expiry)
    logger.info("Gmail watch started, historyId=%s expiry=%s", history_id, expiry)
    return history_id


async def renew_watch(topic_name: str, label_ids: list[str] | None = None) -> str:
    return await setup_watch(topic_name, label_ids)


def get_current_history_id() -> str | None:
    return _current_history_id


def set_history_id(history_id: str) -> None:
    global _current_history_id
    _current_history_id = history_id
