# backend/tools/ver_resultados.py

import sys, os, csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database.connection import SessionLocal
from backend.database.models import ResultadoTradicional

# Inicia conexión a la base de datos
db = SessionLocal()

# Consulta todos los resultados ordenados por fecha descendente
resultados = db.query(ResultadoTradicional).order_by(ResultadoTradicional.fecha.desc()).all()

# Ruta del archivo CSV
ruta_archivo = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../todos_los_resultados.csv"))

# Crear y escribir en el CSV
with open(ruta_archivo, "w", newline="", encoding="utf-8") as archivo:
    writer = csv.writer(archivo)
    writer.writerow(["Fecha", "Lotería", "Primer", "Segundo", "Tercero"])
    for r in resultados:
        writer.writerow([r.fecha, r.loteria, r.primer, r.segundo, r.tercero])

db.close()
print(f"✅ Resultados exportados a: {ruta_archivo}")
