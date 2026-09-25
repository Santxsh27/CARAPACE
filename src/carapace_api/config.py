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
    passport_signing_keys: Mapping[str, str] | None = None
    ai_provider: str = "local"
    google_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3.5-flash-lite"
    bank_signing_key_path: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("CARAPACE_ENV", "development").strip().lower()
        database_path = Path(
            os.getenv("CARAPACE_DB_PATH", "/tmp/carapace/carapace.db")
        )
        raw_keys = os.getenv("CARAPACE_TENANT_KEYS_JSON")
        raw_passport_keys = os.getenv("CARAPACE_PASSPORT_KEYS_JSON")
        raw_bank_signing_key_path = os.getenv("CARAPACE_BANK_SIGNING_KEY_PATH")

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

        passport_signing_keys = None
        if raw_passport_keys:
            parsed_passport_keys = json.loads(raw_passport_keys)
            if not isinstance(parsed_passport_keys, dict) or not parsed_passport_keys:
                raise RuntimeError(
                    "CARAPACE_PASSPORT_KEYS_JSON must be a non-empty object"
                )
            passport_signing_keys = {
                str(key): str(value) for key, value in parsed_passport_keys.items()
            }
        elif environment not in {"development", "test"}:
            raise RuntimeError(
                "CARAPACE_PASSPORT_KEYS_JSON is required outside development"
            )
        if environment not in {"development", "test"} and not raw_bank_signing_key_path:
            raise RuntimeError(
                "CARAPACE_BANK_SIGNING_KEY_PATH must be explicitly provisioned outside development"
            )

        return cls(
            environment=environment,
            database_path=database_path,
            tenant_keys=tenant_keys,
            passport_signing_keys=passport_signing_keys,
            ai_provider=os.getenv("CARAPACE_AI_PROVIDER", "local").strip().lower(),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
            gemini_model=os.getenv("CARAPACE_GEMINI_MODEL", "gemini-3.5-flash-lite"),
            bank_signing_key_path=Path(raw_bank_signing_key_path) if raw_bank_signing_key_path else database_path.parent / "bank-dev-ed25519.pem",
        )

    def passport_signing_key(self, tenant_id: str) -> str:
        if self.passport_signing_keys is not None:
            key = self.passport_signing_keys.get(tenant_id)
            if key:
                return key
        if self.environment in {"development", "test"}:
            return self.tenant_keys[tenant_id]
        raise RuntimeError("release-passport signing key is unavailable")
