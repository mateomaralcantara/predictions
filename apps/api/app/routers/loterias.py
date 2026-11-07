from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as PathParam

from .. import stats, tradicional
from ..cuentas import limites_de
from ..deps import Nivel, get_repository
from ..repository import ResultsRepository

router = APIRouter(prefix="/api/loterias", tags=["loterías"])

Repo = Annotated[ResultsRepository, Depends(get_repository)]
Nombre = Annotated[str, PathParam(min_length=2, max_length=60)]


def _sorteos(repo: ResultsRepository, nombre: str):
    rows = stats.de_loteria(repo.all(), nombre)
    if not rows:
        raise HTTPException(404, f"No hay datos de la lotería «{nombre}».")
    return rows


@router.get("/{nombre}")
def detalle(nombre: Nombre, repo: Repo) -> dict:
    """Todo lo de una lotería en una sola respuesta (para su pantalla de detalle)."""
    rows = _sorteos(repo, nombre)
    return {
        "nombre": rows[0].loteria,
        "resumen": stats.resumen(rows),
        "ultimos": stats.ultimos(rows, 20),
        "top": stats.top_numeros(rows, 10),
        "atrasados": stats.atrasados(rows, 10),
        "combinaciones": stats.combinaciones(rows, 8),
        "pales": stats.pales(rows, 8),
        "posiciones": stats.top_por_posicion(rows, 5),
        "mapa": stats.mapa_numeros(rows),
        "dias_semana": stats.por_dia_semana(rows),
    }


@router.get("/{nombre}/pronostico")
def pronostico(nombre: Nombre, repo: Repo, nivel: Nivel, jugadas: Annotated[int, Query(ge=1, le=10)] = 5) -> dict:
    rows = _sorteos(repo, nombre)
    maximo = limites_de(nivel).jugadas
    try:
        data = tradicional.pronostico(rows, rows[0].loteria, min(jugadas, maximo))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**data, "solicitadas": jugadas, "max_jugadas": maximo, "limitado": jugadas > maximo, "nivel": nivel}
