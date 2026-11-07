from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import predictions
from ..config import Settings
from ..deps import settings_dep

router = APIRouter(prefix="/api/predicciones", tags=["predicciones"])


@router.get("")
def juegos() -> list[dict]:
    return [{"id": k, **v} for k, v in predictions.JUEGOS.items()]


@router.get("/{juego}")
def predecir(
    juego: Literal["loto", "superkino"],
    settings: Annotated[Settings, Depends(settings_dep)],
    jugadas: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict:
    try:
        if juego == "loto":
            return predictions.predecir_loto(settings.loto_csv, jugadas)
        return predictions.predecir_superkino(settings.superkino_csv, jugadas)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
