"""Atomic local acknowledgement without financial mutations or external claims."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient

from carapace_ai.financial_friday import LocalFinancialFridayPlanner
from carapace_api.financial_friday import FinancialFridayService
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_api.friday_followthrough import acknowledge_recorded_bill
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import sha256_hex
from carapace_core.friday_live import TestProviderBill


class FollowThroughTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.signer = BankEnvelopeSigner(root / "key.pem", allow_generate=True)
        self.service = FinancialFridayService(root / "db", self.signer, LocalFinancialFridayPlanner())
        self.bill = TestProviderBill(bill_reference="NEW-123", provider_name="Test power",
            provider_id="power", payee_id="power@upi", amount_minor=123400, due_date="2026-10-18")
        self.service.publish_test_bill("a", self.bill)
        self.goal = "goal-bill-" + sha256_hex({"tenant": "a", "provider": "power", "bill": "NEW-123"})[:24]

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, **overrides):
        payload = {"tenant_id": "a", "goal_id": self.goal, "provider_id": "power",
            "payee_id": "power@upi", "amount_minor": 123400, "currency": "INR",
            "scope": "FINANCIAL_FRIDAY_ARTIFICIAL_MONEY", "operation_id": "op-123"}
        payload.update(overrides)
        receipt = {"payload": payload, "signature": self.signer.sign(payload)}
        with self.service.connect() as db:
            db.execute("INSERT OR REPLACE INTO friday_payments VALUES (?,?,?,?)",
                ("a", self.goal, "idem", json.dumps(receipt)))

    def run_it(self):
        return acknowledge_recorded_bill(self.service, "a", "NEW-123")

    def test_missing_payment_never_implies_paid(self):
        self.assertEqual(self.run_it()["state"], "UNVERIFIED")

    def test_tenant_isolation(self):
        self.record()
        self.assertEqual(acknowledge_recorded_bill(self.service, "other", "NEW-123")["reason"], "BILL_NOT_FOUND")

    def test_signed_wrong_amount_still_held(self):
        self.record(amount_minor=1)
        self.assertEqual(self.run_it()["state"], "HOLD")

    def test_tampered_signature_held(self):
        self.record()
        with self.service.connect() as db:
            row = db.execute("SELECT receipt_json FROM friday_payments").fetchone()
            receipt = json.loads(row[0]); receipt["signature"] = "invalid"
            db.execute("UPDATE friday_payments SET receipt_json=?", (json.dumps(receipt),))
        self.assertEqual(self.run_it()["state"], "HOLD")

    def test_concurrent_acknowledgement_is_once_no_new_payment(self):
        self.record()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.run_it(), range(4)))
        self.assertEqual(sum(r["state"] == "ACKNOWLEDGED" for r in results), 1)
        self.assertTrue(all(not r["money_moved"] and not r["external_settlement_verified"] for r in results))
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM friday_payments").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM friday_bill_acknowledgements").fetchone()[0], 1)
        acknowledgement = results[0]["acknowledgement"]
        self.assertTrue(self.signer.verify(acknowledgement["payload"], acknowledgement["signature"]))

    def test_modified_receipt_does_not_reuse_old_acknowledgement(self):
        self.record(); self.run_it(); self.record(operation_id="op-other")
        self.assertEqual(self.run_it()["state"], "HOLD")

    def test_cloud_disabled_without_local_fallback(self):
        self.service.durable.mode = "FIRESTORE_TRANSACTIONAL"
        self.assertEqual(self.run_it()["reason"], "CLOUD_CONNECTOR_NOT_IMPLEMENTED")

    def test_tampered_acknowledgement_is_held(self):
        self.record(); self.run_it()
        with self.service.connect() as db:
            db.execute("UPDATE friday_bill_acknowledgements SET acknowledgement_json='{}'")
        self.assertEqual(self.run_it()["state"], "HOLD")

    def test_api_auth_and_rejects_client_supplied_receipt(self):
        app = create_app(Settings(environment="test", database_path=Path(self.tmp.name) / "api.db",
            tenant_keys={"a": "secret"}, ai_provider="local"))
        client = TestClient(app)
        self.assertEqual(client.post("/v1/friday/follow-through", json={"bill_reference": "NEW-123"}).status_code, 401)
        headers = {"X-Carapace-Tenant": "a", "X-Carapace-API-Key": "secret"}
        self.assertEqual(client.post("/v1/friday/follow-through", headers=headers,
            json={"bill_reference": "NEW-123", "receipt": {}}).status_code, 422)
        response = client.post("/v1/friday/follow-through", headers=headers, json={"bill_reference": "NEW-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "UNVERIFIED")
