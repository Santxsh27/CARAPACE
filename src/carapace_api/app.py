"""ASGI application imported by Cloud Run servers."""

from .factory import create_app

app = create_app()
