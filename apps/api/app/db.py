"""Modelos y sesiones SQLAlchemy.

- Base de datos de la app (usuarios, órdenes, suscripciones): ``DATABASE_URL``
  o, si no está definida, SQLite en ``data/app.db``.
- Resultados históricos: misma base si es PostgreSQL; si no, CSV.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def utcnow() -> datetime:
    """UTC sin tzinfo: SQLite no guarda zonas horarias y así comparamos igual en todas las bases."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ResultadoTradicional(Base):
    __tablename__ = "resultados_tradicionales"
    __table_args__ = (UniqueConstraint("fecha", "loteria", name="uq_resultado_fecha_loteria"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha = mapped_column(Date, nullable=False, index=True)
    loteria: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    primer: Mapped[int] = mapped_column(Integer, nullable=False)
    segundo: Mapped[int] = mapped_column(Integer, nullable=False)
    tercero: Mapped[int] = mapped_column(Integer, nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    es_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    suscripciones: Mapped[list[Suscripcion]] = relationship(back_populates="usuario", order_by="Suscripcion.fin")


class Orden(Base):
    __tablename__ = "ordenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paypal_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(40), nullable=False)
    monto: Mapped[str] = mapped_column(String(16), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="CREADA", nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    capturada_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Suscripcion(Base):
    __tablename__ = "suscripciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    orden_id: Mapped[int | None] = mapped_column(ForeignKey("ordenes.id"), nullable=True, unique=True)
    plan: Mapped[str] = mapped_column(String(40), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    usuario: Mapped[Usuario] = relationship(back_populates="suscripciones")


def normalizar_url(url: str) -> str:
    """Fuerza el driver psycopg 3 y acepta el esquema ``postgres://`` de Render/Railway/Heroku."""
    for prefijo in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo) :]
    return url


@lru_cache
def get_engine(url: str) -> Engine:
    url = normalizar_url(url)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args_postgres(url))


def connect_args_postgres(url: str) -> dict:
    """Opciones de conexión; ajustes específicos para Supabase."""
    if not url.startswith("postgresql"):
        return {}
    args: dict = {"connect_timeout": 5}
    parsed = make_url(url)
    host = parsed.host or ""
    if host.endswith((".supabase.co", ".supabase.com")) and "sslmode" not in parsed.query:
        args["sslmode"] = "require"
    # El "transaction pooler" (PgBouncer, puerto 6543) no admite sentencias
    # preparadas en el servidor: hay que desactivarlas en psycopg 3.
    if parsed.port == 6543:
        args["prepare_threshold"] = None
    return args


@lru_cache
def session_factory(url: str) -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=get_engine(url))


def session_scope(url: str) -> Iterator[Session]:
    session = session_factory(url)()
    try:
        yield session
    finally:
        session.close()
