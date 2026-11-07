"""Punto de entrada de la API.

uvicorn app.main:app --reload            (desde apps/api)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import __version__
from .config import get_settings
from .deps import get_repository
from .routers import admin, chat, estadisticas, pagos, predicciones

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Predictions RD API",
        version=__version__,
        description="Resultados, estadísticas y jugadas heurísticas de loterías dominicanas.",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"servicio": "Predictions RD API", "version": __version__, "docs": "/docs", "salud": "/api/health"}

    @app.get("/api/health", tags=["sistema"])
    def health() -> dict:
        repo = get_repository()
        rows = repo.all()
        return {
            "estado": "ok" if rows else "sin_datos",
            "version": __version__,
            "fuente_datos": repo.source,
            "sorteos": len(rows),
            "sorteos_descartados": repo.descartados,
            "ultimo_sorteo": rows[-1].fecha.isoformat() if rows else None,
            "openai": settings.openai_enabled,
            "pagos": settings.paypal_enabled,
        }

    for r in (estadisticas.router, chat.router, predicciones.router, pagos.router, admin.router):
        app.include_router(r)
    return app


app = create_app()
