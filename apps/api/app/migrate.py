"""Ejecuta migraciones Alembic desde código (arranque de la API y tests)."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from .config import API_DIR


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    if url:
        cfg.attributes["url"] = url
    return cfg


def upgrade(url: str | None = None) -> None:
    command.upgrade(alembic_config(url), "head")
