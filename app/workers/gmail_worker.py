"""Gmail polling/watch background worker."""
from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.integrations.gmail import client as gmail_client
from app.integrations.gmail.processor import process_message
from app.integrations.gmail.watcher import get_current_history_id, set_history_id

logger = get_logger(__name__)

# Module-level worker state
_worker_task: asyncio.Task | None = None
_last_processed_msg_id: str | None = None
_is_running: bool = False


def is_running() -> bool:
    return _is_running


async def start_worker() -> None:
    global _worker_task, _is_running
    settings = get_settings()
    if _worker_task and not _worker_task.done():
        return
    _is_running = True
    if settings.gmail_strategy == "watch":
        _worker_task = asyncio.create_task(_watch_loop(), name="gmail_watch_worker")
    else:
        _worker_task = asyncio.create_task(_poll_loop(), name="gmail_poll_worker")
    logger.info("Gmail worker started (strategy=%s)", settings.gmail_strategy)


async def stop_worker() -> None:
    global _worker_task, _is_running
    _is_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Gmail worker stopped")


async def trigger_sync() -> int:
    """Manually trigger a sync, return number of messages processed."""
    settings = get_settings()
    if settings.gmail_strategy == "watch":
        return await _process_history()
    return await _poll_once()


async def _poll_loop() -> None:
    settings = get_settings()
    interval = settings.gmail_poll_interval_seconds
    while _is_running:
        try:
            count = await _poll_once()
            if count:
                logger.info("Poll: processed %d messages", count)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Gmail poll error: %s", exc)
        await asyncio.sleep(interval)


async def _poll_once() -> int:
    global _last_processed_msg_id
    settings = get_settings()
    label_ids = [settings.gmail_monitored_label]

    all_msg_ids: list[str] = []
    page_token: str | None = None

    while True:
        resp = await gmail_client.list_messages(
            label_ids=label_ids, page_token=page_token
        )
        messages: list[dict] = resp.get("messages", [])
        all_msg_ids.extend(m["id"] for m in messages)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Only process messages newer than the last processed one
    if _last_processed_msg_id and all_msg_ids:
        try:
            idx = all_msg_ids.index(_last_processed_msg_id)
            all_msg_ids = all_msg_ids[:idx]
        except ValueError:
            pass  # last ID not in current page; process all

    count = 0
    factory = get_session_factory()
    for msg_id in reversed(all_msg_ids):  # oldest first
        try:
            raw = await gmail_client.get_message(msg_id)
            async with factory() as db:
                result = await process_message(db, raw)
                if result is not None:
                    count += 1
            _last_processed_msg_id = msg_id
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Error processing message %s: %s", msg_id, exc)

    return count


async def _watch_loop() -> None:
    """
    Watch mode: re-check history every poll_interval seconds.
    (In production you would receive push notifications via a webhook;
     this loop acts as a heartbeat / fallback.)
    """
    settings = get_settings()
    interval = settings.gmail_poll_interval_seconds
    while _is_running:
        try:
            count = await _process_history()
            if count:
                logger.info("Watch poll: processed %d messages", count)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Gmail watch loop error: %s", exc)
        await asyncio.sleep(interval)


async def _process_history() -> int:
    history_id = get_current_history_id()
    if not history_id:
        return await _poll_once()

    settings = get_settings()
    label_ids = [settings.gmail_monitored_label]

    try:
        resp = await gmail_client.get_history(history_id, label_ids)
    except Exception as exc:
        logger.warning("History fetch failed (%s), falling back to poll", exc)
        return await _poll_once()

    new_history_id = resp.get("historyId")
    if new_history_id:
        set_history_id(new_history_id)

    msg_ids: list[str] = []
    for record in resp.get("history", []):
        for added in record.get("messagesAdded", []):
            msg_id = added.get("message", {}).get("id")
            if msg_id:
                msg_ids.append(msg_id)

    count = 0
    factory = get_session_factory()
    for msg_id in msg_ids:
        try:
            raw = await gmail_client.get_message(msg_id)
            async with factory() as db:
                result = await process_message(db, raw)
                if result is not None:
                    count += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Error processing history message %s: %s", msg_id, exc)

    return count
