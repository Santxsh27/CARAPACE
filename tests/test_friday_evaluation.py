import unittest

from carapace_core.friday_evaluation import build_cases, evaluate


class FridayEvaluationTests(unittest.TestCase):
    def test_independent_labels_and_generated_variations(self):
        cases = build_cases()
        self.assertEqual(len(cases), 51)
        self.assertEqual(len({c.case_id for c in cases}), 51)
        self.assertEqual(sum(c.expected_allow for c in cases), 12)
        self.assertEqual(len({c.goal.max_total_minor for c in cases}) > 3, True)

    def test_guard_allows_valid_and_blocks_unsafe_proposals(self):
        report = evaluate()
        self.assertEqual(report["correct_decisions"], 51)
        self.assertEqual(report["valid_allowed"], 12)
        self.assertEqual(report["unsafe_cases"], 39)
        self.assertEqual(report["unsafe_allowed"], 0)
        self.assertEqual(report["false_holds"], 0)
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["payment_effects"], 0)

    def test_corpus_identity_is_reproducible_and_sensitive_to_changes(self):
        report = evaluate()
        self.assertEqual(report["corpus_sha256"], evaluate()["corpus_sha256"])
        cases = build_cases()
        cases[0].proposal.steps[2].amount_minor += 1
        changed = evaluate(cases)
        self.assertNotEqual(report["corpus_sha256"], changed["corpus_sha256"])
        self.assertEqual(changed["false_holds"], 1)
        self.assertEqual(changed["correct_decisions"], 50)

    def test_ablation_is_not_presented_as_live_model_comparison(self):
        report = evaluate()
        self.assertIn("not plain-Gemini", report["ungated_same_proposals"]["note"])
        self.assertIn("no live Gemini", report["scope"])


if __name__ == "__main__":
    unittest.main()
