from datetime import date

from app import stats
from app.repository import Resultado, load_csv
from conftest import FIXTURES

ROWS = load_csv(FIXTURES / "resultados.csv")


def test_load_csv_ignora_filas_invalidas():
    assert len(ROWS) == 8
    assert all(isinstance(r.fecha, date) for r in ROWS)


def test_normalizar_quita_acentos():
    assert stats.normalizar("Lotería  Más") == "loteria  mas"


def test_filtrar_por_loteria_y_year():
    nacional = stats.filtrar(ROWS, loteria="nacional")
    assert {r.loteria for r in nacional} == {"Lotería Nacional"}
    assert len(stats.filtrar(ROWS, year=2024)) == 1


def test_top_numeros():
    top = stats.top_numeros(ROWS, 2)
    assert top[0] == {"numero": 10, "apariciones": 6}
    assert top[1]["numero"] in {11, 20, 30}


def test_ultimos_ordenados_desc():
    ult = stats.ultimos(ROWS, 3)
    fechas = [u["fecha"] for u in ult]
    assert fechas == sorted(fechas, reverse=True)
    assert ult[0]["fecha"] == "2025-01-03"


def test_combinaciones_ignoran_orden():
    comb = stats.combinaciones(ROWS, 1)
    assert comb[0] == {"combinacion": [10, 20, 30], "apariciones": 2}


def test_apariciones_numero_posiciones():
    info = stats.apariciones_numero(ROWS, 10)
    assert info["total"] == 6
    assert info["posiciones"] == {"primer": 4, "segundo": 0, "tercero": 2}
    assert info["ultima_fecha"] == "2025-01-03"


def test_atrasados_incluye_numeros_que_nunca_salieron():
    atr = stats.atrasados(ROWS, 100)
    assert len(atr) == 100
    nunca = [a for a in atr if a["ultima_fecha"] is None]
    assert nunca and nunca[0]["sorteos_sin_salir"] == len(ROWS)


def test_resumen_vacio_y_con_datos():
    assert stats.resumen([])["ultimo_sorteo"] is None
    r = stats.resumen(ROWS)
    assert r["total_sorteos"] == 8
    assert r["hasta"] == "2025-01-03"
    assert r["mas_frecuente_reciente"]["numero"] == 10


def test_resultado_as_dict():
    r = Resultado(date(2025, 1, 1), "X", 1, 2, 3)
    assert r.as_dict() == {"fecha": "2025-01-01", "loteria": "X", "numeros": [1, 2, 3]}
