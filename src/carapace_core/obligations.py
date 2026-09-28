"""Evidence frontier and exact obligation checks for the development workbench.

AI chooses read-only evidence lookups. This module decides what those results
support. A model explanation cannot change an amount, payee or missing fact.
This bounded one-line-item model is not a general accounting or tax engine.
"""
from __future__ import annotations

from typing import Any


TOOLS = {
    "supplier_registry": "Previously enrolled supplier and approved beneficiary account",
    "purchase_order": "Agreed quantity, unit price, currency and partial-payment terms",
    "delivery_receipts": "Warehouse-confirmed received quantity for this order",
    "credit_notes": "Approved invoice-specific credits from the accounting record",
    "payment_history": "Prior payment allocation to this invoice",
}


def check_obligation(invoice: dict, evidence: dict[str, dict]) -> dict[str, Any]:
    """Return unresolved constraints or a supported instruction, with provenance.

    Evidence is supplied by server-owned connectors, never by an AI response.
    All amounts use integer minor units. Each conflict lists the records that
    witness it; these are rule-specific witnesses, not a globally minimal proof.
    """
    conflicts: list[dict] = []
    missing = [name for name in TOOLS if name not in evidence]

    def fail(code: str, *sources: str) -> None:
        conflicts.append({"code": code, "sources": ["invoice", *sources]})

    amount = invoice.get("amount_minor")
    if type(amount) is not int or amount <= 0:
        fail("INVALID_INVOICE_AMOUNT")
    for name, record in evidence.items():
        if name not in TOOLS:
            fail("UNRECOGNISED_SOURCE", name)
            continue
        if record.get("supplier_id") != invoice.get("supplier_id"):
            fail("EVIDENCE_SUPPLIER_MISMATCH", name)
        if record.get("available") is not True:
            fail("SOURCE_UNAVAILABLE", name)
        if record.get("currency") != invoice.get("currency"):
            fail("CURRENCY_MISMATCH", name)
        if name != "supplier_registry" and record.get("order_id") != invoice.get("order_id"):
            fail("EVIDENCE_ORDER_MISMATCH", name)
        if name in {"credit_notes", "payment_history"} and record.get("invoice_id") != invoice.get("invoice_id"):
            fail("EVIDENCE_INVOICE_MISMATCH", name)

    supplier = evidence.get("supplier_registry")
    if supplier and supplier.get("account") != invoice.get("requested_account"):
        fail("BENEFICIARY_CHANGE_UNVERIFIED", "supplier_registry")
    po = evidence.get("purchase_order")
    received = evidence.get("delivery_receipts")
    credits = evidence.get("credit_notes")
    history = evidence.get("payment_history")
    if po:
        for field in ("quantity", "unit_price_minor"):
            if type(po.get(field)) is not int or po[field] <= 0:
                fail("INVALID_ORDER_VALUES", "purchase_order")
        if not conflicts and amount != po["quantity"] * po["unit_price_minor"]:
            fail("INVOICE_EXCEEDS_OR_DIFFERS_FROM_ORDER", "purchase_order")
    if received:
        if type(received.get("quantity")) is not int or received["quantity"] < 0:
            fail("INVALID_DELIVERY_QUANTITY", "delivery_receipts")
        if received.get("conflicted") is not False:
            fail("CONFLICTING_DELIVERY_EVIDENCE", "delivery_receipts")
    if po and received and not conflicts:
        if received["quantity"] > po["quantity"]:
            fail("DELIVERY_EXCEEDS_ORDER", "purchase_order", "delivery_receipts")
        elif received["quantity"] < po["quantity"] and po.get("partial_payment_agreed") is not True:
            fail("PARTIAL_PAYMENT_NOT_AGREED", "purchase_order", "delivery_receipts")
    for name, record in (("credit_notes", credits), ("payment_history", history)):
        if record and (type(record.get("amount_minor")) is not int or record["amount_minor"] < 0):
            fail("INVALID_ACCOUNTING_AMOUNT", name)

    decision = "HOLD" if conflicts else "INVESTIGATE" if missing else "READY"
    due = None
    if decision == "READY":
        due = received["quantity"] * po["unit_price_minor"] - credits["amount_minor"] - history["amount_minor"]
        if due < 0:
            fail("CREDITS_OR_PAYMENTS_EXCEED_OBLIGATION", "purchase_order", "delivery_receipts", "credit_notes", "payment_history")
            decision = "HOLD"
        elif due == 0:
            decision = "NO_PAYMENT_DUE"
    return {
        "decision": decision, "missing_evidence": missing,
        "conflicts": conflicts, "payable_minor": due,
        "requested_minor": amount, "currency": invoice.get("currency"),
        "payee_account": supplier.get("account") if supplier else None,
        "equation": "received quantity × agreed unit price − approved credits − prior allocations",
        "policy_version": "obligation-rules-v1",
    }


def evidence_graph(invoice: dict, evidence: dict[str, dict]) -> dict:
    return {
        "nodes": [{"id": "invoice", "authority": "UNTRUSTED_REQUEST", "data": invoice}]
        + [{"id": name, "authority": "DEVELOPMENT_CONNECTOR", "data": record} for name, record in evidence.items()],
        "edges": [{"source": name, "target": "invoice", "relation": {
            "supplier_registry": "constrains_beneficiary", "purchase_order": "bounds_obligation",
            "delivery_receipts": "establishes_received_quantity", "credit_notes": "reduces_payable",
            "payment_history": "establishes_prior_allocation",
        }[name]} for name in evidence],
    }
