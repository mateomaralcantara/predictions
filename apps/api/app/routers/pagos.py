from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..cuentas import activar_suscripcion, perfil
from ..db import Orden, utcnow
from ..deps import DB, UsuarioRequerido, get_paypal
from ..payments import PLAN_GRATIS, PLANES, PaymentError, PayPalClient
from ..ratelimit import limit

router = APIRouter(prefix="/api/pagos", tags=["pagos"])

Paypal = Annotated[PayPalClient, Depends(get_paypal)]


class NuevaOrden(BaseModel):
    plan: str = Field(min_length=1, max_length=40)


@router.get("/planes")
def planes(paypal: Paypal) -> dict:
    return {
        "pagos_habilitados": paypal.settings.paypal_enabled,
        "gratis": PLAN_GRATIS,
        "planes": [p.as_dict() for p in PLANES.values()],
    }


@router.post("/ordenes", status_code=201, dependencies=[Depends(limit("ordenes", 10))])
async def crear_orden(body: NuevaOrden, paypal: Paypal, usuario: UsuarioRequerido, db: DB) -> dict:
    try:
        orden = await paypal.crear_orden(body.plan)
    except PaymentError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    plan = PLANES[body.plan]
    db.add(Orden(paypal_id=orden["id"], usuario_id=usuario.id, plan=plan.id, monto=plan.precio, moneda=plan.moneda))
    db.commit()
    return orden


@router.post("/ordenes/{order_id}/captura", dependencies=[Depends(limit("captura", 10))])
async def capturar_orden(order_id: str, paypal: Paypal, usuario: UsuarioRequerido, db: DB) -> dict:
    orden = db.scalar(select(Orden).where(Orden.paypal_id == order_id))
    if orden is None or orden.usuario_id != usuario.id:
        raise HTTPException(404, "Orden no encontrada.")
    if orden.estado == "COMPLETADA":  # idempotente: volver a la página de éxito no cobra dos veces
        return {
            "id": orden.paypal_id,
            "estado": "COMPLETED",
            "plan": PLANES[orden.plan].as_dict(),
            "monto": orden.monto,
            "moneda": orden.moneda,
            "usuario": perfil(db, usuario),
        }
    try:
        captura = await paypal.capturar_orden(order_id)
    except PaymentError as exc:
        if exc.status_code == 409:
            orden.estado = "RECHAZADA"
            db.commit()
        raise HTTPException(exc.status_code, exc.detail) from exc

    pagado_ok = (
        captura.get("estado") == "COMPLETED"
        and captura.get("monto") == orden.monto
        and captura.get("moneda") == orden.moneda
        and (captura.get("plan") or {}).get("id") == orden.plan
    )
    if not pagado_ok:
        orden.estado = "REVISION"
        db.commit()
        raise HTTPException(402, "El pago no se completó o no coincide con el plan. Contacta a soporte.")

    orden.estado = "COMPLETADA"
    orden.capturada_en = utcnow()
    activar_suscripcion(db, usuario, orden)
    db.commit()
    return {**captura, "usuario": perfil(db, usuario)}
