from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .. import chat
from ..config import Settings, get_settings
from ..cuentas import limites_de
from ..deps import Nivel, UsuarioOpcional, get_repository, settings_dep
from ..ratelimit import client_ip, limit, limiter
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
    request: Request,
    usuario: UsuarioOpcional,
    nivel: Nivel,
    repo: Annotated[ResultsRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(settings_dep)],
) -> RespuestaChat:
    clave = f"chat:u{usuario.id}" if usuario else f"chat:{client_ip(request)}"
    limiter.check(clave, limites_de(nivel).chat_por_minuto, 60.0)
    rows = await run_in_threadpool(repo.all)
    r = await chat.responder(body.pregunta, rows, settings)
    return RespuestaChat(pregunta=body.pregunta, intencion=r.intencion, respuesta=r.texto)


@router.get("/pregunta", include_in_schema=False, dependencies=[Depends(limit("chat-legacy", 10))])
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
            try:
                ip = websocket.client.host if websocket.client else "ws"
                limiter.check(f"chat:{ip}", limites_de(0).chat_por_minuto, 60.0)
            except HTTPException as exc:
                await websocket.send_text(str(exc.detail))
                continue
            rows = await run_in_threadpool(repo.all)
            r = await chat.responder(texto, rows, settings)
            await websocket.send_text(r.texto)
    except WebSocketDisconnect:
        log.debug("Cliente de chat desconectado")
