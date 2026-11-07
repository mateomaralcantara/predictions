"""Compatibilidad: ``uvicorn main:app`` sigue funcionando desde apps/api."""

from app.main import app

__all__ = ["app"]
