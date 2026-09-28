"""Tenant-isolated operations workbench; development fixtures only."""
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from carapace_ai.operations import LocalOperationsPlanner
from carapace_integrations.operations_fixtures import CASES
from .auth import TenantContext


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Literal["configured", "local"] = "configured"


def register_operations_routes(application, service, authenticate):
    @application.get("/v1/operations/cases", tags=["operations"])
    def cases(tenant: TenantContext = Depends(authenticate)):
        return {"cases": [{"id": key, "name": value[0], "description": value[1]} for key, value in CASES.items()],
                "configured_mode": service.planner.mode, "model": service.planner.model_name,
                "scope": "Synthetic connector snapshots and artificial money"}

    @application.post("/v1/operations/cases/{case_id}/resolve", tags=["operations"])
    async def resolve(case_id: str, request: ResolveRequest, tenant: TenantContext = Depends(authenticate)):
        if case_id not in CASES:
            raise HTTPException(404, "case not found")
        planner = LocalOperationsPlanner() if request.planner == "local" else None
        return await run_in_threadpool(service.resolve, tenant.tenant_id, case_id, planner)

    @application.get("/v1/operations/runs/{run_id}", tags=["operations"])
    def get_run(run_id: str, tenant: TenantContext = Depends(authenticate)):
        try:
            return service.get(tenant.tenant_id, run_id)
        except KeyError as error:
            raise HTTPException(404, "run not found") from error
