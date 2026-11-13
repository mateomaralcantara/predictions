"""Recolector de loterías tradicionales.

Mantiene ``data/tradicionales/resultados_tradicionales.csv`` al día y rellena
huecos (fechas sin ningún sorteo). Diseñado para correr a diario en CI.

    python apps/collector/tradicionales.py                 # desde el último dato hasta ayer
    python apps/collector/tradicionales.py --rellenar-huecos --desde 2021-08-01
    python apps/collector/tradicionales.py --dry-run --desde 2025-06-25 --hasta 2025-06-29

Protecciones contra datos falsos:
1. Se descarta cada bloque cuya fecha no coincide con la pedida.
2. Se descarta el día completo si la mayoría de sus resultados es idéntica al
   último resultado guardado de cada lotería (página obsoleta).
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from packages.sources import labanca  # noqa: E402
from packages.sources import loteriasdominicanas as fuente  # noqa: E402

log = logging.getLogger("collector.tradicionales")
CSV_POR_DEFECTO = ROOT / "data" / "tradicionales" / "resultados_tradicionales.csv"
CAMPOS = ["fecha", "loteria", "primer", "segundo", "tercero"]
Clave = tuple[str, str]  # (fecha ISO, lotería)


def leer_csv(path: Path) -> dict[Clave, tuple[int, int, int]]:
    filas: dict[Clave, tuple[int, int, int]] = {}
    if not path.exists():
        return filas
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                f = date.fromisoformat(row["fecha"].strip()).isoformat()
                filas[(f, row["loteria"].strip())] = (int(row["primer"]), int(row["segundo"]), int(row["tercero"]))
            except (KeyError, ValueError, AttributeError):
                continue
    return filas


def escribir_csv(path: Path, filas: dict[Clave, tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CAMPOS)
        for (f, lot), nums in sorted(filas.items()):
            w.writerow([f, lot, *nums])
    tmp.replace(path)


def ultimos_por_loteria(filas: dict[Clave, tuple[int, int, int]], antes_de: date) -> dict[str, tuple[int, int, int]]:
    ult: dict[str, tuple[str, tuple[int, int, int]]] = {}
    tope = antes_de.isoformat()
    for (f, lot), nums in filas.items():
        if f < tope and (lot not in ult or f > ult[lot][0]):
            ult[lot] = (f, nums)
    return {lot: v[1] for lot, v in ult.items()}


def dia_obsoleto(dia: fuente.ResultadoDia, previos: dict[str, tuple[int, int, int]]) -> bool:
    comparables = [s for s in dia.sorteos if s.loteria in previos]
    if len(comparables) < 2:
        return False
    iguales = sum(1 for s in comparables if previos[s.loteria] == s.numeros)
    return iguales * 2 >= len(comparables)


def fechas_objetivo(
    filas: dict[Clave, tuple[int, int, int]], desde: date | None, hasta: date, rellenar: bool
) -> list[date]:
    """Fechas sin ningún sorteo guardado entre ``desde`` y ``hasta``.

    Sin ``desde``: día siguiente al último dato, o el primer dato si ``rellenar``.
    """
    con_datos = {date.fromisoformat(f) for f, _ in filas}
    if desde is None:
        if not con_datos:
            desde = date(2010, 8, 1)
        else:
            desde = min(con_datos) if rellenar else max(con_datos) + timedelta(days=1)
    total = (hasta - desde).days + 1
    return [d for d in (desde + timedelta(days=i) for i in range(max(0, total))) if d not in con_datos]


def ejecutar(args: argparse.Namespace, session: requests.Session | None = None) -> dict:
    filas = leer_csv(args.csv)
    hasta = args.hasta or (date.today() - timedelta(days=1))
    if args.completar:
        # Revisa TODAS las fechas del rango y pide solo las loterías que faltan
        # (p. ej. ya salieron las de la mañana y faltan las de la noche).
        inicio = args.desde or hasta
        objetivos = [inicio + timedelta(days=i) for i in range((hasta - inicio).days + 1)]
    else:
        objetivos = fechas_objetivo(filas, args.desde, hasta, args.rellenar_huecos)
    if args.fuente == "labanca":
        objetivos = [d for d in objetivos if d >= labanca.INICIO]
    objetivos = objetivos[: args.max_dias]
    session = session or requests.Session()
    stats = {"dias": len(objetivos), "nuevos": 0, "dias_sin_datos": 0, "dias_obsoletos": 0, "bloques_descartados": 0}

    for i, d in enumerate(objetivos):
        if args.fuente == "labanca":
            ya = {lot for (f, lot) in filas if f == d.isoformat()}
            if args.completar and ya >= set(labanca.LOTERIAS):
                continue
            dia = labanca.dia(d, session, timeout=args.timeout, omitir=ya if args.completar else set())
        else:
            html = fuente.descargar(d, session, timeout=args.timeout)
            if html is None:
                stats["dias_sin_datos"] += 1
                continue
            dia = fuente.parse(html, d)
        stats["bloques_descartados"] += dia.descartados_fecha
        if not dia.sorteos:
            stats["dias_sin_datos"] += 1
            continue
        if not args.completar and dia_obsoleto(dia, ultimos_por_loteria(filas, d)):
            stats["dias_obsoletos"] += 1
            log.warning("%s: la página repite resultados anteriores; se ignora.", d)
            continue
        for s in dia.sorteos:
            clave = (d.isoformat(), s.loteria)
            if clave not in filas:
                filas[clave] = s.numeros
                stats["nuevos"] += 1
        log.info("%s: %d sorteos", d, len(dia.sorteos))
        if args.pausa and i < len(objetivos) - 1:
            time.sleep(args.pausa)

    if stats["nuevos"] and not args.dry_run:
        escribir_csv(args.csv, filas)
    return stats


def _fecha(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Recolector de loterías tradicionales")
    ap.add_argument("--csv", type=Path, default=CSV_POR_DEFECTO)
    ap.add_argument("--desde", type=_fecha, default=None, help="YYYY-MM-DD (por defecto: día siguiente al último dato)")
    ap.add_argument("--hasta", type=_fecha, default=None, help="YYYY-MM-DD (por defecto: ayer)")
    ap.add_argument("--rellenar-huecos", action="store_true", help="Incluye fechas sin datos dentro del rango")
    ap.add_argument("--max-dias", type=int, default=400, help="Tope de días por ejecución")
    ap.add_argument("--pausa", type=float, default=0.5, help="Segundos entre peticiones")
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument("--dry-run", action="store_true", help="No escribe el CSV")
    ap.add_argument(
        "--completar",
        action="store_true",
        help="Revisa cada fecha del rango y descarga solo las loterías que falten (días a medias)",
    )
    ap.add_argument(
        "--fuente",
        choices=["labanca", "loteriasdominicanas"],
        default="labanca",
        help="labanca.do (desde 2026-02-12) o loteriasdominicanas.com (histórico completo; bloquea algunas redes)",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = ejecutar(parser().parse_args(argv))
    print(
        f"Días revisados: {stats['dias']} · nuevos sorteos: {stats['nuevos']} · sin datos: {stats['dias_sin_datos']} · "
        f"páginas obsoletas ignoradas: {stats['dias_obsoletos']} · bloques con otra fecha: {stats['bloques_descartados']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
