"""Autenticación: contraseñas con scrypt y tokens JWT (HS256)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from .config import Settings

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
TOKEN_TTL = timedelta(days=7)
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def email_valido(email: str) -> bool:
    return bool(EMAIL_RE.match(email)) and len(email) <= 254


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(txt: str) -> bytes:
    return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, _unb64(digest))
    except (ValueError, TypeError):
        return False


# Hash fijo para igualar el tiempo de respuesta cuando el email no existe.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def crear_token(settings: Settings, usuario_id: int) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(usuario_id), "iat": now, "exp": now + TOKEN_TTL, "typ": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def leer_token(settings: Settings, token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None
