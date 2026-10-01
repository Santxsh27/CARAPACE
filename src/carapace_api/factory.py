"""FastAPI factory exposing the CARAPACE deterministic trust boundary."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from starlette.concurrency import run_in_threadpool

from carapace_ai.factory import create_incident_reasoning_provider, create_lens_provider
from carapace_ai.incident_reasoning import (
    IncidentReasoningProvider,
    LocalIncidentReasoningProvider,
    build_minimised_incident_context,
)
from carapace_ai.provider import LensIntentProvider
from carapace_ai.operations import create_operations_planner
from carapace_ai.financial_friday import create_financial_friday_planner
from carapace_ai.redaction import redact_for_model
from carapace_core.canonical import request_digest
from carapace_core.fee_policy import assess_upi_charge
from carapace_core.lens import LensInputError, parse_upi_payment_uri, reconcile_intent
from carapace_core.receipt import build_trust_receipt
from carapace_core.release_passport import (
    build_release_passport,
    verify_release_passport,
)
from carapace_core.counterfactual import search_minimal_repair
from carapace_core.verifier import verify_payment
from carapace_core.bank_envelope import BankEnvelopeSigner

from .auth import TenantAuthenticator, TenantContext
from .config import Settings
from .models import (
    ContractResponse,
    AIStatusResponse,
    EvidenceCaseResponse,
    ExecutionEvidence,
    FeeShieldRequest,
    FeeShieldResponse,
    HealthResponse,
    LensAnalysisRequest,
    LensAnalysisResponse,
    PaymentAssuranceContract,
    ProofOpsAnalysisResponse,
    ProofOpsApprovalRequest,
    ProofOpsApprovalResponse,
    ReleasePassportResponse,
    RunResponse,
    TrustReceiptResponse,
    VerificationReportResponse,
)
from .store import SQLiteEvidenceStore, StorageConflictError, StorageNotFoundError
from .preflight import PreflightGate
from .preflight_evidence import PreflightEvidenceLog
from .preflight_routes import register_preflight_routes
from .test_delivery_worker import TestDeliveryWorker
from .operations import OperationsService
from .operations_routes import register_operations_routes
from .financial_friday import FinancialFridayService
from .financial_friday_routes import register_financial_friday_routes
from carapace_integrations.anthos_preflight_bridge import AnthosPreflightBridge


VERSION = "0.10.0"
LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    store: SQLiteEvidenceStore | None = None,
    lens_provider: LensIntentProvider | None = None,
    incident_provider: IncidentReasoningProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_store = store or SQLiteEvidenceStore(resolved_settings.database_path)
    resolved_store.initialize()
    authenticate = TenantAuthenticator(resolved_settings)
    resolved_lens_provider = lens_provider or create_lens_provider(resolved_settings)
    resolved_incident_provider = incident_provider or create_incident_reasoning_provider(
        resolved_lens_provider
    )

    test_delivery_worker: TestDeliveryWorker | None = None

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        stop = threading.Event()
        def inbox_loop():
            while not stop.is_set():
                try:
                    _application.state.friday_inbox.tick()
                except Exception as error:
                    LOGGER.warning("Friday inbox check failed: %s", type(error).__name__)
                stop.wait(5)
        inbox_thread = None
        if hasattr(_application.state, "friday_inbox") and resolved_settings.environment != "test":
            inbox_thread = threading.Thread(target=inbox_loop, daemon=True, name="friday-inbox")
            inbox_thread.start()
        thread: threading.Thread | None = None
        if test_delivery_worker is not None:
            def replay_loop() -> None:
                while not stop.is_set():
                    try:
                        test_delivery_worker.drain_once()
                    except Exception as error:
                        LOGGER.warning("test bridge replay loop failed: %s", type(error).__name__)
                    stop.wait(5)

            thread = threading.Thread(target=replay_loop, name="carapace-test-bridge", daemon=True)
            thread.start()
        try:
            yield
        finally:
            stop.set()
            if inbox_thread is not None:
                inbox_thread.join(timeout=1)
            if thread is not None:
                thread.join(timeout=4)

    application = FastAPI(
        title="Financial Friday Assurance API",
        summary="AI-planned financial tasks with deterministic safety and one-time execution.",
        version=VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.state.store = resolved_store
    preflight_gate = PreflightGate(resolved_settings.database_path)
    preflight_gate.initialize()
    signer = BankEnvelopeSigner(
        resolved_settings.bank_signing_key_path or resolved_settings.database_path.parent / "bank-dev-ed25519.pem",
        allow_generate=resolved_settings.environment in {"development", "test"},
    )
    witness_key_path = resolved_settings.witness_signing_key_path or resolved_settings.database_path.parent / "witness-dev-ed25519.pem"
    bank_key_path = resolved_settings.bank_signing_key_path or resolved_settings.database_path.parent / "bank-dev-ed25519.pem"
    if witness_key_path.resolve() == bank_key_path.resolve():
        raise RuntimeError("bank and witness signing keys must be distinct")
    witness_signer = BankEnvelopeSigner(
        witness_key_path,
        allow_generate=resolved_settings.environment in {"development", "test"},
    )
    evidence_log = PreflightEvidenceLog(resolved_settings.database_path, witness_signer)
    evidence_log.initialize()
    if os.getenv("CARAPACE_TEST_ANTHOS_BRIDGE_ENABLED", "false").lower() == "true":
        if resolved_settings.environment not in {"development", "test"}:
            raise RuntimeError("direct Anthos sample-ledger bridge is forbidden outside development/test")
        database_url = os.getenv("BOA_DATABASE_URL", "")
        test_delivery_worker = TestDeliveryWorker(
            preflight_gate, evidence_log,
            AnthosPreflightBridge(database_url, allow_test_writes=True),
            bank_public_key=signer.public_key_bytes,
            witness_public_key=witness_signer.public_key_bytes,
        )
    application.state.test_delivery_worker = test_delivery_worker
    if resolved_settings.environment in {"development", "test"}:
        operations = OperationsService(resolved_settings.database_path, signer, create_operations_planner(resolved_lens_provider))
        application.state.operations = operations
        register_operations_routes(application, operations, authenticate)
        financial_friday = FinancialFridayService(
            resolved_settings.database_path,
            signer,
            create_financial_friday_planner(resolved_lens_provider),
        )
        application.state.financial_friday = financial_friday
        register_financial_friday_routes(application, financial_friday, authenticate)
    register_preflight_routes(
        application,
        authenticate=authenticate,
        gate=preflight_gate,
        signer=signer,
        witness_signer=witness_signer,
        evidence_log=evidence_log,
        provider=resolved_lens_provider,
        database_path=resolved_settings.database_path,
        test_delivery_worker=test_delivery_worker,
    )

    @application.get(
        "/v1/ai/status",
        response_model=AIStatusResponse,
        tags=["ai"],
    )
    async def ai_status() -> AIStatusResponse:
        is_vertex = resolved_lens_provider.mode == "VERTEX_AI"
        is_gemini_api = resolved_lens_provider.mode == "GEMINI_API"
        return AIStatusResponse(
            provider=resolved_lens_provider.provider_name,
            model=resolved_lens_provider.model_name,
            mode=resolved_lens_provider.mode,
            status=(
                "VERTEX_CONFIGURED"
                if is_vertex
                else "GEMINI_API_CONFIGURED"
                if is_gemini_api
                else "LOCAL_READY"
            ),
            cloud_project_configured=is_vertex,
            external_ai_configured=is_vertex or is_gemini_api,
            message=(
                "Gemini on Vertex AI is configured. Model calls remain advisory; deterministic policy decides."
                if is_vertex
                else "Gemini Developer API is configured through AI Studio. Model calls remain advisory; deterministic policy decides."
                if is_gemini_api
                else "Local no-cost rules are active. Configure the Gemini API or Vertex AI for live model reasoning."
            ),
        )

    @application.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def live() -> HealthResponse:
        return HealthResponse(status="ok", service="financial-friday-api", version=VERSION)

    @application.get("/health/ready", response_model=HealthResponse, tags=["health"])
    async def ready() -> HealthResponse:
        try:
            resolved_store.ping()
        except sqlite3.Error as error:
            raise HTTPException(status_code=503, detail="evidence store unavailable") from error
        return HealthResponse(status="ok", service="financial-friday-api", version=VERSION)

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

        model_input = redact_for_model(request.message_text)
        try:
            intent = await run_in_threadpool(
                resolved_lens_provider.extract_intent,
                model_input.text,
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
                    "input_redaction_applied": model_input.redaction_applied,
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

    @application.post(
        "/v1/cases/{case_id}/analyze",
        response_model=ProofOpsAnalysisResponse,
        tags=["proofops"],
    )
    async def analyze_case(
        case_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> ProofOpsAnalysisResponse:
        try:
            case = resolved_store.get_case(tenant.tenant_id, case_id)
            run = resolved_store.get_run(tenant.tenant_id, case["run_id"])
            contract = resolved_store.get_contract(
                tenant.tenant_id, case["contract_id"]
            )
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        context = build_minimised_incident_context(contract, run, case)
        analysis_provider = resolved_incident_provider
        try:
            hypothesis = await run_in_threadpool(
                analysis_provider.analyze, context
            )
        except Exception as error:
            if analysis_provider.mode == "LOCAL_RULES":
                raise HTTPException(
                    status_code=503,
                    detail="The configured incident-reasoning provider is unavailable.",
                ) from error
            # External model capacity must not make deterministic incident
            # verification unavailable.  The response identifies this honest
            # fallback as LOCAL_RULES rather than pretending Gemini answered.
            analysis_provider = LocalIncidentReasoningProvider()
            hypothesis = await run_in_threadpool(analysis_provider.analyze, context)

        search_result = search_minimal_repair(
            contract,
            run["evidence"],
            hypothesis.ranked_interventions,
        )
        repaired = search_result.counterfactual_verdict == "MATCH"
        analysis_payload = {
                "analysis_id": f"proofops_{uuid4().hex}",
                "case_id": case_id,
                "provider": analysis_provider.provider_name,
                "model": analysis_provider.model_name,
                "mode": analysis_provider.mode,
                "root_cause_summary": hypothesis.root_cause_summary,
                "suspected_component": hypothesis.suspected_component,
                "confidence": hypothesis.confidence,
                "evidence_codes": hypothesis.evidence_codes,
                "patch_strategy": hypothesis.patch_strategy,
                "regression_scenarios": [
                    scenario.model_dump() for scenario in hypothesis.regression_scenarios
                ],
                "counterfactual_search": search_result.as_dict(),
                "verification_status": (
                    "COUNTERFACTUAL_VERIFIED" if repaired else "NO_SAFE_REPAIR_FOUND"
                ),
                "release_authorized": False,
                "human_approval_required": True,
            }
        try:
            resolved_store.put_proofops_analysis(
                tenant.tenant_id, analysis_payload
            )
        except StorageConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return ProofOpsAnalysisResponse.model_validate(analysis_payload)

    @application.post(
        "/v1/cases/{case_id}/approve",
        response_model=ProofOpsApprovalResponse,
        tags=["proofops"],
    )
    async def decide_verified_repair(
        case_id: str,
        request: ProofOpsApprovalRequest,
        tenant: TenantContext = Depends(authenticate),
    ) -> ProofOpsApprovalResponse:
        try:
            case = resolved_store.get_case(tenant.tenant_id, case_id)
            analysis = resolved_store.get_proofops_analysis(
                tenant.tenant_id, request.analysis_id
            )
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        if analysis["case_id"] != case_id:
            raise HTTPException(
                status_code=422,
                detail="analysis does not belong to this evidence case",
            )
        if (
            request.decision == "APPROVE"
            and analysis["verification_status"] != "COUNTERFACTUAL_VERIFIED"
        ):
            raise HTTPException(
                status_code=409,
                detail="an unverified repair cannot be approved for release",
            )

        approval = {
            "approval_id": f"approval_{uuid4().hex[:24]}",
            "case_id": case_id,
            "analysis_id": request.analysis_id,
            "reviewer_id": request.reviewer_id,
            "candidate_reference": request.candidate_reference,
            "decision": request.decision,
            "rationale": request.rationale,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        passport = None
        if request.decision == "APPROVE":
            passport = build_release_passport(
                tenant_id=tenant.tenant_id,
                case=case,
                analysis=analysis,
                approval=approval,
                signing_key=resolved_settings.passport_signing_key(
                    tenant.tenant_id
                ),
            )
        try:
            resolved_store.put_approval(tenant.tenant_id, approval, passport)
        except StorageConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        response_passport = None
        if passport is not None:
            response_passport = {**passport, "signature_valid": True}
        return ProofOpsApprovalResponse.model_validate(
            {"approval": approval, "release_passport": response_passport}
        )

    @application.get(
        "/v1/release-passports/{passport_id}",
        response_model=ReleasePassportResponse,
        tags=["proofops"],
    )
    async def get_release_passport(
        passport_id: str,
        tenant: TenantContext = Depends(authenticate),
    ) -> ReleasePassportResponse:
        try:
            passport = resolved_store.get_release_passport(
                tenant.tenant_id, passport_id
            )
        except StorageNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        signature_valid = verify_release_passport(
            passport,
            resolved_settings.passport_signing_key(tenant.tenant_id),
        )
        return ReleasePassportResponse.model_validate(
            {**passport, "signature_valid": signature_valid}
        )

    return application
