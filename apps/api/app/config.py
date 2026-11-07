"""Configuración central leída de variables de entorno (.env).

Ningún secreto vive en el código: todo sale de ``os.environ``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]

# El .env de apps/api tiene prioridad sobre el de la raíz del repo.
load_dotenv(API_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _first_existing(*candidates: Path) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _path_from_env(name: str, *defaults: Path) -> Path:
    raw = _env(name)
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else (REPO_ROOT / path)
    return _first_existing(*defaults)


def _database_url() -> str | None:
    url = _env("DATABASE_URL")
    if url:
        return url
    host, name, user = _env("DB_HOST"), _env("DB_NAME"), _env("DB_USER")
    if not (host and name and user):
        return None
    password = _env("DB_PASSWORD", "")
    port = _env("DB_PORT", "5432")
    auth = f"{user}:{password}" if password else user
    return f"postgresql://{auth}@{host}:{port}/{name}"


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    openai_api_key: str | None
    openai_model: str
    paypal_client_id: str | None
    paypal_secret: str | None
    paypal_base_url: str
    frontend_url: str
    admin_token: str | None
    resultados_csv: Path
    loto_csv: Path
    superkino_csv: Path
    cors_origins: list[str] = field(default_factory=list)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def paypal_enabled(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_secret)


@lru_cache
def get_settings() -> Settings:
    frontend_url = _env("FRONTEND_URL", "http://localhost:5174").rstrip("/")
    default_origins = [
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    raw_origins = _env("CORS_ORIGINS")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins else default_origins

    return Settings(
        database_url=_database_url(),
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_model=_env("OPENAI_MODEL", "gpt-4o-mini"),
        paypal_client_id=_env("PAYPAL_CLIENT_ID"),
        paypal_secret=_env("PAYPAL_SECRET"),
        paypal_base_url=_env("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/"),
        frontend_url=frontend_url,
        admin_token=_env("ADMIN_TOKEN"),
        resultados_csv=_path_from_env(
            "RESULTADOS_CSV",
            REPO_ROOT / "data" / "tradicionales" / "resultados_tradicionales.csv",
            API_DIR / "loterias" / "resultados_tradicionales_2010_a_hoy.csv",
        ),
        loto_csv=_path_from_env(
            "LOTO_CSV",
            REPO_ROOT / "data" / "loto" / "loto_historico.csv",
            API_DIR / "leidsa" / "lotto" / "loto_leidsa.csv",
        ),
        superkino_csv=_path_from_env(
            "SUPERKINO_CSV",
            REPO_ROOT / "data" / "superkino" / "superkino_historico.csv",
            API_DIR / "leidsa" / "superkino" / "superkino_historico.csv",
        ),
        cors_origins=list(dict.fromkeys(origins)),
    )
