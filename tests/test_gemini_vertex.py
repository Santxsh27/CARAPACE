from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from carapace_ai.gemini_vertex import VertexGeminiIntentProvider
from carapace_core.lens import IntentDirection


class _FakeModels:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self.response_text)


class VertexGeminiIntentProviderTests(unittest.TestCase):
    def test_structured_vertex_response_is_converted_to_intent(self) -> None:
        models = _FakeModels(
            json.dumps(
                {
                    "expected_direction": "RECEIVE_EXPECTED",
                    "expected_amount_minor": 499900,
                    "currency": "INR",
                    "claimed_entity": "ABC Support",
                    "urgency_detected": True,
                    "asks_for_pin_to_receive": True,
                    "summary": "A refund is promised to the user.",
                }
            )
        )
        provider = VertexGeminiIntentProvider(
            "test-project", "global", "gemini-test", client=SimpleNamespace(models=models)
        )

        intent = provider.extract_intent("refund message", "en-IN")

        self.assertEqual(intent.expected_direction, IntentDirection.RECEIVE_EXPECTED)
        self.assertEqual(intent.expected_amount_minor, 499900)
        self.assertEqual(len(models.calls), 1)

    def test_blank_vertex_response_fails_closed(self) -> None:
        provider = VertexGeminiIntentProvider(
            "test-project", "global", "gemini-test", client=SimpleNamespace(models=_FakeModels(""))
        )

        with self.assertRaisesRegex(RuntimeError, "no structured intent"):
            provider.extract_intent("refund message", "en-IN")

    def test_project_is_required_even_with_an_injected_client(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "GOOGLE_CLOUD_PROJECT"):
            VertexGeminiIntentProvider("", "global", "gemini-test", client=object())
