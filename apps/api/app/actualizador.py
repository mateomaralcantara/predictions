"""Actualización automática de todos los sorteos mientras la API está encendida.

Cada ``ACTUALIZAR_CADA_MIN`` minutos (30 por defecto):

1. Tradicionales (14 loterías): revisa los últimos 3 días en labanca.do y
   descarga solo las loterías que falten (completa días a medias).
2. Loto, SuperKino y Loto Pool: descarga los sorteos posteriores al último.
3. Si hay PostgreSQL/Supabase, importa los tradicionales nuevos.
4. Refresca las cachés para que la web muestre los datos nuevos al instante.

Trabaja sobre copias en ``data/vivo/`` (ignoradas por Git) que se combinan con
los CSV versionados al arrancar; así nunca bloquea un ``git pull``.
Cada sincronizador corre como proceso aparte: si uno falla, los demás siguen.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import subprocess
import sys
import threading
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .config import REPO_ROOT, Settings

log = logging.getLogger(__name__)

# juego -> columnas que identifican un sorteo (para combinar CSV)
CLAVES = {"resultados": 2, "loto": 1, "superkino": 1, "lotopool": 1}

_lock = threading.Lock()
estado: dict = {"en_curso": False, "ultima": None, "proxima": None, "resultados": {}}


# --------------------------------------------------------------------------- #
# Copias vivas
# --------------------------------------------------------------------------- #


def _leer(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        filas = [r for r in csv.reader(fh) if r]
    return (filas[0], filas[1:]) if filas else ([], [])


def _clave(fila: list[str], cabecera: list[str], n: int) -> tuple:
    if cabecera and cabecera[0].lower() == "id":  # CSV antiguo con columna id
        fila = fila[1:]
    return tuple(c.strip() for c in fila[:n])


def _normalizar(fila: list[str], cabecera: list[str]) -> list[str]:
    return fila[1:] if cabecera and cabecera[0].lower() == "id" else fila


def combinar(base: Path, viva: Path, n_clave: int) -> int:
    """Une el CSV versionado con la copia viva (la viva gana en conflicto).

    Devuelve cuántas filas aportó el CSV versionado.
    """
    cab_b, filas_b = _leer(base)
    cab_v, filas_v = _leer(viva)
    cabecera = _normalizar(cab_v, cab_v) if cab_v else _normalizar(cab_b, cab_b)
    if not cabecera:
        return 0
    unidas: dict[tuple, list[str]] = {}
    for f in filas_b:
        unidas[_clave(f, cab_b, n_clave)] = _normalizar(f, cab_b)
    nuevas = len(set(unidas) - {_clave(f, cab_v, n_clave) for f in filas_v})
    for f in filas_v:
        unidas[_clave(f, cab_v, n_clave)] = _normalizar(f, cab_v)
    if viva.exists() and nuevas == 0:
        return 0
    viva.parent.mkdir(parents=True, exist_ok=True)
    tmp = viva.with_suffix(viva.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(unidas[k] for k in sorted(unidas))
    tmp.replace(viva)
    return nuevas


def preparar(settings: Settings) -> None:
    """Crea/actualiza data/vivo/ a partir de los CSV versionados."""
    for juego, base in settings.csv_base.items():
        viva = getattr(settings, f"{juego}_csv")
        if viva == base:
            continue
        aporte = combinar(base, viva, CLAVES[juego])
        if aporte:
            log.info("Datos %s: %d sorteos añadidos desde el repositorio.", juego, aporte)


# --------------------------------------------------------------------------- #
# Ciclo de actualización
# --------------------------------------------------------------------------- #


def ultima_fecha(path: Path) -> date | None:
    """Fecha más reciente del CSV (primera columna con forma de fecha)."""
    ultima = None
    _, filas = _leer(path)
    for f in filas:
        for celda in f[:2]:  # algunos CSV antiguos llevan "id" primero
            try:
                d = date.fromisoformat(celda.strip())
            except ValueError:
                continue
            ultima = d if ultima is None or d > ultima else ultima
            break
    return ultima


def _desde(path: Path, hoy: date, margen: int = 3) -> str:
    """Revisa siempre los últimos ``margen`` días y, si el dato más reciente es
    más antiguo (la API estuvo apagada), empieza justo después de él."""
    inicio = hoy - timedelta(days=margen)
    ultima = ultima_fecha(path)
    if ultima is not None and ultima + timedelta(days=1) < inicio:
        inicio = ultima + timedelta(days=1)
    return inicio.isoformat()


def comandos(settings: Settings, hoy: date | None = None) -> dict[str, list[str]]:
    hoy = hoy or date.today()
    py = sys.executable
    return {
        "tradicionales": [
            py, str(REPO_ROOT / "apps" / "collector" / "tradicionales.py"),
            "--csv", str(settings.resultados_csv), "--completar",
            "--desde", _desde(settings.resultados_csv, hoy), "--hasta", hoy.isoformat(), "--pausa", "0",
        ],
        "loto": [py, str(REPO_ROOT / "packages" / "games" / "loto" / "sync.py"),
                 "--csv", str(settings.loto_csv), "--append-latest", "--delay", "0.2"],
        "superkino": [py, str(REPO_ROOT / "packages" / "games" / "superkino" / "sync.py"),
                      "--csv", str(settings.superkino_csv), "--append-latest", "--delay", "0.2"],
        "lotopool": [py, str(REPO_ROOT / "packages" / "games" / "lotopool" / "sync.py"),
                     "--csv", str(settings.lotopool_csv), "--desde", _desde(settings.lotopool_csv, hoy)],
    }  # fmt: skip


def _resumen(salida: str) -> str:
    lineas = [x.strip() for x in salida.splitlines() if x.strip()]
    return lineas[-1][:200] if lineas else ""


def ejecutar_ciclo(settings: Settings, runner=subprocess.run) -> dict:
    """Ejecuta una actualización completa. Seguro ante llamadas concurrentes."""
    if not _lock.acquire(blocking=False):
        return {"omitido": "ya hay una actualización en curso"}
    estado["en_curso"] = True
    resultados: dict[str, dict] = {}
    try:
        preparar(settings)
        for juego, cmd in comandos(settings).items():
            try:
                p = runner(
                    cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=900,
                    encoding="utf-8", errors="replace",
                )  # fmt: skip
                ok = p.returncode == 0
                resultados[juego] = {"ok": ok, "detalle": _resumen(p.stdout if ok else (p.stderr or p.stdout))}
            except Exception as exc:  # noqa: BLE001 - un juego no debe frenar a los demás
                resultados[juego] = {"ok": False, "detalle": f"{exc.__class__.__name__}: {exc}"[:200]}
            nivel = logging.INFO if resultados[juego]["ok"] else logging.WARNING
            log.log(nivel, "Actualización %s: %s", juego, resultados[juego]["detalle"])

        if settings.database_url and resultados.get("tradicionales", {}).get("ok"):
            try:
                from .cli import importar_csv

                nuevos, _ = importar_csv(settings.resultados_csv, settings.database_url)
                resultados["base_de_datos"] = {"ok": True, "detalle": f"{nuevos} sorteos nuevos importados"}
            except Exception as exc:  # noqa: BLE001
                resultados["base_de_datos"] = {"ok": False, "detalle": f"{exc.__class__.__name__}"}

        _refrescar_caches()
        estado["ultima"] = datetime.now(UTC).isoformat(timespec="seconds")
        estado["resultados"] = resultados
        return resultados
    finally:
        estado["en_curso"] = False
        _lock.release()


def _refrescar_caches() -> None:
    from . import predictions, tradicional
    from .deps import get_repository

    get_repository().invalidate()
    predictions.clear_cache()
    tradicional.clear_cache()


async def bucle(settings: Settings, espera_inicial: float = 15) -> None:
    """Tarea de fondo: primera pasada a los pocos segundos y luego periódica."""
    intervalo = settings.actualizar_cada_min * 60
    await asyncio.sleep(espera_inicial)
    while True:
        try:
            await asyncio.to_thread(ejecutar_ciclo, settings)
        except Exception:  # noqa: BLE001
            log.exception("Fallo inesperado en la actualización automática")
        estado["proxima"] = (datetime.now(UTC) + timedelta(seconds=intervalo)).isoformat(timespec="seconds")
        await asyncio.sleep(intervalo)
