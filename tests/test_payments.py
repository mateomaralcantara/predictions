import asyncio
import json

import httpx
import pytest

from app.config import get_settings
from app.payments import PLANES, PaymentError, PayPalClient


def test_planes_publicos(client):
    body = client.get("/api/pagos/planes").json()
    assert body["pagos_habilitados"] is False
    assert [p["id"] for p in body["planes"]] == list(PLANES)


def test_ordenes_requieren_sesion(client):
    assert client.post("/api/pagos/ordenes", json={"plan": "platinum"}).status_code == 401
    assert client.post("/api/pagos/ordenes/ABC12345/captura").status_code == 401


def test_sin_credenciales_responde_503(client):
    from conftest import auth_header, registrar

    h = auth_header(registrar(client)["token"])
    assert client.post("/api/pagos/ordenes", json={"plan": "platinum"}, headers=h).status_code == 503


def _paypal(env, handler):
    env(PAYPAL_CLIENT_ID="cid", PAYPAL_SECRET="sec", PAYPAL_BASE_URL="https://paypal.test")
    return PayPalClient(get_settings(), transport=httpx.MockTransport(handler))


def test_crear_orden_usa_precio_del_servidor(env):
    enviados = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/v2/checkout/orders":
            assert request.headers["authorization"] == "Bearer tok"
            enviados.update(json.loads(request.content))
            return httpx.Response(
                201,
                json={
                    "id": "ORDER123",
                    "status": "CREATED",
                    "links": [{"rel": "approve", "href": "https://paypal.test/approve"}],
                },
            )
        return httpx.Response(404)

    orden = asyncio.run(_paypal(env, handler).crear_orden("platinum"))
    assert orden["id"] == "ORDER123" and orden["approve_url"] == "https://paypal.test/approve"
    unidad = enviados["purchase_units"][0]
    assert unidad["amount"] == {"currency_code": "USD", "value": PLANES["platinum"].precio}
    assert enviados["application_context"]["return_url"] == "http://localhost:5174/pago/exito"


def test_plan_desconocido(env):
    with pytest.raises(PaymentError) as exc:
        asyncio.run(_paypal(env, lambda r: httpx.Response(500)).crear_orden("gratis"))
    assert exc.value.status_code == 404


def test_capturar_orden(env):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok"})
        assert request.url.path == "/v2/checkout/orders/ORDER123/capture"
        return httpx.Response(
            201,
            json={
                "id": "ORDER123",
                "status": "COMPLETED",
                "purchase_units": [
                    {
                        "reference_id": "oraculo",
                        "payments": {"captures": [{"amount": {"value": "59.99", "currency_code": "USD"}}]},
                    }
                ],
            },
        )

    r = asyncio.run(_paypal(env, handler).capturar_orden("ORDER123"))
    assert r["estado"] == "COMPLETED" and r["plan"]["id"] == "oraculo" and r["monto"] == "59.99"


def test_capturar_orden_ya_pagada(env):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(422, json={})

    with pytest.raises(PaymentError) as exc:
        asyncio.run(_paypal(env, handler).capturar_orden("ORDER123"))
    assert exc.value.status_code == 409


def test_capturar_rechaza_id_invalido(env):
    with pytest.raises(PaymentError) as exc:
        asyncio.run(_paypal(env, lambda r: httpx.Response(500)).capturar_orden("../../v1/x"))
    assert exc.value.status_code == 400
