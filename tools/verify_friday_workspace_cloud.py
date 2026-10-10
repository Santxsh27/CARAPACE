"""Release checks without payments/rule changes; optional paid-alert AI intake."""
import argparse
import json
import ssl
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--ca-file")
    parser.add_argument("--check-paid-alert", action="store_true",
        help="One live AI interpretation of an artificial paid notice; never a payment request")
    args = parser.parse_args()
    if not args.url.startswith("https://") or not args.url.endswith(".run.app"):
        parser.error("use the private Cloud Run HTTPS origin")

    def cli(*parts):
        return subprocess.run([args.gcloud, *parts], check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout.decode().strip()

    token = cli("auth", "print-identity-token")
    keys = json.loads(cli("secrets", "versions", "access", "1",
        "--secret=friday-tenant-api-keys", "--project=" + args.project))
    headers = {"Authorization": "Bearer " + token, "X-Carapace-Tenant": "cloud-demo",
               "X-Carapace-API-Key": keys["cloud-demo"], "Content-Type": "application/json"}
    context = ssl.create_default_context(cafile=args.ca_file)

    def request(path, body=None, authenticated=True):
        data = json.dumps(body).encode() if body is not None else None
        with urlopen(Request(args.url + path, data=data,
            headers=headers if authenticated else {}), timeout=60, context=context) as response:
            return json.load(response)

    health = request("/health/ready")
    assert health["version"] == "0.15.0", "wrong candidate version"
    assert request("/v1/friday/storage-status")["mode"] == "FIRESTORE_TRANSACTIONAL"
    before = request("/v1/friday/mandate")["sandbox_balance_minor"]
    workspace = request("/v1/friday/workspace")
    assert workspace["scope"] == "ARTIFICIAL_MONEY" and workspace["read_only"]
    assert not workspace["money_moved"] and workspace["balance_minor"] == before
    assert workspace["coverage"]["bill_records_returned"] == len(workspace["bills"])
    plan = request("/v1/friday/bill-plan")
    assert plan["read_only"] and not plan["money_moved"] and not plan["payment_authorized"]
    if plan["state"] == "PLANNED":
        assert plan["planned_total_minor"] <= workspace["available_above_reserve_minor"]
        assert plan["remaining_above_reserve_minor"] >= 0
    unavailable = request("/v1/friday/follow-through", {"bill_reference": "RELEASE-CHECK-NO-ACTION"})
    assert unavailable["state"] == "UNAVAILABLE"
    assert unavailable["reason"] == "CLOUD_CONNECTOR_NOT_IMPLEMENTED"
    assert not unavailable["money_moved"] and not unavailable["external_settlement_verified"]
    assert request("/v1/friday/mandate")["sandbox_balance_minor"] == before
    paid_alert_verified = False
    if args.check_paid_alert:
        assert workspace["bills"], "an existing artificial bill is needed for the alert check"
        bill = workspace["bills"][0]
        signal = request("/v1/friday/live-input", {"source_type": "MESSAGE",
            "content_text": f"Payment successful. Bill {bill['bill_reference']} from {bill['provider_name']} "
                f"for INR {bill['amount_minor'] // 100}.{bill['amount_minor'] % 100:02d} "
                f"to {bill['payee_id']} was already paid. This is a payment receipt, not a request to pay."})
        assert signal["understanding"]["mode"] == "VERTEX_AI", "live Vertex interpretation required"
        assert signal["state"] == "ATTENTION" and signal["reason"] == ["NOT_A_PAYMENT_REQUEST"]
        assert not signal["money_moved"] and not signal.get("case_id"), "paid notice must not prepare a payment"
        assert request("/v1/friday/mandate")["sandbox_balance_minor"] == before
        paid_alert_verified = True
    try:
        request("/health/ready", authenticated=False)
    except HTTPError as error:
        assert error.code in {401, 403}, "unexpected unauthenticated response"
    else:
        raise AssertionError("anonymous access unexpectedly allowed")
    print(json.dumps({"version": health["version"], "workspace_verified": True,
        "bill_records": len(workspace["bills"]), "balance_unchanged": True,
        "plan_state": plan["state"], "plan_has_no_payment_authority": True,
        "cloud_followthrough_disabled": True, "anonymous_access_rejected": True,
        "live_paid_alert_verified": paid_alert_verified,
        "live_ai_intake_requested": args.check_paid_alert, "payment_requests": 0}))


if __name__ == "__main__":
    main()
