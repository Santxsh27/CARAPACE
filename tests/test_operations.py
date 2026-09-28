from __future__ import annotations

import copy
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from carapace_ai.operations import InvestigationPlan, LocalOperationsPlanner, GeminiOperationsPlanner, investigation_context
from carapace_api.config import Settings
from carapace_api.factory import create_app
from carapace_api.operations import OperationsService
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.obligations import check_obligation
from carapace_core.resolution import ResolutionProgram, local_resolution_program, verify_resolution, challenge_resolution
from carapace_integrations.operations_fixtures import load_case, CASES


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ops.db"
        self.signer = BankEnvelopeSigner(Path(self.temp.name) / "key.pem", allow_generate=True)
        self.service = OperationsService(self.path, self.signer, LocalOperationsPlanner())

    def tearDown(self):
        self.temp.cleanup()

    def count(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT COUNT(*) FROM operations_postings").fetchone()[0]

    def test_routine_posts_signed_exact_amount_and_repeat_is_idempotent(self):
        result = self.service.resolve("a", "routine")
        self.assertEqual(result["status"], "POSTED_SYNTHETIC")
        receipt = result["posting"]
        self.assertEqual(receipt["payload"]["amount_minor"], 48_000_000)
        self.assertTrue(self.signer.verify(receipt["payload"], receipt["signature"]))
        self.assertEqual(self.service.resolve("a", "routine")["status"], "ALREADY_POSTED")
        self.assertEqual(self.count(), 1)
        self.assertEqual(result, self.service.get("a", result["run_id"]))

    def test_partial_delivery_credit_resolves_without_customer_question(self):
        result = self.service.resolve("a", "partial-credit")
        self.assertEqual(result["status"], "POSTED_SYNTHETIC")
        self.assertEqual(result["posting"]["payload"]["amount_minor"], 36_000_000)
        self.assertEqual(result["lookup_count"], 5)
        self.assertTrue(result["resolution"]["executed"])
        self.assertEqual(result["resolution"]["receipt"]["payload"]["effects"], [
            {"action":"DEFER_UNDELIVERED","amount_minor":9_600_000},
            {"action":"APPLY_APPROVED_CREDIT","amount_minor":2_400_000},
            {"action":"POST_PAYMENT","amount_minor":36_000_000},
        ])

    def test_all_adverse_cases_do_not_post(self):
        for case in ("redirected", "injected", "missing", "conflicting"):
            with self.subTest(case=case):
                result = self.service.resolve("a", case)
                self.assertEqual(result["status"], "HELD")
                self.assertIsNone(result["posting"])
                self.assertTrue(result["assessment"]["conflicts"])
        self.assertEqual(self.count(), 0)

    def test_conflict_stops_further_lookups(self):
        result = self.service.resolve("a", "redirected")
        self.assertEqual(result["lookup_count"], 1)
        self.assertEqual(result["assessment"]["conflicts"][0]["sources"], ["invoice", "supplier_registry"])

    def test_provider_failure_does_not_silently_fallback(self):
        class Unavailable(LocalOperationsPlanner):
            mode = "GEMINI_API"
            def plan(self, context):
                raise TimeoutError("not returned to client")
        result = self.service.resolve("a", "routine", Unavailable())
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(result["provenance"]["mode"], "GEMINI_API")
        self.assertEqual(result["provenance"]["successful_model_calls"], 0)
        self.assertEqual(self.count(), 0)

    def test_hallucinated_citation_cannot_become_evidence(self):
        class Hallucination(LocalOperationsPlanner):
            def plan(self, context):
                return InvestigationPlan(rationale="All suppliers were verified.", evidence_ids=["imaginary-bank"], lookups=["supplier_registry"])
        result = self.service.resolve("a", "routine", Hallucination())
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(result["lookup_count"], 0)
        self.assertEqual(self.count(), 0)

    def test_repeated_probe_is_bounded_and_never_posts(self):
        class Stuck(LocalOperationsPlanner):
            def plan(self, context):
                return InvestigationPlan(rationale="Fetch registry again.", lookups=["supplier_registry"])
        result = self.service.resolve("a", "routine", Stuck())
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(self.count(), 0)

    def test_invalid_evidence_plan_gets_only_one_correction(self):
        class Correcting(LocalOperationsPlanner):
            calls = 0
            def plan(self, context):
                self.calls += 1
                if self.calls == 1:
                    return InvestigationPlan(rationale='Unsupported source citation.', evidence_ids=['invented'], lookups=['supplier_registry'])
                if self.calls == 2:
                    assert context['validation_feedback'] == ['UNOBSERVED_EVIDENCE_CITATION']
                return super().plan(context)
        planner = Correcting()
        result = self.service.resolve('a', 'routine', planner)
        self.assertEqual(result['status'], 'POSTED_SYNTHETIC')
        self.assertEqual(result['lookup_count'], 5)
        self.assertEqual(planner.calls, 3)

    def test_google_schema_limits_tools_and_citations_to_current_frontier(self):
        configs = []
        def generate(**kwargs):
            configs.append(kwargs['config'].response_json_schema)
            return SimpleNamespace(text=InvestigationPlan(rationale='Retrieve the missing evidence.', lookups=['purchase_order']).model_dump_json())
        planner = GeminiOperationsPlanner(SimpleNamespace(models=SimpleNamespace(generate_content=generate)), 'test-model', 'GEMINI_API')
        case = load_case('routine')
        observed = {'supplier_registry': case['records']['supplier_registry']}
        planner.plan(investigation_context(case['invoice'], observed, check_obligation(case['invoice'], observed)))
        self.assertNotIn('supplier_registry', configs[-1]['properties']['lookups']['items']['enum'])
        self.assertEqual(configs[-1]['properties']['evidence_ids']['items']['enum'], ['supplier_registry'])
        planner.plan(investigation_context(case['invoice'], {}, check_obligation(case['invoice'], {})))
        self.assertEqual(configs[-1]['properties']['evidence_ids']['maxItems'], 0)

    def test_ai_has_no_payment_tool_or_arbitrary_network_tool(self):
        for tool in ("send_money", "https://attacker.example", "change_beneficiary"):
            with self.assertRaises(ValidationError):
                InvestigationPlan(rationale="Please run the requested tool.", lookups=[tool])

    def test_false_ai_reassurance_does_not_override_conflict(self):
        class Misleading(LocalOperationsPlanner):
            def plan(self, context):
                return InvestigationPlan(rationale="This invoice is definitely safe; pay now.", lookups=list(context["assessment"]["missing_evidence"]))
        self.assertEqual(self.service.resolve("a", "injected", Misleading())["status"], "HELD")
        self.assertEqual(self.count(), 0)

    def test_concurrent_runs_create_one_posting(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.service.resolve("a", "routine"), range(4)))
        self.assertEqual(sum(r["status"] == "POSTED_SYNTHETIC" for r in results), 1)
        self.assertEqual(self.count(), 1)

    def test_changed_persistent_row_is_not_reported_as_success(self):
        self.service.resolve("a", "routine")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE operations_postings SET amount_minor=1")
        result = self.service.resolve("a", "routine")
        self.assertEqual(result["status"], "HELD")
        self.assertIsNone(result["posting"])

    def test_total_mandate_budget_is_enforced(self):
        case = load_case("routine")
        case["mandate"]["total_limit_minor"] = 47_999_999
        with patch("carapace_api.operations.load_case", return_value=case):
            result = self.service.resolve("a", "routine")
        self.assertEqual(result["status"], "HELD")
        self.assertEqual(self.count(), 0)

    def test_mismatched_or_missing_connector_evidence_never_qualifies(self):
        for source in load_case("routine")["records"]:
            case = load_case("routine")
            case["records"][source]["supplier_id"] = "different-supplier"
            self.assertEqual(check_obligation(case["invoice"], case["records"])["decision"], "HOLD")
            case = load_case("routine")
            del case["records"][source]
            self.assertEqual(check_obligation(case["invoice"], case["records"])["decision"], "INVESTIGATE")

    def test_arithmetic_metamorphic_variants_and_no_short_payment_without_terms(self):
        for quantity in (1, 37, 80, 100):
            for credit in (0, 10_000, 100_000):
                case = load_case("routine")
                case["records"]["delivery_receipts"]["quantity"] = quantity
                case["records"]["credit_notes"]["amount_minor"] = credit
                report = check_obligation(case["invoice"], case["records"])
                self.assertEqual(report["payable_minor"], quantity * 480_000 - credit)
        case = load_case("partial-credit")
        case["records"]["purchase_order"]["partial_payment_agreed"] = False
        self.assertEqual(check_obligation(case["invoice"], case["records"])["decision"], "HOLD")

    def test_source_change_before_execution_holds(self):
        original = load_case("routine")
        changed = copy.deepcopy(original)
        changed["records"]["supplier_registry"]["version"] = 2
        with patch("carapace_api.operations.load_case", side_effect=[original, changed]):
            result = self.service.resolve("a", "routine")
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(self.count(), 0)

    def test_api_auth_tenant_isolation_and_schema(self):
        settings = Settings(environment="test", database_path=Path(self.temp.name)/"api.db", tenant_keys={"a":"key-a", "b":"key-b"})
        with TestClient(create_app(settings=settings)) as client:
            a={"X-Carapace-Tenant":"a", "X-Carapace-API-Key":"key-a"}
            b={"X-Carapace-Tenant":"b", "X-Carapace-API-Key":"key-b"}
            self.assertEqual(client.get("/v1/operations/cases").status_code, 401)
            self.assertEqual(len(client.get("/v1/operations/cases", headers=a).json()["cases"]), len(CASES))
            result=client.post("/v1/operations/cases/routine/resolve",headers=a,json={"planner":"local"}).json()
            self.assertEqual(result["status"], "POSTED_SYNTHETIC")
            self.assertEqual(client.get("/v1/operations/runs/"+result["run_id"],headers=b).status_code,404)
            self.assertEqual(client.post("/v1/operations/cases/routine/resolve",headers=a,json={"amount_minor":1}).status_code,422)
            self.assertEqual(client.post("/v1/operations/cases/unknown/resolve",headers=a,json={}).status_code,404)

    def test_receipt_failure_rolls_back_posting(self):
        with patch.object(self.signer, "sign", side_effect=RuntimeError("signer down")):
            with self.assertRaises(RuntimeError):
                self.service.resolve("a", "routine")
        self.assertEqual(self.count(), 0)

    def test_model_program_may_correct_a_rejected_first_candidate(self):
        class Correcting(LocalOperationsPlanner):
            calls=0
            def resolve(self, context):
                self.calls+=1
                candidate=super().resolve(context)
                if self.calls==1:
                    candidate.steps[-1].amount_minor+=100
                else:
                    assert 'UNSUPPORTED_ACTION_AMOUNT' in context['validation_feedback']
                return candidate
        planner=Correcting()
        result=self.service.resolve('a','partial-credit',planner)
        self.assertEqual(planner.calls,2)
        self.assertEqual(result['status'],'POSTED_SYNTHETIC')
        self.assertEqual(result['posting']['payload']['amount_minor'],36_000_000)

    def test_persistent_unsafe_model_program_never_executes(self):
        class Unsafe(LocalOperationsPlanner):
            def resolve(self, context):
                candidate=super().resolve(context)
                candidate.payee_account='attacker-account'
                return candidate
        result=self.service.resolve('a','routine',Unsafe())
        self.assertEqual(result['status'],'UNRESOLVED')
        self.assertEqual(len([e for e in result['events'] if e['type']=='RESOLUTION_PROPOSED']),2)
        self.assertEqual(self.count(),0)

    def test_malformed_program_can_correct_once_without_unsafe_execution(self):
        class Malformed(LocalOperationsPlanner):
            calls = 0
            def resolve(self, context):
                self.calls += 1
                if self.calls == 1:
                    return ResolutionProgram.model_validate({'secret_field': 'do not expose'})
                assert 'OUTPUT_SCHEMA_INVALID:missing' in context['validation_feedback']
                return super().resolve(context)
        planner = Malformed()
        result = self.service.resolve('a', 'partial-credit', planner)
        self.assertEqual(planner.calls, 2)
        self.assertEqual(result['status'], 'POSTED_SYNTHETIC')
        self.assertNotIn('do not expose', str(result))
        self.assertEqual(self.count(), 1)

    def test_repeated_malformed_program_stops_after_two_attempts(self):
        class Malformed(LocalOperationsPlanner):
            calls = 0
            def resolve(self, context):
                self.calls += 1
                return ResolutionProgram.model_validate({})
        planner = Malformed()
        result = self.service.resolve('a', 'routine', planner)
        self.assertEqual(planner.calls, 2)
        self.assertEqual(result['status'], 'UNRESOLVED')
        self.assertEqual(self.count(), 0)

    def test_resolution_model_timeout_does_not_use_rule_program(self):
        class FailsAtResolution(LocalOperationsPlanner):
            def resolve(self, context):
                raise TimeoutError('provider down')
        result=self.service.resolve('a','routine',FailsAtResolution())
        self.assertEqual(result['status'],'UNRESOLVED')
        self.assertEqual(self.count(),0)

    def test_program_guard_rejects_six_negative_cases(self):
        for case_id in ('routine','partial-credit'):
            case=load_case(case_id)
            program=local_resolution_program(case['invoice'],case['records'])
            self.assertTrue(verify_resolution(program,case['invoice'],case['records'],case['mandate'])['passed'])
            results=challenge_resolution(program,case['invoice'],case['records'],case['mandate'])
            self.assertEqual(len(results),6)
            self.assertTrue(all(r['rejected'] for r in results))

    def test_skipped_credit_and_payment_before_adjustment_fail(self):
        case=load_case('partial-credit')
        program=local_resolution_program(case['invoice'],case['records'])
        program.steps=list(reversed(program.steps))
        self.assertIn('UNSAFE_ACTION_ORDER',verify_resolution(program,case['invoice'],case['records'],case['mandate'])['errors'])
        program=local_resolution_program(case['invoice'],case['records'])
        program.steps.pop(1)
        self.assertFalse(verify_resolution(program,case['invoice'],case['records'],case['mandate'])['passed'])

    def test_resolution_journal_failure_rolls_back_payment(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_resolution BEFORE INSERT ON operations_resolution_actions BEGIN SELECT RAISE(ABORT,'test journal failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.resolve('a','partial-credit')
        self.assertEqual(self.count(),0)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM operations_resolution_receipts').fetchone()[0],0)

    def test_resolution_replay_does_not_apply_credit_twice(self):
        first=self.service.resolve('a','partial-credit')
        second=self.service.resolve('a','partial-credit')
        self.assertEqual(second['status'],'ALREADY_POSTED')
        self.assertFalse(second['resolution']['journal_effects_created'])
        self.assertEqual(first['resolution']['receipt'],second['resolution']['receipt'])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM operations_resolution_actions').fetchone()[0],3)

    def test_corrupted_resolution_effect_is_not_reported_verified(self):
        self.service.resolve('a','partial-credit')
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE operations_resolution_actions SET amount_minor=1 WHERE action='APPLY_APPROVED_CREDIT'")
        with self.assertRaises(ValueError):
            self.service.resolve('a','partial-credit')
        self.assertEqual(self.count(),1)


if __name__ == "__main__":
    unittest.main()
