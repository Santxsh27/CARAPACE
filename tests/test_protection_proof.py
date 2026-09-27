from __future__ import annotations

import copy
import base64
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.checkpoint_monitor import (
    CheckpointRejected, main as audit_main, verify_checkpoint_response,
)
from carapace_core.protection_proof import (
    consistency_path,
    inclusion_path,
    leaf_hash,
    merkle_root,
    verify_inclusion,
    verify_consistency,
    verify_protection_bundle,
)


class ProtectionProofTests(unittest.TestCase):
    def test_every_small_tree_has_an_append_only_consistency_proof(self) -> None:
        leaves = [leaf_hash({"index": index}) for index in range(33)]
        for second_size in range(1, len(leaves) + 1):
            for first_size in range(1, second_size + 1):
                with self.subTest(first_size=first_size, second_size=second_size):
                    first_root = merkle_root(leaves[:first_size])
                    second_root = merkle_root(leaves[:second_size])
                    path = consistency_path(leaves[:second_size], first_size)
                    self.assertTrue(verify_consistency(
                        first_size, second_size, first_root, second_root, path,
                    ))
                    self.assertFalse(verify_consistency(
                        first_size, second_size, b"\x00" * 32, second_root, path,
                    ))
                    if path:
                        self.assertFalse(verify_consistency(
                            first_size, second_size, first_root, second_root, path[:-1],
                        ))
        self.assertFalse(verify_consistency(2, 1, b"\x00" * 32, b"\x00" * 32, []))

    def test_forked_history_cannot_extend_a_retained_root(self) -> None:
        original = [leaf_hash({"index": index}) for index in range(6)]
        fork = [leaf_hash({"fork": True})] + original[1:] + [leaf_hash({"index": 6})]
        self.assertFalse(verify_consistency(
            6, 7, merkle_root(original), merkle_root(fork),
            consistency_path(fork, 6),
        ))

    def test_monitor_uses_pinned_key_and_retained_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            witness = BankEnvelopeSigner(Path(directory) / "witness.pem", allow_generate=True)
            attacker = BankEnvelopeSigner(Path(directory) / "attacker.pem", allow_generate=True)
            leaves = [leaf_hash({"index": index}) for index in range(4)]

            def response(size: int, old_size: int = 0) -> dict:
                head = {
                    "schema_version": "carapace-tree-head-1", "tree_size": size,
                    "root_hash": merkle_root(leaves[:size]).hex(),
                    "witness_key_id": witness.key_id,
                }
                previous = response(old_size)["current_head"] if old_size else None
                return {
                    "schema_version": "carapace-consistency-1",
                    "current_head": head,
                    "current_signature": witness.sign(head),
                    "previous_head": previous,
                    "previous_signature": witness.sign(previous) if previous else None,
                    "consistency_path": [
                        node.hex() for node in consistency_path(leaves[:size], old_size)
                    ] if old_size else [],
                }

            saved = verify_checkpoint_response(
                response(2), previous_state=None,
                witness_public_key=witness.public_key_bytes,
            )
            newer = verify_checkpoint_response(
                response(4, 2), previous_state=saved,
                witness_public_key=witness.public_key_bytes,
            )
            self.assertEqual(newer["head"]["tree_size"], 4)
            forged = response(4, 2)
            forged["consistency_path"][0] = "00" * 32
            with self.assertRaises(CheckpointRejected):
                verify_checkpoint_response(
                    forged, previous_state=saved, witness_public_key=witness.public_key_bytes,
                )
            with self.assertRaises(CheckpointRejected):
                verify_checkpoint_response(
                    response(4, 2), previous_state=saved,
                    witness_public_key=attacker.public_key_bytes,
                )
            rollback = response(1)
            rollback["previous_head"] = saved["head"]
            rollback["previous_signature"] = saved["signature"]
            with self.assertRaises(CheckpointRejected):
                verify_checkpoint_response(
                    rollback, previous_state=saved,
                    witness_public_key=witness.public_key_bytes,
                )

    def test_monitor_keeps_last_good_state_when_next_response_is_forged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            witness = BankEnvelopeSigner(base / "witness.pem", allow_generate=True)
            key_file, state_file = base / "pinned-public-key.txt", base / "monitor.json"
            key_file.write_text(base64.b64encode(witness.public_key_bytes).decode())
            leaf = leaf_hash({"event": "first"})
            head = {
                "schema_version": "carapace-tree-head-1", "tree_size": 1,
                "root_hash": leaf.hex(), "witness_key_id": witness.key_id,
            }
            response = {
                "schema_version": "carapace-consistency-1",
                "current_head": head, "current_signature": witness.sign(head),
                "previous_head": None, "previous_signature": None,
                "consistency_path": [],
            }
            argv = [
                "carapace-witness-audit", "--url", "http://localhost:8080",
                "--state-file", str(state_file), "--witness-public-key-file", str(key_file),
            ]
            with patch("sys.argv", argv), patch(
                "carapace_core.checkpoint_monitor._fetch_checkpoint", return_value=response,
            ), redirect_stdout(io.StringIO()):
                audit_main()
            retained = state_file.read_text()
            self.assertEqual(json.loads(retained)["head"], head)
            forged = copy.deepcopy(response)
            forged["previous_head"] = head
            forged["previous_signature"] = response["current_signature"]
            forged["current_head"]["root_hash"] = "00" * 32
            with patch("sys.argv", argv), patch(
                "carapace_core.checkpoint_monitor._fetch_checkpoint", return_value=forged,
            ), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                audit_main()
            self.assertEqual(state_file.read_text(), retained)

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
