"""Financial Friday demo API: bounded AI planning and artificial-money execution."""
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_core.friday_live import FridayMandate, IncomingFinancialSignal, TestProviderBill
from carapace_integrations.financial_friday_fixtures import CASES
from .auth import TenantContext
from .friday_inbox import FridayInbox
from .financial_friday import FridayUnderstandingUnavailable


class WatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class FridayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Literal["configured", "local"] = "configured"


DOCUMENT_TYPES = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024


def _valid_document_signature(mime_type: str, data: bytes) -> bool:
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    return False


async def _read_bounded_document(request: Request) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "document exceeds the 8 MB limit")
        chunks.append(chunk)
    if not chunks:
        raise HTTPException(422, "document is empty")
    return b"".join(chunks)


def register_financial_friday_routes(application, service, authenticate):
    inbox = FridayInbox(service)
    application.state.friday_inbox = inbox

    @application.get("/v1/friday/inbox", tags=["financial-friday"])
    def inbox_read(tenant: TenantContext = Depends(authenticate)):
        return inbox.read(tenant.tenant_id)

    @application.post("/v1/friday/inbox/{event_id}/retry", tags=["financial-friday"])
    def retry(event_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return inbox.retry(tenant.tenant_id, event_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.post("/v1/friday/watch", tags=["financial-friday"])
    def watch(request: WatchRequest, tenant: TenantContext = Depends(authenticate)):
        return inbox.watch(tenant.tenant_id, request.enabled)

    @application.post("/v1/friday/arrivals/{case_id}", tags=["financial-friday"])
    def arrive(case_id: str, tenant: TenantContext = Depends(authenticate)):
        if case_id not in CASES:
            raise HTTPException(404, "scenario not found")
        return inbox.arrive(tenant.tenant_id, case_id)

    @application.get("/v1/friday/today", tags=["financial-friday"])
    def today(tenant: TenantContext = Depends(authenticate)):
        return service.daily_brief(tenant.tenant_id)

    @application.get("/v1/friday/workspace", tags=["financial-friday"])
    def workspace(tenant: TenantContext = Depends(authenticate)):
        from .friday_workspace import financial_workspace
        return financial_workspace(service, tenant.tenant_id)

    @application.get("/v1/friday/storage-status", tags=["financial-friday"])
    def storage_status(tenant: TenantContext = Depends(authenticate)):
        del tenant
        return service.storage_status()

    @application.get("/v1/friday/mandate", tags=["financial-friday"])
    def read_mandate(tenant: TenantContext = Depends(authenticate)):
        return service.mandate(tenant.tenant_id)

    @application.put("/v1/friday/mandate", tags=["financial-friday"])
    def save_mandate(request: FridayMandate, tenant: TenantContext = Depends(authenticate)):
        return service.save_mandate(tenant.tenant_id, request)

    @application.post("/v1/friday/test-provider/bills", tags=["financial-friday"])
    def publish_test_bill(request: TestProviderBill, tenant: TenantContext = Depends(authenticate)):
        return service.publish_test_bill(tenant.tenant_id, request)

    @application.get("/v1/friday/test-provider/bills", tags=["financial-friday"])
    def household_bills(tenant: TenantContext = Depends(authenticate)):
        return service.household_bills(tenant.tenant_id)

    @application.get("/v1/friday/live-input", tags=["financial-friday"])
    def live_inputs(tenant: TenantContext = Depends(authenticate)):
        return service.live_signals(tenant.tenant_id)

    @application.post("/v1/friday/live-input", tags=["financial-friday"])
    async def ingest_live_input(
        request: IncomingFinancialSignal, tenant: TenantContext = Depends(authenticate)
    ):
        try:
            return await run_in_threadpool(service.ingest_live_signal, tenant.tenant_id, request)
        except FridayUnderstandingUnavailable as error:
            raise HTTPException(503, "Financial understanding is unavailable; no payment was submitted", headers={"Retry-After": "10"}) from error

    @application.post("/v1/friday/documents", tags=["financial-friday"])
    async def ingest_document(
        request: Request,
        filename: str = Query(min_length=1, max_length=160),
        tenant: TenantContext = Depends(authenticate),
    ):
        mime_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime_type not in DOCUMENT_TYPES:
            raise HTTPException(415, "use a PNG, JPEG, WebP or PDF document")
        data = await _read_bounded_document(request)
        if not _valid_document_signature(mime_type, data):
            raise HTTPException(422, "file signature does not match its declared document type")
        safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
        if not safe_name:
            raise HTTPException(422, "filename is invalid")
        try:
            return await run_in_threadpool(
                service.ingest_document, tenant.tenant_id, safe_name, mime_type, data
            )
        except FridayUnderstandingUnavailable as error:
            raise HTTPException(503, "document understanding is unavailable; no action was taken") from error
        except Exception as error:
            raise HTTPException(503, "document outcome is unavailable; check activity before retrying") from error

    @application.post("/v1/friday/live-input/{event_id}/run", tags=["financial-friday"])
    async def run_live_input(event_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return await run_in_threadpool(service.run_live_signal, tenant.tenant_id, event_id)
        except KeyError as error:
            raise HTTPException(404, "live input not found") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @application.get("/v1/friday/scenarios", tags=["financial-friday"])
    def scenarios(tenant: TenantContext = Depends(authenticate)):
        return {
            "product": "Financial Friday",
            "promise": "Delegate the goal. AI plans. The safety kernel proves. The executor acts once.",
            "scenarios": [
                {"id": key, "name": value[0], "description": value[1]}
                for key, value in CASES.items()
            ],
            "configured_mode": service.planner.mode,
            "model": service.planner.model_name,
            "storage": service.storage_status(),
            "scope": "Authorized fixtures and artificial money only",
        }

    @application.post("/v1/friday/scenarios/{case_id}/run", tags=["financial-friday"])
    async def run(case_id: str, request: FridayRunRequest, tenant: TenantContext = Depends(authenticate)):
        if case_id not in CASES:
            raise HTTPException(404, "scenario not found")
        planner = LocalFinancialFridayPlanner() if request.planner == "local" else None
        return await run_in_threadpool(service.run, tenant.tenant_id, case_id, planner)

    @application.get("/v1/friday/runs/{run_id}", tags=["financial-friday"])
    def get_run(run_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return service.get(tenant.tenant_id, run_id)
        except KeyError as error:
            raise HTTPException(404, "run not found") from error
