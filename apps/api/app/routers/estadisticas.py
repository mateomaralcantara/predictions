from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi import Path as PathParam

from .. import stats
from ..cuentas import limites_de
from ..deps import Nivel, get_repository
from ..repository import ResultsRepository

router = APIRouter(prefix="/api", tags=["estadísticas"])

Repo = Annotated[ResultsRepository, Depends(get_repository)]
Loteria = Annotated[str | None, Query(max_length=60, description="Fragmento del nombre, p. ej. 'nacional'")]
Year = Annotated[int | None, Query(ge=2000, le=2100)]
Limite = Annotated[int, Query(ge=1, le=100)]


@router.get("/loterias")
def listar_loterias(repo: Repo) -> list[dict]:
    return stats.loterias(repo.all())


@router.get("/estadisticas/resumen")
def resumen(repo: Repo, loteria: Loteria = None) -> dict:
    return stats.resumen(stats.filtrar(repo.all(), loteria=loteria))


@router.get("/estadisticas/top")
def top(repo: Repo, loteria: Loteria = None, year: Year = None, limite: Limite = 10) -> list[dict]:
    return stats.top_numeros(stats.filtrar(repo.all(), loteria=loteria, year=year), limite)


@router.get("/estadisticas/ultimos")
def ultimos(repo: Repo, loteria: Loteria = None, limite: Limite = 10) -> list[dict]:
    return stats.ultimos(stats.filtrar(repo.all(), loteria=loteria), limite)


@router.get("/estadisticas/combinaciones")
def combinaciones(repo: Repo, loteria: Loteria = None, year: Year = None, limite: Limite = 10) -> list[dict]:
    return stats.combinaciones(stats.filtrar(repo.all(), loteria=loteria, year=year), limite)


@router.get("/estadisticas/atrasados")
def atrasados(repo: Repo, loteria: Loteria = None, limite: Limite = 10) -> list[dict]:
    return stats.atrasados(stats.filtrar(repo.all(), loteria=loteria), limite)


@router.get("/estadisticas/numero/{numero}")
def numero(
    repo: Repo,
    numero: Annotated[int, PathParam(ge=0, le=99)],
    nivel: Nivel,
    loteria: Loteria = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict:
    maximo = limites_de(nivel).historial
    info = stats.apariciones_numero(stats.filtrar(repo.all(), loteria=loteria), numero, min(limite, maximo))
    return {**info, "max_historial": maximo, "limitado": limite > maximo and info["total"] > maximo}


# --- Compatibilidad con el frontend anterior ---------------------------------


@router.get("/numeros-mas-salidores", include_in_schema=False)
def numeros_mas_salidores_legacy(repo: Repo) -> list[dict]:
    return stats.top_numeros(stats.filtrar(repo.all(), loteria="loteria nacional"), 10)


@router.get("/fechas-numero", include_in_schema=False)
def fechas_numero_legacy(repo: Repo, numero: Annotated[int, Query(ge=0, le=99)]) -> dict:
    info = stats.apariciones_numero(repo.all(), numero, limite=10_000)
    fechas = sorted(({"fecha": s["fecha"], "loteria": s["loteria"]} for s in info["sorteos"]), key=lambda x: x["fecha"])
    return {"numero": numero, "fechas": fechas}
