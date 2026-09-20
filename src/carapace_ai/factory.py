"""Configuration-driven AI provider selection."""

from __future__ import annotations

from carapace_api.config import Settings

from .gemini_api import GeminiApiIntentProvider
from .gemini_vertex import VertexGeminiIntentProvider
from .incident_reasoning import (
    GeminiIncidentReasoningProvider,
    IncidentReasoningProvider,
    LocalIncidentReasoningProvider,
)
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
    if settings.ai_provider in {"gemini", "ai_studio"}:
        return GeminiApiIntentProvider(
            api_key=settings.google_api_key or "",
            model=settings.gemini_model,
        )
    raise RuntimeError(
        "CARAPACE_AI_PROVIDER must be 'local', 'gemini', 'ai_studio', or 'vertex'"
    )


def create_incident_reasoning_provider(
    lens_provider: LensIntentProvider,
) -> IncidentReasoningProvider:
    if lens_provider.mode == "LOCAL_RULES":
        return LocalIncidentReasoningProvider()
    client = getattr(lens_provider, "_client", None)
    if client is None:
        raise RuntimeError("the configured Gemini provider has no usable client")
    return GeminiIncidentReasoningProvider(
        client=client,
        model=lens_provider.model_name,
        mode=lens_provider.mode,
    )
