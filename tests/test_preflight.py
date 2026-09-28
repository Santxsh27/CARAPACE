from __future__ import annotations

import base64
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from fastapi.testclient import TestClient

from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_api.preflight import PreflightGate
from carapace_api.preflight_evidence import PreflightEvidenceLog
from carapace_api.test_delivery_worker import TestDeliveryWorker
from carapace_ai.incident_reasoning import LocalIncidentReasoningProvider
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_integrations.anthos_preflight_bridge import validate_bridge_input
from carapace_core.lens import IntentDirection, MessageIntent
from carapace_core.checkpoint_monitor import CheckpointRejected, verify_checkpoint_response
from carapace_core.protection_proof import verify_protection_bundle


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
        self.device_id = "test_device_12345"
        self.device_key = ec.generate_private_key(ec.SECP256R1())
        device_spki = self.device_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        enrolled = self.client.post(
            "/v1/preflight/devices", headers=self.bank_a,
            json={"payer_account": "1000000001", "device_id": self.device_id,
                  "public_key_spki_base64": base64.b64encode(device_spki).decode()},
        )
        self.assertEqual(enrolled.status_code, 201, enrolled.text)

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

    def signed_choice(
        self, order_id: str, *, choice: str = "PROCEED", key: ec.EllipticCurvePrivateKey | None = None,
    ) -> tuple[dict, str]:
        response = self.client.get(
            f"/v1/preflight/orders/{order_id}/acknowledgement-challenge",
            headers=self.bank_a, params={"device_id": self.device_id, "choice": choice},
        )
        self.assertEqual(response.status_code, 200, response.text)
        statement_json = response.json()["statement_json"]
        der = (key or self.device_key).sign(statement_json.encode(), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        signature = base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
        return response.json(), signature

    def confirm(self, order_id: str, *, choice: str = "PROCEED") -> dict:
        challenge, signature = self.signed_choice(order_id, choice=choice)
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/acknowledge", headers=self.bank_a,
            json={"device_id": self.device_id, "choice": choice,
                  "statement_json": challenge["statement_json"],
                  "signature_base64": signature},
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

    def test_warn_requires_signed_proceed_before_synthetic_posting(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "", image=True)
        self.assertEqual(decision["verdict"], "WARN")
        url = f"/v1/preflight/orders/{order_id}/submit"
        self.assertEqual(
            self.client.post(url, headers=self.bank_a, json={"decision_id": decision["decision_id"]}).status_code,
            409,
        )
        choice = self.confirm(order_id)
        self.assertEqual(choice["choice_recorded"], "PROCEED")
        posted = self.client.post(url, headers=self.bank_a, json={"decision_id": decision["decision_id"]})
        self.assertEqual(posted.status_code, 200, posted.text)
        self.assertEqual(posted.json()["protection_bundle"]["receipt"]["customer_choice"], "PROCEED")

    def test_hold_cannot_be_overridden_even_by_valid_device_key(self) -> None:
        order = self.order()["envelope"]
        order_id = order["order_id"]
        decision = self.evaluate(order_id, "Refund ₹4,999 to you.")
        self.assertEqual(decision["verdict"], "HOLD")
        response = self.client.get(
            f"/v1/preflight/orders/{order_id}/acknowledgement-challenge",
            headers=self.bank_a, params={"device_id": self.device_id, "choice": "PROCEED"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("HOLD", response.text)
        self.confirm(order_id, choice="CANCEL")
        self.assertEqual(
            self.client.post(
                f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
                json={"decision_id": decision["decision_id"]},
            ).status_code,
            409,
        )

    def test_forged_or_changed_device_statement_cannot_record_choice(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        challenge, forged_signature = self.signed_choice(
            order_id, key=ec.generate_private_key(ec.SECP256R1()),
        )
        url = f"/v1/preflight/orders/{order_id}/acknowledge"
        forged = self.client.post(
            url, headers=self.bank_a,
            json={"device_id": self.device_id, "choice": "PROCEED",
                  "statement_json": challenge["statement_json"],
                  "signature_base64": forged_signature},
        )
        self.assertEqual(forged.status_code, 409)
        self.assertIn("signature", forged.text)
        changed = json.loads(challenge["statement_json"])
        changed["amount_minor"] = 1
        der = self.device_key.sign(
            json.dumps(changed, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(),
            ec.ECDSA(hashes.SHA256()),
        )
        r, s = decode_dss_signature(der)
        response = self.client.post(
            url, headers=self.bank_a,
            json={"device_id": self.device_id, "choice": "PROCEED",
                  "statement_json": json.dumps(changed, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                  "signature_base64": base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("differs", response.text)
        recorded = self.confirm(order_id)
        self.assertEqual(recorded["choice_recorded"], "PROCEED")
        challenge, signature = self.signed_choice(order_id)
        repeated = self.client.post(
            url, headers=self.bank_a,
            json={"device_id": self.device_id, "choice": "PROCEED",
                  "statement_json": challenge["statement_json"], "signature_base64": signature},
        )
        self.assertEqual(repeated.status_code, 409)

    def test_signed_cancel_never_authorizes_payment(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        self.confirm(order_id, choice="CANCEL")
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"], [])

    def test_enrolled_device_key_cannot_be_silently_replaced(self) -> None:
        replacement = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        response = self.client.post(
            "/v1/preflight/devices", headers=self.bank_a,
            json={"payer_account": "1000000001", "device_id": self.device_id,
                  "public_key_spki_base64": base64.b64encode(replacement).decode()},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already enrolled", response.text)

    def test_changed_acknowledgement_receipt_blocks_submission(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        acknowledged = self.confirm(order_id)
        receipt_id = acknowledged["protection_bundle"]["receipt"]["receipt_id"]
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT receipt_json FROM preflight_receipts WHERE receipt_id=?", (receipt_id,),
            ).fetchone()
            receipt = json.loads(row[0])
            receipt["choice"] = "CANCEL"
            connection.execute(
                "UPDATE preflight_receipts SET receipt_json=? WHERE receipt_id=?",
                (json.dumps(receipt), receipt_id),
            )
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"], [])

    def test_corrupt_witness_rolls_back_browser_choice(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        challenge, signature = self.signed_choice(order_id)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_witness_heads SET witness_signature='corrupt' WHERE tree_size=1"
            )
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/acknowledge", headers=self.bank_a,
            json={"device_id": self.device_id, "choice": "PROCEED",
                  "statement_json": challenge["statement_json"],
                  "signature_base64": signature},
        )
        self.assertEqual(response.status_code, 503)
        with sqlite3.connect(self.db_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM preflight_acknowledgements").fetchone()[0]
        self.assertEqual(count, 0)

    def test_genuine_bill_posts_once_and_replay_is_blocked(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(
            order_id, "Example Power bill 7782: Pay ₹4,999 to Example Power.", image=True
        )
        self.assertEqual(decision["verdict"], "ALLOW")
        url = f"/v1/preflight/orders/{order_id}/submit"
        self.assertEqual(
            self.client.post(url, headers=self.bank_a, json={"decision_id": decision["decision_id"]}).status_code,
            409,
        )
        self.confirm(order_id)
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

    def test_warning_and_posting_get_separately_signed_inclusion_proofs(self) -> None:
        keys = self.client.get("/v1/preflight/public-keys", headers=self.bank_a).json()
        pinned = {
            "bank_public_key": base64.b64decode(keys["bank"]["ed25519_public_key_base64"]),
            "witness_public_key": base64.b64decode(keys["witness"]["ed25519_public_key_base64"]),
        }
        self.assertNotEqual(pinned["bank_public_key"], pinned["witness_public_key"])
        blocked_order = self.order()["envelope"]["order_id"]
        blocked = self.evaluate(blocked_order, "Example Power refund ₹4,999: scan to receive.")
        first_bundle = blocked["protection_bundle"]
        self.assertTrue(verify_protection_bundle(first_bundle, **pinned))
        self.assertEqual(first_bundle["receipt"]["acknowledgement_state"], "NOT_ACKNOWLEDGED")
        self.assertEqual(first_bundle["receipt"]["verdict"], "HOLD")
        self.assertEqual(first_bundle["tree_head"]["tree_size"], 1)
        tampered = copy.deepcopy(first_bundle)
        tampered["receipt"]["issued_warning"] = "No warning"
        self.assertFalse(verify_protection_bundle(tampered, **pinned))
        self.assertEqual(
            self.client.get(
                f"/v1/preflight/receipts/{first_bundle['receipt']['receipt_id']}",
                headers=self.bank_b,
            ).status_code,
            404,
        )

        allowed_order = self.order()["envelope"]["order_id"]
        allowed = self.evaluate(allowed_order, "Example Power bill: Pay ₹4,999 to Example Power.")
        acknowledgement = self.confirm(allowed_order)
        self.assertTrue(verify_protection_bundle(acknowledgement["protection_bundle"], **pinned))
        result = self.client.post(
            f"/v1/preflight/orders/{allowed_order}/submit",
            headers=self.bank_a,
            json={"decision_id": allowed["decision_id"]},
        )
        self.assertEqual(result.status_code, 200, result.text)
        posting = result.json()["protection_bundle"]
        self.assertTrue(verify_protection_bundle(posting, **pinned))
        self.assertEqual(posting["receipt"]["transfer_id"], result.json()["transfer"]["transfer_id"])
        self.assertEqual(posting["receipt"]["stage"], "SYNTHETIC_POSTING")
        self.assertEqual(posting["tree_head"]["tree_size"], 4)
        old_again = self.client.get(
            f"/v1/preflight/receipts/{first_bundle['receipt']['receipt_id']}",
            headers=self.bank_a,
        ).json()
        self.assertTrue(old_again["local_proof_verified"])
        self.assertTrue(verify_protection_bundle(old_again["bundle"], **pinned))
        self.assertEqual(old_again["bundle"]["tree_head"]["tree_size"], 4)

    def test_public_checkpoint_proves_history_without_exposing_receipts(self) -> None:
        self.assertEqual(self.client.get("/v1/preflight/log/checkpoint").status_code, 404)
        key_info = self.client.get(
            "/v1/preflight/public-keys", headers=self.bank_a,
        ).json()
        witness_key = base64.b64decode(key_info["witness"]["ed25519_public_key_base64"])
        first_order = self.order()["envelope"]["order_id"]
        self.evaluate(first_order, "Example Power refund ₹4,999: scan to receive.")
        first_response = self.client.get("/v1/preflight/log/checkpoint")
        self.assertEqual(first_response.status_code, 200, first_response.text)
        self.assertNotIn("payer_account", first_response.text)
        self.assertNotIn("issued_warning", first_response.text)
        saved = verify_checkpoint_response(
            first_response.json(), previous_state=None, witness_public_key=witness_key,
        )
        second_order = self.order()["envelope"]["order_id"]
        self.evaluate(second_order, "Example Power bill: Pay ₹4,999 to Example Power.")
        next_response = self.client.get(
            "/v1/preflight/log/checkpoint", params={"from_size": 1},
        )
        self.assertEqual(next_response.status_code, 200, next_response.text)
        newer = verify_checkpoint_response(
            next_response.json(), previous_state=saved, witness_public_key=witness_key,
        )
        self.assertEqual(newer["head"]["tree_size"], 2)
        self.assertEqual(
            self.client.get("/v1/preflight/log/checkpoint", params={"from_size": 3}).status_code,
            422,
        )
        tampered = copy.deepcopy(next_response.json())
        tampered["previous_head"]["root_hash"] = "00" * 32
        with self.assertRaises(CheckpointRejected):
            verify_checkpoint_response(
                tampered, previous_state=saved, witness_public_key=witness_key,
            )

    def test_corrupt_checkpoint_is_not_published_as_valid(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_witness_heads SET witness_signature='corrupt' WHERE tree_size=1"
            )
        response = self.client.get("/v1/preflight/log/checkpoint")
        self.assertEqual(response.status_code, 503)

    def test_synthetic_posting_coverage_audit_detects_missing_evidence(self) -> None:
        empty = self.client.get("/v1/preflight/audit", headers=self.bank_a)
        self.assertEqual(empty.json()["status"], "NO_POSTINGS")
        self.assertEqual(
            self.client.get("/v1/preflight/audit").status_code, 401,
        )
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(
            order_id, "Example Power bill: Pay ₹4,999 to Example Power.",
        )
        self.confirm(order_id)
        submitted = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        passed = self.client.get("/v1/preflight/audit", headers=self.bank_a)
        self.assertEqual(passed.status_code, 200, passed.text)
        self.assertEqual(passed.json()["status"], "PASS")
        self.assertEqual(passed.json()["observed_transfer_count"], 1)
        self.assertEqual(
            self.client.get("/v1/preflight/audit", headers=self.bank_b).json()["status"],
            "NO_POSTINGS",
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "DELETE FROM preflight_receipts WHERE receipt_id=?",
                (submitted.json()["protection_bundle"]["receipt"]["receipt_id"],),
            )
        failed = self.client.get("/v1/preflight/audit", headers=self.bank_a)
        self.assertEqual(failed.json()["status"], "FAIL")
        self.assertIn(
            "POSTING_RECEIPT_COUNT_MISMATCH",
            {item["code"] for item in failed.json()["issues"]},
        )

    def test_synthetic_posting_audit_detects_changed_amount(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(
            order_id, "Example Power bill: Pay ₹4,999 to Example Power.",
        )
        self.confirm(order_id)
        submitted = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_transfers SET amount_minor=499901 WHERE order_id=?",
                (order_id,),
            )
        failed = self.client.get("/v1/preflight/audit", headers=self.bank_a).json()
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn(
            "POSTING_FIELDS_DIFFER_FROM_BANK_ORDER",
            {item["code"] for item in failed["issues"]},
        )

    def test_corrupt_witness_fails_closed_without_saving_next_decision(self) -> None:
        first_order = self.order()["envelope"]["order_id"]
        self.evaluate(first_order, "Example Power bill: Pay ₹4,999 to Example Power.")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_witness_heads SET witness_signature='corrupt' WHERE tree_size=1"
            )
        second_order = self.order()["envelope"]["order_id"]
        response = self.client.post(
            f"/v1/preflight/orders/{second_order}/evaluate",
            headers=self.bank_a,
            json={"context_text": "Example Power bill: Pay ₹4,999 to Example Power."},
        )
        self.assertEqual(response.status_code, 503)
        with sqlite3.connect(self.db_path) as connection:
            stored = connection.execute(
                "SELECT decision_json FROM preflight_orders WHERE order_id=?",
                (second_order,),
            ).fetchone()
        self.assertIsNone(stored[0])

    def test_corrupt_witness_rolls_back_allowed_synthetic_transfer(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        self.assertEqual(decision["verdict"], "ALLOW")
        self.confirm(order_id)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_witness_heads SET witness_signature='corrupt' WHERE tree_size=2"
            )
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit",
            headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"],
            [],
        )

    def test_test_delivery_outbox_is_atomic_and_tenant_scoped(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        self.confirm(order_id)
        submitted = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        transfer_id = submitted.json()["transfer"]["transfer_id"]
        delivery = self.client.get(
            f"/v1/preflight/test-deliveries/{transfer_id}", headers=self.bank_a,
        )
        self.assertEqual(delivery.json()["status"], "PENDING")
        self.assertFalse(delivery.json()["bridge_configured"])
        self.assertEqual(
            self.client.get(
                f"/v1/preflight/test-deliveries/{transfer_id}", headers=self.bank_b,
            ).status_code, 404,
        )
        self.assertEqual(
            self.client.post(
                f"/v1/preflight/test-deliveries/{transfer_id}/attempt", headers=self.bank_a,
            ).status_code, 503,
        )
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT posting_receipt_id FROM preflight_test_deliveries WHERE transfer_id=?",
                (transfer_id,),
            ).fetchone()
        self.assertEqual(
            row[0], submitted.json()["protection_bundle"]["receipt"]["receipt_id"],
        )

    def test_failed_outbox_insert_rolls_back_money_and_posting_proof(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        self.confirm(order_id)
        with sqlite3.connect(self.db_path) as connection:
            before = connection.execute("SELECT COUNT(*) FROM preflight_witness_leaves").fetchone()[0]
            connection.execute(
                "CREATE TRIGGER reject_test_delivery BEFORE INSERT ON preflight_test_deliveries "
                "BEGIN SELECT RAISE(ABORT, 'test outbox failure'); END"
            )
        response = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        )
        self.assertEqual(response.status_code, 409)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM preflight_transfers").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM preflight_test_deliveries").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM preflight_witness_leaves").fetchone()[0], before)

    def test_worker_replays_after_failure_and_restart_without_new_posting(self) -> None:
        order_id = self.order()["envelope"]["order_id"]
        decision = self.evaluate(order_id, "Example Power bill: Pay ₹4,999 to Example Power.")
        self.confirm(order_id)
        submitted = self.client.post(
            f"/v1/preflight/orders/{order_id}/submit", headers=self.bank_a,
            json={"decision_id": decision["decision_id"]},
        ).json()
        transfer_id = submitted["transfer"]["transfer_id"]
        bank = BankEnvelopeSigner(Path(self.temporary.name) / "bank-dev-ed25519.pem", allow_generate=False)
        witness = BankEnvelopeSigner(Path(self.temporary.name) / "witness-dev-ed25519.pem", allow_generate=False)

        class FlakyTestBridge:
            calls = 0
            broken_readback = False

            def post_once_and_reconcile(self, transfer, bundle, *, bank_public_key, witness_public_key):
                validate_bridge_input(
                    transfer, bundle, bank_public_key=bank_public_key,
                    witness_public_key=witness_public_key,
                )
                self.calls += 1
                if self.calls == 1:
                    raise ConnectionError("local test ledger unavailable")
                return {"status": "MATCH", "anthos_transaction_id": 451,
                        "reason_codes": [], "inserted_now": self.calls == 2}

            def reconcile_existing(self, transfer, bundle, *, bank_public_key, witness_public_key):
                validate_bridge_input(
                    transfer, bundle, bank_public_key=bank_public_key,
                    witness_public_key=witness_public_key,
                )
                return {"status": "MISMATCH" if self.broken_readback else "MATCH",
                        "anthos_transaction_id": 451}

        bridge = FlakyTestBridge()
        def new_worker():
            return TestDeliveryWorker(
                PreflightGate(self.db_path), PreflightEvidenceLog(self.db_path, witness),
                bridge, bank_public_key=bank.public_key_bytes,
                witness_public_key=witness.public_key_bytes,
            )

        self.assertEqual(new_worker().attempt("bank-a", transfer_id)["status"], "UNAVAILABLE")
        self.assertEqual(PreflightGate(self.db_path).get_test_delivery("bank-a", transfer_id)["status"], "PENDING")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE preflight_test_deliveries SET next_attempt_at='2000-01-01T00:00:00+00:00' "
                "WHERE transfer_id=?", (transfer_id,),
            )
        self.assertEqual(new_worker().drain_once()[0]["status"], "MATCH")
        self.assertEqual(new_worker().attempt("bank-a", transfer_id)["anthos_transaction_id"], 451)
        status = self.client.get(
            f"/v1/preflight/test-deliveries/{transfer_id}", headers=self.bank_a,
        ).json()
        # This API instance has no bridge: a saved MATCH is not a fresh readback.
        self.assertEqual(status["status"], "UNVERIFIED")
        self.assertFalse(status["bridge_configured"])
        self.assertIsNone(status["anthos_transaction_id"])
        self.assertEqual(new_worker().status("bank-a", transfer_id)["status"], "MATCH")
        bridge.broken_readback = True
        self.assertEqual(new_worker().status("bank-a", transfer_id)["status"], "MISMATCH")
        self.assertEqual(len(self.client.get("/v1/preflight/transfers", headers=self.bank_a).json()["transfers"]), 1)
