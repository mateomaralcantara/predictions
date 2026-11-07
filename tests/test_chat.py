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
