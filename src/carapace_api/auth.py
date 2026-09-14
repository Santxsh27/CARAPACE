"""Small tenant authenticator used until managed identity is wired in."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, status

from .config import Settings


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str


class TenantAuthenticator:
    def __init__(self, settings: Settings) -> None:
        self._tenant_keys = dict(settings.tenant_keys)

    async def __call__(
        self,
        tenant_id: Annotated[str | None, Header(alias="X-Carapace-Tenant")] = None,
        api_key: Annotated[str | None, Header(alias="X-Carapace-API-Key")] = None,
    ) -> TenantContext:
        expected = self._tenant_keys.get(tenant_id or "")
        if expected is None or api_key is None or not hmac.compare_digest(expected, api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid CARAPACE credentials",
            )
        return TenantContext(tenant_id=tenant_id or "")
