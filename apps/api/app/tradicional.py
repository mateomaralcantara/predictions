"""Pronóstico heurístico para loterías tradicionales (3 números 00-99).

Combina dos señales del histórico de la propia lotería:
- frecuencia con peso por recencia (los sorteos recientes cuentan más);
- atraso (sorteos desde la última aparición, acotado).

Es una heurística de selección: en un sorteo justo cada número tiene la misma
probabilidad. Las jugadas son deterministas por (lotería, último sorteo).
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Sequence

import numpy as np

from .repository import Resultado

AVISO = (
    "Números elegidos con criterios heurísticos (frecuencia reciente y atraso). "
    "En un sorteo justo todos los números tienen la misma probabilidad."
)
MIN_SORTEOS = 30
_cache: dict[tuple, dict] = {}
_lock = threading.Lock()


def _seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _norm(x: np.ndarray) -> np.ndarray:
    rango = x.max() - x.min()
    return (x - x.min()) / rango if rango > 0 else np.zeros_like(x)


def puntuaciones(rows: Sequence[Resultado], half_life: int = 90) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (score, frecuencia_reciente, atraso) para los números 0..99."""
    n = len(rows)
    pesos = 0.5 ** ((n - 1 - np.arange(n)) / max(1, half_life))
    freq = np.zeros(100)
    ultimo = np.full(100, -1)
    for i, r in enumerate(rows):
        for num in r.numeros:
            if 0 <= num <= 99:
                freq[num] += pesos[i]
                ultimo[num] = i
    atraso = np.where(ultimo >= 0, n - 1 - ultimo, n).astype(float)
    esperado = 100 / 3  # cada número sale ~1 de cada 33 sorteos
    atraso_acotado = np.minimum(atraso, 3 * esperado)
    score = 0.6 * _norm(freq) + 0.4 * _norm(atraso_acotado) + 0.05
    return score, freq, atraso


def pronostico(rows: Sequence[Resultado], loteria: str, jugadas: int) -> dict:
    rows = sorted(rows, key=lambda r: r.fecha)
    if len(rows) < MIN_SORTEOS:
        raise ValueError(f"Se necesitan al menos {MIN_SORTEOS} sorteos para un pronóstico.")
    ultimo = rows[-1]
    key = (loteria, ultimo.fecha, len(rows), jugadas)
    with _lock:
        if key in _cache:
            return _cache[key]

    score, freq, atraso = puntuaciones(rows)
    rng = np.random.default_rng(_seed(*key))
    p = score**1.5
    p = p / p.sum()
    elegidas: list[list[int]] = []
    intentos = 0
    while len(elegidas) < jugadas and intentos < 5000:
        intentos += 1
        cand = [int(x) for x in rng.choice(100, size=3, replace=False, p=p)]
        if all(len(set(cand) & set(e)) <= 1 for e in elegidas):
            elegidas.append(cand)

    calientes = [int(i) for i in np.argsort(-freq)[:5]]
    frios = [int(i) for i in np.argsort(-atraso)[:5]]
    data = {
        "loteria": loteria,
        "basado_en": {"sorteos": len(rows), "hasta": ultimo.fecha.isoformat()},
        "jugadas": [{"numeros": j, "pales": [[j[0], j[1]], [j[0], j[2]], [j[1], j[2]]]} for j in elegidas],
        "calientes": calientes,
        "frios": frios,
        "aviso": AVISO,
    }
    with _lock:
        _cache[key] = data
    return data


def clear_cache() -> None:
    with _lock:
        _cache.clear()
