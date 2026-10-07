from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
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
from carapace_api.financial_friday import FinancialFridayService, FridayUnderstandingUnavailable
from carapace_api.friday_inbox import FridayInbox
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.financial_friday import (
    FinancialEvidence,
    FinancialGoal,
    challenge_financial_program,
    safe_local_program,
    verify_financial_program,
)
from carapace_core.friday_live import (
    FinancialEvidenceSpan,
    FridayMandate,
    IncomingFinancialSignal,
    InterpretedFinancialSignal,
    TestProviderBill,
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

    def test_understanding_transient_failure_retries_before_any_execution(self):
        error = RuntimeError("temporary provider failure")
        error.code = 504
        call = Mock(side_effect=[error, "interpreted"])
        self.assertEqual(self.service._understand(call), ("interpreted", 2))
        self.assertEqual(call.call_count, 2)
        self.assertEqual(self.payment_count(), 0)

    def test_completed_payment_replay_works_without_ai(self):
        first = self.service.run("tenant-a", "genuine-bill")
        self.service.planner.plan = Mock(side_effect=RuntimeError("AI is offline"))
        second = self.service.run("tenant-a", "genuine-bill")
        self.assertEqual(second["status"], "ALREADY_COMPLETED")
        self.assertEqual(first["outcome"]["receipt"], second["outcome"]["receipt"])
        self.assertEqual(second["provenance"]["successful_model_calls"], 0)
        self.service.planner.plan.assert_not_called()

    def test_corrupt_existing_receipt_is_held_without_ai(self):
        self.service.run("tenant-a", "genuine-bill")
        with self.service.connect() as db:
            db.execute("UPDATE friday_payments SET receipt_json=?", (json.dumps({"payload": {}, "signature": None}),))
        self.service.planner.plan = Mock(side_effect=RuntimeError("AI must not repair a receipt"))
        result = self.service.run("tenant-a", "genuine-bill")
        self.assertEqual(result["status"], "HELD")
        self.assertEqual(result["outcome"]["reason"], ["EXISTING_RECEIPT_INVALID"])
        self.service.planner.plan.assert_not_called()

    def test_non_json_existing_receipt_is_held(self):
        self.service.run("tenant-a", "genuine-bill")
        with self.service.connect() as db:
            db.execute("UPDATE friday_payments SET receipt_json='broken'")
        self.assertEqual(self.service.run("tenant-a", "genuine-bill")["status"], "HELD")

    def test_understanding_retries_are_bounded(self):
        error = RuntimeError("temporary provider failure")
        error.code = 503
        call = Mock(side_effect=error)
        with self.assertRaises(FridayUnderstandingUnavailable):
            self.service._understand(call)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(self.payment_count(), 0)

    def test_understanding_invalid_output_is_not_retried(self):
        call = Mock(side_effect=ValueError("invalid structured output"))
        with self.assertRaises(FridayUnderstandingUnavailable):
            self.service._understand(call)
        self.assertEqual(call.call_count, 1)

    def test_input_api_fails_closed_when_understanding_is_unavailable(self):
        settings = Settings(environment="test", database_path=Path(self.temp.name) / "api-failure.db",
                            tenant_keys={"tenant-a": "secret-a"}, ai_provider="local")
        app = create_app(settings=settings)
        app.state.financial_friday.planner.interpret_signal = Mock(side_effect=RuntimeError("provider unavailable"))
        with TestClient(app) as client:
            response = client.post("/v1/friday/live-input", headers={
                "X-Carapace-Tenant": "tenant-a", "X-Carapace-API-Key": "secret-a"},
                json={"source_type": "MESSAGE", "content_text": "Please read this new bill"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "10")
        self.assertIn("no payment was submitted", response.json()["detail"])

    class MemoryDurableState:
        mode = "FIRESTORE_HYBRID"

        def __init__(self):
            self.records = {}

        def put(self, kind, tenant, record_id, value):
            self.records[(kind, tenant, record_id)] = json.loads(json.dumps(value))

        def get(self, kind, tenant, record_id):
            return self.records.get((kind, tenant, record_id))

        def list(self, kind, tenant, limit=20):
            return [value for (k, t, _), value in self.records.items() if k == kind and t == tenant][:limit]

    def publish_live_bill(self, reference="LIVE-1001", amount=249_900):
        return self.service.publish_test_bill("tenant-a", TestProviderBill(
            bill_reference=reference,
            provider_name="TN Power",
            provider_id="tn-power-test",
            payee_id="tnpower@upi",
            amount_minor=amount,
            due_date="2026-10-04",
        ))

    def test_live_unfamiliar_message_is_grounded_and_executes_once(self):
        self.service.save_mandate("tenant-a", FridayMandate(
            instruction="Handle verified household bills and protect my reserve.",
            protected_balance_minor=1_000_000,
            automatic_payment_limit_minor=300_000,
        ))
        self.publish_live_bill()
        signal = IncomingFinancialSignal(
            source_type="MESSAGE",
            content_text="TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi",
        )
        checked = self.service.ingest_live_signal("tenant-a", signal)
        self.assertEqual(checked["state"], "READY")
        self.assertEqual(checked["interpretation"]["bill_reference"], "LIVE-1001")
        completed = self.service.run_live_signal("tenant-a", checked["event_id"])
        self.assertEqual(completed["run"]["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(completed["run"]["outcome"]["sandbox_balance_minor"], 4_750_100)
        repeated = self.service.ingest_live_signal("tenant-a", signal)
        self.assertEqual(repeated["event_id"], checked["event_id"])
        self.assertEqual(self.payment_count(), 1)

    def test_live_recipient_change_is_stopped_before_execution(self):
        self.publish_live_bill()
        result = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="QR_TEXT",
            content_text="TN Power bill LIVE-1001 for INR 2,499. Payee: attacker@upi",
        ))
        self.assertEqual(result["state"], "ATTENTION")
        self.assertIn("RECIPIENT_MISMATCH", result["reason"])
        with self.assertRaises(ValueError):
            self.service.run_live_signal("tenant-a", result["event_id"])
        self.assertEqual(self.payment_count(), 0)

    def test_live_provider_change_after_interpretation_is_held(self):
        self.publish_live_bill()
        signal = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="MESSAGE", content_text="TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi"))
        self.publish_live_bill(amount=299_900)
        result = self.service.run_live_signal("tenant-a", signal["event_id"])["run"]
        self.assertEqual(result["outcome"]["reason"], ["PROVIDER_CHANGED"])
        self.assertEqual(self.payment_count(), 0)

    def test_live_repeated_bill_in_different_message_pays_once(self):
        self.publish_live_bill()
        for prefix in ("", "Reminder: "):
            signal = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
                source_type="MESSAGE", content_text=prefix + "TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi"))
            self.service.run_live_signal("tenant-a", signal["event_id"])
        self.assertEqual(self.payment_count(), 1)

    def test_live_bill_can_complete_automatically_inside_saved_limits(self):
        self.service.save_mandate("tenant-a", FridayMandate(
            instruction="Automatically handle verified household bills within my limit.",
            protected_balance_minor=1_000_000,
            automatic_payment_limit_minor=300_000,
            automatic_sandbox_execution=True,
        ))
        self.publish_live_bill()
        result = self.service.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="VOICE_TRANSCRIPT",
            content_text="Please handle TN Power bill number LIVE-1001 for ₹2,499 recipient tnpower@upi",
        ))
        self.assertEqual(result["state"], "COMPLETED")
        self.assertTrue(result["money_moved"])
        self.assertEqual(self.payment_count(), 1)

    def test_document_is_ephemeral_grounded_and_cites_exact_evidence(self):
        class DocumentPlanner(LocalFinancialFridayPlanner):
            def interpret_document(self, mime_type, document_bytes, filename):
                self.seen = (mime_type, document_bytes, filename)
                return InterpretedFinancialSignal(
                    request_kind="BILL",
                    bill_reference="LIVE-1001",
                    provider_name="TN Power",
                    amount_minor=249_900,
                    claimed_payee_id="tnpower@upi",
                    summary="A bill was extracted from the uploaded document.",
                    evidence_spans=[
                        FinancialEvidenceSpan(field="bill_reference", quote="Bill LIVE-1001"),
                        FinancialEvidenceSpan(field="amount_minor", quote="₹2,499"),
                        FinancialEvidenceSpan(field="claimed_payee_id", quote="tnpower@upi"),
                    ],
                )

        planner = DocumentPlanner()
        self.service.planner = planner
        self.publish_live_bill()
        result = self.service.ingest_document(
            "tenant-a", "power-bill.png", "image/png", b"\x89PNG\r\n\x1a\nmock"
        )
        self.assertEqual(result["state"], "READY")
        self.assertFalse(result["document"]["raw_file_stored"])
        self.assertEqual(result["document"]["filename"], "power-bill.png")
        self.assertEqual(result["interpretation"]["evidence_spans"][1]["quote"], "₹2,499")
        self.assertEqual(planner.seen[2], "power-bill.png")
        with self.service.connect() as db:
            stored = db.execute("SELECT signal_json FROM friday_live_signals").fetchone()[0]
        self.assertNotIn("mock", stored)

    def test_firestore_phase_one_restores_evidence_but_never_resumes_payment(self):
        durable = self.MemoryDurableState()
        first = FinancialFridayService(self.path, self.signer, LocalFinancialFridayPlanner(), durable)
        first.save_mandate("tenant-a", FridayMandate(
            instruction="Handle verified household bills and protect my reserve.",
            protected_balance_minor=1_000_000,
            automatic_payment_limit_minor=300_000,
        ))
        first.publish_test_bill("tenant-a", TestProviderBill(
            bill_reference="LIVE-1001", provider_name="TN Power",
            provider_id="tn-power-test", payee_id="tnpower@upi",
            amount_minor=249_900, due_date="2026-10-04",
        ))
        checked = first.ingest_live_signal("tenant-a", IncomingFinancialSignal(
            source_type="MESSAGE",
            content_text="TN Power bill LIVE-1001 for ₹2,499. Payee: tnpower@upi",
        ))
        run = first.run("tenant-a", "genuine-bill")
        self.assertEqual(checked["state"], "READY")
        self.assertEqual(first.storage_status()["mode"], "FIRESTORE_HYBRID")
        self.assertEqual(run["status"], "HELD")
        self.assertEqual(run["outcome"]["reason"], ["PAYMENT_STATE_NOT_DURABLE"])
        with first.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM friday_payments").fetchone()[0], 0)

        restored_path = Path(self.temp.name) / "restored.db"
        restored = FinancialFridayService(
            restored_path, self.signer, LocalFinancialFridayPlanner(), durable
        )
        self.assertEqual(restored.mandate("tenant-a")["mandate"]["automatic_payment_limit_minor"], 300_000)
        self.assertEqual(restored.live_signals("tenant-a")["items"][0]["event_id"], checked["event_id"])
        self.assertEqual(restored.get("tenant-a", run["run_id"])["status"], "HELD")
        with self.assertRaisesRegex(ValueError, "payment execution stays disabled"):
            restored.run_live_signal("tenant-a", checked["event_id"])

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

    def test_expired_inbox_claim_recovers_without_payment(self):
        inbox = FridayInbox(self.service)
        inbox.watch('a', True)
        inbox.arrive('a', 'genuine-bill')
        with self.service.connect() as db:
            db.execute("UPDATE friday_inbox SET state='CHECKING', lease_until=1, attempts=1, claim_id='old'")
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['state'], 'READY')
        self.assertEqual(self.payment_count(), 0)

    def test_retry_is_tenant_scoped_and_capped(self):
        inbox = FridayInbox(self.service)
        inbox.arrive('a', 'genuine-bill')
        with self.service.connect() as db:
            db.execute("UPDATE friday_inbox SET state='UNAVAILABLE', attempts=2")
        with self.assertRaises(ValueError):
            inbox.retry('b', 'sample-genuine-bill')
        inbox.retry('a', 'sample-genuine-bill')
        inbox.watch('a', True)
        inbox.tick()
        with self.service.connect() as db:
            db.execute("UPDATE friday_inbox SET state='UNAVAILABLE'")
        with self.assertRaises(ValueError):
            inbox.retry('a', 'sample-genuine-bill')
        self.assertEqual(self.payment_count(), 0)

    def test_stale_worker_cannot_overwrite_new_claim(self):
        original = self.service.planner
        service = self.service
        class SlowPlanner:
            mode, model_name = original.mode, original.model_name
            def plan(self, context):
                with service.connect() as db:
                    db.execute("UPDATE friday_inbox SET claim_id='new-owner', state='READY', result='{}'")
                return original.plan(context)
        service.planner = SlowPlanner()
        inbox = FridayInbox(service)
        inbox.watch('a', True)
        inbox.arrive('a', 'genuine-bill')
        inbox.tick()
        self.assertEqual(inbox.read('a')['items'][0]['result'], {})

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
        class PlannerMustNotRun:
            mode = "VERTEX_AI"
            model_name = "gemini-test"

            def plan(self, context):
                raise AssertionError("identity contradiction must stop before AI")

        result = self.service.run("tenant-a", "recipient-swap", PlannerMustNotRun())
        self.assertEqual(result["status"], "HELD")
        self.assertIn("EVIDENCE_PAYEE_MISMATCH", result["outcome"]["reason"])
        self.assertEqual(result["events"][0]["type"], "DETERMINISTIC_EVIDENCE_HOLD")
        self.assertEqual(result["provenance"]["successful_model_calls"], 0)
        self.assertEqual(self.payment_count(), 0)

    def test_transient_vertex_error_is_retried_then_executes(self):
        local = LocalFinancialFridayPlanner()

        class TransientPlanner:
            mode = "VERTEX_AI"
            model_name = "gemini-test"
            calls = 0

            def plan(self, context):
                self.calls += 1
                if self.calls == 1:
                    ServerError = type("ServerError", (Exception,), {})
                    raise ServerError("temporary provider failure")
                return local.plan(context)

        planner = TransientPlanner()
        result = self.service.run("tenant-a", "genuine-bill", planner)
        self.assertEqual(result["status"], "COMPLETED_SYNTHETIC")
        self.assertEqual(planner.calls, 2)
        self.assertEqual(result["events"][0]["type"], "AI_PROVIDER_RETRY")
        self.assertEqual(result["provenance"]["successful_model_calls"], 1)

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

    def test_gemini_document_adapter_uses_multimodal_typed_output(self):
        expected = InterpretedFinancialSignal(
            request_kind="BILL",
            bill_reference="LIVE-1001",
            amount_minor=249_900,
            summary="The uploaded bill contains a supported amount and reference.",
            evidence_spans=[
                FinancialEvidenceSpan(field="bill_reference", quote="Bill LIVE-1001")
            ],
        )
        calls = []

        def generate_content(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=expected.model_dump_json())

        planner = GeminiFinancialFridayPlanner(
            SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
            "gemini-test",
            "VERTEX_AI",
        )
        actual = planner.interpret_document(
            "image/png", b"\x89PNG\r\n\x1a\nmock", "bill.png"
        )
        self.assertEqual(actual, expected)
        self.assertEqual(len(calls[0]["contents"]), 2)
        self.assertEqual(calls[0]["contents"][1].inline_data.mime_type, "image/png")
        schema = calls[0]["config"].response_json_schema
        self.assertIn("evidence_spans", schema["properties"])

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
            invalid = client.post(
                "/v1/friday/documents?filename=fake.png",
                headers={**a, "Content-Type": "image/png"},
                content=b"not-a-png",
            )
            self.assertEqual(invalid.status_code, 422)
            offline = client.post(
                "/v1/friday/documents?filename=bill.png",
                headers={**a, "Content-Type": "image/png"},
                content=b"\x89PNG\r\n\x1a\nmock",
            )
            self.assertEqual(offline.status_code, 200)
            self.assertEqual(offline.json()["state"], "ATTENTION")
            self.assertFalse(offline.json()["document"]["raw_file_stored"])

    def test_sandbox_ui_explains_ai_and_execution_boundaries(self):
        self.assertIn("Ask naturally. Friday understands the task", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Gemini can propose", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Independent safety proof", FINANCIAL_FRIDAY_HTML)
        self.assertIn("Artificial money only", FINANCIAL_FRIDAY_HTML)
        self.assertIn("/api/friday/scenarios/", FINANCIAL_FRIDAY_HTML)
        self.assertIn("See Friday think, prove and act", FINANCIAL_FRIDAY_HTML)
        for stage in ("understand", "ground", "plan", "prove", "act"):
            self.assertIn(f'data-stage="{stage}"', FINANCIAL_FRIDAY_HTML)
        self.assertIn("DETERMINISTIC_EVIDENCE_HOLD", FINANCIAL_FRIDAY_HTML)
        self.assertIn('id="metric-ai"', FINANCIAL_FRIDAY_HTML)
        self.assertIn('id="metric-effects"', FINANCIAL_FRIDAY_HTML)
        self.assertIn("Financial Friday", FINANCIAL_FRIDAY_HTML)
        self.assertIn('id="core-state"', FINANCIAL_FRIDAY_HTML)
        self.assertIn('id="document-input"', FINANCIAL_FRIDAY_HTML)
        self.assertIn("raw file not stored", FINANCIAL_FRIDAY_HTML)


if __name__ == "__main__":
    unittest.main()
