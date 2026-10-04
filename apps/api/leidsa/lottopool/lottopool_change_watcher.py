#!/usr/bin/env python3
# lottopool_watcher.py
# Watcher moderno para Loto Pool:
# - Vigila la página cada 60 segundos.
# - Detecta si aparece el sorteo de hoy.
# - Si aparecen números nuevos, actualiza el CSV inmediatamente.
# - Si una fecha ya existe pero cambió, la corrige.
# - No duplica fechas.
# - Reescribe CSV ordenado y deduplicado.
# - Crea logs, estado JSON y lock anti doble ejecución.

import argparse
import csv
import json
import logging
import re
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


# ============================================================
# CONFIG
# ============================================================

RD_TZ_NAME = "America/Santo_Domingo"

DEFAULT_CSV = "lotto_pool_historial.csv"
DEFAULT_LOG = "lottopool_watcher.log"
DEFAULT_STATE = "lottopool_watcher_state.json"
DEFAULT_LOCK = "lottopool_watcher.lock"

POOL_MIN = 1
POOL_MAX = 31
POOL_COUNT = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

URL_TRIALS = [
    ("A", "https://loteriasdominicanas.com/leidsa/loto-pool?date={iso}"),
    ("B", "https://loteriasdominicanas.com/leidsa/loto-pool?date={dmY}"),
    ("C", "https://loteriasdominicanas.com/pagina/ultimos-resultados?date={iso}"),
]


# ============================================================
# MODELOS
# ============================================================

@dataclass(frozen=True)
class ScrapeResult:
    iso: str
    nums: List[int]
    route_tag: str
    extractor: str


@dataclass
class WatchState:
    last_run_at: str
    csv_path: str
    watched_dates: List[str]
    changed: bool
    added: int
    updated: int
    unchanged: int
    misses: int
    errors: int
    next_run_seconds: int


# ============================================================
# LOGGING
# ============================================================

def setup_logger(log_path: Path, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("lottopool_watcher")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# ============================================================
# TIEMPO RD
# ============================================================

def rd_now() -> datetime:
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(RD_TZ_NAME))
        except Exception:
            pass
    return datetime.now()


def parse_date_any(raw: str) -> Optional[date]:
    raw = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except Exception:
            continue
    return None


def daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def build_watch_dates(watch_days: int, include_yesterday: bool = True) -> List[date]:
    today = rd_now().date()
    if watch_days <= 1:
        return [today]

    start = today - timedelta(days=watch_days - 1)
    days = list(daterange(start, today))

    if not include_yesterday:
        return [today]

    return days


# ============================================================
# LOCK
# ============================================================

@contextmanager
def single_instance_lock(lock_path: Path, stale_after_seconds: int = 60 * 60 * 6):
    now_ts = time.time()

    if lock_path.exists():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            created_ts = float(data.get("created_ts", 0))
        except Exception:
            created_ts = 0

        if created_ts and (now_ts - created_ts) < stale_after_seconds:
            raise SystemExit(
                f"❌ Ya hay una instancia activa: {lock_path}\n"
                f"Si estás seguro de que no corre nada, borra ese archivo."
            )

        try:
            lock_path.unlink()
        except Exception:
            pass

    payload = {
        "pid": getattr(__import__("os"), "getpid")(),
        "created_at": rd_now().isoformat(),
        "created_ts": now_ts,
    }

    lock_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except Exception:
            pass


# ============================================================
# CSV
# ============================================================

def ensure_header(csv_path: Path) -> None:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(["fecha", "num1", "num2", "num3", "num4", "num5"])


def valid_pool(nums: List[int]) -> bool:
    return (
        len(nums) == POOL_COUNT
        and len(set(nums)) == POOL_COUNT
        and all(POOL_MIN <= n <= POOL_MAX for n in nums)
    )


def read_rows(csv_path: Path) -> Dict[str, List[int]]:
    ensure_header(csv_path)

    rows: Dict[str, List[int]] = {}

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)

        first = next(reader, None)
        pending_first = None

        if first and parse_date_any(first[0]):
            pending_first = first

        def iter_rows():
            if pending_first:
                yield pending_first
            for row in reader:
                yield row

        for row in iter_rows():
            if not row:
                continue

            d = parse_date_any(row[0])
            if not d:
                continue

            nums: List[int] = []
            for x in row[1:6]:
                x = str(x).strip()
                if x.isdigit():
                    nums.append(int(x))

            if valid_pool(nums):
                rows[d.isoformat()] = nums

    return rows


def write_rows_atomic(csv_path: Path, rows_by_iso: Dict[str, List[int]]) -> None:
    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")

    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["fecha", "num1", "num2", "num3", "num4", "num5"])

        for iso in sorted(rows_by_iso.keys()):
            nums = rows_by_iso[iso]
            if valid_pool(nums):
                writer.writerow([iso] + nums)

    tmp.replace(csv_path)


# ============================================================
# SCRAPING
# ============================================================

def fetch(
    session: requests.Session,
    url: str,
    attempts: int = 3,
    timeout: int = 18,
    backoff: float = 0.8,
) -> Optional[str]:
    for i in range(attempts):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception:
            if i == attempts - 1:
                return None
            time.sleep(backoff * (i + 1))

    return None


def ints_in(node) -> List[int]:
    nums: List[int] = []

    selectors = (
        "span.score, "
        "span.number, "
        "li span.number, "
        "div.number, "
        "span.ball, "
        "li.ball, "
        ".score, "
        ".number"
    )

    for el in node.select(selectors):
        text = el.get_text(strip=True)
        if text.isdigit():
            nums.append(int(text))

    if not nums:
        text = node.get_text(" ", strip=True)
        nums.extend(int(x) for x in re.findall(r"\b\d{1,2}\b", text))

    return nums


def pick_first_five_unique_1_31(seq: List[int]) -> Optional[List[int]]:
    seen = set()
    out: List[int] = []

    for v in seq:
        if POOL_MIN <= v <= POOL_MAX and v not in seen:
            out.append(v)
            seen.add(v)

        if len(out) == POOL_COUNT:
            break

    return out if valid_pool(out) else None


def extract_date_near_pool(soup: BeautifulSoup) -> Optional[date]:
    hits = soup.find_all(string=re.compile(r"\bloto\s*pool\b", re.I))

    patterns = [
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        r"\b(\d{2})-(\d{2})-(\d{4})\b",
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
    ]

    for h in hits[:10]:
        parent = getattr(h, "parent", None)
        if not parent:
            continue

        container = parent
        for _ in range(5):
            if getattr(container, "name", None) in ("section", "article", "div", "main", "li"):
                break
            if container.parent is None:
                break
            container = container.parent

        text = container.get_text(" ", strip=True)

        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue

            try:
                groups = m.groups()
                if len(groups[0]) == 4:
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                return date(int(groups[2]), int(groups[1]), int(groups[0]))
            except Exception:
                continue

    return None


def target_date_guard(soup: BeautifulSoup, target: date) -> bool:
    """
    Si la página muestra una fecha cerca de Loto Pool y esa fecha NO coincide,
    rechazamos el resultado para evitar guardar números viejos bajo fecha nueva.
    Si no muestra fecha detectable, no bloqueamos.
    """
    detected = extract_date_near_pool(soup)
    if detected is None:
        return True
    return detected == target


def extract_from_gameblock(soup: BeautifulSoup) -> Optional[List[int]]:
    for block in soup.select(".game-block"):
        title = ""
        h = block.find(["h1", "h2", "h3", "h4"])
        if h:
            title = " ".join(h.get_text(" ", strip=True).split()).lower()

        if "loto" in title and "pool" in title:
            picked = pick_first_five_unique_1_31(ints_in(block))
            if picked:
                return picked

    return None


def extract_from_named_context(soup: BeautifulSoup) -> Optional[List[int]]:
    hits = soup.find_all(string=re.compile(r"\bloto\s*pool\b", re.I))

    for h in hits[:10]:
        parent = getattr(h, "parent", None)
        if not parent:
            continue

        container = parent
        for _ in range(5):
            if getattr(container, "name", None) in ("section", "article", "div", "main", "li"):
                break
            if container.parent is None:
                break
            container = container.parent

        picked = pick_first_five_unique_1_31(ints_in(container))
        if picked:
            return picked

    return None


def extract_global_guarded(soup: BeautifulSoup) -> Optional[List[int]]:
    page_text = soup.get_text(" ", strip=True)

    if not re.search(r"\bloto\s*pool\b", page_text, re.I):
        return None

    return pick_first_five_unique_1_31(ints_in(soup))


def scrape_pool_for_date(
    session: requests.Session,
    d: date,
    allow_global_fallback: bool = False,
) -> Optional[ScrapeResult]:
    fmt = {
        "iso": d.strftime("%Y-%m-%d"),
        "dmY": d.strftime("%d-%m-%Y"),
    }

    extractors = [
        ("gameblock", extract_from_gameblock),
        ("named_context", extract_from_named_context),
    ]

    if allow_global_fallback:
        extractors.append(("global_guarded", extract_global_guarded))

    for tag, template in URL_TRIALS:
        url = template.format(**fmt)
        html = fetch(session, url)

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        if not target_date_guard(soup, d):
            continue

        for extractor_name, extractor in extractors:
            nums = extractor(soup)

            if nums and valid_pool(nums):
                return ScrapeResult(
                    iso=d.isoformat(),
                    nums=nums,
                    route_tag=tag,
                    extractor=extractor_name,
                )

    return None


# ============================================================
# WATCH CYCLE
# ============================================================

def run_watch_cycle(args, logger: logging.Logger) -> WatchState:
    csv_path = Path(args.csv)
    state_path = Path(args.state)

    rows = read_rows(csv_path)
    watch_dates = build_watch_dates(args.watch_days)

    added = 0
    updated = 0
    unchanged = 0
    misses = 0
    errors = 0
    changed = False

    logger.info(f"👀 Vigilando fechas: {[d.isoformat() for d in watch_dates]}")

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for d in watch_dates:
            iso = d.isoformat()

            try:
                result = scrape_pool_for_date(
                    session=session,
                    d=d,
                    allow_global_fallback=args.allow_global_fallback,
                )
            except Exception as e:
                errors += 1
                logger.exception(f"❌ {iso} error: {e}")
                time.sleep(args.delay)
                continue

            if not result:
                misses += 1
                logger.info(f"— {iso}: todavía sin resultado detectable.")
                time.sleep(args.delay)
                continue

            old_nums = rows.get(result.iso)

            if old_nums is None:
                rows[result.iso] = result.nums
                added += 1
                changed = True
                logger.info(f"✅ NUEVO {result.iso}: {result.nums} ({result.route_tag}/{result.extractor})")

            elif old_nums != result.nums:
                rows[result.iso] = result.nums
                updated += 1
                changed = True
                logger.warning(f"♻️ CAMBIO {result.iso}: {old_nums} -> {result.nums}")

            else:
                unchanged += 1
                logger.info(f"✔️ SIN CAMBIO {result.iso}: {result.nums}")

            time.sleep(args.delay)

    if changed:
        write_rows_atomic(csv_path, rows)
        logger.info("🧹 CSV actualizado inmediatamente: ordenado y sin duplicados.")

    state = WatchState(
        last_run_at=rd_now().isoformat(),
        csv_path=str(csv_path.resolve()),
        watched_dates=[d.isoformat() for d in watch_dates],
        changed=changed,
        added=added,
        updated=updated,
        unchanged=unchanged,
        misses=misses,
        errors=errors,
        next_run_seconds=args.interval,
    )

    tmp_state = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp_state.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_state.replace(state_path)

    return state


# ============================================================
# CLI
# ============================================================

STOP = False


def handle_stop(signum, frame):
    global STOP
    STOP = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watcher Loto Pool — detecta cambios en la página y actualiza el CSV."
    )

    parser.add_argument("--csv", default=DEFAULT_CSV, help="CSV histórico.")
    parser.add_argument("--log", default=DEFAULT_LOG, help="Archivo de log.")
    parser.add_argument("--state", default=DEFAULT_STATE, help="Archivo JSON de estado.")
    parser.add_argument("--lock", default=DEFAULT_LOCK, help="Archivo lock.")

    parser.add_argument("--interval", type=int, default=60, help="Segundos entre chequeos.")
    parser.add_argument("--delay", type=float, default=0.5, help="Pausa entre fechas consultadas.")
    parser.add_argument("--watch-days", type=int, default=2, help="Cantidad de días recientes a vigilar. Default: hoy y ayer.")
    parser.add_argument("--allow-global-fallback", action="store_true", help="Permite fallback global protegido.")
    parser.add_argument("--once", action="store_true", help="Corre un ciclo y termina.")
    parser.add_argument("--verbose", action="store_true", help="Más detalle en consola.")

    args = parser.parse_args()

    logger = setup_logger(Path(args.log), verbose=args.verbose)

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    with single_instance_lock(Path(args.lock)):
        logger.info("🚀 Watcher Loto Pool iniciado.")
        logger.info(f"CSV: {Path(args.csv).resolve()}")
        logger.info(f"Intervalo: {args.interval}s")

        if args.once:
            run_watch_cycle(args, logger)
            logger.info("Modo --once finalizado.")
            return

        while not STOP:
            started = time.time()

            try:
                state = run_watch_cycle(args, logger)

                if state.changed:
                    logger.info(
                        f"🔥 CAMBIO DETECTADO | nuevos={state.added} | "
                        f"actualizados={state.updated}"
                    )

            except Exception as e:
                logger.exception(f"🔥 Error general del ciclo: {e}")

            elapsed = time.time() - started
            sleep_for = max(1, int(args.interval - elapsed))

            logger.info(f"⏳ Próxima revisión en {sleep_for}s. Ctrl+C para detener.")

            for _ in range(sleep_for):
                if STOP:
                    break
                time.sleep(1)

        logger.info("🛑 Watcher detenido correctamente.")


if __name__ == "__main__":
    main()