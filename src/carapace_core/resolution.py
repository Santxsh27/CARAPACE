"""Typed financial action programs and a deterministic, side-effect-free verifier.

The model may compose a program; only the fixed executor implements its verbs.
No generated Python, shell, URLs, SQL or arbitrary banking tools are executed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .obligations import check_obligation


class ResolutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["DEFER_UNDELIVERED", "APPLY_APPROVED_CREDIT", "RECOGNISE_PRIOR_PAYMENT", "POST_PAYMENT"]
    amount_minor: int = Field(strict=True, gt=0, le=100_000_000)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)


class ResolutionProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str = Field(min_length=1, max_length=120)
    payee_account: str = Field(min_length=1, max_length=120)
    currency: Literal["INR"]
    explanation: str = Field(min_length=5, max_length=900)
    steps: list[ResolutionStep] = Field(min_length=1, max_length=4)


SOURCES = {
    "DEFER_UNDELIVERED": {"purchase_order", "delivery_receipts"},
    "APPLY_APPROVED_CREDIT": {"credit_notes"},
    "RECOGNISE_PRIOR_PAYMENT": {"payment_history"},
    "POST_PAYMENT": {"supplier_registry", "purchase_order", "delivery_receipts", "credit_notes", "payment_history"},
}


def local_resolution_program(invoice: dict, evidence: dict) -> ResolutionProgram:
    """Explicit rule baseline, never presented as model generation."""
    report = check_obligation(invoice, evidence)
    if report["decision"] != "READY":
        raise ValueError("an unsupported obligation cannot have a payment program")
    deferred = invoice["amount_minor"] - evidence["delivery_receipts"]["quantity"] * evidence["purchase_order"]["unit_price_minor"]
    amounts = [("DEFER_UNDELIVERED", deferred), ("APPLY_APPROVED_CREDIT", evidence["credit_notes"]["amount_minor"]),
               ("RECOGNISE_PRIOR_PAYMENT", evidence["payment_history"]["amount_minor"]), ("POST_PAYMENT", report["payable_minor"])]
    return ResolutionProgram(invoice_id=invoice["invoice_id"], payee_account=report["payee_account"], currency=invoice["currency"],
        explanation="Defer goods not received, apply approved credits and prior allocations, then pay only the remaining supported amount.",
        steps=[ResolutionStep(action=action, amount_minor=amount, evidence_ids=sorted(SOURCES[action])) for action, amount in amounts if amount > 0])


def verify_resolution(program: ResolutionProgram, invoice: dict, evidence: dict, mandate: dict) -> dict:
    """Interpret a candidate without writes; require each justified effect once."""
    report = check_obligation(invoice, evidence)
    errors: list[str] = []
    if report["decision"] != "READY":
        return {"passed": False, "errors": ["OBLIGATION_NOT_READY"], "effects": []}
    if program.invoice_id != invoice["invoice_id"]:
        errors.append("WRONG_INVOICE")
    if program.currency != invoice["currency"] or program.currency != mandate["currency"]:
        errors.append("WRONG_CURRENCY")
    if program.payee_account != report["payee_account"] or program.payee_account != mandate["account"]:
        errors.append("WRONG_BENEFICIARY")
    if invoice["supplier_id"] != mandate["supplier_id"]:
        errors.append("SUPPLIER_OUTSIDE_MANDATE")
    expected = {
        "DEFER_UNDELIVERED": invoice["amount_minor"] - evidence["delivery_receipts"]["quantity"] * evidence["purchase_order"]["unit_price_minor"],
        "APPLY_APPROVED_CREDIT": evidence["credit_notes"]["amount_minor"],
        "RECOGNISE_PRIOR_PAYMENT": evidence["payment_history"]["amount_minor"],
        "POST_PAYMENT": report["payable_minor"],
    }
    balance = invoice["amount_minor"]
    effects, seen = [], set()
    ranks = {name: index for index, name in enumerate(SOURCES)}
    last_rank = -1
    for step in program.steps:
        if step.action in seen:
            errors.append("REPEATED_ACTION")
        seen.add(step.action)
        if ranks[step.action] < last_rank:
            errors.append("UNSAFE_ACTION_ORDER")
        last_rank = ranks[step.action]
        if not SOURCES[step.action].issubset(step.evidence_ids) or not set(step.evidence_ids).issubset(evidence):
            errors.append("UNSUPPORTED_ACTION_EVIDENCE")
        if step.amount_minor != expected[step.action]:
            errors.append("UNSUPPORTED_ACTION_AMOUNT")
        if step.action == "POST_PAYMENT" and step.amount_minor > mandate["per_payment_limit_minor"]:
            errors.append("PAYMENT_LIMIT_EXCEEDED")
        balance -= step.amount_minor
        if balance < 0:
            errors.append("OBLIGATION_OVERDRAWN")
        effects.append({"action": step.action, "amount_minor": step.amount_minor})
    if seen != {action for action, amount in expected.items() if amount > 0}:
        errors.append("REQUIRED_ACTIONS_MISSING")
    if balance != 0:
        errors.append("RESOLUTION_DOES_NOT_BALANCE")
    return {"passed": not errors, "errors": sorted(set(errors)), "effects": effects,
            "payable_minor": report["payable_minor"], "deferred_minor": expected["DEFER_UNDELIVERED"],
            "credit_minor": expected["APPLY_APPROVED_CREDIT"], "remaining_current_payable_minor": balance,
            "scope": "Exact checks within the single-line-item development model, not a universal safety proof."}


def challenge_resolution(program: ResolutionProgram, invoice: dict, evidence: dict, mandate: dict) -> list[dict]:
    """Six bounded negative checks of the guard, not a complete bank simulation."""
    cases = []
    changed = program.model_copy(deep=True)
    changed.payee_account = "unapproved-beneficiary"
    cases.append(("Changed destination rejected", changed, evidence))
    changed = program.model_copy(deep=True)
    changed.steps[-1].amount_minor += 1
    cases.append(("One extra minor unit rejected", changed, evidence))
    changed_evidence = deepcopy(evidence)
    del changed_evidence["delivery_receipts"]
    cases.append(("Missing delivery evidence rejected", program, changed_evidence))
    changed_evidence = deepcopy(evidence)
    changed_evidence["supplier_registry"]["account"] = "changed-source-account"
    cases.append(("Changed source identity rejected", program, changed_evidence))
    changed = program.model_copy(deep=True)
    changed.steps.append(changed.steps[-1].model_copy())
    cases.append(("Repeated payment instruction rejected", changed, evidence))
    changed = program.model_copy(deep=True)
    changed.steps.pop(0)
    cases.append(("Missing required action rejected", changed, evidence))
    return [{"name": name, "rejected": not verify_resolution(candidate, invoice, source, mandate)["passed"]}
            for name, candidate, source in cases]
