"""Local-only, atomic bill acknowledgement from verified artificial receipts.

Not a real biller connector or settlement claim. Never inserts a payment,
changes a balance, trusts model-supplied evidence, or calls an external service.
"""
import json

from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import TestProviderBill


def acknowledge_recorded_bill(service, tenant: str, reference: str) -> dict:
    base = {"scope": "LOCAL_ARTIFICIAL_BILLER", "money_moved": False,
            "external_settlement_verified": False, "bill_reference": reference}
    if service.durable.mode != "SQLITE_LOCAL":
        return {**base, "state": "UNAVAILABLE", "reason": "CLOUD_CONNECTOR_NOT_IMPLEMENTED"}
    with service.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS friday_bill_acknowledgements (
            tenant_id TEXT NOT NULL, bill_reference TEXT NOT NULL,
            acknowledgement_json TEXT NOT NULL, PRIMARY KEY (tenant_id, bill_reference))""")
        row = db.execute("SELECT bill_json FROM friday_provider_bills WHERE tenant_id=? AND bill_reference=?",
                         (tenant, reference)).fetchone()
        if not row:
            return {**base, "state": "UNVERIFIED", "reason": "BILL_NOT_FOUND"}
        bill = TestProviderBill.model_validate_json(row[0])
        goal = "goal-bill-" + sha256_hex({"tenant": tenant, "provider": bill.provider_id,
                                       "bill": bill.bill_reference})[:24]
        payment = db.execute("SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                             (tenant, goal)).fetchone()
        if not payment:
            return {**base, "state": "UNVERIFIED", "reason": "NO_RECORDED_PAYMENT_DO_NOT_ASSUME_PAID"}
        try:
            receipt = json.loads(payment[0])
            payload = receipt["payload"]
            expected = {"tenant_id": tenant, "goal_id": goal, "provider_id": bill.provider_id,
                        "payee_id": bill.payee_id, "amount_minor": bill.amount_minor,
                        "currency": bill.currency, "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY"}
            valid = (all(payload.get(k) == v for k, v in expected.items())
                     and isinstance(payload.get("operation_id"), str) and bool(payload["operation_id"])
                     and service.signer.verify(payload, receipt["signature"]))
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            return {**base, "state": "HOLD", "reason": "RECEIPT_BINDING_OR_SIGNATURE_INVALID"}
        digest = sha256_hex(receipt)
        old = db.execute("SELECT acknowledgement_json FROM friday_bill_acknowledgements WHERE tenant_id=? AND bill_reference=?",
                         (tenant, reference)).fetchone()
        if old:
            try:
                acknowledgement = json.loads(old[0])
                intact = (acknowledgement["payload"]["receipt_digest"] == digest
                          and service.signer.verify(acknowledgement["payload"], acknowledgement["signature"]))
            except (KeyError, TypeError, ValueError):
                intact = False
            if not intact:
                return {**base, "state": "HOLD", "reason": "ACKNOWLEDGEMENT_RECEIPT_CONFLICT"}
            return {**base, "state": "ALREADY_ACKNOWLEDGED", "acknowledgement": acknowledgement}
        evidence = {**expected, "bill_reference": reference, "operation_id": payload["operation_id"],
                    "receipt_digest": digest, "meaning": "LOCAL_ARTIFICIAL_BILL_RECORD_ACKNOWLEDGED"}
        acknowledgement = {"payload": evidence, "signature": service.signer.sign(evidence),
                           "key_id": service.signer.key_id}
        db.execute("INSERT INTO friday_bill_acknowledgements VALUES (?,?,?)",
                   (tenant, reference, json.dumps(acknowledgement)))
        return {**base, "state": "ACKNOWLEDGED", "acknowledgement": acknowledgement}
