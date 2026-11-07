"""Expone los predictores heurísticos de ``packages/games`` vía API.

Las jugadas se cachean por (juego, último sorteo, cantidad): mientras no haya
un sorteo nuevo, todos los usuarios ven las mismas jugadas y el cálculo pesado
solo se hace una vez.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from packages.games.loto import predictor as loto
from packages.games.superkino import predictor as superkino

AVISO = (
    "Jugadas generadas con criterios heurísticos sobre el histórico. "
    "En un sorteo justo todas las combinaciones tienen la misma probabilidad."
)

JUEGOS = {
    "loto": {"nombre": "Loto LEIDSA", "reglas": "6 números del 1 al 40 + Más (1-12) + Súper Más (1-15)"},
    "superkino": {"nombre": "SuperKino", "reglas": "Jugadas de 10 números del 1 al 84 (salen 20 por sorteo)"},
}

_cache: dict[tuple, dict] = {}
_lock = threading.Lock()


def _seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:8], 16)


def _paridad(nums: list[int]) -> dict:
    pares = sum(1 for n in nums if n % 2 == 0)
    return {"pares": pares, "impares": len(nums) - pares}


def predecir_loto(csv_path: Path, jugadas: int) -> dict:
    draws = loto.load_csv(str(csv_path))
    if not draws:
        raise FileNotFoundError(f"Sin histórico de Loto en {csv_path}")
    ultimo = draws[-1]
    key = ("loto", ultimo.fecha, jugadas)
    with _lock:
        if key in _cache:
            return _cache[key]
    panels = loto.panels(draws, jugadas, _seed(*key), half=60, candidates=2000, max_overlap=4)
    extras = loto.extras(draws, len(panels))
    data = {
        "juego": "loto",
        **JUEGOS["loto"],
        "historico": {"sorteos": len(draws), "desde": draws[0].fecha, "hasta": ultimo.fecha},
        "ultimo_sorteo": {
            "fecha": ultimo.fecha,
            "numeros": list(ultimo.nums),
            "mas": ultimo.mas,
            "super_mas": ultimo.super_mas,
        },
        "jugadas": [
            {"numeros": nums, "mas": mas, "super_mas": sup, **_paridad(nums)}
            for nums, (mas, sup) in zip(panels, extras, strict=False)
        ],
        "aviso": AVISO,
    }
    with _lock:
        _cache[key] = data
    return data


def predecir_superkino(csv_path: Path, jugadas: int) -> dict:
    df = superkino._load_loose_rows(str(csv_path))
    if df.empty:
        raise FileNotFoundError(f"Sin histórico de SuperKino en {csv_path}")
    fechas = df["fecha"].tolist()
    historico = superkino.cargar_historico(str(csv_path))
    key = ("superkino", fechas[-1], jugadas)
    with _lock:
        if key in _cache:
            return _cache[key]
    panels = superkino.generar_panels(historico=historico, panels=jugadas, k=10, seed=_seed(*key), n_cands=1200)
    ultimo = sorted(int(x) for x in historico[-1])
    data = {
        "juego": "superkino",
        **JUEGOS["superkino"],
        "historico": {"sorteos": len(historico), "desde": fechas[0], "hasta": fechas[-1]},
        "ultimo_sorteo": {"fecha": fechas[-1], "numeros": ultimo},
        "jugadas": [{"numeros": sorted(int(n) for n in p), **_paridad([int(n) for n in p])} for p in panels],
        "aviso": AVISO,
    }
    with _lock:
        _cache[key] = data
    return data


def clear_cache() -> None:
    with _lock:
        _cache.clear()


__all__ = ["JUEGOS", "AVISO", "predecir_loto", "predecir_superkino", "clear_cache"]
