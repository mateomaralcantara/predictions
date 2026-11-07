"""Sincroniza Loto Pool (LEIDSA: 5 números del 1 al 31, sorteo diario) desde labanca.do.

    python packages/games/lotopool/sync.py                    # del último dato a hoy
    python packages/games/lotopool/sync.py --desde 2026-05-25 # re-verifica desde esa fecha

La página de cada fecha incluye la frase «El número ganador de Loto Pool
Leidsa del D de MES de AAAA fue a-b-c-d-e»; solo se acepta si la fecha
de la frase coincide con la pedida (evita guardar el resultado de otro día).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
CSV_POR_DEFECTO = ROOT / "data" / "lotopool" / "lotopool_historico.csv"
URL = "https://labanca.do/loterias/leidsa/loto-pool/{:%Y-%m-%d}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PredictionsRD/1.0)", "Accept-Language": "es-DO,es;q=0.9"}
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]  # fmt: skip
CAMPOS = ["fecha", "num1", "num2", "num3", "num4", "num5"]


def valido(nums: list[int]) -> bool:
    return len(nums) == 5 and len(set(nums)) == 5 and all(1 <= n <= 31 for n in nums)


def parse(html: str, d: date) -> list[int] | None:
    texto = " ".join(BeautifulSoup(html, "html.parser").get_text(" ", strip=True).split())
    frase = re.escape(f"{d.day} de {MESES[d.month]} de {d.year}")
    m = re.search(rf"ganador de Loto Pool[^.]{{0,40}}?del {frase} fue ((?:\d{{1,2}}-){{4}}\d{{1,2}})", texto, re.I)
    if not m:
        return None
    nums = sorted(int(x) for x in m.group(1).split("-"))
    return nums if valido(nums) else None


def leer(path: Path) -> dict[date, list[int]]:
    out: dict[date, list[int]] = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.reader(fh):
                try:
                    d = date.fromisoformat(row[0].strip())
                    nums = sorted(int(x) for x in row[1:6])
                except (ValueError, IndexError):
                    continue
                if valido(nums):
                    out[d] = nums
    return out


def escribir(path: Path, filas: dict[date, list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CAMPOS)
        for d in sorted(filas):
            w.writerow([d.isoformat(), *filas[d]])
    tmp.replace(path)


def descargar(session: requests.Session, d: date, intentos: int = 3) -> str | None:
    for i in range(intentos):
        try:
            r = session.get(URL.format(d), headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(0.8 * 2**i)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sincroniza Loto Pool desde labanca.do")
    ap.add_argument("--csv", type=Path, default=CSV_POR_DEFECTO)
    ap.add_argument("--desde", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date())
    ap.add_argument("--hasta", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(), default=date.today())
    ap.add_argument("--pausa", type=float, default=0.3)
    args = ap.parse_args(argv)

    filas = leer(args.csv)
    desde = args.desde or ((max(filas) + timedelta(days=1)) if filas else date(2024, 12, 1))
    session = requests.Session()
    nuevos = corregidos = sin_dato = 0
    d = desde
    while d <= args.hasta:
        html = descargar(session, d)
        nums = parse(html, d) if html else None
        if nums is None:
            sin_dato += 1
            print(f"{d}: sin resultado")
        elif d not in filas:
            filas[d] = nums
            nuevos += 1
            print(f"{d}: {nums}")
        elif filas[d] != nums:
            print(f"{d}: corregido {filas[d]} -> {nums}")
            filas[d] = nums
            corregidos += 1
        d += timedelta(days=1)
        time.sleep(args.pausa)
    if nuevos or corregidos:
        escribir(args.csv, filas)
    print(f"Loto Pool listo: {nuevos} nuevos, {corregidos} corregidos, {sin_dato} sin resultado. Último: {max(filas) if filas else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
