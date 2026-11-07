"""Estadísticas puras sobre resultados tradicionales (sin I/O)."""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from .repository import Resultado

NUMERO_MIN, NUMERO_MAX = 0, 99


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos: 'Lotería Más' -> 'loteria mas'."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower().strip()


def filtrar(
    rows: Iterable[Resultado],
    loteria: str | None = None,
    year: int | None = None,
    desde: date | None = None,
) -> list[Resultado]:
    filtro = normalizar(loteria) if loteria else None
    out = []
    for r in rows:
        if filtro and filtro not in normalizar(r.loteria):
            continue
        if year and r.fecha.year != year:
            continue
        if desde and r.fecha < desde:
            continue
        out.append(r)
    return out


def top_numeros(rows: Sequence[Resultado], cantidad: int = 10) -> list[dict]:
    conteo = Counter(n for r in rows for n in r.numeros)
    return [{"numero": n, "apariciones": c} for n, c in conteo.most_common(cantidad)]


def ultimos(rows: Sequence[Resultado], cantidad: int = 10) -> list[dict]:
    ordenados = sorted(rows, key=lambda r: (r.fecha, r.loteria), reverse=True)
    return [r.as_dict() for r in ordenados[:cantidad]]


def combinaciones(rows: Sequence[Resultado], cantidad: int = 10) -> list[dict]:
    """Ternas más repetidas sin importar el orden de salida."""
    conteo = Counter(tuple(sorted(r.numeros)) for r in rows)
    return [{"combinacion": list(c), "apariciones": n} for c, n in conteo.most_common(cantidad)]


def apariciones_numero(rows: Sequence[Resultado], numero: int, limite: int = 100) -> dict:
    hits = [r for r in rows if numero in r.numeros]
    hits.sort(key=lambda r: (r.fecha, r.loteria), reverse=True)
    posiciones = Counter()
    for r in hits:
        for nombre, valor in zip(("primer", "segundo", "tercero"), r.numeros, strict=True):
            if valor == numero:
                posiciones[nombre] += 1
    return {
        "numero": numero,
        "total": len(hits),
        "ultima_fecha": hits[0].fecha.isoformat() if hits else None,
        "posiciones": {k: posiciones.get(k, 0) for k in ("primer", "segundo", "tercero")},
        "sorteos": [r.as_dict() for r in hits[:limite]],
    }


def atrasados(rows: Sequence[Resultado], cantidad: int = 10) -> list[dict]:
    """Números (00-99) que más sorteos llevan sin salir."""
    if not rows:
        return []
    ordenados = sorted(rows, key=lambda r: (r.fecha, r.loteria))
    ultima_vez: dict[int, int] = {}
    for i, r in enumerate(ordenados):
        for n in r.numeros:
            ultima_vez[n] = i
    total = len(ordenados)
    universo = range(NUMERO_MIN, NUMERO_MAX + 1)
    filas = []
    for n in universo:
        idx = ultima_vez.get(n)
        filas.append(
            {
                "numero": n,
                "sorteos_sin_salir": total - 1 - idx if idx is not None else total,
                "ultima_fecha": ordenados[idx].fecha.isoformat() if idx is not None else None,
            }
        )
    filas.sort(key=lambda f: f["sorteos_sin_salir"], reverse=True)
    return filas[:cantidad]


def loterias(rows: Sequence[Resultado]) -> list[dict]:
    info: dict[str, dict] = {}
    for r in rows:
        item = info.setdefault(r.loteria, {"nombre": r.loteria, "sorteos": 0, "desde": r.fecha, "hasta": r.fecha})
        item["sorteos"] += 1
        item["desde"] = min(item["desde"], r.fecha)
        item["hasta"] = max(item["hasta"], r.fecha)
    out = sorted(info.values(), key=lambda x: x["sorteos"], reverse=True)
    return [{**x, "desde": x["desde"].isoformat(), "hasta": x["hasta"].isoformat()} for x in out]


def resumen(rows: Sequence[Resultado], dias_recientes: int = 30) -> dict:
    """Datos reales para las tarjetas de la portada."""
    if not rows:
        return {"total_sorteos": 0, "ultimo_sorteo": None, "mas_frecuente_reciente": None, "mas_atrasado": None}
    ultimo = max(rows, key=lambda r: (r.fecha, r.loteria))
    desde = ultimo.fecha - timedelta(days=dias_recientes)
    recientes = [r for r in rows if r.fecha > desde]
    top = top_numeros(recientes, 1)
    atrasado = atrasados(rows, 1)
    return {
        "total_sorteos": len(rows),
        "desde": min(r.fecha for r in rows).isoformat(),
        "hasta": ultimo.fecha.isoformat(),
        "ultimo_sorteo": ultimo.as_dict(),
        "dias_recientes": dias_recientes,
        "mas_frecuente_reciente": top[0] if top else None,
        "mas_atrasado": atrasado[0] if atrasado else None,
    }
