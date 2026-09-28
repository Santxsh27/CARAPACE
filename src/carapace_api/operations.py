"""Durable resolution runs and a mandate-limited synthetic action executor."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from carapace_ai.operations import investigation_context
from carapace_core.canonical import sha256_hex
from carapace_core.obligations import TOOLS, check_obligation, evidence_graph
from carapace_core.resolution import verify_resolution, challenge_resolution
from carapace_integrations.operations_fixtures import load_case


class InvalidInvestigationPlan(ValueError):
    """Safe fixed diagnostic codes, never raw provider or document text."""


class OperationsService:
    def __init__(self, database_path: Path, signer, planner):
        self.path, self.signer, self.planner = database_path, signer, planner
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS operations_runs (
                    tenant_id TEXT NOT NULL, run_id TEXT NOT NULL,
                    result_json TEXT NOT NULL, PRIMARY KEY (tenant_id,run_id));
                CREATE TABLE IF NOT EXISTS operations_postings (
                    tenant_id TEXT NOT NULL, invoice_id TEXT NOT NULL,
                    posting_id TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
                    payee_account TEXT NOT NULL, currency TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL, receipt_json TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,invoice_id));
                CREATE TABLE IF NOT EXISTS operations_resolution_actions (
                    tenant_id TEXT NOT NULL, invoice_id TEXT NOT NULL,
                    action TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
                    PRIMARY KEY(tenant_id,invoice_id,action));
                CREATE TABLE IF NOT EXISTS operations_resolution_receipts (
                    tenant_id TEXT NOT NULL, invoice_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL, PRIMARY KEY(tenant_id,invoice_id));
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def save(self, tenant: str, result: dict) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO operations_runs VALUES (?,?,?) ON CONFLICT(tenant_id,run_id) DO UPDATE SET result_json=excluded.result_json",
                       (tenant, result["run_id"], json.dumps(result)))

    def get(self, tenant: str, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT result_json FROM operations_runs WHERE tenant_id=? AND run_id=?", (tenant, run_id)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row[0])

    def resolve(self, tenant: str, case_id: str, planner=None) -> dict:
        case = load_case(case_id)
        planner = planner or self.planner
        invoice, observed, events = case["invoice"], {}, []
        result = {"run_id": "ops_" + uuid4().hex, "case_id": case_id, "status": "INVESTIGATING",
                  "started_at": datetime.now(timezone.utc).isoformat(), "events": events,
                  "provenance": {"mode": planner.mode, "model": planner.model_name,
                                 "successful_model_calls": 0, "successful_resolution_calls": 0,
                                 "connector": "SYNTHETIC_SNAPSHOT"},
                  "posting": None, "scope": "Artificial-money operations ledger; no real bank, ERP or settlement integration."}
        self.save(tenant, result)
        assessment = check_obligation(invoice, observed)
        plan_feedback = []
        correction_used = False
        for _ in range(len(TOOLS) + 1):
            if assessment["decision"] != "INVESTIGATE":
                break
            try:
                context = investigation_context(invoice, observed, assessment)
                if plan_feedback:
                    context["validation_feedback"] = plan_feedback
                plan = planner.plan(context)
                if planner.mode != "LOCAL_RULES":
                    result["provenance"]["successful_model_calls"] += 1
                if not set(plan.evidence_ids).issubset(observed):
                    raise InvalidInvestigationPlan("UNOBSERVED_EVIDENCE_CITATION")
                if len(set(plan.lookups)) != len(plan.lookups) or any(tool not in TOOLS or tool in observed for tool in plan.lookups):
                    raise InvalidInvestigationPlan("INVALID_OR_REPEATED_LOOKUP")
                plan_feedback = []
                events.append({"type": "PLAN", "rationale": plan.rationale,
                               "lookups": plan.lookups, "evidence_ids": plan.evidence_ids,
                               "authority": "HYPOTHESIS_ONLY"})
                for tool in plan.lookups:
                    observed[tool] = case["records"][tool]
                    events.append({"type": "EVIDENCE_RETRIEVED", "source": tool,
                                   "record": observed[tool]})
                    assessment = check_obligation(invoice, observed)
                    if assessment["decision"] == "HOLD":
                        break
                self.save(tenant, result)
            except (ValidationError, InvalidInvestigationPlan) as error:
                plan_feedback = ([str(error)] if isinstance(error, InvalidInvestigationPlan)
                                 else ["OUTPUT_SCHEMA_INVALID"])
                events.append({"type": "EVIDENCE_PLAN_REJECTED", "errors": plan_feedback})
                if correction_used:
                    result["status"] = "UNRESOLVED"
                    break
                correction_used = True
                self.save(tenant, result)
            except Exception as error:
                # No silent switch from live Gemini to local planning.
                events.append({"type": "INVESTIGATION_STOPPED", "error_type": type(error).__name__})
                result["status"] = "UNRESOLVED"
                break
        result.update({"assessment": assessment, "graph": evidence_graph(invoice, observed),
                       "lookup_count": len(observed), "mandate": case["mandate"]})
        if result["status"] == "UNRESOLVED":
            self.save(tenant, result)
            return result
        result["status"] = {"HOLD": "HELD", "NO_PAYMENT_DUE": "NO_PAYMENT_DUE",
                            "INVESTIGATE": "UNRESOLVED", "READY": "READY"}[assessment["decision"]]
        if result["status"] == "READY":
            program = self._compose_resolution(tenant, result, case, observed, planner)
            if program is not None:
                self._execute(tenant, result, case, observed, program)
        else:
            events.append({"type": "GATE", "outcome": result["status"], "money_moved": False})
            self.save(tenant, result)
        return result

    def _compose_resolution(self, tenant, result, case, observed, planner):
        context = {"untrusted_invoice": case["invoice"], "observed_evidence": observed,
                   "mandate": case["mandate"]}
        for attempt in range(2):
            try:
                program = planner.resolve(context)
                if planner.mode != "LOCAL_RULES":
                    result["provenance"]["successful_model_calls"] += 1
                    result["provenance"]["successful_resolution_calls"] += 1
                verification = verify_resolution(program, case["invoice"], observed, case["mandate"])
                result["events"].append({"type": "RESOLUTION_PROPOSED", "attempt": attempt + 1,
                                         "program": program.model_dump(), "verification": verification})
                if not verification["passed"]:
                    context["validation_feedback"] = verification["errors"]
                    self.save(tenant, result)
                    continue
                challenges = challenge_resolution(program, case["invoice"], observed, case["mandate"])
                if not all(item["rejected"] for item in challenges):
                    raise ValueError("resolution challenge failed")
                result["resolution"] = {"program": program.model_dump(), "verification": verification,
                                        "challenges": challenges, "executed": False}
                result["events"].append({"type": "RESOLUTION_VERIFIED", "checks": len(challenges),
                                         "scope": "Six bounded negative tests; not a complete banking simulation."})
                self.save(tenant, result)
                return program
            except ValidationError as error:
                # Give the model one bounded chance to repair its output shape.
                # Never echo raw rejected values or provider error messages.
                feedback = sorted({"OUTPUT_SCHEMA_INVALID:" + issue["type"]
                                   for issue in error.errors(include_input=False)})[:8]
                context["validation_feedback"] = feedback
                result["events"].append({"type": "RESOLUTION_SCHEMA_REJECTED",
                                         "attempt": attempt + 1, "errors": feedback})
                self.save(tenant, result)
            except Exception as error:
                result["events"].append({"type": "RESOLUTION_STOPPED", "error_type": type(error).__name__})
                break
        result["status"] = "UNRESOLVED"
        self.save(tenant, result)
        return None

    def _execute(self, tenant: str, result: dict, case: dict, observed: dict, program) -> None:
        """Recheck at the write boundary; commit receipt and posting atomically."""
        fresh = load_case(result["case_id"])
        if fresh != case or observed != {key: fresh["records"][key] for key in observed}:
            result["status"] = "UNRESOLVED"
            result["events"].append({"type": "GATE", "outcome": "SOURCE_CHANGED"})
            self.save(tenant, result)
            return
        verified = check_obligation(fresh["invoice"], observed)
        plan_check = verify_resolution(program, fresh["invoice"], observed, fresh["mandate"])
        mandate, invoice = fresh["mandate"], fresh["invoice"]
        due = verified["payable_minor"]
        if (not plan_check["passed"] or verified["decision"] != "READY" or type(due) is not int or not 0 < due <= mandate["per_payment_limit_minor"]
            or invoice["supplier_id"] != mandate["supplier_id"] or verified["payee_account"] != mandate["account"]
            or invoice["currency"] != mandate["currency"]):
            result["status"] = "HELD"
            result["events"].append({"type": "GATE", "outcome": "MANDATE_REJECTED"})
            self.save(tenant, result)
            return
        digest = sha256_hex({"invoice": invoice, "evidence": observed, "mandate": mandate})
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM operations_postings WHERE tenant_id=? AND invoice_id=?", (tenant, invoice["invoice_id"])).fetchone()
            if existing:
                receipt = json.loads(existing["receipt_json"])
                payload = receipt["payload"]
                intact = (existing["evidence_digest"] == digest and existing["amount_minor"] == due
                          and existing["payee_account"] == mandate["account"] and existing["currency"] == invoice["currency"]
                          and self.signer.verify(payload, receipt["signature"])
                          and payload == {"tenant_id": tenant, "invoice_id": invoice["invoice_id"],
                                          "posting_id": existing["posting_id"], "amount_minor": due,
                                          "payee_account": mandate["account"], "currency": invoice["currency"],
                                          "evidence_digest": digest, "mandate_version": mandate["version"],
                                          "scope": "OPERATIONS_SYNTHETIC_LEDGER"})
                result["status"] = "ALREADY_POSTED" if intact else "HELD"
                result["posting"] = receipt if intact else None
                result["events"].append({"type": "GATE", "outcome": result["status"], "new_posting": False})
            else:
                total = db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM operations_postings WHERE tenant_id=?", (tenant,)).fetchone()[0]
                if total + due > mandate["total_limit_minor"]:
                    result["status"] = "HELD"
                    result["events"].append({"type": "GATE", "outcome": "MANDATE_TOTAL_LIMIT"})
                else:
                    payload = {"tenant_id": tenant, "invoice_id": invoice["invoice_id"], "posting_id": "opay_" + uuid4().hex,
                               "amount_minor": due, "payee_account": mandate["account"], "currency": invoice["currency"],
                               "evidence_digest": digest, "mandate_version": mandate["version"],
                               "scope": "OPERATIONS_SYNTHETIC_LEDGER"}
                    receipt = {"payload": payload, "signature": self.signer.sign(payload), "key_id": self.signer.key_id}
                    db.execute("INSERT INTO operations_postings VALUES (?,?,?,?,?,?,?,?)", (
                        tenant, invoice["invoice_id"], payload["posting_id"], due, mandate["account"], invoice["currency"], digest, json.dumps(receipt)))
                    row = db.execute("SELECT amount_minor,payee_account FROM operations_postings WHERE tenant_id=? AND invoice_id=?", (tenant, invoice["invoice_id"])).fetchone()
                    if tuple(row) != (due, mandate["account"]):
                        raise RuntimeError("posting readback failed")
                    result["status"], result["posting"] = "POSTED_SYNTHETIC", receipt
                    result["events"].append({"type": "EXECUTED_AND_READ_BACK", "amount_minor": due,
                                             "adjustment_minor": invoice["amount_minor"] - due,
                                             "new_posting": True})
            if result["status"] in {"POSTED_SYNTHETIC", "ALREADY_POSTED"}:
                self._record_resolution(db, tenant, result, invoice, digest, plan_check)
            db.execute("UPDATE operations_runs SET result_json=? WHERE tenant_id=? AND run_id=?",
                       (json.dumps(result), tenant, result["run_id"]))

    def _record_resolution(self, db, tenant, result, invoice, digest, plan_check):
        payload = {"tenant_id": tenant, "invoice_id": invoice["invoice_id"],
                   "posting_id": result["posting"]["payload"]["posting_id"], "evidence_digest": digest,
                   "effects": plan_check["effects"], "scope": "SYNTHETIC_RESOLUTION_JOURNAL",
                   "deferred_minor": plan_check["deferred_minor"], "credit_minor": plan_check["credit_minor"]}
        row = db.execute("SELECT receipt_json FROM operations_resolution_receipts WHERE tenant_id=? AND invoice_id=?",
                         (tenant, invoice["invoice_id"])).fetchone()
        if row:
            receipt = json.loads(row[0])
            if receipt.get("payload") != payload or not self.signer.verify(payload, receipt.get("signature", "")):
                raise ValueError("resolution receipt integrity mismatch")
        else:
            receipt = {"payload": payload, "signature": self.signer.sign(payload), "key_id": self.signer.key_id}
            for effect in plan_check["effects"]:
                db.execute("INSERT INTO operations_resolution_actions VALUES (?,?,?,?)",
                           (tenant, invoice["invoice_id"], effect["action"], effect["amount_minor"]))
            db.execute("INSERT INTO operations_resolution_receipts VALUES (?,?,?)", (tenant, invoice["invoice_id"], json.dumps(receipt)))
        actions = db.execute("SELECT action,amount_minor FROM operations_resolution_actions WHERE tenant_id=? AND invoice_id=?",
                             (tenant, invoice["invoice_id"])).fetchall()
        if sorted((r[0], r[1]) for r in actions) != sorted((e["action"], e["amount_minor"]) for e in plan_check["effects"]):
            raise ValueError("resolution journal readback failed")
        result["resolution"].update({"executed": True, "receipt": receipt,
            "reused_posting": result["status"] == "ALREADY_POSTED",
            "journal_effects_created": row is None})
        result["events"].append({"type": "RESOLUTION_ACTIONS_RECONCILED", "new_journal": row is None,
                                 "effects": plan_check["effects"], "scope": "Local development journal only."})
