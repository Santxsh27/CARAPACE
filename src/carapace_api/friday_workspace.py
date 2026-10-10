"""Read-only financial workspace over tenant-owned artificial records.

This projection neither calls a model nor authorizes a payment. Totals are a
bounded snapshot, not a complete bank statement or externally verified balance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import FridayMandate, TestProviderBill, bill_increase_requires_review


def financial_workspace(service, tenant: str) -> dict:
    rules = service.mandate(tenant)
    mandate = FridayMandate.model_validate(rules["mandate"])
    balance = rules["sandbox_balance_minor"]
    cloud = service.durable.mode == "FIRESTORE_TRANSACTIONAL"
    if cloud:
        records = service.durable.list("provider_bills", tenant, 100)
    else:
        with service.connect() as db:
            records = [json.loads(row[0]) for row in db.execute(
                "SELECT bill_json FROM friday_provider_bills WHERE tenant_id=? ORDER BY rowid DESC LIMIT 101",
                (tenant,)).fetchall()]
    truncated = len(records) >= 100 if cloud else len(records) > 100
    bills = []
    for record in records[:100]:
        bill = TestProviderBill.model_validate(record)
        goal = "goal-bill-" + sha256_hex({"tenant": tenant, "provider": bill.provider_id,
                                       "bill": bill.bill_reference})[:24]
        if cloud:
            identity = "bill:" + bill.provider_id + ":" + bill.bill_reference
            payment = service.durable.get("payments", tenant, hashlib.sha256(identity.encode()).hexdigest())
            receipt = payment.get("receipt") if payment else None
        else:
            with service.connect() as db:
                row = db.execute("SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                                 (tenant, goal)).fetchone()
            try:
                receipt = json.loads(row[0]) if row else None
            except (TypeError, ValueError):
                receipt = {}
        status, reason = "UNPAID_RECORD", "No matching internal payment receipt; external payment status is unknown."
        if receipt is not None:
            try:
                payload = receipt["payload"]
                valid = (all(payload.get(k) == v for k, v in {
                    "tenant_id": tenant, "goal_id": goal, "provider_id": bill.provider_id,
                    "payee_id": bill.payee_id, "amount_minor": bill.amount_minor,
                    "currency": bill.currency, "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY"}.items())
                    and service.signer.verify(payload, receipt["signature"]))
            except (KeyError, TypeError, ValueError):
                valid = False
            status = "RECORDED_PAID" if valid else "RECEIPT_CONFLICT"
            reason = ("Signed internal artificial-payment receipt matched; external settlement is not established."
                      if valid else "Existing receipt does not match this bill; do not pay again without reconciliation.")
        elif bill_increase_requires_review(bill, mandate.bill_increase_review_percent):
            status, reason = "REVIEW_INCREASE", "Increase exceeds your chosen review threshold; this is not a fraud verdict."
        bills.append({**bill.model_dump(), "status": status, "reason": reason,
                      "history_status": "AVAILABLE" if bill.previous_amount_minor else "NOT_AVAILABLE"})
    bills.sort(key=lambda b: (b["due_date"], b["bill_reference"]))
    committed = sum(b["amount_minor"] for b in bills if b["status"] != "RECORDED_PAID")
    available = max(0, balance - mandate.protected_balance_minor)
    brief = service.daily_brief(tenant)
    return {
        "scope": "ARTIFICIAL_MONEY", "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True, "money_moved": False, "currency": "INR",
        "balance_minor": balance, "protected_balance_minor": mandate.protected_balance_minor,
        "available_above_reserve_minor": available, "bills": bills,
        "automatic_payment_limit_minor": mandate.automatic_payment_limit_minor,
        "upcoming_total_minor": committed,
        "budget": {"committed_minor": committed,
                   "remaining_after_bills_minor": available - committed,
                   "shortfall_minor": max(0, committed - available),
                   "meaning": "Planning estimate over displayed records, not a payment reservation or instruction."},
        "coverage": {"bill_records_returned": len(bills), "limit": 100, "may_be_truncated": truncated,
                     "snapshot_atomic": False},
        "recent_runs": brief["recent_runs"],
        "capabilities": [
            {"id": "understand", "title": "Understand my money", "status": "AVAILABLE",
             "description": "See recorded bills, reserve, a cash-flow estimate and completed task evidence."},
            {"id": "handle", "title": "Handle supported tasks", "status": "SANDBOX",
             "description": "Gemini interprets new bill requests; the verifier permits artificial payments within your rules."},
            {"id": "protect", "title": "Protect my decisions", "status": "AVAILABLE",
             "description": "Stop mismatched recipients, amounts, recurring requests, unusual increases and reserve violations."},
            {"id": "resolve", "title": "Resolve financial problems", "status": "CONNECTOR_PENDING",
             "description": "Receipt-first replay works today. Biller correction and refund execution are not connected."},
        ],
        "limits": ["No real bank account, external settlement or stock-trading service is connected.",
                   "Provider records are same-operator development data, not independent utility verification.",
                   "Records may be incomplete or change between reads; the execution gate rechecks current state.",
                   "Unknown external payments and receipt conflicts require reconciliation, not another blind payment.",
                   "No bank credentials, PINs or OTPs are requested. Always-on phone monitoring is not enabled."],
    }
