from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import get_paypal
from ..payments import PLANES, PaymentError, PayPalClient

router = APIRouter(prefix="/api/pagos", tags=["pagos"])

Paypal = Annotated[PayPalClient, Depends(get_paypal)]


class NuevaOrden(BaseModel):
    plan: str = Field(min_length=1, max_length=40)


@router.get("/planes")
def planes(paypal: Paypal) -> dict:
    return {"pagos_habilitados": paypal.settings.paypal_enabled, "planes": [p.as_dict() for p in PLANES.values()]}


@router.post("/ordenes", status_code=201)
async def crear_orden(body: NuevaOrden, paypal: Paypal) -> dict:
    try:
        return await paypal.crear_orden(body.plan)
    except PaymentError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/ordenes/{order_id}/captura")
async def capturar_orden(order_id: str, paypal: Paypal) -> dict:
    try:
        return await paypal.capturar_orden(order_id)
    except PaymentError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
