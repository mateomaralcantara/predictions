from datetime import date, timedelta

import pytest

from app import stats, tradicional
from app.repository import Resultado


def _serie(n: int = 120, nombre: str = "Lotería Nacional") -> list[Resultado]:
    base = date(2025, 1, 1)
    return [
        Resultado(base + timedelta(days=i), nombre, (i * 7) % 100, (i * 13 + 5) % 100, (i * 29 + 11) % 100)
        for i in range(n)
    ]


def test_de_loteria_es_exacta_y_sin_acentos():
    rows = _serie(5) + _serie(5, "Quiniela Leidsa")
    assert len(stats.de_loteria(rows, "loteria nacional")) == 5
    assert stats.de_loteria(rows, "nacional") == []


def test_mapa_cubre_00_a_99_y_suma_bien():
    rows = _serie(50)
    mapa = stats.mapa_numeros(rows)
    assert [m["numero"] for m in mapa] == list(range(100))
    assert sum(m["apariciones"] for m in mapa) == 150
    for m in mapa:
        assert m["apariciones"] == m["primer"] + m["segundo"] + m["tercero"]


def test_pales_y_posiciones():
    rows = [Resultado(date(2025, 1, i), "X", 1, 2, 3) for i in range(1, 4)] + [
        Resultado(date(2025, 1, 9), "X", 5, 5, 6)
    ]
    assert stats.pales(rows, 1) == [{"pale": [1, 2], "apariciones": 3}] or stats.pales(rows, 1)[0]["apariciones"] == 3
    assert {"pale": [5, 5], "apariciones": 1} not in stats.pales(
        rows, 10
    )  # pareja de un número consigo mismo no cuenta
    assert stats.top_por_posicion(rows, 1)["primer"] == [{"numero": 1, "apariciones": 3}]


def test_pronostico_determinista_diverso_y_valido():
    rows = _serie()
    a = tradicional.pronostico(rows, "Lotería Nacional", 6)
    tradicional.clear_cache()
    b = tradicional.pronostico(rows, "Lotería Nacional", 6)
    assert a == b and len(a["jugadas"]) == 6
    for i, j in enumerate(a["jugadas"]):
        assert len(set(j["numeros"])) == 3 and all(0 <= n <= 99 for n in j["numeros"])
        assert len(j["pales"]) == 3
        for k in a["jugadas"][i + 1 :]:
            assert len(set(j["numeros"]) & set(k["numeros"])) <= 1
    assert len(a["calientes"]) == len(a["frios"]) == 5


def test_pronostico_exige_historial_minimo():
    with pytest.raises(ValueError):
        tradicional.pronostico(_serie(10), "X", 3)


def test_endpoints_detalle_y_pronostico(client, monkeypatch):
    from app.deps import get_repository

    detalle = client.get("/api/loterias/Lotería Nacional").json()
    assert detalle["nombre"] == "Lotería Nacional"
    assert detalle["resumen"]["total_sorteos"] == 3
    assert len(detalle["mapa"]) == 100 and len(detalle["dias_semana"]) == 7
    assert client.get("/api/loterias/No Existe").status_code == 404
    # Con 3 sorteos no hay pronóstico posible.
    assert client.get("/api/loterias/Lotería Nacional/pronostico").status_code == 422

    repo = get_repository()
    monkeypatch.setattr(repo, "all", lambda: _serie())
    p = client.get("/api/loterias/loteria nacional/pronostico", params={"jugadas": 8}).json()
    assert len(p["jugadas"]) == 2 and p["limitado"] and p["max_jugadas"] == 2
