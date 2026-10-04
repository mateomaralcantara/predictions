
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import requests
from bs4 import BeautifulSoup
from bs4 import FeatureNotFound

DEFAULT_CSV = "superkino_historico.csv"
DEFAULT_FULL_SYNC_START = date(2010, 1, 1)
DEFAULT_STATE_FILE = "superkino_watch_state.json"

MIN_NUMBER = 1
MAX_NUMBER = 84
DRAW_SIZE = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

BASE_URLS = (
    ("LB", "https://labanca.do/loterias/leidsa/super-kino-tv/{:%Y-%m-%d}/"),
    ("C", "https://loteriasdominicanas.com/pagina/ultimos-resultados?date={:%Y-%m-%d}"),
    ("A", "https://loteriasdominicanas.com/leidsa/super-kino-tv?date={:%Y-%m-%d}"),
    ("B", "https://loteriasdominicanas.com/leidsa/super-kino-tv?date={:%d-%m-%Y}"),
)

LATEST_URLS = (
    ("LBL", "https://labanca.do/loterias/leidsa/super-kino-tv/"),
    ("L1", "https://loteriasdominicanas.com/leidsa/super-kino-tv"),
    ("L2", "https://loteriasdominicanas.com/leidsa"),
    ("L3", "https://loteriasdominicanas.com/pagina/ultimos-resultados"),
)

DOW_CODES = ["L", "M", "X", "J", "V", "S", "D"]

DATE_RE = re.compile(
    r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b|\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"
)
RUN20_RE = re.compile(r"(?:\b\d{1,2}\b\s+){19}\b\d{1,2}\b")
SUPERKINO_LABEL_RE = re.compile(r"super\s*kino\s*tv|kino\s*tv|kinotv|super\s*kino", re.I)

SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def load_rd_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Santo_Domingo")
    except Exception:
        try:
            import pytz
            return pytz.timezone("America/Santo_Domingo")
        except Exception:
            return None


RD_TZ = load_rd_tz()


def now_rd() -> datetime:
    if RD_TZ is None:
        return datetime.now()
    return datetime.now(RD_TZ)


def today_rd() -> date:
    return now_rd().date()


def after_cutoff_rd(d: date) -> bool:
    n = now_rd()
    if d != n.date():
        return True
    # Domingo 15:55, resto 20:55
    if n.weekday() == 6:
        return (n.hour, n.minute) >= (15, 55)
    return (n.hour, n.minute) >= (20, 55)


def weekday_code(d: date) -> str:
    return DOW_CODES[d.weekday()]


def parse_dias(dias_str: str) -> Set[str]:
    dias_str = dias_str.upper().replace(",", "").replace(" ", "")
    given = set(dias_str)
    valid = set(DOW_CODES)
    if not given or not given.issubset(valid):
        raise ValueError("Valor inválido para --dias. Usa letras de 'LMXJVSD'.")
    return given


def parse_date_flexible(s: str) -> date:
    s = (s or "").strip()
    if not s:
        raise ValueError("Fecha vacía.")
    try:
        return date.fromisoformat(s)
    except Exception:
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    raise ValueError(f"Fecha inválida: {s}. Usa YYYY-MM-DD o DD/MM/YYYY.")


parse_iso_date = parse_date_flexible


def iter_dates(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def ensure_header(csv_path: Path) -> None:
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fecha"] + [f"num_{i}" for i in range(1, 21)])


def parse_date_cell(raw: str) -> Optional[date]:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except Exception:
            continue
    return None


def _date_from_match(m: re.Match) -> Optional[date]:
    try:
        if m.group(1) and m.group(2) and m.group(3):
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if m.group(4) and m.group(5) and m.group(6):
            yy = int(m.group(6))
            year = yy if yy >= 100 else 2000 + yy
            return date(year, int(m.group(5)), int(m.group(4)))
    except Exception:
        return None
    return None


def _logical_rows_from_cells(row: Sequence[str]) -> List[Tuple[date, List[int]]]:
    """Recupera una o varias filas lógicas incluso si dos sorteos quedaron concatenados."""
    out: List[Tuple[date, List[int]]] = []
    current_date: Optional[date] = None
    current_nums: List[int] = []

    def flush() -> None:
        nonlocal current_date, current_nums
        if current_date is not None:
            nums = dedupe_keep_order(current_nums, DRAW_SIZE)
            if validar_superkino(nums):
                out.append((current_date, nums))
        current_nums = []

    for raw in row:
        cell = (raw or "").strip()
        if not cell:
            continue

        exact_date = parse_date_cell(cell)
        match = None if exact_date is not None else DATE_RE.search(cell)
        embedded_date = _date_from_match(match) if match else None
        found_date = exact_date or embedded_date

        if found_date is not None:
            if match and match.start() > 0 and current_date is not None:
                before = cell[:match.start()].strip(" ,;|")
                if before.isdigit():
                    current_nums.append(int(before))

            flush()
            current_date = found_date

            if match and match.end() < len(cell):
                after = cell[match.end():].strip(" ,;|")
                if after.isdigit():
                    current_nums.append(int(after))
            continue

        if current_date is not None and cell.isdigit():
            current_nums.append(int(cell))

    flush()
    return out


def parse_csv_rows_loose(csv_path: Path) -> List[Tuple[date, List[int]]]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []

    rows: List[Tuple[date, List[int]]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, start=1):
            if not row:
                continue
            if i == 1 and row[0].strip().lower() in {"fecha", "date"}:
                continue
            rows.extend(_logical_rows_from_cells(row))

    return rows


def read_existing_dates(csv_path: Path) -> Tuple[Set[date], Optional[date], Optional[date]]:
    rows = parse_csv_rows_loose(csv_path)
    if not rows:
        return set(), None, None
    dates = sorted({d for d, _ in rows})
    return set(dates), dates[0], dates[-1]


def load_csv_map(csv_path: Path) -> Dict[date, List[int]]:
    mp: Dict[date, List[int]] = {}
    for d, nums in parse_csv_rows_loose(csv_path):
        mp[d] = nums
    return dict(sorted(mp.items(), key=lambda kv: kv[0]))


def write_csv_map(csv_path: Path, rows_map: Dict[date, List[int]], backup: bool = False) -> int:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if backup and csv_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = csv_path.with_suffix(csv_path.suffix + f".bak_{stamp}")
        bak.write_bytes(csv_path.read_bytes())

    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fecha"] + [f"num_{i}" for i in range(1, 21)])
        for d, nums in sorted(rows_map.items(), key=lambda kv: kv[0]):
            w.writerow([d.isoformat()] + list(nums))
    tmp.replace(csv_path)
    return len(rows_map)


def append_rows(csv_path: Path, rows: Sequence[Tuple[date, List[int]]]) -> int:
    rows_map = load_csv_map(csv_path)
    added = 0
    for d, nums in rows:
        if d not in rows_map:
            rows_map[d] = nums
            added += 1
    if added:
        write_csv_map(csv_path, rows_map, backup=False)
    return added


def upsert_rows(csv_path: Path, rows: Sequence[Tuple[date, List[int]]], backup: bool = False) -> Tuple[int, int]:
    rows_map = load_csv_map(csv_path)
    inserted = 0
    updated = 0
    for d, nums in rows:
        old = rows_map.get(d)
        if old is None:
            rows_map[d] = nums
            inserted += 1
        elif old != nums:
            rows_map[d] = nums
            updated += 1
    if inserted or updated:
        write_csv_map(csv_path, rows_map, backup=backup)
    return inserted, updated


def dump_debug_html(debug_dir: Optional[Path], d: date, tag: str, reason: str, html: str) -> None:
    if not debug_dir:
        return
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        safe_reason = re.sub(r"[^a-zA-Z0-9_-]+", "-", reason)[:40]
        p = debug_dir / f"{d.isoformat()}_{tag}_{safe_reason}.html"
        p.write_text(html, encoding="utf-8")
    except Exception:
        return


@dataclass(frozen=True)
class FetchConfig:
    timeout_s: float = 15.0
    attempts: int = 3
    backoff_s: float = 0.8
    max_retry_after_s: float = 20.0


def fetch_html(session: requests.Session, url: str, cfg: FetchConfig) -> Optional[str]:
    for i in range(1, cfg.attempts + 1):
        try:
            r = session.get(url, timeout=cfg.timeout_s)
            if r.status_code == 429:
                ra = r.headers.get("Retry-After", "")
                wait_s = min(float(int(ra)), cfg.max_retry_after_s) if ra.isdigit() else cfg.backoff_s * i
                time.sleep(wait_s)
                continue
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            if i >= cfg.attempts:
                return None
            time.sleep(cfg.backoff_s * i)
    return None


def make_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


def normalize_text(s: str) -> str:
    return " ".join((s or "").split()).strip().lower()


def date_tokens(d: date) -> List[str]:
    tokens = [
        d.strftime("%Y-%m-%d"),
        d.strftime("%d-%m-%Y"),
        d.strftime("%d/%m/%Y"),
        d.strftime("%Y/%m/%d"),
        d.strftime("%d-%m"),
        d.strftime("%d/%m"),
        f"{d.day}-{d.month:02d}",
        f"{d.day}/{d.month:02d}",
        f"{d.day} de {SPANISH_MONTHS[d.month]} de {d.year}",
    ]
    return list(dict.fromkeys(tokens))


def extract_page_date(soup: BeautifulSoup) -> Optional[date]:
    text = soup.get_text(" ", strip=True)
    m = DATE_RE.search(text)
    if not m:
        return None
    if m.group(1) and m.group(2) and m.group(3):
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None
    if m.group(4) and m.group(5) and m.group(6):
        yy = int(m.group(6))
        year = yy if yy >= 100 else (2000 + yy)
        try:
            return date(year, int(m.group(5)), int(m.group(4)))
        except Exception:
            return None
    return None


def page_mentions_target_date(soup: BeautifulSoup, d: date) -> bool:
    text = soup.get_text(" ", strip=True)
    return any(token in text for token in date_tokens(d))


def validar_superkino(nums: List[int]) -> bool:
    return (
        len(nums) == DRAW_SIZE
        and len(set(nums)) == DRAW_SIZE
        and all(MIN_NUMBER <= n <= MAX_NUMBER for n in nums)
    )


def dedupe_keep_order(nums: List[int], target: int = DRAW_SIZE) -> List[int]:
    seen: Set[int] = set()
    out: List[int] = []
    for n in nums:
        if n in seen:
            continue
        out.append(n)
        seen.add(n)
        if len(out) >= target:
            break
    return out


def ints_in(node) -> List[int]:
    nums: List[int] = []
    for el in node.select("span.score, li span.number, span.number, .score, .number"):
        t = el.get_text(strip=True)
        if t.isdigit():
            nums.append(int(t))
    return nums


def extract_20_from_result_sentence(soup: BeautifulSoup, target: Optional[date] = None) -> Optional[List[int]]:
    """Extrae la frase estable: '... del <fecha> fue 01-02-...-20'."""
    text = soup.get_text(" ", strip=True)
    if target is not None:
        date_phrase = re.escape(f"{target.day} de {SPANISH_MONTHS[target.month]} de {target.year}")
        pattern = rf"(?:super\s*kino\s*tv|súper\s*kino\s*tv).{{0,180}}?{date_phrase}.{{0,120}}?fue\s+((?:\d{{1,2}}[-\s]+){{19}}\d{{1,2}})"
    else:
        pattern = r"(?:super\s*kino\s*tv|súper\s*kino\s*tv).{0,260}?fue\s+((?:\d{1,2}[-\s]+){19}\d{1,2})"

    m = re.search(pattern, text, flags=re.I | re.S)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    nums = dedupe_keep_order(nums, DRAW_SIZE)
    return nums if validar_superkino(nums) else None


def extract_spanish_page_date(soup: BeautifulSoup) -> Optional[date]:
    text = normalize_text(soup.get_text(" ", strip=True))
    month_lookup = {name: num for num, name in SPANISH_MONTHS.items()}
    m = re.search(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(20\d{2})\b",
        text,
        flags=re.I,
    )
    if not m:
        return None
    try:
        return date(int(m.group(3)), month_lookup[m.group(2).lower()], int(m.group(1)))
    except Exception:
        return None


def extract_20_by_labeled_section(soup: BeautifulSoup, target: Optional[date] = None) -> Optional[List[int]]:
    text = soup.get_text(" ", strip=True)
    label_pat = r"(?:super\s*kino\s*tv|kino\s*tv|kinotv|super\s*kino)"
    run_pat = r"((?:\b\d{1,2}\b\s+){19}\b\d{1,2}\b)"
    patterns: List[str] = []
    if target is not None:
        for token in date_tokens(target):
            t = re.escape(token)
            patterns.extend([
                rf"{t}.{{0,220}}?{label_pat}.{{0,260}}?{run_pat}",
                rf"{label_pat}.{{0,260}}?{t}.{{0,260}}?{run_pat}",
            ])
    patterns.append(rf"{label_pat}.{{0,300}}?{run_pat}")
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I | re.S)
        if not m:
            continue
        chunk = m.group(1)
        nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", chunk)]
        nums = dedupe_keep_order(nums, 20)
        if validar_superkino(nums):
            return nums
    return None


def extract_20_by_text_run(soup: BeautifulSoup, target: Optional[date] = None) -> Optional[List[int]]:
    text = soup.get_text(" ", strip=True)
    targets: List[int] = []
    if target is not None:
        for s in date_tokens(target):
            idx = text.find(s)
            if idx != -1:
                targets.append(idx)
    best: Optional[Tuple[int, List[int]]] = None
    for m in RUN20_RE.finditer(text):
        nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", m.group(0))]
        nums = dedupe_keep_order(nums, 20)
        if not validar_superkino(nums):
            continue
        if not targets:
            return nums
        pos = m.start()
        dist = min(abs(pos - t) for t in targets)
        if best is None or dist < best[0]:
            best = (dist, nums)
    return best[1] if best else None


def extract_20_from_gameblocks(soup: BeautifulSoup) -> Optional[List[int]]:
    selectors = [".game-block", ".result", ".result-item", "article", ".card"]
    for sel in selectors:
        for block in soup.select(sel):
            title = normalize_text(block.get_text(" ", strip=True))
            if "super kino" not in title and "kino tv" not in title:
                continue
            nums = dedupe_keep_order(ints_in(block), 20)
            if validar_superkino(nums):
                return nums
            txt_nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", block.get_text(" ", strip=True))]
            txt_nums = dedupe_keep_order(txt_nums, 20)
            if validar_superkino(txt_nums):
                return txt_nums
    return None


def extract_latest_superkino_entry(soup: BeautifulSoup) -> Optional[Tuple[date, List[int]]]:
    text = soup.get_text(" ", strip=True)
    # Busca secuencias tipo "03-06 Super Kino TV 01 07 11 ..."
    pattern = re.compile(
        r"(\d{2}-\d{2}(?:-\d{4})?).{0,120}?(?:super\s*kino\s*tv|kino\s*tv|kinotv|super\s*kino).{0,200}?((?:\b\d{1,2}\b\s+){19}\b\d{1,2}\b)",
        re.I | re.S
    )
    best: Optional[Tuple[date, List[int]]] = None
    current_year = today_rd().year
    for m in pattern.finditer(text):
        raw_date = m.group(1)
        nums = dedupe_keep_order([int(x) for x in re.findall(r"\b\d{1,2}\b", m.group(2))], 20)
        if not validar_superkino(nums):
            continue
        d: Optional[date] = None
        for fmt in ("%d-%m-%Y", "%d-%m"):
            try:
                parsed = datetime.strptime(raw_date, fmt)
                if fmt == "%d-%m":
                    d = date(current_year, parsed.month, parsed.day)
                else:
                    d = parsed.date()
                break
            except Exception:
                continue
        if d is None:
            continue
        if best is None or d > best[0]:
            best = (d, nums)
    return best


def scrape_superkino_for_date(
    session: requests.Session,
    d: date,
    cfg: FetchConfig,
    validate_page_date: bool = True,
    debug_dir: Optional[Path] = None,
) -> Optional[Tuple[date, List[int], str]]:
    extractors: Sequence[Callable[[BeautifulSoup], Optional[List[int]]]] = (
        lambda soup: extract_20_from_result_sentence(soup, target=d),
        lambda soup: extract_20_by_labeled_section(soup, target=d),
        lambda soup: extract_20_by_text_run(soup, target=d),
        extract_20_from_gameblocks,
        lambda soup: None,
    )

    for tag, tpl in BASE_URLS:
        url = tpl.format(datetime.combine(d, datetime.min.time()))
        html = fetch_html(session, url, cfg)
        if not html:
            continue
        soup = make_soup(html)
        if validate_page_date and not page_mentions_target_date(soup, d):
            visible_date = extract_page_date(soup) or extract_spanish_page_date(soup)
            reason = f"date-mismatch-{visible_date.isoformat()}" if visible_date else "date-mismatch"
            dump_debug_html(debug_dir, d, tag, reason, html)
            continue

        for ex in extractors:
            nums = ex(soup)
            if nums:
                nums = dedupe_keep_order(nums, 20)
                if validar_superkino(nums):
                    return d, nums, tag
        dump_debug_html(debug_dir, d, tag, "no-nums", html)
    return None


def extract_latest_stable_entry(soup: BeautifulSoup) -> Optional[Tuple[date, List[int]]]:
    d = extract_spanish_page_date(soup) or extract_page_date(soup)
    if d is None:
        return None
    nums = extract_20_from_result_sentence(soup, target=d)
    if nums and validar_superkino(nums):
        return d, nums
    return None


def scrape_latest_superkino(
    session: requests.Session,
    cfg: FetchConfig,
    debug_dir: Optional[Path] = None,
) -> Optional[Tuple[date, List[int], str]]:
    for tag, url in LATEST_URLS:
        html = fetch_html(session, url, cfg)
        if not html:
            continue
        soup = make_soup(html)
        entry = extract_latest_stable_entry(soup) or extract_latest_superkino_entry(soup)
        if entry:
            d, nums = entry
            if validar_superkino(nums):
                return d, nums, tag
        nums = extract_20_from_gameblocks(soup) or extract_20_by_labeled_section(soup)
        if nums:
            # Sin fecha confiable no se guarda, pero sirve para debug.
            dump_debug_html(debug_dir, today_rd(), tag, "latest-no-date", html)
    return None


def build_targets(
    start_d: date,
    end_d: date,
    dias_set: Set[str],
    existing: Set[date],
    skip_early_today: bool,
) -> List[date]:
    out: List[date] = []
    for d in iter_dates(start_d, end_d):
        if weekday_code(d) not in dias_set:
            continue
        if skip_early_today and not after_cutoff_rd(d):
            continue
        if d not in existing:
            out.append(d)
    return out


def pick_sync_start(args_start: Optional[str], existing_min: Optional[date]) -> date:
    if args_start:
        return parse_iso_date(args_start)
    if existing_min is not None:
        return existing_min
    return DEFAULT_FULL_SYNC_START


def compact_signature(nums: List[int]) -> str:
    return hashlib.sha1(",".join(map(str, nums)).encode("utf-8")).hexdigest()[:12]


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def repair_csv(csv_path: Path, backup: bool = True) -> dict:
    rows = parse_csv_rows_loose(csv_path)
    before = len(rows)
    mp: Dict[date, List[int]] = {}
    duplicates = 0
    for d, nums in rows:
        if d in mp:
            duplicates += 1
        mp[d] = nums
    write_csv_map(csv_path, mp, backup=backup)
    dates = sorted(mp)
    return {
        "rows_inferidas": before,
        "rows_finales": len(mp),
        "duplicados_resueltos": duplicates,
        "fecha_min": dates[0].isoformat() if dates else None,
        "fecha_max": dates[-1].isoformat() if dates else None,
    }


def watch_latest(
    session: requests.Session,
    csv_path: Path,
    cfg: FetchConfig,
    state_path: Path,
    interval_s: float,
    max_cycles: int,
    backup_on_change: bool,
    debug_dir: Optional[Path] = None,
) -> None:
    state = load_state(state_path)
    cycles = 0
    print(f"👀 Vigilando Super Kino cada {interval_s:.0f}s. Ctrl+C para salir.")
    while True:
        cycles += 1
        latest = scrape_latest_superkino(session, cfg, debug_dir=debug_dir)
        if latest:
            d, nums, tag = latest
            sig = compact_signature(nums)
            prev = state.get("last_signature")
            prev_date = state.get("last_date")
            inserted, updated = upsert_rows(csv_path, [(d, nums)], backup=backup_on_change)
            state.update({
                "last_date": d.isoformat(),
                "last_signature": sig,
                "last_nums": nums,
                "last_source": tag,
                "last_seen_at": now_rd().isoformat(),
            })
            save_state(state_path, state)

            if inserted:
                print(f"✅ Nuevo resultado detectado {d.isoformat()} ({tag}) -> insertado.")
            elif updated:
                print(f"♻️ Cambio detectado {d.isoformat()} ({tag}) -> fila actualizada.")
            else:
                changed = (prev != sig) or (prev_date != d.isoformat())
                if changed:
                    print(f"ℹ️ Resultado observado {d.isoformat()} ({tag}) sin cambios de CSV.")
                else:
                    print(f"… sin novedad ({d.isoformat()} / {tag})")
        else:
            print("… no se pudo extraer resultado reciente")
        if max_cycles > 0 and cycles >= max_cycles:
            print("🛑 Watch finalizado por límite de ciclos.")
            return
        time.sleep(interval_s)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="SuperKino (Leidsa) — limpia CSV, sincroniza faltantes y vigila cambios en la página."
    )
    ap.add_argument("--csv", default=DEFAULT_CSV, help="Ruta del CSV histórico.")
    ap.add_argument("--dias", default="LMXJVSD", help="Días con sorteo (LMXJVSD).")
    ap.add_argument("--delay", type=float, default=0.4, help="Pausa entre fechas (segundos).")
    ap.add_argument("--skip-early-today", action="store_true", help="No procesa hoy si aún no pasó la hora del sorteo.")
    ap.add_argument("--include-early-today", action="store_true", help="Fuerza procesar hoy aunque falte el horario.")
    ap.add_argument("--probe", nargs="*", help="Diagnóstico: fechas (YYYY-MM-DD ...) sin guardar.")
    ap.add_argument("--append-latest", action="store_true", help="Desde la fecha más reciente del CSV +1 día hasta hoy.")
    ap.add_argument("--sync-missing", action="store_true", help="Rellena huecos desde --start (o min del CSV) hasta hoy.")
    ap.add_argument("--start", help="Inicio YYYY-MM-DD.")
    ap.add_argument("--timeout-s", type=float, default=15.0, help="Timeout por request.")
    ap.add_argument("--attempts", type=int, default=3, help="Reintentos por URL.")
    ap.add_argument("--backoff", type=float, default=0.8, help="Backoff base.")
    ap.add_argument("--no-validate-page-date", action="store_true", help="Desactiva validación de fecha en HTML.")
    ap.add_argument("--debug-dir", help="Guarda HTML crudo cuando falle el parseo.")
    ap.add_argument("--repair-csv", action="store_true", help="Limpia y normaliza el CSV antes de cualquier otra cosa.")
    ap.add_argument("--backup-csv", action="store_true", help="Guarda backup antes de reescribir CSV.")
    ap.add_argument("--watch-latest", action="store_true", help="Vigila la página y actualiza el CSV si el resultado cambia.")
    ap.add_argument("--poll-seconds", type=float, default=90.0, help="Cada cuántos segundos revisar en watch.")
    ap.add_argument("--max-cycles", type=int, default=0, help="Máximo de ciclos en watch (0 = infinito).")
    ap.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="JSON para recordar el último resultado observado.")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    state_path = Path(args.state_file)
    debug_dir: Optional[Path] = Path(args.debug_dir) if args.debug_dir else None

    ensure_header(csv_path)

    if args.repair_csv:
        info = repair_csv(csv_path, backup=args.backup_csv)
        print("🧹 CSV reparado:")
        for k, v in info.items():
            print(f"   - {k}: {v}")

    try:
        dias_set = parse_dias(args.dias)
    except Exception as e:
        print(f"Error en --dias: {e}", file=sys.stderr)
        raise SystemExit(1)

    existing, mn, mx = read_existing_dates(csv_path)
    cfg = FetchConfig(timeout_s=args.timeout_s, attempts=max(1, args.attempts), backoff_s=max(0.1, args.backoff))
    validate_page_date = not args.no_validate_page_date

    if not args.append_latest and not args.sync_missing and not args.probe and not args.watch_latest and not args.repair_csv:
        args.append_latest = True
        print("Modo automático: --append-latest activado.")

    skip_early_today = True
    if args.include_early_today:
        skip_early_today = False
    elif args.skip_early_today:
        skip_early_today = True

    with requests.Session() as s:
        s.headers.update(HEADERS)

        if args.probe:
            for fs in args.probe:
                try:
                    d = parse_iso_date(fs)
                except Exception:
                    print(f"Fecha inválida en --probe: {fs}", file=sys.stderr)
                    continue
                print(f"Probe {d.isoformat()} ({weekday_code(d)}): ", end="", flush=True)
                res = scrape_superkino_for_date(s, d, cfg, validate_page_date=validate_page_date, debug_dir=debug_dir)
                if res:
                    _, nums, tag = res
                    print(f"OK {tag} -> {nums}")
                else:
                    print("—")
                time.sleep(args.delay)

        if args.watch_latest:
            watch_latest(
                session=s,
                csv_path=csv_path,
                cfg=cfg,
                state_path=state_path,
                interval_s=max(15.0, args.poll_seconds),
                max_cycles=max(0, args.max_cycles),
                backup_on_change=args.backup_csv,
                debug_dir=debug_dir,
            )

        if args.sync_missing:
            start_date = pick_sync_start(args.start, mn)
            end_date = today_rd()
            if start_date > end_date:
                print(f"Rango inválido: inicio {start_date} > hoy RD {end_date}")
                raise SystemExit(1)

            targets = build_targets(start_date, end_date, dias_set, existing, skip_early_today)
            if not targets:
                print(f"✅ No hay huecos por rellenar entre {start_date} y {end_date}. CSV min/max: {mn} / {mx}")
            else:
                print(f"🧩 Huecos detectados: {len(targets)} (de {start_date} a {end_date})")
                found: List[Tuple[date, List[int]]] = []
                misses = 0
                for d in targets:
                    print(f"🔍 {d.isoformat()} ({weekday_code(d)}) ... ", end="", flush=True)
                    res = scrape_superkino_for_date(s, d, cfg, validate_page_date=validate_page_date, debug_dir=debug_dir)
                    if res:
                        dd, nums, tag = res
                        found.append((dd, nums))
                        existing.add(dd)
                        print(f"✅ ({tag})")
                    else:
                        misses += 1
                        print("—")
                    time.sleep(args.delay)
                ins, upd = upsert_rows(csv_path, found, backup=args.backup_csv)
                print(f"🎉 Sync completa. CSV: {csv_path} | Insertados: {ins} | Actualizados: {upd} | Sin resultado: {misses}")

        if args.append_latest:
            if mx is None:
                start_date = parse_iso_date(args.start) if args.start else DEFAULT_FULL_SYNC_START
                if not args.start:
                    print("CSV vacío: usaré 2010-01-01 como inicio por defecto.")
            else:
                start_date = mx + timedelta(days=1)

            end_date = today_rd()
            if start_date > end_date:
                print(f"✅ Ya estás al día. Última fecha en CSV: {mx} | Hoy RD: {end_date}")
            else:
                targets = build_targets(start_date, end_date, dias_set, existing, skip_early_today)
                if not targets:
                    print(f"✅ No hay faltantes recientes. Última fecha en CSV: {mx} | Hoy RD: {end_date}")
                else:
                    print(f"🧩 Faltantes detectados: {len(targets)} (de {start_date} a {end_date})")
                    found: List[Tuple[date, List[int]]] = []
                    misses = 0
                    for d in targets:
                        print(f"🔍 {d.isoformat()} ({weekday_code(d)}) ... ", end="", flush=True)
                        res = scrape_superkino_for_date(s, d, cfg, validate_page_date=validate_page_date, debug_dir=debug_dir)
                        if res:
                            dd, nums, tag = res
                            found.append((dd, nums))
                            existing.add(dd)
                            print(f"✅ ({tag})")
                        else:
                            misses += 1
                            print("—")
                        time.sleep(args.delay)
                    ins, upd = upsert_rows(csv_path, found, backup=args.backup_csv)
                    print(f"🎉 Listo. CSV: {csv_path} | Insertados: {ins} | Actualizados: {upd} | Sin resultado: {misses}")

        if not args.append_latest and not args.sync_missing and not args.probe and not args.watch_latest:
            print("Nada que hacer. Usa --append-latest, --sync-missing, --watch-latest o --probe.")


if __name__ == "__main__":
    main()