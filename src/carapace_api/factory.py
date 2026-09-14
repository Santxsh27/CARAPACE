"""FastAPI factory exposing the CARAPACE deterministic trust boundary."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, FastAPI, HTTPException, status

from carapace_core.canonical import request_digest
from carapace_core.verifier import verify_payment

from .auth import TenantAuthenticator, TenantContext
from .config import Settings
from .models import (
    ContractResponse,
    EvidenceCaseResponse,
    ExecutionEvidence,
    HealthResponse,
    PaymentAssuranceContract,
    RunResponse,
    VerificationReportResponse,
)
from .store import SQLiteEvidenceStore, StorageConflictError, StorageNotFoundError


VERSION = "0.2.0"


def create_app(
    settings: Settings | None = None,
    store: SQLiteEvidenceStore | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_store = store or SQLiteEvidenceStore(resolved_settings.database_path)
    resolved_store.initialize()
    authenticate = TenantAuthenticator(resolved_settings)

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
        try:
            case_id = resolved_store.put_run(
                tenant.tenant_id, evidence_payload, report_payload
            )
        except StorageConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        return RunResponse(
            evidence=evidence,
            report=VerificationReportResponse.model_validate(report_payload),
            case_id=case_id,
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
