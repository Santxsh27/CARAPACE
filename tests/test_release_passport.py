from __future__ import annotations

import unittest

from carapace_core.release_passport import (
    build_release_passport,
    verify_release_passport,
)


class ReleasePassportTests(unittest.TestCase):
    def test_passport_detects_tampering(self) -> None:
        case = {
            "case_id": "case_demo",
            "run_id": "run_demo",
            "contract_id": "contract_demo",
            "failed_checks": ["AT_MOST_ONE_POSTED_DEBIT"],
        }
        analysis = {
            "analysis_id": "proofops_0123456789abcdef0123456789abcdef",
            "provider": "google",
            "model": "gemini-test",
            "mode": "VERTEX_AI",
            "verification_status": "COUNTERFACTUAL_VERIFIED",
            "counterfactual_search": {
                "counterfactual_verdict": "MATCH",
                "minimal_interventions": ["DEDUPLICATE_LOGICAL_DEBITS"],
            },
            "regression_scenarios": [{"name": "lost response and retry"}],
        }
        approval = {
            "approval_id": "approval_0123456789abcdef01234567",
            "reviewer_id": "release-manager",
            "candidate_reference": "commit-deadbee",
            "decision": "APPROVE",
        }
        passport = build_release_passport(
            tenant_id="bank-a",
            case=case,
            analysis=analysis,
            approval=approval,
            signing_key="separate-test-signing-key",
        )

        self.assertTrue(
            verify_release_passport(passport, "separate-test-signing-key")
        )
        passport["candidate_reference"] = "commit-attacker"
        self.assertFalse(
            verify_release_passport(passport, "separate-test-signing-key")
        )


if __name__ == "__main__":
    unittest.main()
