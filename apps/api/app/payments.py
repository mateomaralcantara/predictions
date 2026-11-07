"""Pagos con PayPal (Orders v2).

Los precios viven SOLO en el servidor: el cliente envía el id del plan, nunca
el monto. Sin credenciales configuradas, los endpoints responden 503.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import httpx

from .config import Settings


@dataclass(frozen=True)
class Plan:
    id: str
    nombre: str
    precio: str  # string decimal: PayPal exige 2 decimales exactos
    moneda: str
    descripcion: str
    beneficios: tuple[str, ...]
    destacado: bool = False

    def as_dict(self) -> dict:
        d = asdict(self)
        d["beneficios"] = list(self.beneficios)
        return d


PLANES: dict[str, Plan] = {
    p.id: p
    for p in (
        Plan(
            "explorador",
            "Explorador",
            "9.99",
            "USD",
            "Para empezar a seguir tus loterías favoritas.",
            ("Estadísticas de todas las loterías", "Predicciones heurísticas de Loto y SuperKino", "Asistente de chat"),
        ),
        Plan(
            "platinum",
            "Platinum",
            "29.99",
            "USD",
            "Para jugadores que analizan a fondo.",
            (
                "Todo lo de Explorador",
                "Historial completo por número",
                "Números atrasados y combinaciones",
                "Gráficos avanzados",
            ),
            destacado=True,
        ),
        Plan(
            "oraculo",
            "Oráculo",
            "59.99",
            "USD",
            "Acceso total y soporte prioritario.",
            ("Todo lo de Platinum", "Soporte prioritario", "Acceso anticipado a nuevas loterías"),
        ),
    )
}

ORDER_ID_RE = re.compile(r"^[A-Z0-9]{5,40}$")


class PaymentError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class PayPalClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.settings.paypal_base_url, timeout=20, transport=self._transport)

    def _ensure_enabled(self) -> None:
        if not self.settings.paypal_enabled:
            raise PaymentError(503, "Pagos no configurados: faltan PAYPAL_CLIENT_ID / PAYPAL_SECRET.")

    async def _token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(self.settings.paypal_client_id or "", self.settings.paypal_secret or ""),
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200 or "access_token" not in resp.json():
            raise PaymentError(502, "No se pudo autenticar con PayPal.")
        return resp.json()["access_token"]

    async def crear_orden(self, plan_id: str) -> dict:
        self._ensure_enabled()
        plan = PLANES.get(plan_id)
        if plan is None:
            raise PaymentError(404, f"Plan desconocido: {plan_id}")
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": plan.id,
                    "description": f"Plan {plan.nombre}",
                    "amount": {"currency_code": plan.moneda, "value": plan.precio},
                }
            ],
            "application_context": {
                "brand_name": "Predictions RD",
                "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING",
                "return_url": f"{self.settings.frontend_url}/pago/exito",
                "cancel_url": f"{self.settings.frontend_url}/pago/cancelado",
            },
        }
        async with self._client() as client:
            token = await self._token(client)
            resp = await client.post("/v2/checkout/orders", json=body, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code not in (200, 201):
            raise PaymentError(502, "PayPal rechazó la creación de la orden.")
        data = resp.json()
        approve = next(
            (link["href"] for link in data.get("links", []) if link.get("rel") in ("approve", "payer-action")), None
        )
        if not data.get("id") or not approve:
            raise PaymentError(502, "Respuesta incompleta de PayPal.")
        return {"id": data["id"], "estado": data.get("status"), "approve_url": approve, "plan": plan.as_dict()}

    async def capturar_orden(self, order_id: str) -> dict:
        self._ensure_enabled()
        if not ORDER_ID_RE.match(order_id or ""):
            raise PaymentError(400, "Id de orden inválido.")
        async with self._client() as client:
            token = await self._token(client)
            resp = await client.post(
                f"/v2/checkout/orders/{order_id}/capture",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        if resp.status_code == 422:
            raise PaymentError(409, "La orden no se puede capturar (¿ya fue pagada o cancelada?).")
        if resp.status_code not in (200, 201):
            raise PaymentError(502, "PayPal rechazó la captura.")
        data = resp.json()
        unidad = (data.get("purchase_units") or [{}])[0]
        captura = ((unidad.get("payments") or {}).get("captures") or [{}])[0]
        plan_id = unidad.get("reference_id")
        return {
            "id": data.get("id"),
            "estado": data.get("status"),
            "plan": PLANES[plan_id].as_dict() if plan_id in PLANES else None,
            "monto": (captura.get("amount") or {}).get("value"),
            "moneda": (captura.get("amount") or {}).get("currency_code"),
        }
