"""Configuración central leída de variables de entorno (.env).

Ningún secreto vive en el código: todo sale de ``os.environ``.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]

# Orden de prioridad (la primera que defina una variable gana; las variables
# de entorno del sistema siempre ganan a cualquier archivo):
ENV_FILES = (
    REPO_ROOT / ".env.local",  # configuración local recomendada (npm run setup)
    API_DIR / ".env.local",
    API_DIR / ".env",  # compatibilidad con instalaciones anteriores
    REPO_ROOT / ".env",
)
for _f in ENV_FILES:
    load_dotenv(_f, override=False)


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
    url = _env("DATABASE_URL") or _env("SUPABASE_DB_URL")
    if url:
        return url
    host, name, user = _env("DB_HOST"), _env("DB_NAME"), _env("DB_USER")
    if not (host and name and user):
        return None
    password = _env("DB_PASSWORD", "")
    port = _env("DB_PORT", "5432")
    auth = f"{user}:{password}" if password else user
    return f"postgresql://{auth}@{host}:{port}/{name}"


log = logging.getLogger(__name__)


def _bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "si", "sí", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str
    secret_key: str
    app_database_url: str
    auto_migrate: bool
    trust_proxy_headers: bool
    database_url: str | None
    openai_api_key: str | None
    openai_model: str
    gemini_api_key: str | None
    gemini_model: str
    paypal_client_id: str | None
    paypal_secret: str | None
    paypal_base_url: str
    frontend_url: str
    admin_token: str | None
    resultados_csv: Path
    loto_csv: Path
    superkino_csv: Path
    lotopool_csv: Path
    auto_actualizar: bool = False
    actualizar_cada_min: int = 30
    # juego -> CSV versionado en Git (origen de la copia viva en data/vivo/)
    csv_base: dict[str, Path] = field(default_factory=dict)
    cors_origins: list[str] = field(default_factory=list)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def ia_proveedor(self) -> str | None:
        """Gemini tiene prioridad si hay clave; luego OpenAI; si no, respuestas locales."""
        if self.gemini_enabled:
            return "gemini"
        if self.openai_enabled:
            return "openai"
        return None

    @property
    def paypal_enabled(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_secret)


VIVO_DIR = REPO_ROOT / "data" / "vivo"

# juego -> (variable de entorno, CSV versionado)
DATOS = {
    "resultados": ("RESULTADOS_CSV", REPO_ROOT / "data" / "tradicionales" / "resultados_tradicionales.csv"),
    "loto": ("LOTO_CSV", REPO_ROOT / "data" / "loto" / "loto_historico.csv"),
    "superkino": ("SUPERKINO_CSV", REPO_ROOT / "data" / "superkino" / "superkino_historico.csv"),
    "lotopool": ("LOTOPOOL_CSV", REPO_ROOT / "data" / "lotopool" / "lotopool_historico.csv"),
}


def _rutas_datos(auto_actualizar: bool) -> dict:
    """Con auto-actualización la API lee y escribe copias en data/vivo/ (ignoradas
    por Git), para no ensuciar los CSV versionados ni bloquear un ``git pull``."""
    rutas: dict = {"csv_base": {}}
    for juego, (var, base) in DATOS.items():
        explicita = _env(var)
        rutas["csv_base"][juego] = _path_from_env(var, base)
        if explicita or not auto_actualizar:
            rutas[f"{juego}_csv"] = _path_from_env(var, base)
        else:
            rutas[f"{juego}_csv"] = VIVO_DIR / base.relative_to(REPO_ROOT / "data")
    return rutas


_override: Settings | None = None


def get_settings() -> Settings:
    return _override or _build_settings()


def _cache_clear() -> None:
    global _override
    _override = None
    _build_settings.cache_clear()


get_settings.cache_clear = _cache_clear  # type: ignore[attr-defined]


def usar_sqlite_local() -> Settings:
    """Desarrollo: si la base configurada no responde, guarda cuentas en SQLite local."""
    global _override
    db_file = REPO_ROOT / "data" / "app.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    _override = replace(_build_settings(), app_database_url=f"sqlite:///{db_file}", database_url=None)
    return _override


@lru_cache
def _build_settings() -> Settings:
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

    environment = (_env("ENVIRONMENT", "development") or "development").lower()
    secret_key = _env("SECRET_KEY")
    if not secret_key:
        if environment == "production":
            raise RuntimeError("SECRET_KEY es obligatoria en producción.")
        secret_key = secrets.token_urlsafe(48)
        log.warning("SECRET_KEY no definida: se usa una clave temporal (las sesiones se pierden al reiniciar).")
    elif environment == "production" and len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY debe tener al menos 32 caracteres en producción.")

    database_url = _database_url()
    app_db = _env("APP_DATABASE_URL") or database_url
    if not app_db:
        db_file = REPO_ROOT / "data" / "app.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        app_db = f"sqlite:///{db_file}"

    auto_actualizar = _bool("AUTO_ACTUALIZAR", True)

    return Settings(
        environment=environment,
        secret_key=secret_key,
        app_database_url=app_db,
        auto_migrate=_bool("AUTO_MIGRATE", True),
        trust_proxy_headers=_bool("TRUST_PROXY_HEADERS", False),
        database_url=database_url,
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_model=_env("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_api_key=_env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"),
        gemini_model=_env("GEMINI_MODEL", "gemini-2.5-flash"),
        paypal_client_id=_env("PAYPAL_CLIENT_ID"),
        paypal_secret=_env("PAYPAL_SECRET"),
        paypal_base_url=_env("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/"),
        frontend_url=frontend_url,
        admin_token=_env("ADMIN_TOKEN"),
        **_rutas_datos(auto_actualizar),
        auto_actualizar=auto_actualizar,
        actualizar_cada_min=max(5, int(_env("ACTUALIZAR_CADA_MIN", "30") or 30)),
        cors_origins=list(dict.fromkeys(origins)),
    )
