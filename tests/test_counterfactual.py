from __future__ import annotations

import json
import unittest
from pathlib import Path

from carapace_core.counterfactual import search_minimal_repair


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    with (ROOT / "examples" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class CounterfactualSafetySearchTests(unittest.TestCase):
    def test_duplicate_debit_has_one_minimal_safe_intervention(self) -> None:
        result = search_minimal_repair(
            load_example("payment-promise.json"),
            load_example("execution-duplicate-debit.json"),
            ["DEDUPLICATE_LOGICAL_DEBITS"],
        )

        self.assertEqual(result.original_verdict, "MISMATCH")
        self.assertEqual(result.counterfactual_verdict, "MATCH")
        self.assertEqual(
            result.minimal_interventions, ("DEDUPLICATE_LOGICAL_DEBITS",)
        )
        self.assertEqual(result.experiments_run, 1)

    def test_valid_execution_requires_no_intervention(self) -> None:
        result = search_minimal_repair(
            load_example("payment-promise.json"),
            load_example("execution-valid.json"),
        )

        self.assertEqual(result.original_verdict, "MATCH")
        self.assertEqual(result.minimal_interventions, ())
        self.assertEqual(result.experiments_run, 0)
