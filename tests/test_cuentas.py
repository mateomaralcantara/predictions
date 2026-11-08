"""Registro, login, niveles y el flujo completo de pago -> suscripción."""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest

from app import auth
from app.config import get_settings
from app.cuentas import activar_suscripcion, nivel_de
from app.db import Orden, Suscripcion, Usuario, session_factory, utcnow
from app.deps import get_paypal
from app.payments import PLANES, PayPalClient
from conftest import auth_header, registrar


def test_hash_password():
    h = auth.hash_password("secreto-123")
    assert h.startswith("scrypt$") and "secreto" not in h
    assert auth.verify_password("secreto-123", h)
    assert not auth.verify_password("otro", h)
    assert not auth.verify_password("x", "basura")
    assert auth.hash_password("secreto-123") != h  # sal aleatoria


def test_token_valido_expirado_y_manipulado():
    s = get_settings()
    tok = auth.crear_token(s, 7)
    assert auth.leer_token(s, tok) == 7
    assert auth.leer_token(s, tok + "x") is None
    import jwt

    vencido = jwt.encode({"sub": "7", "exp": 1, "typ": "access"}, s.secret_key, algorithm="HS256")
    assert auth.leer_token(s, vencido) is None
    ajeno = jwt.encode(
        {"sub": "7", "exp": 9999999999, "typ": "access"}, "otra-clave-de-32-bytes-o-mas-123456", algorithm="HS256"
    )
    assert auth.leer_token(s, ajeno) is None


def test_registro_login_y_perfil(client):
    sesion = registrar(client, email="  Ana@Example.COM ")
    assert sesion["usuario"]["email"] == "ana@example.com"
    assert sesion["usuario"]["nivel"] == 0 and sesion["usuario"]["plan"]["id"] == "gratis"

    r = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "clave-segura-1"})
    assert r.status_code == 200
    yo = client.get("/api/auth/yo", headers=auth_header(r.json()["token"])).json()
    assert yo["nombre"] == "Ana" and yo["limites"]["jugadas"] == 2


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"email": "no-es-correo", "password": "clave-segura-1", "nombre": "A b"}, 422),
        ({"email": "b@example.com", "password": "corta", "nombre": "Bea"}, 422),
        ({"email": "b@example.com", "password": "12345678", "nombre": "Bea"}, 422),
    ],
)
def test_registro_valida(client, body, status):
    assert client.post("/api/auth/registro", json=body).status_code == status


def test_registro_duplicado(client):
    registrar(client)
    r = client.post(
        "/api/auth/registro", json={"email": "ANA@example.com", "password": "otra-clave-1", "nombre": "Xavi"}
    )
    assert r.status_code == 409


def test_login_incorrecto_no_revela_si_existe(client):
    registrar(client)
    a = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "mala-clave"})
    b = client.post("/api/auth/login", json={"email": "nadie@example.com", "password": "mala-clave"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_token_invalido_da_401(client):
    assert client.get("/api/auth/yo").status_code == 401
    assert client.get("/api/auth/yo", headers=auth_header("x.y.z")).status_code == 401
    # Un token roto en un endpoint público también se rechaza (no se ignora en silencio).
    assert client.get("/api/predicciones/loto", headers=auth_header("x.y.z")).status_code == 401


def test_cambiar_password(client):
    h = auth_header(registrar(client)["token"])
    assert (
        client.post("/api/auth/password", json={"actual": "mala", "nueva": "nueva-clave-1"}, headers=h).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/password", json={"actual": "clave-segura-1", "nueva": "nueva-clave-1"}, headers=h
        ).status_code
        == 200
    )
    assert (
        client.post("/api/auth/login", json={"email": "ana@example.com", "password": "nueva-clave-1"}).status_code
        == 200
    )


def test_rate_limit_login(client):
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"})
    r = client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"})
    assert r.status_code == 429 and "retry-after" in r.headers


def _dar_plan(email: str, plan: str, dias: int = 30) -> None:
    with session_factory(get_settings().app_database_url)() as db:
        u = db.query(Usuario).filter_by(email=email).one()
        db.add(Suscripcion(usuario_id=u.id, plan=plan, inicio=utcnow(), fin=utcnow() + timedelta(days=dias)))
        db.commit()


def test_limites_por_nivel_en_predicciones_e_historial(client):
    anon = client.get("/api/predicciones/loto", params={"jugadas": 8}).json()
    assert len(anon["jugadas"]) == 2 and anon["limitado"] and anon["max_jugadas"] == 2

    h = auth_header(registrar(client)["token"])
    _dar_plan("ana@example.com", "platinum")
    premium = client.get("/api/predicciones/loto", params={"jugadas": 8}, headers=h).json()
    assert len(premium["jugadas"]) == 8 and not premium["limitado"] and premium["nivel"] == 2

    info = client.get("/api/estadisticas/numero/10", params={"limite": 500}).json()
    assert info["max_historial"] == 10
    assert client.get("/api/estadisticas/numero/10", params={"limite": 500}, headers=h).json()["max_historial"] == 500


def test_suscripcion_vencida_no_cuenta(client):
    h = auth_header(registrar(client)["token"])
    _dar_plan("ana@example.com", "oraculo", dias=-1)
    assert client.get("/api/auth/yo", headers=h).json()["nivel"] == 0


def test_activar_suscripcion_acumula_dias_e_idempotente():
    with session_factory(get_settings().app_database_url)() as db:
        u = Usuario(email="z@example.com", nombre="Z", password_hash="x")
        db.add(u)
        db.flush()
        o1 = Orden(paypal_id="O1XXXXX", usuario_id=u.id, plan="explorador", monto="9.99", moneda="USD")
        o2 = Orden(paypal_id="O2XXXXX", usuario_id=u.id, plan="explorador", monto="9.99", moneda="USD")
        db.add_all([o1, o2])
        db.flush()
        s1 = activar_suscripcion(db, u, o1)
        db.flush()
        assert activar_suscripcion(db, u, o1) is s1
        s2 = activar_suscripcion(db, u, o2)
        db.flush()
        assert s2.inicio == s1.fin and (s2.fin - s1.inicio).days == 60
        assert nivel_de(db, u) == PLANES["explorador"].nivel


def _mock_paypal(capturas: list, monto: str = "29.99", estado: str = "COMPLETED", plan: str = "platinum"):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/v2/checkout/orders":
            return httpx.Response(
                201, json={"id": "ORDER999", "status": "CREATED", "links": [{"rel": "approve", "href": "https://pp/a"}]}
            )
        if request.url.path.endswith("/capture"):
            capturas.append(request.url.path)
            return httpx.Response(
                201,
                json={
                    "id": "ORDER999",
                    "status": estado,
                    "purchase_units": [
                        {
                            "reference_id": plan,
                            "payments": {"captures": [{"amount": {"value": monto, "currency_code": "USD"}}]},
                        }
                    ],
                },
            )
        return httpx.Response(404)

    return handler


@pytest.fixture
def paypal_mock(env, client):
    env(PAYPAL_CLIENT_ID="cid", PAYPAL_SECRET="sec", PAYPAL_BASE_URL="https://paypal.test")
    estado: dict = {"capturas": [], "kw": {}}

    def factory() -> PayPalClient:
        return PayPalClient(
            get_settings(), transport=httpx.MockTransport(_mock_paypal(estado["capturas"], **estado["kw"]))
        )

    client.app.dependency_overrides[get_paypal] = factory
    yield estado
    client.app.dependency_overrides.clear()


def test_flujo_completo_de_pago_activa_plan(client, paypal_mock):
    h = auth_header(registrar(client)["token"])
    orden = client.post("/api/pagos/ordenes", json={"plan": "platinum"}, headers=h)
    assert orden.status_code == 201 and orden.json()["approve_url"] == "https://pp/a"

    cap = client.post("/api/pagos/ordenes/ORDER999/captura", headers=h)
    assert cap.status_code == 200, cap.text
    assert cap.json()["usuario"]["nivel"] == 2 and cap.json()["usuario"]["suscripcion_vence"]

    # Repetir la captura (recargar la página de éxito) no vuelve a cobrar.
    again = client.post("/api/pagos/ordenes/ORDER999/captura", headers=h)
    assert again.status_code == 200 and len(paypal_mock["capturas"]) == 1

    pagos = client.get("/api/auth/pagos", headers=h).json()
    assert pagos[0]["estado"] == "COMPLETADA" and pagos[0]["monto"] == "29.99"


def test_no_se_puede_capturar_orden_ajena(client, paypal_mock):
    h1 = auth_header(registrar(client)["token"])
    client.post("/api/pagos/ordenes", json={"plan": "platinum"}, headers=h1)
    h2 = auth_header(registrar(client, email="eve@example.com")["token"])
    assert client.post("/api/pagos/ordenes/ORDER999/captura", headers=h2).status_code == 404
    assert paypal_mock["capturas"] == []


def test_monto_distinto_no_activa_plan(client, paypal_mock):
    paypal_mock["kw"] = {"monto": "0.01"}
    h = auth_header(registrar(client)["token"])
    client.post("/api/pagos/ordenes", json={"plan": "platinum"}, headers=h)
    assert client.post("/api/pagos/ordenes/ORDER999/captura", headers=h).status_code == 402
    assert client.get("/api/auth/yo", headers=h).json()["nivel"] == 0
    assert client.get("/api/auth/pagos", headers=h).json()[0]["estado"] == "REVISION"


def test_cli_importar_avisa_destino_local(capsys, tmp_path, env):
    from app import cli

    env(DATABASE_URL="", SUPABASE_DB_URL="", APP_DATABASE_URL=f"sqlite:///{tmp_path / 'c.db'}")
    csv = tmp_path / "r.csv"
    csv.write_text("fecha,loteria,primer,segundo,tercero\n2025-01-01,X,1,2,3\n", encoding="utf-8")
    assert cli.main(["importar-csv", str(csv)]) == 0
    out = capsys.readouterr().out
    assert "SQLite LOCAL" in out and "Importados 1" in out
    assert cli._ocultar("postgresql://u:secreta@h:5432/db") == "postgresql://u:***@h:5432/db"
