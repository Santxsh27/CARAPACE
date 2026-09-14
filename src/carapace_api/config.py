"""Configuration with secure production defaults and explicit local settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


LOCAL_DEMO_KEY = "local-demo-key-change-me"


@dataclass(frozen=True)
class Settings:
    environment: str
    database_path: Path
    tenant_keys: Mapping[str, str]

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("CARAPACE_ENV", "development").strip().lower()
        database_path = Path(
            os.getenv("CARAPACE_DB_PATH", "/tmp/carapace/carapace.db")
        )
        raw_keys = os.getenv("CARAPACE_TENANT_KEYS_JSON")

        if raw_keys:
            parsed = json.loads(raw_keys)
            if not isinstance(parsed, dict) or not parsed:
                raise RuntimeError("CARAPACE_TENANT_KEYS_JSON must be a non-empty object")
            tenant_keys = {str(key): str(value) for key, value in parsed.items()}
        elif environment == "development":
            tenant_keys = {"demo-bank": LOCAL_DEMO_KEY}
        else:
            raise RuntimeError(
                "CARAPACE_TENANT_KEYS_JSON is required outside development"
            )

        if any(not tenant or not key for tenant, key in tenant_keys.items()):
            raise RuntimeError("tenant IDs and API keys must be non-empty")
        if environment != "development" and LOCAL_DEMO_KEY in tenant_keys.values():
            raise RuntimeError("the local demonstration API key is forbidden in production")

        return cls(
            environment=environment,
            database_path=database_path,
            tenant_keys=tenant_keys,
        )
