from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import auth
from .config import Settings, get_settings
from .cuentas import nivel_de
from .db import Usuario, session_factory
from .payments import PayPalClient
from .repository import ResultsRepository

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_repository() -> ResultsRepository:
    s = get_settings()
    return ResultsRepository(csv_path=s.resultados_csv, database_url=s.database_url)


def get_paypal() -> PayPalClient:
    return PayPalClient(get_settings())


def settings_dep() -> Settings:
    return get_settings()


def get_db() -> Iterator[Session]:
    session = session_factory(get_settings().app_database_url)()
    try:
        yield session
    finally:
        session.close()


DB = Annotated[Session, Depends(get_db)]


def usuario_opcional(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> Usuario | None:
    if cred is None:
        return None
    uid = auth.leer_token(get_settings(), cred.credentials)
    usuario = db.get(Usuario, uid) if uid is not None else None
    if usuario is None:
        raise HTTPException(401, "Sesión inválida o expirada.", headers={"WWW-Authenticate": "Bearer"})
    return usuario


def usuario_requerido(usuario: Annotated[Usuario | None, Depends(usuario_opcional)]) -> Usuario:
    if usuario is None:
        raise HTTPException(401, "Inicia sesión para continuar.", headers={"WWW-Authenticate": "Bearer"})
    return usuario


def nivel_actual(db: DB, usuario: Annotated[Usuario | None, Depends(usuario_opcional)]) -> int:
    return nivel_de(db, usuario)


UsuarioOpcional = Annotated[Usuario | None, Depends(usuario_opcional)]
UsuarioRequerido = Annotated[Usuario, Depends(usuario_requerido)]
Nivel = Annotated[int, Depends(nivel_actual)]
