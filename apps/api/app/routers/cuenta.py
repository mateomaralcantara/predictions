from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import auth
from ..config import get_settings
from ..cuentas import historial_pagos, perfil
from ..db import Usuario
from ..deps import DB, UsuarioRequerido
from ..ratelimit import limit

router = APIRouter(prefix="/api/auth", tags=["cuenta"])


class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class CambioPassword(BaseModel):
    actual: str = Field(min_length=1, max_length=128)
    nueva: str = Field(min_length=8, max_length=128)


def _sesion(db, usuario: Usuario) -> dict:
    return {"token": auth.crear_token(get_settings(), usuario.id), "usuario": perfil(db, usuario)}


@router.post("/registro", status_code=201, dependencies=[Depends(limit("registro", 5))])
def registro(body: Registro, db: DB) -> dict:
    email = auth.normalizar_email(body.email)
    if not auth.email_valido(email):
        raise HTTPException(422, "Correo electrónico inválido.")
    if body.password.lower() in {"12345678", "password", "contraseña", "123456789", "qwertyui"}:
        raise HTTPException(422, "Elige una contraseña menos común.")
    usuario = Usuario(email=email, nombre=body.nombre.strip(), password_hash=auth.hash_password(body.password))
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una cuenta con ese correo.") from None
    return _sesion(db, usuario)


@router.post("/login", dependencies=[Depends(limit("login", 10))])
def login(body: Login, db: DB) -> dict:
    email = auth.normalizar_email(body.email)
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    ok = auth.verify_password(body.password, usuario.password_hash if usuario else auth.DUMMY_HASH)
    if not usuario or not ok:
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    return _sesion(db, usuario)


@router.get("/yo")
def yo(usuario: UsuarioRequerido, db: DB) -> dict:
    return perfil(db, usuario)


@router.get("/pagos")
def mis_pagos(usuario: UsuarioRequerido, db: DB) -> list[dict]:
    return historial_pagos(db, usuario)


@router.post("/password", dependencies=[Depends(limit("password", 5))])
def cambiar_password(body: CambioPassword, usuario: UsuarioRequerido, db: DB) -> dict:
    if not auth.verify_password(body.actual, usuario.password_hash):
        raise HTTPException(401, "La contraseña actual no es correcta.")
    usuario.password_hash = auth.hash_password(body.nueva)
    db.commit()
    return {"ok": True}
