from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .payments import PayPalClient
from .repository import ResultsRepository


@lru_cache
def get_repository() -> ResultsRepository:
    s = get_settings()
    return ResultsRepository(csv_path=s.resultados_csv, database_url=s.database_url)


def get_paypal() -> PayPalClient:
    return PayPalClient(get_settings())


def settings_dep() -> Settings:
    return get_settings()
