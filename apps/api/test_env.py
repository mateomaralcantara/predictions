import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)  # ← forzamos carga desde raíz

print("🔍 PAYPAL_CLIENT_ID:", os.getenv("PAYPAL_CLIENT_ID"))
print("🔍 PAYPAL_SECRET:", os.getenv("PAYPAL_SECRET"))
print("🔍 PAYPAL_BASE_URL:", os.getenv("PAYPAL_BASE_URL"))
