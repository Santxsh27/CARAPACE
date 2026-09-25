"""Deterministic payment-intent reconciliation for CARAPACE Lens.

AI may extract what a message appears to promise.  This module independently
parses the payment request and applies named, testable contradiction rules.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from urllib.parse import parse_qs, unquote, urlparse


class LensInputError(ValueError):
    """Raised when a payment request cannot be safely interpreted."""


class IntentDirection(str, Enum):
    SEND = "SEND"
    REQUEST = "REQUEST"
    RECEIVE_EXPECTED = "RECEIVE_EXPECTED"
    UNKNOWN = "UNKNOWN"


class LensDecision(str, Enum):
    ALLOW = "ALLOW"
    CAUTION = "CAUTION"
    STOP = "STOP"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class MessageIntent:
    expected_direction: IntentDirection
    expected_amount_minor: int | None
    currency: str
    claimed_entity: str | None
    urgency_detected: bool
    asks_for_pin_to_receive: bool
    summary: str
    evidence_span: str | None = None

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["expected_direction"] = self.expected_direction.value
        return payload


@dataclass(frozen=True)
class PaymentRequest:
    direction: IntentDirection
    amount_minor: int | None
    currency: str
    payee_id: str
    payee_name: str | None
    note: str | None
    source: str = "UPI_URI"

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["direction"] = self.direction.value
        return payload


@dataclass(frozen=True)
class LensFinding:
    code: str
    severity: str
    title: str
    explanation: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class LensAssessment:
    decision: LensDecision
    findings: tuple[LensFinding, ...]
    plain_language_result: str

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "findings": [finding.as_dict() for finding in self.findings],
            "plain_language_result": self.plain_language_result,
        }


def parse_upi_payment_uri(payment_uri: str) -> PaymentRequest:
    """Parse the canonical fields encoded in a decoded UPI payment QR/link."""

    value = payment_uri.strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() != "upi" or parsed.netloc.lower() not in {"pay", "mandate"}:
        raise LensInputError("Only a decoded upi://pay or upi://mandate request is supported")

    query = parse_qs(parsed.query, keep_blank_values=True)
    payee_id = _single(query, "pa")
    if not payee_id:
        raise LensInputError("The UPI request does not contain a payee address (pa)")

    amount_text = _single(query, "am")
    amount_minor = _amount_to_minor(amount_text) if amount_text else None
    currency = (_single(query, "cu") or "INR").upper()
    if currency != "INR":
        raise LensInputError("This Lens milestone currently supports INR UPI requests only")

    return PaymentRequest(
        direction=IntentDirection.SEND,
        amount_minor=amount_minor,
        currency=currency,
        payee_id=unquote(payee_id),
        payee_name=_decoded_or_none(_single(query, "pn")),
        note=_decoded_or_none(_single(query, "tn")),
    )


def reconcile_intent(
    intent: MessageIntent,
    payment: PaymentRequest,
) -> LensAssessment:
    """Compare semantic intent with canonical payment fields using fixed rules."""

    findings: list[LensFinding] = []

    if intent.expected_direction == IntentDirection.RECEIVE_EXPECTED and payment.direction == IntentDirection.SEND:
        findings.append(
            LensFinding(
                code="DIRECTION_CONTRADICTION",
                severity="CRITICAL",
                title="Receive story opens a send payment",
                explanation="The message says money will come to you, but the UPI request sends money from you.",
            )
        )

    if (
        intent.expected_amount_minor is not None
        and payment.amount_minor is not None
        and intent.expected_amount_minor != payment.amount_minor
    ):
        findings.append(
            LensFinding(
                code="AMOUNT_CONTRADICTION",
                severity="CRITICAL",
                title="The amount changed",
                explanation=(
                    f"The story mentions INR {intent.expected_amount_minor / 100:,.2f}, "
                    f"but the payment request is INR {payment.amount_minor / 100:,.2f}."
                ),
            )
        )

    if intent.claimed_entity and payment.payee_name and not _entities_compatible(
        intent.claimed_entity, payment.payee_name
    ):
        findings.append(
            LensFinding(
                code="PAYEE_IDENTITY_CONTRADICTION",
                severity="HIGH",
                title="The named organisation and payee differ",
                explanation=(
                    f"The message identifies {intent.claimed_entity}, while the request names "
                    f"{payment.payee_name}. Confirm through the organisation's official channel."
                ),
            )
        )

    if intent.asks_for_pin_to_receive and intent.expected_direction == IntentDirection.RECEIVE_EXPECTED:
        findings.append(
            LensFinding(
                code="PIN_TO_RECEIVE_DECEPTION",
                severity="CRITICAL",
                title="A PIN is being requested for a supposed incoming payment",
                explanation="A UPI PIN authorises an outgoing action; it is not required merely to receive money.",
            )
        )

    if intent.urgency_detected:
        findings.append(
            LensFinding(
                code="SOCIAL_PRESSURE_SIGNAL",
                severity="MEDIUM",
                title="Urgency or pressure language detected",
                explanation="Pressure is a risk signal, not proof of fraud. Pause and verify independently.",
            )
        )

    critical = any(item.severity in {"CRITICAL", "HIGH"} for item in findings)
    if critical:
        decision = LensDecision.STOP
        result = "Stop. The story and the actual payment request contradict each other."
    elif intent.expected_direction == IntentDirection.UNKNOWN or payment.amount_minor is None:
        decision = LensDecision.UNVERIFIED
        result = "CARAPACE does not have enough evidence to verify this payment."
    elif findings:
        decision = LensDecision.CAUTION
        result = "Pause and independently confirm the request before paying."
    else:
        decision = LensDecision.ALLOW
        result = "No contradiction was found in the fields checked, but this is not a guarantee that the payee is honest."

    return LensAssessment(decision=decision, findings=tuple(findings), plain_language_result=result)


def _single(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0].strip() if values and values[0].strip() else None


def _decoded_or_none(value: str | None) -> str | None:
    return unquote(value) if value else None


def _amount_to_minor(value: str) -> int:
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise LensInputError("The UPI amount is not a valid number") from error
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise LensInputError("The UPI amount must be positive with at most two decimal places")
    return int(amount * 100)


def _normalise_entity(value: str) -> set[str]:
    ignored = {"limited", "ltd", "private", "pvt", "the", "support", "payments"}
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return {token for token in tokens if token not in ignored and len(token) > 1}


def _entities_compatible(claimed: str, payee: str) -> bool:
    claimed_tokens = _normalise_entity(claimed)
    payee_tokens = _normalise_entity(payee)
    return bool(claimed_tokens and payee_tokens and claimed_tokens.intersection(payee_tokens))
