"""Security helpers: token generation and hashing."""
from __future__ import annotations

import hashlib
import secrets


TOKEN_BYTES = 32


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """SHA-256 hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(raw: str, hashed: str) -> bool:
    """Constant-time comparison of raw token against stored hash."""
    expected = hash_token(raw)
    return secrets.compare_digest(expected, hashed)
