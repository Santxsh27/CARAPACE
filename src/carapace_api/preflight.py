"""Tenant-scoped pre-payment gate backed by one atomic local test ledger."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import canonical_json
from carapace_core.device_ack import (
    build_device_statement, device_key_fingerprint, verify_device_signature,
)

from .preflight_evidence import PreflightEvidenceLog


class PreflightNotFound(Exception):
    pass


class PreflightConflict(Exception):
    pass


class PreflightGate:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS preflight_orders (
                    tenant_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    bank_signature TEXT NOT NULL,
                    decision_json TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, order_id)
                );
                CREATE TABLE IF NOT EXISTS preflight_transfers (
                    tenant_id TEXT NOT NULL,
                    transfer_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    payer_account TEXT NOT NULL,
                    payee_account TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, transfer_id),
                    UNIQUE (tenant_id, order_id),
                    FOREIGN KEY (tenant_id, order_id)
                        REFERENCES preflight_orders (tenant_id, order_id)
                );
                CREATE TABLE IF NOT EXISTS preflight_devices (
                    tenant_id TEXT NOT NULL,
                    payer_account TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    public_key_spki_base64 TEXT NOT NULL,
                    device_key_sha256 TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, payer_account, device_id)
                );
                CREATE TABLE IF NOT EXISTS preflight_acknowledgements (
                    tenant_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    choice TEXT NOT NULL CHECK (choice IN ('PROCEED', 'CANCEL')),
                    statement_json TEXT NOT NULL,
                    device_signature_base64 TEXT NOT NULL,
                    acknowledgement_receipt_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, order_id),
                    FOREIGN KEY (tenant_id, order_id)
                        REFERENCES preflight_orders (tenant_id, order_id)
                );
                """
            )

    def register_device(
        self, tenant_id: str, payer_account: str, device_id: str,
        public_key_spki_base64: str,
    ) -> dict[str, Any]:
        fingerprint = device_key_fingerprint(public_key_spki_base64)
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO preflight_devices VALUES (?, ?, ?, ?, ?, ?)",
                    (tenant_id, payer_account, device_id, public_key_spki_base64,
                     fingerprint, datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise PreflightConflict("device ID is already enrolled for this account") from error
        return {"device_id": device_id, "device_key_sha256": fingerprint}

    def get_device(self, tenant_id: str, payer_account: str, device_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT public_key_spki_base64, device_key_sha256 FROM preflight_devices "
                "WHERE tenant_id=? AND payer_account=? AND device_id=?",
                (tenant_id, payer_account, device_id),
            ).fetchone()
        if row is None:
            raise PreflightNotFound("test device is not enrolled for this payer")
        return dict(row)

    def put_acknowledgement(
        self, tenant_id: str, order_id: str, *, device_id: str, choice: str,
        statement_json: str, device_signature_base64: str, now: datetime,
        verify_envelope: Any, verify_decision: Any,
        evidence_log: PreflightEvidenceLog, bank_signer: BankEnvelopeSigner,
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT envelope_json, bank_signature, decision_json FROM preflight_orders "
                "WHERE tenant_id=? AND order_id=?", (tenant_id, order_id),
            ).fetchone()
            if row is None:
                raise PreflightNotFound("payment order not found")
            envelope = json.loads(row["envelope_json"])
            decision = json.loads(row["decision_json"]) if row["decision_json"] else None
            if not verify_envelope(envelope, row["bank_signature"]):
                raise PreflightConflict("bank payment signature is invalid")
            if decision is None or not verify_decision(decision):
                raise PreflightConflict("signed preflight decision is unavailable")
            if envelope["tenant_id"] != tenant_id or decision["order_id"] != order_id:
                raise PreflightConflict("payment identity mismatch")
            if decision["envelope_signature"] != row["bank_signature"]:
                raise PreflightConflict("decision does not bind this payment")
            if datetime.fromisoformat(envelope["expires_at"]) <= now:
                raise PreflightConflict("payment order expired")
            if choice not in {"PROCEED", "CANCEL"}:
                raise PreflightConflict("unsupported customer choice")
            if decision["verdict"] == "HOLD" and choice == "PROCEED":
                raise PreflightConflict("HOLD cannot be overridden by customer choice")
            device = connection.execute(
                "SELECT public_key_spki_base64, device_key_sha256 FROM preflight_devices "
                "WHERE tenant_id=? AND payer_account=? AND device_id=?",
                (tenant_id, envelope["payer_account"], device_id),
            ).fetchone()
            if device is None:
                raise PreflightConflict("test device is not enrolled for this payer")
            expected = canonical_json(build_device_statement(
                envelope, decision, choice=choice, device_id=device_id,
                device_key_sha256=device["device_key_sha256"],
            ))
            if statement_json != expected:
                raise PreflightConflict("acknowledgement differs from signed payment or warning")
            if not verify_device_signature(
                statement_json, device_signature_base64, device["public_key_spki_base64"],
            ):
                raise PreflightConflict("device acknowledgement signature is invalid")
            receipt_id = f"protection_{uuid4().hex}"
            try:
                connection.execute(
                    "INSERT INTO preflight_acknowledgements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (tenant_id, order_id, decision["decision_id"], device_id, choice,
                     statement_json, device_signature_base64, receipt_id, now.isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise PreflightConflict("payment choice was already recorded") from error
            receipt = {
                "schema_version": "carapace-protection-1",
                "receipt_id": receipt_id,
                "stage": "DEVICE_ACKNOWLEDGEMENT",
                "tenant_id": tenant_id,
                "order_id": order_id,
                "decision_id": decision["decision_id"],
                "decision_receipt_id": decision["protection_receipt_id"],
                "device_id": device_id,
                "device_key_sha256": device["device_key_sha256"],
                "statement": json.loads(statement_json),
                "device_signature_base64": device_signature_base64,
                "choice": choice,
                "recorded_at": now.isoformat(),
                "claim_limit": "A registered development key signed bytes; this does not prove a human saw or understood them.",
            }
            bundle = evidence_log.append(
                connection, tenant_id=tenant_id, receipt=receipt,
                bank_signer=bank_signer,
            )
            connection.commit()
            return bundle
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def put_order(self, tenant_id: str, envelope: Mapping[str, Any], signature: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO preflight_orders VALUES (?, ?, ?, ?, NULL, ?)",
                (tenant_id, envelope["order_id"], canonical_json(envelope), signature,
                 datetime.now(timezone.utc).isoformat()),
            )

    def get_order(self, tenant_id: str, order_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT envelope_json, bank_signature, decision_json FROM preflight_orders WHERE tenant_id=? AND order_id=?",
                (tenant_id, order_id),
            ).fetchone()
        if row is None:
            raise PreflightNotFound("payment order not found")
        return {
            "envelope": json.loads(row["envelope_json"]),
            "bank_signature": row["bank_signature"],
            "decision": json.loads(row["decision_json"]) if row["decision_json"] else None,
        }

    def put_decision(
        self, tenant_id: str, order_id: str, decision: Mapping[str, Any],
        *, receipt: Mapping[str, Any], evidence_log: PreflightEvidenceLog,
        bank_signer: BankEnvelopeSigner,
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = connection.execute(
                "UPDATE preflight_orders SET decision_json=? WHERE tenant_id=? AND order_id=? AND decision_json IS NULL",
                (canonical_json(decision), tenant_id, order_id),
            )
            if result.rowcount != 1:
                raise PreflightConflict("order was already evaluated or is unavailable")
            bundle = evidence_log.append(
                connection, tenant_id=tenant_id, receipt=receipt,
                bank_signer=bank_signer,
            )
            connection.commit()
            return bundle
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def submit(
        self, tenant_id: str, order_id: str, decision_id: str, transfer_id: str,
        *, now: datetime, verify_envelope: Any, verify_decision: Any,
        evidence_log: PreflightEvidenceLog, bank_signer: BankEnvelopeSigner,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Enforce decision and insert synthetic money effect in one SQLite transaction."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT envelope_json, bank_signature, decision_json FROM preflight_orders WHERE tenant_id=? AND order_id=?",
                (tenant_id, order_id),
            ).fetchone()
            if row is None:
                raise PreflightNotFound("payment order not found")
            envelope = json.loads(row["envelope_json"])
            if not verify_envelope(envelope, row["bank_signature"]):
                raise PreflightConflict("bank payment signature is invalid")
            if envelope["tenant_id"] != tenant_id or datetime.fromisoformat(envelope["expires_at"]) <= now:
                raise PreflightConflict("payment order is expired or belongs to another bank")
            if row["decision_json"] is None:
                raise PreflightConflict("payment has no preflight decision")
            decision = json.loads(row["decision_json"])
            if not verify_decision(decision):
                raise PreflightConflict("preflight decision signature is invalid")
            if decision["decision_id"] != decision_id or decision["verdict"] not in {"ALLOW", "WARN"}:
                raise PreflightConflict("payment gate refuses HOLD or an invalid decision")
            if decision["envelope_signature"] != row["bank_signature"]:
                raise PreflightConflict("decision does not bind this signed payment")
            ack = connection.execute(
                "SELECT * FROM preflight_acknowledgements WHERE tenant_id=? AND order_id=?",
                (tenant_id, order_id),
            ).fetchone()
            if ack is None or ack["decision_id"] != decision_id or ack["choice"] != "PROCEED":
                raise PreflightConflict("signed customer-device PROCEED choice is required")
            device = connection.execute(
                "SELECT public_key_spki_base64, device_key_sha256 FROM preflight_devices "
                "WHERE tenant_id=? AND payer_account=? AND device_id=?",
                (tenant_id, envelope["payer_account"], ack["device_id"]),
            ).fetchone()
            if device is None:
                raise PreflightConflict("enrolled test device is unavailable")
            expected_statement = canonical_json(build_device_statement(
                envelope, decision, choice="PROCEED", device_id=ack["device_id"],
                device_key_sha256=device["device_key_sha256"],
            ))
            if ack["statement_json"] != expected_statement or not verify_device_signature(
                expected_statement, ack["device_signature_base64"],
                device["public_key_spki_base64"],
            ):
                raise PreflightConflict("device acknowledgement is invalid")
            receipt_row = connection.execute(
                "SELECT receipt_json, bank_signature FROM preflight_receipts "
                "WHERE tenant_id=? AND receipt_id=?",
                (tenant_id, ack["acknowledgement_receipt_id"]),
            ).fetchone()
            if receipt_row is None:
                raise PreflightConflict("device acknowledgement receipt is missing")
            ack_receipt = json.loads(receipt_row["receipt_json"])
            if (
                not bank_signer.verify(ack_receipt, receipt_row["bank_signature"])
                or ack_receipt.get("stage") != "DEVICE_ACKNOWLEDGEMENT"
                or ack_receipt.get("statement") != json.loads(expected_statement)
                or ack_receipt.get("device_signature_base64") != ack["device_signature_base64"]
                or ack_receipt.get("decision_receipt_id") != decision["protection_receipt_id"]
            ):
                raise PreflightConflict("device acknowledgement receipt is invalid")
            transfer = {
                "transfer_id": transfer_id,
                "order_id": order_id,
                "decision_id": decision_id,
                "payer_account": envelope["payer_account"],
                "payee_account": envelope["payee_account"],
                "amount_minor": envelope["amount_minor"],
                "currency": envelope["currency"],
                "created_at": now.isoformat(),
                "ledger": "CARAPACE_LOCAL_SYNTHETIC",
            }
            connection.execute(
                "INSERT INTO preflight_transfers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tenant_id, transfer_id, order_id, decision_id,
                 transfer["payer_account"], transfer["payee_account"],
                 transfer["amount_minor"], transfer["currency"], transfer["created_at"]),
            )
            receipt = {
                "schema_version": "carapace-protection-1",
                "receipt_id": f"protection_{uuid4().hex}",
                "stage": "SYNTHETIC_POSTING",
                "tenant_id": tenant_id,
                "order_id": order_id,
                "decision_id": decision_id,
                "decision_receipt_id": decision.get("protection_receipt_id"),
                "acknowledgement_receipt_id": ack["acknowledgement_receipt_id"],
                "customer_choice": ack["choice"],
                "gateway_outcome": "POSTED_SYNTHETIC",
                "transfer_id": transfer_id,
                "amount_minor": transfer["amount_minor"],
                "currency": transfer["currency"],
                "bank_payee": envelope["payee_display_name"],
                "bank_payee_account_last4": envelope["payee_account"][-4:],
                "issued_at": now.isoformat(),
                "claim_limit": "Artificial-money posting only; not settlement evidence or customer acknowledgement.",
            }
            bundle = evidence_log.append(
                connection, tenant_id=tenant_id, receipt=receipt,
                bank_signer=bank_signer,
            )
            connection.commit()
            return transfer, bundle
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise PreflightConflict("payment order was already submitted") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_transfers(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM preflight_transfers WHERE tenant_id=? ORDER BY created_at",
                (tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]
