"""Límite de peticiones en memoria (ventana deslizante) por clave.

Suficiente para una instancia. Con varias réplicas, poner el límite en el
proxy (nginx, Cloudflare) o usar Redis.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: float) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(window - (now - q[0])))
                raise HTTPException(
                    429,
                    "Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)
            if len(self._hits) > 50_000:  # evita crecimiento sin límite
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > window]:
                    del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocido"


def limit(name: str, per_minute: int):
    """Dependencia FastAPI: ``Depends(limit("chat", 20))``."""

    def _dep(request: Request) -> None:
        limiter.check(f"{name}:{client_ip(request)}", per_minute, 60.0)

    return _dep
