from __future__ import annotations

import unittest

from carapace_ai.redaction import redact_for_model


class ModelInputRedactionTests(unittest.TestCase):
    def test_sensitive_payment_credentials_are_removed_before_model_use(self) -> None:
        result = redact_for_model(
            "Your OTP is 123456. UPI PIN: 1234. CVV=123. "
            "Password: secret-value. Card 4111 1111 1111 1111."
        )

        self.assertTrue(result.redaction_applied)
        self.assertNotIn("123456", result.text)
        self.assertNotIn("1234", result.text)
        self.assertNotIn("4111", result.text)
        self.assertIn("[REDACTED_OTP]", result.text)
        self.assertIn("[REDACTED_PIN]", result.text)

    def test_safety_warning_without_a_secret_remains_usable(self) -> None:
        result = redact_for_model("Never share your UPI PIN with a caller.")

        self.assertFalse(result.redaction_applied)
        self.assertEqual(result.text, "Never share your UPI PIN with a caller.")
