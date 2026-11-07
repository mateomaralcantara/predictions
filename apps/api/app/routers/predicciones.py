from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import predictions
from ..config import Settings
from ..cuentas import limites_de
from ..deps import Nivel, settings_dep

router = APIRouter(prefix="/api/predicciones", tags=["predicciones"])


@router.get("")
def juegos() -> list[dict]:
    return [{"id": k, **v} for k, v in predictions.JUEGOS.items()]


@router.get("/{juego}")
def predecir(
    juego: Literal["loto", "superkino"],
    settings: Annotated[Settings, Depends(settings_dep)],
    nivel: Nivel,
    jugadas: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict:
    maximo = limites_de(nivel).jugadas
    permitidas = min(jugadas, maximo)
    try:
        if juego == "loto":
            data = predictions.predecir_loto(settings.loto_csv, permitidas)
        else:
            data = predictions.predecir_superkino(settings.superkino_csv, permitidas)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {**data, "solicitadas": jugadas, "max_jugadas": maximo, "limitado": jugadas > maximo, "nivel": nivel}
