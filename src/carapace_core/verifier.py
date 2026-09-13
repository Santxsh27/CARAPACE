"""Independent, deterministic verification of payment execution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import request_digest
from .lifecycle import invalid_transitions


@dataclass(frozen=True)
class CheckResult:
    code: str
    passed: bool
    message: str
    severity: str = "CRITICAL"


@dataclass(frozen=True)
class VerificationReport:
    contract_id: str
    run_id: str
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def verdict(self) -> str:
        return "MATCH" if self.passed else "MISMATCH"

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "run_id": self.run_id,
            "verdict": self.verdict,
            "checks": [
                {
                    "code": check.code,
                    "passed": check.passed,
                    "severity": check.severity,
                    "message": check.message,
                }
                for check in self.checks
            ],
        }


def _check(code: str, condition: bool, success: str, failure: str) -> CheckResult:
    return CheckResult(code=code, passed=condition, message=success if condition else failure)


def verify_payment(
    contract: Mapping[str, Any], evidence: Mapping[str, Any]
) -> VerificationReport:
    """Check one execution against a Payment Assurance Contract.

    This function intentionally performs no probabilistic or AI reasoning. Its
    output depends only on the supplied versioned contract and evidence.
    """

    payment = contract.get("payment", {})
    integrity = contract.get("integrity", {})
    entries = evidence.get("ledger_entries", [])
    contract_id = str(contract.get("contract_id", ""))
    run_id = str(evidence.get("run_id", ""))

    expected_hash = integrity.get("request_hash_sha256")
    calculated_contract_hash = request_digest(payment)
    actual_request = evidence.get("actual_request", {})
    calculated_actual_hash = request_digest(actual_request)
    reported_actual_hash = evidence.get("actual_request_hash_sha256")

    posted_debits = [
        entry
        for entry in entries
        if entry.get("direction") == "DEBIT" and entry.get("status") == "POSTED"
    ]

    lifecycle = evidence.get("lifecycle", [])
    lifecycle_errors = invalid_transitions(lifecycle)
    final_state = lifecycle[-1] if lifecycle else None

    checks = (
        _check(
            "CONTRACT_ID_MATCH",
            evidence.get("contract_id") == contract_id,
            "Execution evidence references this contract.",
            "Execution evidence references a different contract.",
        ),
        _check(
            "CONTRACT_REQUEST_HASH_VALID",
            expected_hash == calculated_contract_hash,
            "The contract digest matches its canonical payment fields.",
            "The contract digest does not match its canonical payment fields.",
        ),
        _check(
            "ACTUAL_REQUEST_HASH_VALID",
            reported_actual_hash == calculated_actual_hash,
            "The reported request digest matches the observed request.",
            "The reported request digest does not match the observed request.",
        ),
        _check(
            "REQUEST_BOUND_TO_INTENT",
            calculated_actual_hash == expected_hash,
            "The submitted request matches the customer-confirmed promise.",
            "The submitted request differs from the customer-confirmed promise.",
        ),
        _check(
            "IDEMPOTENCY_KEY_MATCH",
            evidence.get("idempotency_key") == integrity.get("idempotency_key"),
            "Execution reused the contract idempotency identity.",
            "Execution used a different idempotency identity.",
        ),
        _check(
            "LEGAL_LIFECYCLE",
            not lifecycle_errors,
            "Every payment lifecycle transition is allowed.",
            "; ".join(lifecycle_errors),
        ),
        _check(
            "AT_MOST_ONE_POSTED_DEBIT",
            len(posted_debits) <= 1,
            "The logical payment produced at most one posted debit.",
            f"The logical payment produced {len(posted_debits)} posted debits.",
        ),
        _check(
            "DEBIT_AMOUNT_MATCH",
            len(posted_debits) == 1
            and posted_debits[0].get("amount_minor") == payment.get("amount_minor"),
            "The posted debit equals the authorized amount.",
            "The posted debit count or amount differs from the authorized amount.",
        ),
        _check(
            "DEBIT_CURRENCY_MATCH",
            bool(posted_debits)
            and all(
                entry.get("currency") == payment.get("currency")
                for entry in posted_debits
            ),
            "Every posted debit uses the contract currency.",
            "At least one posted debit is missing or uses a different currency.",
        ),
        _check(
            "PAYEE_MATCH",
            bool(posted_debits)
            and all(
                entry.get("counterparty_ref") == payment.get("payee_id")
                for entry in posted_debits
            ),
            "Every posted debit references the confirmed payee.",
            "At least one posted debit is missing or references another payee.",
        ),
        _check(
            "LOGICAL_PAYMENT_MATCH",
            bool(posted_debits)
            and all(
                entry.get("logical_payment_id") == contract_id
                for entry in posted_debits
            ),
            "Every posted debit is bound to this logical payment.",
            "At least one posted debit is missing or bound to another payment.",
        ),
        _check(
            "SETTLEMENT_EVIDENCE_PRESENT",
            final_state != "SETTLED" or bool(evidence.get("settlement_reference")),
            "A settled payment includes settlement evidence.",
            "The payment claims settlement without a settlement reference.",
        ),
    )

    return VerificationReport(contract_id=contract_id, run_id=run_id, checks=checks)
