from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.protection_proof import leaf_hash
from carapace_integrations.anthos_preflight_bridge import (
    AnthosPreflightBridge, BridgeRejected, reconcile_bound_row,
    validate_bridge_input,
)
from carapace_integrations.bank_of_anthos import (
    LOCAL_ROUTING_NUMBER, BankOfAnthosTransaction,
)


def fixture() -> tuple[dict, dict, bytes, bytes]:
    directory = tempfile.TemporaryDirectory()
    # Keep the key directory alive for this function call only; the public keys
    # and signatures are immutable bytes after it returns.
    try:
        bank = BankEnvelopeSigner(Path(directory.name) / "bank.pem", allow_generate=True)
        witness = BankEnvelopeSigner(Path(directory.name) / "witness.pem", allow_generate=True)
        transfer = {
            "transfer_id": f"synthetic_{uuid4().hex}", "order_id": f"order_{uuid4().hex}",
            "decision_id": f"decision_{uuid4().hex}",
            "payer_account": "1000000001", "payee_account": "2000000002",
            "amount_minor": 499900, "currency": "INR", "ledger": "CARAPACE_LOCAL_SYNTHETIC",
        }
        receipt = {
            "receipt_id": f"protection_{uuid4().hex}", "stage": "SYNTHETIC_POSTING",
            "gateway_outcome": "POSTED_SYNTHETIC", "customer_choice": "PROCEED",
            "transfer_id": transfer["transfer_id"], "order_id": transfer["order_id"],
            "decision_id": transfer["decision_id"],
            "amount_minor": transfer["amount_minor"], "currency": transfer["currency"],
            "bank_payee_account_last4": transfer["payee_account"][-4:],
        }
        bank_signature = bank.sign(receipt)
        leaf = leaf_hash({"receipt": receipt, "bank_signature": bank_signature})
        head = {
            "schema_version": "carapace-tree-head-1", "tree_size": 1,
            "root_hash": leaf.hex(), "witness_key_id": witness.key_id,
        }
        bundle = {
            "receipt": receipt, "bank_signature": bank_signature,
            "leaf_hash": leaf.hex(), "leaf_index": 0,
            "tree_head": head, "head_signature": witness.sign(head),
            "inclusion_path": [],
        }
        return transfer, bundle, bank.public_key_bytes, witness.public_key_bytes
    finally:
        directory.cleanup()


class AnthosPreflightBridgeTests(unittest.TestCase):
    def test_test_bridge_requires_opt_in_and_local_database(self) -> None:
        local = "postgresql://test:test@localhost:5432/postgresdb"
        with self.assertRaises(BridgeRejected):
            AnthosPreflightBridge(local)
        with self.assertRaises(BridgeRejected):
            AnthosPreflightBridge(
                "postgresql://test:test@bank.example:5432/postgresdb",
                allow_test_writes=True,
            )
        with self.assertRaises(BridgeRejected):
            AnthosPreflightBridge(
                "postgresql://test:test@localhost:5432/production",
                allow_test_writes=True,
            )
        self.assertIsInstance(
            AnthosPreflightBridge(local, allow_test_writes=True), AnthosPreflightBridge,
        )

    def test_bridge_accepts_only_matching_signed_synthetic_posting(self) -> None:
        transfer, bundle, bank_key, witness_key = fixture()
        digest = validate_bridge_input(
            transfer, bundle, bank_public_key=bank_key, witness_public_key=witness_key,
        )
        self.assertEqual(len(digest), 64)
        changed = dict(transfer, amount_minor=499901)
        with self.assertRaises(BridgeRejected):
            validate_bridge_input(
                changed, bundle, bank_public_key=bank_key, witness_public_key=witness_key,
            )
        forged = {**bundle, "receipt": {**bundle["receipt"], "customer_choice": "CANCEL"}}
        with self.assertRaises(BridgeRejected):
            validate_bridge_input(
                transfer, forged, bank_public_key=bank_key, witness_public_key=witness_key,
            )

    def test_exact_bound_row_reconciliation(self) -> None:
        transfer, bundle, _, _ = fixture()
        binding = {**transfer, "carapace_transfer_id": transfer["transfer_id"],
                   "transaction_id": 23, "posting_receipt_id": bundle["receipt"]["receipt_id"]}
        ledger_row = BankOfAnthosTransaction(
            23, transfer["payer_account"], transfer["payee_account"],
            LOCAL_ROUTING_NUMBER, LOCAL_ROUTING_NUMBER,
            transfer["amount_minor"], datetime.now(timezone.utc),
        )
        self.assertEqual(reconcile_bound_row(transfer, binding, ledger_row)["status"], "MATCH")
        self.assertEqual(reconcile_bound_row(transfer, None, None)["status"], "UNBOUND")
        wrong_amount = BankOfAnthosTransaction(
            23, transfer["payer_account"], transfer["payee_account"],
            LOCAL_ROUTING_NUMBER, LOCAL_ROUTING_NUMBER, 499901,
            datetime.now(timezone.utc),
        )
        result = reconcile_bound_row(transfer, binding, wrong_amount)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertIn("ANTHOS_LEDGER_FIELDS_MISMATCH", result["reason_codes"])

    @unittest.skipUnless(
        os.getenv("CARAPACE_BOA_TEST_DATABASE_URL"),
        "set CARAPACE_BOA_TEST_DATABASE_URL for the authorised local ledger integration test",
    )
    def test_real_anthos_test_row_is_idempotent_and_exactly_bound(self) -> None:
        transfer, bundle, bank_key, witness_key = fixture()
        bridge = AnthosPreflightBridge(
            os.environ["CARAPACE_BOA_TEST_DATABASE_URL"], allow_test_writes=True,
        )
        first = bridge.post_once_and_reconcile(
            transfer, bundle, bank_public_key=bank_key, witness_public_key=witness_key,
        )
        second = bridge.post_once_and_reconcile(
            transfer, bundle, bank_public_key=bank_key, witness_public_key=witness_key,
        )
        self.assertEqual(first["status"], "MATCH")
        self.assertTrue(first["inserted_now"])
        self.assertEqual(second["status"], "MATCH")
        self.assertFalse(second["inserted_now"])
        self.assertEqual(first["anthos_transaction_id"], second["anthos_transaction_id"])
        checked = bridge.reconcile_existing(
            transfer, bundle, bank_public_key=bank_key, witness_public_key=witness_key,
        )
        self.assertEqual(checked["status"], "MATCH")
        self.assertEqual(checked["anthos_transaction_id"], first["anthos_transaction_id"])
