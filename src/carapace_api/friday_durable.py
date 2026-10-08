"""Optional transactional Firestore state for Friday's artificial-money sandbox."""
from __future__ import annotations

from typing import Any, Protocol
from copy import deepcopy
from hashlib import sha256

from carapace_core.friday_live import FridayMandate, TestProviderBill, bill_increase_requires_review


KINDS = {"mandates", "accounts", "provider_bills", "signals", "dynamic_cases", "runs", "payments", "idempotency"}


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
    """Tenant-scoped authoritative state, including atomic artificial payments."""

    mode = "FIRESTORE_TRANSACTIONAL"

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

    def _atomic(self, callback):
        from google.cloud import firestore
        return firestore.transactional(callback)(self._client.transaction())

    def save_mandate(self, tenant: str, mandate: dict, now: str) -> None:
        self._validate("mandates", tenant, "current")
        account = self._documents("accounts", tenant).document("current")
        instruction = self._documents("mandates", tenant).document("current")

        def commit(transaction):
            existing = account.get(transaction=transaction)
            transaction.set(instruction, {"mandate": mandate, "updated_at": now})
            if not existing.exists:
                transaction.set(account, {"balance_minor": 5_000_000, "updated_at": now})
        self._atomic(commit)

    def execute_payment(self, tenant: str, result: dict, receipt: dict, live: dict | None,
                        signer) -> dict:
        """Commit an artificial payment, balance and run together; never real funds.

        The callback can be retried by Firestore. It has no model calls, external
        payment calls or mutations to the caller's result.
        """
        payload = receipt["payload"]
        self._validate("runs", tenant, result["run_id"])
        identity = ("bill:" + live["authoritative_bill"]["provider_id"] + ":" +
                    live["authoritative_bill"]["bill_reference"]) if live else "goal:" + payload["goal_id"]
        payment = self._documents("payments", tenant).document(sha256(identity.encode()).hexdigest())
        idem = self._documents("idempotency", tenant).document(sha256(payload["idempotency_key"].encode()).hexdigest())
        account = self._documents("accounts", tenant).document("current")
        mandate = self._documents("mandates", tenant).document("current")
        run = self._documents("runs", tenant).document(result["run_id"])
        bill = self._documents("provider_bills", tenant).document(live["authoritative_bill"]["bill_reference"]) if live else None

        def commit(transaction):
            prior = payment.get(transaction=transaction)
            prior_idem = idem.get(transaction=transaction)
            balance_record = account.get(transaction=transaction)
            mandate_record = mandate.get(transaction=transaction)
            bill_record = bill.get(transaction=transaction) if bill else None
            output = deepcopy(result)
            reason = []
            balance = None
            old = prior.to_dict().get("receipt") if prior.exists else None
            if old:
                bound = all(old["payload"].get(k) == payload[k] for k in
                            ("tenant_id", "provider_id", "payee_id", "amount_minor", "currency"))
                if not bound or not signer.verify(old["payload"], old["signature"]):
                    reason = ["EXISTING_RECEIPT_INVALID"]
                else:
                    output["status"] = "ALREADY_COMPLETED"
                    output["outcome"] = {"money_moved": False, "new_payment_created": False, "receipt": old}
            elif prior_idem.exists:
                reason = ["IDEMPOTENCY_CONFLICT"]
            elif live:
                if not bill_record.exists or bill_record.to_dict() != live["authoritative_bill"]:
                    reason = ["PROVIDER_CHANGED"]
                elif not mandate_record.exists or not balance_record.exists:
                    reason = ["MANDATE_OR_ACCOUNT_MISSING"]
                else:
                    rules = mandate_record.to_dict()["mandate"]
                    balance = balance_record.to_dict()["balance_minor"] - payload["amount_minor"]
                    if rules["instruction"] != result["goal"]["instruction"] or rules["max_fee_minor"] < result["goal"]["max_fee_minor"]:
                        reason = ["MANDATE_CHANGED"]
                    elif output.get("automatic") and (not rules["automatic_sandbox_execution"] or payload["amount_minor"] > rules["automatic_payment_limit_minor"]):
                        reason = ["AUTOMATIC_PERMISSION_CHANGED"]
                    elif bill_increase_requires_review(
                        TestProviderBill.model_validate(live["authoritative_bill"]),
                        FridayMandate.model_validate(rules).bill_increase_review_percent,
                    ):
                        reason = ["UNUSUAL_BILL_INCREASE"]
                    elif balance < rules["protected_balance_minor"]:
                        reason = ["PROTECTED_BALANCE"]
            if reason:
                output["status"] = "HELD"
                output["outcome"] = {"money_moved": False, "new_payment_created": False, "reason": reason}
            elif not old:
                output["status"] = "COMPLETED_SYNTHETIC"
                output["outcome"] = {"money_moved": True, "new_payment_created": True,
                                     "receipt": receipt, "sandbox_balance_minor": balance}
                transaction.set(payment, {"receipt": receipt})
                transaction.set(idem, {"payment_id": payment.id})
                if balance is not None:
                    transaction.set(account, {"balance_minor": balance})
            output["events"].append({"type": "RESTRICTED_EXECUTOR_RESULT", "status": output["status"],
                                     "new_payment": output["outcome"]["new_payment_created"]})
            transaction.set(run, {"result": output})
            return output
        return self._atomic(commit)

    def payment_receipt(self, tenant: str, goal_id: str, live: dict | None) -> dict | None:
        self._validate("payments", tenant, "lookup")
        identity = ("bill:" + live["authoritative_bill"]["provider_id"] + ":" +
                    live["authoritative_bill"]["bill_reference"]) if live else "goal:" + goal_id
        record = self.get("payments", tenant, sha256(identity.encode()).hexdigest())
        return record.get("receipt", {}) if record is not None else None


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
