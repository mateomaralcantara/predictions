"""Configuración común: la API se prueba contra CSV de fixtures, sin red,
sin base de datos y sin credenciales reales."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path[:0] = [str(ROOT), str(ROOT / "apps" / "api")]

_TMP = Path(tempfile.mkdtemp(prefix="predictions-tests-"))

TEST_ENV = {
    "ENVIRONMENT": "test",
    "SECRET_KEY": "clave-de-pruebas-suficientemente-larga-1234567890",
    # CI puede probar contra PostgreSQL real con TEST_APP_DATABASE_URL.
    "APP_DATABASE_URL": os.environ.get("TEST_APP_DATABASE_URL") or f"sqlite:///{_TMP / 'app.db'}",
    "AUTO_MIGRATE": "true",
    "AUTO_ACTUALIZAR": "false",
    "TRUST_PROXY_HEADERS": "",
    "DATABASE_URL": "",
    "DB_HOST": "",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "SUPABASE_DB_URL": "",
    "GOOGLE_API_KEY": "",
    "PAYPAL_CLIENT_ID": "",
    "PAYPAL_SECRET": "",
    "ADMIN_TOKEN": "",
    "FRONTEND_URL": "http://localhost:5174",
    "RESULTADOS_CSV": str(FIXTURES / "resultados.csv"),
    "LOTO_CSV": str(ROOT / "data" / "loto" / "loto_historico.csv"),
    "SUPERKINO_CSV": str(ROOT / "data" / "superkino" / "superkino_historico.csv"),
}
os.environ.update(TEST_ENV)


def _reset_caches() -> None:
    from app import deps, predictions, tradicional
    from app.config import get_settings
    from app.ratelimit import limiter

    get_settings.cache_clear()
    deps.get_repository.cache_clear()
    predictions.clear_cache()
    tradicional.clear_cache()
    limiter.reset()


@pytest.fixture(autouse=True)
def _db_limpia():
    """Cada test empieza con la base de la app vacía (pero migrada)."""
    from app.config import get_settings
    from app.db import Base, session_factory
    from app.migrate import upgrade

    _reset_caches()
    url = get_settings().app_database_url
    upgrade(url)
    with session_factory(url)() as db:
        for tabla in reversed(Base.metadata.sorted_tables):
            if tabla.name != "resultados_tradicionales":
                db.execute(tabla.delete())
        db.commit()
    yield


def registrar(client, email: str = "ana@example.com", password: str = "clave-segura-1", nombre: str = "Ana") -> dict:
    r = client.post("/api/auth/registro", json={"email": email, "password": password, "nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def env(monkeypatch):
    """Permite cambiar variables de entorno dentro de un test."""

    def _set(**values: str) -> None:
        for k, v in values.items():
            monkeypatch.setenv(k, v)
        _reset_caches()

    yield _set
    _reset_caches()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    _reset_caches()
    with TestClient(create_app()) as c:
        yield c
