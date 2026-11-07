"""Punto de entrada de la API.

uvicorn app.main:app --reload            (desde apps/api)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import __version__
from .config import get_settings
from .deps import get_repository
from .routers import admin, chat, cuenta, estadisticas, pagos, predicciones

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.auto_migrate:
        from .migrate import upgrade

        try:
            upgrade(settings.app_database_url)
        except Exception as exc:
            if settings.is_production:
                raise
            # Desarrollo: típico .env apuntando a un PostgreSQL apagado.
            log.error(
                "No se pudo conectar a la base de datos configurada (%s). "
                "Se usará SQLite local para las cuentas y el CSV para los resultados. "
                "Revisa DATABASE_URL / DB_* en apps/api/.env o enciende PostgreSQL.",
                exc.__class__.__name__,
            )
            from .config import usar_sqlite_local

            upgrade(usar_sqlite_local().app_database_url)
        log.info("Base de datos de la app al día.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        lifespan=lifespan,
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
        allow_headers=["Content-Type", "Authorization", "X-Admin-Token"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # noqa: ANN001, ANN202
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/auth"):
            response.headers["Cache-Control"] = "no-store"
        return response

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
            "entorno": settings.environment,
        }

    for r in (estadisticas.router, chat.router, predicciones.router, cuenta.router, pagos.router, admin.router):
        app.include_router(r)
    return app


app = create_app()
