"""Durable orchestrator and restricted artificial-money executor."""
from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from carapace_core.canonical import sha256_hex
from carapace_core.financial_friday import (
    FinancialEvidence,
    FinancialGoal,
    challenge_financial_program,
    verify_evidence_identity,
    verify_financial_program,
)
from carapace_core.friday_live import (
    FridayMandate,
    IncomingFinancialSignal,
    InterpretedFinancialSignal,
    TestProviderBill,
)
from carapace_integrations.financial_friday_fixtures import load_case
from .friday_durable import LocalFridayState


class FridayUnderstandingUnavailable(RuntimeError):
    """Understanding failed before any financial execution was submitted."""


class FinancialFridayService:
    def __init__(self, database_path: Path, signer, planner, durable_state=None):
        self.path, self.signer, self.planner = database_path, signer, planner
        self.durable = durable_state or LocalFridayState()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS friday_runs (
                    tenant_id TEXT NOT NULL, run_id TEXT NOT NULL,
                    result_json TEXT NOT NULL, PRIMARY KEY (tenant_id, run_id));
                CREATE TABLE IF NOT EXISTS friday_payments (
                    tenant_id TEXT NOT NULL, goal_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL, receipt_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, goal_id),
                    UNIQUE (tenant_id, idempotency_key));
                CREATE TABLE IF NOT EXISTS friday_mandates (
                    tenant_id TEXT PRIMARY KEY, mandate_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS friday_accounts (
                    tenant_id TEXT PRIMARY KEY, balance_minor INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS friday_provider_bills (
                    tenant_id TEXT NOT NULL, bill_reference TEXT NOT NULL,
                    bill_json TEXT NOT NULL, PRIMARY KEY (tenant_id, bill_reference));
                CREATE TABLE IF NOT EXISTS friday_live_signals (
                    tenant_id TEXT NOT NULL, event_id TEXT NOT NULL,
                    signal_json TEXT NOT NULL, interpretation_json TEXT NOT NULL,
                    case_id TEXT, state TEXT NOT NULL, result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, PRIMARY KEY (tenant_id, event_id));
                CREATE TABLE IF NOT EXISTS friday_dynamic_cases (
                    tenant_id TEXT NOT NULL, case_id TEXT NOT NULL,
                    case_json TEXT NOT NULL, PRIMARY KEY (tenant_id, case_id));
            """)

    def storage_status(self) -> dict:
        return {
            "mode": self.durable.mode,
            "durable_non_payment_state": self.durable.mode.startswith("FIRESTORE_"),
            "payment_transaction": "FIRESTORE_ARTIFICIAL_MONEY" if self.durable.mode == "FIRESTORE_TRANSACTIONAL" else "SQLITE_ARTIFICIAL_MONEY",
            "claim": (
                "Firestore mirrors and restores mandates, provider bills, signals, cases and run evidence. "
                "Artificial-money payment execution is disabled until idempotency and balance updates "
                "share one durable transaction."
                if self.durable.mode == "FIRESTORE_HYBRID"
                else "Firestore atomically records artificial payments, idempotency, balances and run outcomes. No real funds are connected."
                if self.durable.mode == "FIRESTORE_TRANSACTIONAL"
                else "All Friday state is local to this development instance."
            ),
        }

    @staticmethod
    def _default_mandate() -> FridayMandate:
        return FridayMandate(
            instruction="Track my verified household bills, protect ₹10,000, and never create subscriptions.",
            protected_balance_minor=1_000_000,
            automatic_payment_limit_minor=500_000,
            max_fee_minor=0,
            automatic_sandbox_execution=False,
        )

    def mandate(self, tenant: str) -> dict:
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            record = self.durable.get("mandates", tenant, "current")
            account = self.durable.get("accounts", tenant, "current")
            return {"mandate": record["mandate"] if record else self._default_mandate().model_dump(),
                    "sandbox_balance_minor": account["balance_minor"] if account else 5_000_000,
                    "scope": "Artificial-money account and enrolled test providers only",
                    "storage": self.storage_status()}
        with self.connect() as db:
            row = db.execute(
                "SELECT mandate_json FROM friday_mandates WHERE tenant_id=?", (tenant,)
            ).fetchone()
            account = db.execute(
                "SELECT balance_minor FROM friday_accounts WHERE tenant_id=?", (tenant,)
            ).fetchone()
        durable_mandate = self.durable.get("mandates", tenant, "current") if row is None else None
        durable_account = self.durable.get("accounts", tenant, "current") if account is None else None
        mandate = (
            FridayMandate.model_validate_json(row[0])
            if row
            else FridayMandate.model_validate(durable_mandate["mandate"])
            if durable_mandate
            else self._default_mandate()
        )
        return {
            "mandate": mandate.model_dump(),
            "sandbox_balance_minor": account[0] if account else durable_account["balance_minor"] if durable_account else 5_000_000,
            "scope": "Artificial-money account and enrolled test providers only",
            "storage": self.storage_status(),
        }

    def save_mandate(self, tenant: str, mandate: FridayMandate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            self.durable.save_mandate(tenant, mandate.model_dump(), now)
            return self.mandate(tenant)
        with self.connect() as db:
            db.execute(
                "INSERT INTO friday_mandates VALUES (?,?,?) ON CONFLICT(tenant_id) "
                "DO UPDATE SET mandate_json=excluded.mandate_json, updated_at=excluded.updated_at",
                (tenant, mandate.model_dump_json(), now),
            )
            db.execute(
                "INSERT OR IGNORE INTO friday_accounts VALUES (?,?)", (tenant, 5_000_000)
            )
        current = self.mandate(tenant)
        self.durable.put("mandates", tenant, "current", {
            "mandate": mandate.model_dump(), "updated_at": now
        })
        self.durable.put("accounts", tenant, "current", {
            "balance_minor": current["sandbox_balance_minor"], "updated_at": now
        })
        return current

    def publish_test_bill(self, tenant: str, bill: TestProviderBill) -> dict:
        with self.connect() as db:
            db.execute(
                "INSERT INTO friday_provider_bills VALUES (?,?,?) ON CONFLICT(tenant_id,bill_reference) "
                "DO UPDATE SET bill_json=excluded.bill_json",
                (tenant, bill.bill_reference, bill.model_dump_json()),
            )
        self.durable.put("provider_bills", tenant, bill.bill_reference, bill.model_dump())
        return {"published": True, "bill": bill.model_dump(), "scope": "ENROLLED_TEST_PROVIDER"}

    def _load_case(self, tenant: str, case_id: str) -> dict:
        if case_id.startswith("live-"):
            if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
                record = self.durable.get("dynamic_cases", tenant, case_id)
                if record is None:
                    raise KeyError(case_id)
                return record["case"]
            with self.connect() as db:
                row = db.execute(
                    "SELECT case_json FROM friday_dynamic_cases WHERE tenant_id=? AND case_id=?",
                    (tenant, case_id),
                ).fetchone()
            if row is None:
                durable_case = self.durable.get("dynamic_cases", tenant, case_id)
                if durable_case is None:
                    raise KeyError(case_id)
                return durable_case["case"]
            return json.loads(row[0])
        return load_case(case_id)

    def ingest_live_signal(self, tenant: str, signal: IncomingFinancialSignal) -> dict:
        """Interpret a novel input, ground it in the test provider, and optionally execute."""
        interpretation, attempts = self._understand(
            self.planner.interpret_signal, signal.source_type, signal.content_text)
        return self._ingest_interpreted_signal(tenant, signal, interpretation, source_metadata={
            "understanding": {"mode": self.planner.mode, "model": self.planner.model_name,
                              "attempts": attempts, "successful_model_calls": int(self.planner.mode != "LOCAL_RULES")}})

    @staticmethod
    def _understand(call, *args):
        # Read-only model requests may retry; financial execution must not.
        for attempt in range(2):
            try:
                return call(*args), attempt + 1
            except Exception as error:
                transient = getattr(error, "code", None) in {500, 502, 503, 504}
                if not transient or attempt == 1:
                    raise FridayUnderstandingUnavailable("Financial understanding is unavailable") from error
        raise AssertionError("unreachable")

    def ingest_document(
        self, tenant: str, filename: str, mime_type: str, document_bytes: bytes
    ) -> dict:
        """Interpret an ephemeral document; persist its digest and evidence, never its raw bytes."""
        digest = hashlib.sha256(document_bytes).hexdigest()
        interpretation, attempts = self._understand(
            self.planner.interpret_document, mime_type, document_bytes, filename)
        signal = IncomingFinancialSignal(
            source_type="DOCUMENT",
            content_text=f"Uploaded document: {filename} ({mime_type})",
            event_id="doc-" + digest[:24],
        )
        metadata = {
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(document_bytes),
            "sha256": digest,
            "raw_file_stored": False,
        }
        return self._ingest_interpreted_signal(
            tenant,
            signal,
            interpretation,
            source_evidence_id="document-sha256:" + digest,
            source_metadata={"document": metadata, "understanding": {
                "mode": self.planner.mode, "model": self.planner.model_name,
                "attempts": attempts, "successful_model_calls": int(self.planner.mode != "LOCAL_RULES")}},
        )

    def _ingest_interpreted_signal(
        self,
        tenant: str,
        signal: IncomingFinancialSignal,
        interpretation: InterpretedFinancialSignal,
        *,
        source_evidence_id: str | None = None,
        source_metadata: dict | None = None,
    ) -> dict:
        event_id = signal.event_id or "evt-" + sha256_hex({
            "tenant": tenant, "source": signal.source_type, "content": signal.content_text
        })[:24]
        durable_existing = self.durable.get("signals", tenant, event_id)
        if durable_existing is not None:
            return durable_existing["result"]
        now = datetime.now(timezone.utc).isoformat()
        result = {
            "event_id": event_id,
            "state": "ATTENTION",
            "interpretation": interpretation.model_dump(),
            "message": "Friday needs an enrolled provider record before it can act.",
            "money_moved": False,
            **(source_metadata or {}),
        }
        bill = None
        if interpretation.bill_reference:
            with self.connect() as db:
                row = db.execute(
                    "SELECT bill_json FROM friday_provider_bills WHERE tenant_id=? AND bill_reference=?",
                    (tenant, interpretation.bill_reference),
                ).fetchone()
            if row and self.durable.mode != "FIRESTORE_TRANSACTIONAL":
                bill = TestProviderBill.model_validate_json(row[0])
            else:
                durable_bill = self.durable.get(
                    "provider_bills", tenant, interpretation.bill_reference
                )
                bill = TestProviderBill.model_validate(durable_bill) if durable_bill else None

        case_id = None
        if bill is not None:
            mandate_data = self.mandate(tenant)
            mandate = FridayMandate.model_validate(mandate_data["mandate"])
            case_id = "live-" + sha256_hex({"tenant": tenant, "event": event_id, "bill": bill.model_dump()})[:24]
            claimed_payee = interpretation.claimed_payee_id or bill.payee_id
            amount = interpretation.amount_minor or bill.amount_minor
            case = {
                "goal": {
                    "goal_id": "goal-bill-" + sha256_hex({"tenant": tenant, "provider": bill.provider_id, "bill": bill.bill_reference})[:24],
                    "instruction": mandate.instruction,
                    "provider_id": bill.provider_id,
                    "payee_id": bill.payee_id,
                    "currency": bill.currency,
                    "max_total_minor": bill.amount_minor,
                    "max_fee_minor": mandate.max_fee_minor,
                    "cadence": "ONE_TIME",
                    "allowed_data_fields": ["BILL_REFERENCE"],
                    "idempotency_key": "idem-bill-" + sha256_hex({"tenant": tenant, "provider": bill.provider_id, "bill": bill.bill_reference})[:24],
                },
                "evidence": {
                    "obligation_id": bill.bill_reference,
                    "provider_id": bill.provider_id,
                    "payee_id": claimed_payee,
                    "currency": bill.currency,
                    "principal_minor": amount,
                    "fee_minor": 0,
                    "provider_verified": True,
                    "highlighted_option_id": "provider-one-time",
                    "available_options": [{
                        "option_id": "provider-one-time",
                        "label": "Enrolled test provider bill",
                        "principal_minor": amount,
                        "fee_minor": 0,
                        "cadence": "RECURRING" if interpretation.recurring_requested else "ONE_TIME",
                        "authenticated": amount == bill.amount_minor,
                    }],
                    "requested_cadence": "RECURRING" if interpretation.recurring_requested else "ONE_TIME",
                    "requested_data_fields": ["BILL_REFERENCE"],
                    "prior_outcome": "NONE",
                    "reconciliation_result": "NOT_APPLICABLE",
                    "evidence_ids": [
                        source_evidence_id or "live-signal:" + event_id,
                        "test-provider:" + bill.bill_reference,
                    ],
                },
                "live": {"event_id": event_id, "authoritative_bill": bill.model_dump()},
            }
            mismatch = []
            if signal.source_type == "DOCUMENT":
                quoted_fields = {span.field for span in interpretation.evidence_spans}
                required_fields = {"bill_reference", "amount_minor", "claimed_payee_id"}
                if not required_fields.issubset(quoted_fields):
                    mismatch.append("DOCUMENT_EVIDENCE_INCOMPLETE")
            if interpretation.amount_minor is not None and interpretation.amount_minor != bill.amount_minor:
                mismatch.append("AMOUNT_MISMATCH")
            if interpretation.claimed_payee_id and interpretation.claimed_payee_id != bill.payee_id:
                mismatch.append("RECIPIENT_MISMATCH")
            if interpretation.suspicious_instructions:
                mismatch.append("EMBEDDED_INSTRUCTION")
            if interpretation.recurring_requested:
                mismatch.append("RECURRING_REQUEST")
            with self.connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO friday_dynamic_cases VALUES (?,?,?)",
                    (tenant, case_id, json.dumps(case)),
                )
            self.durable.put("dynamic_cases", tenant, case_id, {"case": case})
            balance = mandate_data["sandbox_balance_minor"]
            affordable = balance - bill.amount_minor >= mandate.protected_balance_minor
            within_limit = bill.amount_minor <= mandate.automatic_payment_limit_minor
            if mismatch:
                result.update(state="ATTENTION", message="Friday found a contradiction and stopped before payment.", reason=mismatch)
            elif not affordable:
                result.update(state="ATTENTION", message="Friday protected your reserved balance.", reason=["PROTECTED_BALANCE"])
            elif not within_limit:
                result.update(state="READY", message="Verified bill exceeds the automatic limit and needs approval.", reason=["ABOVE_AUTOMATIC_LIMIT"])
            else:
                result.update(state="READY", message="Bill matched the enrolled provider and is ready.", reason=[])
                if mandate.automatic_sandbox_execution:
                    run = self.run(tenant, case_id, automatic=True)
                    result.update(
                        state="COMPLETED" if run["status"] in {"COMPLETED_SYNTHETIC", "ALREADY_COMPLETED"} else "ATTENTION",
                        message="Friday completed the verified test bill automatically." if run["status"] == "COMPLETED_SYNTHETIC" else "Friday finished with a protected outcome.",
                        run_id=run["run_id"], money_moved=run["outcome"].get("money_moved", False),
                    )

        with self.connect() as db:
            existing = db.execute(
                "SELECT result_json FROM friday_live_signals WHERE tenant_id=? AND event_id=?",
                (tenant, event_id),
            ).fetchone()
            if existing:
                return json.loads(existing[0])
            db.execute(
                "INSERT INTO friday_live_signals VALUES (?,?,?,?,?,?,?,?)",
                (tenant, event_id, signal.model_dump_json(), interpretation.model_dump_json(),
                 case_id, result["state"], json.dumps(result), now),
            )
        self.durable.put("signals", tenant, event_id, {
            "event_id": event_id,
            "case_id": case_id,
            "signal": signal.model_dump(),
            "interpretation": interpretation.model_dump(),
            "state": result["state"],
            "result": result,
            "created_at": now,
        })
        return result

    def live_signals(self, tenant: str) -> dict:
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            return {"items": [r["result"] for r in self.durable.list("signals", tenant, 20)], "storage": self.storage_status()}
        with self.connect() as db:
            rows = db.execute(
                "SELECT result_json FROM friday_live_signals WHERE tenant_id=? ORDER BY rowid DESC LIMIT 20",
                (tenant,),
            ).fetchall()
        items = [json.loads(row[0]) for row in rows]
        if not items:
            items = [record["result"] for record in self.durable.list("signals", tenant, 20)]
        return {"items": items, "storage": self.storage_status()}

    def run_live_signal(self, tenant: str, event_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT case_id,result_json FROM friday_live_signals WHERE tenant_id=? AND event_id=?",
                (tenant, event_id),
            ).fetchone()
        if row is None:
            durable_signal = self.durable.get("signals", tenant, event_id)
            if durable_signal is None or not durable_signal.get("case_id"):
                raise KeyError(event_id)
            if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
                case_id, existing = durable_signal["case_id"], durable_signal["result"]
            else:
                raise ValueError(
                    "This signal was restored from Firestore for review, but payment execution stays disabled "
                    "until payment idempotency moves into the same durable transaction."
                )
        else:
            if not row[0]:
                raise KeyError(event_id)
            case_id, existing = row[0], json.loads(row[1])
        if existing.get("reason") and existing["reason"] != ["ABOVE_AUTOMATIC_LIMIT"]:
            raise ValueError("This input has unresolved contradictions and cannot execute.")
        run = self.run(tenant, case_id)
        updated = dict(existing, state="COMPLETED" if run["status"] != "HELD" else "ATTENTION",
                       run_id=run["run_id"], money_moved=run["outcome"].get("money_moved", False),
                       message="Friday completed the verified test bill." if run["status"] != "HELD" else "The safety kernel held this task.")
        with self.connect() as db:
            db.execute(
                "UPDATE friday_live_signals SET state=?,result_json=? WHERE tenant_id=? AND event_id=?",
                (updated["state"], json.dumps(updated), tenant, event_id),
            )
        durable_signal = self.durable.get("signals", tenant, event_id) or {
            "event_id": event_id, "case_id": case_id
        }
        durable_signal.update(state=updated["state"], result=updated)
        self.durable.put("signals", tenant, event_id, durable_signal)
        return {"signal": updated, "run": run}

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _save(self, tenant: str, result: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO friday_runs VALUES (?,?,?) ON CONFLICT(tenant_id,run_id) "
                "DO UPDATE SET result_json=excluded.result_json",
                (tenant, result["run_id"], json.dumps(result)),
            )
        self.durable.put("runs", tenant, result["run_id"], {"result": result})

    def get(self, tenant: str, run_id: str) -> dict:
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            record = self.durable.get("runs", tenant, run_id)
            if record is None:
                raise KeyError(run_id)
            return record["result"]
        with self.connect() as db:
            row = db.execute(
                "SELECT result_json FROM friday_runs WHERE tenant_id=? AND run_id=?",
                (tenant, run_id),
            ).fetchone()
        if row is None:
            durable_run = self.durable.get("runs", tenant, run_id)
            if durable_run is None:
                raise KeyError(run_id)
            return durable_run["result"]
        return json.loads(row[0])

    def daily_brief(self, tenant: str) -> dict:
        """Read the actual sandbox journal; never infer an account balance."""
        goal = load_case("genuine-bill")["goal"]
        with self.connect() as db:
            payments = db.execute(
                "SELECT receipt_json FROM friday_payments WHERE tenant_id=?", (tenant,)
            ).fetchall()
            rows = db.execute(
                "SELECT result_json FROM friday_runs WHERE tenant_id=? ORDER BY rowid DESC LIMIT 10",
                (tenant,),
            ).fetchall()
            live_rows = db.execute(
                "SELECT result_json FROM friday_live_signals WHERE tenant_id=? ORDER BY rowid DESC LIMIT 5",
                (tenant,),
            ).fetchall()
        receipts = []
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            payments = [(json.dumps(r["receipt"]),) for r in self.durable.list("payments", tenant, 100)]
            rows = [(json.dumps(r["result"]),) for r in self.durable.list("runs", tenant, 10)]
            live_rows = [(json.dumps(r["result"]),) for r in self.durable.list("signals", tenant, 5)]
        invalid = 0
        for row in payments:
            try:
                receipt = json.loads(row[0])
                if not self.signer.verify(receipt["payload"], receipt["signature"]):
                    invalid += 1
                    continue
                receipts.append(receipt)
            except (ValueError, KeyError, TypeError):
                invalid += 1
        paid = any(r["payload"]["goal_id"] == goal["goal_id"] for r in receipts)
        return {
            "scope": "Artificial-money sandbox journal only; no real account connected",
            "bill": {"label": "Sample electricity bill", "amount_minor": 199900,
                     "status": "UNVERIFIED" if invalid else "PAID" if paid else "READY",
                     "scenario_id": "genuine-bill"},
            "recorded_total_minor": sum(r["payload"]["amount_minor"] for r in receipts),
            "verified_receipt_count": len(receipts), "invalid_receipt_count": invalid,
            "recent_runs": [{"run_id": r["run_id"], "case_id": r["case_id"],
                             "status": r["status"], "started_at": r["started_at"]}
                            for r in (json.loads(row[0]) for row in rows)],
            "balance": None,
            "live_activity": [json.loads(row[0]) for row in live_rows],
        }

    def run(self, tenant: str, case_id: str, planner=None, *, automatic=False) -> dict:
        case = self._load_case(tenant, case_id)
        goal = FinancialGoal.model_validate(case["goal"])
        evidence = FinancialEvidence.model_validate(case["evidence"])
        planner = planner or self.planner
        result = {
            "run_id": "ff_" + uuid4().hex,
            "case_id": case_id,
            "automatic": automatic,
            "status": "PLANNING",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "goal": goal.model_dump(),
            "events": [],
            "provenance": {
                "mode": planner.mode,
                "model": planner.model_name,
                "successful_model_calls": 0,
            },
            "scope": "Financial Friday sandbox provider and artificial money; no real bank access.",
        }
        self._save(tenant, result)
        identity_errors = verify_evidence_identity(goal, evidence)
        if identity_errors:
            result["events"].append({
                "type": "DETERMINISTIC_EVIDENCE_HOLD",
                "errors": identity_errors,
                "authority": "SAFETY_KERNEL",
            })
            result["status"] = "HELD"
            result["outcome"] = {"money_moved": False, "reason": identity_errors}
            self._save(tenant, result)
            return result

        existing = self._existing_receipt(tenant, goal, case.get("live"))
        if existing is not None:
            payload = existing.get("payload", {}) if isinstance(existing, dict) else {}
            valid_totals = {option.principal_minor + option.fee_minor for option in evidence.available_options
                            if option.authenticated and option.cadence == "ONE_TIME" and option.fee_minor <= goal.max_fee_minor}
            intact = isinstance(existing, dict) and isinstance(payload, dict) and all(
                payload.get(field) == expected for field, expected in {
                    "tenant_id": tenant, "provider_id": goal.provider_id, "payee_id": goal.payee_id,
                    "currency": goal.currency, "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY"}.items()) and payload.get("amount_minor") in valid_totals
            intact = intact and isinstance(existing.get("signature"), str)
            intact = intact and payload["amount_minor"] <= goal.max_total_minor and self.signer.verify(payload, existing.get("signature", ""))
            result["status"] = "ALREADY_COMPLETED" if intact else "HELD"
            result["outcome"] = {"money_moved": False, "new_payment_created": False,
                                 "receipt": existing if intact else None}
            if not intact:
                result["outcome"]["reason"] = ["EXISTING_RECEIPT_INVALID"]
            result["events"].append({"type": "EXISTING_PAYMENT_RECONCILED", "receipt_verified": bool(intact),
                                     "authority": "SAFETY_KERNEL", "new_payment": False})
            self._save(tenant, result)
            return result

        context = {"goal": goal.model_dump(), "evidence": evidence.model_dump()}
        program = None
        verification = None
        for attempt in range(3):
            try:
                program = planner.plan(context)
                if planner.mode != "LOCAL_RULES":
                    result["provenance"]["successful_model_calls"] += 1
                verification = verify_financial_program(program, goal, evidence)
                result["events"].append({
                    "type": "AI_PROGRAM_PROPOSED",
                    "attempt": attempt + 1,
                    "program": program.model_dump(),
                    "verification": verification,
                    "authority": "PROPOSAL_ONLY",
                })
                if verification["passed"]:
                    break
                context["validation_feedback"] = verification["errors"]
                self._save(tenant, result)
            except ValidationError as error:
                context["validation_feedback"] = sorted({
                    "OUTPUT_SCHEMA_INVALID:" + issue["type"]
                    for issue in error.errors(include_input=False)
                })[:8]
                result["events"].append({
                    "type": "AI_PROGRAM_REJECTED",
                    "attempt": attempt + 1,
                    "errors": context["validation_feedback"],
                })
            except Exception as error:
                if type(error).__name__ == "ServerError" and attempt < 2:
                    result["events"].append({
                        "type": "AI_PROVIDER_RETRY",
                        "attempt": attempt + 1,
                        "error_type": type(error).__name__,
                    })
                    self._save(tenant, result)
                    continue
                result["events"].append({
                    "type": "AI_PLANNING_STOPPED", "error_type": type(error).__name__
                })
                break

        if program is None or verification is None or not verification["passed"]:
            result["status"] = "HELD"
            result["outcome"] = {
                "money_moved": False,
                "reason": (verification or {}).get("errors", ["NO_VERIFIED_PROGRAM"]),
            }
            self._save(tenant, result)
            return result

        challenges = challenge_financial_program(program, goal, evidence)
        if not all(item["rejected"] for item in challenges):
            result["status"] = "HELD"
            result["outcome"] = {"money_moved": False, "reason": ["GUARD_CHALLENGE_FAILED"]}
            self._save(tenant, result)
            return result
        result["program"] = {
            "candidate": program.model_dump(),
            "verification": verification,
            "adversarial_checks": challenges,
        }
        self._execute(tenant, result, goal, evidence, program)
        return result

    def _existing_receipt(self, tenant, goal, live):
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            return self.durable.payment_receipt(tenant, goal.goal_id, live)
        with self.connect() as db:
            row = db.execute("SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                             (tenant, goal.goal_id)).fetchone()
            if row is None and live:
                bill = live["authoritative_bill"]
                row = db.execute(
                    "SELECT p.receipt_json FROM friday_payments p JOIN friday_dynamic_cases c "
                    "ON p.tenant_id=c.tenant_id AND p.goal_id=json_extract(c.case_json,'$.goal.goal_id') "
                    "WHERE p.tenant_id=? AND json_extract(c.case_json,'$.live.authoritative_bill.bill_reference')=? "
                    "AND json_extract(c.case_json,'$.live.authoritative_bill.provider_id')=? LIMIT 1",
                    (tenant, bill["bill_reference"], bill["provider_id"])).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (ValueError, TypeError):
            return {}

    def _execute(self, tenant, result, goal, evidence, program) -> None:
        fresh = self._load_case(tenant, result["case_id"])
        fresh_goal = FinancialGoal.model_validate(fresh["goal"])
        fresh_evidence = FinancialEvidence.model_validate(fresh["evidence"])
        if fresh_goal != goal or fresh_evidence != evidence:
            result["status"] = "HELD"
            result["outcome"] = {"money_moved": False, "reason": ["SOURCE_CHANGED"]}
            self._save(tenant, result)
            return
        verification = verify_financial_program(program, fresh_goal, fresh_evidence)
        if not verification["passed"]:
            result["status"] = "HELD"
            result["outcome"] = {"money_moved": False, "reason": verification["errors"]}
            self._save(tenant, result)
            return

        if fresh_evidence.prior_outcome == "UNKNOWN":
            result["status"] = "RECONCILED_COMPLETED" if fresh_evidence.reconciliation_result == "SUCCEEDED" else "HELD"
            result["outcome"] = {
                "money_moved": False,
                "new_payment_created": False,
                "provider_outcome": fresh_evidence.reconciliation_result,
                "message": "Existing provider operation was checked; no retry was sent.",
            }
            result["events"].append({"type": "RECONCILED_BEFORE_RETRY", "new_payment": False})
            self._save(tenant, result)
            return

        if self.durable.mode == "FIRESTORE_HYBRID":
            result["status"] = "HELD"
            result["outcome"] = {
                "money_moved": False,
                "new_payment_created": False,
                "reason": ["PAYMENT_STATE_NOT_DURABLE"],
            }
            result["events"].append({
                "type": "PAYMENT_HELD_UNTIL_DURABLE_TRANSACTION",
                "new_payment": False,
            })
            self._save(tenant, result)
            return

        payload = {
            "tenant_id": tenant,
            "goal_id": goal.goal_id,
            "operation_id": "ffpay_" + uuid4().hex,
            "provider_id": goal.provider_id,
            "payee_id": goal.payee_id,
            "amount_minor": verification["authorised_total_minor"],
            "currency": goal.currency,
            "idempotency_key": goal.idempotency_key,
            "evidence_digest": sha256_hex(fresh_evidence.model_dump()),
            "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY",
        }
        if self.durable.mode == "FIRESTORE_TRANSACTIONAL":
            receipt = {"payload": payload, "signature": self.signer.sign(payload), "key_id": self.signer.key_id}
            committed = self.durable.execute_payment(tenant, result, receipt, fresh.get("live"), self.signer)
            result.clear()
            result.update(committed)
            return
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                (tenant, goal.goal_id),
            ).fetchone()
            if row is None and fresh.get("live"):
                # Preserve payments made before bill-level identities were introduced.
                bill = fresh["live"]["authoritative_bill"]
                row = db.execute(
                    "SELECT p.receipt_json FROM friday_payments p JOIN friday_dynamic_cases c "
                    "ON p.tenant_id=c.tenant_id AND p.goal_id=json_extract(c.case_json,'$.goal.goal_id') "
                    "WHERE p.tenant_id=? AND json_extract(c.case_json,'$.live.authoritative_bill.bill_reference')=? "
                    "AND json_extract(c.case_json,'$.live.authoritative_bill.provider_id')=? LIMIT 1",
                    (tenant, bill["bill_reference"], bill["provider_id"]),
                ).fetchone()
            if row:
                receipt = json.loads(row[0])
                intact = self.signer.verify(receipt["payload"], receipt["signature"]) and all(
                    receipt["payload"].get(field) == payload[field]
                    for field in ("tenant_id", "provider_id", "payee_id", "amount_minor", "currency")
                )
                result["status"] = "ALREADY_COMPLETED" if intact else "HELD"
                result["outcome"] = {
                    "money_moved": False,
                    "new_payment_created": False,
                    "receipt": receipt if intact else None,
                }
            else:
                remaining_balance = None
                if fresh.get("live"):
                    mandate_row = db.execute(
                        "SELECT mandate_json FROM friday_mandates WHERE tenant_id=?", (tenant,)
                    ).fetchone()
                    account_row = db.execute(
                        "SELECT balance_minor FROM friday_accounts WHERE tenant_id=?", (tenant,)
                    ).fetchone()
                    mandate = FridayMandate.model_validate_json(mandate_row[0]) if mandate_row else self._default_mandate()
                    bill = fresh["live"]["authoritative_bill"]
                    provider_row = db.execute(
                        "SELECT bill_json FROM friday_provider_bills WHERE tenant_id=? AND bill_reference=?",
                        (tenant, bill["bill_reference"]),
                    ).fetchone()
                    changed = []
                    if provider_row is None or json.loads(provider_row[0]) != bill:
                        changed = ["PROVIDER_CHANGED"]
                    elif mandate.instruction != goal.instruction or mandate.max_fee_minor < goal.max_fee_minor:
                        changed = ["MANDATE_CHANGED"]
                    elif result.get("automatic") and (not mandate.automatic_sandbox_execution or payload["amount_minor"] > mandate.automatic_payment_limit_minor):
                        changed = ["AUTOMATIC_PERMISSION_CHANGED"]
                    if changed:
                        result["status"] = "HELD"
                        result["outcome"] = {"money_moved": False, "new_payment_created": False, "reason": changed}
                        db.execute("UPDATE friday_runs SET result_json=? WHERE tenant_id=? AND run_id=?",
                                   (json.dumps(result), tenant, result["run_id"]))
                        return
                    balance = account_row[0] if account_row else 5_000_000
                    remaining_balance = balance - verification["authorised_total_minor"]
                    if remaining_balance < mandate.protected_balance_minor:
                        result["status"] = "HELD"
                        result["outcome"] = {
                            "money_moved": False,
                            "new_payment_created": False,
                            "reason": ["PROTECTED_BALANCE"],
                        }
                        result["events"].append({"type": "PROTECTED_BALANCE_HELD", "new_payment": False})
                        db.execute(
                            "UPDATE friday_runs SET result_json=? WHERE tenant_id=? AND run_id=?",
                            (json.dumps(result), tenant, result["run_id"]),
                        )
                        self.durable.put("runs", tenant, result["run_id"], {"result": result})
                        return
                receipt = {
                    "payload": payload,
                    "signature": self.signer.sign(payload),
                    "key_id": self.signer.key_id,
                }
                db.execute(
                    "INSERT INTO friday_payments VALUES (?,?,?,?)",
                    (tenant, goal.goal_id, goal.idempotency_key, json.dumps(receipt)),
                )
                if remaining_balance is not None:
                    db.execute(
                        "INSERT INTO friday_accounts VALUES (?,?) ON CONFLICT(tenant_id) "
                        "DO UPDATE SET balance_minor=excluded.balance_minor",
                        (tenant, remaining_balance),
                    )
                saved = db.execute(
                    "SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                    (tenant, goal.goal_id),
                ).fetchone()
                if saved is None or json.loads(saved[0]) != receipt:
                    raise RuntimeError("financial action readback failed")
                result["status"] = "COMPLETED_SYNTHETIC"
                result["outcome"] = {
                    "money_moved": True,
                    "new_payment_created": True,
                    "receipt": receipt,
                    "sandbox_balance_minor": remaining_balance,
                }
            result["events"].append({
                "type": "RESTRICTED_EXECUTOR_RESULT",
                "status": result["status"],
                "new_payment": result["outcome"]["new_payment_created"],
            })
            db.execute(
                "UPDATE friday_runs SET result_json=? WHERE tenant_id=? AND run_id=?",
                (json.dumps(result), tenant, result["run_id"]),
            )
        self.durable.put("runs", tenant, result["run_id"], {"result": result})
        final_balance = result.get("outcome", {}).get("sandbox_balance_minor")
        if final_balance is not None:
            self.durable.put("accounts", tenant, "current", {
                "balance_minor": final_balance,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
