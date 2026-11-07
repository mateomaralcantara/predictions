"""Comprobaciones reales de las claves configuradas (las usan setup y doctor)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"


def probar_gemini(clave: str, modelo: str = "gemini-2.5-flash", transport=None) -> tuple[bool, str]:
    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}"
    try:
        with httpx.Client(timeout=10, transport=transport) as client:
            r = client.get(url, headers={"x-goog-api-key": clave})
    except httpx.HTTPError as exc:
        return False, f"sin conexión con Google ({exc.__class__.__name__})"
    if r.status_code == 200:
        return True, f"clave válida, modelo {modelo} disponible"
    if r.status_code == 404:
        return False, f"el modelo «{modelo}» no existe; revisa GEMINI_MODEL"
    if r.status_code in (400, 401, 403):
        return False, "clave rechazada por Google (¿copiada completa? ¿API habilitada?)"
    if r.status_code == 429:
        return True, "clave válida, pero sin cuota ahora mismo (429)"
    return False, f"respuesta inesperada de Google: HTTP {r.status_code}"


def probar_db(url: str) -> tuple[bool, str]:
    sys.path[:0] = [str(ROOT), str(API)]
    try:
        from sqlalchemy import text

        from app.db import get_engine

        engine = get_engine(url)
        consulta = "select sqlite_version()" if engine.dialect.name == "sqlite" else "select version()"
        with engine.connect() as conn:
            version = conn.execute(text(consulta)).scalar() or ""
        if engine.dialect.name == "sqlite":
            version = f"SQLite {version}"
        return True, "conectado · " + " ".join(str(version).split()[:2])
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).splitlines()[0][:160]
        return False, f"{exc.__class__.__name__}: {msg}"


def ocultar_url(url: str) -> str:
    """postgresql://user:SECRETO@host/db -> postgresql://user:***@host/db"""
    if "@" not in url or "://" not in url:
        return url
    esquema, resto = url.split("://", 1)
    cred, host = resto.rsplit("@", 1)
    usuario = cred.split(":", 1)[0]
    return f"{esquema}://{usuario}:***@{host}"
