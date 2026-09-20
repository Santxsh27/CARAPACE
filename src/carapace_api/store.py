"""Tenant-scoped SQLite evidence store for local and hackathon execution."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from carapace_core.canonical import canonical_json


class StorageConflictError(Exception):
    pass


class StorageNotFoundError(Exception):
    pass


class SQLiteEvidenceStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS contracts (
                    tenant_id TEXT NOT NULL,
                    contract_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, contract_id)
                );

                CREATE TABLE IF NOT EXISTS runs (
                    tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    contract_id TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    verdict TEXT NOT NULL CHECK (verdict IN ('MATCH', 'MISMATCH')),
                    case_id TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, run_id),
                    FOREIGN KEY (tenant_id, contract_id)
                        REFERENCES contracts (tenant_id, contract_id)
                );

                CREATE TABLE IF NOT EXISTS evidence_cases (
                    tenant_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    contract_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'OPEN'),
                    severity TEXT NOT NULL CHECK (severity = 'CRITICAL'),
                    failed_checks_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, case_id),
                    UNIQUE (tenant_id, run_id),
                    FOREIGN KEY (tenant_id, run_id)
                        REFERENCES runs (tenant_id, run_id)
                );

                CREATE TABLE IF NOT EXISTS trust_receipts (
                    tenant_id TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    contract_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, receipt_id),
                    UNIQUE (tenant_id, run_id),
                    FOREIGN KEY (tenant_id, run_id)
                        REFERENCES runs (tenant_id, run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_runs_contract
                    ON runs (tenant_id, contract_id);
                CREATE INDEX IF NOT EXISTS idx_receipts_contract
                    ON trust_receipts (tenant_id, contract_id);
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def put_contract(self, tenant_id: str, payload: Mapping[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO contracts (tenant_id, contract_id, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        payload["contract_id"],
                        canonical_json(payload),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise StorageConflictError("contract already exists") from error

    def get_contract(self, tenant_id: str, contract_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM contracts
                WHERE tenant_id = ? AND contract_id = ?
                """,
                (tenant_id, contract_id),
            ).fetchone()
        if row is None:
            raise StorageNotFoundError("contract not found")
        return json.loads(row["payload_json"])

    def put_run(
        self,
        tenant_id: str,
        evidence: Mapping[str, Any],
        report: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> str | None:
        now = datetime.now(timezone.utc).isoformat()
        case_id = None
        failed_checks = [
            check["code"] for check in report["checks"] if not check["passed"]
        ]
        if report["verdict"] == "MISMATCH":
            case_id = f"case_{uuid4().hex}"

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO runs (
                        tenant_id, run_id, contract_id, evidence_json,
                        report_json, verdict, case_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        evidence["run_id"],
                        evidence["contract_id"],
                        canonical_json(evidence),
                        canonical_json(report),
                        report["verdict"],
                        case_id,
                        now,
                    ),
                )
                if case_id is not None:
                    connection.execute(
                        """
                        INSERT INTO evidence_cases (
                            tenant_id, case_id, run_id, contract_id, status,
                            severity, failed_checks_json, created_at
                        ) VALUES (?, ?, ?, ?, 'OPEN', 'CRITICAL', ?, ?)
                        """,
                        (
                            tenant_id,
                            case_id,
                            evidence["run_id"],
                            evidence["contract_id"],
                            canonical_json(failed_checks),
                            now,
                        ),
                    )
                connection.execute(
                    """
                    INSERT INTO trust_receipts (
                        tenant_id, receipt_id, run_id, contract_id,
                        payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        receipt["receipt_id"],
                        evidence["run_id"],
                        evidence["contract_id"],
                        canonical_json(receipt),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise StorageConflictError("run already exists or contract is missing") from error
        return case_id

    def get_run(self, tenant_id: str, run_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT r.evidence_json, r.report_json, r.case_id,
                       t.payload_json AS receipt_json
                FROM runs AS r
                LEFT JOIN trust_receipts AS t
                  ON t.tenant_id = r.tenant_id AND t.run_id = r.run_id
                WHERE r.tenant_id = ? AND r.run_id = ?
                """,
                (tenant_id, run_id),
            ).fetchone()
        if row is None:
            raise StorageNotFoundError("run not found")
        return {
            "evidence": json.loads(row["evidence_json"]),
            "report": json.loads(row["report_json"]),
            "case_id": row["case_id"],
            "receipt": (
                json.loads(row["receipt_json"])
                if row["receipt_json"] is not None
                else None
            ),
        }

    def get_receipt(self, tenant_id: str, receipt_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM trust_receipts
                WHERE tenant_id = ? AND receipt_id = ?
                """,
                (tenant_id, receipt_id),
            ).fetchone()
        if row is None:
            raise StorageNotFoundError("trust receipt not found")
        return json.loads(row["payload_json"])

    def get_case(self, tenant_id: str, case_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT case_id, run_id, contract_id, status, severity,
                       failed_checks_json, created_at
                FROM evidence_cases
                WHERE tenant_id = ? AND case_id = ?
                """,
                (tenant_id, case_id),
            ).fetchone()
        if row is None:
            raise StorageNotFoundError("evidence case not found")
        return {
            "case_id": row["case_id"],
            "run_id": row["run_id"],
            "contract_id": row["contract_id"],
            "status": row["status"],
            "severity": row["severity"],
            "failed_checks": json.loads(row["failed_checks_json"]),
            "created_at": row["created_at"],
        }
