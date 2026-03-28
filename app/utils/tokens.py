"""Token / ID utilities."""
from __future__ import annotations

import secrets
import string


_PUBLIC_ID_CHARS = string.ascii_lowercase + string.digits
PUBLIC_ID_LENGTH = 12


def generate_public_id() -> str:
    """Generate a short, URL-safe public session identifier."""
    return "".join(secrets.choice(_PUBLIC_ID_CHARS) for _ in range(PUBLIC_ID_LENGTH))
