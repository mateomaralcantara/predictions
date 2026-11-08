import importlib.util
from datetime import date
from pathlib import Path

import pytest

from conftest import FIXTURES, ROOT
from packages.sources import loteriasdominicanas as fuente

_spec = importlib.util.spec_from_file_location("collector", ROOT / "apps" / "collector" / "tradicionales.py")
collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collector)

HTML = (FIXTURES / "loteriasdominicanas_2025-07-01.html").read_text(encoding="utf-8")
DIA = date(2025, 7, 1)


def test_parse_valida_fecha_nombre_y_cantidad():
    r = fuente.parse(HTML, DIA)
    assert {s.loteria: s.numeros for s in r.sorteos} == {
        "Lotería Nacional": (12, 45, 7),
        "Quiniela Leidsa": (3, 88, 61),
    }
    assert r.descartados_fecha == 1  # Loteka trae la fecha de ayer


class _Resp:
    def __init__(self, text: str, status: int = 200):
        self.text, self.status_code = text, status


class _Session:
    def __init__(self, pages: dict[date, str]):
        self.pages, self.pedidas = pages, []

    def get(self, url, headers=None, timeout=None):  # noqa: ARG002
        d = (
            next(d for d in self.pages if f"{d:%d-%m-%Y}" in url)
            if any(f"{d:%d-%m-%Y}" in url for d in self.pages)
            else None
        )
        self.pedidas.append(url)
        return _Resp(self.pages[d]) if d else _Resp("", 404)


def _csv(tmp_path: Path, filas: str) -> Path:
    p = tmp_path / "r.csv"
    p.write_text("fecha,loteria,primer,segundo,tercero\n" + filas, encoding="utf-8")
    return p


def _args(csv: Path, *extra: str):
    return collector.parser().parse_args(["--csv", str(csv), "--pausa", "0", "--fuente", "loteriasdominicanas", *extra])


def test_agrega_dias_nuevos_y_escribe_csv(tmp_path):
    csv = _csv(tmp_path, "2025-06-30,Lotería Nacional,1,2,3\n")
    s = _Session({DIA: HTML})
    stats = collector.ejecutar(_args(csv, "--hasta", "2025-07-01"), session=s)
    assert stats["nuevos"] == 2 and stats["dias"] == 1
    filas = collector.leer_csv(csv)
    assert filas[("2025-07-01", "Lotería Nacional")] == (12, 45, 7)
    # Volver a correr no duplica ni vuelve a descargar.
    s2 = _Session({DIA: HTML})
    assert collector.ejecutar(_args(csv, "--hasta", "2025-07-01"), session=s2)["dias"] == 0
    assert s2.pedidas == []


def test_ignora_pagina_obsoleta(tmp_path):
    # El día anterior ya tenía exactamente los mismos números: la página es la "última", no la del día.
    csv = _csv(tmp_path, "2025-06-30,Lotería Nacional,12,45,7\n2025-06-30,Quiniela Leidsa,3,88,61\n")
    stats = collector.ejecutar(_args(csv, "--hasta", "2025-07-01"), session=_Session({DIA: HTML}))
    assert stats["nuevos"] == 0 and stats["dias_obsoletos"] == 1


def test_rellena_huecos_y_dry_run(tmp_path):
    csv = _csv(tmp_path, "2025-06-29,Lotería Nacional,1,2,3\n2025-07-03,Lotería Nacional,4,5,6\n")
    objetivos = collector.fechas_objetivo(collector.leer_csv(csv), None, date(2025, 7, 3), rellenar=True)
    assert objetivos == [date(2025, 6, 30), date(2025, 7, 1), date(2025, 7, 2)]
    antes = csv.read_text()
    stats = collector.ejecutar(
        _args(csv, "--rellenar-huecos", "--hasta", "2025-07-03", "--dry-run"), session=_Session({DIA: HTML})
    )
    assert stats["nuevos"] == 2 and stats["dias_sin_datos"] == 2
    assert csv.read_text() == antes


@pytest.mark.parametrize(
    ("texto", "esperado"), [("01-07", DIA), ("1/7/2025", DIA), ("30-06-25", date(2025, 6, 30)), ("sin fecha", None)]
)
def test_fecha_bloque(texto, esperado):
    assert fuente._fecha_bloque(texto, DIA) == esperado


def test_labanca_parse_valida_fecha():
    from packages.sources import labanca

    html = (
        "<html><body><p>Gana Más 6 de noviembre de 2026</p>"
        "<p>El número ganador de Gana Más del 6 de noviembre de 2026 fue 06-29-97. Fuente: x</p></body></html>"
    )
    assert labanca.parse(html, date(2026, 11, 6)) == (6, 29, 97)
    assert labanca.parse(html, date(2026, 11, 5)) is None  # otra fecha: se rechaza
    assert labanca.parse(html.replace("06-29-97", "06-29-197"), date(2026, 11, 6)) is None


def test_labanca_no_pide_fechas_anteriores_al_inicio():
    from packages.sources import labanca

    class SinRed:
        def get(self, *a, **k):  # pragma: no cover - no debe llamarse
            raise AssertionError("no debía pedir nada")

    assert labanca.dia(date(2025, 7, 1), SinRed()).sorteos == []
