"""Discord webhook notifications."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# #000000 as a decimal integer
_EMBED_COLOR = 0x000000

# Shared client for connection reuse across webhook calls
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10)
    return _http_client


async def send_code_received_notification(
    *,
    device_name: str,
    alias_address: str,
    code: str,
    session_id: str,
) -> None:
    """Send a Discord embed notification when a verification code is extracted.

    If ``DISCORD_WEBHOOK_URL`` is not configured this function returns silently.
    All errors are caught and logged so the main extraction flow is never blocked.
    """
    settings = get_settings()
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        return

    now = datetime.now(timezone.utc)
    unix_ts = int(now.timestamp())

    payload = {
        "embeds": [
            {
                "title": "📬 Verification Code Received",
                "description": (
                    f'**"{device_name}"** has received a code for `{alias_address}`'
                ),
                "color": _EMBED_COLOR,
                "fields": [
                    {"name": "Code", "value": f"`{code}`", "inline": True},
                    {"name": "Session ID", "value": session_id, "inline": True},
                    {"name": "Timestamp", "value": f"<t:{unix_ts}:F>", "inline": False},
                ],
                "footer": {"text": "Shortcut API"},
            }
        ]
    }

    try:
        client = _get_http_client()
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Discord webhook notification failed: %s", exc)
