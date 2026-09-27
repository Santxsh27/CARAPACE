"""Test-only bridge from an authorised CARAPACE posting to Anthos PostgreSQL.

This inserts artificial money directly into the sample ledger, not through
Bank of Anthos's official LedgerWriter/payment API. The companion binding
table stores the exact returned transaction ID in the same PostgreSQL
transaction. This is a controlled test boundary, not a production connector.
"""

from __future__ import annotations

from typing import Any, Mapping

import psycopg
from psycopg.conninfo import conninfo_to_dict

from carapace_core.canonical import sha256_hex
from carapace_core.protection_proof import verify_protection_bundle

from .bank_of_anthos import LOCAL_ROUTING_NUMBER, BankOfAnthosTransaction


class BridgeRejected(ValueError):
    pass


def validate_bridge_input(
    transfer: Mapping[str, Any], bundle: Mapping[str, Any], *,
    bank_public_key: bytes, witness_public_key: bytes,
) -> str:
    """Check a disclosed posting proof and return its stable request digest."""
    if not verify_protection_bundle(
        bundle, bank_public_key=bank_public_key, witness_public_key=witness_public_key,
    ):
        raise BridgeRejected("posting receipt or witness proof is invalid")
    receipt = bundle["receipt"]
    if (
        transfer.get("ledger") != "CARAPACE_LOCAL_SYNTHETIC"
        or receipt.get("stage") != "SYNTHETIC_POSTING"
        or receipt.get("gateway_outcome") != "POSTED_SYNTHETIC"
        or receipt.get("customer_choice") != "PROCEED"
        or receipt.get("transfer_id") != transfer.get("transfer_id")
        or receipt.get("order_id") != transfer.get("order_id")
        or receipt.get("decision_id") != transfer.get("decision_id")
        or receipt.get("amount_minor") != transfer.get("amount_minor")
        or receipt.get("currency") != transfer.get("currency")
        or receipt.get("bank_payee_account_last4") != str(transfer.get("payee_account", ""))[-4:]
    ):
        raise BridgeRejected("posting receipt differs from the authorised test transfer")
    for field in ("payer_account", "payee_account"):
        value = transfer.get(field)
        if not isinstance(value, str) or len(value) != 10 or not value.isdigit():
            raise BridgeRejected(f"{field} must be a ten-digit test account")
    for field in ("transfer_id", "order_id", "decision_id"):
        value = transfer.get(field)
        if not isinstance(value, str) or not 8 <= len(value) <= 100:
            raise BridgeRejected(f"{field} is not a valid test identifier")
    if type(transfer.get("amount_minor")) is not int or transfer["amount_minor"] <= 0:
        raise BridgeRejected("amount must be a positive integer in minor units")
    if transfer.get("currency") != "INR":
        raise BridgeRejected("this test bridge currently accepts INR-tagged CARAPACE orders only")
    return sha256_hex({
        "transfer_id": transfer["transfer_id"],
        "order_id": transfer["order_id"],
        "decision_id": transfer["decision_id"],
        "payer_account": transfer["payer_account"],
        "payee_account": transfer["payee_account"],
        "amount_minor": transfer["amount_minor"],
        "currency": transfer["currency"],
        "posting_receipt_id": receipt["receipt_id"],
    })


def reconcile_bound_row(
    transfer: Mapping[str, Any], binding: Mapping[str, Any] | None,
    ledger_row: BankOfAnthosTransaction | None,
) -> dict[str, Any]:
    if binding is None:
        return {"status": "UNBOUND", "reason_codes": ["NO_ANTHOS_TEST_BINDING"],
                "anthos_transaction_id": None}
    transaction_id = binding.get("transaction_id")
    reasons: list[str] = []
    if binding.get("carapace_transfer_id") != transfer.get("transfer_id"):
        reasons.append("BINDING_TRANSFER_ID_MISMATCH")
    if any(binding.get(field) != transfer.get(field) for field in (
        "order_id", "decision_id", "payer_account", "payee_account",
        "amount_minor", "currency",
    )):
        reasons.append("BINDING_PAYMENT_FIELDS_MISMATCH")
    if ledger_row is None or ledger_row.transaction_id != transaction_id:
        reasons.append("ANTHOS_LEDGER_ROW_MISSING")
    elif (
        ledger_row.from_account != transfer.get("payer_account")
        or ledger_row.to_account != transfer.get("payee_account")
        or ledger_row.amount_minor != transfer.get("amount_minor")
        or ledger_row.from_routing != LOCAL_ROUTING_NUMBER
        or ledger_row.to_routing != LOCAL_ROUTING_NUMBER
    ):
        reasons.append("ANTHOS_LEDGER_FIELDS_MISMATCH")
    return {
        "status": "MISMATCH" if reasons else "MATCH",
        "reason_codes": reasons,
        "anthos_transaction_id": transaction_id,
        "scope": "Exact bound row in local Bank of Anthos test PostgreSQL; no settlement or official transfer-service claim.",
    }


class AnthosPreflightBridge:
    def __init__(self, database_url: str, *, allow_test_writes: bool = False) -> None:
        if not allow_test_writes:
            raise BridgeRejected("direct sample-ledger writes require explicit test-only opt-in")
        info = conninfo_to_dict(database_url)
        if info.get("host") not in {"anthos-ledger", "localhost", "127.0.0.1"} or info.get("dbname") != "postgresdb":
            raise BridgeRejected("test bridge accepts only the local Bank of Anthos sample database")
        self._database_url = database_url

    @staticmethod
    def _initialize(connection: psycopg.Connection) -> None:
        connection.execute("CREATE SCHEMA IF NOT EXISTS carapace_test")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS carapace_test.preflight_bindings (
                carapace_transfer_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                posting_receipt_id TEXT NOT NULL,
                payer_account CHAR(10) NOT NULL,
                payee_account CHAR(10) NOT NULL,
                amount_minor INT NOT NULL CHECK (amount_minor > 0),
                currency CHAR(3) NOT NULL,
                request_digest CHAR(64) NOT NULL,
                transaction_id BIGINT UNIQUE REFERENCES public.transactions(transaction_id),
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)

    def post_once_and_reconcile(
        self, transfer: Mapping[str, Any], bundle: Mapping[str, Any], *,
        bank_public_key: bytes, witness_public_key: bytes,
    ) -> dict[str, Any]:
        digest = validate_bridge_input(
            transfer, bundle, bank_public_key=bank_public_key,
            witness_public_key=witness_public_key,
        )
        with psycopg.connect(self._database_url, autocommit=True) as connection:
            self._initialize(connection)
            with connection.transaction():
                inserted = connection.execute("""
                    INSERT INTO carapace_test.preflight_bindings (
                        carapace_transfer_id, order_id, decision_id,
                        posting_receipt_id, payer_account, payee_account,
                        amount_minor, currency, request_digest
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (carapace_transfer_id) DO NOTHING
                """, (
                    transfer["transfer_id"], transfer["order_id"], transfer["decision_id"],
                    bundle["receipt"]["receipt_id"], transfer["payer_account"],
                    transfer["payee_account"], transfer["amount_minor"],
                    transfer["currency"], digest,
                )).rowcount == 1
                row = connection.execute("""
                    SELECT carapace_transfer_id, order_id, decision_id,
                           posting_receipt_id, payer_account, payee_account,
                           amount_minor, currency, request_digest, transaction_id
                    FROM carapace_test.preflight_bindings
                    WHERE carapace_transfer_id=%s FOR UPDATE
                """, (transfer["transfer_id"],)).fetchone()
                if row is None or str(row[8]).strip() != digest:
                    raise BridgeRejected("test transfer ID was reused with different payment evidence")
                if inserted:
                    ledger = connection.execute("""
                        INSERT INTO public.transactions (
                            from_acct, to_acct, from_route, to_route, amount, timestamp
                        ) VALUES (%s, %s, %s, %s, %s, now())
                        RETURNING transaction_id
                    """, (
                        transfer["payer_account"], transfer["payee_account"],
                        LOCAL_ROUTING_NUMBER, LOCAL_ROUTING_NUMBER,
                        transfer["amount_minor"],
                    )).fetchone()
                    if ledger is None:
                        raise RuntimeError("Anthos test ledger did not return a transaction ID")
                    connection.execute("""
                        UPDATE carapace_test.preflight_bindings SET transaction_id=%s
                        WHERE carapace_transfer_id=%s
                    """, (int(ledger[0]), transfer["transfer_id"]))
                    transaction_id = int(ledger[0])
                else:
                    if row[9] is None:
                        raise BridgeRejected("existing Anthos test binding has no ledger row")
                    transaction_id = int(row[9])
                ledger_row = connection.execute("""
                    SELECT transaction_id, from_acct, to_acct, from_route,
                           to_route, amount, timestamp
                    FROM public.transactions WHERE transaction_id=%s
                """, (transaction_id,)).fetchone()
                bound = {
                    "carapace_transfer_id": str(row[0]), "order_id": str(row[1]),
                    "decision_id": str(row[2]), "posting_receipt_id": str(row[3]),
                    "payer_account": str(row[4]).strip(),
                    "payee_account": str(row[5]).strip(), "amount_minor": int(row[6]),
                    "currency": str(row[7]).strip(), "transaction_id": transaction_id,
                }
                result = reconcile_bound_row(
                    transfer, bound,
                    BankOfAnthosTransaction.from_row(ledger_row) if ledger_row else None,
                )
                result["inserted_now"] = inserted
                return result
