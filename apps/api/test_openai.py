from dotenv import load_dotenv
import os
from openai import OpenAI

# Cargar el archivo .env
load_dotenv()

# Leer la clave desde el entorno
api_key = os.getenv("OPENAI_API_KEY")
print("✅ CLAVE LEÍDA:", api_key)

# Verifica si se leyó correctamente
if not api_key:
    print("❌ No se leyó la clave. Verifica el archivo .env.")
    exit()

# Crear cliente de OpenAI
client = OpenAI(api_key=api_key)

# Hacer una prueba de conversación
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Dime 3 números de la suerte"}
        ],
        temperature=0.3
    )

    print("✅ RESPUESTA DEL MODELO:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ Error al conectar con el modelo:")
    print(e)
