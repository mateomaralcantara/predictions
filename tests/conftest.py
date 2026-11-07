"""Configuración común: la API se prueba contra CSV de fixtures, sin red,
sin base de datos y sin credenciales reales."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path[:0] = [str(ROOT), str(ROOT / "apps" / "api")]

TEST_ENV = {
    "DATABASE_URL": "",
    "DB_HOST": "",
    "OPENAI_API_KEY": "",
    "PAYPAL_CLIENT_ID": "",
    "PAYPAL_SECRET": "",
    "ADMIN_TOKEN": "",
    "FRONTEND_URL": "http://localhost:5174",
    "RESULTADOS_CSV": str(FIXTURES / "resultados.csv"),
    "LOTO_CSV": str(ROOT / "apps" / "api" / "leidsa" / "lotto" / "loto_leidsa.csv"),
    "SUPERKINO_CSV": str(ROOT / "apps" / "api" / "leidsa" / "superkino" / "superkino_historico.csv"),
}
os.environ.update(TEST_ENV)


def _reset_caches() -> None:
    from app import deps, predictions
    from app.config import get_settings

    get_settings.cache_clear()
    deps.get_repository.cache_clear()
    predictions.clear_cache()


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
