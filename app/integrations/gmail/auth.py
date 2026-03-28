"""Gmail OAuth credential management."""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_credentials() -> Credentials:
    """
    Return valid Google credentials, refreshing or re-running OAuth if needed.
    Stores/loads token from the configured token file.
    """
    settings = get_settings()
    token_path = Path(settings.gmail_token_file)
    creds_path = Path(settings.gmail_credentials_file)

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds, token_path)
        return creds

    # Need fresh OAuth (interactive)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Gmail credentials file not found: {creds_path}. "
            "Run scripts/gmail_auth.py to set up OAuth first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_path)
    return creds


def _save_token(creds: Credentials, path: Path) -> None:
    path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("Gmail token saved to %s", path)
