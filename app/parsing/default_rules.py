"""Default parsing rules seeded into the database on first run."""
from __future__ import annotations

DEFAULT_RULES = [
    {
        "name": "Code in bold HTML element after 'code' keyword",
        "priority": 5,
        "body_regex": (
            r"(?:code|password|OTP)\s*:?\s*</(?:p|td|div|span)>\s*"
            r"(?:<[^>]*>\s*)*<(?:p|td|div|span)[^>]*>\s*([A-Za-z0-9]{4,8})"
        ),
        "code_capture_group": 1,
        "description": (
            "Matches a code that appears in a separate HTML element immediately "
            "after a cell/div containing 'code', 'password', or 'OTP'. "
            "Handles the Uber-style layout."
        ),
    },
    {
        "name": "Generic numeric code near verification keyword",
        "priority": 10,
        "body_regex": (
            r"(?:verification\s*code|your\s*code\s*is|enter\s*(?:this|the)\s*code"
            r"|one.?time\s*(?:password|code)|OTP)\s*[:\s]*(\d{4,8})"
        ),
        "code_capture_group": 1,
        "description": "Numeric 4-8 digit code preceded by common verification phrases.",
    },
    {
        "name": "Alphanumeric code near verification keyword",
        "priority": 30,
        "body_regex": (
            r"(?:verification\s*code|your\s*code\s*is|enter\s*(?:this|the)\s*code"
            r"|one.?time\s*(?:password|code)|OTP)\s*[:\s]*([A-Za-z0-9]{4,10})"
        ),
        "code_capture_group": 1,
        "description": "Alphanumeric 4-10 char code preceded by common verification phrases.",
    },
    {
        "name": "Standalone 4-8 digit code (fallback)",
        "priority": 50,
        "body_regex": r"\b(\d{4,8})\b",
        "code_capture_group": 1,
        "description": "Fallback: any standalone 4-8 digit number in the body.",
    },
]
