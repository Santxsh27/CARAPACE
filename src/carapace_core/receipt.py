"""Customer-facing assurance receipts derived from deterministic evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .canonical import sha256_hex


FIELD_BINDING_CHECKS = (
    "CONTRACT_REQUEST_HASH_VALID",
    "ACTUAL_REQUEST_HASH_VALID",
    "REQUEST_BOUND_TO_INTENT",
    "IDEMPOTENCY_KEY_MATCH",
)

POSTING_CHECKS = (
    "AT_MOST_ONE_POSTED_DEBIT",
    "DEBIT_AMOUNT_MATCH",
    "DEBIT_CURRENCY_MATCH",
    "PAYEE_MATCH",
    "LOGICAL_PAYMENT_MATCH",
)


@dataclass(frozen=True)
class ReceiptStage:
    code: str
    state: str
    message: str


@dataclass(frozen=True)
class TrustReceipt:
    schema_version: str
    receipt_id: str
    contract_id: str
    run_id: str
    issued_at: str
    assurance_level: str
    verdict: str
    summary: str
    direction: str
    amount_minor: int
    currency: str
    payee_id: str
    payee_display_name: str
    stages: tuple[ReceiptStage, ...]
    evidence_digest_sha256: str
    integrity_protection: str = "SHA256_EVIDENCE_DIGEST"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_map(report: Mapping[str, Any]) -> dict[str, bool]:
    return {
        str(check.get("code")): bool(check.get("passed"))
        for check in report.get("checks", [])
    }


def _all_pass(checks: Mapping[str, bool], required: Sequence[str]) -> bool:
    return all(checks.get(code) is True for code in required)


def build_trust_receipt(
    contract: Mapping[str, Any],
    evidence: Mapping[str, Any],
    report: Mapping[str, Any],
) -> TrustReceipt:
    """Create an honest receipt from exact verifier output.

    The receipt adds no new claim. It only translates named deterministic
    checks into stages a customer can understand.
    """

    payment = contract.get("payment", {})
    checks = _check_map(report)
    fields_bound = _all_pass(checks, FIELD_BINDING_CHECKS)
    posting_matched = _all_pass(checks, POSTING_CHECKS)
    report_matched = report.get("verdict") == "MATCH"
    lifecycle = [str(state) for state in evidence.get("lifecycle", [])]
    settlement_confirmed = (
        report_matched
        and bool(lifecycle)
        and lifecycle[-1] == "SETTLED"
        and bool(evidence.get("settlement_reference"))
        and checks.get("SETTLEMENT_EVIDENCE_PRESENT") is True
    )

    stages = (
        ReceiptStage(
            code="PAYMENT_FIELDS_BOUND",
            state="PASS" if fields_bound else "FAIL",
            message=(
                "The submitted amount, recipient and payment identity match the customer-confirmed promise."
                if fields_bound
                else "The submitted payment fields could not be proven to match the customer-confirmed promise."
            ),
        ),
        ReceiptStage(
            code="BANK_POSTING_MATCHED",
            state="PASS" if posting_matched else "FAIL",
            message=(
                "The observed bank posting matches the promised amount, currency, recipient and one-debit limit."
                if posting_matched
                else "The observed bank posting violates at least one promised financial condition."
            ),
        ),
        ReceiptStage(
            code="SETTLEMENT_CONFIRMED",
            state=(
                "PASS"
                if settlement_confirmed
                else "PENDING"
                if report_matched
                else "FAIL"
            ),
            message=(
                "Authoritative settlement evidence is present."
                if settlement_confirmed
                else "The bank posting matched, but final settlement evidence is not available yet."
                if report_matched
                else "Settlement assurance is withheld because the execution contains a mismatch."
            ),
        ),
    )

    if not report_matched:
        assurance_level = "MISMATCH"
        summary = "CARAPACE found a contradiction between the payment promise and the observed execution."
    elif settlement_confirmed:
        assurance_level = "SETTLEMENT_CONFIRMED"
        summary = "The confirmed payment fields, bank posting and final settlement evidence all match."
    elif posting_matched:
        assurance_level = "BANK_POSTING_MATCHED"
        summary = "The bank posting matches the confirmed payment; final settlement is still pending or unavailable."
    elif fields_bound:
        assurance_level = "PAYMENT_FIELDS_BOUND"
        summary = "The submitted payment matches the confirmed fields, but bank posting evidence is not yet proven."
    else:
        assurance_level = "UNVERIFIED"
        summary = "CARAPACE does not have enough matching evidence to verify this payment."

    evidence_digest = sha256_hex(
        {
            "contract_id": contract.get("contract_id"),
            "run_id": evidence.get("run_id"),
            "evidence": evidence,
            "report": report,
        }
    )
    receipt_id = f"receipt_{evidence_digest[:24]}"
    return TrustReceipt(
        schema_version="1.0",
        receipt_id=receipt_id,
        contract_id=str(contract.get("contract_id", "")),
        run_id=str(evidence.get("run_id", "")),
        issued_at=str(evidence.get("observed_at", "")),
        assurance_level=assurance_level,
        verdict=str(report.get("verdict", "MISMATCH")),
        summary=summary,
        direction=str(payment.get("direction", "")),
        amount_minor=int(payment.get("amount_minor", 0)),
        currency=str(payment.get("currency", "")),
        payee_id=str(payment.get("payee_id", "")),
        payee_display_name=str(payment.get("payee_display_name", "")),
        stages=stages,
        evidence_digest_sha256=evidence_digest,
    )
