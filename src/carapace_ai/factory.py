"""Configuration-driven AI provider selection."""

from __future__ import annotations

from carapace_api.config import Settings

from .gemini_vertex import VertexGeminiIntentProvider
from .provider import LensIntentProvider, LocalDemoIntentProvider


def create_lens_provider(settings: Settings) -> LensIntentProvider:
    if settings.ai_provider == "local":
        return LocalDemoIntentProvider()
    if settings.ai_provider == "vertex":
        return VertexGeminiIntentProvider(
            project=settings.google_cloud_project or "",
            location=settings.google_cloud_location,
            model=settings.gemini_model,
        )
    raise RuntimeError("CARAPACE_AI_PROVIDER must be 'local' or 'vertex'")
