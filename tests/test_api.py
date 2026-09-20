from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from carapace_api.config import Settings
from carapace_api.factory import create_app


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    with (ROOT / "examples" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class AssuranceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        settings = Settings(
            environment="test",
            database_path=Path(self.temporary_directory.name) / "evidence.db",
            tenant_keys={"bank-a": "key-a", "bank-b": "key-b"},
        )
        self.client = TestClient(create_app(settings=settings))
        self.bank_a = {
            "X-Carapace-Tenant": "bank-a",
            "X-Carapace-API-Key": "key-a",
        }
        self.bank_b = {
            "X-Carapace-Tenant": "bank-b",
            "X-Carapace-API-Key": "key-b",
        }

    def tearDown(self) -> None:
        self.client.close()
        self.temporary_directory.cleanup()

    def create_contract(self) -> dict:
        contract = load_example("payment-promise.json")
        response = self.client.post(
            "/v1/contracts", json=contract, headers=self.bank_a
        )
        self.assertEqual(response.status_code, 201, response.text)
        return contract

    def test_health_is_public_and_ready(self) -> None:
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_ai_status_truthfully_reports_local_fallback(self) -> None:
        response = self.client.get("/v1/ai/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "LOCAL_RULES")
        self.assertEqual(response.json()["status"], "LOCAL_READY")
        self.assertFalse(response.json()["cloud_project_configured"])
        self.assertFalse(response.json()["external_ai_configured"])

    def test_contract_endpoint_requires_authentication(self) -> None:
        response = self.client.post(
            "/v1/contracts", json=load_example("payment-promise.json")
        )
        self.assertEqual(response.status_code, 401)

    def test_fee_shield_detects_customer_mdr_surcharge(self) -> None:
        response = self.client.post(
            "/v1/fees/upi/assess",
            headers=self.bank_a,
            json={
                "amount_minor": 1_000_000,
                "initiated_on": "2026-10-15",
                "payment_kind": "P2M",
                "customer_mdr_surcharge_minor": 4_000,
                "actual_merchant_mdr_minor": 4_000,
                "sector": "STANDARD",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["expected_mdr_minor"], 4_000)
        self.assertEqual(response.json()["verdict"], "VIOLATION")
        self.assertIn(
            "CUSTOMER_MDR_SURCHARGE_PROHIBITED",
            response.json()["violations"],
        )

    def test_public_lens_finds_exact_refund_payment_contradiction(self) -> None:
        response = self.client.post(
            "/v1/lens/analyze",
            json={
                "message_text": (
                    "ABC Support: Urgent! We are refunding ₹4,999. "
                    "Scan this QR and enter your UPI PIN now."
                ),
                "payment_uri": (
                    "upi://pay?pa=rktraders@upi&pn=R%20K%20Traders"
                    "&am=4999&cu=INR"
                ),
                "locale": "en-IN",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["decision"], "STOP")
        self.assertEqual(body["intent"]["expected_direction"], "RECEIVE_EXPECTED")
        self.assertEqual(body["payment"]["direction"], "SEND")
        self.assertEqual(body["payment"]["amount_minor"], 499_900)
        self.assertEqual(body["provenance"]["mode"], "LOCAL_RULES")
        self.assertFalse(body["provenance"]["ai_is_authority"])
        self.assertFalse(body["provenance"]["input_redaction_applied"])
        codes = {finding["code"] for finding in body["findings"]}
        self.assertIn("DIRECTION_CONTRADICTION", codes)

    def test_lens_redacts_a_supplied_secret_before_provider_analysis(self) -> None:
        response = self.client.post(
            "/v1/lens/analyze",
            json={
                "message_text": "ABC Support: refund ₹4,999. UPI PIN is 1234. Scan now.",
                "payment_uri": "upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["provenance"]["input_redaction_applied"])
        self.assertEqual(response.json()["decision"], "STOP")

    def test_lens_rejects_non_upi_request(self) -> None:
        response = self.client.post(
            "/v1/lens/analyze",
            json={
                "message_text": "Please pay ₹100",
                "payment_uri": "https://example.com/pay",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_contract_is_isolated_by_tenant(self) -> None:
        contract = self.create_contract()
        own_response = self.client.get(
            f"/v1/contracts/{contract['contract_id']}", headers=self.bank_a
        )
        other_response = self.client.get(
            f"/v1/contracts/{contract['contract_id']}", headers=self.bank_b
        )
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_invalid_contract_digest_is_rejected_before_storage(self) -> None:
        contract = load_example("payment-promise.json")
        contract["payment"]["amount_minor"] += 1
        response = self.client.post(
            "/v1/contracts", json=contract, headers=self.bank_a
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"], "CONTRACT_REQUEST_HASH_INVALID"
        )

    def test_valid_run_is_stored_without_case(self) -> None:
        self.create_contract()
        evidence = load_example("execution-valid.json")
        response = self.client.post(
            f"/v1/contracts/{evidence['contract_id']}/runs",
            json=evidence,
            headers=self.bank_a,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["report"]["verdict"], "MATCH")
        self.assertIsNone(body["case_id"])
        self.assertEqual(
            body["receipt"]["assurance_level"], "SETTLEMENT_CONFIRMED"
        )

        saved = self.client.get(
            f"/v1/runs/{evidence['run_id']}", headers=self.bank_a
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["report"]["verdict"], "MATCH")
        self.assertEqual(
            saved.json()["receipt"]["receipt_id"],
            body["receipt"]["receipt_id"],
        )

        receipt_id = body["receipt"]["receipt_id"]
        receipt = self.client.get(
            f"/v1/receipts/{receipt_id}", headers=self.bank_a
        )
        hidden = self.client.get(
            f"/v1/receipts/{receipt_id}", headers=self.bank_b
        )
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(receipt.json()["run_id"], evidence["run_id"])
        self.assertEqual(hidden.status_code, 404)

    def test_duplicate_debit_creates_retrievable_evidence_case(self) -> None:
        self.create_contract()
        evidence = load_example("execution-duplicate-debit.json")
        response = self.client.post(
            f"/v1/contracts/{evidence['contract_id']}/runs",
            json=evidence,
            headers=self.bank_a,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["report"]["verdict"], "MISMATCH")
        self.assertIsNotNone(body["case_id"])
        self.assertEqual(body["receipt"]["assurance_level"], "MISMATCH")

        case = self.client.get(
            f"/v1/cases/{body['case_id']}", headers=self.bank_a
        )
        self.assertEqual(case.status_code, 200)
        self.assertEqual(case.json()["status"], "OPEN")
        self.assertIn(
            "AT_MOST_ONE_POSTED_DEBIT", case.json()["failed_checks"]
        )

        analysis = self.client.post(
            f"/v1/cases/{body['case_id']}/analyze", headers=self.bank_a
        )
        self.assertEqual(analysis.status_code, 200, analysis.text)
        proof = analysis.json()
        self.assertEqual(proof["verification_status"], "COUNTERFACTUAL_VERIFIED")
        self.assertEqual(
            proof["counterfactual_search"]["counterfactual_verdict"], "MATCH"
        )
        self.assertEqual(
            proof["counterfactual_search"]["minimal_interventions"],
            ["DEDUPLICATE_LOGICAL_DEBITS"],
        )
        self.assertFalse(proof["release_authorized"])
        self.assertTrue(proof["human_approval_required"])

        hidden_analysis = self.client.post(
            f"/v1/cases/{body['case_id']}/analyze", headers=self.bank_b
        )
        self.assertEqual(hidden_analysis.status_code, 404)

    def test_duplicate_run_id_is_rejected(self) -> None:
        self.create_contract()
        evidence = load_example("execution-valid.json")
        first = self.client.post(
            f"/v1/contracts/{evidence['contract_id']}/runs",
            json=evidence,
            headers=self.bank_a,
        )
        second = self.client.post(
            f"/v1/contracts/{evidence['contract_id']}/runs",
            json=evidence,
            headers=self.bank_a,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)


if __name__ == "__main__":
    unittest.main()
