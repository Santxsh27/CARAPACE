from __future__ import annotations

import unittest

from carapace_ai.provider import LocalDemoIntentProvider
from carapace_core.lens import (
    IntentDirection,
    LensInputError,
    MessageIntent,
    parse_upi_payment_uri,
    reconcile_intent,
)


class LensCoreTests(unittest.TestCase):
    def test_upi_uri_is_parsed_as_canonical_send_request(self) -> None:
        request = parse_upi_payment_uri(
            "upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR&tn=Order%207782"
        )
        self.assertEqual(request.direction, IntentDirection.SEND)
        self.assertEqual(request.amount_minor, 499_900)
        self.assertEqual(request.payee_name, "R K Traders")

    def test_receive_story_and_send_request_are_stopped(self) -> None:
        provider = LocalDemoIntentProvider()
        intent = provider.extract_intent(
            "ABC Support: Urgent! We are refunding ₹4,999. Scan this QR and enter your UPI PIN now.",
            "en-IN",
        )
        payment = parse_upi_payment_uri(
            "upi://pay?pa=rktraders@upi&pn=R%20K%20Traders&am=4999&cu=INR"
        )
        assessment = reconcile_intent(intent, payment)
        self.assertEqual(assessment.decision.value, "STOP")
        codes = {finding.code for finding in assessment.findings}
        self.assertIn("DIRECTION_CONTRADICTION", codes)
        self.assertIn("PAYEE_IDENTITY_CONTRADICTION", codes)
        self.assertIn("PIN_TO_RECEIVE_DECEPTION", codes)

    def test_matching_purchase_is_allowed_with_honest_limit(self) -> None:
        intent = MessageIntent(
            expected_direction=IntentDirection.SEND,
            expected_amount_minor=499_900,
            currency="INR",
            claimed_entity="ABC Electronics",
            urgency_detected=False,
            asks_for_pin_to_receive=False,
            summary="Purchase payment",
        )
        payment = parse_upi_payment_uri(
            "upi://pay?pa=abc@upi&pn=ABC%20Electronics&am=4999&cu=INR"
        )
        assessment = reconcile_intent(intent, payment)
        self.assertEqual(assessment.decision.value, "ALLOW")
        self.assertIn("not a guarantee", assessment.plain_language_result)

    def test_invalid_or_overprecise_amount_is_rejected(self) -> None:
        with self.assertRaises(LensInputError):
            parse_upi_payment_uri("https://example.com/pay")
        with self.assertRaises(LensInputError):
            parse_upi_payment_uri("upi://pay?pa=merchant@upi&am=10.999")


if __name__ == "__main__":
    unittest.main()
