from __future__ import annotations

import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_ai.incident_reasoning import LocalIncidentReasoningProvider
from carapace_core.lens import IntentDirection, MessageIntent


PNG_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9eJZAXYAAAAASUVORK5CYII="
)


class FakeContextProvider:
    provider_name = "fake-gemini-test"
    model_name = "fake-structured-model"
    mode = "GEMINI_API"

    def __init__(self) -> None:
        self.image_calls = 0
        self.fail = False

    def extract_intent(self, message_text: str, locale: str) -> MessageIntent:
        del locale
        if self.fail:
            raise RuntimeError("provider unavailable")
        refund = "refund" in message_text.lower()
        return MessageIntent(
            expected_direction=IntentDirection.RECEIVE_EXPECTED if refund else IntentDirection.SEND,
            expected_amount_minor=499900,
            currency="INR",
            claimed_entity="Example Power",
            urgency_detected=refund,
            asks_for_pin_to_receive=refund,
            summary="Test extraction",
            evidence_span="refund" if refund else "Pay",
        )

    def extract_intent_from_image(
        self, image_bytes: bytes, mime_type: str, message_text: str, locale: str
    ) -> MessageIntent:
        self.image_calls += 1
        assert image_bytes == PNG_PIXEL
        assert mime_type == "image/png"
        return self.extract_intent(message_text, locale)


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary.name) / "evidence.db"
        self.provider = FakeContextProvider()
        self.settings = Settings(
            environment="test",
            database_path=self.db_path,
            tenant_keys={"bank-a": "key-a", "bank-b": "key-b"},
        )
        self.client = TestClient(create_app(settings=self.settings, lens_provider=self.provider, incident_provider=LocalIncidentReasoningProvider()))
        self.bank_a = {"X-Carapace-Tenant": "bank-a", "X-Carapace-API-Key": "key-a"}
        self.bank_b = {"X-Carapace-Tenant": "bank-b", "X-Carapace-API-Key": "key-b"}

    def tearDown(self) -> None:
        self.client.close()
        self.temporary.cleanup()

    def order(self, payee_name: str = "Example Power") -> dict:
        response = self.client.post(
            "/v1/preflight/orders",
            headers=self.bank_a,
            json={
                "payer_account": "1000000001",
                "payee_account": "2000000002",
                "payee_display_name": payee_name,
                "amount_minor": 499900,
                "currency": "INR",
                "reference": "bill-7782",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def evaluate(self, order_id: str, context_text: str, *, image: bool = False) -> dict:
        payload = {"context_text": context_text}
        if image:
            payload["image_base64"] = base64.b64encode(PNG_PIXEL).decode()
            payload["image_mime_type"] = "image/png"
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/evaluate", headers=self.bank_a, json=payload
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_refund_screenshot_is_held_and_cannot_post(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(
            order_id, "Example Power: Your ₹4,999 refund is coming. Scan to receive it.", image=True
        )
        self.assertEqual(self.provider.image_calls, 1)
        self.assertEqual(decision["verdict"], "HOLD")
        self.assertTrue(decision["live_model_called"])
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit",
            headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)
        transfers = self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()
        self.assertEqual(transfers["transfers"], [])

    def test_image_only_claim_is_unverified_warn_not_a_grounded_hold(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "", image=True)
        self.assertEqual(decision["verdict"], "WARN")
        self.assertIn("IMAGE_TEXT_NOT_INDEPENDENTLY_GROUNDED", decision["reason_codes"])
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit",
            headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)

    def test_genuine_bill_posts_once_and_replay_is_blocked(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(
            order_id, "Example Power bill 7782: Pay ₹4,999 to Example Power.", image=True
        )
        self.assertEqual(decision["verdict"], "ALLOW")
        url = f"/v1/preflight/orders/{order_id}/submit"
        first = self.client.post(url, headers=self.bank_a, json={"decision_id": decision["decision_id"]})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["status"], "POSTED_SYNTHETIC")
        self.assertEqual(self.client.post(url, headers=self.bank_a, json={"decision_id": decision["decision_id"]}).status_code, 409)
        self.assertEqual(len(self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"]), 1)

    def test_claimed_payee_conflicts_with_signed_bank_payee(self) -> None:
        order_id = self.order("R K Traders")["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill 7782: Pay ₹4,999 to Example Power.")
        self.assertEqual(decision["verdict"], "HOLD")
        self.assertIn("CLAIMED_PAYEE_DIFFERS_FROM_BANK_PAYEE", decision["reason_codes"])
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit",
            headers=self.bank_a, json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)

    def test_tampered_bank_order_is_rejected(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute("SELECT envelope_json FROM preflight_orders WHERE order_id=?", (order_id,)).fetchone()
            envelope = json.loads(row[0])
            envelope["amount_minor"] = 999900
            connection.execute(
                "UPDATE preflight_orders SET envelope_json=? WHERE order_id=?",
                (json.dumps(envelope), order_id),
            )
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/evaluate",
            headers=self.bank_a,
            json={"context_text": "Pay ₹4,999"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("signature", response.text)

    def test_bank_isolation_and_auth(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        self.assertEqual(self.client.get(f"/v1/preflight/orders/{order_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/v1/preflight/orders/{order_id}", headers=self.bank_b).status_code, 404)
        self.assertEqual(self.client.get("/v1/preflight/transfers", headers=self.bank_b).json()["transfers"], [])

    def test_provider_failure_fails_closed_and_no_money_moves(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        self.provider.fail = True
        decision = self.evaluate(order_id, "Pay ₹4,999 to Example Power.")
        self.assertEqual(decision["verdict"], "HOLD")
        self.assertFalse(decision["live_model_called"])
        self.assertIn("CONTEXT_ANALYSIS_UNAVAILABLE", decision["reason_codes"])
        self.assertEqual(self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"], [])

    def test_changed_decision_cannot_authorize_money(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Refund ₹4,999 to you.")
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute("SELECT decision_json FROM preflight_orders WHERE order_id=?", (order_id,)).fetchone()
            changed = json.loads(row[0])
            changed["verdict"] = "ALLOW"
            connection.execute("UPDATE preflight_orders SET decision_json=? WHERE order_id=?", (json.dumps(changed), order_id))
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit",
            headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("signature", response.text)
