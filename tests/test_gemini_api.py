from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from carapace_ai.gemini_api import GeminiApiIntentProvider


class _FakeModels:
    def generate_content(self, **kwargs):
        del kwargs
        return SimpleNamespace(
            text=json.dumps(
                {
                    "expected_direction": "SEND",
                    "expected_amount_minor": 10000,
                    "currency": "INR",
                    "claimed_entity": "Demo Merchant",
                    "urgency_detected": False,
                    "asks_for_pin_to_receive": False,
                    "summary": "A purchase payment is requested.",
                }
            )
        )


class GeminiApiIntentProviderTests(unittest.TestCase):
    def test_ai_studio_adapter_uses_structured_gemini_response(self) -> None:
        provider = GeminiApiIntentProvider(
            "synthetic-key",
            "gemini-test",
            client=SimpleNamespace(models=_FakeModels()),
        )

        intent = provider.extract_intent("Pay INR 100", "en-IN")

        self.assertEqual(intent.expected_amount_minor, 10000)
        self.assertEqual(provider.mode, "GEMINI_API")

    def test_api_key_is_required(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "GOOGLE_API_KEY"):
            GeminiApiIntentProvider("", "gemini-test", client=object())
