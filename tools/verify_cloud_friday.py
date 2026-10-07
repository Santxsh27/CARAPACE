"""Authenticated private-cloud checks using artificial funds only.

Credentials stay in process memory. Output contains only check results and
artificial event/receipt identifiers. Requires the already-authorized gcloud CLI.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--resume-event")
    parser.add_argument("--expected-balance", type=int)
    parser.add_argument("--expected-operation")
    parser.add_argument("--expected-key")
    parser.add_argument("--ca-file", help="Trusted PEM CA bundle when the local Python lacks system roots")
    parser.add_argument("--expected-version", default="0.13.2")
    parser.add_argument("--inspect", action="store_true", help="Read sanitized cloud run outcomes without creating a payment")
    args = parser.parse_args()
    if not args.url.startswith("https://") or not args.url.endswith(".run.app"):
        parser.error("use the private Cloud Run HTTPS origin without a path")

    def cli(*parts):
        return subprocess.run([args.gcloud, *parts], check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout.decode().strip()

    token = cli("auth", "print-identity-token")
    keys = json.loads(cli("secrets", "versions", "access", "1", "--secret=friday-tenant-api-keys",
                          "--project=" + args.project))
    tenant = "cloud-demo"
    headers = {"Authorization": "Bearer " + token, "X-Carapace-Tenant": tenant,
               "X-Carapace-API-Key": keys[tenant], "Content-Type": "application/json"}
    tls = ssl.create_default_context(cafile=args.ca_file)

    def request(path, method="GET", body=None, *, authenticated=True):
        data = json.dumps(body).encode() if body is not None else None
        with urlopen(Request(args.url + path, data=data, method=method,
                             headers=headers if authenticated else {}), timeout=180, context=tls) as response:
            return json.load(response)

    health = request("/health/ready")
    assert health["version"] == args.expected_version, health
    storage = request("/v1/friday/storage-status")
    assert storage["mode"] == "FIRESTORE_TRANSACTIONAL", storage
    if args.inspect:
        items = request("/v1/friday/live-input")["items"]
        recent = request("/v1/friday/today")["recent_runs"]
        runs = [request("/v1/friday/runs/" + item["run_id"]) for item in recent]
        print(json.dumps({"balance": request("/v1/friday/mandate")["sandbox_balance_minor"],
                          "signals": [{k: item.get(k) for k in ("event_id", "state", "run_id")} for item in items],
                          "runs": [{"run_id": r["run_id"], "status": r["status"], "outcome": r.get("outcome"),
                                    "events": [{k: e.get(k) for k in ("type", "errors", "error_type")} for e in r["events"]]} for r in runs]}))
        return
    try:
        request("/health/ready", authenticated=False)
        raise AssertionError("service unexpectedly permits anonymous access")
    except HTTPError as error:
        assert error.code in {401, 403}, error.code

    if args.resume_event:
        before = request("/v1/friday/mandate")["sandbox_balance_minor"]
        repeated = request("/v1/friday/live-input/" + args.resume_event + "/run", "POST")["run"]
        after = request("/v1/friday/mandate")["sandbox_balance_minor"]
        assert repeated["status"] == "ALREADY_COMPLETED", repeated["status"]
        assert not repeated["outcome"]["new_payment_created"]
        assert repeated["provenance"]["successful_model_calls"] == 0
        assert before == after == args.expected_balance
        receipt = repeated["outcome"]["receipt"]
        if args.expected_operation:
            assert receipt["payload"]["operation_id"] == args.expected_operation
        if args.expected_key:
            assert receipt["key_id"] == args.expected_key
        print(json.dumps({"phase": "RESUME", "status": repeated["status"], "balance": after,
                          "event_id": args.resume_event, "key_id": receipt["key_id"],
                          "operation_id": receipt["payload"]["operation_id"], "anonymous_blocked": True}))
        return

    rules = {"instruction": "Handle verified household bills and protect my reserve.",
             "protected_balance_minor": 1_000_000, "automatic_payment_limit_minor": 300_000,
             "max_fee_minor": 0, "automatic_sandbox_execution": True}
    before = request("/v1/friday/mandate", "PUT", rules)["sandbox_balance_minor"]
    reference = "FRIDAY-" + uuid4().hex[:12]
    bill = {"bill_reference": reference, "provider_name": "Friday Cloud Power",
            "provider_id": "friday-cloud-power", "payee_id": "fridaycloud@upi",
            "amount_minor": 247_900, "currency": "INR", "due_date": "2026-10-28"}
    request("/v1/friday/test-provider/bills", "POST", bill)
    signal = request("/v1/friday/live-input", "POST", {
        "source_type": "MESSAGE", "content_text":
        f"Friday Cloud Power electricity bill {reference}: INR 2479.00 due 2026-10-28. Payee: fridaycloud@upi. One-time payment."})
    assert signal["state"] == "COMPLETED", signal
    assert signal["understanding"]["mode"] == "VERTEX_AI", signal["understanding"]
    run = request("/v1/friday/runs/" + signal["run_id"])
    assert run["status"] == "COMPLETED_SYNTHETIC", run["status"]
    assert run["provenance"]["mode"] == "VERTEX_AI", run["provenance"]
    assert run["provenance"]["successful_model_calls"] > 0
    after = request("/v1/friday/mandate")["sandbox_balance_minor"]
    assert after == before - bill["amount_minor"]
    assert request("/v1/friday/runs/" + run["run_id"])["status"] == run["status"]
    repeated = request("/v1/friday/live-input/" + signal["event_id"] + "/run", "POST")["run"]
    assert repeated["status"] == "ALREADY_COMPLETED", repeated["status"]
    assert repeated["provenance"]["successful_model_calls"] == 0
    assert request("/v1/friday/mandate")["sandbox_balance_minor"] == after
    mismatch = request("/v1/friday/scenarios/recipient-swap/run", "POST", {"planner": "configured"})
    assert mismatch["status"] == "HELD"
    assert mismatch["provenance"]["successful_model_calls"] == 0
    receipt = run["outcome"]["receipt"]
    print(json.dumps({"phase": "INITIAL", "version": health["version"], "storage": storage["mode"],
                      "status": run["status"], "event_id": signal["event_id"], "run_id": run["run_id"],
                      "balance": after, "key_id": receipt["key_id"],
                      "operation_id": receipt["payload"]["operation_id"],
                      "model": run["provenance"]["model"], "automatic_completion": True,
                      "understanding_attempts": signal["understanding"]["attempts"], "duplicate_blocked": True,
                      "recipient_mismatch_held": True, "anonymous_blocked": True}))


if __name__ == "__main__":
    main()
