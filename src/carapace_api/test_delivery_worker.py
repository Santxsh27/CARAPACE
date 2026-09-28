"""Recoverable, test-only delivery of signed postings to the Anthos sample DB.

The CARAPACE posting and its outbox entry commit together in SQLite. This
worker can be restarted or run twice; the Anthos bridge binds one exact row
idempotently in PostgreSQL. It is not an official bank processor adapter.
"""

from __future__ import annotations

from typing import Any

from carapace_integrations.anthos_preflight_bridge import AnthosPreflightBridge

from .preflight import PreflightGate
from .preflight_evidence import PreflightEvidenceLog


class TestDeliveryWorker:
    def __init__(
        self, gate: PreflightGate, evidence_log: PreflightEvidenceLog,
        bridge: AnthosPreflightBridge, *, bank_public_key: bytes,
        witness_public_key: bytes,
    ) -> None:
        self._gate = gate
        self._evidence_log = evidence_log
        self._bridge = bridge
        self._bank_public_key = bank_public_key
        self._witness_public_key = witness_public_key

    def attempt(self, tenant_id: str, transfer_id: str) -> dict[str, Any]:
        delivery = self._gate.get_test_delivery(tenant_id, transfer_id)
        try:
            bundle = self._evidence_log.get_bundle(
                tenant_id, delivery["posting_receipt_id"],
            )
            result = self._bridge.post_once_and_reconcile(
                delivery["transfer"], bundle,
                bank_public_key=self._bank_public_key,
                witness_public_key=self._witness_public_key,
            )
            if result["status"] == "MATCH":
                self._gate.record_test_delivery_match(
                    tenant_id, transfer_id, result["anthos_transaction_id"],
                )
            else:
                self._gate.record_test_delivery_failure(
                    tenant_id, transfer_id, "ANTHOS_TEST_ROW_MISMATCH",
                )
            return result
        except Exception as error:
            # Never mark a match after a failed or incomplete outside-DB step.
            self._gate.record_test_delivery_failure(
                tenant_id, transfer_id, type(error).__name__,
            )
            return {
                "status": "UNAVAILABLE",
                "reason_codes": ["ANTHOS_TEST_DELIVERY_FAILED"],
                "error_type": type(error).__name__,
                "anthos_transaction_id": None,
            }

    def drain_once(self, limit: int = 20) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for tenant_id, transfer_id in self._gate.pending_test_deliveries(limit):
            result = self.attempt(tenant_id, transfer_id)
            results.append({
                "tenant_id": tenant_id,
                "transfer_id": transfer_id,
                "status": result["status"],
            })
        return results

    def status(self, tenant_id: str, transfer_id: str) -> dict[str, Any]:
        """Re-read the Anthos row before displaying a recorded MATCH."""
        delivery = self._gate.get_test_delivery(tenant_id, transfer_id)
        if delivery["status"] != "MATCH":
            return {"status": "PENDING", "anthos_transaction_id": None}
        try:
            bundle = self._evidence_log.get_bundle(
                tenant_id, delivery["posting_receipt_id"],
            )
            result = self._bridge.reconcile_existing(
                delivery["transfer"], bundle,
                bank_public_key=self._bank_public_key,
                witness_public_key=self._witness_public_key,
            )
            if (
                result["status"] == "MATCH"
                and result["anthos_transaction_id"] == delivery["anthos_transaction_id"]
            ):
                return result
            return {"status": "MISMATCH", "anthos_transaction_id": None,
                    "reason_codes": ["RECORDED_TEST_MATCH_NO_LONGER_VERIFIED"]}
        except Exception as error:
            return {"status": "UNAVAILABLE", "anthos_transaction_id": None,
                    "reason_codes": ["ANTHOS_TEST_RECHECK_FAILED"],
                    "error_type": type(error).__name__}
