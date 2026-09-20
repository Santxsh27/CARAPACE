"""Minimise sensitive data before untrusted context reaches an AI provider."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactedModelInput:
    text: str
    redaction_applied: bool


_SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "OTP",
        re.compile(
            r"\b(?:otp|one[-\s]?time\s+password)\s*(?:is|:|=)?\s*\d{4,8}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_OTP]",
    ),
    (
        "UPI_PIN",
        re.compile(
            r"\b(?:upi\s*)?pin\s*(?:is|:|=)?\s*\d{4,6}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_PIN]",
    ),
    (
        "CVV",
        re.compile(r"\b(?:cvv|cvc)\s*(?:is|:|=)?\s*\d{3,4}\b", re.IGNORECASE),
        "[REDACTED_CVV]",
    ),
    (
        "PASSWORD",
        re.compile(
            r"\b(?:password|passcode)\s*(?:is|:|=)\s*[^\s,.;]+",
            re.IGNORECASE,
        ),
        "[REDACTED_PASSWORD]",
    ),
    (
        "CARD_NUMBER",
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        "[REDACTED_CARD_NUMBER]",
    ),
)


def redact_for_model(message_text: str) -> RedactedModelInput:
    """Remove credentials from AI input while preserving the surrounding story.

    The result deliberately retains phrases such as "enter your UPI PIN". That
    lets the model identify the social-engineering pattern while ensuring that
    an actual PIN or OTP value is never sent to a cloud provider.
    """

    redacted = message_text
    redaction_applied = False
    for _, pattern, replacement in _SENSITIVE_PATTERNS:
        redacted, replacements = pattern.subn(replacement, redacted)
        redaction_applied = redaction_applied or replacements > 0
    return RedactedModelInput(
        text=redacted,
        redaction_applied=redaction_applied,
    )
