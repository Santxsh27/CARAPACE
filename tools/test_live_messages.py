import unittest

from evaluate_live_messages import cases, extended_cases, preflight, score


class LiveMessageEvaluationTests(unittest.TestCase):
    def test_above_limit_preflight(self):
        mandate = {"sandbox_balance_minor": 20000, "mandate": {
            "automatic_payment_limit_minor": 5000, "protected_balance_minor": 10000}}
        self.assertEqual(preflight(mandate), 5100)
        mandate["sandbox_balance_minor"] = 15000
        with self.assertRaises(ValueError):
            preflight(mandate)

    def test_case_labels_and_fresh_reference(self):
        corpus = cases("FRESH-123", 300100)
        self.assertEqual(len(corpus), 8)
        self.assertEqual(sum(c[2] == "READY" for c in corpus), 3)
        self.assertTrue(all("FRESH-123" in c[1] for c in corpus))
        self.assertIn("FRESH-123-UNKNOWN", corpus[-1][1])

    def test_extended_cases_are_bounded_and_include_negation_and_languages(self):
        corpus = extended_cases("NEW-123", 300100)
        self.assertEqual(len(corpus), 16)
        self.assertEqual(len({case[0] for case in corpus}), 16)
        self.assertEqual(sum(c[2] == "READY" for c in corpus), 8)
        self.assertTrue(all("NEW-123" in c[1] for c in corpus))

    def test_scoring_is_fail_closed(self):
        valid = {"state": "READY", "reason": ["ABOVE_AUTOMATIC_LIMIT"], "money_moved": False,
                 "understanding": {"mode": "VERTEX_AI", "successful_model_calls": 1}}
        self.assertEqual(score(valid, "READY", "ABOVE_AUTOMATIC_LIMIT"), [])
        for changed in ({"run_id": "ff_unexpected"}, {"money_moved": True}, {"understanding": {}},
                        {"state": "ATTENTION"}, {"reason": []}):
            with self.subTest(changed=changed):
                self.assertTrue(score({**valid, **changed}, "READY", "ABOVE_AUTOMATIC_LIMIT"))

    def test_extraction_is_checked_not_just_state(self):
        result = {"state": "READY", "reason": [], "money_moved": False,
                  "understanding": {"mode": "VERTEX_AI", "successful_model_calls": 1},
                  "interpretation": {"amount_minor": 999}}
        self.assertIn("incorrect extracted amount_minor", score(result, "READY", None, {"amount_minor": 100}))

    def test_unsupported_quotation_is_not_counted_as_a_pass(self):
        result = {"state": "READY", "money_moved": False,
                  "understanding": {"mode": "VERTEX_AI", "successful_model_calls": 1},
                  "interpretation": {"evidence_spans": [{"quote": "invented amount"}]}}
        self.assertIn("unsupported source quotation", score(result, "READY", None, source_text="INR 100"))
        result["interpretation"]["evidence_spans"] = [{"quote": "INR 100"}]
        self.assertEqual(score(result, "READY", None, source_text="INR 100"), [])


if __name__ == "__main__":
    unittest.main()
