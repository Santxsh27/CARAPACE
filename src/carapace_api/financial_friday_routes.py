"""Financial Friday demo API: bounded AI planning and artificial-money execution."""
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_integrations.financial_friday_fixtures import CASES
from .auth import TenantContext
from .friday_inbox import FridayInbox


class WatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class FridayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Literal["configured", "local"] = "configured"


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
