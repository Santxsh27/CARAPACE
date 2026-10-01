from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from carapace_ai.financial_friday import (
    GeminiFinancialFridayPlanner,
    LocalFinancialFridayPlanner,
    deliberately_unsafe_subscription_candidate,
)
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_api.financial_friday import FinancialFridayService
from carapace_api.friday_inbox import FridayInbox
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.financial_friday import (
    FinancialEvidence,
    FinancialGoal,
    challenge_financial_program,
    safe_local_program,
    verify_financial_program,
)
from carapace_integrations.financial_friday_fixtures import load_case
from carapace_integrations.financial_friday_ui import FINANCIAL_FRIDAY_HTML


class FinancialFridayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "friday.db"
        self.signer = BankEnvelopeSigner(Path(self.temp.name) / "key.pem", allow_generate=True)
        self.service = FinancialFridayService(self.path, self.signer, LocalFinancialFridayPlanner())

    def tearDown(self):
        self.temp.cleanup()

    def payment_count(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT COUNT(*) FROM friday_payments").fetchone()[0]

    def test_proactive_intake_is_opt_in_deduplicated_and_never_pays(self):
        inbox = FridayInbox(self.service)
        inbox.arrive('a', 'genuine-bill')
        inbox.arrive('a', 'genuine-bill')
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['state'], 'QUEUED')
        inbox.watch('a', True)
        inbox.tick()
        result = inbox.read('a')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['state'], 'READY')
        self.assertEqual(inbox.read('b')['items'], [])
        self.assertEqual(self.payment_count(), 0)
        inbox.watch('a', False)
        inbox.arrive('a', 'recipient-swap')
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['state'], 'QUEUED')
        inbox.watch('a', True)
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['state'], 'ATTENTION')
        self.assertEqual(self.payment_count(), 0)

    def test_proactive_model_failure_is_visible_and_not_retried_forever(self):
        class BrokenPlanner:
            def plan(self, context):
                raise RuntimeError('offline')
        self.service.planner = BrokenPlanner()
        inbox = FridayInbox(self.service)
        inbox.watch('a', True)
        inbox.arrive('a', 'genuine-bill')
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['state'], 'UNAVAILABLE')
        self.assertEqual(self.payment_count(), 0)

    def test_genuine_bill_executes_once_and_reuses_signed_receipt(self):
        first = self.service.run("tenant-a", "genuine-bill")
        self.assertEqual(first["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(first["outcome"]["receipt"]["payload"]["amount_minor"], 199_900)
        self.assertTrue(self.signer.verify(
            first["outcome"]["receipt"]["payload"], first["outcome"]["receipt"]["signature"]
        ))
        second = self.service.run("tenant-a", "genuine-bill")
        self.assertEqual(second["status"], "ALREADY_COMPLETED")
        self.assertFalse(second["outcome"]["money_moved"])
        self.assertEqual(self.payment_count(), 1)

    def test_misleading_recurring_offer_is_repaired_to_one_time_option(self):
        result = self.service.run("tenant-a", "subscription-trap")
        self.assertEqual(result["status"], "COMPLETED_SYNTHETIC")
        payment = next(
            step for step in result["program"]["candidate"]["steps"]
            if step["action"] == "CREATE_ONE_TIME_PAYMENT"
        )
        self.assertEqual(payment["option_id"], "standard-one-time")
        self.assertEqual(payment["amount_minor"], 199_900)
        self.assertEqual(self.payment_count(), 1)

    def test_recurring_only_provider_is_held_without_relaxing_goal(self):
        result = self.service.run("tenant-a", "recurring-only")
        self.assertEqual(result["status"], "HELD")
        self.assertIn("WRONG_CADENCE", result["outcome"]["reason"])
        self.assertEqual(self.payment_count(), 0)

    def test_changed_recipient_is_held(self):
        result = self.service.run("tenant-a", "recipient-swap")
        self.assertEqual(result["status"], "HELD")
        self.assertIn("EVIDENCE_PAYEE_MISMATCH", result["outcome"]["reason"])
        self.assertEqual(self.payment_count(), 0)

    def test_unknown_outcome_is_reconciled_without_retry(self):
        result = self.service.run("tenant-a", "unknown-outcome")
        self.assertEqual(result["status"], "RECONCILED_COMPLETED")
        self.assertFalse(result["outcome"]["money_moved"])
        self.assertFalse(result["outcome"]["new_payment_created"])
        self.assertEqual(self.payment_count(), 0)

    def test_rejected_ai_plan_can_be_repaired_but_never_executes_first(self):
        class CorrectingPlanner(LocalFinancialFridayPlanner):
            mode = "VERTEX_AI"
            model_name = "fake-gemini"
            calls = 0

            def plan(self, context):
                self.calls += 1
                if self.calls == 1:
                    return deliberately_unsafe_subscription_candidate(context)
                self.assert_feedback(context)
                return super().plan(context)

            @staticmethod
            def assert_feedback(context):
                assert "RECURRING_FORBIDDEN" in context["validation_feedback"]

        planner = CorrectingPlanner()
        result = self.service.run("tenant-a", "genuine-bill", planner)
        self.assertEqual(planner.calls, 2)
        self.assertEqual(result["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(result["provenance"]["successful_model_calls"], 2)
        self.assertEqual(self.payment_count(), 1)

    def test_guard_rejects_every_adversarial_mutation(self):
        case = load_case("genuine-bill")
        goal = FinancialGoal.model_validate(case["goal"])
        evidence = FinancialEvidence.model_validate(case["evidence"])
        program = safe_local_program(goal, evidence)
        self.assertTrue(verify_financial_program(program, goal, evidence)["passed"])
        challenges = challenge_financial_program(program, goal, evidence)
        self.assertEqual(len(challenges), 6)
        self.assertTrue(all(item["rejected"] for item in challenges))

    def test_gemini_adapter_requests_typed_program_only(self):
        case = load_case("genuine-bill")
        goal = FinancialGoal.model_validate(case["goal"])
        evidence = FinancialEvidence.model_validate(case["evidence"])
        expected = safe_local_program(goal, evidence)
        calls = []

        def generate_content(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=expected.model_dump_json())

        planner = GeminiFinancialFridayPlanner(
            SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
            "gemini-test",
            "VERTEX_AI",
        )
        actual = planner.plan({"goal": goal.model_dump(), "evidence": evidence.model_dump()})
        self.assertEqual(actual, expected)
        self.assertEqual(calls[0]["config"].response_mime_type, "application/json")
        self.assertIn("steps", calls[0]["config"].response_json_schema["properties"])

    def test_api_is_tenant_isolated_and_rejects_extra_input(self):
        settings = Settings(
            environment="test",
            database_path=Path(self.temp.name) / "api.db",
            tenant_keys={"a": "key-a", "b": "key-b"},
        )
        with TestClient(create_app(settings=settings)) as client:
            a = {"X-Carapace-Tenant": "a", "X-Carapace-API-Key": "key-a"}
            b = {"X-Carapace-Tenant": "b", "X-Carapace-API-Key": "key-b"}
            scenarios = client.get("/v1/friday/scenarios", headers=a)
            self.assertEqual(scenarios.status_code, 200)
            self.assertEqual(scenarios.json()["product"], "Financial Friday")
            response = client.post(
                "/v1/friday/scenarios/genuine-bill/run",
                headers=a,
                json={"planner": "local"},
            )
            self.assertEqual(response.status_code, 200)
            run = response.json()
            self.assertEqual(run["status"], "COMPLETED_SYNTHETIC")
            self.assertEqual(client.get("/v1/friday/runs/" + run["run_id"], headers=b).status_code, 404)
            self.assertEqual(client.post(
                "/v1/friday/scenarios/genuine-bill/run", headers=a, json={"amount": 1}
            ).status_code, 422)

    def test_sandbox_ui_explains_ai_and_execution_boundaries(self):
        self.assertIn("Tell Friday the outcome. Not every step.", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Gemini can propose", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Independent safety proof", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Restricted sandbox · no real bank access", FINANCIAL_FRIDAY_HTML)
        self.assertIn("/api/friday/scenarios/", FINANCIAL_FRIDAY_HTML)


if __name__ == "__main__":
    unittest.main()
