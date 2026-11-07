"""Acceso a resultados de loterías tradicionales (3 números por sorteo).

Orden de fuentes: PostgreSQL (si ``DATABASE_URL`` está configurada y responde)
y, si no, el CSV histórico. Los datos se cachean en memoria con un TTL corto:
son ~25k filas, así que calcular estadísticas en Python es instantáneo.
"""

from __future__ import annotations

import csv
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from .db import ResultadoTradicional, session_factory

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Resultado:
    fecha: date
    loteria: str
    primer: int
    segundo: int
    tercero: int

    @property
    def numeros(self) -> tuple[int, int, int]:
        return (self.primer, self.segundo, self.tercero)

    def as_dict(self) -> dict:
        return {
            "fecha": self.fecha.isoformat(),
            "loteria": self.loteria,
            "numeros": list(self.numeros),
        }


def load_csv(path: Path) -> list[Resultado]:
    rows: list[Resultado] = []
    if not path.exists():
        log.warning("CSV de resultados no encontrado: %s", path)
        return rows
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                rows.append(
                    Resultado(
                        fecha=date.fromisoformat(row["fecha"].strip()),
                        loteria=row["loteria"].strip(),
                        primer=int(row["primer"]),
                        segundo=int(row["segundo"]),
                        tercero=int(row["tercero"]),
                    )
                )
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
    return rows


def load_db(url: str) -> list[Resultado]:
    Session = session_factory(url)
    with Session() as session:
        records = session.execute(select(ResultadoTradicional)).scalars().all()
        return [
            Resultado(r.fecha, r.loteria, int(r.primer), int(r.segundo), int(r.tercero))
            for r in records
            if None not in (r.fecha, r.loteria, r.primer, r.segundo, r.tercero)
        ]


class ResultsRepository:
    def __init__(self, csv_path: Path, database_url: str | None = None, ttl_seconds: float = 300):
        self.csv_path = csv_path
        self.database_url = database_url
        self.ttl_seconds = ttl_seconds
        self._rows: list[Resultado] = []
        self._source = "none"
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    @property
    def source(self) -> str:
        self.all()
        return self._source

    def all(self) -> list[Resultado]:
        now = time.monotonic()
        if self._loaded_at and now - self._loaded_at < self.ttl_seconds:
            return self._rows
        with self._lock:
            if self._loaded_at and time.monotonic() - self._loaded_at < self.ttl_seconds:
                return self._rows
            rows, source = self._load()
            rows.sort(key=lambda r: (r.fecha, r.loteria))
            self._rows, self._source, self._loaded_at = rows, source, time.monotonic()
            return rows

    def invalidate(self) -> None:
        with self._lock:
            self._loaded_at = 0.0

    def _load(self) -> tuple[list[Resultado], str]:
        if self.database_url:
            try:
                rows = load_db(self.database_url)
                if rows:
                    return rows, "postgres"
                log.warning("La base de datos no tiene resultados; usando CSV.")
            except Exception as exc:  # noqa: BLE001 - cualquier fallo de DB => CSV
                log.warning("No se pudo leer PostgreSQL (%s); usando CSV.", exc.__class__.__name__)
        return load_csv(self.csv_path), "csv"
