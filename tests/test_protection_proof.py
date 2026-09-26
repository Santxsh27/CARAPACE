from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.protection_proof import (
    inclusion_path,
    leaf_hash,
    merkle_root,
    verify_inclusion,
    verify_protection_bundle,
)


class ProtectionProofTests(unittest.TestCase):
    def test_rfc9162_tree_shape_and_every_inclusion_index(self) -> None:
        leaves = [leaf_hash({"index": index}) for index in range(17)]
        for size in range(1, len(leaves) + 1):
            root = merkle_root(leaves[:size])
            for index in range(size):
                path = inclusion_path(leaves[:size], index)
                self.assertTrue(verify_inclusion(leaves[index], index, size, path, root))
                self.assertFalse(verify_inclusion(leaves[index], index, size, path, b"\x00" * 32))
                if path:
                    self.assertFalse(verify_inclusion(leaves[index], index, size, path[:-1], root))

    def test_tampered_proof_or_warning_fails_with_pinned_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bank = BankEnvelopeSigner(Path(directory) / "bank.pem", allow_generate=True)
            witness = BankEnvelopeSigner(Path(directory) / "witness.pem", allow_generate=True)
            receipt = {"receipt_id": "r1", "issued_warning": "Do not pay"}
            bank_signature = bank.sign(receipt)
            record = {"receipt": receipt, "bank_signature": bank_signature}
            digest = leaf_hash(record)
            head = {"tree_size": 1, "root_hash": digest.hex()}
            bundle = {
                "receipt": receipt,
                "bank_signature": bank_signature,
                "leaf_hash": digest.hex(),
                "leaf_index": 0,
                "tree_head": head,
                "head_signature": witness.sign(head),
                "inclusion_path": [],
            }
            keys = {"bank_public_key": bank.public_key_bytes, "witness_public_key": witness.public_key_bytes}
            self.assertTrue(verify_protection_bundle(bundle, **keys))
            changed = copy.deepcopy(bundle)
            changed["receipt"]["issued_warning"] = "Safe to pay"
            self.assertFalse(verify_protection_bundle(changed, **keys))
            changed = copy.deepcopy(bundle)
            changed["tree_head"]["root_hash"] = "00" * 32
            self.assertFalse(verify_protection_bundle(changed, **keys))
            self.assertFalse(
                verify_protection_bundle(
                    bundle, bank_public_key=witness.public_key_bytes,
                    witness_public_key=bank.public_key_bytes,
                )
            )
