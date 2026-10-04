# loto_leidsa_update.py
# Actualiza loto_leidsa.csv hasta la fecha actual (America/Santo_Domingo)
# Requisitos: pip install "httpx[http2]" beautifulsoup4 typer
#
# Uso típico:
#   python loto_leidsa_update.py
#   python loto_leidsa_update.py --since 2024-01-01 --until 2024-12-31
#   python loto_leidsa_update.py update --dry-run
#
# Nota: En algunas versiones de Typer/Click, el tipo datetime.date en parámetros CLI provoca:
#   RuntimeError: Type not yet supported: <class 'datetime.date'>
# Por eso "since" y "until" se reciben como str y se parsean manualmente.

from __future__ import annotations

import asyncio
import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import httpx
import typer
from bs4 import BeautifulSoup

app = typer.Typer(add_completion=False, no_args_is_help=False)

# ----------------------- Config -----------------------
CSV_OUT = "loto_leidsa.csv"
TZ_NAME = "America/Santo_Domingo"

# RD es UTC-4 y NO usa DST: para "hoy" basta ajustar desde UTC.
RD_UTC_OFFSET_HOURS = -4

# Varias rutas candidatas: la web a veces cambia endpoints o formato de fecha.
CANDIDATE_URLS: Tuple[str, ...] = (
    "https://loteriasdominicanas.com/leidsa/loto-mas?date={:%Y-%m-%d}",
    "https://loteriasdominicanas.com/leidsa/loto-mas?date={:%d-%m-%Y}",
    "https://loteriasdominicanas.com/pagina/ultimos-resultados?date={:%Y-%m-%d}",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Fechas típicas en las páginas (común en RD: dd-mm-YYYY, pero también aparece YYYY-mm-dd).
DATE_RE_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")  # dd-mm-YYYY o dd/mm/YYYY
DATE_RE_YMD = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")  # YYYY-mm-dd o YYYY/mm/dd


# ----------------------- Utils -----------------------
def today_santo_domingo() -> date:
    """Fecha 'hoy' en RD sin depender de zoneinfo (Windows a veces requiere tzdata)."""
    return (datetime.utcnow() + timedelta(hours=RD_UTC_OFFSET_HOURS)).date()


def normalize_text(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def is_draw_day(d: date) -> bool:
    # Miércoles=2, Sábado=5
    return d.weekday() in (2, 5)


def draw_days_between(start: date, end: date) -> Iterable[date]:
    """Itera únicamente los días de sorteo (Mié/Sáb) dentro del rango [start, end]."""
    if start > end:
        return
    d = start
    while d <= end and not is_draw_day(d):
        d += timedelta(days=1)
    while d <= end:
        yield d
        # Miércoles -> +3 para Sábado, Sábado -> +4 para Miércoles
        d += timedelta(days=3 if d.weekday() == 2 else 4)


def parse_date_cli(value: Optional[str]) -> Optional[date]:
    """Parsea fecha desde CLI. Acepta: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD."""
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise typer.BadParameter(
        f"Fecha inválida: '{value}'. Formatos soportados: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD."
    )


def ensure_csv(path: Path) -> Tuple[set[str], Optional[str]]:
    """
    Asegura encabezado y devuelve:
      - set de fechas ya presentes (ISO YYYY-MM-DD)
      - última fecha ISO encontrada (para default_since)
    """
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(["fecha", "n1", "n2", "n3", "n4", "n5", "n6", "mas", "super_mas"])
        return set(), None

    fechas: set[str] = set()
    last_iso: Optional[str] = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        next(r, None)  # header
        for row in r:
            if not row:
                continue
            raw = (row[0] or "").strip()
            if not raw:
                continue
            # Acepta ISO o DD-MM-YYYY antiguos; normaliza a ISO.
            parsed: Optional[date] = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    parsed = datetime.strptime(raw, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed:
                iso = parsed.isoformat()
                fechas.add(iso)
                if last_iso is None or iso > last_iso:
                    last_iso = iso
    return fechas, last_iso


def ints_from(node) -> List[int]:
    nums: List[int] = []
    # Selectores comunes de números en estas páginas (si cambian, el fallback regex salva).
    for el in node.select("span.score, span.number, li span.number"):
        t = el.get_text(strip=True)
        if t.isdigit():
            nums.append(int(t))
    if not nums:
        nums.extend(int(x) for x in re.findall(r"\b\d{1,2}\b", node.get_text(" ", strip=True)))
    return nums


def looks_like_loto_title(text: str) -> bool:
    t = normalize_text(text)
    if "pool" in t or "kino" in t:
        return False
    return ("loto" in t and "mas" in t) or ("super loto" in t) or ("super loto mas" in t)


def extract_ordered_8(stream: Sequence[int]) -> Optional[List[int]]:
    """Devuelve [6 base 1..40, mas 1..12, super 1..15] si cumple rangos y sin repetir."""
    base: List[int] = []
    loto_mas: Optional[int] = None
    super_mas: Optional[int] = None
    seen = set()

    for v in stream:
        # Base: 6 números del 1 al 40, sin repetir.
        if len(base) < 6 and 1 <= v <= 40 and v not in seen:
            base.append(v)
            seen.add(v)
            continue

        # Extras: 1..12 y 1..15 (en ese orden).
        if len(base) == 6 and loto_mas is None and 1 <= v <= 12:
            loto_mas = v
            continue
        if len(base) == 6 and loto_mas is not None and super_mas is None and 1 <= v <= 15:
            super_mas = v
            break

    if len(base) == 6 and loto_mas is not None and super_mas is not None:
        return base + [loto_mas, super_mas]
    return None


def find_first_date(text: str) -> Optional[date]:
    """Encuentra la primera fecha en texto (soporta DMY y YMD)."""
    t = text or ""
    m = DATE_RE_DMY.search(t)
    if m:
        d1, d2, y = m.groups()
        try:
            return datetime.strptime(f"{int(d1):02d}-{int(d2):02d}-{y}", "%d-%m-%Y").date()
        except ValueError:
            pass
    m = DATE_RE_YMD.search(t)
    if m:
        y, mo, da = m.groups()
        try:
            return datetime.strptime(f"{y}-{int(mo):02d}-{int(da):02d}", "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def extract_page_date(soup: BeautifulSoup) -> Optional[date]:
    # 1) Cerca de títulos 'Loto' (más preciso)
    for h in soup.find_all(["h1", "h2", "h3"]):
        if looks_like_loto_title(h.get_text(" ", strip=True)):
            ctx = h.get_text(" ", strip=True)
            parent = h.find_parent()
            if parent:
                ctx = ctx + " " + parent.get_text(" ", strip=True)
            d = find_first_date(ctx)
            if d:
                return d

    # 2) Global (fallback)
    return find_first_date(soup.get_text(" ", strip=True))


def extract_loto_mas(soup: BeautifulSoup) -> Optional[List[int]]:
    # Bloques preferidos
    for b in soup.select(".game-block"):
        title_el = b.find(["h1", "h2", "h3"])
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if title and looks_like_loto_title(title):
            nums = ints_from(b)
            res = extract_ordered_8(nums)
            if res:
                return res

    # Fallback: alrededor de encabezados
    for h in soup.find_all(["h1", "h2", "h3"]):
        if looks_like_loto_title(h.get_text(" ", strip=True)):
            seg: List[int] = []
            for el in h.next_elements:
                if getattr(el, "name", "") in {"h1", "h2", "h3"}:
                    break
                if isinstance(el, str):
                    seg.extend(int(x) for x in re.findall(r"\b\d{1,2}\b", el))
                else:
                    seg.extend(ints_from(el))
            res = extract_ordered_8(seg)
            if res:
                return res

    # Fallback global
    all_nums = ints_from(soup)
    return extract_ordered_8(all_nums)


@dataclass(slots=True)
class FetchResult:
    fecha: date
    nums: Optional[List[int]]
    source: Optional[str]
    ok: bool
    error: Optional[str] = None


# ----------------------- Networking -----------------------
async def fetch_html(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
    backoff: float = 0.8,
    timeout_s: float = 15.0,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Devuelve (html, error). No lanza excepción.
    - Reintenta con backoff lineal.
    - Si recibe 429, respeta Retry-After cuando aplica.
    """
    last_err: Optional[str] = None

    for i in range(attempts):
        try:
            r = await client.get(url, timeout=timeout_s)
            if r.status_code == 429:
                ra = (r.headers.get("Retry-After") or "").strip()
                delay = None
                if ra.isdigit():
                    delay = float(ra)
                if delay is None:
                    delay = backoff * (i + 1)
                await asyncio.sleep(delay)
                last_err = f"429 Too Many Requests (retry-after={ra or 'n/a'})"
                continue

            r.raise_for_status()
            return r.text, None

        except httpx.HTTPStatusError as e:
            last_err = f"HTTP {e.response.status_code}"
        except httpx.RequestError as e:
            last_err = f"request error: {type(e).__name__}"

        if i < attempts - 1:
            await asyncio.sleep(backoff * (i + 1))

    return None, last_err or "unknown error"


async def fetch_one_date(
    client: httpx.AsyncClient,
    d: date,
    *,
    attempts: int,
    backoff: float,
    timeout_s: float,
) -> FetchResult:
    for tpl in CANDIDATE_URLS:
        url = tpl.format(d)
        html, err = await fetch_html(client, url, attempts=attempts, backoff=backoff, timeout_s=timeout_s)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Confirmar fecha de la página: si no coincide, probablemente devolvió el "último sorteo".
        page_date = extract_page_date(soup)
        if page_date and page_date != d:
            continue

        nums = extract_loto_mas(soup)
        if nums:
            return FetchResult(fecha=d, nums=nums, source=url, ok=True)

    return FetchResult(
        fecha=d,
        nums=None,
        source=None,
        ok=False,
        error="sin resultado/indisponible",
    )


async def gather_dates(
    dates: List[date],
    *,
    concurrency: int = 5,
    attempts: int = 3,
    backoff: float = 0.8,
    timeout_s: float = 15.0,
) -> List[FetchResult]:
    sem = asyncio.Semaphore(concurrency)
    results: List[FetchResult] = []

    limits = httpx.Limits(
        max_connections=max(10, concurrency * 2),
        max_keepalive_connections=max(10, concurrency),
    )

    async with httpx.AsyncClient(
        headers=HEADERS,
        http2=True,
        follow_redirects=True,
        limits=limits,
    ) as client:

        async def run(one: date) -> FetchResult:
            async with sem:
                return await fetch_one_date(
                    client,
                    one,
                    attempts=attempts,
                    backoff=backoff,
                    timeout_s=timeout_s,
                )

        tasks = [asyncio.create_task(run(d)) for d in dates]
        for t in asyncio.as_completed(tasks):
            results.append(await t)

    return results


# ----------------------- CSV I/O -----------------------
def append_results(csv_path: Path, existing_isos: set[str], fetched: List[FetchResult]) -> Tuple[int, int]:
    new_rows = 0
    skipped = 0

    fetched.sort(key=lambda r: r.fecha)

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in fetched:
            iso = r.fecha.isoformat()
            if iso in existing_isos:
                skipped += 1
                continue
            if r.ok and r.nums:
                w.writerow([iso] + r.nums)
                existing_isos.add(iso)
                new_rows += 1

    return new_rows, skipped


# ----------------------- Core Logic -----------------------
def run_update(
    *,
    csv_out: Path,
    since: Optional[str],
    until: Optional[str],
    concurrency: int,
    dry_run: bool,
    show_misses: bool,
    attempts: int,
    backoff: float,
    timeout_s: float,
) -> None:
    existing, last_iso = ensure_csv(csv_out)

    # Determinar rango
    default_since = date(2010, 8, 1)
    if last_iso:
        try:
            default_since = datetime.strptime(last_iso, "%Y-%m-%d").date() + timedelta(days=1)
        except ValueError:
            pass

    start = parse_date_cli(since) or default_since
    end = parse_date_cli(until) or today_santo_domingo()

    if start > end:
        typer.echo("Nada que hacer: rango vacío.")
        raise typer.Exit(code=0)

    to_fetch = list(draw_days_between(start, end))
    if not to_fetch:
        typer.echo("No hay días de sorteo en el rango.")
        raise typer.Exit(code=0)

    typer.echo(f"Buscando {len(to_fetch)} fechas (Mié/Sáb) {start} → {end} ...")

    fetched = asyncio.run(
        gather_dates(
            to_fetch,
            concurrency=concurrency,
            attempts=attempts,
            backoff=backoff,
            timeout_s=timeout_s,
        )
    )

    found_ok = [r for r in fetched if r.ok and r.nums]
    misses = [r for r in fetched if not (r.ok and r.nums)]

    typer.echo(f"Encontrados: {len(found_ok)} | Sin resultado: {len(misses)}")

    if show_misses and misses:
        misses.sort(key=lambda r: r.fecha)
        for r in misses:
            typer.echo(f"  - {r.fecha.isoformat()}: {r.error or 'sin detalle'}")

    if dry_run:
        for r in sorted(found_ok, key=lambda x: x.fecha):
            typer.echo(f"{r.fecha.isoformat()} -> {r.nums}  [{r.source}]")
        typer.echo("DRY-RUN: no se escribió nada.")
        raise typer.Exit(code=0)

    new_rows, skipped = append_results(csv_out, existing, fetched)
    typer.echo(f"Escrito: {new_rows} nuevos | Saltados (ya estaban): {skipped}")
    typer.echo(f"Archivo: {csv_out.resolve()}")


# ----------------------- CLI -----------------------
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    csv_out: Path = typer.Option(Path(CSV_OUT), "--csv", help="Ruta del CSV de salida."),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Desde. Formatos: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD. Si no, usa (última+1) o 2010-08-01.",
    ),
    until: Optional[str] = typer.Option(
        None,
        "--until",
        help="Hasta. Formatos: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD. Por defecto, hoy (RD).",
    ),
    concurrency: int = typer.Option(5, min=1, max=16, help="Máximo de requests en paralelo."),
    attempts: int = typer.Option(3, min=1, max=10, help="Reintentos por URL."),
    backoff: float = typer.Option(0.8, min=0.1, max=10.0, help="Backoff (segundos) entre reintentos."),
    timeout_s: float = typer.Option(15.0, min=3.0, max=60.0, help="Timeout por request (segundos)."),
    dry_run: bool = typer.Option(False, help="No escribe CSV; solo muestra qué se obtendría."),
    show_misses: bool = typer.Option(False, help="Muestra el detalle de fechas que no se pudieron obtener."),
):
    # Si no se invoca un subcomando, ejecuta update por defecto.
    if ctx.invoked_subcommand is None:
        run_update(
            csv_out=csv_out,
            since=since,
            until=until,
            concurrency=concurrency,
            dry_run=dry_run,
            show_misses=show_misses,
            attempts=attempts,
            backoff=backoff,
            timeout_s=timeout_s,
        )


@app.command("update")
def cmd_update(
    csv_out: Path = typer.Option(Path(CSV_OUT), "--csv", help="Ruta del CSV de salida."),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Desde. Formatos: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD. Si no, usa (última+1) o 2010-08-01.",
    ),
    until: Optional[str] = typer.Option(
        None,
        "--until",
        help="Hasta. Formatos: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD. Por defecto, hoy (RD).",
    ),
    concurrency: int = typer.Option(5, min=1, max=16, help="Máximo de requests en paralelo."),
    attempts: int = typer.Option(3, min=1, max=10, help="Reintentos por URL."),
    backoff: float = typer.Option(0.8, min=0.1, max=10.0, help="Backoff (segundos) entre reintentos."),
    timeout_s: float = typer.Option(15.0, min=3.0, max=60.0, help="Timeout por request (segundos)."),
    dry_run: bool = typer.Option(False, help="No escribe CSV; solo muestra qué se obtendría."),
    show_misses: bool = typer.Option(False, help="Muestra el detalle de fechas que no se pudieron obtener."),
):
    run_update(
        csv_out=csv_out,
        since=since,
        until=until,
        concurrency=concurrency,
        dry_run=dry_run,
        show_misses=show_misses,
        attempts=attempts,
        backoff=backoff,
        timeout_s=timeout_s,
    )


if __name__ == "__main__":
    app()
