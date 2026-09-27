"""Atomic local receipt/witness ledger for the pre-payment demonstration.

The bank and witness use distinct keys, but both currently run under one local
operator. This is cryptographic separation, not operational independence.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import canonical_json
from carapace_core.protection_proof import (
    consistency_path, inclusion_path, leaf_hash, merkle_root,
)


class EvidenceNotFound(Exception):
    pass


class EvidenceIntegrityError(Exception):
    pass


class PreflightEvidenceLog:
    def __init__(self, database_path: Path, witness_signer: BankEnvelopeSigner) -> None:
        self._database_path = database_path
        self._witness_signer = witness_signer

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS preflight_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    bank_signature TEXT NOT NULL,
                    leaf_index INTEGER NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS preflight_witness_leaves (
                    leaf_index INTEGER PRIMARY KEY,
                    leaf_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS preflight_witness_heads (
                    tree_size INTEGER PRIMARY KEY,
                    head_json TEXT NOT NULL,
                    witness_signature TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_preflight_receipts_tenant_order
                    ON preflight_receipts (tenant_id, order_id);
                """
            )

    def append(
        self,
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        receipt: Mapping[str, Any],
        bank_signer: BankEnvelopeSigner,
    ) -> dict[str, Any]:
        """Append using the caller's SQLite transaction; failure rolls it back."""
        if receipt.get("tenant_id") != tenant_id:
            raise EvidenceIntegrityError("receipt bank identity mismatch")
        rows = connection.execute(
            "SELECT leaf_index, leaf_hash FROM preflight_witness_leaves ORDER BY leaf_index"
        ).fetchall()
        leaves = [bytes.fromhex(row["leaf_hash"]) for row in rows]
        if any(row["leaf_index"] != index for index, row in enumerate(rows)):
            raise EvidenceIntegrityError("witness leaf sequence is incomplete")
        if leaves:
            previous = connection.execute(
                "SELECT head_json, witness_signature FROM preflight_witness_heads WHERE tree_size=?",
                (len(leaves),),
            ).fetchone()
            if previous is None:
                raise EvidenceIntegrityError("previous witness checkpoint is missing")
            previous_head = json.loads(previous["head_json"])
            if (
                previous_head.get("root_hash") != merkle_root(leaves).hex()
                or not self._witness_signer.verify(previous_head, previous["witness_signature"])
            ):
                raise EvidenceIntegrityError("previous witness checkpoint is invalid")
        bank_signature = bank_signer.sign(receipt)
        record = {"receipt": dict(receipt), "bank_signature": bank_signature}
        current_leaf = leaf_hash(record)
        leaf_index = len(leaves)
        leaves.append(current_leaf)
        tree_head = {
            "schema_version": "carapace-tree-head-1",
            "tree_size": len(leaves),
            "root_hash": merkle_root(leaves).hex(),
            "witness_key_id": self._witness_signer.key_id,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        head_signature = self._witness_signer.sign(tree_head)
        connection.execute(
            "INSERT INTO preflight_receipts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                receipt["receipt_id"], tenant_id, receipt["order_id"], receipt["stage"],
                canonical_json(receipt), bank_signature, leaf_index,
            ),
        )
        connection.execute(
            "INSERT INTO preflight_witness_leaves VALUES (?, ?)",
            (leaf_index, current_leaf.hex()),
        )
        connection.execute(
            "INSERT INTO preflight_witness_heads VALUES (?, ?, ?)",
            (len(leaves), canonical_json(tree_head), head_signature),
        )
        return {
            "receipt": dict(receipt),
            "bank_signature": bank_signature,
            "leaf_hash": current_leaf.hex(),
            "leaf_index": leaf_index,
            "tree_head": tree_head,
            "head_signature": head_signature,
            "inclusion_path": [node.hex() for node in inclusion_path(leaves, leaf_index)],
        }

    def get_bundle(self, tenant_id: str, receipt_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            # Keep the receipt, head and leaves on one SQLite read snapshot while
            # another request may be appending a new checkpoint.
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT * FROM preflight_receipts WHERE tenant_id=? AND receipt_id=?",
                (tenant_id, receipt_id),
            ).fetchone()
            if row is None:
                raise EvidenceNotFound("protection receipt not found")
            head_row = connection.execute(
                "SELECT head_json, witness_signature FROM preflight_witness_heads ORDER BY tree_size DESC LIMIT 1"
            ).fetchone()
            if head_row is None:
                raise EvidenceIntegrityError("witness checkpoint is missing")
            head = json.loads(head_row["head_json"])
            leaves = [
                bytes.fromhex(item["leaf_hash"])
                for item in connection.execute(
                    "SELECT leaf_hash FROM preflight_witness_leaves ORDER BY leaf_index"
                ).fetchall()
            ]
            if len(leaves) != head["tree_size"]:
                raise EvidenceIntegrityError("witness tree size does not match leaves")
            leaf_index = row["leaf_index"]
            if not 0 <= leaf_index < len(leaves):
                raise EvidenceIntegrityError("receipt points outside witness tree")
            return {
                "receipt": json.loads(row["receipt_json"]),
                "bank_signature": row["bank_signature"],
                "leaf_hash": leaves[leaf_index].hex(),
                "leaf_index": leaf_index,
                "tree_head": head,
                "head_signature": head_row["witness_signature"],
                "inclusion_path": [
                    node.hex() for node in inclusion_path(leaves, leaf_index)
                ],
            }

    def get_checkpoint(self, from_size: int = 0) -> dict[str, Any]:
        """Return signed heads and an RFC 9162 append-only proof, without receipts.

        An external monitor must compare the prior head to one it retained; a
        head supplied by this endpoint alone cannot establish history.
        """
        if type(from_size) is not int or from_size < 0:
            raise ValueError("from_size must be a non-negative integer")
        with self._connect() as connection:
            connection.execute("BEGIN")
            rows = connection.execute(
                "SELECT leaf_index, leaf_hash FROM preflight_witness_leaves ORDER BY leaf_index"
            ).fetchall()
            if not rows:
                raise EvidenceNotFound("no witness checkpoint has been issued")
            if from_size > len(rows):
                raise ValueError("from_size is newer than the witness checkpoint")
            try:
                if any(row["leaf_index"] != index for index, row in enumerate(rows)):
                    raise EvidenceIntegrityError("witness leaf sequence is incomplete")
                leaves = [bytes.fromhex(row["leaf_hash"]) for row in rows]
                if any(len(item) != 32 for item in leaves):
                    raise EvidenceIntegrityError("witness leaf hash has invalid length")

                def signed_head(size: int) -> tuple[dict[str, Any], str]:
                    row = connection.execute(
                        "SELECT head_json, witness_signature FROM preflight_witness_heads WHERE tree_size=?",
                        (size,),
                    ).fetchone()
                    if row is None:
                        raise EvidenceIntegrityError("witness checkpoint is missing")
                    head = json.loads(row["head_json"])
                    signature = row["witness_signature"]
                    if (
                        head.get("schema_version") != "carapace-tree-head-1"
                        or head.get("tree_size") != size
                        or head.get("root_hash") != merkle_root(leaves[:size]).hex()
                        or head.get("witness_key_id") != self._witness_signer.key_id
                        or not self._witness_signer.verify(head, signature)
                    ):
                        raise EvidenceIntegrityError("witness checkpoint is invalid")
                    return head, signature

                current_head, current_signature = signed_head(len(leaves))
                previous_head, previous_signature = (
                    signed_head(from_size) if from_size else (None, None)
                )
                return {
                    "schema_version": "carapace-consistency-1",
                    "current_head": current_head,
                    "current_signature": current_signature,
                    "previous_head": previous_head,
                    "previous_signature": previous_signature,
                    "consistency_path": (
                        [node.hex() for node in consistency_path(leaves, from_size)]
                        if from_size else []
                    ),
                }
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                raise EvidenceIntegrityError("witness checkpoint is malformed") from error
