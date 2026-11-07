"""Operaciones administrativas protegidas por ``ADMIN_TOKEN``.

Si ``ADMIN_TOKEN`` no está definido, estos endpoints no existen (404).
"""

from __future__ import annotations

import asyncio
import hmac
import sys
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from ..config import API_DIR, Settings
from ..deps import get_repository, settings_dep

router = APIRouter(prefix="/api/admin", tags=["admin"], include_in_schema=False)

SCRAPER = API_DIR / "loterias" / "scraper_tradicional_hasta_ayer.py"
_scraping_lock = asyncio.Lock()


def require_admin(
    settings: Annotated[Settings, Depends(settings_dep)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.admin_token:
        raise HTTPException(404, "Not Found")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Token de administrador inválido.")


@router.post("/scraping", dependencies=[Depends(require_admin)])
async def ejecutar_scraping() -> dict:
    if _scraping_lock.locked():
        raise HTTPException(409, "Ya hay un scraping en curso.")
    async with _scraping_lock:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(SCRAPER),
            cwd=str(SCRAPER.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=900)
        except TimeoutError:
            proc.kill()
            raise HTTPException(504, "El scraping tardó demasiado.") from None
    get_repository().invalidate()
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "codigo_salida": proc.returncode,
        "salida": stdout.decode(errors="replace")[-4000:],
        "errores": stderr.decode(errors="replace")[-4000:] if not ok else "",
    }


@router.post("/recargar", dependencies=[Depends(require_admin)])
def recargar_datos() -> dict:
    repo = get_repository()
    repo.invalidate()
    return {"ok": True, "sorteos": len(repo.all()), "fuente": repo.source}
