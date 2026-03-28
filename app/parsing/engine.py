"""Parsing engine — applies regex rules to extracted email body text."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger
from app.models.parsing_rule import ParsingRule

logger = get_logger(__name__)


@dataclass
class ParseResult:
    code: str
    rule_id: int
    rule_name: str
    confidence: float
    capture_group: int


def apply_rules(
    body_text: str,
    rules: list[ParsingRule],
    *,
    from_address: str | None = None,
    subject: str | None = None,
) -> ParseResult | None:
    """
    Apply rules (sorted by priority ascending — lower = higher priority) and
    return the first match.

    Each rule may optionally filter by sender/subject pattern before the body
    regex is attempted.
    """
    enabled_rules = [r for r in rules if r.enabled]
    enabled_rules.sort(key=lambda r: r.priority)

    for rule in enabled_rules:
        # Optional sender filter
        if rule.sender_pattern and from_address:
            if not re.search(rule.sender_pattern, from_address, re.IGNORECASE):
                continue
        # Optional subject filter
        if rule.subject_pattern and subject:
            if not re.search(rule.subject_pattern, subject, re.IGNORECASE):
                continue

        match = re.search(rule.body_regex, body_text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                code = match.group(rule.code_capture_group)
            except IndexError:
                logger.warning(
                    "Rule %r: capture group %d not in match", rule.name, rule.code_capture_group
                )
                continue

            if not code:
                continue

            # Confidence: inversely proportional to priority (lower = more specific)
            confidence = max(0.1, 1.0 - rule.priority / 100.0)
            logger.info(
                "Rule %r matched code=%r confidence=%.2f", rule.name, code, confidence
            )
            return ParseResult(
                code=code,
                rule_id=rule.id,
                rule_name=rule.name,
                confidence=confidence,
                capture_group=rule.code_capture_group,
            )

    return None
