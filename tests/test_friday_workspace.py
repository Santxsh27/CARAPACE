"""Read-only workspace and non-payment intake safety regressions, without cloud calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_api.financial_friday import FinancialFridayService
from carapace_api.friday_workspace import financial_workspace
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import (
    FridayMandate, IncomingFinancialSignal, InterpretedFinancialSignal, TestProviderBill,
)
from carapace_integrations.friday_cloud_web import WebSettings, create_cloud_web


class ScopedReadStore:
    """Firestore-shaped reads only; mutation fails the test immediately."""
    mode = "FIRESTORE_TRANSACTIONAL"

    def __init__(self, records):
        self.records = records
        self.calls = []

    def get(self, kind, tenant, record_id):
        self.calls.append(("get", kind, tenant, record_id))
        return deepcopy(self.records.get((kind, tenant, record_id)))

    def list(self, kind, tenant, limit=20):
        self.calls.append(("list", kind, tenant, limit))
        return deepcopy([value for (k, t, _), value in self.records.items()
                         if k == kind and t == tenant][:limit])

    def put(self, *args):
        raise AssertionError("workspace must not write durable records")


class FridayWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.signer = BankEnvelopeSigner(self.root / "key.pem", allow_generate=True)
        self.planner = LocalFinancialFridayPlanner()
        self.service = FinancialFridayService(self.root / "workspace.db", self.signer, self.planner)
        self.rules = FridayMandate(instruction="Handle permitted household bills and preserve my reserve.",
                                   protected_balance_minor=1_000_000,
                                   automatic_payment_limit_minor=300_000)
        self.service.save_mandate("one", self.rules)

    def tearDown(self):
        self.tmp.cleanup()

    def bill(self, reference="BILL-1001", amount=178_000, previous=None, tenant="one"):
        bill = TestProviderBill(bill_reference=reference, provider_name="Artificial power",
                                provider_id="power-test", payee_id="power@upi",
                                amount_minor=amount, previous_amount_minor=previous,
                                due_date="2026-10-12")
        self.service.publish_test_bill(tenant, bill)
        return bill

    def goal(self, bill, tenant="one"):
        return "goal-bill-" + sha256_hex({"tenant": tenant, "provider": bill.provider_id,
                                        "bill": bill.bill_reference})[:24]

    def receipt(self, bill, tenant="one"):
        payload = {"tenant_id": tenant, "goal_id": self.goal(bill, tenant),
                   "provider_id": bill.provider_id, "payee_id": bill.payee_id,
                   "amount_minor": bill.amount_minor, "currency": "INR",
                   "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY", "idempotency_key": "key-" + bill.bill_reference}
        return {"payload": payload, "signature": self.signer.sign(payload), "key_id": self.signer.key_id}

    def record_receipt(self, bill, receipt):
        with self.service.connect() as db:
            db.execute("INSERT INTO friday_payments VALUES (?,?,?,?)",
                       ("one", self.goal(bill), "key-" + bill.bill_reference, json.dumps(receipt)))

    def test_cashflow_is_exact_and_missing_history_is_not_a_pass(self):
        self.bill(amount=178_001)
        self.bill("BILL-1002", amount=248_700, previous=160_000)
        view = financial_workspace(self.service, "one")
        self.assertEqual(view["balance_minor"], 5_000_000)
        self.assertEqual(view["available_above_reserve_minor"], 4_000_000)
        self.assertEqual(view["upcoming_total_minor"], 426_701)
        self.assertEqual(view["budget"]["remaining_after_bills_minor"], 3_573_299)
        self.assertEqual(view["budget"]["shortfall_minor"], 0)
        self.assertEqual(view["bills"][0]["history_status"], "NOT_AVAILABLE")
        self.assertEqual(view["bills"][1]["status"], "REVIEW_INCREASE")

    def test_shortfall_is_reported_without_payment_or_negative_available(self):
        self.service.save_mandate("one", self.rules.model_copy(update={"protected_balance_minor": 6_000_000}))
        self.bill(amount=178_000)
        view = financial_workspace(self.service, "one")
        self.assertEqual(view["available_above_reserve_minor"], 0)
        self.assertEqual(view["budget"]["remaining_after_bills_minor"], -178_000)
        self.assertEqual(view["budget"]["shortfall_minor"], 178_000)
        self.assertFalse(view["money_moved"])

    def test_local_receipt_and_debit_alerts_never_prepare_payment(self):
        self.bill()
        self.service.save_mandate("one", self.rules.model_copy(update={"automatic_sandbox_execution": True}))
        for content in (
            "Bill BILL-1001 INR 1780 recipient power@upi was already paid.",
            "Bill BILL-1001 INR 1780 recipient power@upi payment successful.",
            "Refund receipt bill BILL-1001 INR 1780 recipient power@upi credited.",
        ):
            with self.subTest(content=content):
                result = self.service.ingest_live_signal("one", IncomingFinancialSignal(
                    source_type="MESSAGE", content_text=content))
                self.assertEqual(result["state"], "ATTENTION")
                self.assertEqual(result["reason"], ["NOT_A_PAYMENT_REQUEST"])
                self.assertFalse(result["money_moved"])
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_payments").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_dynamic_cases").fetchone()[0], 0)

    def test_tenant_records_do_not_leak(self):
        self.bill()
        self.bill("PRIVATE-9001", tenant="two")
        one = financial_workspace(self.service, "one")
        self.assertEqual([b["bill_reference"] for b in one["bills"]], ["BILL-1001"])
        self.assertNotIn("PRIVATE-9001", json.dumps(one))

    def test_read_does_not_write_call_models_or_execute(self):
        self.bill()
        self.planner.plan = Mock(side_effect=AssertionError("model called"))
        self.planner.interpret_signal = Mock(side_effect=AssertionError("model called"))
        self.service.run = Mock(side_effect=AssertionError("payment executed"))
        with self.service.connect() as db:
            before = list(db.iterdump())
        first = financial_workspace(self.service, "one")
        financial_workspace(self.service, "one")
        with self.service.connect() as db:
            self.assertEqual(list(db.iterdump()), before)
        self.assertTrue(first["read_only"])
        self.planner.plan.assert_not_called()
        self.planner.interpret_signal.assert_not_called()
        self.service.run.assert_not_called()

    def test_matching_signed_dynamic_goal_receipt_excludes_paid_bill(self):
        bill = self.bill()
        self.record_receipt(bill, self.receipt(bill))
        view = financial_workspace(self.service, "one")
        self.assertEqual(view["bills"][0]["status"], "RECORDED_PAID")
        self.assertEqual(view["upcoming_total_minor"], 0)
        self.assertIn("external settlement is not established", view["bills"][0]["reason"])

    def test_tampered_receipt_is_conflict_not_paid(self):
        bill = self.bill()
        receipt = self.receipt(bill)
        receipt["payload"]["amount_minor"] += 1
        self.record_receipt(bill, receipt)
        view = financial_workspace(self.service, "one")
        self.assertEqual(view["bills"][0]["status"], "RECEIPT_CONFLICT")
        self.assertEqual(view["upcoming_total_minor"], bill.amount_minor)

    def test_valid_signature_for_wrong_tenant_still_conflicts(self):
        bill = self.bill()
        self.record_receipt(bill, self.receipt(bill, "two"))
        self.assertEqual(financial_workspace(self.service, "one")["bills"][0]["status"], "RECEIPT_CONFLICT")

    def test_firestore_reads_are_scoped_and_limit_is_explicit(self):
        records = {
            ("mandates", "one", "current"): {"mandate": self.rules.model_dump()},
            ("accounts", "one", "current"): {"balance_minor": 5_000_000},
        }
        for i in range(101):
            bill = TestProviderBill(bill_reference=f"BILL-{1000+i}", provider_name="Artificial power",
                                    provider_id="power-test", payee_id="power@upi", amount_minor=100,
                                    due_date="2026-10-12")
            records[("provider_bills", "one", bill.bill_reference)] = bill.model_dump()
        records[("provider_bills", "two", "SECRET-1001")] = deepcopy(bill.model_dump())
        store = ScopedReadStore(records)
        self.service.durable = store
        view = financial_workspace(self.service, "one")
        self.assertEqual(view["coverage"]["bill_records_returned"], 100)
        self.assertTrue(view["coverage"]["may_be_truncated"])
        self.assertFalse(view["coverage"]["snapshot_atomic"])
        self.assertEqual(view["upcoming_total_minor"], 10_000)
        self.assertTrue(all(call[2] == "one" for call in store.calls))

    def test_firestore_receipt_uses_provider_bill_identity_key(self):
        bill = self.bill()
        identity = "bill:" + bill.provider_id + ":" + bill.bill_reference
        receipt_id = hashlib.sha256(identity.encode()).hexdigest()
        self.service.durable = ScopedReadStore({
            ("mandates", "one", "current"): {"mandate": self.rules.model_dump()},
            ("accounts", "one", "current"): {"balance_minor": 5_000_000},
            ("provider_bills", "one", bill.bill_reference): bill.model_dump(),
            ("payments", "one", receipt_id): {"receipt": self.receipt(bill)},
        })
        self.assertEqual(financial_workspace(self.service, "one")["bills"][0]["status"], "RECORDED_PAID")
        self.assertIn(("get", "payments", "one", receipt_id), self.service.durable.calls)

    def test_alert_and_unknown_intake_never_prepare_or_execute_payment(self):
        self.bill()
        self.service.save_mandate("one", self.rules.model_copy(update={"automatic_sandbox_execution": True}))
        self.service.run = Mock(side_effect=AssertionError("non-payment executed"))
        for kind in ("TRANSACTION_ALERT", "UNKNOWN"):
            with self.subTest(kind=kind):
                result = self.service._ingest_interpreted_signal("one",
                    IncomingFinancialSignal(source_type="MESSAGE", content_text="BILL-1001 was paid externally.",
                                            event_id="nonpayment-" + kind),
                    InterpretedFinancialSignal(request_kind=kind, bill_reference="BILL-1001",
                                               summary="This is an informational record, not a payment instruction."))
                self.assertEqual(result["reason"], ["NOT_A_PAYMENT_REQUEST"])
                self.assertFalse(result["money_moved"])
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_dynamic_cases").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_payments").fetchone()[0], 0)
            self.assertTrue(all(row[0] is None for row in db.execute("SELECT case_id FROM friday_live_signals")))
        self.assertEqual(self.service.mandate("one")["sandbox_balance_minor"], 5_000_000)
        self.service.run.assert_not_called()

    def test_workspace_api_requires_valid_tenant_authentication(self):
        app = create_app(Settings(environment="test", database_path=self.root / "api.db",
                                  tenant_keys={"one": "secret-one"}, ai_provider="local"))
        client = TestClient(app)
        self.assertEqual(client.get("/v1/friday/workspace").status_code, 401)
        self.assertEqual(client.get("/v1/friday/workspace", headers={"X-Carapace-Tenant": "two",
                                  "X-Carapace-API-Key": "secret-one"}).status_code, 401)
        response = client.get("/v1/friday/workspace", headers={"X-Carapace-Tenant": "one",
                              "X-Carapace-API-Key": "secret-one"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["read_only"])

    def test_cloud_workspace_allowlist_preserves_identity_and_read_only_method(self):
        settings = WebSettings("https://private-api.run.app", "https://friday-web.run.app",
                               "/projects/123/locations/asia-south1/services/friday-web",
                               {"one@example.com": "one"}, {"one": "secret-one"})
        transport = Mock(return_value=(200, {"read_only": True}))
        client = TestClient(create_cloud_web(settings, verifier=lambda token, audience: {"email": token},
                                            transport=transport, html="<h1>Friday</h1>"))
        headers = {"X-Goog-Iap-Jwt-Assertion": "one@example.com", "Origin": settings.public_origin,
                   "X-Carapace-Tenant": "attacker"}
        self.assertEqual(client.get("/api/friday/workspace", headers=headers).status_code, 200)
        self.assertEqual(transport.call_args.args[1:4], ("one", "/v1/friday/workspace", "GET"))
        self.assertEqual(client.post("/api/friday/workspace", headers=headers, json={}).status_code, 404)
        self.assertEqual(client.get("/api/friday/workspace?tenant=two", headers=headers).status_code, 400)
        self.assertEqual(transport.call_count, 1)
