from __future__ import annotations

import json
import unittest
from pathlib import Path

from carapace_ai.incident_reasoning import build_minimised_incident_context
from carapace_core.verifier import verify_payment


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    with (ROOT / "examples" / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class IncidentReasoningPrivacyTests(unittest.TestCase):
    def test_model_context_uses_counts_and_excludes_account_identifiers(self) -> None:
        contract = load_example("payment-promise.json")
        evidence = load_example("execution-duplicate-debit.json")
        report = verify_payment(contract, evidence).as_dict()
        account_identifiers = {
            str(entry.get("account_ref"))
            for entry in evidence["ledger_entries"]
            if entry.get("account_ref")
        }

        context = build_minimised_incident_context(
            contract,
            {"evidence": evidence, "report": report},
            {
                "case_id": "case_privacy_test",
                "failed_checks": [
                    check["code"] for check in report["checks"] if not check["passed"]
                ],
            },
        )
        serialized = json.dumps(context, sort_keys=True)

        self.assertEqual(context["observations"]["posted_debit_count"], 2)
        self.assertNotIn("ledger_entries", serialized)
        for identifier in account_identifiers:
            self.assertNotIn(identifier, serialized)


if __name__ == "__main__":
    unittest.main()
