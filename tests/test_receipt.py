from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from carapace_core.receipt import build_trust_receipt
from carapace_core.verifier import verify_payment


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    with (ROOT / "examples" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class TrustReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_example("payment-promise.json")

    def make_receipt(self, evidence: dict):
        report = verify_payment(self.contract, evidence).as_dict()
        return build_trust_receipt(self.contract, evidence, report)

    def test_settled_matching_payment_receives_highest_proven_level(self) -> None:
        receipt = self.make_receipt(load_example("execution-valid.json"))

        self.assertEqual(receipt.assurance_level, "SETTLEMENT_CONFIRMED")
        self.assertEqual(receipt.verdict, "MATCH")
        self.assertEqual([stage.state for stage in receipt.stages], ["PASS"] * 3)

    def test_posted_but_not_settled_payment_remains_pending(self) -> None:
        evidence = copy.deepcopy(load_example("execution-valid.json"))
        evidence["lifecycle"] = evidence["lifecycle"][:-1]
        evidence["settlement_reference"] = None

        receipt = self.make_receipt(evidence)

        self.assertEqual(receipt.assurance_level, "BANK_POSTING_MATCHED")
        self.assertEqual(receipt.stages[-1].state, "PENDING")
        self.assertIn("final settlement", receipt.summary)

    def test_duplicate_debit_creates_mismatch_receipt(self) -> None:
        receipt = self.make_receipt(
            load_example("execution-duplicate-debit.json")
        )

        self.assertEqual(receipt.assurance_level, "MISMATCH")
        self.assertEqual(receipt.verdict, "MISMATCH")
        posting = next(
            stage for stage in receipt.stages
            if stage.code == "BANK_POSTING_MATCHED"
        )
        self.assertEqual(posting.state, "FAIL")

    def test_receipt_identifier_and_digest_are_reproducible(self) -> None:
        evidence = load_example("execution-valid.json")
        first = self.make_receipt(evidence)
        second = self.make_receipt(evidence)

        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(
            first.evidence_digest_sha256, second.evidence_digest_sha256
        )


if __name__ == "__main__":
    unittest.main()
