"""Modelos SQLAlchemy. La base de datos es opcional: si no está configurada
o no responde, la API usa el CSV histórico."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Column, Date, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ResultadoTradicional(Base):
    __tablename__ = "resultados_tradicionales"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, index=True)
    loteria = Column(String, nullable=False, index=True)
    primer = Column(Integer)
    segundo = Column(Integer)
    tercero = Column(Integer)


@lru_cache
def get_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, connect_args=_connect_args(url))


def _connect_args(url: str) -> dict:
    return {"connect_timeout": 3} if url.startswith("postgresql") else {}


def session_factory(url: str):
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine(url))
