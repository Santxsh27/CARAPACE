"""Cloud Run-compatible control plane for CARAPACE."""

from .factory import create_app

__all__ = ["create_app"]
