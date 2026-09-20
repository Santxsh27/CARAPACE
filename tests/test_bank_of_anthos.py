from __future__ import annotations

import unittest
from datetime import datetime

from carapace_core.verifier import verify_payment
from carapace_integrations.anthos_demo import build_contract, build_evidence
from carapace_integrations.bank_of_anthos import BankOfAnthosTransaction


def transaction(transaction_id: int) -> BankOfAnthosTransaction:
    return BankOfAnthosTransaction(
        transaction_id=transaction_id,
        from_account="1000000001",
        to_account="2000000002",
        from_routing="883745000",
        to_routing="883745000",
        amount_minor=4_999,
        timestamp=datetime(2026, 9, 15, 12, 0, 0),
    )


class BankOfAnthosMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = build_contract(
            contract_id="pac_boa_unit123",
            payer="1000000001",
            payee="2000000002",
            amount_minor=4_999,
        )

    def test_one_real_ledger_row_maps_to_a_valid_debit(self) -> None:
        evidence = build_evidence(
            contract=self.contract,
            rows=[transaction(41)],
            run_label="correct",
        )

        self.assertEqual(
            evidence["ledger_entries"][0]["entry_id"], "boa:transaction:41"
        )
        self.assertEqual(evidence["lifecycle"][-1], "ACCEPTED")
        self.assertIsNone(evidence["settlement_reference"])
        report = verify_payment(self.contract, evidence)
        self.assertEqual(report.verdict, "MATCH")

    def test_two_bound_rows_prove_a_duplicate_debit(self) -> None:
        evidence = build_evidence(
            contract=self.contract,
            rows=[transaction(41), transaction(42)],
            run_label="duplicate",
        )

        report = verify_payment(self.contract, evidence)
        failed = {check.code for check in report.checks if not check.passed}
        self.assertEqual(report.verdict, "MISMATCH")
        self.assertIn("AT_MOST_ONE_POSTED_DEBIT", failed)

    def test_database_padding_is_removed_from_identifiers(self) -> None:
        row = BankOfAnthosTransaction.from_row(
            (
                9,
                "1000000001   ",
                "2000000002   ",
                "883745000 ",
                "883745000 ",
                500,
                datetime(2026, 9, 15, 12, 0, 0),
            )
        )

        self.assertEqual(row.from_account, "1000000001")
        self.assertEqual(row.to_routing, "883745000")

    def test_public_explorer_record_preserves_exact_ledger_values(self) -> None:
        record = transaction(77).as_public_record()

        self.assertEqual(record["transaction_id"], 77)
        self.assertEqual(record["from_account"], "1000000001")
        self.assertEqual(record["to_account"], "2000000002")
        self.assertEqual(record["amount_minor"], 4_999)
        self.assertEqual(record["timestamp"], "2026-09-15T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
