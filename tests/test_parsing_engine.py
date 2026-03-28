"""Tests for parsing engine."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.parsing.engine import ParseResult, apply_rules


def _make_rule(
    id: int,
    name: str,
    priority: int,
    body_regex: str,
    capture_group: int = 1,
    enabled: bool = True,
    sender_pattern: str | None = None,
    subject_pattern: str | None = None,
) -> MagicMock:
    rule = MagicMock()
    rule.id = id
    rule.name = name
    rule.priority = priority
    rule.body_regex = body_regex
    rule.code_capture_group = capture_group
    rule.enabled = enabled
    rule.sender_pattern = sender_pattern
    rule.subject_pattern = subject_pattern
    return rule


UBER_HTML = """
<td class="p1b" style="font-family: 'UberMoveText-Bold'"><p>6601</p></td>
"""

UBER_CONTEXT = """
Verification code:
</td>
<td class="p1b" style="font-family: 'UberMoveText-Bold'"><p>6601</p></td>
Enter this code on the sign-up page to continue.
"""


def test_generic_numeric_rule() -> None:
    rule = _make_rule(
        1,
        "generic numeric",
        10,
        r"(?:verification\s*code|your\s*code\s*is|enter\s*(?:this|the)\s*code"
        r"|one.?time\s*(?:password|code)|OTP)\s*[:\s]*(\d{4,8})",
    )
    body = "Your verification code: 123456"
    result = apply_rules(body, [rule])
    assert result is not None
    assert result.code == "123456"


def test_standalone_fallback_rule() -> None:
    rule = _make_rule(2, "fallback", 50, r"\b(\d{4,8})\b")
    body = "Use code 9876 to log in."
    result = apply_rules(body, [rule])
    assert result is not None
    assert result.code == "9876"


def test_html_element_rule_uber() -> None:
    rule = _make_rule(
        3,
        "HTML element after code keyword",
        5,
        r"(?:code|password|OTP)\s*:?\s*</(?:p|td|div|span)>\s*"
        r"(?:<[^>]*>\s*)*<(?:p|td|div|span)[^>]*>\s*([A-Za-z0-9]{4,8})",
    )
    result = apply_rules(UBER_CONTEXT, [rule])
    assert result is not None
    assert result.code == "6601"


def test_rules_ordered_by_priority() -> None:
    high_priority = _make_rule(1, "high", 5, r"\b(\d{4,8})\b")
    low_priority = _make_rule(2, "low", 50, r"\b(\d{4,8})\b")
    body = "Code 1234"
    result = apply_rules(body, [low_priority, high_priority])
    assert result is not None
    assert result.rule_name == "high"


def test_disabled_rule_skipped() -> None:
    disabled = _make_rule(1, "disabled", 5, r"\b(\d{4,8})\b", enabled=False)
    fallback = _make_rule(2, "fallback", 50, r"\b(\d{4,8})\b")
    body = "Code 5678"
    result = apply_rules(body, [disabled, fallback])
    assert result is not None
    assert result.rule_name == "fallback"


def test_no_match_returns_none() -> None:
    rule = _make_rule(1, "digits", 10, r"\b(\d{6})\b")
    result = apply_rules("no digits here", [rule])
    assert result is None


def test_sender_filter_blocks() -> None:
    rule = _make_rule(1, "uber", 10, r"\b(\d{4,8})\b", sender_pattern=r"uber\.com")
    result = apply_rules("Code 1234", [rule], from_address="noreply@amazon.com")
    assert result is None


def test_sender_filter_allows() -> None:
    rule = _make_rule(1, "uber", 10, r"\b(\d{4,8})\b", sender_pattern=r"uber\.com")
    result = apply_rules("Code 1234", [rule], from_address="noreply@uber.com")
    assert result is not None


def test_otp_keyword() -> None:
    rule = _make_rule(
        1,
        "generic",
        10,
        r"(?:verification\s*code|your\s*code\s*is|enter\s*(?:this|the)\s*code"
        r"|one.?time\s*(?:password|code)|OTP)\s*[:\s]*(\d{4,8})",
    )
    result = apply_rules("OTP: 4567", [rule])
    assert result is not None
    assert result.code == "4567"
