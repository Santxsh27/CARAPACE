"""Financial Friday's typed plan language and independent safety kernel.

Gemini may propose and repair a plan, but this module alone decides whether the
plan is executable.  It deliberately contains no model calls or provider writes.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Action = Literal[
    "VERIFY_PROVIDER",
    "LOAD_OBLIGATION",
    "RECONCILE_EXISTING",
    "CREATE_ONE_TIME_PAYMENT",
    "CREATE_RECURRING_MANDATE",
    "CONFIRM_RESULT",
]


class FinancialGoal(BaseModel):
    """The user's immutable delegation boundary."""

    model_config = ConfigDict(extra="forbid")
    goal_id: str = Field(min_length=3, max_length=100)
    instruction: str = Field(min_length=5, max_length=500)
    provider_id: str = Field(min_length=2, max_length=100)
    payee_id: str = Field(min_length=2, max_length=100)
    currency: Literal["INR"] = "INR"
    max_total_minor: int = Field(strict=True, gt=0, le=100_000_000)
    max_fee_minor: int = Field(default=0, strict=True, ge=0, le=10_000_000)
    cadence: Literal["ONE_TIME"] = "ONE_TIME"
    allowed_data_fields: list[Literal["CUSTOMER_REFERENCE", "BILL_REFERENCE"]] = Field(
        default_factory=list, max_length=2
    )
    idempotency_key: str = Field(min_length=8, max_length=120)


class ProviderOption(BaseModel):
    """One provider-authenticated way to satisfy an obligation."""

    model_config = ConfigDict(extra="forbid")
    option_id: str = Field(min_length=2, max_length=100)
    label: str = Field(min_length=2, max_length=200)
    principal_minor: int = Field(strict=True, gt=0, le=100_000_000)
    fee_minor: int = Field(default=0, strict=True, ge=0, le=10_000_000)
    cadence: Literal["ONE_TIME", "RECURRING"]
    authenticated: bool = True


class FinancialEvidence(BaseModel):
    """Authoritative facts supplied by enrolled, server-side connectors."""

    model_config = ConfigDict(extra="forbid")
    obligation_id: str = Field(min_length=2, max_length=100)
    provider_id: str = Field(min_length=2, max_length=100)
    payee_id: str = Field(min_length=2, max_length=100)
    currency: Literal["INR"] = "INR"
    principal_minor: int = Field(strict=True, gt=0, le=100_000_000)
    fee_minor: int = Field(default=0, strict=True, ge=0, le=10_000_000)
    provider_verified: bool
    highlighted_option_id: str = Field(min_length=2, max_length=100)
    available_options: list[ProviderOption] = Field(min_length=1, max_length=8)
    requested_cadence: Literal["ONE_TIME", "RECURRING"]
    requested_data_fields: list[str] = Field(default_factory=list, max_length=8)
    prior_outcome: Literal["NONE", "UNKNOWN", "SUCCEEDED", "FAILED"] = "NONE"
    reconciliation_result: Literal["NOT_APPLICABLE", "SUCCEEDED", "FAILED"] = "NOT_APPLICABLE"
    evidence_ids: list[str] = Field(min_length=1, max_length=8)


class FinancialAction(BaseModel):
    """A small, non-Turing-complete action; never generated code or a URL."""

    model_config = ConfigDict(extra="forbid")
    action: Action
    provider_id: str = Field(min_length=2, max_length=100)
    payee_id: str = Field(min_length=2, max_length=100)
    amount_minor: int = Field(default=0, strict=True, ge=0, le=100_000_000)
    fee_minor: int = Field(default=0, strict=True, ge=0, le=10_000_000)
    cadence: Literal["NONE", "ONE_TIME", "RECURRING"] = "NONE"
    option_id: str | None = Field(default=None, max_length=100)
    data_fields: list[str] = Field(default_factory=list, max_length=8)
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)


class FinancialProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal_id: str = Field(min_length=3, max_length=100)
    explanation: str = Field(min_length=8, max_length=800)
    steps: list[FinancialAction] = Field(min_length=1, max_length=6)


def verify_evidence_identity(goal: FinancialGoal, evidence: FinancialEvidence) -> list[str]:
    """Reject authoritative identity contradictions before any model is called."""

    errors: list[str] = []
    if not evidence.provider_verified:
        errors.append("PROVIDER_NOT_VERIFIED")
    if evidence.provider_id != goal.provider_id:
        errors.append("EVIDENCE_PROVIDER_MISMATCH")
    if evidence.payee_id != goal.payee_id:
        errors.append("EVIDENCE_PAYEE_MISMATCH")
    if evidence.currency != goal.currency:
        errors.append("EVIDENCE_CURRENCY_MISMATCH")
    return sorted(set(errors))


def safe_local_program(goal: FinancialGoal, evidence: FinancialEvidence) -> FinancialProgram:
    """Deterministic comparison planner, explicitly labelled as non-AI."""

    common = {
        "provider_id": goal.provider_id,
        "payee_id": goal.payee_id,
        "evidence_ids": evidence.evidence_ids,
    }
    if evidence.prior_outcome == "UNKNOWN":
        steps = [
            FinancialAction(action="RECONCILE_EXISTING", **common),
            FinancialAction(action="CONFIRM_RESULT", **common),
        ]
        explanation = "Reconcile the unknown provider outcome before considering any retry."
    else:
        choice = next(
            (
                option
                for option in evidence.available_options
                if option.authenticated
                and option.cadence == goal.cadence
                and option.fee_minor <= goal.max_fee_minor
                and option.principal_minor + option.fee_minor <= goal.max_total_minor
            ),
            next(
                option
                for option in evidence.available_options
                if option.option_id == evidence.highlighted_option_id
            ),
        )
        total = choice.principal_minor + choice.fee_minor
        steps = [
            FinancialAction(action="VERIFY_PROVIDER", **common),
            FinancialAction(action="LOAD_OBLIGATION", **common),
            FinancialAction(
                action="CREATE_ONE_TIME_PAYMENT",
                amount_minor=total,
                fee_minor=choice.fee_minor,
                cadence=choice.cadence,
                option_id=choice.option_id,
                data_fields=evidence.requested_data_fields,
                **common,
            ),
            FinancialAction(action="CONFIRM_RESULT", **common),
        ]
        explanation = "Verify the enrolled provider, load the supported bill, make one bounded payment, and confirm its result."
    return FinancialProgram(goal_id=goal.goal_id, explanation=explanation, steps=steps)


def verify_financial_program(
    program: FinancialProgram, goal: FinancialGoal, evidence: FinancialEvidence
) -> dict:
    """Prove a candidate stays inside the goal and current connector evidence."""

    errors = verify_evidence_identity(goal, evidence)
    if program.goal_id != goal.goal_id:
        errors.append("WRONG_GOAL")

    names = [step.action for step in program.steps]
    if len(names) != len(set(names)):
        errors.append("REPEATED_ACTION")
    if "CREATE_RECURRING_MANDATE" in names:
        errors.append("RECURRING_FORBIDDEN")

    total = evidence.principal_minor + evidence.fee_minor
    allowed_fields = set(goal.allowed_data_fields)
    observed_ids = set(evidence.evidence_ids)
    for step in program.steps:
        if step.provider_id != goal.provider_id:
            errors.append("WRONG_PROVIDER")
        if step.payee_id != goal.payee_id:
            errors.append("WRONG_PAYEE")
        if not set(step.evidence_ids).issubset(observed_ids):
            errors.append("UNOBSERVED_EVIDENCE")
        if not set(step.data_fields).issubset(allowed_fields):
            errors.append("EXCESS_DATA_DISCLOSURE")
        if step.action == "CREATE_ONE_TIME_PAYMENT":
            option = next(
                (item for item in evidence.available_options if item.option_id == step.option_id),
                None,
            )
            if option is None:
                errors.append("UNKNOWN_PROVIDER_OPTION")
                continue
            option_total = option.principal_minor + option.fee_minor
            total = option_total
            if not option.authenticated:
                errors.append("UNAUTHENTICATED_PROVIDER_OPTION")
            if step.cadence != "ONE_TIME" or option.cadence != "ONE_TIME":
                errors.append("WRONG_CADENCE")
            if step.amount_minor != option_total:
                errors.append("WRONG_TOTAL")
            if step.fee_minor != option.fee_minor or step.fee_minor > goal.max_fee_minor:
                errors.append("FEE_OUTSIDE_GOAL")
            if step.amount_minor > goal.max_total_minor:
                errors.append("TOTAL_OUTSIDE_GOAL")

    if evidence.prior_outcome == "UNKNOWN":
        if names != ["RECONCILE_EXISTING", "CONFIRM_RESULT"]:
            errors.append("RECONCILIATION_REQUIRED_BEFORE_RETRY")
    else:
        required = [
            "VERIFY_PROVIDER",
            "LOAD_OBLIGATION",
            "CREATE_ONE_TIME_PAYMENT",
            "CONFIRM_RESULT",
        ]
        if names != required:
            errors.append("UNSAFE_ACTION_SEQUENCE")

    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "authorised_total_minor": total,
        "currency": goal.currency,
        "scope": "Bounded demo provider and artificial money; not authority over a real bank account.",
    }


def challenge_financial_program(
    program: FinancialProgram, goal: FinancialGoal, evidence: FinancialEvidence
) -> list[dict]:
    """Run deliberate mutations against the same independent guard."""

    if evidence.prior_outcome == "UNKNOWN":
        changed = program.model_copy(deep=True)
        changed.steps.insert(0, FinancialAction(
            action="CREATE_ONE_TIME_PAYMENT", provider_id=goal.provider_id,
            payee_id=goal.payee_id, amount_minor=evidence.principal_minor,
            cadence="ONE_TIME", evidence_ids=evidence.evidence_ids,
        ))
        return [{
            "name": "Retry before reconciliation rejected",
            "rejected": not verify_financial_program(changed, goal, evidence)["passed"],
        }]

    cases: list[tuple[str, FinancialProgram]] = []
    payment_index = next(i for i, step in enumerate(program.steps) if step.action == "CREATE_ONE_TIME_PAYMENT")
    changed = program.model_copy(deep=True)
    changed.steps[payment_index].amount_minor += 1
    cases.append(("Extra amount rejected", changed))
    changed = program.model_copy(deep=True)
    changed.steps[payment_index].payee_id = "unapproved-payee"
    cases.append(("Changed payee rejected", changed))
    changed = program.model_copy(deep=True)
    changed.steps[payment_index].data_fields = ["CONTACTS"]
    cases.append(("Excess data request rejected", changed))
    changed = program.model_copy(deep=True)
    changed.steps[payment_index].action = "CREATE_RECURRING_MANDATE"
    changed.steps[payment_index].cadence = "RECURRING"
    cases.append(("Recurring mandate rejected", changed))
    changed = program.model_copy(deep=True)
    changed.steps.append(deepcopy(changed.steps[payment_index]))
    cases.append(("Repeated financial action rejected", changed))
    changed = program.model_copy(deep=True)
    changed.steps = [step for step in changed.steps if step.action != "CONFIRM_RESULT"]
    cases.append(("Missing result confirmation rejected", changed))
    return [
        {
            "name": name,
            "rejected": not verify_financial_program(candidate, goal, evidence)["passed"],
        }
        for name, candidate in cases
    ]
