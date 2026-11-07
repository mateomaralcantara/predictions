import asyncio

import pytest

from app import chat
from app.config import get_settings
from app.repository import descartar_repeticiones, load_csv
from conftest import FIXTURES

ROWS, _ = descartar_repeticiones(load_csv(FIXTURES / "resultados.csv"))


@pytest.mark.parametrize(
    ("pregunta", "intencion", "loteria", "year", "cantidad", "numero"),
    [
        ("Top 5 números más salidos de 2024 en la Nacional", "top", "loteria nacional", 2024, 5, None),
        ("últimos 3 resultados de Leidsa", "ultimos", "quiniela leidsa", None, 3, None),
        ("¿Cuándo salió el 23?", "numero", None, None, 10, 23),
        ("cuantas veces ha salido el numero 7 en loteka", "numero", "loteka", None, 10, 7),
        ("números más atrasados", "atrasados", None, None, 10, None),
        ("combinaciones más repetidas", "combinaciones", None, None, 10, None),
        ("hola", "ayuda", None, None, 10, None),
        ("xyz", "desconocida", None, None, 10, None),
    ],
)
def test_interpretar(pregunta, intencion, loteria, year, cantidad, numero):
    c = chat.interpretar(pregunta)
    assert (c.intencion, c.loteria, c.year, c.cantidad, c.numero) == (intencion, loteria, year, cantidad, numero)


def test_year_no_se_confunde_con_numero():
    c = chat.interpretar("top 3 números del 2025")
    assert c.intencion == "top" and c.year == 2025 and c.cantidad == 3


def test_cantidad_acotada():
    assert chat.interpretar("top 999 numeros").cantidad == 50


def test_respuesta_local_top():
    r = chat.responder_local(chat.interpretar("top 1 números de la nacional"), ROWS)
    assert "10 — 3 veces" in r.texto


def test_respuesta_sin_datos():
    r = chat.responder_local(chat.interpretar("top numeros de 2030"), ROWS)
    assert "No hay sorteos" in r.texto


def test_responder_agrega_aviso_y_no_llama_openai_sin_clave():
    settings = get_settings()
    assert not settings.openai_enabled
    r = asyncio.run(chat.responder("últimos resultados de la nacional", ROWS, settings))
    assert r.intencion == "ultimos"
    assert chat.DISCLAIMER in r.texto


def test_pregunta_vacia():
    r = asyncio.run(chat.responder("   ", ROWS, get_settings()))
    assert r.intencion == "vacia"


def test_gemini_redacta_la_respuesta(env, monkeypatch):
    import json

    import httpx

    llamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "El 10 es el que más sale."}]}}]}
        )

    env(GEMINI_API_KEY="clave-gemini")
    monkeypatch.setattr(chat, "_gemini_transport", httpx.MockTransport(handler))
    s = get_settings()
    assert s.ia_proveedor == "gemini"
    r = asyncio.run(chat.responder("top 1 números de la nacional", ROWS, s))
    assert r.texto.startswith("El 10 es el que más sale.")
    req = llamadas[0]
    assert req.headers["x-goog-api-key"] == "clave-gemini"
    assert "gemini-2.5-flash:generateContent" in str(req.url)
    body = json.loads(req.content)
    assert "10 — 3 veces" in body["systemInstruction"]["parts"][0]["text"]  # datos reales como contexto


def test_si_gemini_falla_se_usa_la_respuesta_local(env, monkeypatch):
    import httpx

    env(GEMINI_API_KEY="clave-gemini")
    monkeypatch.setattr(chat, "_gemini_transport", httpx.MockTransport(lambda r: httpx.Response(429, json={})))
    r = asyncio.run(chat.responder("top 1 números de la nacional", ROWS, get_settings()))
    assert "10 — 3 veces" in r.texto
