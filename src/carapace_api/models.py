"""Strict public API models for contracts, evidence, reports, and cases."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from carapace_core.fee_policy import MerchantSector, UpiPaymentKind


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentDirection(str, Enum):
    SEND = "SEND"
    REQUEST = "REQUEST"
    RECEIVE_EXPECTED = "RECEIVE_EXPECTED"


class LifecycleState(str, Enum):
    DRAFT = "DRAFT"
    USER_CONFIRMED = "USER_CONFIRMED"
    AUTHORIZED = "AUTHORIZED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class PaymentFields(StrictModel):
    direction: PaymentDirection
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    fees_minor: int = Field(ge=0)
    payee_id: str = Field(min_length=1)
    payee_display_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class ActualPaymentRequest(StrictModel):
    direction: PaymentDirection
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    fees_minor: int = Field(ge=0)
    payee_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class IntegrityFields(StrictModel):
    nonce: str = Field(min_length=16)
    request_hash_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(min_length=8)


class Confirmation(StrictModel):
    confirmed_at: datetime
    method: Literal["BANK_UI", "WALLET_UI", "TEST_FIXTURE"]

    @field_validator("confirmed_at")
    @classmethod
    def confirmed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("confirmed_at must include a timezone")
        return value


class PaymentAssuranceContract(StrictModel):
    schema_version: Literal["1.0"]
    contract_id: str = Field(min_length=8, pattern=r"^[A-Za-z0-9_-]+$")
    created_at: datetime
    expires_at: datetime
    actor_ref: str = Field(min_length=1)
    session_ref: str = Field(min_length=1)
    payment: PaymentFields
    integrity: IntegrityFields
    confirmation: Confirmation
    policy_version: str = Field(min_length=1)

    @field_validator("created_at", "expires_at")
    @classmethod
    def timestamps_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_time_window(self) -> "PaymentAssuranceContract":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        if not self.created_at <= self.confirmation.confirmed_at <= self.expires_at:
            raise ValueError("confirmed_at must fall inside the contract time window")
        return self


class LedgerEntry(StrictModel):
    entry_id: str = Field(min_length=1)
    logical_payment_id: str = Field(min_length=1)
    account_ref: str = Field(min_length=1)
    counterparty_ref: str = Field(min_length=1)
    direction: Literal["DEBIT", "CREDIT"]
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    status: Literal["PENDING", "POSTED", "REVERSED"]


class ExecutionEvidence(StrictModel):
    schema_version: Literal["1.0"]
    run_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    contract_id: str = Field(min_length=8, pattern=r"^[A-Za-z0-9_-]+$")
    observed_at: datetime
    actual_request: ActualPaymentRequest
    actual_request_hash_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(min_length=8)
    lifecycle: list[LifecycleState] = Field(min_length=1)
    settlement_reference: str | None = None
    ledger_entries: list[LedgerEntry]

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return value


class HealthResponse(StrictModel):
    status: Literal["ok"]
    service: Literal["carapace-api"]
    version: str


class ContractResponse(StrictModel):
    contract: PaymentAssuranceContract


class CheckResponse(StrictModel):
    code: str
    passed: bool
    severity: str
    message: str


class VerificationReportResponse(StrictModel):
    contract_id: str
    run_id: str
    verdict: Literal["MATCH", "MISMATCH"]
    checks: list[CheckResponse]


class ReceiptStageResponse(StrictModel):
    code: Literal[
        "PAYMENT_FIELDS_BOUND",
        "BANK_POSTING_MATCHED",
        "SETTLEMENT_CONFIRMED",
    ]
    state: Literal["PASS", "PENDING", "FAIL"]
    message: str


class TrustReceiptResponse(StrictModel):
    schema_version: Literal["1.0"]
    receipt_id: str = Field(pattern=r"^receipt_[a-f0-9]{24}$")
    contract_id: str
    run_id: str
    issued_at: datetime
    assurance_level: Literal[
        "PAYMENT_FIELDS_BOUND",
        "BANK_POSTING_MATCHED",
        "SETTLEMENT_CONFIRMED",
        "MISMATCH",
        "UNVERIFIED",
    ]
    verdict: Literal["MATCH", "MISMATCH"]
    summary: str
    direction: PaymentDirection
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    payee_id: str
    payee_display_name: str
    stages: list[ReceiptStageResponse]
    evidence_digest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    integrity_protection: Literal["SHA256_EVIDENCE_DIGEST"]


class RunResponse(StrictModel):
    evidence: ExecutionEvidence
    report: VerificationReportResponse
    case_id: str | None
    receipt: TrustReceiptResponse | None = None


class EvidenceCaseResponse(StrictModel):
    case_id: str
    run_id: str
    contract_id: str
    status: Literal["OPEN"]
    severity: Literal["CRITICAL"]
    failed_checks: list[str]
    created_at: datetime


class FeeShieldRequest(StrictModel):
    amount_minor: int = Field(gt=0)
    initiated_on: date
    payment_kind: UpiPaymentKind
    customer_mdr_surcharge_minor: int = Field(ge=0)
    actual_merchant_mdr_minor: int | None = Field(default=None, ge=0)
    sector: MerchantSector = MerchantSector.STANDARD
    merchant_monthly_upi_minor: int | None = Field(default=None, ge=0)


class FeeShieldResponse(StrictModel):
    policy_version: str
    expected_mdr_minor: int
    customer_mdr_surcharge_minor: int
    customer_protected: bool
    merchant_settlement_matches: bool | None
    violations: list[str]
    explanation: str
    verdict: Literal["COMPLIANT", "VIOLATION"]


class LensAnalysisRequest(StrictModel):
    message_text: str = Field(min_length=3, max_length=8_000)
    payment_uri: str = Field(min_length=10, max_length=2_048)
    locale: str = Field(default="en-IN", min_length=2, max_length=20)


class LensIntentResponse(StrictModel):
    expected_direction: Literal["SEND", "REQUEST", "RECEIVE_EXPECTED", "UNKNOWN"]
    expected_amount_minor: int | None
    currency: str
    claimed_entity: str | None
    urgency_detected: bool
    asks_for_pin_to_receive: bool
    summary: str


class LensPaymentResponse(StrictModel):
    direction: Literal["SEND", "REQUEST", "RECEIVE_EXPECTED", "UNKNOWN"]
    amount_minor: int | None
    currency: str
    payee_id: str
    payee_name: str | None
    note: str | None
    source: Literal["UPI_URI"]


class LensFindingResponse(StrictModel):
    code: str
    severity: Literal["MEDIUM", "HIGH", "CRITICAL"]
    title: str
    explanation: str


class LensProvenanceResponse(StrictModel):
    provider: str
    model: str
    mode: Literal["LOCAL_RULES", "GEMINI_API", "VERTEX_AI"]
    ai_is_authority: Literal[False] = False
    input_redaction_applied: bool
    deterministic_policy: Literal["lens-reconciliation-v1"] = "lens-reconciliation-v1"


class LensAnalysisResponse(StrictModel):
    analysis_id: str
    intent: LensIntentResponse
    payment: LensPaymentResponse
    decision: Literal["ALLOW", "CAUTION", "STOP", "UNVERIFIED"]
    findings: list[LensFindingResponse]
    plain_language_result: str
    provenance: LensProvenanceResponse


class AIStatusResponse(StrictModel):
    provider: str
    model: str
    mode: Literal["LOCAL_RULES", "GEMINI_API", "VERTEX_AI"]
    status: Literal["LOCAL_READY", "GEMINI_API_CONFIGURED", "VERTEX_CONFIGURED"]
    cloud_project_configured: bool
    external_ai_configured: bool
    message: str


class DiagnosticScenarioResponse(StrictModel):
    name: str
    fault_injection: str
    expected_contract: str


class CounterfactualSearchResponse(StrictModel):
    original_verdict: Literal["MATCH", "MISMATCH"]
    counterfactual_verdict: Literal["MATCH", "MISMATCH"]
    minimal_interventions: list[str]
    experiments_run: int = Field(ge=0)
    remaining_failed_checks: list[str]


class ProofOpsAnalysisResponse(StrictModel):
    analysis_id: str
    case_id: str
    provider: str
    model: str
    mode: Literal["LOCAL_RULES", "GEMINI_API", "VERTEX_AI"]
    root_cause_summary: str
    suspected_component: str
    confidence: float = Field(ge=0, le=1)
    evidence_codes: list[str]
    patch_strategy: str
    regression_scenarios: list[DiagnosticScenarioResponse]
    counterfactual_search: CounterfactualSearchResponse
    verification_status: Literal["COUNTERFACTUAL_VERIFIED", "NO_SAFE_REPAIR_FOUND"]
    release_authorized: Literal[False] = False
    human_approval_required: Literal[True] = True
