"""Read-only coverage audit for CARAPACE's controlled synthetic postings only."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import canonical_json
from carapace_core.device_ack import build_device_statement, verify_device_signature
from carapace_core.protection_proof import verify_protection_bundle

from .preflight_evidence import EvidenceIntegrityError, EvidenceNotFound, PreflightEvidenceLog


def audit_synthetic_postings(
    database_path: Path, tenant_id: str, *, bank_public_key: bytes,
    witness_public_key: bytes, evidence_log: PreflightEvidenceLog,
) -> dict[str, Any]:
    """Check each observed synthetic transfer has a matching signed evidence chain.

    This cannot discover payments outside this gateway or prove that a deleted
    transfer and all its records never existed. That needs an independent rail.
    """
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")
        transfers = [dict(row) for row in connection.execute(
            "SELECT * FROM preflight_transfers WHERE tenant_id=? ORDER BY transfer_id",
            (tenant_id,),
        )]
        orders = {row["order_id"]: dict(row) for row in connection.execute(
            "SELECT * FROM preflight_orders WHERE tenant_id=?", (tenant_id,),
        )}
        acknowledgements = {row["order_id"]: dict(row) for row in connection.execute(
            "SELECT * FROM preflight_acknowledgements WHERE tenant_id=?", (tenant_id,),
        )}
        devices = {(row["payer_account"], row["device_id"]): dict(row)
                   for row in connection.execute(
                       "SELECT * FROM preflight_devices WHERE tenant_id=?", (tenant_id,),
                   )}
        receipt_rows = [dict(row) for row in connection.execute(
            "SELECT receipt_id, stage, receipt_json FROM preflight_receipts WHERE tenant_id=?",
            (tenant_id,),
        )]
    finally:
        connection.close()

    issues: list[dict[str, str]] = []

    def issue(code: str, transfer_id: str) -> None:
        issues.append({"transfer_id": transfer_id, "code": code})

    receipts: dict[str, dict[str, Any]] = {}
    postings: dict[str, list[dict[str, Any]]] = {}
    for row in receipt_rows:
        try:
            receipt = json.loads(row["receipt_json"])
            if not isinstance(receipt, dict) or receipt.get("receipt_id") != row["receipt_id"]:
                raise ValueError("receipt identity mismatch")
        except (ValueError, TypeError):
            issue("MALFORMED_RECEIPT", row["receipt_id"])
            continue
        receipts[row["receipt_id"]] = receipt
        if row["stage"] == "SYNTHETIC_POSTING":
            postings.setdefault(str(receipt.get("transfer_id")), []).append(receipt)

    transfer_ids = {transfer["transfer_id"] for transfer in transfers}
    for posting_transfer_id in postings:
        if posting_transfer_id not in transfer_ids:
            issue("ORPHAN_POSTING_RECEIPT", posting_transfer_id)

    def proven_receipt(receipt_id: str | None, stage: str, transfer_id: str) -> dict[str, Any] | None:
        if not receipt_id or receipt_id not in receipts:
            issue(f"MISSING_{stage}_RECEIPT", transfer_id)
            return None
        try:
            bundle = evidence_log.get_bundle(tenant_id, receipt_id)
        except (EvidenceNotFound, EvidenceIntegrityError, ValueError, TypeError):
            issue(f"INVALID_{stage}_PROOF", transfer_id)
            return None
        if not verify_protection_bundle(
            bundle, bank_public_key=bank_public_key,
            witness_public_key=witness_public_key,
        ) or bundle["receipt"].get("stage") != stage:
            issue(f"INVALID_{stage}_PROOF", transfer_id)
            return None
        return bundle["receipt"]

    for transfer in transfers:
        transfer_id, order_id = transfer["transfer_id"], transfer["order_id"]
        order = orders.get(order_id)
        if order is None:
            issue("MISSING_ORDER", transfer_id)
            continue
        try:
            envelope = json.loads(order["envelope_json"])
            decision = json.loads(order["decision_json"])
            decision_signature = decision.pop("bank_signature")
            valid_decision = BankEnvelopeSigner.verify_with_public_key(
                decision, decision_signature, bank_public_key,
            )
            decision["bank_signature"] = decision_signature
            valid_order = BankEnvelopeSigner.verify_with_public_key(
                envelope, order["bank_signature"], bank_public_key,
            )
            if not isinstance(envelope, dict) or not isinstance(decision, dict):
                raise ValueError("order data is not an object")
        except (ValueError, TypeError, KeyError, AttributeError):
            issue("MALFORMED_ORDER_OR_DECISION", transfer_id)
            continue
        if not valid_order or not valid_decision:
            issue("INVALID_BANK_SIGNATURE", transfer_id)
        if (
            envelope.get("tenant_id") != tenant_id
            or envelope.get("order_id") != order_id
            or decision.get("order_id") != order_id
            or decision.get("decision_id") != transfer["decision_id"]
            or decision.get("envelope_signature") != order["bank_signature"]
            or decision.get("verdict") not in {"ALLOW", "WARN"}
        ):
            issue("POSTING_NOT_AUTHORIZED_BY_DECISION", transfer_id)
        if any(transfer[field] != envelope.get(field) for field in (
            "payer_account", "payee_account", "amount_minor", "currency",
        )):
            issue("POSTING_FIELDS_DIFFER_FROM_BANK_ORDER", transfer_id)

        decision_receipt_id = decision.get("protection_receipt_id")
        decision_receipt = proven_receipt(decision_receipt_id, "DECISION", transfer_id)
        if decision_receipt and (
            decision_receipt.get("order_id") != order_id
            or decision_receipt.get("decision_id") != transfer["decision_id"]
            or decision_receipt.get("verdict") != decision.get("verdict")
            or decision_receipt.get("issued_warning") != decision.get("customer_message")
            or decision_receipt.get("bank_order_signature") != order["bank_signature"]
            or decision_receipt.get("amount_minor") != envelope.get("amount_minor")
            or decision_receipt.get("direction") != envelope.get("direction")
            or decision_receipt.get("bank_payee") != envelope.get("payee_display_name")
        ):
            issue("DECISION_RECEIPT_MISMATCH", transfer_id)

        ack = acknowledgements.get(order_id)
        if ack is None:
            issue("MISSING_DEVICE_CHOICE", transfer_id)
            continue
        device = devices.get((envelope.get("payer_account"), ack["device_id"]))
        if device is None:
            issue("MISSING_DEVICE_KEY", transfer_id)
        else:
            try:
                expected = canonical_json(build_device_statement(
                    envelope, decision, choice="PROCEED", device_id=ack["device_id"],
                    device_key_sha256=device["device_key_sha256"],
                ))
                valid_choice = (
                    ack["choice"] == "PROCEED"
                    and ack["decision_id"] == transfer["decision_id"]
                    and ack["statement_json"] == expected
                    and verify_device_signature(
                        expected, ack["device_signature_base64"],
                        device["public_key_spki_base64"],
                    )
                )
            except (ValueError, KeyError, TypeError):
                valid_choice = False
            if not valid_choice:
                issue("INVALID_DEVICE_CHOICE", transfer_id)
        ack_receipt = proven_receipt(
            ack["acknowledgement_receipt_id"], "DEVICE_ACKNOWLEDGEMENT", transfer_id,
        )
        try:
            saved_statement = json.loads(ack["statement_json"])
        except (ValueError, TypeError):
            saved_statement = None
        if ack_receipt and (
            ack_receipt.get("order_id") != order_id
            or ack_receipt.get("decision_id") != transfer["decision_id"]
            or ack_receipt.get("decision_receipt_id") != decision_receipt_id
            or saved_statement is None
            or ack_receipt.get("statement") != saved_statement
            or ack_receipt.get("device_signature_base64") != ack["device_signature_base64"]
            or ack_receipt.get("device_id") != ack["device_id"]
            or (device is not None and ack_receipt.get("device_key_sha256") != device["device_key_sha256"])
            or ack_receipt.get("choice") != "PROCEED"
        ):
            issue("DEVICE_RECEIPT_MISMATCH", transfer_id)

        transfer_postings = postings.get(transfer_id, [])
        if len(transfer_postings) != 1:
            issue("POSTING_RECEIPT_COUNT_MISMATCH", transfer_id)
            continue
        posting = proven_receipt(
            transfer_postings[0].get("receipt_id"), "SYNTHETIC_POSTING", transfer_id,
        )
        if posting and (
            posting.get("tenant_id") != tenant_id
            or posting.get("order_id") != order_id
            or posting.get("decision_id") != transfer["decision_id"]
            or posting.get("decision_receipt_id") != decision_receipt_id
            or posting.get("acknowledgement_receipt_id") != ack["acknowledgement_receipt_id"]
            or posting.get("customer_choice") != "PROCEED"
            or posting.get("gateway_outcome") != "POSTED_SYNTHETIC"
            or posting.get("transfer_id") != transfer_id
            or posting.get("amount_minor") != transfer["amount_minor"]
            or posting.get("currency") != transfer["currency"]
            or posting.get("bank_payee") != envelope.get("payee_display_name")
            or posting.get("bank_payee_account_last4") != transfer["payee_account"][-4:]
        ):
            issue("POSTING_RECEIPT_MISMATCH", transfer_id)

    return {
        "scope": "CARAPACE_LOCAL_SYNTHETIC_ONLY",
        "status": "FAIL" if issues else "PASS" if transfers else "NO_POSTINGS",
        "observed_transfer_count": len(transfers),
        "observed_posting_receipt_count": sum(map(len, postings.values())),
        "issues": issues,
        "limit": "Cannot observe or certify transfers outside this controlled gateway and database.",
    }
