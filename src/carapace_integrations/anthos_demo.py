"""End-to-end artificial-money demonstration using Bank of Anthos's ledger."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg

from carapace_core.canonical import request_digest

from .bank_of_anthos import BankOfAnthosLedger, BankOfAnthosTransaction


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _account_number() -> str:
    return f"{int(uuid4().hex[:12], 16) % 10_000_000_000:010d}"


def _api_call(
    base_url: str,
    path: str,
    tenant: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "X-Carapace-Tenant": tenant,
        "X-Carapace-API-Key": api_key,
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CARAPACE API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError("cannot reach the CARAPACE API") from error


def build_contract(
    *, contract_id: str, payer: str, payee: str, amount_minor: int
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payment = {
        "direction": "SEND",
        "amount_minor": amount_minor,
        "currency": "USD",
        "fees_minor": 0,
        "payee_id": payee,
        "payee_display_name": "Bank of Anthos Demo Merchant",
        "purpose": "GOODS",
        "reference": f"boa-order-{contract_id[-10:]}",
    }
    return {
        "schema_version": "1.0",
        "contract_id": contract_id,
        "created_at": _timestamp(now),
        "expires_at": _timestamp(now + timedelta(minutes=15)),
        "actor_ref": payer,
        "session_ref": f"boa-session-{contract_id[-10:]}",
        "payment": payment,
        "integrity": {
            "nonce": f"boa_nonce_{uuid4().hex}",
            "request_hash_sha256": request_digest(payment),
            "idempotency_key": f"boa_idem_{uuid4().hex}",
        },
        "confirmation": {
            "confirmed_at": _timestamp(now + timedelta(seconds=1)),
            "method": "TEST_FIXTURE",
        },
        "policy_version": "boa-local-demo-v1",
    }


def build_evidence(
    *,
    contract: dict[str, Any],
    rows: Sequence[BankOfAnthosTransaction],
    run_label: str,
) -> dict[str, Any]:
    payment = contract["payment"]
    actual_request = {
        key: payment[key]
        for key in (
            "direction",
            "amount_minor",
            "currency",
            "fees_minor",
            "payee_id",
            "purpose",
            "reference",
        )
    }
    return {
        "schema_version": "1.0",
        "run_id": f"boa_{run_label}_{uuid4().hex[:12]}",
        "contract_id": contract["contract_id"],
        "observed_at": _timestamp(datetime.now(timezone.utc)),
        "actual_request": actual_request,
        "actual_request_hash_sha256": request_digest(actual_request),
        "idempotency_key": contract["integrity"]["idempotency_key"],
        "lifecycle": [
            "DRAFT",
            "USER_CONFIRMED",
            "AUTHORIZED",
            "SUBMITTED",
            "ACCEPTED",
        ],
        # A Bank of Anthos ledger row proves posting, not external-rail settlement.
        "settlement_reference": None,
        "ledger_entries": [
            row.as_debit_evidence(
                contract_id=contract["contract_id"], currency=payment["currency"]
            )
            for row in rows
        ],
    }


@dataclass(frozen=True)
class AnthosDemoResult:
    contract_id: str
    payer_account: str
    payee_account: str
    amount_minor: int
    currency: str
    first_transaction_id: int
    duplicate_transaction_id: int
    correct_payment_verdict: str
    duplicate_payment_verdict: str
    trust_receipt_id: str
    trust_receipt_level: str
    trust_receipt_summary: str
    settlement_state: str
    mismatch_receipt_id: str
    mismatch_receipt_level: str
    incident_case_id: str
    failed_checks: list[str]
    overall: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_demo(
    *,
    database_url: str,
    api_base_url: str,
    tenant: str,
    api_key: str,
) -> AnthosDemoResult:
    ledger = BankOfAnthosLedger(database_url)
    ledger.wait_until_ready()

    suffix = uuid4().hex[:12]
    contract_id = f"pac_boa_{suffix}"
    payer = _account_number()
    payee = _account_number()
    while payee == payer:
        payee = _account_number()
    amount_minor = 4_999
    contract = build_contract(
        contract_id=contract_id,
        payer=payer,
        payee=payee,
        amount_minor=amount_minor,
    )

    _api_call(
        api_base_url,
        "/v1/contracts",
        tenant,
        api_key,
        method="POST",
        payload=contract,
    )

    first_id = ledger.insert_controlled_test_transaction(
        from_account=payer,
        to_account=payee,
        amount_minor=amount_minor,
    )
    first_rows = ledger.fetch_bound_transactions([first_id])
    correct = _api_call(
        api_base_url,
        f"/v1/contracts/{contract_id}/runs",
        tenant,
        api_key,
        method="POST",
        payload=build_evidence(
            contract=contract, rows=first_rows, run_label="correct"
        ),
    )

    duplicate_id = ledger.insert_controlled_test_transaction(
        from_account=payer,
        to_account=payee,
        amount_minor=amount_minor,
    )
    duplicate_rows = ledger.fetch_bound_transactions([first_id, duplicate_id])
    duplicate = _api_call(
        api_base_url,
        f"/v1/contracts/{contract_id}/runs",
        tenant,
        api_key,
        method="POST",
        payload=build_evidence(
            contract=contract,
            rows=duplicate_rows,
            run_label="duplicate",
        ),
    )

    case_id = duplicate.get("case_id")
    if not case_id:
        raise RuntimeError("duplicate ledger rows did not create an incident")
    incident = _api_call(
        api_base_url, f"/v1/cases/{case_id}", tenant, api_key
    )
    correct_verdict = correct["report"]["verdict"]
    duplicate_verdict = duplicate["report"]["verdict"]
    receipt = correct.get("receipt")
    if not receipt:
        raise RuntimeError("matching payment did not produce a Trust Receipt")
    settlement_stage = next(
        (
            stage
            for stage in receipt["stages"]
            if stage["code"] == "SETTLEMENT_CONFIRMED"
        ),
        None,
    )
    if settlement_stage is None:
        raise RuntimeError("Trust Receipt omitted the settlement stage")
    mismatch_receipt = duplicate.get("receipt")
    if not mismatch_receipt:
        raise RuntimeError("duplicate payment did not produce a mismatch receipt")
    failed_checks = list(incident["failed_checks"])
    passed = (
        correct_verdict == "MATCH"
        and duplicate_verdict == "MISMATCH"
        and receipt["assurance_level"] == "BANK_POSTING_MATCHED"
        and settlement_stage["state"] == "PENDING"
        and mismatch_receipt["assurance_level"] == "MISMATCH"
        and "AT_MOST_ONE_POSTED_DEBIT" in failed_checks
    )
    return AnthosDemoResult(
        contract_id=contract_id,
        payer_account=payer,
        payee_account=payee,
        amount_minor=amount_minor,
        currency="USD",
        first_transaction_id=first_id,
        duplicate_transaction_id=duplicate_id,
        correct_payment_verdict=correct_verdict,
        duplicate_payment_verdict=duplicate_verdict,
        trust_receipt_id=str(receipt["receipt_id"]),
        trust_receipt_level=str(receipt["assurance_level"]),
        trust_receipt_summary=str(receipt["summary"]),
        settlement_state=str(settlement_stage["state"]),
        mismatch_receipt_id=str(mismatch_receipt["receipt_id"]),
        mismatch_receipt_level=str(mismatch_receipt["assurance_level"]),
        incident_case_id=str(case_id),
        failed_checks=failed_checks,
        overall="PASS" if passed else "FAIL",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carapace-anthos-demo",
        description="verify real rows from the local Bank of Anthos ledger",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "BOA_DATABASE_URL",
            "postgresql://admin:password@127.0.0.1:5433/postgresdb",
        ),
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("CARAPACE_API_BASE_URL", "http://127.0.0.1:8080"),
    )
    parser.add_argument("--tenant", default="demo-bank")
    parser.add_argument("--api-key", default="local-demo-key-change-me")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_demo(
            database_url=args.database_url,
            api_base_url=args.api_base_url,
            tenant=args.tenant,
            api_key=args.api_key,
        )
        if args.json_output:
            print(json.dumps(result.as_dict(), indent=2))
        else:
            print("BANK OF ANTHOS -> CARAPACE LIVE DEMO")
            print(f"1. Payment Promise created: {result.contract_id}")
            print(
                "2. Official ledger stored one artificial payment: "
                f"transaction #{result.first_transaction_id}"
            )
            print(
                "3. CARAPACE read that row: "
                f"{result.correct_payment_verdict}"
            )
            print(
                "4. Test harness forced a retry debit: "
                f"transaction #{result.duplicate_transaction_id}"
            )
            print(
                "5. CARAPACE read both rows: "
                f"{result.duplicate_payment_verdict}"
            )
            print(
                "6. Customer Trust Receipt: "
                f"{result.trust_receipt_level} ({result.settlement_state})"
            )
            print(f"7. Evidence case opened: {result.incident_case_id}")
            print(f"   Failed rules: {', '.join(result.failed_checks)}")
            print(f"Overall integration check: {result.overall}")
        return 0 if result.overall == "PASS" else 1
    except (OSError, ValueError, KeyError, RuntimeError, psycopg.Error) as error:
        print(f"Bank of Anthos demo failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
