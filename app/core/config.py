"""Application configuration via pydantic-settings."""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Domain ───────────────────────────────────────────
    alias_domain: str = "mail-one4all.uk"
    alias_length: int = 12
    alias_charset: str = "abcdefghjkmnpqrstuvwxyz23456789"
    alias_prefix: str = ""
    alias_suffix: str = ""

    # ── Session ──────────────────────────────────────────
    session_ttl_seconds: int = 600

    # ── Database ─────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./shortcut_api.db"

    # ── Gmail ────────────────────────────────────────────
    gmail_credentials_file: Path = Path("credentials.json")
    gmail_token_file: Path = Path("token.json")
    gmail_monitored_label: str = "INBOX"
    gmail_strategy: Literal["polling", "watch"] = "polling"
    gmail_poll_interval_seconds: int = 10

    # ── Security ─────────────────────────────────────────
    admin_token: str = "change-me"
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60

    # ── Retention ────────────────────────────────────────
    retention_enabled: bool = False
    retention_redact_body: bool = True
    retention_days: int = 7

    # ── Recycle ──────────────────────────────────────────
    recycle_enabled: bool = False

    # ── Server ───────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        if self.admin_token == "change-me":
            warnings.warn(
                "ADMIN_TOKEN is set to the insecure default 'change-me'. "
                "Set a strong token in your .env before deploying.",
                stacklevel=2,
            )
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
