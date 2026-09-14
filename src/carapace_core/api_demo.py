"""Run a repeatable end-to-end demonstration against the CARAPACE API."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .canonical import request_digest


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _prepare_payloads(
    examples_directory: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    suffix = uuid4().hex[:10]
    contract_id = f"pac_demo_{suffix}"
    idempotency_key = f"idem_demo_{suffix}"
    now = datetime.now(timezone.utc)

    contract = deepcopy(_load(examples_directory / "payment-promise.json"))
    contract["contract_id"] = contract_id
    contract["created_at"] = _timestamp(now)
    contract["expires_at"] = _timestamp(now + timedelta(minutes=15))
    contract["confirmation"]["confirmed_at"] = _timestamp(
        now + timedelta(seconds=1)
    )
    contract["integrity"]["nonce"] = f"nonce_demo_{uuid4().hex}"
    contract["integrity"]["idempotency_key"] = idempotency_key
    contract["integrity"]["request_hash_sha256"] = request_digest(
        contract["payment"]
    )

    valid = deepcopy(_load(examples_directory / "execution-valid.json"))
    duplicate = deepcopy(
        _load(examples_directory / "execution-duplicate-debit.json")
    )

    for label, evidence in (("valid", valid), ("duplicate", duplicate)):
        evidence["run_id"] = f"run_{label}_{suffix}"
        evidence["contract_id"] = contract_id
        evidence["observed_at"] = _timestamp(now + timedelta(seconds=2))
        evidence["idempotency_key"] = idempotency_key
        evidence["actual_request_hash_sha256"] = request_digest(
            evidence["actual_request"]
        )
        evidence["settlement_reference"] = f"settlement_{label}_{suffix}"
        for index, entry in enumerate(evidence["ledger_entries"], start=1):
            entry["entry_id"] = f"entry_{label}_{suffix}_{index}"
            entry["logical_payment_id"] = contract_id

    return contract, valid, duplicate


def _call(
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
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(
            f"cannot reach CARAPACE at {base_url}; start the API first"
        ) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carapace-demo",
        description="run the valid and duplicate-debit API workflow",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--tenant", default="demo-bank")
    parser.add_argument("--api-key", default="local-demo-key-change-me")
    parser.add_argument("--examples-dir", default="examples", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        contract, valid, duplicate = _prepare_payloads(args.examples_dir)
        contract_id = contract["contract_id"]

        print("[1/4] Registering a fresh synthetic Payment Promise...")
        _call(
            args.base_url,
            "/v1/contracts",
            args.tenant,
            args.api_key,
            method="POST",
            payload=contract,
        )

        print("[2/4] Verifying one correct debit...")
        valid_result = _call(
            args.base_url,
            f"/v1/contracts/{contract_id}/runs",
            args.tenant,
            args.api_key,
            method="POST",
            payload=valid,
        )

        print("[3/4] Injecting a duplicate-debit counterexample...")
        duplicate_result = _call(
            args.base_url,
            f"/v1/contracts/{contract_id}/runs",
            args.tenant,
            args.api_key,
            method="POST",
            payload=duplicate,
        )
        case_id = duplicate_result.get("case_id")
        if not case_id:
            raise RuntimeError("the mismatch did not create an evidence case")

        print("[4/4] Retrieving the persisted critical incident...")
        incident = _call(
            args.base_url,
            f"/v1/cases/{case_id}",
            args.tenant,
            args.api_key,
        )

        valid_verdict = valid_result["report"]["verdict"]
        duplicate_verdict = duplicate_result["report"]["verdict"]
        failed_checks = incident["failed_checks"]
        passed = (
            valid_verdict == "MATCH"
            and duplicate_verdict == "MISMATCH"
            and "AT_MOST_ONE_POSTED_DEBIT" in failed_checks
        )

        print()
        print("CARAPACE DEMO RESULT")
        print(f"  Correct payment: {valid_verdict}")
        print(f"  Duplicate debit: {duplicate_verdict}")
        print(f"  Incident: {incident['case_id']} ({incident['status']})")
        print(f"  Failed rules: {', '.join(failed_checks)}")
        print(f"  Overall: {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"CARAPACE demo failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
