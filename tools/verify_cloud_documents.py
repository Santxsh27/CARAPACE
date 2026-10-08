"""Live Vertex document check using artificial PDF fixtures, with no payment.

Registers an artificial bill above the existing automatic-payment limit. Does
not change standing permission, identity enrollment or IAM. No POST retries.
"""
import argparse
import json
import ssl
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def validate_result(result, *, reference, amount, payee, mismatch=False):
    facts = result["interpretation"]
    assert facts["bill_reference"] == reference, "bill reference extraction failed"
    assert facts["amount_minor"] == amount, "amount extraction failed"
    assert facts["claimed_payee_id"] == payee, "recipient extraction failed"
    assert result["understanding"]["mode"] == "VERTEX_AI", "not a live Vertex result"
    assert result["understanding"]["successful_model_calls"] >= 1
    assert result["document"]["raw_file_stored"] is False
    assert facts["evidence_spans"], "no source quotations"
    assert not result["money_moved"] and not result.get("run_id"), "unexpected execution"
    if mismatch:
        assert result["state"] == "ATTENTION"
        assert "RECIPIENT_MISMATCH" in result["reason"]
    else:
        assert result["state"] == "READY"
        assert "ABOVE_AUTOMATIC_LIMIT" in result["reason"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--amount-minor", type=int, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--mismatch-pdf", type=Path, required=True)
    parser.add_argument("--ca-file")
    parser.add_argument("--inspect", action="store_true", help="Read existing artificial document results only")
    args = parser.parse_args()
    if not args.url.startswith("https://") or not args.url.endswith(".run.app"):
        parser.error("use the private Cloud Run HTTPS origin without a path")
    def cli(*parts):
        return subprocess.run([args.gcloud, *parts], check=True, capture_output=True).stdout.decode().strip()
    token = cli("auth", "print-identity-token")
    keys = json.loads(cli("secrets", "versions", "access", "1", "--secret=friday-tenant-api-keys",
                          "--project=" + args.project))
    headers = {"Authorization": "Bearer " + token, "X-Carapace-Tenant": "cloud-demo",
               "X-Carapace-API-Key": keys["cloud-demo"]}
    tls = ssl.create_default_context(cafile=args.ca_file)
    def request(path, body=None, mime="application/json"):
        payload = json.dumps(body).encode() if isinstance(body, dict) else body
        with urlopen(Request(args.url + "/v1/friday/" + path, data=payload,
                             headers={**headers, "Content-Type": mime}), context=tls, timeout=180) as r:
            return json.load(r)
    mandate = request("mandate")
    if args.inspect:
        items = request("live-input")["items"]
        print(json.dumps([item for item in items if item.get("interpretation", {}).get("bill_reference") == args.reference], indent=2))
        return
    rules = mandate["mandate"]
    if args.amount_minor <= rules["automatic_payment_limit_minor"]:
        raise ValueError("test could execute automatically; choose an amount above the saved limit")
    if mandate["sandbox_balance_minor"] - args.amount_minor < rules["protected_balance_minor"]:
        raise ValueError("test would hit the reserve instead of isolating document validation")
    before = mandate["sandbox_balance_minor"]
    request("test-provider/bills", {"bill_reference": args.reference, "provider_name": "Friday Test Power",
            "provider_id": "friday-test-power", "payee_id": "fridaydocs@upi", "amount_minor": args.amount_minor,
            "currency": "INR", "due_date": "2026-10-28"})
    outcomes = []
    for file, payee, mismatch in ((args.pdf, "fridaydocs@upi", False),
                                  (args.mismatch_pdf, "stranger@upi", True)):
        result = request("documents?" + urlencode({"filename": file.name}), file.read_bytes(), "application/pdf")
        validate_result(result, reference=args.reference, amount=args.amount_minor, payee=payee, mismatch=mismatch)
        outcomes.append({"state": result["state"], "reason": result["reason"],
                         "event_id": result["event_id"], "model": result["understanding"]["model"],
                         "document_sha256": result["document"]["sha256"], "money_moved": False})
    assert request("mandate")["sandbox_balance_minor"] == before, "balance changed"
    print(json.dumps({"scope": "Two artificial PDF fixtures; live private API, not browser upload or real-bank proof",
                      "balance_unchanged": True, "outcomes": outcomes}, indent=2))


if __name__ == "__main__":
    main()
