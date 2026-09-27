import psycopg2
from psycopg2 import OperationalError

def verificar_conexion(user, password, dbname, host="localhost", port="5432"):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        return "✅ Conexión exitosa: la contraseña es CORRECTA."
    except OperationalError as e:
        if "password authentication failed" in str(e):
            return "❌ Contraseña INCORRECTA para el usuario."
        else:
            return f"⚠️ Otro error ocurrió: {e}"

# 👉 Modifica aquí tus datos
usuario = "postgres"
contrasena = "tu_clave_a_probar"
base_datos = "loteria"

resultado = verificar_conexion(usuario, contrasena, base_datos)
print(resultado)
