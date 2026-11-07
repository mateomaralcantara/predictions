"""esquema inicial: resultados, usuarios, ordenes, suscripciones

Revision ID: 0001
Revises:
Create Date: 2026-11-07 16:48:58.375440
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _existe(tabla: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(tabla)


def upgrade() -> None:
    # La tabla de resultados puede existir ya en bases PostgreSQL heredadas
    # (creada por los scrapers antiguos): en ese caso se respeta tal cual.
    if not _existe("resultados_tradicionales"):
        _crear_resultados()
    _crear_cuentas()


def _crear_resultados() -> None:
    op.create_table(
        "resultados_tradicionales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("loteria", sa.String(length=80), nullable=False),
        sa.Column("primer", sa.Integer(), nullable=False),
        sa.Column("segundo", sa.Integer(), nullable=False),
        sa.Column("tercero", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fecha", "loteria", name="uq_resultado_fecha_loteria"),
    )
    with op.batch_alter_table("resultados_tradicionales", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resultados_tradicionales_fecha"), ["fecha"], unique=False)
        batch_op.create_index(batch_op.f("ix_resultados_tradicionales_loteria"), ["loteria"], unique=False)


def _crear_cuentas() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("es_admin", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_usuarios_email"), ["email"], unique=True)

    op.create_table(
        "ordenes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paypal_id", sa.String(length=64), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("monto", sa.String(length=16), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("capturada_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ordenes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ordenes_paypal_id"), ["paypal_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_ordenes_usuario_id"), ["usuario_id"], unique=False)

    op.create_table(
        "suscripciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("orden_id", sa.Integer(), nullable=True),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fin", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["orden_id"],
            ["ordenes.id"],
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("orden_id"),
    )
    with op.batch_alter_table("suscripciones", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_suscripciones_fin"), ["fin"], unique=False)
        batch_op.create_index(batch_op.f("ix_suscripciones_usuario_id"), ["usuario_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("suscripciones", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_suscripciones_usuario_id"))
        batch_op.drop_index(batch_op.f("ix_suscripciones_fin"))

    op.drop_table("suscripciones")
    with op.batch_alter_table("ordenes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ordenes_usuario_id"))
        batch_op.drop_index(batch_op.f("ix_ordenes_paypal_id"))

    op.drop_table("ordenes")
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_usuarios_email"))

    op.drop_table("usuarios")
    # resultados_tradicionales se conserva: contiene datos históricos.
