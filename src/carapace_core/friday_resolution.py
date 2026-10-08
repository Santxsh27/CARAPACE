"""Read-only resolution decisions over connector-owned bank and biller evidence.

This is not signature verification or a bank connector. The caller must verify
provider authentication and supply its trusted issuer allowlists. An AI payload
must never be allowed to populate that trust context. No decision moves money,
refunds a debit, or rewrites a bill; reconciliation is a restricted API request.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=200)]
MinorAmount = Annotated[int, Field(strict=True, gt=0)]
Timestamp = Annotated[int, Field(strict=True, ge=0)]


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class BillBinding(StrictRecord):
    tenant_id: Identifier
    biller_id: Identifier
    bill_id: Identifier
    payee_id: Identifier
    amount_minor: MinorAmount
    currency: Annotated[str, Field(strict=True, pattern=r"^[A-Z]{3}$")]


class BankPosting(StrictRecord):
    binding: BillBinding
    issuer_id: Identifier
    evidence_ref: Identifier
    posting_id: Identifier
    payment_ref: Identifier
    status: Annotated[str, Field(pattern=r"^(SETTLED|PENDING|UNKNOWN|FAILED|REVERSED)$")]
    observed_at: Timestamp


class BillerStatus(StrictRecord):
    binding: BillBinding
    issuer_id: Identifier
    evidence_ref: Identifier
    status: Annotated[str, Field(pattern=r"^(PAID|OVERDUE|DUE|UNKNOWN)$")]
    payment_ref: Identifier | None = None
    observed_at: Timestamp


class ResolutionTrust(StrictRecord):
    """Server-owned connector trust and consent; never populated by the LLM."""

    bank_issuers: tuple[Identifier, ...]
    biller_issuers: tuple[Identifier, ...]
    checked_at: Timestamp
    max_age_seconds: Annotated[int, Field(strict=True, gt=0)] = 300
    reconciliation_permitted: bool = False


class ResolutionState(str, Enum):
    CONFIRMED = "CONFIRMED"
    RECONCILIATION_PROPOSED = "RECONCILIATION_PROPOSED"
    RECONCILIATION_READY = "RECONCILIATION_READY"
    REVIEW_DUPLICATE = "REVIEW_DUPLICATE"
    PENDING = "PENDING"
    UNVERIFIED = "UNVERIFIED"
    HOLD = "HOLD"


class BillResolution(StrictRecord):
    state: ResolutionState
    reason: str
    evidence_refs: tuple[str, ...]
    action: str | None = None
    action_permitted: bool = False
    money_movement_permitted: bool = False


def resolve_bill(
    binding: BillBinding,
    postings: tuple[BankPosting, ...],
    biller: BillerStatus | None,
    trust: ResolutionTrust,
) -> BillResolution:
    """Re-evaluate current evidence immediately before a restricted request.

    Earlier results are not execution permissions. Call again on freshly read
    evidence before sending a request, then bind the request to the bill/payment
    identifiers and use provider-side idempotency. Unknown outcomes never imply
    a failed payment; no branch authorizes a replacement payment or refund.
    """
    refs = tuple(p.evidence_ref for p in postings) + ((biller.evidence_ref,) if biller else ())

    def result(state: ResolutionState, reason: str, action: str | None = None, permitted: bool = False) -> BillResolution:
        return BillResolution(state=state, reason=reason, evidence_refs=refs, action=action, action_permitted=permitted)

    if not postings or biller is None:
        return result(ResolutionState.UNVERIFIED, "MISSING_PROVIDER_EVIDENCE")
    if any(p.binding != binding for p in postings) or biller.binding != binding:
        return result(ResolutionState.HOLD, "EVIDENCE_BINDING_MISMATCH")
    if any(p.issuer_id not in trust.bank_issuers for p in postings) or biller.issuer_id not in trust.biller_issuers:
        return result(ResolutionState.UNVERIFIED, "UNTRUSTED_CONNECTOR_ISSUER")
    for record in (*postings, biller):
        age = trust.checked_at - record.observed_at
        if age < 0 or age > trust.max_age_seconds:
            return result(ResolutionState.UNVERIFIED, "STALE_OR_FUTURE_EVIDENCE")
    if len(set(refs)) != len(refs):
        return result(ResolutionState.HOLD, "DUPLICATE_EVIDENCE_REFERENCE")
    posting_ids = [(p.issuer_id, p.posting_id) for p in postings]
    if len(set(posting_ids)) != len(posting_ids):
        return result(ResolutionState.HOLD, "REPEATED_OR_CONFLICTING_POSTING")
    settled = [p for p in postings if p.status == "SETTLED"]
    if len(settled) > 1:
        return result(ResolutionState.REVIEW_DUPLICATE, "MULTIPLE_SETTLED_DEBITS_REQUIRE_PROVIDER_REVIEW")
    if any(p.status in {"PENDING", "UNKNOWN"} for p in postings):
        return result(ResolutionState.PENDING, "PAYMENT_OUTCOME_NOT_FINAL_DO_NOT_REPAY")
    if not settled:
        return result(ResolutionState.UNVERIFIED, "NO_CONFIRMED_SETTLED_PAYMENT")
    payment = settled[0]
    if any(p.payment_ref == payment.payment_ref and p.status in {"FAILED", "REVERSED"} for p in postings):
        return result(ResolutionState.HOLD, "CONFLICTING_FINAL_PAYMENT_STATUS")
    if biller.payment_ref is not None and biller.payment_ref != payment.payment_ref:
        return result(ResolutionState.HOLD, "BILLER_PAYMENT_REFERENCE_MISMATCH")
    if biller.status == "PAID":
        if biller.payment_ref is None:
            return result(ResolutionState.UNVERIFIED, "PAID_STATUS_MISSING_PAYMENT_LINK")
        return result(ResolutionState.CONFIRMED, "BANK_PAYMENT_MATCHES_BILLER_CONFIRMATION")
    if biller.status in {"OVERDUE", "DUE"}:
        permitted = trust.reconciliation_permitted
        return result(
            ResolutionState.RECONCILIATION_READY if permitted else ResolutionState.RECONCILIATION_PROPOSED,
            "SETTLED_PAYMENT_NOT_ACKNOWLEDGED_BY_BILLER",
            "REQUEST_BILLER_RECONCILIATION", permitted,
        )
    return result(ResolutionState.UNVERIFIED, "BILLER_OUTCOME_UNKNOWN")
