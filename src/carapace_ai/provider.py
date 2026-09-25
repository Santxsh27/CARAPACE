"""AI-provider boundary and a transparent no-cost local demonstration provider."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Protocol

from carapace_core.lens import IntentDirection, MessageIntent


class LensIntentProvider(Protocol):
    provider_name: str
    model_name: str
    mode: str

    def extract_intent(self, message_text: str, locale: str) -> MessageIntent:
        """Extract structured claims from untrusted user-supplied content."""

    def extract_intent_from_image(
        self, image_bytes: bytes, mime_type: str, message_text: str, locale: str
    ) -> MessageIntent:
        """Interpret a supplied screenshot together with optional context text."""


class LocalDemoIntentProvider:
    """Deterministic fixture so the full product works without cloud credentials.

    This is deliberately labelled as local rules in every response. It is not
    presented as Gemini and is only a development fallback.
    """

    provider_name = "carapace-local"
    model_name = "deterministic-intent-fixture-v1"
    mode = "LOCAL_RULES"

    RECEIVE_TERMS = ("refund", "receive", "credited", "cashback", "money back")
    SEND_TERMS = ("pay", "purchase", "send", "buy", "checkout")
    URGENCY_TERMS = ("urgent", "immediately", "now", "expires", "last chance", "within 5")

    def extract_intent(self, message_text: str, locale: str) -> MessageIntent:
        del locale
        text = message_text.strip()
        lowered = text.lower()
        expected_direction = IntentDirection.UNKNOWN
        if any(term in lowered for term in self.RECEIVE_TERMS):
            expected_direction = IntentDirection.RECEIVE_EXPECTED
        elif any(term in lowered for term in self.SEND_TERMS):
            expected_direction = IntentDirection.SEND

        amount_minor = _first_amount_minor(text)
        claimed_entity = _claimed_entity(text)
        asks_for_pin = "pin" in lowered and any(term in lowered for term in self.RECEIVE_TERMS)
        urgency = any(term in lowered for term in self.URGENCY_TERMS)

        return MessageIntent(
            expected_direction=expected_direction,
            expected_amount_minor=amount_minor,
            currency="INR",
            claimed_entity=claimed_entity,
            urgency_detected=urgency,
            asks_for_pin_to_receive=asks_for_pin,
            summary="Local rules extracted the payment claim for an offline demonstration.",
            evidence_span=next((term for term in self.RECEIVE_TERMS + self.SEND_TERMS if term in lowered), None),
        )

    def extract_intent_from_image(
        self, image_bytes: bytes, mime_type: str, message_text: str, locale: str
    ) -> MessageIntent:
        del image_bytes, mime_type
        return self.extract_intent(message_text, locale)


def _first_amount_minor(text: str) -> int | None:
    match = re.search(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(Decimal(match.group(1).replace(",", "")) * 100)
    except InvalidOperation:
        return None


def _claimed_entity(text: str) -> str | None:
    first_line = text.splitlines()[0].strip()
    if ":" in first_line:
        candidate = first_line.split(":", 1)[0].strip()
        if 2 <= len(candidate) <= 80:
            return candidate
    match = re.search(r"(?:from|by)\s+([A-Z][A-Za-z0-9 &.-]{1,60})", text)
    return match.group(1).strip(" .") if match else None
