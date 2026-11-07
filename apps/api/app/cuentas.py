"""Usuarios, niveles de acceso y activación de suscripciones."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Orden, Suscripcion, Usuario, utcnow
from .payments import LIMITES, PLAN_GRATIS, PLANES, Limites


def suscripcion_activa(db: Session, usuario: Usuario | None, ahora: datetime | None = None) -> Suscripcion | None:
    """La suscripción vigente de mayor nivel (y, a igual nivel, la que dura más)."""
    if usuario is None:
        return None
    ahora = ahora or utcnow()
    vigentes = db.scalars(
        select(Suscripcion).where(
            Suscripcion.usuario_id == usuario.id, Suscripcion.inicio <= ahora, Suscripcion.fin > ahora
        )
    ).all()
    if not vigentes:
        return None
    return max(vigentes, key=lambda s: (PLANES[s.plan].nivel if s.plan in PLANES else 0, s.fin))


def nivel_de(db: Session, usuario: Usuario | None) -> int:
    sus = suscripcion_activa(db, usuario)
    if usuario is not None and usuario.es_admin:
        return max(LIMITES)
    if sus is None or sus.plan not in PLANES:
        return 0
    return PLANES[sus.plan].nivel


def limites_de(nivel: int) -> Limites:
    return LIMITES.get(nivel, LIMITES[0])


def activar_suscripcion(db: Session, usuario: Usuario, orden: Orden) -> Suscripcion:
    """Crea la suscripción de una orden pagada. Idempotente por orden.

    Si ya hay una suscripción vigente del mismo plan, la nueva empieza cuando
    termina esa (los días se acumulan). Un plan distinto empieza ya.
    """
    existente = db.scalar(select(Suscripcion).where(Suscripcion.orden_id == orden.id))
    if existente:
        return existente
    plan = PLANES[orden.plan]
    ahora = utcnow()
    ultima_mismo_plan = db.scalar(
        select(Suscripcion)
        .where(Suscripcion.usuario_id == usuario.id, Suscripcion.plan == plan.id, Suscripcion.fin > ahora)
        .order_by(Suscripcion.fin.desc())
    )
    inicio = ultima_mismo_plan.fin if ultima_mismo_plan else ahora
    sus = Suscripcion(
        usuario_id=usuario.id, orden_id=orden.id, plan=plan.id, inicio=inicio, fin=inicio + timedelta(days=plan.dias)
    )
    db.add(sus)
    return sus


def perfil(db: Session, usuario: Usuario) -> dict:
    sus = suscripcion_activa(db, usuario)
    nivel = nivel_de(db, usuario)
    lim = limites_de(nivel)
    plan = PLANES[sus.plan].as_dict() if sus and sus.plan in PLANES else dict(PLAN_GRATIS)
    futuras = db.scalars(
        select(Suscripcion).where(Suscripcion.usuario_id == usuario.id, Suscripcion.fin > utcnow())
    ).all()
    vence = max((s.fin for s in futuras if s.plan == (sus.plan if sus else None)), default=None)
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "es_admin": usuario.es_admin,
        "creado_en": usuario.creado_en.isoformat() + "Z",
        "nivel": nivel,
        "plan": plan,
        "suscripcion_vence": vence.isoformat() + "Z" if vence else None,
        "limites": {"jugadas": lim.jugadas, "historial": lim.historial, "chat_por_minuto": lim.chat_por_minuto},
    }


def historial_pagos(db: Session, usuario: Usuario) -> list[dict]:
    ordenes = db.scalars(
        select(Orden).where(Orden.usuario_id == usuario.id).order_by(Orden.creado_en.desc()).limit(50)
    ).all()
    return [
        {
            "id": o.paypal_id,
            "plan": PLANES[o.plan].nombre if o.plan in PLANES else o.plan,
            "monto": o.monto,
            "moneda": o.moneda,
            "estado": o.estado,
            "fecha": (o.capturada_en or o.creado_en).isoformat() + "Z",
        }
        for o in ordenes
    ]
