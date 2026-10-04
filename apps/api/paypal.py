import os
import requests
from dotenv import load_dotenv

# 💡 Forzar carga del .env desde la raíz del proyecto
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path)

# 🔐 Credenciales de PayPal
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")
BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")

# 👀 Confirmación visual en consola
print("📦 BASE_URL cargada:", BASE_URL)
print("🔐 CLIENT_ID:", CLIENT_ID[:4] + "..." + CLIENT_ID[-4:] if CLIENT_ID else "⚠️ NO CARGADO")
print("🔐 SECRET:", SECRET[:4] + "..." + SECRET[-4:] if SECRET else "⚠️ NO CARGADO")

print("📦 BASE_URL cargada:", BASE_URL)

# 🧠 Obtener token de acceso de PayPal
def get_access_token():
    try:
        response = requests.post(
            f"{BASE_URL}/v1/oauth2/token",
            headers={"Accept": "application/json"},
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, SECRET),
        )
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            raise Exception("No se recibió token de acceso.")
        return access_token
    except Exception as e:
        print("❌ Error al obtener token de PayPal:", str(e))
        raise

# 💳 Crear una orden de pago
def create_order(amount="5.00", currency="USD"):
    try:
        amount = float(amount)  # Validar que sea un número
        token = get_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}"
                }
            }],
            "application_context": {
                "return_url": "http://localhost:5173/success",  # Cambiar en producción
                "cancel_url": "http://localhost:5173/cancel"
            }
        }

        response = requests.post(
            f"{BASE_URL}/v2/checkout/orders",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        print("💬 Respuesta de PayPal:", result)

        if "id" not in result:
            raise Exception("No se generó un ID de orden válido. Respuesta incompleta.")

        return result

    except Exception as e:
        print("❌ Error al crear orden:", str(e))
        return {"error": str(e)}

print("🔐 CLIENT_ID:", CLIENT_ID)
print("🔐 SECRET:", SECRET[:4] + "..." + SECRET[-4:])  # Solo muestra parcial

def capture_order(order_id: str):
    try:
        token = get_access_token()
        response = requests.post(
            f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Error al capturar orden:", str(e))
        return {"error": str(e)}
