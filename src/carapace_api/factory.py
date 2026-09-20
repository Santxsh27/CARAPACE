"""FastAPI factory exposing the CARAPACE deterministic trust boundary."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from starlette.concurrency import run_in_threadpool

from carapace_ai.factory import create_lens_provider
from carapace_ai.provider import LensIntentProvider
from carapace_core.canonical import request_digest
from carapace_core.fee_policy import assess_upi_charge
from carapace_core.lens import LensInputError, parse_upi_payment_uri, reconcile_intent
from carapace_core.receipt import build_trust_receipt
from carapace_core.verifier import verify_payment

from .auth import TenantAuthenticator, TenantContext
from .config import Settings
from .models import (
    ContractResponse,
    EvidenceCaseResponse,
    ExecutionEvidence,
    FeeShieldRequest,
    FeeShieldResponse,
    HealthResponse,
    LensAnalysisRequest,
    LensAnalysisResponse,
    PaymentAssuranceContract,
    RunResponse,
    TrustReceiptResponse,
    VerificationReportResponse,
)
from .store import SQLiteEvidenceStore, StorageConflictError, StorageNotFoundError


VERSION = "0.5.0"


def create_app(
    settings: Settings | None = None,
    store: SQLiteEvidenceStore | None = None,
    lens_provider: LensIntentProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_store = store or SQLiteEvidenceStore(resolved_settings.database_path)
    resolved_store.initialize()
    authenticate = TenantAuthenticator(resolved_settings)
    resolved_lens_provider = lens_provider or create_lens_provider(resolved_settings)

    application = FastAPI(
        title="CARAPACE Assurance API",
        summary="Bind payment intent, verify execution, and preserve mismatches.",
        version=VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.store = resolved_store

    @application.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", service="carapace-api", version=VERSION)

    @application.get("/health/ready", response_model=HealthResponse, tags=["health"])
    async def ready() -> HealthResponse:
        try:
            resolved_store.ping()
        except sqlite3.Error as error:
            raise HTTPException(status_code=503, detail="evidence store unavailable") from error
        return HealthResponse(status="ok", service="carapace-api", version=VERSION)

    @application.post(
        "/v1/lens/analyze",
        response_model=LensAnalysisResponse,
        tags=["lens"],
    )
    async def analyze_payment_context(
        request: LensAnalysisRequest,
    ) -> LensAnalysisResponse:
        try:
            payment = parse_upi_payment_uri(request.payment_uri)
        except LensInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        try:
            intent = await run_in_threadpool(
                resolved_lens_provider.extract_intent,
                request.message_text,
                request.locale,
            )
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="The configured intent-analysis provider is unavailable.",
            ) from error

        assessment = reconcile_intent(intent, payment)
        return LensAnalysisResponse.model_validate(
            {
                "analysis_id": f"lens_{uuid4().hex}",
                "intent": intent.as_dict(),
                "payment": payment.as_dict(),
                **assessment.as_dict(),
                "provenance": {
                    "provider": resolved_lens_provider.provider_name,
                    "model": resolved_lens_provider.model_name,
                    "mode": resolved_lens_provider.mode,
                    "ai_is_authority": False,
                    "deterministic_policy": "lens-reconciliation-v1",
                },
            }
        )

    @application.post(
        "/v1/fees/upi/assess",
        response_model=FeeShieldResponse,
        tags=["fee-shield"],
    )
    async def assess_upi_fee(
        request: FeeShieldRequest,
        _: TenantContext = Depends(authenticate),
    ) -> FeeShieldResponse:
        assessment = assess_upi_charge(**request.model_dump())
        return FeeShieldResponse.model_validate(assessment.as_dict())

    @application.post(
        "/v1/contracts",
        response_model=ContractResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["contracts"],
    )
    async def create_contract(
        contract: PaymentAssuranceContract,
        tenant: TenantContext = Depends(authenticate),
    ) -> ContractResponse:
        payload = contract.model_dump(mode="json")
        calculated_hash = request_digest(payload["payment"])
        if calculated_hash != payload["integrity"]["request_hash_sha256"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CONTRACT_REQUEST_HASH_INVALID",
                    "message": "request hash does not match the canonical payment fields",
                },
            )
        try:
            resolved_store.put_contract(tenant.tenant_id, payload)
        except StorageConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return ContractResponse(contract=contract)

    @application.get(
        "/v1/contracts/{contract_id}",
        response_model=ContractResponse,
        tags=["contracts"],
    )
    async def get_contract(
        contract_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> ContractResponse:
        try:
            payload = resolved_store.get_contract(tenant.tenant_id, contract_id)
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return ContractResponse(
            contract=PaymentAssuranceContract.model_validate(payload)
        )

    @application.post(
        "/v1/contracts/{contract_id}/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["verification"],
    )
    async def submit_run(
        contract_id: str,
        evidence: ExecutionEvidence,
        tenant: TenantContext = Depends(authenticate),
    ) -> RunResponse:
        if evidence.contract_id != contract_id:
            raise HTTPException(
                status_code=422,
                detail="path contract_id must match evidence contract_id",
            )
        try:
            contract_payload = resolved_store.get_contract(
                tenant.tenant_id, contract_id
            )
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        evidence_payload = evidence.model_dump(mode="json")
        report = verify_payment(contract_payload, evidence_payload)
        report_payload = report.as_dict()
        receipt_payload = build_trust_receipt(
            contract_payload, evidence_payload, report_payload
        ).as_dict()
        try:
            case_id = resolved_store.put_run(
                tenant.tenant_id,
                evidence_payload,
                report_payload,
                receipt_payload,
            )
        except StorageConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return RunResponse(
            evidence=evidence,
            report=VerificationReportResponse.model_validate(report_payload),
            case_id=case_id,
            receipt=TrustReceiptResponse.model_validate(receipt_payload),
        )

    @application.get(
        "/v1/runs/{run_id}",
        response_model=RunResponse,
        tags=["verification"],
    )
    async def get_run(
        run_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> RunResponse:
        try:
            payload = resolved_store.get_run(tenant.tenant_id, run_id)
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return RunResponse.model_validate(payload)

    @application.get(
        "/v1/receipts/{receipt_id}",
        response_model=TrustReceiptResponse,
        tags=["receipts"],
    )
    async def get_receipt(
        receipt_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> TrustReceiptResponse:
        try:
            payload = resolved_store.get_receipt(tenant.tenant_id, receipt_id)
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return TrustReceiptResponse.model_validate(payload)

    @application.get(
        "/v1/cases/{case_id}",
        response_model=EvidenceCaseResponse,
        tags=["cases"],
    )
    async def get_case(
        case_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> EvidenceCaseResponse:
        try:
            payload = resolved_store.get_case(tenant.tenant_id, case_id)
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return EvidenceCaseResponse.model_validate(payload)

    return application
