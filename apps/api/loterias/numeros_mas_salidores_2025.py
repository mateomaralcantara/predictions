from sqlalchemy import create_engine, text
from datetime import datetime

# Configuración de conexión
DATABASE_URL = "postgresql://postgres:123456@localhost:5432/loterias_db"
engine = create_engine(DATABASE_URL)

# Fechas del rango
fecha_inicio = datetime(2025, 1, 2)
fecha_actual = datetime.now()

# Consulta SQL
query = text("""
    SELECT numero, COUNT(*) AS apariciones
    FROM (
        SELECT primer AS numero FROM resultados_tradicionales
        WHERE loteria ILIKE '%nacional%' AND fecha BETWEEN :fecha_inicio AND :fecha_fin
        UNION ALL
        SELECT segundo AS numero FROM resultados_tradicionales
        WHERE loteria ILIKE '%nacional%' AND fecha BETWEEN :fecha_inicio AND :fecha_fin
        UNION ALL
        SELECT tercero AS numero FROM resultados_tradicionales
        WHERE loteria ILIKE '%nacional%' AND fecha BETWEEN :fecha_inicio AND :fecha_fin
    ) AS todos
    GROUP BY numero
    ORDER BY apariciones DESC
""")

# Ejecutar consulta
with engine.connect() as conn:
    resultados = conn.execute(query, {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_actual}).fetchall()

    if resultados:
        print(f"🔢 Números más salidores en la Lotería Nacional desde el {fecha_inicio.date()} hasta hoy:\n")
        for numero, apariciones in resultados:
            print(f"Número {numero}: {apariciones} veces")
    else:
        print("⚠️ No se encontraron resultados en ese rango.")
