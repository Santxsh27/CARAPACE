import unittest

from verify_cloud_documents import validate_payment_preflight, validate_result


class CloudDocumentChecksTests(unittest.TestCase):
    def setUp(self):
        self.mandate = {"sandbox_balance_minor": 10000, "mandate": {
            "automatic_sandbox_execution": True, "automatic_payment_limit_minor": 5000,
            "protected_balance_minor": 5000}}

    def test_small_permitted_payment(self):
        validate_payment_preflight(self.mandate, 4900)

    def test_caps_and_nonpositive_amounts(self):
        for amount in (0, -1, 5001):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                validate_payment_preflight(self.mandate, amount)

    def test_permission_cannot_be_broadened_by_tool(self):
        self.mandate["mandate"]["automatic_sandbox_execution"] = False
        with self.assertRaises(ValueError):
            validate_payment_preflight(self.mandate, 4900)

    def test_reserve_is_preserved(self):
        self.mandate["sandbox_balance_minor"] = 9000
        with self.assertRaises(ValueError):
            validate_payment_preflight(self.mandate, 4900)

    def test_missing_live_evidence_fails_verification(self):
        result = {"interpretation": {"bill_reference": "DOC-TEST", "amount_minor": 4900,
                                    "claimed_payee_id": "fridaydocs@upi", "evidence_spans": []},
                  "understanding": {"mode": "VERTEX_AI", "successful_model_calls": 1},
                  "document": {"raw_file_stored": False}, "state": "COMPLETED", "run_id": "ff_test"}
        with self.assertRaises(AssertionError):
            validate_result(result, reference="DOC-TEST", amount=4900, payee="fridaydocs@upi", payment=True)


if __name__ == "__main__":
    unittest.main()
