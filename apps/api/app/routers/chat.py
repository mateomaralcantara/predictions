from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .. import chat
from ..config import Settings, get_settings
from ..deps import get_repository, settings_dep
from ..repository import ResultsRepository

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=1, max_length=chat.MAX_PREGUNTA)


class RespuestaChat(BaseModel):
    pregunta: str
    intencion: str
    respuesta: str


@router.post("/api/chat", response_model=RespuestaChat)
async def preguntar(
    body: Pregunta,
    repo: Annotated[ResultsRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(settings_dep)],
) -> RespuestaChat:
    rows = await run_in_threadpool(repo.all)
    r = await chat.responder(body.pregunta, rows, settings)
    return RespuestaChat(pregunta=body.pregunta, intencion=r.intencion, respuesta=r.texto)


@router.get("/pregunta", include_in_schema=False)
async def preguntar_legacy(
    texto: Annotated[str, Query(min_length=1, max_length=chat.MAX_PREGUNTA)],
    repo: Annotated[ResultsRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(settings_dep)],
) -> dict:
    rows = await run_in_threadpool(repo.all)
    r = await chat.responder(texto, rows, settings)
    return {"pregunta": texto, "respuesta": r.texto}


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    repo = get_repository()
    settings = get_settings()
    try:
        while True:
            texto = await websocket.receive_text()
            if len(texto) > chat.MAX_PREGUNTA:
                await websocket.send_text(f"La pregunta es muy larga (máximo {chat.MAX_PREGUNTA} caracteres).")
                continue
            rows = await run_in_threadpool(repo.all)
            r = await chat.responder(texto, rows, settings)
            await websocket.send_text(r.texto)
    except WebSocketDisconnect:
        log.debug("Cliente de chat desconectado")
