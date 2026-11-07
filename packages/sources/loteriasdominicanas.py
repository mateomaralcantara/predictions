"""Fuente: loteriasdominicanas.com (resultados de loterías tradicionales).

La página ``/?date=DD-MM-YYYY`` lista bloques ``.game-block`` con el nombre
de la lotería (``.game-title``), la fecha del sorteo (``.session-date``) y
tres ``.score``. Para días sin datos el sitio a veces devuelve el *último*
resultado: por eso cada bloque se valida contra la fecha pedida.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date

import requests
from bs4 import BeautifulSoup

URL = "https://loteriasdominicanas.com/?date={:%d-%m-%Y}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PredictionsRD-collector/1.0)",
    "Accept-Language": "es-DO,es;q=0.9",
}

LOTERIAS = (
    "Gana Más", "Lotería Nacional", "Loteria Real", "Lotería Real", "Pega 3 Más", "Quiniela Leidsa",
    "Florida Día", "New York Noche", "La Primera Día", "Primera Noche", "Quiniela Loteka",
    "Quiniela LoteDom", "La Suerte 12:30", "La Suerte 18:00", "Anguila Mañana", "Anguila Medio Día",
    "Anguila Tarde", "Anguila Noche", "King Lottery 12:30", "King Lottery 7:30",
)  # fmt: skip

_FECHA_RE = re.compile(r"\b(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?\b")


@dataclass(frozen=True)
class Sorteo:
    fecha: date
    loteria: str
    primer: int
    segundo: int
    tercero: int

    @property
    def numeros(self) -> tuple[int, int, int]:
        return (self.primer, self.segundo, self.tercero)


@dataclass
class ResultadoDia:
    fecha: date
    sorteos: list[Sorteo]
    descartados_fecha: int = 0  # bloques cuya fecha no coincide (página obsoleta)


def _fecha_bloque(texto: str, objetivo: date) -> date | None:
    m = _FECHA_RE.search(texto or "")
    if not m:
        return None
    dia, mes, anio = int(m.group(1)), int(m.group(2)), m.group(3)
    year = objetivo.year if anio is None else (int(anio) + 2000 if len(anio) == 2 else int(anio))
    try:
        return date(year, mes, dia)
    except ValueError:
        return None


def parse(html: str, objetivo: date, loterias: tuple[str, ...] = LOTERIAS) -> ResultadoDia:
    soup = BeautifulSoup(html, "html.parser")
    sorteos: list[Sorteo] = []
    descartados = 0
    for bloque in soup.select(".game-block"):
        titulo = bloque.select_one(".game-title span") or bloque.select_one(".game-title")
        if not titulo:
            continue
        nombre = " ".join(titulo.get_text(" ", strip=True).split())
        if nombre not in loterias:
            continue
        fecha_node = bloque.select_one(".session-date")
        if fecha_node is not None:
            f = _fecha_bloque(fecha_node.get_text(" ", strip=True), objetivo)
            if f is not None and f != objetivo:
                descartados += 1
                continue
        try:
            nums = [int(n.get_text(strip=True)) for n in bloque.select(".score")]
        except ValueError:
            continue
        if len(nums) != 3 or not all(0 <= n <= 99 for n in nums):
            continue
        sorteos.append(Sorteo(objetivo, nombre.replace("Loteria Real", "Lotería Real"), *nums))
    # Una misma lotería no puede aparecer dos veces el mismo día.
    unicos = {s.loteria: s for s in sorteos}
    return ResultadoDia(objetivo, list(unicos.values()), descartados)


def descargar(fecha: date, session: requests.Session, timeout: float = 15, intentos: int = 3) -> str | None:
    for intento in range(intentos):
        try:
            r = session.get(URL.format(fecha), headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(0.8 * (2**intento))
    return None
