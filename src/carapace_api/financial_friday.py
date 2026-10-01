"""Durable orchestrator and restricted artificial-money executor."""
from __future__ import annotations

import json
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
    verify_financial_program,
)
from carapace_integrations.financial_friday_fixtures import load_case


class FinancialFridayService:
    def __init__(self, database_path: Path, signer, planner):
        self.path, self.signer, self.planner = database_path, signer, planner
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
            """)

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

    def get(self, tenant: str, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT result_json FROM friday_runs WHERE tenant_id=? AND run_id=?",
                (tenant, run_id),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
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
        receipts = []
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
        }

    def run(self, tenant: str, case_id: str, planner=None) -> dict:
        case = load_case(case_id)
        goal = FinancialGoal.model_validate(case["goal"])
        evidence = FinancialEvidence.model_validate(case["evidence"])
        planner = planner or self.planner
        result = {
            "run_id": "ff_" + uuid4().hex,
            "case_id": case_id,
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
        context = {"goal": goal.model_dump(), "evidence": evidence.model_dump()}
        program = None
        verification = None
        for attempt in range(2):
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

    def _execute(self, tenant, result, goal, evidence, program) -> None:
        fresh = load_case(result["case_id"])
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
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT receipt_json FROM friday_payments WHERE tenant_id=? AND goal_id=?",
                (tenant, goal.goal_id),
            ).fetchone()
            if row:
                receipt = json.loads(row[0])
                intact = self.signer.verify(receipt["payload"], receipt["signature"])
                result["status"] = "ALREADY_COMPLETED" if intact else "HELD"
                result["outcome"] = {
                    "money_moved": False,
                    "new_payment_created": False,
                    "receipt": receipt if intact else None,
                }
            else:
                receipt = {
                    "payload": payload,
                    "signature": self.signer.sign(payload),
                    "key_id": self.signer.key_id,
                }
                db.execute(
                    "INSERT INTO friday_payments VALUES (?,?,?,?)",
                    (tenant, goal.goal_id, goal.idempotency_key, json.dumps(receipt)),
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
