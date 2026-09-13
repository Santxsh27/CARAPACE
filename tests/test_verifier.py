from __future__ import annotations

import json
import unittest
from pathlib import Path

from carapace_core.canonical import request_digest
from carapace_core.lifecycle import invalid_transitions
from carapace_core.verifier import verify_payment


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    with (ROOT / "examples" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class CanonicalRequestTests(unittest.TestCase):
    def test_digest_is_stable_across_key_order(self) -> None:
        first = {
            "direction": "SEND",
            "amount_minor": 100,
            "currency": "INR",
            "fees_minor": 0,
            "payee_id": "payee",
            "purpose": "GOODS",
            "reference": "order",
        }
        second = dict(reversed(list(first.items())))
        self.assertEqual(request_digest(first), request_digest(second))


class LifecycleTests(unittest.TestCase):
    def test_valid_lifecycle(self) -> None:
        self.assertEqual(
            invalid_transitions(
                [
                    "DRAFT",
                    "USER_CONFIRMED",
                    "AUTHORIZED",
                    "SUBMITTED",
                    "ACCEPTED",
                    "SETTLED",
                ]
            ),
            [],
        )

    def test_illegal_lifecycle_is_rejected(self) -> None:
        errors = invalid_transitions(["DRAFT", "SETTLED"])
        self.assertIn("illegal lifecycle transition: DRAFT -> SETTLED", errors)


class PaymentVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_example("payment-promise.json")

    def test_valid_execution_matches(self) -> None:
        report = verify_payment(self.contract, load_example("execution-valid.json"))
        self.assertTrue(report.passed)
        self.assertEqual(report.verdict, "MATCH")

    def test_duplicate_debit_is_a_mismatch(self) -> None:
        report = verify_payment(
            self.contract, load_example("execution-duplicate-debit.json")
        )
        self.assertFalse(report.passed)
        failed_codes = {check.code for check in report.checks if not check.passed}
        self.assertIn("AT_MOST_ONE_POSTED_DEBIT", failed_codes)
        self.assertIn("DEBIT_AMOUNT_MATCH", failed_codes)
        self.assertNotIn("DEBIT_CURRENCY_MATCH", failed_codes)
        self.assertNotIn("PAYEE_MATCH", failed_codes)
        self.assertNotIn("LOGICAL_PAYMENT_MATCH", failed_codes)

    def test_empty_lifecycle_is_reported_without_crashing(self) -> None:
        evidence = load_example("execution-valid.json")
        evidence["lifecycle"] = []
        report = verify_payment(self.contract, evidence)
        failed_codes = {check.code for check in report.checks if not check.passed}
        self.assertIn("LEGAL_LIFECYCLE", failed_codes)

    def test_mutated_payment_request_is_a_mismatch(self) -> None:
        evidence = load_example("execution-valid.json")
        evidence["actual_request"]["amount_minor"] = 599900
        evidence["actual_request_hash_sha256"] = request_digest(
            evidence["actual_request"]
        )
        report = verify_payment(self.contract, evidence)
        failed_codes = {check.code for check in report.checks if not check.passed}
        self.assertIn("REQUEST_BOUND_TO_INTENT", failed_codes)

    def test_false_settlement_without_reference_is_rejected(self) -> None:
        evidence = load_example("execution-valid.json")
        evidence["settlement_reference"] = None
        report = verify_payment(self.contract, evidence)
        failed_codes = {check.code for check in report.checks if not check.passed}
        self.assertIn("SETTLEMENT_EVIDENCE_PRESENT", failed_codes)


if __name__ == "__main__":
    unittest.main()
