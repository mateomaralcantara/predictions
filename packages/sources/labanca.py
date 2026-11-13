"""Fuente: labanca.do (páginas por fecha desde el 2026-02-12).

Cada lotería tiene su URL ``/loterias/<grupo>/<juego>/<AAAA-MM-DD>/`` con la
frase «El número ganador de … del D de MES de AAAA fue a-b-c». Solo se acepta
el resultado si la fecha de la frase coincide con la pedida.

Florida y New York no se incluyen: labanca.do los publica como Pick 3/Pick 4
y su conversión a quiniela no está verificada contra el histórico.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests
from bs4 import BeautifulSoup

from .loteriasdominicanas import ResultadoDia, Sorteo

INICIO = date(2026, 2, 12)  # primera fecha con páginas en labanca.do
URL = "https://labanca.do/loterias/{slug}/{fecha:%Y-%m-%d}/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PredictionsRD/1.0)", "Accept-Language": "es-DO,es;q=0.9"}
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]  # fmt: skip

# Nombre en el histórico -> ruta en labanca.do
LOTERIAS: dict[str, str] = {
    "Lotería Nacional": "nacional/loteria-nacional",
    "Gana Más": "nacional/gana-mas",
    "Quiniela Leidsa": "leidsa/quiniela-pale",
    "Pega 3 Más": "leidsa/pega-3-mas",
    "Quiniela Loteka": "loteka/quiniela",
    "Quiniela LoteDom": "lotedom/quiniela",
    "La Primera Día": "la-primera/quiniela-dia",
    "Primera Noche": "la-primera/quiniela-noche",
    "King Lottery 12:30": "king-lottery/quiniela-dia",
    "King Lottery 7:30": "king-lottery/quiniela-noche",
    "Anguila Mañana": "anguila/quiniela-10am",
    "Anguila Medio Día": "anguila/quiniela-1pm",
    "Anguila Tarde": "anguila/quiniela-6pm",
    "Anguila Noche": "anguila/quiniela-9pm",
}


def parse(html: str, d: date) -> tuple[int, int, int] | None:
    texto = " ".join(BeautifulSoup(html, "html.parser").get_text(" ", strip=True).split())
    frase = re.escape(f"{d.day} de {MESES[d.month]} de {d.year}")
    m = re.search(rf"ganador de [^.]{{0,80}}?del {frase} fue (\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})\b", texto)
    if not m:
        return None
    nums = tuple(int(x) for x in m.groups())
    return nums if all(0 <= n <= 99 for n in nums) else None  # type: ignore[return-value]


def _descargar(session: requests.Session, slug: str, d: date, timeout: float, intentos: int = 3) -> str | None:
    for i in range(intentos):
        try:
            r = session.get(URL.format(slug=slug, fecha=d), headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(0.8 * 2**i)
    return None


def dia(
    d: date, session: requests.Session, timeout: float = 15, hilos: int = 6, omitir: set[str] | None = None
) -> ResultadoDia:
    """Resultados de un día. ``omitir``: loterías que ya se tienen (no se piden)."""
    if d < INICIO:
        return ResultadoDia(d, [])
    pendientes = {k: v for k, v in LOTERIAS.items() if k not in (omitir or set())}

    def una(item: tuple[str, str]) -> Sorteo | None:
        nombre, slug = item
        html = _descargar(session, slug, d, timeout)
        nums = parse(html, d) if html else None
        return Sorteo(d, nombre, *nums) if nums else None

    with ThreadPoolExecutor(max_workers=hilos) as ex:
        sorteos = [s for s in ex.map(una, pendientes.items()) if s]
    return ResultadoDia(d, sorteos)
