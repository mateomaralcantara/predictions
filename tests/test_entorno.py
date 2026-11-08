"""Configuración: .env.local, Supabase y asistente de setup."""

from __future__ import annotations

import importlib.util
import sys

import httpx
import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import checks  # noqa: E402

from app.db import connect_args_postgres, normalizar_url  # noqa: E402


def _cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, ROOT / "scripts" / f"{nombre}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_env_local_tiene_prioridad():
    from app import config

    assert config.ENV_FILES[0] == ROOT / ".env.local"


def test_supabase_db_url_se_usa_como_base(env):
    from app.config import get_settings

    env(
        SUPABASE_DB_URL="postgresql://postgres.abc:pw@aws-0-us-east-1.pooler.supabase.com:5432/postgres",
        APP_DATABASE_URL="",
    )
    s = get_settings()
    assert s.database_url.endswith("pooler.supabase.com:5432/postgres")
    assert s.app_database_url == s.database_url


def test_database_url_gana_a_supabase(env):
    from app.config import get_settings

    env(DATABASE_URL="postgresql://u:p@otro/db", SUPABASE_DB_URL="postgresql://u:p@x.supabase.co/db")
    assert get_settings().database_url == "postgresql://u:p@otro/db"


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("postgresql://postgres:pw@db.abc.supabase.co:5432/postgres", {"connect_timeout": 5, "sslmode": "require"}),
        (
            "postgresql://postgres.abc:pw@aws-0-sa-east-1.pooler.supabase.com:6543/postgres",
            {"connect_timeout": 5, "sslmode": "require", "prepare_threshold": None},
        ),
        ("postgresql://u:p@x.supabase.co:5432/db?sslmode=verify-full", {"connect_timeout": 5}),
        ("postgresql://u:p@localhost:5432/db", {"connect_timeout": 5}),
        ("sqlite:///x.db", {}),
    ],
)
def test_connect_args_supabase(url, esperado):
    assert connect_args_postgres(normalizar_url(url)) == esperado


def test_ocultar_url():
    assert (
        checks.ocultar_url("postgresql://postgres.abc:Sup3r$ecret@host:5432/db")
        == "postgresql://postgres.abc:***@host:5432/db"
    )
    assert checks.ocultar_url("sqlite:///x.db") == "sqlite:///x.db"


@pytest.mark.parametrize(
    ("status", "ok", "texto"),
    [(200, True, "válida"), (403, False, "rechazada"), (404, False, "no existe"), (429, True, "cuota")],
)
def test_probar_gemini(status, ok, texto):
    vistos = []

    def handler(req: httpx.Request) -> httpx.Response:
        vistos.append(req)
        return httpx.Response(status, json={})

    res = checks.probar_gemini("k-123", "gemini-2.5-flash", transport=httpx.MockTransport(handler))
    assert res[0] is ok and texto in res[1]
    assert vistos[0].headers["x-goog-api-key"] == "k-123"
    assert "k-123" not in str(vistos[0].url)  # la clave no viaja en la URL


def test_probar_db_sqlite(tmp_path):
    ok, msg = checks.probar_db(f"sqlite:///{tmp_path / 'x.db'}")
    assert ok and "conectado" in msg


def test_setup_escribe_env_local_sin_mostrar_secretos(tmp_path, monkeypatch, capsys):
    setup = _cargar("configurar_env")
    destino = tmp_path / ".env.local"
    monkeypatch.setattr(setup, "DESTINO", destino)
    monkeypatch.setattr(setup, "LEGADO", tmp_path / "no-existe")
    secretos = iter(["gem-SECRETA-1234", "postgresql://postgres:pw@db.x.supabase.co:5432/postgres", "pp-secret"])
    monkeypatch.setattr(setup.getpass, "getpass", lambda _p: next(secretos))
    entradas = iter(["pp-client-id", "s"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(entradas))
    monkeypatch.setattr(setup, "probar_gemini", lambda *a: (True, "ok"))
    monkeypatch.setattr(setup, "probar_db", lambda *a: (True, "ok"))

    assert setup.main() == 0
    texto = destino.read_text(encoding="utf-8")
    valores = setup.leer(destino)
    assert valores["GEMINI_API_KEY"] == "gem-SECRETA-1234"
    assert valores["SUPABASE_DB_URL"].startswith("postgresql://postgres:pw@db.x.supabase.co")
    assert valores["PAYPAL_CLIENT_ID"] == "pp-client-id" and valores["PAYPAL_BASE_URL"].endswith("sandbox.paypal.com")
    assert len(valores["SECRET_KEY"]) >= 32 and valores["ADMIN_TOKEN"]
    assert "# ── Inteligencia artificial" in texto  # conserva los comentarios de la plantilla
    salida = capsys.readouterr().out
    assert "gem-SECRETA-1234" not in salida and "pw@" not in salida  # nada secreto en pantalla

    # Segunda ejecución: Enter mantiene todo, "-" borra.
    secretos2 = iter(["", "-", ""])
    monkeypatch.setattr(setup.getpass, "getpass", lambda _p: next(secretos2))
    entradas2 = iter(["", "r"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(entradas2))
    setup.main()
    v2 = setup.leer(destino)
    assert v2["GEMINI_API_KEY"] == "gem-SECRETA-1234" and "SUPABASE_DB_URL" not in v2
    assert v2["SECRET_KEY"] == valores["SECRET_KEY"] and v2["PAYPAL_BASE_URL"] == "https://api-m.paypal.com"


@pytest.mark.parametrize(
    ("clave", "tipo"),
    [
        ("sb_publishable_abc", "publishable"),
        ("sb_secret_abc", "secret"),
        ("eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.firma", "legacy"),
        ("cualquier-cosa", "desconocida"),
    ],
)
def test_tipo_clave_supabase(clave, tipo):
    assert checks.tipo_clave_supabase(clave) == tipo


@pytest.mark.parametrize(
    ("status", "ok", "texto"), [(200, True, "aceptada"), (401, False, "rechaza"), (404, False, "no encontrado")]
)
def test_probar_supabase(status, ok, texto):
    vistos = []

    def handler(req: httpx.Request) -> httpx.Response:
        vistos.append(req)
        return httpx.Response(status, json={})

    res = checks.probar_supabase("https://abc.supabase.co/", "sb_publishable_x", transport=httpx.MockTransport(handler))
    assert res[0] is ok and texto in res[1]
    assert str(vistos[0].url) == "https://abc.supabase.co/auth/v1/settings"
    assert vistos[0].headers["apikey"] == "sb_publishable_x"
    assert checks.probar_supabase("http://otro.com", "k")[0] is False


def test_detecta_secretos_en_variables_vite():
    import base64

    rol = base64.urlsafe_b64encode(b'{"role":"service_role"}').decode().rstrip("=")
    env = {
        "VITE_SUPABASE_URL": "https://abc.supabase.co",
        "VITE_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_ok",
        "VITE_SUPABASE_KEY": "sb_secret_mal",
        "VITE_SUPABASE_SERVICE_ROLE_KEY": "x",
        "VITE_ANON": f"eyJh.{rol}.firma",
        "SUPABASE_SECRET_KEY": "sb_secret_bien_aqui",
    }
    assert sorted(checks.variables_vite_peligrosas(env)) == [
        "VITE_ANON",
        "VITE_SUPABASE_KEY",
        "VITE_SUPABASE_SERVICE_ROLE_KEY",
    ]
