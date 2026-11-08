"""Activa Row Level Security en todas las tablas (PostgreSQL).

En Supabase el esquema ``public`` se publica en la Data API (PostgREST): sin
RLS, cualquiera con la clave ``anon`` (pública) podría leer ``usuarios``.
RLS activado y SIN políticas = la Data API no ve nada. La app no se ve
afectada: se conecta como el dueño de las tablas, que no está sujeto a RLS
(no se usa FORCE ROW LEVEL SECURITY).

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLAS = ("usuarios", "ordenes", "suscripciones", "resultados_tradicionales", "alembic_version")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for tabla in TABLAS:
        op.execute(f'ALTER TABLE IF EXISTS public."{tabla}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for tabla in TABLAS:
        op.execute(f'ALTER TABLE IF EXISTS public."{tabla}" DISABLE ROW LEVEL SECURITY')
