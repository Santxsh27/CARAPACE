"""Optional durable state for Financial Friday's non-payment records.

The artificial-money payment transaction intentionally remains in SQLite until
its complete idempotency/account update can move as one Firestore transaction.
This module never claims otherwise.
"""
from __future__ import annotations

from typing import Any, Protocol


KINDS = {"mandates", "accounts", "provider_bills", "signals", "dynamic_cases", "runs"}


class FridayDurableState(Protocol):
    mode: str

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None: ...
    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None: ...
    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]: ...


class LocalFridayState:
    mode = "SQLITE_LOCAL"

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None:
        del kind, tenant, record_id, value

    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None:
        del kind, tenant, record_id
        return None

    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]:
        del kind, tenant, limit
        return []


class FirestoreFridayState:
    """Tenant-scoped Firestore mirror and restart source for non-payment state."""

    mode = "FIRESTORE_HYBRID"

    def __init__(
        self,
        project: str,
        database: str = "(default)",
        collection: str = "financial_friday_v1",
        *,
        client=None,
    ) -> None:
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Firestore state")
        if not collection.replace("_", "").replace("-", "").isalnum():
            raise RuntimeError("CARAPACE_FIRESTORE_COLLECTION contains invalid characters")
        if client is None:
            try:
                from google.cloud import firestore
            except ImportError as error:
                raise RuntimeError("Install google-cloud-firestore for Firestore state") from error
            client = firestore.Client(project=project, database=database)
        self._client = client
        self._collection = collection

    @staticmethod
    def _validate(kind: str, tenant: str, record_id: str) -> None:
        if kind not in KINDS:
            raise ValueError("unsupported durable-state kind")
        if not tenant or "/" in tenant or not record_id or "/" in record_id:
            raise ValueError("invalid durable-state identity")

    def _documents(self, kind: str, tenant: str):
        return self._client.collection(self._collection).document(tenant).collection(kind)

    def put(self, kind: str, tenant: str, record_id: str, value: dict[str, Any]) -> None:
        self._validate(kind, tenant, record_id)
        self._documents(kind, tenant).document(record_id).set(value)

    def get(self, kind: str, tenant: str, record_id: str) -> dict[str, Any] | None:
        self._validate(kind, tenant, record_id)
        snapshot = self._documents(kind, tenant).document(record_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list(self, kind: str, tenant: str, limit: int = 20) -> list[dict[str, Any]]:
        self._validate(kind, tenant, "list")
        if not 1 <= limit <= 100:
            raise ValueError("durable-state list limit is invalid")
        return [snapshot.to_dict() for snapshot in self._documents(kind, tenant).limit(limit).stream()]


def create_friday_durable_state(settings) -> FridayDurableState:
    mode = settings.friday_durable_store
    if mode == "sqlite":
        return LocalFridayState()
    if mode == "firestore":
        return FirestoreFridayState(
            project=settings.google_cloud_project or "",
            database=settings.firestore_database,
            collection=settings.firestore_collection,
        )
    raise RuntimeError("CARAPACE_FRIDAY_DURABLE_STORE must be 'sqlite' or 'firestore'")
