"""Gemini Developer API adapter for no-cost AI Studio development."""

from __future__ import annotations

from typing import Any

from .gemini_vertex import VertexGeminiIntentProvider


class GeminiApiIntentProvider(VertexGeminiIntentProvider):
    """Use the same hardened schema through the Gemini Developer API.

    The API key is supplied only to the Google Gen AI client. It is never
    returned through CARAPACE status or provenance responses.
    """

    provider_name = "google-gemini-api"
    mode = "GEMINI_API"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for the Gemini API provider")
        self.model_name = model
        if client is not None:
            self._client = client
            return
        try:
            from google import genai
        except ImportError as error:
            raise RuntimeError("Install the google-genai dependency to use Gemini") from error
        self._client = genai.Client(api_key=api_key, http_options={"timeout": 20000})
