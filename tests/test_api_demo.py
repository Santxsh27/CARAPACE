from __future__ import annotations

import unittest
from pathlib import Path

from carapace_core.api_demo import _prepare_payloads
from carapace_core.canonical import request_digest


ROOT = Path(__file__).resolve().parents[1]


class ApiDemoPayloadTests(unittest.TestCase):
    def test_demo_creates_fresh_consistent_identifiers(self) -> None:
        first = _prepare_payloads(ROOT / "examples")
        second = _prepare_payloads(ROOT / "examples")

        first_contract, first_valid, first_duplicate = first
        second_contract, _, _ = second

        self.assertNotEqual(
            first_contract["contract_id"], second_contract["contract_id"]
        )
        self.assertEqual(first_valid["contract_id"], first_contract["contract_id"])
        self.assertEqual(
            first_duplicate["contract_id"], first_contract["contract_id"]
        )
        self.assertTrue(
            all(
                entry["logical_payment_id"] == first_contract["contract_id"]
                for entry in first_duplicate["ledger_entries"]
            )
        )

    def test_demo_recomputes_bound_request_hashes(self) -> None:
        contract, valid, duplicate = _prepare_payloads(ROOT / "examples")

        self.assertEqual(
            contract["integrity"]["request_hash_sha256"],
            request_digest(contract["payment"]),
        )
        self.assertEqual(
            valid["actual_request_hash_sha256"],
            request_digest(valid["actual_request"]),
        )
        self.assertEqual(
            duplicate["actual_request_hash_sha256"],
            request_digest(duplicate["actual_request"]),
        )


if __name__ == "__main__":
    unittest.main()
