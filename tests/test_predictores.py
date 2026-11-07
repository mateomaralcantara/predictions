import numpy as np

from conftest import ROOT
from packages.games.loto import predictor as loto
from packages.games.superkino import predictor as superkino

LOTO_CSV = ROOT / "apps" / "api" / "leidsa" / "lotto" / "loto_leidsa.csv"
SK_CSV = ROOT / "apps" / "api" / "leidsa" / "superkino" / "superkino_historico.csv"


def test_loto_load_csv_valida_reglas():
    draws = loto.load_csv(str(LOTO_CSV))
    assert len(draws) > 1000
    fechas = [d.fecha for d in draws]
    assert fechas == sorted(fechas) and len(set(fechas)) == len(fechas)
    assert all(len(set(d.nums)) == 6 and all(1 <= n <= 40 for n in d.nums) for d in draws)


def test_loto_shape():
    assert loto.shape([3, 8, 15, 22, 29, 36])
    assert not loto.shape([1, 2, 3, 4, 5, 6])
    assert not loto.shape([2, 4, 6, 8, 30, 40])  # 6 pares


def test_loto_panels_reproducibles_y_diversos():
    draws = loto.load_csv(str(LOTO_CSV))
    a = loto.panels(draws, 6, 42, 60, 1500, 3)
    b = loto.panels(draws, 6, 42, 60, 1500, 3)
    assert a == b and len(a) == 6
    for i, x in enumerate(a):
        assert loto.shape(x)
        for y in a[i + 1 :]:
            assert len(set(x) & set(y)) <= 3


def test_superkino_invert_weights_no_explota_con_ceros():
    w = np.array([0.0, 0.0, 0.5, 0.5])
    inv = superkino.invert_weights(w)
    assert np.isclose(inv.sum(), 1.0)
    assert inv.max() <= 2.5 * inv.min()


def test_superkino_panels_rapidos_y_validos():
    import time

    hist = superkino.cargar_historico(str(SK_CSV))
    t = time.perf_counter()
    panels = superkino.generar_panels(hist, panels=8, k=10, seed=7, n_cands=300)
    assert time.perf_counter() - t < 10, "regresión de rendimiento del predictor SuperKino"
    assert len(panels) == 8
    for p in panels:
        assert len(set(p)) == 10 and all(1 <= n <= 84 for n in p)
